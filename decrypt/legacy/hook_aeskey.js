// hook OpenSSL 低层 AES key 设置: arg0=裸key, arg1=bits。DB页解密每次调用。
function hex(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}
const freq={};  // keyhex -> {count,bits,fn}
function rec(fn, userKey, bits){
    if(userKey.isNull()) return;
    if(bits!==128 && bits!==192 && bits!==256) return;
    try{
        const kh=hex(userKey, bits/8);
        if(/^0*$/.test(kh)) return;
        if(!freq[kh]) freq[kh]={count:0,bits,fn};
        freq[kh].count++;
    }catch(e){}
}
["AES_set_decrypt_key","AES_set_encrypt_key","aes_v8_set_decrypt_key","aes_v8_set_encrypt_key","vpaes_set_decrypt_key","vpaes_set_encrypt_key"].forEach(name=>{
    const f=Module.findGlobalExportByName(name);
    if(f) Interceptor.attach(f,{ onEnter(a){ rec(name, a[0], a[1].toInt32()); } });
});
rpc.exports={ dump(){ return Object.entries(freq).map(([k,v])=>({key:k,...v})).sort((a,b)=>b.count-a.count); } };
console.log("[*] aeskey hook installed");
