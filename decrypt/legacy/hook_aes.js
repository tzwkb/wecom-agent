const seen = new Set();
function hex(ptr, len) {
    return Array.from(new Uint8Array(ptr.readByteArray(len)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}
function note(tag, ptr, len) {
    if (len <= 0 || len > 64) return;
    try {
        const h = hex(ptr, len);
        if (h === "00".repeat(len)) return;
        const k = tag + h;
        if (!seen.has(k)) { seen.add(k); console.log(`[${tag}] len=${len} ${h}`); }
    } catch (e) {}
}

// CCCryptorCreate(op, alg, options, key, keyLength, iv, dataIn, dataInLength, dataOut, dataOutAvailable, dataOutMoved)
const create = Module.findGlobalExportByName("CCCryptorCreate");
if (create) {
    console.log("[+] CCCryptorCreate @ " + create);
    Interceptor.attach(create, {
        onEnter(a) {
            const alg = a[1].toInt32();      // kCCAlgorithmAES = 0
            const key = a[3];
            const keyLen = a[4].toInt32();
            if (alg === 0 && (keyLen === 16 || keyLen === 32 || keyLen === 24)) {
                note("AESKEY", key, keyLen);
            }
        }
    });
}

// CCCrypt(op, alg, options, key, keyLength, iv, dataIn, dataInLength, dataOut, dataOutAvailable, dataOutMoved)
const crypt = Module.findGlobalExportByName("CCCrypt");
if (crypt) {
    console.log("[+] CCCrypt @ " + crypt);
    Interceptor.attach(crypt, {
        onEnter(a) {
            const alg = a[1].toInt32();
            const key = a[3];
            const keyLen = a[4].toInt32();
            if (alg === 0 && (keyLen === 16 || keyLen === 32 || keyLen === 24)) {
                note("AESKEY", key, keyLen);
            }
        }
    });
}

// 兜底: CCCryptorCreateWithMode
const createMode = Module.findGlobalExportByName("CCCryptorCreateWithMode");
if (createMode) {
    console.log("[+] CCCryptorCreateWithMode @ " + createMode);
    Interceptor.attach(createMode, {
        onEnter(a) {
            // (op, mode, alg, padding, iv, key, keyLength, tweak, tweakLength, ...)
            const alg = a[2].toInt32();
            const key = a[5];
            const keyLen = a[6].toInt32();
            if (alg === 0 && (keyLen === 16 || keyLen === 32 || keyLen === 24)) {
                note("AESKEY", key, keyLen);
            }
        }
    });
}

if (!create && !crypt && !createMode)
    console.log("[!] 未找到 CommonCrypto AES 符号 — 可能静态链接了 openssl/wxSQLite3 自带");
console.log("[*] aes hook installed");
