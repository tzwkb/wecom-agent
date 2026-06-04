// 扫进程内存找解密后的SQLite页缓存(含明文消息),carve出来
function hex(p,n){try{return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,"0")).join("");}catch(e){return"";}}

const HDR = "53 51 4c 69 74 65 20 66 6f 72 6d 61 74 20 33 00"; // "SQLite format 3\0"
let found = 0;
const hits = [];
const ranges = Process.enumerateRanges({protection:'rw-', coalesce:true});
console.log("[*] rw ranges: " + ranges.length);
for (const r of ranges) {
    try {
        const ms = Memory.scanSync(r.base, r.size, HDR);
        for (const m of ms) {
            found++;
            // 读该页头部判断page_size(offset16-17)
            try {
                const pg = m.address.readByteArray(32);
                const b = new Uint8Array(pg);
                const ps = (b[16]<<8)|b[17];
                hits.push({addr:m.address.toString(), page_size:ps, hdr:hex(m.address,32)});
                console.log(`[SQLITE] @${m.address} page_size_field=${ps}`);
            } catch(e){}
            if (found>=20) break;
        }
    } catch(e){}
    if (found>=20) break;
}
console.log(`[*] found ${found} decrypted SQLite headers in memory`);
// 把第一个命中的整库dump思路: 报告地址供python读
rpc.exports = {
    hits(){ return hits; },
    readmem(addr, size){
        try { return hex(ptr(addr), size); } catch(e){ return ""; }
    }
};
console.log("[*] carve hook ready");
