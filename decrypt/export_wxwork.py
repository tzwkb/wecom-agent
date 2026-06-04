#!/usr/bin/env python3
"""从解密后的企业微信(macOS)消息库做**结构化提取** → CSV/JSON。

输出每条：时间 / 会话(名) / 发送者(真名) / 类型 / 正文。
- 发送者：sender_id → Session.db `USER`(RID→name) 解析真名；系统/应用号标注。
- 类型：content_type(38种) 分类——文本/图片/语音/文件/卡片/系统/会议/文档链接；媒体显示 [图片]/[语音]/[文件]。
- 正文：文本类走 protobuf 递归抽取；会话名来自 CONVERSATION。
- 跳过 FTS 虚拟表(避免 icu tokenizer)。
用法: export_wxwork.py [--db 解密后的Info.db] [--out 目录]
"""
import csv
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wecom_paths import decrypted
DEFAULT_DB = decrypted("Messages1", "Info.db")
OUTDIR = os.path.join(HERE, "export")
_SHADOW = ("_content", "_segdir", "_segments", "_docsize", "_idx", "_data", "_config", "_stat")

# content_type → 类型名（据实测样本归类；未知码回退 type<码>）
TYPE_LABEL = {
    0: "文本", 2: "文本", 6: "文本",
    13: "文档链接", 29: "图片", 4: "图片", 14: "语音", 15: "文件", 16: "文件",
    40: "音视频通话", 1073: "会议",
    38: "系统通知", 501: "系统", 503: "系统", 1011: "协作事件",
    1001: "事件", 1002: "事件", 1006: "事件", 1018: "事件", 1022: "事件", 1051: "事件", 1052: "事件",
    10: "卡片", 20: "卡片", 105: "卡片", 123: "卡片", 145: "卡片", 221: "卡片", 516: "卡片",
    561: "卡片", 565: "卡片", 570: "卡片", 573: "卡片", 579: "卡片", 580: "卡片", 581: "卡片", 582: "卡片",
}
# 二进制媒体：不强抽文本，直接给标签(+ URL 若有)
MEDIA = {14: "[语音]", 15: "[文件]", 16: "[文件]", 29: "[图片]", 4: "[图片]", 40: "[音视频通话]"}
# 卡片/应用消息：内嵌 JSON，解析 标题+链接
CARD_TYPES = {10, 20, 105, 123, 145, 221, 516, 561, 565, 570, 573, 579, 580, 581, 582}


def _cols(conn, table):
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _pick(cols, *keys):
    low = {c.lower(): c for c in cols}
    for k in keys:                       # 精确列名优先(避免 content 命中 content_type)
        if k in low:
            return low[k]
    for k in keys:                       # 再子串匹配
        for lc, orig in low.items():
            if k in lc:
                return orig
    return None


def find_message_tables(conn):
    out = []
    for name, sql in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
        if sql and sql.upper().lstrip().startswith("CREATE VIRTUAL"):
            continue
        if any(name.endswith(s) for s in _SHADOW):
            continue
        cols = _cols(conn, name)
        content_c = _pick(cols, "content", "message", "msg", "text", "body", "digest")
        time_c = _pick(cols, "send_time", "sendtime", "createtime", "timestamp", "msgtime", "time")
        sender_c = _pick(cols, "sender_id", "sender", "from", "talker", "sendid", "userid")
        if not (content_c and time_c and sender_c):   # 三要素, 排除会话/配置表
            continue
        try:
            if conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] == 0:
                continue
        except Exception:
            continue
        out.append((name, cols, content_c, time_c, sender_c))
    return out


def _load_conv_names(conn):
    m = {}
    try:
        cols = _cols(conn, "CONVERSATION")
    except Exception:
        return m
    if not cols:
        return m
    namecol = next((c for c in cols if c.lower() == "name"), None)
    idcols = [c for c in cols if c.upper() in ("RID", "LID", "CONV_ID", "CONVID")]
    if not namecol or not idcols:
        return m
    for r in conn.execute('SELECT * FROM "CONVERSATION"'):
        d = dict(zip(cols, r))
        nm = d.get(namecol)
        if isinstance(nm, bytes):
            try:
                nm = nm.decode("utf-8")
            except UnicodeDecodeError:
                nm = None
        if nm and isinstance(nm, str) and nm.strip():
            for ic in idcols:
                if isinstance(d.get(ic), int) and d[ic]:
                    m.setdefault(d[ic], nm.strip())
    return m


def _load_user_names(info_db):
    """sender_id → 真名，来自同目录 Session.db 的 USER(RID→name)。"""
    p = os.path.join(os.path.dirname(info_db), "Session.db")
    m = {}
    if not os.path.exists(p):
        return m
    try:
        c = sqlite3.connect(p)
        cols = [r[1] for r in c.execute("PRAGMA table_info(USER)")]
        if "RID" in cols and "name" in cols:
            for rid, name in c.execute("SELECT RID, name FROM USER"):
                if name:
                    m[rid] = name if isinstance(name, str) else name.decode("utf-8", "replace")
        c.close()
    except Exception:
        pass
    return m


