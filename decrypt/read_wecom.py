#!/usr/bin/env python3
"""一键读取企业微信聊天记录(macOS) —— 智能跳过已完成步骤。

  ① 若 wxwork_keys.json 的 key 仍能解 Info.db → 跳过内存扫描;
     否则跑 find_key_fast.py(需企微运行并登录、已 adhoc 重签)。
  ② decrypt_wxwork.py 全库解密 → ③ export_wxwork.py 结构化导出。
日常增量请用 monitor.py。
用法: read_wecom.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wxwork_crypto import PAGE_SZ, load_valid_keys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
from wecom_paths import info_db
INFO = info_db()
KEYS = os.path.join(HERE, "wxwork_keys.json")


def key_valid():
    if not (os.path.exists(KEYS) and os.path.exists(INFO)):
        return False
    with open(INFO, "rb") as f:
        pg1 = f.read(PAGE_SZ)
    return bool(load_valid_keys(KEYS, pg1))


def run(script, *args):
    print(f"\n▶ {script} {' '.join(args)}".rstrip())
    if subprocess.run([PY, os.path.join(HERE, script), *args]).returncode != 0:
        sys.exit(f"✗ {script} 失败")


def main():
    if key_valid():
        print("✓ 已有可用 key（跳过内存扫描）")
    else:
        print("✗ 无可用 key → 扫活进程内存（需企微运行并登录、已 adhoc 重签）")
        run("find_key_fast.py")
        if not key_valid():
            sys.exit("扫描后仍无可用 key，检查企微是否登录")
    run("decrypt_wxwork.py")
    run("export_wxwork.py")
    print("\n✅ 完成。导出在 decrypt/export/messages.csv|json；日常增量用 monitor.py")


if __name__ == "__main__":
    main()
