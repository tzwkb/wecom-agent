// 详细记录 CommonCrypto AES 调用：key+iv+dataLen，识别 DB 页(4096)解密
function hex(ptr, len) {
    return Array.from(new Uint8Array(ptr.readByteArray(len)))
        .map(b => b.toString(16).padStart(2,"0")).join("");
}
const stats = {};  // key_hex -> {count, lens:Set}
function rec(key, keyLen, iv, ivLen, dataLen) {
    if (keyLen <= 0 || keyLen > 64) return;
    let kh;
    try { kh = hex(key, keyLen); } catch(e){ return; }
    if (/^0*$/.test(kh)) return;
    if (!stats[kh]) stats[kh] = { count:0, lens:new Set(), keyLen, iv:null };
    stats[kh].count++;
    stats[kh].lens.add(dataLen);
    if (!stats[kh].iv && iv && ivLen>0) { try { stats[kh].iv = hex(iv, ivLen); } catch(e){} }
}

const create = Module.findGlobalExportByName("CCCryptorCreate");
if (create) Interceptor.attach(create, { onEnter(a){
    // (op,alg,options,key,keyLength,iv,...)
    if (a[1].toInt32()===0) rec(a[3], a[4].toInt32(), a[5], 16, -1);
}});
const createMode = Module.findGlobalExportByName("CCCryptorCreateWithMode");
if (createMode) Interceptor.attach(createMode, { onEnter(a){
    // (op,mode,alg,padding,iv,key,keyLength,...)
    if (a[2].toInt32()===0) rec(a[5], a[6].toInt32(), a[4], 16, -1);
}});
const crypt = Module.findGlobalExportByName("CCCrypt");
if (crypt) Interceptor.attach(crypt, { onEnter(a){
    // (op,alg,options,key,keyLength,iv,dataIn,dataInLength,...)
    if (a[1].toInt32()===0) rec(a[3], a[4].toInt32(), a[5], 16, a[7].toInt32());
}});

// CCCryptorUpdate(cryptorRef, dataIn, dataInLength, ...) — 记录块大小到最近的cryptor难关联，跳过

rpc.exports = {
    dump() {
        const out = [];
        for (const k in stats) {
            out.push({ key:k, keyLen:stats[k].keyLen, count:stats[k].count,
                       lens:Array.from(stats[k].lens), iv:stats[k].iv });
        }
        return out;
    }
};
console.log("[*] aes2 hook installed (create="+!!create+" mode="+!!createMode+" crypt="+!!crypt+")");
