#!/usr/bin/env python3
"""用 wxwork_keys.json 的 16B raw key 解密企业微信(macOS)各加密库 → decrypt/decrypted/。
自动按页1匹配可用 key(不同库可能不同 key); 明文库直接拷贝; 末尾打印消息库 schema。
用法: decrypt_wxwork.py [--profile DIR] [--out DIR]
"""
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wxwork_crypto import PAGE_SZ, SQLITE_HDR, decrypt_database, load_valid_keys, table_names, verify_key

HERE = os.path.dirname(os.path.abspath(__file__))
from wecom_paths import profile_dir
PROFILE = profile_dir()
OUTDIR = os.path.join(HERE, "decrypted")
KEYS = os.path.join(HERE, "wxwork_keys.json")


def load_keys():
    if not os.path.exists(KEYS):
        sys.exit(f"缺 {KEYS}, 先跑 find_key_fast.py")
    keys = load_valid_keys(KEYS)
    if not keys:
        sys.exit("wxwork_keys.json 无有效 16B key")
    return keys


def main():
    prof, out = PROFILE, OUTDIR
    if "--profile" in sys.argv:
        prof = sys.argv[sys.argv.index("--profile") + 1]
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    keys = load_keys()
    print(f"{len(keys)} 个候选 key; profile={prof}")

    ok = copied = fail = 0
    msgdb = None
    for root, _, files in os.walk(prof):
        for name in sorted(files):
            if not name.endswith(".db") or name.endswith(("-wal", "-shm", "-journal")):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, prof)
            if os.path.getsize(path) < PAGE_SZ:
                continue
            with open(path, "rb") as f:
                pg1 = f.read(PAGE_SZ)
            outp = os.path.join(out, rel)
            if pg1[:16] == SQLITE_HDR:
                os.makedirs(os.path.dirname(outp), exist_ok=True)
                shutil.copy2(path, outp)
                copied += 1
                continue
            key = next((k for k in keys if verify_key(k, pg1)), None)
            if not key:
                print(f"SKIP {rel} (无匹配 key)")
                fail += 1
                continue
            try:
                decrypt_database(path, outp, key)
                tbls = table_names(outp)
                ok += 1
                print(f"OK   {rel}  表{len(tbls)}: {', '.join(tbls[:6])}")
                if rel.replace(os.sep, "/").endswith("Messages1/Info.db"):
                    msgdb = outp
            except Exception as e:
                print(f"FAIL {rel} ({e})")
                fail += 1

    print(f"\n解密 {ok}, 拷贝 {copied}, 跳过/失败 {fail} → {out}")
    if msgdb:
        print(f"\n=== 消息库 schema: {os.path.relpath(msgdb, HERE)} ===")
        conn = sqlite3.connect(msgdb)
        for (sql,) in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql NOT NULL ORDER BY name"
        ):
            print((sql or "")[:400])
        conn.close()


if __name__ == "__main__":
    main()
