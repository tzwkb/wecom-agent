const seen = new Set();
function hex(ptr, len) {
    return Array.from(new Uint8Array(ptr.readByteArray(len)))
        .map(b => b.toString(16).padStart(2, "0")).join("");
}
function grab(tag, keyPtr, keyLen) {
    if (keyLen <= 0 || keyLen > 128) return;
    try {
        const h = hex(keyPtr, keyLen);
        if (/^0*$/.test(h)) return;
        if (!seen.has(h)) {
            seen.add(h);
            const asc = Array.from(new Uint8Array(keyPtr.readByteArray(keyLen)))
                .map(b => (b >= 32 && b < 127) ? String.fromCharCode(b) : ".").join("");
            console.log(`[${tag}] keyLen=${keyLen} hex=${h} ascii=${asc}`);
        }
    } catch (e) {}
}

let hooked = 0;
// sqlite3_key(db, pKey, nKey)
for (const name of ["sqlite3_key", "sqlite3_key_v2", "sqlite3_rekey", "sqlite3_rekey_v2"]) {
    const f = Module.findGlobalExportByName(name);
    if (f) {
        hooked++;
        console.log(`[+] ${name} @ ${f}`);
        const keyArgIdx = name.endsWith("_v2") ? 2 : 1;  // v2: (db, zDbName, pKey, nKey)
        const lenArgIdx = name.endsWith("_v2") ? 3 : 2;
        Interceptor.attach(f, {
            onEnter(a) { grab(name, a[keyArgIdx], a[lenArgIdx].toInt32()); }
        });
    }
}

// wxSQLite3 / SQLCipher codec attach 变体
for (const name of ["sqlite3CodecAttach", "sqlite3codec_set_key", "codec_set_pass", "sqlcipher_codec_ctx_set_pass"]) {
    const f = Module.findGlobalExportByName(name);
    if (f) {
        hooked++;
        console.log(`[+] ${name} @ ${f}`);
        Interceptor.attach(f, {
            onEnter(a) {
                // 尝试几个常见的 (ptr,len) 参数位
                for (const [pi, li] of [[1,2],[2,3],[1,2]]) {
                    try { grab(name, a[pi], a[li].toInt32()); } catch(e){}
                }
            }
        });
    }
}

if (hooked === 0) {
    console.log("[!] 未找到 sqlite3_key 导出 — 搜索含 key/codec/cipher 的符号:");
    Process.enumerateModules().forEach(m => {
        try {
            m.enumerateExports().forEach(e => {
                if (/sqlite3.*key|codec|cipher.*key|set_key|key_v2/i.test(e.name))
                    console.log(`  ${m.name}: ${e.name} @ ${e.address}`);
            });
        } catch (e) {}
    });
}
console.log(`[*] sqlite hook installed (hooked ${hooked} fns)`);
