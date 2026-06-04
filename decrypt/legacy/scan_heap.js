// 扫 rw- 堆找 salt锚点 + cipher名串, dump周边(codec含key)
function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}
function pat(h){return h.match(/../g).join(" ");}
const SALT=SALT_PH;
const dumps=[];
const ranges=Process.enumerateRanges({protection:'rw-',coalesce:true});
console.log("[*] rw- ranges:"+ranges.length);
// 1) salt 锚点
let n=0;
for(const r of ranges){
  try{
    const ms=Memory.scanSync(r.base,r.size,pat(SALT));
    for(const m of ms){
      n++;
      dumps.push({anchor:"salt",addr:m.address.toString(),around:hex(m.address.sub(64),192)});
      if(n>=30)break;
    }
  }catch(e){}
  if(n>=30)break;
}
console.log("[*] salt命中:"+n);
// 2) cipher名串 "aes-256-cbc"
const cipherStr="61 65 73 2d 32 35 36 2d 63 62 63"; // aes-256-cbc
let c=0;
for(const r of ranges){
  try{
    const ms=Memory.scanSync(r.base,r.size,cipherStr);
    for(const m of ms){
      c++;
      dumps.push({anchor:"cipherstr",addr:m.address.toString(),around:hex(m.address.sub(128),256)});
      if(c>=20)break;
    }
  }catch(e){}
  if(c>=20)break;
}
console.log("[*] aes-256-cbc命中:"+c);
rpc.exports={dump(){return dumps;}};
console.log("[*] heap scan done");
