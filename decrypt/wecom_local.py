#!/usr/bin/env python3
"""企业微信**本地数据**查询 —— 基于已解密的 53 库 + 明文缓存, 全本地、无需 API/网络/模型。

子命令:
  contacts [关键词]      通讯录(姓名/部门/职位/手机/邮箱), 可按词过滤
  conversations          会话列表(名称/消息数/最后时间)
  members <会话名或ID>   某会话的参与者
  search <关键词>        全文搜索消息(时间/会话/发送者/正文)
  stats                  统计(总量/发言排行/会话排行/类型/按小时/按天)
  todo                   待办(内容/状态/创建者/提醒)
  calendar               日程
  media [--out 目录]     导出明文缓存的图片+文件(按原名)
前提: 先跑 read_wecom.py 解密。用法: wecom_local.py <子命令> [参数]
"""
import glob
import os
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_wxwork as ex

HERE = os.path.dirname(os.path.abspath(__file__))
from wecom_paths import caches, decrypted
DEC = decrypted()
INFO = decrypted("Messages1", "Info.db")
SESS = decrypted("Messages1", "Session.db")
CACHES = caches()


def _conn(path):
    if not os.path.exists(path):
        sys.exit(f"缺 {path}, 先跑 read_wecom.py 解密")
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def cmd_contacts(args):
    kw = args[0] if args else ""
    c = _conn(SESS)
    n = 0
    for r in c.execute("SELECT name, fullpath, job, mobile, email, alias FROM USER ORDER BY name"):
        blob = " ".join(str(r[k] or "") for k in ("name", "fullpath", "job", "mobile", "email", "alias"))
        if kw and kw not in blob:
            continue
        fields = [str(r["name"] or ""), str(r["job"] or ""), str(r["mobile"] or ""),
                  str(r["email"] or ""), str(r["fullpath"] or "")]
        print("  " + " | ".join(x for x in fields if x))
        n += 1
    c.close()
    print(f"\n{n} 人" + (f' (含"{kw}")' if kw else ""))


def cmd_conversations(args):
    info = _conn(INFO)
    convn = ex._load_conv_names(info)
    counts, last = Counter(), defaultdict(int)
    for cid, st in info.execute("SELECT conv_id, send_time FROM MESSAGE"):
        counts[cid] += 1
        last[cid] = max(last[cid], st or 0)
    info.close()
    for cid, n in sorted(counts.items(), key=lambda x: last[x[0]], reverse=True):
        print(f"  {ex.fmt_time(last[cid])}  {n:>5}条  {convn.get(cid, cid)}")
    print(f"\n{len(counts)} 个会话")


def cmd_members(args):
    if not args:
        sys.exit("用法: members <会话名或ID>")
    q = args[0]
    info = _conn(INFO)
    convn = ex._load_conv_names(info)
    users = ex._load_user_names(INFO)
    targets = {cid for cid, nm in convn.items() if q == str(cid) or q in str(nm)}
    if not targets:
        sys.exit(f"没找到会话 '{q}'")
    seen = Counter()
    for cid in targets:
        for (sid,) in info.execute("SELECT sender_id FROM MESSAGE WHERE conv_id=?", (cid,)):
            seen[ex.resolve_sender(sid, users)] += 1
    info.close()
    print(f"会话 '{q}' 参与者(按发言数):")
    for name, n in seen.most_common():
        print(f"  {n:>4}  {name}")


def cmd_search(args):
    if not args:
        sys.exit("用法: search <关键词>")
    kw = args[0]
    info = _conn(INFO)
    users = ex._load_user_names(INFO)
    convn = ex._load_conv_names(info)
    kwb = kw.encode("utf-8")
    hits = 0
    for r in info.execute("SELECT conv_id, sender_id, content_type, send_time, content "
                          "FROM MESSAGE ORDER BY send_time"):
        raw = r["content"]
        sender = ex.resolve_sender(r["sender_id"], users)
        conv = convn.get(r["conv_id"], r["conv_id"])
        # 预过滤: 命中发送者/会话/类型名, 或 kw 字节在原始 content 里; 否则跳过昂贵的 render
        if not (kw in str(conv) or kw in str(sender) or kw in ex.type_name(r["content_type"])
                or (isinstance(raw, (bytes, bytearray)) and kwb in bytes(raw))
                or (isinstance(raw, str) and kw in raw)):
            continue
        content = ex.render(r["content_type"], raw)
        if kw in str(content) or kw in str(sender) or kw in str(conv):
            print(f"  [{ex.fmt_time(r['send_time'])}] {str(conv)[:14]} | {str(sender)[:8]} : {str(content)[:60]}")
            hits += 1
    info.close()
    print(f"\n命中 {hits} 条")


