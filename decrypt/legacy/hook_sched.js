// 精确关联: set_decrypt_key(userKey,bits,schedule) 记 schedule指针→裸key
// AES_decrypt(in,out,schedule) 用 schedule指针反查真实key
function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}
const sched2key={};  // schedule地址 -> keyhex
["AES_set_decrypt_key","aes_v8_set_decrypt_key","vpaes_set_decrypt_key"].forEach(n=>{
  const f=Module.findGlobalExportByName(n);
  if(f) Interceptor.attach(f,{onEnter(a){
    const bits=a[1].toInt32();
    if(bits!==128&&bits!==256) return;
    sched2key[a[2].toString()]=hex(a[0],bits/8);
  }});
});
const samples=[];
const dec=Module.findGlobalExportByName("AES_decrypt");
Interceptor.attach(dec,{
  onEnter(a){ this.sched=a[2].toString(); this.cin=hex(a[0],16); this.outp=a[1]; },
  onLeave(){
    if(samples.length>=16) return;
    const k=sched2key[this.sched];
    if(!k) return;
    samples.push({key:k, cipher_in:this.cin, ecb_out:hex(this.outp,16)});
  }
});
rpc.exports={ dump(){ return samples; }, clear(){ samples.length=0; } };
console.log("[*] sched hook installed");
