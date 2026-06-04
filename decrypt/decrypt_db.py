#!/usr/bin/env python3
"""解密企业微信 wxSQLite3 DB → 标准 SQLite。
方案: page_size=1024, reserve=16(页尾IV), AES-256-CBC, 已派生key直接用。
用法: decrypt_db.py <enc_db> <key_hex> <out_db>
"""
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ENC = sys.argv[1]
KEY = bytes.fromhex(sys.argv[2])
OUT = sys.argv[3]
PAGE = 1024
RESERVE = 16
HDR = b"SQLite format 3\x00"

data = open(ENC, "rb").read()
n_pages = len(data) // PAGE
out = bytearray()

def dec(iv, ct):
    c = Cipher(algorithms.AES(KEY), modes.CBC(iv)); d = c.decryptor()
    return d.update(ct) + d.finalize()

for i in range(n_pages):
    page = data[i*PAGE:(i+1)*PAGE]
    iv = page[PAGE-RESERVE:PAGE]
    if i == 0:
        ct = page[16:PAGE-RESERVE]
        pt = dec(iv, ct)
        out += HDR + pt + page[PAGE-RESERVE:PAGE]
    else:
        ct = page[:PAGE-RESERVE]
        pt = dec(iv, ct)
        out += pt + page[PAGE-RESERVE:PAGE]

open(OUT, "wb").write(out)
print(f"解密 {n_pages} 页 → {OUT} ({len(out)} bytes)")
print(f"输出头16字节: {out[:16]}")
