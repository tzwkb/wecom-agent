const seen = new Set();

function hex(ptr, len) {
    return Array.from(new Uint8Array(ptr.readByteArray(len)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}

const pbkdf = Module.findGlobalExportByName("CCKeyDerivationPBKDF");
if (pbkdf) {
    console.log("[+] CCKeyDerivationPBKDF @ " + pbkdf);
    Interceptor.attach(pbkdf, {
        onEnter(a) {
            this.pwd = a[1]; this.pwdLen = a[2].toInt32();
            this.salt = a[3]; this.saltLen = a[4].toInt32();
            this.rounds = a[6].toInt32();
            this.dk = a[7]; this.dkLen = a[8] ? a[8].toInt32() : 0;
        },
        onLeave(ret) {
            if (this.dkLen <= 0 || this.dkLen > 64) return;
            console.log(`[PBKDF] pwdLen=${this.pwdLen} saltLen=${this.saltLen} rounds=${this.rounds} dkLen=${this.dkLen} ret=${ret.toInt32()}`);
            try {
                if (this.pwdLen > 0 && this.pwdLen <= 64) {
                    const p = hex(this.pwd, this.pwdLen);
                    if (!seen.has("p" + p)) { seen.add("p" + p); console.log(`  PASSWORD=${p}`); }
                }
                if (this.saltLen > 0 && this.saltLen <= 64) {
                    const s = hex(this.salt, this.saltLen);
                    if (!seen.has("s" + s)) { seen.add("s" + s); console.log(`  SALT=${s}`); }
                }
                if (ret.toInt32() === 0) {
                    const d = hex(this.dk, this.dkLen);
                    if (!seen.has("d" + d)) { seen.add("d" + d); console.log(`  DERIVED=${d}`); }
                }
            } catch (e) { console.log("  read_err " + e); }
        }
    });
} else {
    console.log("[!] CCKeyDerivationPBKDF NOT found — 企业微信可能自带crypto。搜索候选符号:");
    Process.enumerateModules().forEach(m => {
        if (!/企业微信|WXWork|WeWork|Work/i.test(m.name)) return;
        m.enumerateExports().forEach(e => {
            if (/pbkdf|derive|sqlite3_key|codec|aes.*key|rawkey/i.test(e.name))
                console.log(`  ${m.name}: ${e.name}`);
        });
    });
}
console.log("[*] probe installed");
