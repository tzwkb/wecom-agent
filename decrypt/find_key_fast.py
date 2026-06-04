#!/usr/bin/env python3
"""macOS 活进程内存扫描(C 加速)找 WeCom 16B raw key。

只读 task_for_pid + mach_vm_read_overwrite(需企微 adhoc 重签, 本项目已具备), 不注入、不改内存。
每个内存区域交给 validate.dylib(CommonCrypto 原生速度)逐 16B 窗校验 wxSQLite3 页1。
前提: 企业微信运行并已登录(key 在内存)。命中存 wxwork_keys.json。
"""
import ctypes
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wxwork_crypto import PAGE_SZ, generate_initial_vector, verify_key

HERE = os.path.dirname(os.path.abspath(__file__))
from wecom_paths import profile_dir
PROFILE = profile_dir()
TARGETS = [("messages", "Messages1/Info.db"),
           ("session", "Messages1/Session.db"),
           ("contact", "Contact/Contact.db")]
OUT = os.path.join(HERE, "wxwork_keys.json")
LIB = os.path.join(HERE, "validate.dylib")


def find_pid():
    r = subprocess.run(
        ["pgrep", "-f", "/Applications/企业微信.app/Contents/MacOS/企业微信"],
        capture_output=True, text=True,
    )
    s = r.stdout.split()
    return int(s[0]) if s else None


def main():
    names, page1s = [], []
    for n, rel in TARGETS:
        p = os.path.join(PROFILE, rel)
        if not os.path.exists(p):
            continue
        with open(p, "rb") as f:
            pg = f.read(PAGE_SZ)
        if len(pg) == PAGE_SZ:
            names.append(n)
            page1s.append(pg)
    if not page1s:
        sys.exit("无目标库")
    ntgt = len(page1s)
    iv = generate_initial_vector(1)               # 所有库页1共用
    frag8 = b"".join(bytes(pg[16:24]) for pg in page1s)
    cb0 = b"".join(bytes(pg[8:16]) + bytes(pg[24:32]) for pg in page1s)
    ivflat = iv * ntgt

    if not os.path.exists(LIB):
        sys.exit(f"缺 {LIB}, 先编译 validate.c")
    lib = ctypes.CDLL(LIB)
    lib.scan_buf.restype = ctypes.c_long
    lib.scan_buf.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_int,
                             ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                             ctypes.c_char_p, ctypes.c_char_p]

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
    print(f"task_for_pid OK pid={pid}; 目标 {names}")

    out_keys = ctypes.create_string_buffer(16 * ntgt)
    found = ctypes.create_string_buffer(ntgt)
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
                lib.scan_buf(data, len(data), ntgt, frag8, cb0, ivflat, out_keys, found)
                if all(found.raw[t] for t in range(ntgt)):
                    break
        addr.value += size.value
        if regions % 300 == 0 and regions:
            print(f"  ...{scanned // 1024 // 1024}MB {regions}区 {time.time()-t0:.0f}s 命中{sum(found.raw)}")

    res = {}
    for t, n in enumerate(names):
        if found.raw[t]:
            k = out_keys.raw[t * 16:t * 16 + 16]
            if verify_key(k, page1s[t]):
                res[n] = k.hex()
                print(f"  [FOUND] {n}: {k.hex()}")
    print(f"\n扫描 {scanned // 1024 // 1024}MB/{regions}区 {time.time()-t0:.0f}s; 命中 {len(res)}/{ntgt}")
    if res:
        json.dump(res, open(OUT, "w"), indent=2, ensure_ascii=False)
        try:
            os.chmod(OUT, 0o600)
        except OSError:
            pass
        print(f"已存 {OUT} → decrypt_wxwork.py")
    else:
        print("未命中(内存中无匹配16B窗口)。可能 key 经轮密钥扩展存储或在>300MB区被跳过。")


if __name__ == "__main__":
    main()