def resolve_sender(sid, users):
    name = users.get(sid)
    if name:
        return name
    try:
        n = int(sid)
    except (TypeError, ValueError):
        return str(sid)
    if 0 < n < 1_000_000:
        return f"[系统/应用 {n}]"
    return str(n)


# ── protobuf 文本抽取 ────────────────────────────────────────────────
def _rv(d, p):
    v = s = 0
    while p < len(d) and s < 64:
        b = d[p]; p += 1; v |= (b & 0x7F) << s
        if not b & 0x80:
            return v, p
        s += 7
    raise ValueError


def _seg_text(seg):
    if not seg or b"\x00" in seg:
        return None
    try:
        t = seg.decode("utf-8")
    except UnicodeDecodeError:
        return None
    t = "".join(ch if ch.isprintable() or ch in "\n\t" else " " for ch in t).strip()
    if len(t) < 2 or re.fullmatch(r"[0-9a-fA-F]{32,}", t):
        return None
    if sum(c.isprintable() or c in "\n\t" for c in t) / max(len(t), 1) < 0.9:
        return None
    return t


def _pb_strings(d, depth=0):
    if depth > 4 or not d:
        return []
    p = 0; out = []; fields = 0
    try:
        while p < len(d):
            tag, p = _rv(d, p)
            if tag == 0:
                return []
            wire = tag & 7; fields += 1
            if wire == 0:
                _, p = _rv(d, p)
            elif wire == 1:
                p += 8
            elif wire == 5:
                p += 4
            elif wire == 2:
                ln, p = _rv(d, p)
                if ln < 0 or p + ln > len(d):
                    return []
                seg = d[p:p + ln]; p += ln
                rec = _pb_strings(seg, depth + 1)   # 优先钻到最内层文本(去框架字节)
                if rec:
                    out.extend(rec)
                else:
                    t = _seg_text(seg)
                    if t:
                        out.append(t)
            else:
                return []
    except Exception:
        return []
    return out if fields else []


