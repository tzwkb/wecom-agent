function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}
const sched2key={};
["AES_set_decrypt_key","aes_v8_set_decrypt_key","AES_set_encrypt_key","aes_v8_set_encrypt_key"].forEach(n=>{
  const f=Module.findGlobalExportByName(n);
  if(f)Interceptor.attach(f,{onEnter(a){const b=a[1].toInt32();if(b===128||b===256)sched2key[a[2].toString()]=hex(a[0],b/8);}});
});
const samples=[];
const f=Module.findGlobalExportByName("aes_v8_cbc_encrypt");
// (in,out,len,key,ivec,enc)
Interceptor.attach(f,{onEnter(a){
  const len=a[2].toInt32(),enc=a[5].toInt32();
  if(enc!==0||len<512)return;
  if(samples.length>=200)return;
  samples.push({key:sched2key[a[3].toString()]||"",iv:hex(a[4],16),len:len,in16:hex(a[0],16)});
}});
rpc.exports={dump(){return samples;}};
console.log("v8 hook installed");
