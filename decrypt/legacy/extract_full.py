#!/usr/bin/env python3
"""从carve.bin提取完整消息记录: 解析所有table-leaf页, 输出含中文/可读文本的记录(发送者+时间+正文)。"""
import struct, sys, re, json

d = open("/tmp/carve.bin", "rb").read()
pages = []
i = 0
while i + 8 + 4096 <= len(d):
    i += 8; pages.append(d[i:i+4096]); i += 4096

def varint(b, o):
    v = 0
    for k in range(9):
        c = b[o+k]
        if k == 8: return (v << 8) | c, o+9
        v = (v << 7) | (c & 0x7f)
        if not (c & 0x80): return v, o+k+1
    return v, o+9

def sval(b, o, t):
    if t == 0: return None, o
    if 1 <= t <= 6:
        sz = {1:1,2:2,3:3,4:4,5:6,6:8}[t]
        return int.from_bytes(b[o:o+sz], "big", signed=True), o+sz
    if t == 7: return struct.unpack(">d", b[o:o+8])[0], o+8
    if t == 8: return 0, o
    if t == 9: return 1, o
    n = (t-12)//2 if t % 2 == 0 else (t-13)//2
    raw = b[o:o+n]
    if t % 2 == 1:
        try: return raw.decode("utf-8"), o+n
        except: return "<bin%d>" % n, o+n
    return "<blob%d>" % n, o+n

cn = re.compile('[一-鿿]')
recs = []
for pg in pages:
    if pg[0] != 0x0d: continue
    nc = (pg[3] << 8) | pg[4]
    if not (0 < nc <= 400): continue
    for c in range(nc):
        po = 8 + c*2
        if po+2 > 4096: break
        cp = (pg[po] << 8) | pg[po+1]
        if not (8 <= cp < 4096): continue
        try:
            o = cp
            paylen, o = varint(pg, o)
            rowid, o = varint(pg, o)
            if not (2 <= paylen <= 4000): continue
            hl, o2 = varint(pg, o)
            types = []; p = o2; hend = o + hl
            while p < hend and p < 4096:
                t, p = varint(pg, p); types.append(t)
            vals = []; vp = hend
            for t in types:
                if vp > 4096: break
                v, vp = sval(pg, vp, t); vals.append(v)
            txt = " | ".join(str(v) for v in vals if isinstance(v, (str, int)))
            if cn.search(txt):
                recs.append((rowid, vals, txt))
        except Exception:
            continue

# 去重 + 输出
seen = set(); out = []
for rid, vals, txt in recs:
    if txt in seen: continue
    seen.add(txt); out.append((rid, vals, txt))

with open("/tmp/wecom_FULL.txt", "w") as f:
    f.write(f"共 {len(out)} 条含中文记录(去重)\n\n")
    for rid, vals, txt in out:
        f.write(f"{txt}\n")
print(f"提取 {len(out)} 条含中文记录 → /tmp/wecom_FULL.txt")
print("\n=== 预览(消息正文样本) ===")
for rid, vals, txt in out[:30]:
    print(" ", txt[:110])
