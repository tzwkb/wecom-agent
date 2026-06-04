// 按 cipher NID 区分: CBC=DB页key, GCM=消息key
function hex(p, n) {
    return Array.from(new Uint8Array(p.readByteArray(n)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}
const klenFn = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_CTX_key_length"), "int", ["pointer"]);
const cipherFn = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_CTX_cipher"), "pointer", ["pointer"]);
const nidFn = new NativeFunction(Module.findGlobalExportByName("EVP_CIPHER_nid"), "int", ["pointer"]);

const rows = {};  // key|nid -> {count, iv, klen, nid}
function rec(ctx, key, iv) {
    if (key.isNull()) return;
    let klen = 32, nid = -1;
    try { const k = klenFn(ctx); if (k>0&&k<=64) klen=k; } catch(e){}
    try { nid = nidFn(cipherFn(ctx)); } catch(e){}
    try {
        const kh = hex(key, klen);
        if (/^0*$/.test(kh)) return;
        const id = kh + "|" + nid;
        if (!rows[id]) {
            let ivh=""; try{ ivh = iv.isNull()?"":hex(iv,16);}catch(e){}
            rows[id] = {key:kh, count:0, iv:ivh, klen, nid};
        }
        rows[id].count++;
    } catch(e){}
}
for (const name of ["EVP_DecryptInit_ex","EVP_CipherInit_ex"]) {
    const f = Module.findGlobalExportByName(name);
    if (f) Interceptor.attach(f, { onEnter(a){ rec(a[0], a[3], a[4]); } });
}
rpc.exports = {
    dump(){ return Object.values(rows).sort((a,b)=>b.count-a.count); }
};
console.log("[*] evp nid hook installed");
