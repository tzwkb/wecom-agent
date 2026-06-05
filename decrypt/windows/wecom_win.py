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
import re
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

# Windows content_type 码 ≠ macOS —— 覆盖 export_wxwork 的渲染映射(文件15/16、文档13 与 Mac 同, 直接复用)
ex.MEDIA = {4: "[图片]", 14: "[图片]", 29: "[图片]", 40: "[音视频通话]", 1018: "[语音通话]"}
ex.CARD_TYPES = {10, 20, 21, 22, 105, 123, 145, 221, 516, 561, 565, 570, 573, 579, 580, 581, 582}
ex.TYPE_LABEL = {
    0: "文本", 2: "文本", 6: "位置", 4: "图片", 14: "图片", 29: "图片", 15: "文件", 16: "文件",
    13: "文档链接", 40: "音视频通话", 1018: "语音通话", 1073: "会议", 1001: "会议",
    580: "会议", 581: "会议", 582: "会议", 1011: "协作", 565: "协作", 570: "协作", 70: "待办",
    38: "系统", 501: "系统", 503: "系统", 1022: "系统", 1002: "系统", 1006: "系统",
    1017: "系统", 1051: "系统", 1052: "系统", 1055: "系统", 1004: "系统", 671: "系统", 132: "系统", 215: "笔记",
    10: "卡片", 20: "卡片", 21: "卡片", 22: "卡片", 105: "卡片", 123: "卡片", 145: "卡片",
    221: "卡片", 516: "卡片", 561: "卡片", 573: "卡片", 579: "卡片",
}


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
    return ex.render(ct, raw)


