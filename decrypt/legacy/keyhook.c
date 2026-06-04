// v6: hook EVP_DecryptUpdate + CRYPTO_cbc128_decrypt + aes_v8_cbc_encrypt
// 匹配 Info.db/Session.db 页, 命中即dump明文。覆盖所有解密路径。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <mach/mach.h>
#include <libkern/OSCacheControl.h>
#include <unistd.h>
#include <dirent.h>

// 路径运行时解析: $HOME + 沙盒容器; profile 自动探测(或 WECOM_PROFILE 覆盖)。不硬编码用户名/profile。
#define CONTAINER "Library/Containers/com.tencent.WeWorkMac/Data"
static char g_log[1024], g_dump[1024], g_carve[1024], g_prof[1200];
static void setup_paths(){
    const char* home = getenv("HOME"); if(!home||!*home) home = "/tmp";
    char data[800]; snprintf(data, sizeof(data), "%s/%s", home, CONTAINER);
    snprintf(g_log,   sizeof(g_log),   "%s/dbkey.log",     data);
    snprintf(g_dump,  sizeof(g_dump),  "%s/page_dump.bin", data);
    snprintf(g_carve, sizeof(g_carve), "%s/carve.bin",     data);
    char prof[300] = "";
    const char* env = getenv("WECOM_PROFILE");
    if(env && *env){ snprintf(prof, sizeof(prof), "%s", env); }
    else {
        char pdir[900]; snprintf(pdir, sizeof(pdir), "%s/Documents/Profiles", data);
        DIR* d = opendir(pdir);
        if(d){ struct dirent* e; while((e = readdir(d))){ if(e->d_name[0] != '.'){ snprintf(prof, sizeof(prof), "%s", e->d_name); break; } } closedir(d); }
    }
    snprintf(g_prof, sizeof(g_prof), "%s/Documents/Profiles/%s/", data, prof);
}

static void logmsg(const char* m){ FILE*f=fopen(g_log,"a"); if(f){fprintf(f,"%s\n",m);fclose(f);} }

// 加载多个db做匹配锚点
#define NDB 3
static const char* dbnames[NDB]={"Messages1/Info.db","Messages1/Session.db","Messages1/InfoMFTS6.db"};
static unsigned char* g_db[NDB]={0}; static long g_sz[NDB]={0};
static void load_dbs(){
    for(int i=0;i<NDB;i++){
        char path[512]; snprintf(path,sizeof(path),"%s%s",g_prof,dbnames[i]);
        FILE*f=fopen(path,"rb"); if(!f){continue;}
        fseek(f,0,SEEK_END); g_sz[i]=ftell(f); fseek(f,0,SEEK_SET);
        g_db[i]=malloc(g_sz[i]); fread(g_db[i],1,g_sz[i],f); fclose(f);
        char b[128]; snprintf(b,sizeof(b),"loaded db%d %s %ldB",i,dbnames[i],g_sz[i]); logmsg(b);
    }
}
// in前16字节匹配哪个db的哪页(返回 db_id*10000000 + offset, 否则-1)
static long match(const unsigned char* in){
    for(int i=0;i<NDB;i++){
        if(!g_db[i])continue;
        int np=g_sz[i]/4096;
        for(int p=0;p<np;p++){
            unsigned char* pg=g_db[i]+(long)p*4096;
            if(memcmp(in,pg,16)==0||memcmp(in,pg+16,16)==0||memcmp(in,pg+24,16)==0)
                return (long)i*100000000L+(long)p*4096;
        }
    }
    return -1;
}

