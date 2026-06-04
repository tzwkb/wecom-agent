import frida, sys, time, os
PID = int(sys.argv[1])
SALT = sys.argv[2]
OUT = "/tmp/wecom_scan.log"
open(OUT,"w").close()
def emit(t): open(OUT,"a").write(t+"\n")
DIR = os.path.dirname(os.path.abspath(__file__))
js = open(os.path.join(DIR,"scan_codec.js")).read().replace("SALT_PLACEHOLDER", '"%s"' % SALT)
s = frida.attach(PID)
sc = s.create_script(js)
sc.set_log_handler(lambda lvl,txt: emit(txt))
sc.on("message", lambda m,d: emit(str(m.get("payload",m))))
sc.load()
# 等扫描完成
t=time.time()
while time.time()-t < 120:
    time.sleep(2)
    if "scan done" in open(OUT).read(): break
emit("[*] python done")
