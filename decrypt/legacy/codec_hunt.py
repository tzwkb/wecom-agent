#!/usr/bin/env python3
"""锚点扫描+key测试合一: 扫内存 magic 前缀, 对周围每个32B窗口试解 Info.db page2。
gentle(task_for_pid只读)。"""
import ctypes, sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PID=int(sys.argv[1]); DB=sys.argv[2]
data=open(DB,"rb").read()
PS=4096; pg2=data[PS:2*PS]

def valid(key):
    for rsv in (48,16,64,80,32):
        end=PS-rsv
        if end%16: continue
        iv=pg2[end:end+16]
        try:
            c=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor()
            pt=c.update(pg2[:end])+c.finalize()
        except: continue
        if pt and pt[0] in (0x02,0x05,0x0a,0x0d):
            cs=(pt[5]<<8)|pt[6]
            if (cs==0 or 8<=cs<=PS) and ((pt[3]<<8)|pt[4])<=1000:
                return rsv
    return None

libc=ctypes.CDLL("/usr/lib/libSystem.dylib",use_errno=True)
mts=ctypes.c_uint.in_dll(libc,"mach_task_self_").value
tfp=libc.task_for_pid; tfp.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]; tfp.restype=ctypes.c_int
vmr=libc.mach_vm_region; vmr.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint64),ctypes.c_int,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(ctypes.c_uint)]; vmr.restype=ctypes.c_int
vrd=libc.mach_vm_read_overwrite; vrd.argtypes=[ctypes.c_uint,ctypes.c_uint64,ctypes.c_uint64,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint64)]; vrd.restype=ctypes.c_int
task=ctypes.c_uint(0)
if tfp(mts,PID,ctypes.byref(task))!=0: sys.exit("tfp失败")

MAGIC=bytes.fromhex("a41d91375995d7d6")
addr=ctypes.c_uint64(0); size=ctypes.c_uint64(0); info=(ctypes.c_int*10)(); cnt=ctypes.c_uint(10); obj=ctypes.c_uint(0)
anchors=0; tested=0
while True:
    if vmr(task,ctypes.byref(addr),ctypes.byref(size),9,ctypes.cast(info,ctypes.c_void_p),ctypes.byref(cnt),ctypes.byref(obj))!=0: break
    rs=size.value
    if 0<rs<300*1024*1024:
        b=ctypes.create_string_buffer(rs); o=ctypes.c_uint64(0)
        if vrd(task,addr.value,rs,ctypes.cast(b,ctypes.c_void_p),ctypes.byref(o))==0:
            d=b.raw[:o.value]
            i=d.find(MAGIC)
            while i!=-1:
                anchors+=1
                lo=max(0,i-512); hi=min(len(d),i+512)
                win=d[lo:hi]
                for off in range(0,len(win)-32):
                    key=win[off:off+32]
                    if len(set(key))<8: continue   # 跳过低熵
                    tested+=1
                    rsv=valid(key)
                    if rsv is not None:
                        print(f"🎉 KEY={key.hex()} reserve={rsv} (anchor@{hex(addr.value+i)})")
                        import json; json.dump({"key":key.hex(),"keylen":256,"page":PS,"reserve":rsv},open("/tmp/wecom_dbkey.json","w"))
                        sys.exit(0)
                i=d.find(MAGIC,i+1)
    addr.value+=size.value
    if anchors>=200: break
print(f"anchors={anchors} tested={tested} [MISS]")