def _iter_messages(key, users, convs, self_uid):
    info = decrypt_db("message.db", key)
    for r in info.execute("SELECT send_time, conversation_id, sender_id, content_type, content "
                          "FROM message_table ORDER BY send_time"):
        st, conv, sender, ct, content = r
        yield {
            "time": ex.fmt_time(st) if st else "",
            "conversation": res_conv(conv, convs, users, self_uid),
            "sender": res_sender(sender, users),
            "type": ex.type_name(ct),
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


def cmd_members(key, args):
    if not args:
        sys.exit("用法: members <会话名或ID>")
    q = args[0]
    users, convs, self_uid = load_names(key)
    s = decrypt_db("session.db", key)
    targets, seen = set(), {}
    for cid, cname in s.execute("SELECT id, name FROM conversation_table"):
        cid = str(cid)
        nm = cname or res_conv(cid, convs, users, self_uid)
        if q == cid or q in str(nm):
            targets.add(cid)
    if not targets:
        sys.exit(f"没找到会话 '{q}'")
    for cid in targets:
        for uid, nick in s.execute("SELECT user_id, nick_name FROM conversation_user_table WHERE conversation_id=?", (cid,)):
            uid = str(uid)
            seen[uid] = users.get(uid) or nick or uid
    s.close()
    print(f"会话 '{q}' 成员({len(seen)}):")
    for uid, nm in sorted(seen.items(), key=lambda x: x[1]):
        print(f"  {nm}")


def _cache(sub):
    return os.path.join(os.path.dirname(_data_dir()), "Cache", sub)


def cmd_calendar(key, args):
    c = decrypt_db("calendar_r7.db", key)
    if not c:
        sys.exit("无 calendar_r7.db")
    n = 0
    for st, et, raw in c.execute("SELECT starttime, endtime, rawdata FROM calendar_main_table_v2 ORDER BY starttime DESC"):
        strs = ex._pb_strings(bytes(raw)) if raw else []
        cjk = [s for s in strs if re.search(r"[一-鿿]", s)]
        title = cjk[0] if cjk else (strs[0] if strs else "(无标题)")
        print(f"  {ex.fmt_time(st)} ~ {ex.fmt_time(et)[11:]}  {title[:50]}")
        n += 1
    c.close()
    print(f"\n{n} 个日程")


def cmd_media(key, args):
    import shutil
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(OUT, "media")
    total = 0
    for sub in ("File", "Image"):
        root = _cache(sub)
        if not os.path.isdir(root):
            continue
        dst = os.path.join(out, sub)
        os.makedirs(dst, exist_ok=True)
        for f in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if os.path.isfile(f):
                try:
                    shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
                    total += 1
                except OSError:
                    pass
        print(f"  {sub}: → {dst}")
    print(f"\n共导出 {total} 个媒体文件 → {out}（明文缓存，企微存的原名）")


def cmd_openfile(key, args):
    if not args:
        sys.exit("用法: openfile <文件名或关键词>")
    import read_doc
    kw = args[0]
    cache = {}
    for f in glob.glob(os.path.join(_cache("File"), "**", "*"), recursive=True):
        if os.path.isfile(f):
            cache.setdefault(os.path.basename(f), []).append(f)
    meta = {}
    fdb = decrypt_db("file.db", key)
    if fdb:
        users, convs, self_uid = load_names(key)
        for name, sender, conv, rt in fdb.execute("SELECT name, sender_id, conversation_id, receive_time FROM file_table4"):
            if name:
                meta.setdefault(str(name), (res_sender(sender, users), res_conv(conv, convs, users, self_uid),
                                            ex.fmt_time(rt) if rt else ""))
        fdb.close()
    hits = {n: p for n, p in cache.items() if kw.lower() in n.lower()}
    if not hits:
        sys.exit(f"缓存里没含「{kw}」的文件（只覆盖下载/打开过的）")
    print(f"匹配 {len(hits)} 个文档:\n")
    for name, paths in sorted(hits.items()):
        path = max(paths, key=os.path.getsize)
        s, cv, t = meta.get(name, ("?", "?", ""))
        print(f"📄 《{name}》  {s} {t} @ {cv}")
        body = read_doc.read_file(path, limit=1500)
        if body.startswith(read_doc.VISUAL_MARK):
            print(f"   {body}")
        else:
            print(f"   本地: {path}\n   ── 内容 ──")
            for line in body.splitlines():
                print("   " + line)
        print()


def cmd_voice(key, args):
    root = _cache("Voice")
    files = sorted(f for f in glob.glob(os.path.join(root, "**", "*"), recursive=True) if os.path.isfile(f))
    print(f"缓存语音 {len(files)} 条 @ {root}")
    try:
        import pilk
        from faster_whisper import WhisperModel
    except ImportError:
        for f in files[:20]:
            print(f"  {os.path.getsize(f) // 1024}KB  {os.path.basename(f)}")
        print("\n转写: SILK→pilk→faster-whisper。x64 Windows 有 wheel 可直接装；")
        print("  本 ARM VM 无 win_arm64 wheel 且无 C++ 工具链, 转写不可用(定位/导出仍可)。")
        return
    import wave
    model = WhisperModel("base", device="cpu", compute_type="int8")
    res = {}
    for f in files:
        try:
            pcm = f + ".pcm"
            pilk.decode(f, pcm)
            wav = f + ".wav"
            with open(pcm, "rb") as p, wave.open(wav, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
                w.writeframes(p.read())
            seg, _ = model.transcribe(wav, language="zh")
            res[os.path.basename(f)] = "".join(s.text for s in seg).strip()
        except Exception as e:
            res[os.path.basename(f)] = f"[转写失败 {e}]"
    json.dump(res, open(os.path.join(OUT, "voice_transcripts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in res.items():
        print(f"  {k}: {v[:60]}")
    print(f"\n{len(res)} 条 → {OUT}\\voice_transcripts.json")


def cmd_monitor(key, args):
    sf = os.path.join(OUT, "monitor_state.json")
    os.makedirs(OUT, exist_ok=True)
    wm = json.load(open(sf)).get("watermark", 0) if os.path.exists(sf) else 0
    users, convs, self_uid = load_names(key)
    info = decrypt_db("message.db", key)
    new, hi = [], wm
    for st, conv, sender, ct, content in info.execute(
            "SELECT send_time, conversation_id, sender_id, content_type, content "
            "FROM message_table WHERE send_time > ? ORDER BY send_time", (wm,)):
        new.append((st, res_conv(conv, convs, users, self_uid), res_sender(sender, users), _content(ct, content)))
        hi = max(hi, st or 0)
    info.close()
    json.dump({"watermark": hi}, open(sf, "w"))
    if wm == 0:
        print(f"首次建立水位(send_time>{hi}); 共 {len(new)} 条历史. 之后再跑只出新消息。")
    else:
        print(f"新消息 {len(new)} 条:")
        for st, cv, s, c in new[:30]:
            print(f"  [{ex.fmt_time(st)}] 【{str(cv)[:12]}】{str(s)[:8]}: {str(c)[:40]}")


CMDS = {"read": cmd_read, "contacts": cmd_contacts, "conversations": cmd_conversations,
        "members": cmd_members, "search": cmd_search, "stats": cmd_stats, "todo": cmd_todo,
        "calendar": cmd_calendar, "media": cmd_media, "openfile": cmd_openfile,
        "voice": cmd_voice, "monitor": cmd_monitor}


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
