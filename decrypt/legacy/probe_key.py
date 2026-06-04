#!/usr/bin/env python3
import frida, sys, time, os

APP = "/Applications/企业微信.app/Contents/MacOS/企业微信"
WAIT = int(sys.argv[1]) if len(sys.argv) > 1 else 180
OUT = "/tmp/wecom_keys.log"
DIR = os.path.dirname(os.path.abspath(__file__))

with open(f"{DIR}/hook_probe.js") as f:
    HOOK = f.read()

open(OUT, "w").close()
def emit(text):
    with open(OUT, "a") as fp:
        fp.write(text + "\n"); fp.flush()

def on_msg(m, data):
    if m.get("type") == "send":
        emit(str(m["payload"]))
    elif m.get("type") == "error":
        emit("[JS ERROR] " + str(m.get("stack", m)))

dev = frida.get_local_device()
emit(f"[*] spawning 企业微信 ...")
pid = dev.spawn([APP])
session = dev.attach(pid)
script = session.create_script(HOOK)
script.on("message", on_msg)
script.set_log_handler(lambda level, text: emit(text))
script.load()
dev.resume(pid)
emit(f"[*] resumed pid={pid}; 等待扫码登录，最长 {WAIT}s。")

deadline = time.time() + WAIT
got = False
while time.time() < deadline:
    time.sleep(2)
    txt = open(OUT).read()
    if "[PBKDF]" in txt:
        got = True
        emit("[+] 已捕获密钥派生，继续观察 8s 收集全部 ...")
        time.sleep(8)
        break

emit("[*] done" + ("（已抓到）" if got else "（超时未抓到）"))
