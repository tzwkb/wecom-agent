#!/usr/bin/env python3
"""纯 mach_vm 内存读取（task_for_pid，不 ptrace/不注入，反调试无感）。
搜数据库 salt 定位 wxSQLite3 codec 结构，dump 周边供分析 key。
用法: mem_scan.py <pid> <db_path>
"""
import ctypes, sys

PID = int(sys.argv[1])
DB = sys.argv[2]

libc = ctypes.CDLL("/usr/lib/libSystem.dylib", use_errno=True)
mts = ctypes.c_uint.in_dll(libc, "mach_task_self_").value

task_for_pid = libc.task_for_pid
task_for_pid.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
task_for_pid.restype = ctypes.c_int

mach_vm_region = libc.mach_vm_region
mach_vm_region.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64), ctypes.c_int, ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
mach_vm_region.restype = ctypes.c_int

mach_vm_read_overwrite = libc.mach_vm_read_overwrite
mach_vm_read_overwrite.argtypes = [ctypes.c_uint, ctypes.c_uint64, ctypes.c_uint64,
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
mach_vm_read_overwrite.restype = ctypes.c_int

task = ctypes.c_uint(0)
kr = task_for_pid(mts, PID, ctypes.byref(task))
if kr != 0:
    print(f"task_for_pid FAILED kr={kr} (需 sudo 或权限不足)"); sys.exit(1)
print(f"task_for_pid OK task={task.value}")

salt = open(DB, "rb").read(16)
print(f"salt(db头16字节)={salt.hex()}")

VM_BASIC_INFO_64 = 9
addr = ctypes.c_uint64(0); size = ctypes.c_uint64(0)
info = (ctypes.c_int * 10)(); cnt = ctypes.c_uint(10); obj = ctypes.c_uint(0)
hits = []; scanned = 0
while True:
    kr = mach_vm_region(task, ctypes.byref(addr), ctypes.byref(size),
        VM_BASIC_INFO_64, ctypes.cast(info, ctypes.c_void_p),
        ctypes.byref(cnt), ctypes.byref(obj))
    if kr != 0:
        break
    rsize = size.value
    if 0 < rsize < 300 * 1024 * 1024:
        buf = ctypes.create_string_buffer(rsize)
        out = ctypes.c_uint64(0)
        if mach_vm_read_overwrite(task, addr.value, rsize,
                ctypes.cast(buf, ctypes.c_void_p), ctypes.byref(out)) == 0:
            data = buf.raw[:out.value]; scanned += len(data)
            i = data.find(salt)
            while i != -1:
                s = max(0, i - 80); e = min(len(data), i + 96)
                hits.append((addr.value + i, data[s:e]))
                i = data.find(salt, i + 1)
    addr.value += size.value
    if len(hits) > 60:
        break

print(f"扫描 {scanned//1024//1024}MB, salt 命中 {len(hits)} 处")
for off, chunk in hits[:30]:
    print(f"@{hex(off)} {chunk.hex()}")
