#!/usr/bin/env python3
"""macOS 活进程内存扫描, 找 WeCom 各库 16 字节 raw key。

只读 task_for_pid(需企微 adhoc 重签去 hardened runtime, 本项目已具备), 不注入、不改内存。
前提: 企业微信已运行并登录。
策略(命中即用 verify_key 全量确认):
  ① x'<32hex>' SQL 字面量(C 正则, 快)
  ② 裸 32-hex 文本(C 正则, 快)
  ③ --deep: 16B 原始窗口(熵过滤 + 限时, best-effort; 纯 Python 慢, 仅兜底)
用法: find_key_macos.py [--deep] [--seconds N]
"""
import ctypes
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wxwork_crypto import PAGE_SZ, quick_verify, verify_key

PROFILE = os.path.expanduser(
    "~/Library/Containers/com.tencent.WeWorkMac/Data/Documents/Profiles/"
    "821FB603491DCFE76AB2D610CB6D9C89"
)
TARGETS = {
    "messages": os.path.join(PROFILE, "Messages1/Info.db"),
    "session": os.path.join(PROFILE, "Messages1/Session.db"),
    "contact": os.path.join(PROFILE, "Contact/Contact.db"),
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wxwork_keys.json")


def find_pid():
    r = subprocess.run(
        ["pgrep", "-f", "/Applications/企业微信.app/Contents/MacOS/企业微信"],
        capture_output=True, text=True,
    )
    s = r.stdout.split()
    return int(s[0]) if s else None


def main():
    deep = "--deep" in sys.argv
    secs = int(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 180

    pages = {}
    for n, p in TARGETS.items():
        if os.path.exists(p):
            with open(p, "rb") as f:
                pg = f.read(PAGE_SZ)
            if len(pg) == PAGE_SZ:
                pages[n] = pg
    if not pages:
        sys.exit("无目标库")
    pid = find_pid()
    if not pid:
        sys.exit("企业微信未运行,请先启动并登录")

    libc = ctypes.CDLL("/usr/lib/libSystem.dylib", use_errno=True)
    mts = ctypes.c_uint.in_dll(libc, "mach_task_self_").value
    tfp = libc.task_for_pid
    tfp.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
    tfp.restype = ctypes.c_int
    vmr = libc.mach_vm_region
    vmr.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64),
                    ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
    vmr.restype = ctypes.c_int
    vrd = libc.mach_vm_read_overwrite
    vrd.argtypes = [ctypes.c_uint, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    vrd.restype = ctypes.c_int

    task = ctypes.c_uint(0)
    if tfp(mts, pid, ctypes.byref(task)) != 0:
        sys.exit("task_for_pid 失败(需对企微 adhoc 重签去 hardened runtime)")
    print(f"task_for_pid OK pid={pid}, 目标库 {list(pages)}; deep={deep}")

    found = {}

    def check(cand):
        for n, pg in pages.items():
            if n in found:
                continue
            if quick_verify(cand, pg) and verify_key(cand, pg):
                found[n] = cand.hex()
                print(f"\n  [FOUND] {n}: {cand.hex()}")
        return len(found) == len(pages)

    hexlit = re.compile(rb"x'([0-9a-fA-F]{32})'")
    barehex = re.compile(rb"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])")
    addr = ctypes.c_uint64(0); size = ctypes.c_uint64(0)
    info = (ctypes.c_int * 10)(); cnt = ctypes.c_uint(10); obj = ctypes.c_uint(0)
    t0 = time.time(); scanned = 0; regions = 0

    while True:
        if vmr(task, ctypes.byref(addr), ctypes.byref(size), 9,
               ctypes.cast(info, ctypes.c_void_p), ctypes.byref(cnt), ctypes.byref(obj)) != 0:
            break
        rs = size.value
        if 0 < rs < 300 * 1024 * 1024:
            b = ctypes.create_string_buffer(rs); o = ctypes.c_uint64(0)
            if vrd(task, addr.value, rs, ctypes.cast(b, ctypes.c_void_p), ctypes.byref(o)) == 0:
                data = b.raw[:o.value]; scanned += len(data); regions += 1
                for m in hexlit.finditer(data):
                    try:
                        if check(bytes.fromhex(m.group(1).decode())):
                            break
                    except ValueError:
                        pass
                if len(found) < len(pages):
                    for m in barehex.finditer(data):
                        try:
                            if check(bytes.fromhex(m.group(1).decode())):
                                break
                        except ValueError:
                            pass
                if deep and len(found) < len(pages):
                    for i in range(len(data) - 16):
                        c = data[i:i + 16]
                        if len(set(c)) < 8:
                            continue
                        if any(quick_verify(c, pg) for n, pg in pages.items() if n not in found):
                            if check(c):
                                break
                        if time.time() - t0 > secs:
                            print(f"[WARN] --deep 限时 {secs}s 到; 已扫 {scanned//1024//1024}MB/{regions}区, 覆盖不完全")
                            break
        addr.value += size.value
        if len(found) == len(pages):
            break
        if deep and time.time() - t0 > secs:
            break

    print(f"\n扫描 {scanned//1024//1024}MB/{regions}区 {time.time()-t0:.1f}s; 命中 {len(found)}/{len(pages)}")
    if found:
        json.dump(found, open(OUT, "w"), indent=2, ensure_ascii=False)
        try:
            os.chmod(OUT, 0o600)
        except OSError:
            pass
        print(f"已保存 {OUT} (0600) → 跑 decrypt_wxwork.py")
    else:
        print("未命中。若 key 仅以二进制存在(非hex字面量): 重试加 --deep, 或用 keyhook.c "
              "注入版在进程内 C 速度全扫(最稳, 需重编+注入+go)。")


if __name__ == "__main__":
    main()
