#!/usr/bin/env python3
"""企业微信 Windows 版 · 全功能本地读取 —— 复用 Mac 解密核心 + 内容解析原语。

子命令(对齐 macOS wecom_local)：
  read           解密导出全部消息(含真名/会话名) → export/messages.json|csv
  contacts [词]  通讯录(姓名/手机/邮箱), 可按词过滤
  conversations  会话列表(名称/消息数/最后时间)
  search <词>    全文搜索消息
  stats          统计(发言排行/会话排行/类型/按小时/按天)
  todo           待办

用法: python wecom_win.py <key_hex> <子命令> [参数]
key 由 find_key.ps1 扫内存抓到。Windows 专属: CreateFileW 共享读(企微开着也能读)。
"""
import csv
import ctypes
import glob
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from ctypes import wintypes
from datetime import datetime

_H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_H, os.path.dirname(_H)]
from wxwork_crypto import decrypt_database
import export_wxwork as ex

OUT = os.path.join(_H, "export")
DEC = os.path.join(OUT, "dec")


def read_shared(path):
    GENERIC_READ = 0x80000000
    SHARE_ALL = 0x07
    k = ctypes.windll.kernel32
    k.CreateFileW.restype = wintypes.HANDLE
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    h = k.CreateFileW(path, GENERIC_READ, SHARE_ALL, None, 3, 0x80, None)
    if h == wintypes.HANDLE(-1).value:
        raise OSError("CreateFileW failed")
    try:
        sz = os.path.getsize(path)
        buf = (ctypes.c_char * sz)()
        rd = wintypes.DWORD(0)
        k.ReadFile(h, buf, sz, ctypes.byref(rd), None)
        return bytes(buf[:rd.value])
    finally:
        k.CloseHandle(h)


def _data_dir():
    m = sorted(glob.glob(r"C:\Users\*\Documents\WXWork\*\Data\message.db"),
               key=os.path.getsize, reverse=True)
    if not m:
        sys.exit("没找到 message.db (企业微信装了吗/登录了吗?)")
    return os.path.dirname(m[0])


def decrypt_db(name, key):
    src = os.path.join(_data_dir(), name)
    if not os.path.exists(src):
        return None
    os.makedirs(DEC, exist_ok=True)
    tmp = os.path.join(DEC, "_src_" + name)
    with open(tmp, "wb") as f:
        f.write(read_shared(src))
    dec = os.path.join(DEC, name)
    decrypt_database(tmp, dec, key)
    con = sqlite3.connect(dec)
    con.text_factory = lambda b: b.decode("utf-8", "replace") if isinstance(b, bytes) else b
    return con


def load_names(key):
    """返回 (users{uid:名}, convs{cid:名}, self_uid)。"""
    users = {}
    u = decrypt_db("user.db", key)
    if u:
        for r in u.execute("SELECT id, name FROM user_table"):
            if r[1]:
                users[str(r[0])] = r[1]
        try:
            for r in u.execute("SELECT wxid, name FROM wechat_contactV1"):
                if r[1] and r[1] != "-":
                    users.setdefault(str(r[0]), r[1])
        except sqlite3.Error:
            pass
        u.close()
    convs, self_uid = {}, None
    s = decrypt_db("session.db", key)
    if s:
        srows = list(s.execute("SELECT id, name FROM conversation_table"))
        s.close()
        cnt = Counter()
        for cid, cname in srows:
            cid = str(cid)
            if cname:
                convs[cid] = cname
            if cid.startswith("S:"):
                for p in cid[2:].split("_"):
                    cnt[p] += 1
        if cnt:
            self_uid = cnt.most_common(1)[0][0]
    return users, convs, self_uid


def res_sender(sid, users):
    sid = str(sid)
    if sid in users:
        return users[sid]
    if sid.isdigit() and len(sid) < 12:
        return f"[系统/应用 {sid}]"
    return sid


def res_conv(cid, convs, users, self_uid):
    cid = str(cid)
    if cid in convs:
        return convs[cid]
    if cid.startswith("S:"):
        other = [p for p in cid[2:].split("_") if p != self_uid] or cid[2:].split("_")
        return users.get(other[0], cid)
    return cid


def _content(ct, raw):
    txt = ex.decode_text(raw) if raw else ""
    return txt if txt else f"[类型{ct}]"


def _iter_messages(key, users, convs, self_uid):
    info = decrypt_db("message.db", key)
    for r in info.execute("SELECT send_time, conversation_id, sender_id, content_type, content "
                          "FROM message_table ORDER BY send_time"):
        st, conv, sender, ct, content = r
        yield {
            "time": ex.fmt_time(st) if st else "",
            "conversation": res_conv(conv, convs, users, self_uid),
            "sender": res_sender(sender, users),
            "type": ct,
            "content": _content(ct, content),
        }
    info.close()


