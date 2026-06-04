#!/usr/bin/env python3
"""解析carve.bin里的SQLite table-leaf页(0x0d), 提取消息记录。
每页: b-tree leaf, cell指针数组 → 每cell: varint(payloadlen)+varint(rowid)+record。
record: header(serial types) + values。输出可读记录。
"""
import struct, sys, json

CARVE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/carve.bin"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/wecom_messages_structured.txt"

d = open(CARVE, "rb").read()
pages = []
i = 0
while i + 8 + 4096 <= len(d):
    i += 8
    pages.append(d[i:i+4096]); i += 4096

def varint(b, o):
    v = 0
    for k in range(9):
        c = b[o+k]
        if k == 8:
            v = (v << 8) | c; return v, o+9
        v = (v << 7) | (c & 0x7f)
        if not (c & 0x80):
            return v, o+k+1
    return v, o+9

def serial_len(t):
    if t == 0: return 0
    if t <= 4: return t
    if t == 5: return 6
    if t == 6 or t == 7: return 8
    if t == 8 or t == 9: return 0
    if t >= 12:
        return (t-12)//2 if t % 2 == 0 else (t-13)//2
    return 0

def read_val(b, o, t):
    n = serial_len(t)
    if t == 0: return None, o
    if 1 <= t <= 6:
        sz = serial_len(t); v = int.from_bytes(b[o:o+sz], "big", signed=True); return v, o+sz
    if t == 7:
        return struct.unpack(">d", b[o:o+8])[0], o+8
    if t == 8: return 0, o
    if t == 9: return 1, o
    if t >= 12:
        raw = b[o:o+n]
        if t % 2 == 1:  # text
            try: return raw.decode("utf-8"), o+n
            except: return raw, o+n
        return raw, o+n  # blob
    return None, o+n

records = []
for pg in pages:
    if pg[0] != 0x0d:  # table leaf only
        continue
    ncell = (pg[3] << 8) | pg[4]
    if ncell == 0 or ncell > 400:
        continue
    cellptrs = []
    for c in range(ncell):
        off = 8 + c*2
        if off+2 > len(pg): break
        cellptrs.append((pg[off] << 8) | pg[off+1])
    for cp in cellptrs:
        if cp < 8 or cp >= 4096:
            continue
        try:
            o = cp
            paylen, o = varint(pg, o)
            rowid, o = varint(pg, o)
            if paylen < 2 or paylen > 4000:
                continue
            hdrlen, o2 = varint(pg, o)
            types = []
            p = o2
            hend = o + hdrlen
            while p < hend and p < len(pg):
                t, p = varint(pg, p)
                types.append(t)
            vals = []
            vp = hend
            for t in types:
                if vp > len(pg): break
                v, vp = read_val(pg, vp, t)
                vals.append(v)
            # 仅保留含可读文本的记录
            texts = [v for v in vals if isinstance(v, str) and len(v) >= 1]
            if texts:
                records.append({"rowid": rowid, "vals": vals})
        except Exception:
            continue

# 输出
with open(OUT, "w") as f:
    f.write(f"解析出 {len(records)} 条记录\n\n")
    for r in records:
        readable = [str(v) for v in r["vals"] if isinstance(v, (str, int)) and (isinstance(v, int) or len(str(v).strip()) > 0)]
        line = " | ".join(str(v)[:60] for v in r["vals"] if isinstance(v, (str, int)))
        if line.strip():
            f.write(f"[{r['rowid']}] {line}\n")

print(f"解析 {len(records)} 条记录 → {OUT}")
# 预览含中文的
import re
cn = re.compile(r'[一-鿿]')
shown = 0
for r in records:
    line = " | ".join(str(v)[:50] for v in r["vals"] if isinstance(v, (str, int)))
    if cn.search(line) and shown < 25:
        print(" ", line[:100])
        shown += 1
