#!/usr/bin/env python3
"""穷举: top裸key × 全page × reserve0-64 × IV方案 × 两类验证。"""
import sys, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

data=open(sys.argv[1],"rb").read()
rows=json.load(open(sys.argv[2]))
# 按频率取 top key (256优先) + 128
rows=sorted(rows,key=lambda r:-r.get("count",0))
keys=[(r["key"],r.get("count",0),r.get("bits",0)) for r in rows[:25]]
TARGET=b"SQLite format 3\x00"

def d(key,iv,ct):
    try:
        c=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor(); return c.update(ct)+c.finalize()
    except: return None

def valid_wholefile(pt): return pt and pt[:15]==TARGET[:15]
def valid_salt(pt): return pt and len(pt)>=8 and pt[5]==0x40 and pt[6]==0x20 and pt[7]==0x20

found=None
for kh,cnt,bits in keys:
    kcands=[]
    if len(kh)==64: kcands.append(bytes.fromhex(kh))
    if len(kh)>=32: kcands.append(bytes.fromhex(kh[:32]))
    for key in kcands:
        for ps in (4096,1024,2048,512,8192):
            pg=data[:ps]
            for reserve in range(0,81):
                end=ps-reserve
                if end<=32: continue
                # IV候选: 页尾reserve开头16 / 全0 / salt后(offset16起16)
                ivs=[bytes(16)]
                if reserve>=16: ivs.append(pg[end:end+16])
                ivs.append(pg[16:32])
                for iv in ivs:
                    if len(iv)!=16: continue
                    # 整库(从0)
                    body=pg[:end]; body=body[:len(body)//16*16]
                    pt=d(key,iv,body)
                    if valid_wholefile(pt): found=(kh,len(key)*8,ps,reserve,"whole",iv.hex(),pt); break
                    # salt(跳16)
                    ct=pg[16:end];
                    if len(ct)%16==0:
                        pt=d(key,iv,ct)
                        if valid_salt(pt): found=(kh,len(key)*8,ps,reserve,"salt",iv.hex(),pt); break
                if found: break
            if found: break
        if found: break
    if found: break

if found:
    kh,kl,ps,res,sch,iv,pt=found
    print("🎉🎉🎉 命中!")
    print("KEY=",kh)
    print(f"keylen={kl} page={ps} reserve={res} scheme={sch} iv={iv}")
    print("解出:",pt[:40].hex())
    print("ASCII:",bytes(b if 32<=b<127 else 46 for b in pt[:32]))
    json.dump({"key":kh,"keylen":kl,"page":ps,"reserve":res,"scheme":sch},open("/tmp/wecom_dbkey.json","w"))
else:
    print("[MISS] top25 key 全方案未命中")
