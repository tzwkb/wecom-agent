// hook EVP_DecryptUpdate: 对非GCM的ctx, dump cipher_data(含AES密钥编排表)
function hex(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}
const getData = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_CTX_get_cipher_data"),"pointer",["pointer"]);
const cipherFn = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_CTX_cipher"),"pointer",["pointer"]);
const nidFn = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_nid"),"int",["pointer"]);

const dumps = {};  // nid -> set of cipher_data hex
const f = Module.findGlobalExportByName("EVP_DecryptUpdate");
Interceptor.attach(f, {
    onEnter(a){
        const ctx=a[0], inlen=a[4]?a[4].toInt32():-1;
        let nid=-1;
        try{ nid=nidFn(cipherFn(ctx)); }catch(e){return;}
        if (nid===901) return;  // 跳过 GCM 消息
        try{
            const cd=getData(ctx);
            if(cd.isNull()) return;
            const dump=hex(cd,256);  // AES_KEY: rd_key[60]*4=240B + rounds
            const key=nid+"|"+dump.slice(0,32);
            if(!dumps[key]){ dumps[key]=1; console.log(`[CTX] nid=${nid} inlen=${inlen} cipher_data=${dump}`); }
        }catch(e){}
    }
});
console.log("[*] ctx dump hook installed");
