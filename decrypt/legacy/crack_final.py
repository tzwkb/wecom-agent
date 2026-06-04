#!/usr/bin/env python3
"""综合试解: 对每个裸key, 试两类验证。
 A) 整库加密: 解密后开头=='SQLite format 3'
 B) SQLCipher salt: 跳16B salt解密, 偏移21-23==40 20 20
用法: crack_final.py <db> <aeskeys.json>
"""
import sys, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DB=sys.argv[1]; data=open(DB,"rb").read()
rows=json.load(open(sys.argv[2]))
keys=[r["key"] for r in rows if r.get("bits")==256] + [r["key"] for r in rows if r.get("bits")==128]
TARGET=b"SQLite format 3\x00"

def dec(key,iv,ct,mode="cbc"):
    try:
        m = modes.CBC(iv) if mode=="cbc" else modes.ECB()
        c=Cipher(algorithms.AES(key),m); d=c.decryptor()
        return d.update(ct)+d.finalize()
    except: return None

def kbytes(kh):
    r=[]
    if len(kh)==64: r.append(bytes.fromhex(kh))
    if len(kh)>=32: r.append(bytes.fromhex(kh[:32]))
    return r

hits=[]
for kh in keys:
    for key in kbytes(kh):
        for ps in (1024,4096,512,2048,8192):
            pg=data[:ps]
            for reserve in (0,16,48,32,24):
                # ---- A: 整库, IV=0 / IV=页尾 ----
                bodyA = pg[:ps-reserve] if reserve else pg
                if len(bodyA)>=16:
                    b=bodyA[:len(bodyA)//16*16]
                    pt=dec(key,bytes(16),b)
                    if pt and pt[:15]==TARGET[:15]: hits.append((kh,len(key),ps,reserve,"A_IV0",pt)); break
                    if reserve>=16:
                        iv=pg[ps-reserve:ps-reserve+16]
                        pt=dec(key,iv,pg[:ps-reserve])
                        if pt and pt[:15]==TARGET[:15]: hits.append((kh,len(key),ps,reserve,"A_IVend",pt)); break
                # ---- B: SQLCipher salt(跳16B) ----
                if reserve>=16:
                    iv=pg[ps-reserve:ps-reserve+16]; ct=pg[16:ps-reserve]
                    if len(ct)%16==0:
                        pt=dec(key,iv,ct)
                        if pt and len(pt)>=8 and pt[5]==0x40 and pt[6]==0x20 and pt[7]==0x20:
                            hits.append((kh,len(key),ps,reserve,"B_salt",pt)); break
            if hits: break
        if hits: break
    if hits: break

if hits:
    kh,kl,ps,res,sch,pt=hits[0]
    print(f"🎉🎉🎉 DB KEY 确认!")
    print(f"KEY={kh}")
    print(f"keylen={kl*8}bit page={ps} reserve={res} scheme={sch}")
    print(f"解出头32B: {pt[:32].hex()}")
    print(f"ASCII: {bytes(b if 32<=b<127 else 46 for b in pt[:24])}")
    json.dump({"key":kh,"keylen":kl,"page":ps,"reserve":res,"scheme":sch}, open("/tmp/wecom_dbkey.json","w"))
    print("→ 已存 /tmp/wecom_dbkey.json")
else:
    print("[MISS] 仍未命中")
