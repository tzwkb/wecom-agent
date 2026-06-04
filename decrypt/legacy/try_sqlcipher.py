#!/usr/bin/env python3
"""严格判据批量试解 SQLCipher DB。
判据: 解密 page1(跳过16B salt) 后, db偏移21-23 必须 == 40 20 20 (SQLite固定payload比例),
      且偏移16-17为合法页大小。
用法: try_sqlcipher.py <db> <keys.json>
"""
import sys, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DB = sys.argv[1]
data = open(DB, "rb").read()
salt = data[:16]
with open(sys.argv[2]) as f:
    rows = json.load(f)
keys, seen = [], set()
for r in rows:
    k = r["key"]
    if len(k) == 64 and k not in seen:
        seen.add(k); keys.append(k)
print(f"salt={salt.hex()}  候选32B key={len(keys)}")

def dec(key, iv, ct):
    c = Cipher(algorithms.AES(key), modes.CBC(iv)); d = c.decryptor()
    return d.update(ct) + d.finalize()

VALID_PS = {512,1024,2048,4096,8192,16384,32768,65536}

def test(key_hex, page_size, reserve, iv_at_end):
    key = bytes.fromhex(key_hex)
    page1 = data[:page_size]
    if iv_at_end:
        iv = page1[page_size-reserve : page_size-reserve+16]
        ct = page1[16 : page_size-reserve]
    else:
        iv = bytes(16)
        ct = page1[16 : page_size]
    if len(ct) % 16 or len(iv) != 16:
        return None
    try:
        pt = dec(key, iv, ct)   # pt[0] = db offset16
    except Exception:
        return None
    # 偏移21-23 = pt[5:8]  应为 40 20 20
    if len(pt) >= 8 and pt[5]==0x40 and pt[6]==0x20 and pt[7]==0x20:
        ps_field = (pt[0]<<8)|pt[1]   # 偏移16-17
        return pt, ps_field
    return None

hit=False
for kh in keys:
    for ps in (1024,4096,2048,512,8192):
        for reserve in (48,32,16,24,64,0):
            for iv_end in (True, False):
                r = test(kh, ps, reserve, iv_end)
                if r:
                    pt, psf = r
                    print(f"\n🎉 [HIT] key={kh}")
                    print(f"   page_size={ps} reserve={reserve} iv_at_end={iv_end}")
                    print(f"   偏移21-23=40 20 20 ✓  页大小字段={psf}")
                    print(f"   page1[16:48]={pt[:32].hex()}")
                    hit=True; break
            if hit: break
        if hit: break
    if hit: break
if not hit:
    print("[MISS] 严格判据下无命中")
