#!/usr/bin/env python3
"""用抓到的 key 试解 wxSQLite3 DB。自动尝试多种 page/reserve/KDF 方案。
用法: try_decrypt.py <db> <key_hex>
key_hex 可为 16字节(32hex,直接AES key) 或 ASCII形式。
"""
import sys, hashlib, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DB = sys.argv[1]
KEY_ARG = sys.argv[2]

data = open(DB, "rb").read()
salt = data[:16]
SQLITE_HDR = b"SQLite format 3\x00"

def aes_cbc_dec(key, iv, ct):
    c = Cipher(algorithms.AES(key), modes.CBC(iv))
    d = c.decryptor()
    return d.update(ct) + d.finalize()

def try_scheme(raw_key, page_size, reserve, kdf_iter, label):
    # KDF: 若 kdf_iter>0 用 PBKDF2(raw_key, salt) 派生; 否则直接用 raw_key
    if kdf_iter > 0:
        key = hashlib.pbkdf2_hmac("sha1", raw_key, salt, kdf_iter, dklen=len(raw_key))
    else:
        key = raw_key
    # 第一页: 跳过16字节salt, 加密区到 page_size-reserve, IV在reserve区开头
    first = data[:page_size]
    enc_start = 16
    enc_end = page_size - reserve
    if reserve < 16:
        return False
    iv = first[enc_end:enc_end + 16]
    ct = first[enc_start:enc_end]
    if len(ct) % 16 != 0:
        ct = ct[:len(ct) // 16 * 16]
    try:
        pt = aes_cbc_dec(key, iv, ct)
    except Exception as e:
        return False
    # 解密后应是 page1 内容(salt之后), SQLite header前16字节已被salt替换
    # 检查: 解出的内容里 page1 的 b-tree 头特征, 或可读ASCII比例
    # 更强校验: page_size 字段在 header offset 16-17, 但我们跳过了header
    # 改判据: 解出数据中含 "SQLite" 或大量结构化字节
    printable = sum(1 for b in pt[:200] if 9 <= b <= 126)
    if SQLITE_HDR[:6] in pt or printable > 120:
        print(f"[HIT] {label} ps={page_size} reserve={reserve} kdf={kdf_iter}")
        print(f"      解出前64字节: {pt[:64].hex()}")
        print(f"      ASCII: {bytes(b if 32<=b<127 else 46 for b in pt[:64])}")
        return True
    return False

# 准备候选 key 形式
cands = []
kh = KEY_ARG.strip()
if len(kh) == 32:  # 32 hex = 16 bytes
    cands.append(("hex16", bytes.fromhex(kh)))
    cands.append(("ascii16", kh.encode()[:16] if len(kh.encode())>=16 else None))
# ASCII 解码形式
try:
    ascii_form = bytes.fromhex(kh)
    if len(ascii_form) == 16:
        cands.append(("ascii_decoded", ascii_form))
        # 该ascii串本身当作key
        s = ascii_form.decode("latin1")
except Exception:
    pass

cands = [(n, k) for n, k in cands if k and len(k) in (16, 24, 32)]
print(f"salt={salt.hex()}  候选key: {[(n,k.hex()) for n,k in cands]}")
print()

found = False
for name, key in cands:
    for ps in (4096, 1024):
        for reserve in (48, 32, 16, 0):
            for kdf in (0, 1, 64000, 256000):
                if try_scheme(key, ps, reserve, kdf, f"{name}"):
                    found = True
if not found:
    print("[MISS] 所有方案未命中 — key 可能非DB key,或方案更特殊")
