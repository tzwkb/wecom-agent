// 抓 OpenSSL EVP DB key + PBKDF2 派生
function hex(p, n) {
    return Array.from(new Uint8Array(p.readByteArray(n)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}
const keyLenFn = new NativeFunction(
    Module.findGlobalExportByName("EVP_CIPHER_CTX_key_length"), "int", ["pointer"]);

const seen = new Set();
function grabKey(tag, ctx, key, iv) {
    if (key.isNull()) return;
    let klen = 32;
    try { const k = keyLenFn(ctx); if (k > 0 && k <= 64) klen = k; } catch (e) {}
    try {
        const kh = hex(key, klen);
        if (/^0*$/.test(kh)) return;
        const ivh = iv.isNull() ? "" : hex(iv, 16);
        if (!seen.has(kh)) {
            seen.add(kh);
            console.log(`[${tag}] keyLen=${klen} KEY=${kh} IV=${ivh}`);
        }
    } catch (e) {}
}

// EVP_DecryptInit_ex(ctx, type, impl, key, iv)
for (const name of ["EVP_DecryptInit_ex", "EVP_CipherInit_ex", "EVP_EncryptInit_ex"]) {
    const f = Module.findGlobalExportByName(name);
    if (f) Interceptor.attach(f, {
        onEnter(a) { this.ctx = a[0]; this.key = a[3]; this.iv = a[4]; },
        onLeave() { grabKey(name, this.ctx, this.key, this.iv); }
    });
}

// PKCS5_PBKDF2_HMAC(pass, passlen, salt, saltlen, iter, digest, keylen, out)
const pb = Module.findGlobalExportByName("PKCS5_PBKDF2_HMAC");
if (pb) Interceptor.attach(pb, {
    onEnter(a) {
        this.pass = a[0]; this.passlen = a[1].toInt32();
        this.salt = a[2]; this.saltlen = a[3].toInt32();
        this.iter = a[4].toInt32(); this.keylen = a[6].toInt32(); this.out = a[7];
    },
    onLeave() {
        try {
            const p = this.passlen > 0 && this.passlen <= 128 ? hex(this.pass, this.passlen) : "";
            const s = this.saltlen > 0 && this.saltlen <= 64 ? hex(this.salt, this.saltlen) : "";
            const o = this.keylen > 0 && this.keylen <= 64 ? hex(this.out, this.keylen) : "";
            const sig = "pb" + o;
            if (!seen.has(sig)) {
                seen.add(sig);
                console.log(`[PBKDF2] iter=${this.iter} keylen=${this.keylen} PASS=${p} SALT=${s} DERIVED=${o}`);
            }
        } catch (e) {}
    }
});
console.log("[*] evp hook installed");