def decode_text(raw):
    """抽取可读文本；纯二进制返回 ''。"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    d = bytes(raw)
    if not d:
        return ""
    ctrl = sum(b < 32 and b not in (9, 10, 13) for b in d)
    if ctrl == 0:
        try:
            return d.decode("utf-8").strip()
        except UnicodeDecodeError:
            pass
    ss = _pb_strings(d)
    if ss:
        seen = set(); u = []
        for s in ss:
            s = s.strip()
            if s and s not in seen:
                seen.add(s); u.append(s)
        if u:
            return "\n".join(u[:12])
    try:
        if ctrl / max(len(d), 1) < 0.15:
            return d.decode("utf-8").strip()
    except UnicodeDecodeError:
        pass
    return ""


_URL = re.compile(rb"https?://[\w./%?=&#:+~@!$',;*-]+")


def _first_url(raw, skip_assets=True):
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    for m in _URL.finditer(bytes(raw)):
        u = m.group().decode("utf-8", "replace")
        if skip_assets and ("wwcdn." in u or "/images/" in u or u.endswith((".png", ".bin", ".jpg"))):
            continue
        return u
    return ""


def _filename(raw):
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    best = ""
    for m in re.findall(rb"(?:[\x20-\x7e]|[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){4,}", bytes(raw)):
        s = m.decode("utf-8", "replace").strip()
        s = re.sub(r"^[^\w一-鿿]+", "", s)         # 去 protobuf 框架前缀字符
        if not s or s.startswith(("http", "www", "30")):
            continue
        if re.fullmatch(r"[0-9a-fA-F]{12,}", s.replace(" ", "")):
            continue
        score = (100 if "." in s else 0) + len(s)
        if score > (100 if "." in best else 0) + len(best):
            best = s
    return best[:80]


def _extract_json(b):
    """从 blob 里抠出第一个平衡的 JSON 对象（卡片正文内嵌）。"""
    i = b.find(b"{")
    while i != -1:
        depth = 0; instr = False; esc = False
        for j in range(i, min(len(b), i + 30000)):
            c = b[j]
            if esc:
                esc = False; continue
            if instr:
                if c == 0x5C: esc = True
                elif c == 0x22: instr = False
                continue
            if c == 0x22: instr = True
            elif c == 0x7B: depth += 1
            elif c == 0x7D:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(b[i:j + 1].decode("utf-8", "replace"))
                    except Exception:
                        break
        i = b.find(b"{", i + 1)
    return None


def _card_title(j):
    if not isinstance(j, dict):
        return ""
    for k in ("card_title", "main_title", "title"):
        v = j.get(k)
        if isinstance(v, dict) and v.get("title"):
            return str(v["title"])
        if isinstance(v, str) and v:
            return v
    return ""


def render(content_type, raw):
    """按类型呈现正文：媒体→标签(+URL)；卡片→标题+链接；文本/系统→抽取文本。"""
    try:
        ct = int(content_type or 0)
    except (TypeError, ValueError):
        ct = 0
    txt = decode_text(raw)
    if ct in (15, 16):                         # 文件: 提文件名
        fn = _filename(raw)
        return f"[文件] {fn}".strip() if fn else "[文件]"
    if ct == 13:                               # 文档链接: 标题+链接
        url = _first_url(raw)
        title = txt.split("http")[0].strip().split("\n")[0][:60] if txt else ""
        return ("[文档] " + " ".join(p for p in (title, url) if p)).strip()
    if ct in MEDIA:
        url = _first_url(raw, skip_assets=False)
        return (MEDIA[ct] + (" " + url if url else "")).strip()
    if ct in CARD_TYPES:
        j = _extract_json(bytes(raw)) if isinstance(raw, (bytes, bytearray)) else None
        title = _card_title(j)
        if not title and txt:
            title = txt.split("{")[0].strip().split("\n")[0][:120]
        url = _first_url(raw)
        s = "[卡片] " + title if title else "[卡片]"
        return (s + (" " + url if url else "")).strip()
    if txt:
        return txt
    return f"[{TYPE_LABEL.get(ct, '类型' + str(ct))}]"


def type_name(content_type):
    try:
        ct = int(content_type or 0)
    except (TypeError, ValueError):
        return str(content_type)
    return TYPE_LABEL.get(ct, f"type{ct}")


def fmt_time(ts):
    try:
        ts = int(ts or 0)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    if ts > 20_000_000_000:
        ts /= 1000
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(ts)


def main():
    db, out = DEFAULT_DB, OUTDIR
    if "--db" in sys.argv:
        db = sys.argv[sys.argv.index("--db") + 1]
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if not os.path.exists(db):
        sys.exit(f"消息库不存在: {db} (先跑 decrypt_wxwork.py)")

    users = _load_user_names(db)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conv_names = _load_conv_names(conn)
    tables = find_message_tables(conn)
    if not tables:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        sys.exit(f"未识别到消息表(含 content+time+sender)。库内表: {names}")
    print(f"USER 姓名表 {len(users)} 人; 会话名 {len(conv_names)} 个")

    os.makedirs(out, exist_ok=True)
    rows = []
    for t, cols, content_c, time_c, sender_c in tables:
        conv_c = _pick(cols, "conv_id", "conversation", "conv", "chat", "room", "session", "talker")
        type_c = _pick(cols, "content_type", "msgtype", "type")
        sel = list(dict.fromkeys(c for c in (conv_c, sender_c, time_c, type_c, content_c) if c))
        q = 'SELECT ' + ",".join(f'"{c}"' for c in sel) + f' FROM "{t}"'
        n0 = len(rows)
        for r in conn.execute(q):
            cv = r[conv_c] if conv_c else ""
            sid = r[sender_c] if sender_c else ""
            ct = r[type_c] if type_c else 0
            rows.append({
                "table": t,
                "time": fmt_time(r[time_c] if time_c else 0),
                "conv_id": cv,
                "conversation": conv_names.get(cv, cv),
                "sender_id": sid,
                "sender": resolve_sender(sid, users),
                "type_code": ct,
                "type": type_name(ct),
                "content": render(ct, r[content_c]),
            })
        print(f"{t}: {len(rows)-n0} 行  (conv={conv_c}, sender={sender_c}, time={time_c}, "
              f"type={type_c}, content={content_c})")
    conn.close()

    rows.sort(key=lambda x: x["time"])
    cpath = os.path.join(out, "messages.csv")
    with open(cpath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["时间", "会话", "会话ID", "发送者", "发送者ID", "类型", "type码", "正文", "来源表"])
        for x in rows:
            w.writerow([x["time"], x["conversation"], x["conv_id"], x["sender"], x["sender_id"],
                        x["type"], x["type_code"], x["content"], x["table"]])
    json.dump(rows, open(os.path.join(out, "messages.json"), "w"), ensure_ascii=False, indent=2)

    name_set = set(users.values())
    named = sum(1 for x in rows if x["sender"] in name_set)
    readable = sum(1 for x in rows if x["content"] and not x["content"].startswith("["))
    print(f"\n✅ 结构化提取 {len(rows)} 条 → {cpath} + messages.json")
    print(f"   发送者解析出真名 {named} 条; 正文为可读文本 {readable} 条")
    print("最近样本:")
    for x in rows[-18:]:
        print(f"  [{x['time']}] {str(x['conversation'])[:14]} | {str(x['sender'])[:8]} "
              f"[{x['type']}] {str(x['content'])[:42]}")


if __name__ == "__main__":
    main()
