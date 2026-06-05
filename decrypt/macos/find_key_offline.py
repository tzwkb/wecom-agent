#!/usr/bin/env python3
"""离线找 WeCom 消息库 16 字节 raw key —— 不碰活进程, 纯离线。

候选来源(均为上次会话已落盘的数据):
  1. /tmp/allkeys.txt   : 961+ 个 32B 候选 key(OpenSSL hook 抓的, 多为消息GCM/缓存key);
                          对每个取 [:16] / [16:] / md5 当 16B raw key 试。
  2. /tmp/carve.bin     : 1.3MB carve 出的进程内存; 16B 滑窗逐个试(quick_verify 极快)。
用 Info.db/Session.db/Contact.db 页1 校验; 命中再 verify_key 全量确认, 存 wxwork_keys.json。

命中 = 拿到 key, 可直接离线解密; 未命中 = key 只在活进程内存, 需 find_key_macos.py。
"""
import hashlib
import json
import os
import sys

_H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_H, os.path.dirname(_H)]
from wxwork_crypto import PAGE_SZ, quick_verify, verify_key

from wecom_paths import profile_dir
PROFILE = profile_dir()
# 同 magic = 同 key 一组; 不同库可能不同 key, 都试
TARGETS = {
    "messages(Info.db)": os.path.join(PROFILE, "Messages1/Info.db"),
    "session(Session.db)": os.path.join(PROFILE, "Messages1/Session.db"),
    "contact(Contact.db)": os.path.join(PROFILE, "Contact/Contact.db"),
}
ALLKEYS = "/tmp/allkeys.txt"
CARVE = "/tmp/carve.bin"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wxwork_keys.json")


def load_page1(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        pg = f.read(PAGE_SZ)
    return pg if len(pg) == PAGE_SZ else None


def iter_candidates():
    seen = set()
    if os.path.exists(ALLKEYS):
        n = 0
        for line in open(ALLKEYS):
            h = line.strip()
            if len(h) != 64:
                continue
            try:
                k = bytes.fromhex(h)
            except ValueError:
                continue
            for cand in (k[:16], k[16:], hashlib.md5(k).digest()):
                if cand not in seen:
                    seen.add(cand)
                    n += 1
                    yield cand, f"allkeys:{h[:12]}.."
        print(f"[*] allkeys.txt 派生 {n} 个 16B 候选")
    if os.path.exists(CARVE):
        data = open(CARVE, "rb").read()
        print(f"[*] carve.bin {len(data)} 字节, 16B 滑窗扫描中...")
        for i in range(len(data) - 16):
            cand = bytes(data[i : i + 16])
            if len(set(cand)) < 6 or cand in seen:  # 低熵/重复跳过
                continue
            seen.add(cand)
            yield cand, f"carve@{i}"


def main():
    pages = {}
    for name, path in TARGETS.items():
        pg = load_page1(path)
        if pg:
            pages[name] = pg
        else:
            print(f"[!] 缺失/异常: {path}")
    if not pages:
        sys.exit("无可用目标库")
    print(f"[*] 目标库: {', '.join(pages)}")

    found = {}
    tested = 0
    for cand, src in iter_candidates():
        tested += 1
        for name, pg in pages.items():
            if name in found:
                continue
            if quick_verify(cand, pg) and verify_key(cand, pg):
                found[name] = {"key": cand.hex(), "src": src}
                print(f"\n  [FOUND] {name}\n    key = {cand.hex()}\n    src = {src}")
        if len(found) == len(pages):
            break

    print(f"\n[*] 共测 {tested} 候选; 命中 {len(found)}/{len(pages)}")
    if found:
        json.dump({k: v["key"] for k, v in found.items()},
                  open(OUT, "w"), indent=2, ensure_ascii=False)
        try:
            os.chmod(OUT, 0o600)
        except OSError:
            pass
        print(f"[*] 已保存 {OUT} (0600)")
        print("[*] 下一步: 用该 key 解密 → 结构化导出")
    else:
        print("[*] 离线未命中 → key 只在活进程内存; 启动企业微信登录后跑 find_key_macos.py")


if __name__ == "__main__":
    main()
