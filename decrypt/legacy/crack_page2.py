#!/usr/bin/env python3
"""用page-2(纯b-tree页)验证key+方案。SQLCipher: page N = enc[0:ps-rsv] + IV[ps-rsv:+16] + HMAC。
解密后首字节∈{2,5,10,13}, cell数/内容起始 合理。"""
import sys, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
data=open(sys.argv[1],"rb").read()
rows=json.load(open(sys.argv[2]))
rows=sorted(rows,key=lambda r:-r.get("count",0))
keys=[r["key"] for r in rows]

def dec(key,iv,ct):
    try:
        c=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor(); return c.update(ct)+c.finalize()
    except: return None

def valid_btree(pt, ps):
    if not pt or len(pt)<8: return False
    if pt[0] not in (0x02,0x05,0x0a,0x0d): return False
    ncell=(pt[3]<<8)|pt[4]
    cstart=(pt[5]<<8)|pt[6]
    if ncell>1000: return False
    if cstart==0: cstart=65536
    if cstart>ps or cstart<8: return False
    return True

found=None
for kh in keys:
    kcands=[bytes.fromhex(kh)] if len(kh)==64 else []
    if len(kh)>=32: kcands.append(bytes.fromhex(kh[:32]))
    for key in kcands:
        for ps in (4096,1024,2048):
            if len(data)<2*ps: continue
            pg2=data[ps:2*ps]
            for rsv in (48,16,64,80,32,0):
                end=ps-rsv
                if end<=16 or end%16: continue
                iv=pg2[end:end+16] if rsv>=16 else bytes(16)
                if len(iv)!=16: continue
                pt=dec(key,iv,pg2[:end])
                if valid_btree(pt,ps):
                    found=(kh,len(key)*8,ps,rsv,pt); break
            if found: break
        if found: break
    if found: break

if found:
    kh,kl,ps,rsv,pt=found
    print("🎉 KEY+方案命中(page2验证)!")
    print("KEY=",kh, f"keylen={kl} page={ps} reserve={rsv}")
    print("page2首字节=0x%02x cells=%d"%(pt[0],(pt[3]<<8)|pt[4]))
    json.dump({"key":kh,"keylen":kl,"page":ps,"reserve":rsv},open("/tmp/wecom_dbkey.json","w"))
    print("→ /tmp/wecom_dbkey.json")
else:
    print("[MISS]")
