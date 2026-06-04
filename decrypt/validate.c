// wxSQLite3 AES-128 key 单块校验器(供 find_key_fast.py 经 ctypes 调用, CommonCrypto 原生速度)。
// 对每个 16B 候选: page_key=md5(key||01000000||"sAlT"); AES-128-CBC 解 page1 第一密文块,
// 比对 decrypted[0:8]==明文片段。page_key 与 page_no=1 IV 对所有库相同, 故每窗只算一次 md5。
// ⚠️ 此算法须与 decrypt/wxwork_crypto.py 的 derive_page_key/generate_initial_vector/quick_verify
//    保持一致——改页格式两边同步, 否则 C 快速路径与 Python 校验静默不符。
// 编译: clang -O2 -dynamiclib -o validate.dylib validate.c -Wno-deprecated-declarations
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <CommonCrypto/CommonCrypto.h>

static inline int passes(const uint8_t* w) {
    uint8_t seen[256];
    memset(seen, 0, 256);
    int distinct = 0, nonascii = 0;
    for (int i = 0; i < 16; i++) {
        uint8_t b = w[i];
        if (!seen[b]) { seen[b] = 1; distinct++; }
        if (b < 0x20 || b > 0x7e) nonascii++;
    }
    return distinct >= 11 && nonascii >= 3;  // 高熵二进制(排除文本/重复/指针)
}

// 扫 buf, 对每个未命中目标 t 校验; 命中写 out_keys[t*16] 并置 found[t]=1。返回新命中数。
long scan_buf(const uint8_t* buf, long len, int ntgt,
              const uint8_t* frag8, const uint8_t* cb0, const uint8_t* iv,
              uint8_t* out_keys, uint8_t* found) {
    int remaining = 0;
    for (int t = 0; t < ntgt; t++) if (!found[t]) remaining++;
    if (remaining == 0) return 0;

    long newhits = 0;
    for (long off = 0; off + 16 <= len; off++) {
        const uint8_t* w = buf + off;
        if (!passes(w)) continue;
        uint8_t mat[24];
        memcpy(mat, w, 16);
        mat[16] = 1; mat[17] = 0; mat[18] = 0; mat[19] = 0;
        memcpy(mat + 20, "sAlT", 4);
        uint8_t pk[16];
        CC_MD5(mat, 24, pk);
        for (int t = 0; t < ntgt; t++) {
            if (found[t]) continue;
            uint8_t pt[16];
            size_t mv = 0;
            if (CCCrypt(kCCDecrypt, kCCAlgorithmAES, 0, pk, 16,
                        iv + t * 16, cb0 + t * 16, 16, pt, 16, &mv) != kCCSuccess)
                continue;
            if (memcmp(pt, frag8 + t * 8, 8) == 0) {
                memcpy(out_keys + t * 16, w, 16);
                found[t] = 1;
                newhits++;
            }
        }
    }
    return newhits;
}