static void* mk_tramp(void* t){
    uint32_t* s=(uint32_t*)t;
    uint32_t* tr=mmap(0,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    if(tr==MAP_FAILED)return 0;
    tr[0]=s[0];tr[1]=s[1];tr[2]=s[2];tr[3]=s[3];
    tr[4]=0x58000051;tr[5]=0xd61f0220;
    uint64_t b=(uint64_t)t+16; memcpy(&tr[6],&b,8);
    mprotect(tr,4096,PROT_READ|PROT_EXEC); sys_icache_invalidate(tr,64);
    return tr;
}
static int patch(void* t,void* h){
    uint32_t c[4]; c[0]=0x58000051;c[1]=0xd61f0220; uint64_t hh=(uint64_t)h; memcpy(&c[2],&hh,8);
    vm_address_t a=(vm_address_t)t;
    if(vm_protect(mach_task_self(),a,16,FALSE,VM_PROT_READ|VM_PROT_WRITE|VM_PROT_COPY)!=KERN_SUCCESS)return -1;
    memcpy(t,c,16);
    vm_protect(mach_task_self(),a,16,FALSE,VM_PROT_READ|VM_PROT_EXECUTE);
    sys_icache_invalidate(t,16); return 0;
}
static int g_n=0;
static void do_dump(int fn,const unsigned char* in,const unsigned char* out,int len){
    if(g_n>=3000)return;
    if(len<512||len>8192)return;
    long m=match(in); if(m<0)return;
    FILE*f=fopen(g_dump,"ab");
    if(f){ int n=len>4096?4096:len;
        fwrite(&fn,4,1,f); fwrite(&m,8,1,f); fwrite(&n,4,1,f); fwrite(out,1,n,f); fclose(f); g_n++;
        if(g_n<=3){ char b[64]; snprintf(b,sizeof(b),"DUMP fn=%d m=%ld len=%d",fn,m,n); logmsg(b);} }
}

// EVP_DecryptUpdate(ctx,out,outl,in,inl): x1=out,x3=in,x4=inl
typedef int(*evpdu_t)(void*,unsigned char*,int*,const unsigned char*,int);
static evpdu_t tr_evpdu=0;
static int h_evpdu(void* c,unsigned char* out,int* ol,const unsigned char* in,int inl){
    int r=tr_evpdu(c,out,ol,in,inl); if(in&&out)do_dump(1,in,out,inl); return r; }
// CRYPTO_cbc128_decrypt(in,out,len,key,ivec,block): x0=in,x1=out,x2=len
typedef void(*cbc_t)(const unsigned char*,unsigned char*,size_t,const void*,unsigned char*,void*);
static cbc_t tr_cbc=0;
static void h_cbc(const unsigned char* in,unsigned char* out,size_t len,const void* key,unsigned char* iv,void* blk){
    tr_cbc(in,out,len,key,iv,blk); if(in&&out)do_dump(2,in,out,(int)len); }
// aes_v8_cbc_encrypt(in,out,len,key,ivec,enc): x0=in,x1=out,x2=len,x5=enc
typedef void(*v8_t)(const unsigned char*,unsigned char*,size_t,const void*,unsigned char*,int);
static v8_t tr_v8=0;
static void h_v8(const unsigned char* in,unsigned char* out,size_t len,const void* key,unsigned char* iv,int enc){
    tr_v8(in,out,len,key,iv,enc); if(enc==0&&in&&out)do_dump(3,in,out,(int)len); }


#include <pthread.h>
extern kern_return_t mach_vm_region(vm_map_t,mach_vm_address_t*,mach_vm_size_t*,vm_region_flavor_t,vm_region_info_t,mach_msg_type_number_t*,mach_port_t*);
extern kern_return_t mach_vm_read_overwrite(vm_map_t,mach_vm_address_t,mach_vm_size_t,mach_vm_address_t,mach_vm_size_t*);
static void* carve_thread(void* arg){
    sleep(20);
    logmsg("carve start(fine)");
    task_t task=mach_task_self();
    mach_vm_address_t addr=0; mach_vm_size_t size=0;
    vm_region_basic_info_data_64_t info; mach_msg_type_number_t cnt; mach_port_t obj;
    int dumped=0;
    FILE* out=fopen(g_carve,"wb");
    unsigned char* buf=malloc(65536);
    while(dumped<6000){
        cnt=VM_REGION_BASIC_INFO_COUNT_64;
        if(mach_vm_region(task,&addr,&size,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&cnt,&obj)!=KERN_SUCCESS)break;
        if((info.protection&3)==3 && size>=4096 && size<400000000){
            mach_vm_address_t end=addr+size;
            for(mach_vm_address_t a=addr;a+4096<=end;a+=512){ // 512步长
                mach_vm_size_t got=0;
                if(mach_vm_read_overwrite(task,a,4096,(mach_vm_address_t)buf,&got)==0 && got==4096){
                    unsigned char t=buf[0];
                    if(t==0x0d||t==0x05||t==0x0a||t==0x02){
                        int nc=(buf[3]<<8)|buf[4]; int cs=(buf[5]<<8)|buf[6];
                        if(nc>0&&nc<400&&cs>=8&&cs<=4096){
                            // 排除CEF(含http/cfurl/cache的页跳过)
                            int cef=0;
                            for(int k=0;k<4080;k++){ if(buf[k]=='c'&&buf[k+1]=='f'&&buf[k+2]=='u'&&buf[k+3]=='r'){cef=1;break;} if(buf[k]=='h'&&buf[k+1]=='t'&&buf[k+2]=='t'&&buf[k+3]=='p'){cef=1;break;} }
                            if(!cef){ fwrite(&a,8,1,out);fwrite(buf,1,4096,out);dumped++; if(dumped>=6000)break; a+=3584; }
                        }
                    }
                }
            }
        }
        addr+=size;
    }
    fclose(out); free(buf);
    char b[64]; snprintf(b,sizeof(b),"carve done %d",dumped); logmsg(b);
    return 0;
}

__attribute__((constructor))
static void init(){
    setup_paths(); logmsg("dylib v7 loaded"); load_dbs();
    void* a=dlsym(RTLD_DEFAULT,"EVP_DecryptUpdate");
    if(a){tr_evpdu=(evpdu_t)mk_tramp(a); if(tr_evpdu&&patch(a,(void*)h_evpdu)==0)logmsg("evpdu hooked");}
    void* b=dlsym(RTLD_DEFAULT,"CRYPTO_cbc128_decrypt");
    if(b){tr_cbc=(cbc_t)mk_tramp(b); if(tr_cbc&&patch(b,(void*)h_cbc)==0)logmsg("cbc hooked");}
    void* c=dlsym(RTLD_DEFAULT,"aes_v8_cbc_encrypt");
    if(c){tr_v8=(v8_t)mk_tramp(c); if(tr_v8&&patch(c,(void*)h_v8)==0)logmsg("v8 hooked");}
    pthread_t th; pthread_create(&th,0,carve_thread,0);
}
