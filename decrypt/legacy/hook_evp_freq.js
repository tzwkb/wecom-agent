// 统计 EVP key 调用频率：DB 页 key 复用最频繁，消息GCM key 各一次
function hex(p, n) {
    return Array.from(new Uint8Array(p.readByteArray(n)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}
const keyLenFn = new NativeFunction(
    Module.findGlobalExportByName("EVP_CIPHER_CTX_key_length"), "int", ["pointer"]);

const freq = {};   // keyhex -> count
const ivsample = {}; // keyhex -> first iv
function rec(ctx, key, iv) {
    if (key.isNull()) return;
    let klen = 32;
    try { const k = keyLenFn(ctx); if (k>0 && k<=64) klen=k; } catch(e){}
    try {
        const kh = hex(key, klen);
        if (/^0*$/.test(kh)) return;
        freq[kh] = (freq[kh]||0) + 1;
        if (!ivsample[kh]) { try { ivsample[kh] = iv.isNull()?"":hex(iv,16); } catch(e){ ivsample[kh]=""; } }
    } catch(e){}
}

for (const name of ["EVP_DecryptInit_ex","EVP_CipherInit_ex"]) {
    const f = Module.findGlobalExportByName(name);
    if (f) Interceptor.attach(f, { onEnter(a){ rec(a[0], a[3], a[4]); } });
}

rpc.exports = {
    top() {
        const arr = Object.entries(freq).map(([k,c])=>({key:k, count:c, iv:ivsample[k]}));
        arr.sort((a,b)=>b.count-a.count);
        return arr.slice(0,15);
    },
    total(){ return Object.keys(freq).length; }
};
console.log("[*] evp freq hook installed");
