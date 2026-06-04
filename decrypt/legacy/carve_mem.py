#!/usr/bin/env python3
"""ctypes task_for_pid 扫内存(只读,无frida): 找解密后SQLite页缓存。
找 'SQLite format 3' + b-tree叶子页, 提取明文消息。
用法: carve_mem.py <pid>
"""
import ctypes, sys, re

PID = int(sys.argv[1])
libc = ctypes.CDLL("/usr/lib/libSystem.dylib", use_errno=True)
mts = ctypes.c_uint.in_dll(libc, "mach_task_self_").value
tfp = libc.task_for_pid; tfp.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]; tfp.restype=ctypes.c_int
vmr = libc.mach_vm_region
vmr.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint64),ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ctypes.c_uint)]
vmr.restype=ctypes.c_int
vrd = libc.mach_vm_read_overwrite
vrd.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint64)]
vrd.restype=ctypes.c_int

task=ctypes.c_uint(0)
if tfp(mts,PID,ctypes.byref(task))!=0:
    print("task_for_pid 失败"); sys.exit(1)
print(f"task_for_pid OK task={task.value}")

HDR=b"SQLite format 3\x00"
addr=ctypes.c_uint64(0); size=ctypes.c_uint64(0)
info=(ctypes.c_int*10)(); cnt=ctypes.c_uint(10); obj=ctypes.c_uint(0)
hdr_hits=0; pages=[]; scanned=0
while True:
    if vmr(task,ctypes.byref(addr),ctypes.byref(size),9,ctypes.cast(info,ctypes.c_void_p),ctypes.byref(cnt),ctypes.byref(obj))!=0:
        break
    rs=size.value
    if 0<rs<400*1024*1024:
        buf=ctypes.create_string_buffer(rs); out=ctypes.c_uint64(0)
        if vrd(task,addr.value,rs,ctypes.cast(buf,ctypes.c_void_p),ctypes.byref(out))==0:
            data=buf.raw[:out.value]; scanned+=len(data)
            i=data.find(HDR)
            while i!=-1:
                hdr_hits+=1
                ps=(data[i+16]<<8)|data[i+17] if i+18<=len(data) else 0
                pages.append((addr.value+i, ps, data[i:i+64]))
                i=data.find(HDR,i+1)
    addr.value+=size.value
    if hdr_hits>=30: break
print(f"扫描 {scanned//1024//1024}MB, 'SQLite format 3' 命中 {hdr_hits} 处")
for off,ps,head in pages[:10]:
    valid = ps in (512,1024,2048,4096,8192,16384,32768,65536)
    print(f"@{hex(off)} page_size字段={ps} {'✓合法SQLite头' if valid else ''}")
    print(f"   {head.hex()}")
