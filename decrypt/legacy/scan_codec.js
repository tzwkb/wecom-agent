// 进程内扫描 wxSQLite3 codec_ctx：搜 db 文件 salt，dump 周边定位 key
// 由 attach_scan.py 注入，salt 通过 rpc 传入
const SALT_HEX = SALT_PLACEHOLDER;  // 由 python 替换

function toHex(arr) {
    return Array.from(new Uint8Array(arr)).map(b => b.toString(16).padStart(2,"0")).join("");
}

function pattern(hex) {
    return hex.match(/../g).join(" ");
}

console.log("[*] scanning for salt " + SALT_HEX);
let hitCount = 0;
const ranges = Process.enumerateRanges({ protection: 'r--', coalesce: true });
console.log("[*] readable ranges: " + ranges.length);

const pat = pattern(SALT_HEX);
let totalMB = 0;
for (const r of ranges) {
    totalMB += r.size / 1048576;
    try {
        const matches = Memory.scanSync(r.base, r.size, pat);
        for (const m of matches) {
            hitCount++;
            // dump salt 前后 96 字节，codec key 常在 salt 附近
            const start = m.address.sub(96);
            try {
                const around = toHex(start.readByteArray(208));
                console.log(`[HIT#${hitCount}] @${m.address} (range ${r.base})`);
                console.log(`  ctx: ${around}`);
            } catch (e) {
                console.log(`[HIT#${hitCount}] @${m.address} (read周边失败 ${e})`);
            }
            if (hitCount >= 40) break;
        }
    } catch (e) {}
    if (hitCount >= 40) break;
}
console.log(`[*] scanned ~${Math.round(totalMB)}MB, salt hits: ${hitCount}`);
console.log("[*] scan done");