def cmd_stats(args):
    info = _conn(INFO)
    users = ex._load_user_names(INFO)
    convn = ex._load_conv_names(info)
    by_s, by_c, by_t, by_h, by_d = Counter(), Counter(), Counter(), Counter(), Counter()
    total = 0
    for r in info.execute("SELECT conv_id, sender_id, content_type, send_time FROM MESSAGE"):
        total += 1
        by_s[ex.resolve_sender(r["sender_id"], users)] += 1
        by_c[convn.get(r["conv_id"], r["conv_id"])] += 1
        by_t[ex.type_name(r["content_type"])] += 1
        if r["send_time"]:
            dt = datetime.fromtimestamp(r["send_time"])
            by_h[dt.hour] += 1
            by_d[dt.strftime("%Y-%m-%d")] += 1
    info.close()
    print(f"总消息 {total} 条")
    print("\n发言最多:")
    for s, n in by_s.most_common(10):
        print(f"  {n:>5}  {s}")
    print("\n最活跃会话:")
    for c, n in by_c.most_common(10):
        print(f"  {n:>5}  {c}")
    print("\n类型分布:")
    for t, n in by_t.most_common(12):
        print(f"  {n:>5}  {t}")
    print("\n按小时:")
    mx = max(by_h.values()) if by_h else 1
    for h in range(24):
        bar = "█" * int(by_h.get(h, 0) / mx * 30)
        print(f"  {h:02d}时 {by_h.get(h,0):>4} {bar}")
    print("\n最近 7 活跃天:")
    for d, n in sorted(by_d.items())[-7:]:
        print(f"  {d}  {n}")


def cmd_todo(args):
    p = os.path.join(DEC, "Todo", "Todo.db")
    users = ex._load_user_names(INFO)
    c = _conn(p)
    n = 0
    for r in c.execute("SELECT content, completed, creator, remindtime FROM TODOTABLE3 WHERE deleted=0 "
                       "ORDER BY remindtime DESC"):
        st = "✓完成" if r["completed"] else "○待办"
        who = users.get(r["creator"], str(r["creator"]))
        rt = ex.fmt_time(r["remindtime"]) if r["remindtime"] else ""
        print(f"  {st}  {str(r['content'] or '')[:54]:<54} {who} {rt}")
        n += 1
    c.close()
    print(f"\n{n} 条待办")


def cmd_calendar(args):
    p = os.path.join(DEC, "Calendar", "Calendar_tmp19.db")
    c = _conn(p)
    n = 0
    for r in c.execute("SELECT starttime, endtime, blob FROM calevent2 ORDER BY starttime DESC"):
        title = ex.decode_text(r["blob"]) if r["blob"] else ""
        title = title.split("\n")[0][:50] if title else "(无标题)"
        print(f"  {ex.fmt_time(r['starttime'])} ~ {ex.fmt_time(r['endtime'])[11:]}  {title}")
        n += 1
    c.close()
    print(f"\n{n} 个日程")


def cmd_media(args):
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "export", "media")
    total = 0
    for sub in ("Images", "Files"):
        src = os.path.join(CACHES, sub)
        if not os.path.isdir(src):
            continue
        dst_dir = os.path.join(out, sub)
        os.makedirs(dst_dir, exist_ok=True)
        for f in glob.glob(os.path.join(src, "**", "*"), recursive=True):
            if not os.path.isfile(f) or os.path.basename(f) == ".DS_Store":
                continue
            try:
                shutil.copy2(f, os.path.join(dst_dir, os.path.basename(f)))
                total += 1
            except OSError:
                pass
        print(f"  {sub}: 导出到 {dst_dir}")
    print(f"\n共导出 {total} 个媒体文件 → {out}")


CMDS = {"contacts": cmd_contacts, "conversations": cmd_conversations, "members": cmd_members,
        "search": cmd_search, "stats": cmd_stats, "todo": cmd_todo, "calendar": cmd_calendar,
        "media": cmd_media}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        print("子命令:", ", ".join(CMDS))
        sys.exit(1)
    CMDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
