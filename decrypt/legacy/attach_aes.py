import frida, sys, time, os
PID = int(sys.argv[1]); WAIT = int(sys.argv[2]) if len(sys.argv)>2 else 60
OUT = "/tmp/wecom_aes.log"
open(OUT,"w").close()
def emit(t): open(OUT,"a").write(t+"\n")
DIR = os.path.dirname(os.path.abspath(__file__))
HOOK = open(os.path.join(DIR,"hook_aes.js")).read()
s = frida.attach(PID)
sc = s.create_script(HOOK)
sc.set_log_handler(lambda lvl,txt: emit(txt))
sc.on("message", lambda m,d: emit(str(m.get("payload",m))))
sc.load()
emit("[*] attached")
t=time.time()
while time.time()-t < WAIT: time.sleep(2)
emit("[*] done")
