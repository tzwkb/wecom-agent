// hook AES_cbc_encrypt + set_decrypt_key: 捕获 key+iv+密文+明文 三元组(decrypt调用)
function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}
const lastKey={};  // threadId -> {key,bits}
["AES_set_decrypt_key","aes_v8_set_decrypt_key","vpaes_set_decrypt_key"].forEach(n=>{
  const f=Module.findGlobalExportByName(n);
  if(f) Interceptor.attach(f,{onEnter(a){
    const bits=a[1].toInt32();
    if(bits===128||bits===256){ lastKey[this.threadId]=hex(a[0],bits/8); }
  }});
});
const samples=[];
const cbc=Module.findGlobalExportByName("AES_cbc_encrypt");
// AES_cbc_encrypt(in,out,len,key,ivec,enc)
Interceptor.attach(cbc,{
  onEnter(a){
    this.enc=a[5].toInt32();
    this.len=a[2].toInt32();
    this.inp=a[0]; this.out=a[1]; this.iv=a[4];
    this.cin=hex(a[0],16); this.civ=hex(a[4],16);
    this.k=lastKey[this.threadId]||"";
  },
  onLeave(){
    if(this.enc!==0) return;            // 只要解密
    if(this.len<256) return;            // 页级
    if(samples.length>=8) return;
    samples.push({key:this.k, iv:this.civ, len:this.len,
                  cipher_in:this.cin, plain_out:hex(this.out,32)});
  }
});
rpc.exports={ dump(){ return samples; } };
console.log("[*] cbc hook installed");