def cmd_read(key, args):
    users, convs, self_uid = load_names(key)
    rows = list(_iter_messages(key, users, convs, self_uid))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "messages.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "messages.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "conversation", "sender", "type", "content"])
        w.writeheader()
        w.writerows(rows)
    print(f"✅ {len(rows)} 条 → {OUT}\\messages.json|csv")
    for m in rows[-6:]:
        print(f"  [{m['time']}] 【{str(m['conversation'])[:12]}】{str(m['sender'])[:10]}: {str(m['content'])[:40]}")


def cmd_contacts(key, args):
    kw = args[0] if args else ""
    u = decrypt_db("user.db", key)
    n = 0
    for r in u.execute("SELECT name, english_name, mobile, email, position FROM user_table ORDER BY name"):
        blob = " ".join(str(x or "") for x in r)
        if kw and kw not in blob:
            continue
        fields = [str(r[0] or ""), str(r[1] or ""), str(r[2] or ""), str(r[3] or ""), str(r[4] or "")]
        print("  " + " | ".join(x for x in fields if x))
        n += 1
    u.close()
    print(f"\n{n} 人" + (f'(含"{kw}")' if kw else ""))


def cmd_conversations(key, args):
    users, convs, self_uid = load_names(key)
    info = decrypt_db("message.db", key)
    counts, last = Counter(), defaultdict(int)
    for cid, st in info.execute("SELECT conversation_id, send_time FROM message_table"):
        counts[str(cid)] += 1
        last[str(cid)] = max(last[str(cid)], st or 0)
    info.close()
    for cid, c in sorted(counts.items(), key=lambda x: last[x[0]], reverse=True):
        print(f"  {ex.fmt_time(last[cid])}  {c:>5}条  {res_conv(cid, convs, users, self_uid)}")
    print(f"\n{len(counts)} 个会话")


def cmd_search(key, args):
    if not args:
        sys.exit("用法: search <关键词>")
    kw = args[0]
    users, convs, self_uid = load_names(key)
    hits = 0
    for m in _iter_messages(key, users, convs, self_uid):
        if kw in str(m["content"]) or kw in str(m["sender"]) or kw in str(m["conversation"]):
            print(f"  [{m['time']}] {str(m['conversation'])[:12]} | {str(m['sender'])[:8]}: {str(m['content'])[:60]}")
            hits += 1
    print(f"\n命中 {hits} 条")


def cmd_stats(key, args):
    users, convs, self_uid = load_names(key)
    by_s, by_c, by_t, by_h, by_d = Counter(), Counter(), Counter(), Counter(), Counter()
    total = 0
    info = decrypt_db("message.db", key)
    for st, conv, sender, ct in info.execute("SELECT send_time, conversation_id, sender_id, content_type FROM message_table"):
        total += 1
        by_s[res_sender(sender, users)] += 1
        by_c[res_conv(conv, convs, users, self_uid)] += 1
        by_t[ct] += 1
        if st:
            dt = datetime.fromtimestamp(st)
            by_h[dt.hour] += 1
            by_d[dt.strftime("%Y-%m-%d")] += 1
    info.close()
    print(f"总消息 {total} 条")
    print("\n发言最多:")
    for s, c in by_s.most_common(10):
        print(f"  {c:>6}  {s}")
    print("\n最活跃会话:")
    for s, c in by_c.most_common(10):
        print(f"  {c:>6}  {s}")
    print("\n最近 7 活跃天:")
    for d, c in sorted(by_d.items())[-7:]:
        print(f"  {d}  {c}")


def cmd_todo(key, args):
    users, _, _ = load_names(key)
    f = decrypt_db("forever_store.db", key)
    if not f:
        sys.exit("无 forever_store.db")
    n = 0
    try:
        for r in f.execute("SELECT content, status, creator_id, from_info_name, create_time FROM todo_v4 ORDER BY create_time DESC"):
            content, status, creator, fromname, ctime = r
            st = "✓完成" if status == 1 else "○待办"
            who = users.get(str(creator), fromname or str(creator))
            print(f"  {st}  {str(content or '')[:50]:<50} {who} {ex.fmt_time(ctime) if ctime else ''}")
            n += 1
    except sqlite3.Error as e:
        sys.exit(f"读 todo_v4 失败: {e}")
    f.close()
    print(f"\n{n} 条待办")


CMDS = {"read": cmd_read, "contacts": cmd_contacts, "conversations": cmd_conversations,
        "search": cmd_search, "stats": cmd_stats, "todo": cmd_todo}


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in CMDS:
        print(__doc__)
        print("子命令:", ", ".join(CMDS))
        sys.exit(1)
    key = bytes.fromhex(sys.argv[1].strip())
    if len(key) != 16:
        sys.exit("key 必须 16 字节(32 hex)")
    CMDS[sys.argv[2]](key, sys.argv[3:])


if __name__ == "__main__":
    main()
