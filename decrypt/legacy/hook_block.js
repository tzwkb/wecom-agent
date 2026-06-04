// hook AES_decrypt单块 + set_decrypt_key(线程级key关联)
// 抓 key + 输入密文块 + 输出块, 离线匹配文件反推方案
function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}
const lastKey={};
["AES_set_decrypt_key","aes_v8_set_decrypt_key","vpaes_set_decrypt_key"].forEach(n=>{
  const f=Module.findGlobalExportByName(n);
  if(f) Interceptor.attach(f,{onEnter(a){
    const bits=a[1].toInt32();
    if(bits===128||bits===256) lastKey[this.threadId]=hex(a[0],bits/8);
  }});
});
const samples=[];
// AES_decrypt(in,out,key)
const dec=Module.findGlobalExportByName("AES_decrypt");
Interceptor.attach(dec,{
  onEnter(a){ this.inp=a[0]; this.out=a[1]; this.cin=hex(a[0],16); this.k=lastKey[this.threadId]||""; },
  onLeave(){
    if(samples.length>=12) return;
    if(!this.k) return;
    samples.push({key:this.k, cipher_in:this.cin, ecb_out:hex(this.out,16)});
  }
});
rpc.exports={ dump(){ return samples; }, clear(){ samples.length=0; } };
console.log("[*] block hook installed");
