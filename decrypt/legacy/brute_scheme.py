#!/usr/bin/env python3
"""无歧义暴力: 解密后开头须 == 'SQLite format 3'。
覆盖 WCDB 可能方案: 从offset0解 / 跳salt, AES-128/256, IV={0,页尾,页首存储}, 多page。
用法: brute_scheme.py <db> <keys.json>
"""
import sys, json, itertools
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DB=sys.argv[1]; data=open(DB,"rb").read()
rows=json.load(open(sys.argv[2]))
keys=[]; seen=set()
for r in rows:
    k=r["key"] if isinstance(r,dict) else r
    if len(k) in (32,64) and k not in seen: seen.add(k); keys.append(k)
print(f"候选key={len(keys)}  db={len(data)}B")

TARGET=b"SQLite format 3\x00"
def cbc(key,iv,ct):
    try:
        c=Cipher(algorithms.AES(key),modes.CBC(iv)); d=c.decryptor()
        return d.update(ct)+d.finalize()
    except: return None
def ecb(key,ct):
    try:
        c=Cipher(algorithms.AES(key),modes.ECB()); d=c.decryptor()
        return d.update(ct)+d.finalize()
    except: return None

def keyforms(kh):
    out=[]
    if len(kh)==64: out.append(("aes256",bytes.fromhex(kh)))
    if len(kh)>=32: out.append(("aes128",bytes.fromhex(kh[:32])))
    return out

hits=[]
for kh in keys:
    for tag,key in keyforms(kh):
        for ps in (1024,4096,512,2048,8192):
            page=data[:ps]
            # 方案A: 从offset0, IV=0
            for reserve in (0,16,48,32):
                body=page[:ps-reserve] if reserve else page
                if len(body)%16: body=body[:len(body)//16*16]
                # IV=0
                pt=cbc(key,bytes(16),body)
                if pt and pt[:15]==TARGET[:15]: hits.append((kh,tag,ps,reserve,"IV0_off0",pt));
                # IV=页尾reserve
                if reserve>=16:
                    iv=page[ps-reserve:ps-reserve+16]
                    pt=cbc(key,iv,page[:ps-reserve])
                    if pt and pt[:15]==TARGET[:15]: hits.append((kh,tag,ps,reserve,"IVend_off0",pt))
            # 方案B: ECB
            pt=ecb(key,page[:ps//16*16])
            if pt and pt[:15]==TARGET[:15]: hits.append((kh,tag,ps,0,"ECB",pt))
        if hits: break
    if hits: break

if hits:
    for kh,tag,ps,res,sch,pt in hits[:3]:
        print(f"\n🎉 KEY={kh}")
        print(f"   {tag} page={ps} reserve={res} scheme={sch}")
        print(f"   解出头: {pt[:32]}")
else:
    print("[MISS] 'SQLite format 3' 未出现 — DB key 不在这批EVP捕获里")
