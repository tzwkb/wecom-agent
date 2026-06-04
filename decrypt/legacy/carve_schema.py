#!/usr/bin/env python3
"""扫所有解密SQLite头, 打印page-1里的CREATE TABLE schema文本, 找WeCom消息库。"""
import ctypes, sys, re
PID=int(sys.argv[1])
libc=ctypes.CDLL("/usr/lib/libSystem.dylib",use_errno=True)
mts=ctypes.c_uint.in_dll(libc,"mach_task_self_").value
tfp=libc.task_for_pid; tfp.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]; tfp.restype=ctypes.c_int
vmr=libc.mach_vm_region; vmr.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint64),ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ctypes.c_uint)]; vmr.restype=ctypes.c_int
vrd=libc.mach_vm_read_overwrite; vrd.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint64)]; vrd.restype=ctypes.c_int
task=ctypes.c_uint(0)
if tfp(mts,PID,ctypes.byref(task))!=0: sys.exit("tfp失败")

HDR=b"SQLite format 3\x00"
addr=ctypes.c_uint64(0); size=ctypes.c_uint64(0)
info=(ctypes.c_int*10)(); cnt=ctypes.c_uint(10); obj=ctypes.c_uint(0)
hits=0
while True:
    if vmr(task,ctypes.byref(addr),ctypes.byref(size),9,ctypes.cast(info,ctypes.c_void_p),ctypes.byref(cnt),ctypes.byref(obj))!=0: break
    rs=size.value
    if 0<rs<400*1024*1024:
        buf=ctypes.create_string_buffer(rs); out=ctypes.c_uint64(0)
        if vrd(task,addr.value,rs,ctypes.cast(buf,ctypes.c_void_p),ctypes.byref(out))==0:
            data=buf.raw[:out.value]
            i=data.find(HDR)
            while i!=-1:
                hits+=1
                page=data[i:i+4096]
                # 提取 CREATE TABLE / 表名 文本
                txt=re.findall(rb"CREATE [A-Z]+ [\"']?[A-Za-z_][A-Za-z0-9_]{2,40}", page)
                names=set(re.findall(rb"[A-Za-z_][A-Za-z0-9_]{4,40}", page))
                wecom=[n for n in names if re.search(rb"essage|hat|ession|ontact|onversation|sg|oom|edia", n)]
                if txt or wecom:
                    print(f"@{hex(addr.value+i)}:")
                    for t in txt[:8]: print("   ",t.decode('latin1'))
                    if wecom: print("    候选表名:", [w.decode('latin1') for w in list(wecom)[:12]])
                    print()
                i=data.find(HDR,i+1)
    addr.value+=size.value
    if hits>=60: break
print(f"共 {hits} 个SQLite头")
