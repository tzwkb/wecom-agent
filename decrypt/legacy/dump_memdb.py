#!/usr/bin/env python3
"""从内存连续地址 dump 解密后的 SQLite DB 镜像 → 文件。
用法: dump_memdb.py <pid> <addr_hex> <out.db>
读 header 的 db-size(页数) 字段, 读完整库。
"""
import ctypes, sys

PID=int(sys.argv[1]); ADDR=int(sys.argv[2],16); OUT=sys.argv[3]
libc=ctypes.CDLL("/usr/lib/libSystem.dylib",use_errno=True)
mts=ctypes.c_uint.in_dll(libc,"mach_task_self_").value
tfp=libc.task_for_pid; tfp.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]; tfp.restype=ctypes.c_int
vrd=libc.mach_vm_read_overwrite
vrd.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint64)]; vrd.restype=ctypes.c_int

task=ctypes.c_uint(0)
if tfp(mts,PID,ctypes.byref(task))!=0: print("tfp失败"); sys.exit(1)

def rd(a,n):
    buf=ctypes.create_string_buffer(n); out=ctypes.c_uint64(0)
    if vrd(task,a,n,ctypes.cast(buf,ctypes.c_void_p),ctypes.byref(out))!=0: return None
    return buf.raw[:out.value]

head=rd(ADDR,100)
if not head or head[:15]!=b"SQLite format 3":
    print("该地址非SQLite头"); sys.exit(1)
ps=(head[16]<<8)|head[17]
npages=int.from_bytes(head[28:32],"big")
print(f"page_size={ps} db_size={npages}页 = {ps*npages}字节")
if npages<=0 or npages>1000000: npages=2000  # 兜底
total=ps*npages
data=rd(ADDR,total)
if not data: print("读取失败"); sys.exit(1)
open(OUT,"wb").write(data)
print(f"已写 {len(data)} 字节 → {OUT}")
