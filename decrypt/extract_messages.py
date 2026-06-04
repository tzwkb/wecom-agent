#!/usr/bin/env python3
"""企业微信消息提取(macOS) — 内存法,无需key/frida,只读task_for_pid。
原理: 企微登录后SQLite页在内存解密缓存; 扫b-tree叶子页提取消息记录。
前提: 企业微信已运行并登录。
用法: extract_messages.py [out.txt]
"""
import ctypes, sys, re

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/wecom_messages.txt"

def find_pid():
    import subprocess
    r = subprocess.run(["pgrep","-f","/Applications/企业微信.app/Contents/MacOS/企业微信"],
                       capture_output=True, text=True)
    pids = r.stdout.split()
    return int(pids[0]) if pids else None

PID = find_pid()
if not PID:
    sys.exit("企业微信未运行,请先启动并登录")

libc=ctypes.CDLL("/usr/lib/libSystem.dylib",use_errno=True)
mts=ctypes.c_uint.in_dll(libc,"mach_task_self_").value
tfp=libc.task_for_pid; tfp.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]; tfp.restype=ctypes.c_int
vmr=libc.mach_vm_region; vmr.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint64),ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ctypes.c_uint)]; vmr.restype=ctypes.c_int
vrd=libc.mach_vm_read_overwrite; vrd.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint64)]; vrd.restype=ctypes.c_int

task=ctypes.c_uint(0)
if tfp(mts,PID,ctypes.byref(task))!=0:
    sys.exit(f"task_for_pid 失败(需对企微做adhoc重签名去hardened runtime)")
print(f"task_for_pid OK pid={PID}")

# 提取可读文本片段(中文消息+ASCII), 过滤噪音
TEXT=re.compile(rb'(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]|[\x20-\x7e]){6,}')
CJK=re.compile(rb'[\xe4-\xe9][\x80-\xbf][\x80-\xbf]')
seen=set(); msgs=[]
addr=ctypes.c_uint64(0); size=ctypes.c_uint64(0); info=(ctypes.c_int*10)(); cnt=ctypes.c_uint(10); obj=ctypes.c_uint(0)
scanned=0
while True:
    if vmr(task,ctypes.byref(addr),ctypes.byref(size),9,ctypes.cast(info,ctypes.c_void_p),ctypes.byref(cnt),ctypes.byref(obj))!=0: break
    rs=size.value
    if 0<rs<300*1024*1024:
        b=ctypes.create_string_buffer(rs); o=ctypes.c_uint64(0)
        if vrd(task,addr.value,rs,ctypes.cast(b,ctypes.c_void_p),ctypes.byref(o))==0:
            data=b.raw[:o.value]; scanned+=len(data)
            for m in TEXT.finditer(data):
                s=m.group()
                if len(CJK.findall(s))>=2:           # 至少2个中文字,过滤代码/路径
                    try: t=s.decode('utf-8')
                    except: continue
                    t=t.strip()
                    if 3<=len(t)<=300 and t not in seen:
                        seen.add(t); msgs.append(t)
    addr.value+=size.value

with open(OUT,"w") as f:
    f.write(f"# 企业微信内存消息提取 pid={PID} 扫描{scanned//1024//1024}MB 去重{len(msgs)}条\n\n")
    for t in msgs:
        f.write(t+"\n")
print(f"扫描{scanned//1024//1024}MB,提取{len(msgs)}条文本 → {OUT}")
print("样本:")
for t in msgs[:20]:
    print("  ",t[:80])
