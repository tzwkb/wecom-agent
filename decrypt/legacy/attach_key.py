#!/usr/bin/env python3
import frida, sys, time, os

WAIT = int(sys.argv[1]) if len(sys.argv) > 1 else 240
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
target = sys.argv[2] if len(sys.argv) > 2 else "企业微信"
try:
    session = dev.attach(int(target) if target.isdigit() else target)
except Exception as e:
    emit(f"[!] attach 失败: {e}")
    sys.exit(1)

script = session.create_script(HOOK)
script.on("message", on_msg)
script.set_log_handler(lambda level, text: emit(text))
script.load()
emit(f"[*] attached + hook installed; 现在去扫码登录，最长等 {WAIT}s")

deadline = time.time() + WAIT
got = False
while time.time() < deadline:
    time.sleep(2)
    if "[PBKDF]" in open(OUT).read():
        got = True
        emit("[+] 捕获到密钥派生，再收集 8s ...")
        time.sleep(8)
        break

emit("[*] done" + ("（已抓到）" if got else "（超时未抓到 PBKDF 调用）"))
