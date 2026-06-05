#!/usr/bin/env python3
"""企业微信本地消息**增量监控** —— 用已存的 key 重解密 Info.db, 取上次以来的新消息。

特点: 无需重扫内存(key 已存 wxwork_keys.json), 无需重签; 纯读磁盘 DB + 已知 key。
(企微在跑才会写入新消息; WAL 下最新几条可能未合并进主库, 有秒级延迟。)
解析复用 export_wxwork(发送者真名/类型/卡片/文件/文档)。
用法: monitor.py [--once] [--poll 30] [--all]
  --once  跑一次即退出   --poll N 轮询秒数(默认30)   --all 忽略水位,输出全部
"""
import json
import os
import sqlite3
import sys
import time

_H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_H, os.path.dirname(_H)]
from wxwork_crypto import PAGE_SZ, decrypt_database, load_valid_keys
import export_wxwork as ex

HERE = os.path.dirname(os.path.abspath(__file__))
from wecom_paths import decrypted, info_db, session_db
SRC_INFO = info_db()
SRC_SESS = session_db()
DEC = decrypted("Messages1")
KEYS = os.path.join(HERE, "wxwork_keys.json")
STATE = os.path.join(HERE, "export", "monitor_state.json")
OUTLOG = os.path.join(HERE, "export", "monitor.jsonl")


def load_messages_key():
    if not os.path.exists(KEYS):
        sys.exit(f"缺 {KEYS}, 先跑 find_key_fast.py")
    with open(SRC_INFO, "rb") as f:
        pg1 = f.read(PAGE_SZ)
    keys = load_valid_keys(KEYS, pg1)
    if not keys:
        sys.exit("wxwork_keys.json 里没有能解 Info.db 的 key, 重跑 find_key_fast.py")
    return keys[0]


def decrypt_fresh(key):
    """把当前磁盘上的 Info.db / Session.db 用 key 重新解密到 decrypted/。"""
    os.makedirs(DEC, exist_ok=True)
    info_out = os.path.join(DEC, "Info.db")
    decrypt_database(SRC_INFO, info_out, key)
    if os.path.exists(SRC_SESS):
        try:
            decrypt_database(SRC_SESS, os.path.join(DEC, "Session.db"), key)
        except Exception:
            pass
    return info_out


def fetch_new(info_db, watermark):
    users = ex._load_user_names(info_db)
    conn = sqlite3.connect(info_db)
    conn.row_factory = sqlite3.Row
    conv = ex._load_conv_names(conn)
    out = []
    hi = watermark
    for r in conn.execute(
        "SELECT LID, conv_id, sender_id, content_type, send_time, content "
        "FROM MESSAGE WHERE send_time > ? ORDER BY send_time, LID", (watermark,)
    ):
        st = r["send_time"] or 0
        hi = max(hi, st)
        cv = r["conv_id"]
        out.append({
            "lid": r["LID"], "send_time": st,
            "time": ex.fmt_time(st),
            "conversation": conv.get(cv, cv),
            "sender": ex.resolve_sender(r["sender_id"], users),
            "type": ex.type_name(r["content_type"]),
            "content": ex.render(r["content_type"], r["content"]),
        })
    conn.close()
    return out, hi


def main():
    once = "--once" in sys.argv
    allmsg = "--all" in sys.argv
    poll = float(sys.argv[sys.argv.index("--poll") + 1]) if "--poll" in sys.argv else 30.0

    key = load_messages_key()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    watermark = 0 if allmsg else int(state.get("watermark", 0))
    os.makedirs(os.path.dirname(OUTLOG), exist_ok=True)
    print(f"监控启动: 水位 send_time>{watermark}; {'单次' if once else f'每{poll:.0f}s'}")

    last_mtime = 0

    def tick():
        nonlocal watermark, last_mtime
        mt = os.path.getmtime(SRC_INFO) if os.path.exists(SRC_INFO) else 0
        if mt == last_mtime and last_mtime:
            return 0                       # 源库未变 → 必无新消息, 跳过重解密
        last_mtime = mt
        info_path = decrypt_fresh(key)
        new, hi = fetch_new(info_path, watermark)
        if new:
            with open(OUTLOG, "a", encoding="utf-8") as f:
                for m in new:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
            for m in new:
                print(f"  [{m['time']}] {str(m['conversation'])[:14]} | {str(m['sender'])[:8]} "
                      f"[{m['type']}] {str(m['content'])[:48]}")
            watermark = hi
            json.dump({"watermark": watermark}, open(STATE, "w"))
            try:
                os.chmod(STATE, 0o600)
            except OSError:
                pass
        return len(new)

    if once:
        print(f"新消息 {tick()} 条 → {OUTLOG}")
        return
    while True:
        n = tick()
        if n:
            print(f"[{ex.fmt_time(int(time.time()))}] +{n} 条")
        time.sleep(poll)


if __name__ == "__main__":
    main()
