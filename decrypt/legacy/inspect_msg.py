#!/usr/bin/env python3
"""探查解密后的企业微信消息库真实结构, 为结构化导出定位消息表/正文列/分库。只读。"""
import os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEC = os.path.join(HERE, "decrypted")
INFO = os.path.join(DEC, "Messages1", "Info.db")


def nonvirtual_tables(conn):
    out = []
    for name, sql in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
        if sql and sql.upper().startswith("CREATE VIRTUAL"):
            continue
        if any(name.endswith(s) for s in ("_content", "_segdir", "_segments", "_docsize",
                                           "_idx", "_data", "_config", "_stat")):
            continue
        out.append(name)
    return out


def dump(path, focus):
    print(f"\n########## {os.path.relpath(path, HERE)} ##########")
    conn = sqlite3.connect(path)
    for t in nonvirtual_tables(conn):
        try:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except Exception as e:
            print(f"  [{t}] count失败 {e}"); continue
        cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
        mark = "  <<<" if (t in focus or cnt > 50) else ""
        print(f"  {t}({cnt}行): {','.join(cols)}{mark}")
    for t in focus:
        try:
            sql = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()
            if not sql:
                continue
            print(f"\n=== FULL {t} ===\n{sql[0].decode() if isinstance(sql[0],bytes) else sql[0]}")
            rows = conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 3').fetchall()
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
            for r in rows:
                d = {}
                for c, v in zip(cols, r):
                    if isinstance(v, bytes):
                        try:
                            s = v.decode("utf-8")
                            d[c] = s if s.isprintable() or "\n" in s else f"<blob {len(v)}B>"
                        except Exception:
                            d[c] = f"<blob {len(v)}B>"
                    else:
                        d[c] = v
                print(f"  ROW: {d}")
        except Exception as e:
            print(f"  {t} sample失败: {e}")
    conn.close()


if not os.path.exists(INFO):
    sys.exit(f"{INFO} 不存在")
dump(INFO, focus=["MESSAGE", "CONV_ATTACH_MSG_CACHE1", "stashed_msg_ops", "SubMessageDB", "CONVERSATION"])

# SubMessageDB → 是否有分会话子库
conn = sqlite3.connect(INFO)
try:
    subs = conn.execute("SELECT * FROM SubMessageDB").fetchall()
    print(f"\n### SubMessageDB {len(subs)} 条(分会话消息库名) ###")
    for r in subs[:20]:
        print("  ", r)
except Exception as e:
    print("SubMessageDB:", e)
conn.close()

# 其他可能含消息的库
print("\n### 其他库里名字像消息/会话的表 ###")
for root, _, files in os.walk(DEC):
    for name in sorted(files):
        if not name.endswith(".db"):
            continue
        p = os.path.join(root, name)
        try:
            c = sqlite3.connect(p)
            ts = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            hit = [t for t in ts if any(k in t.upper() for k in ("MESSAGE", "MSG", "CHATLOG", "RECORD"))]
            if hit and not p.endswith("Messages1/Info.db"):
                print(f"  {os.path.relpath(p,HERE)}: {hit}")
            c.close()
        except Exception:
            pass
