import frida, sys, time, os
PID = int(sys.argv[1]); WAIT = int(sys.argv[2]) if len(sys.argv)>2 else 120
OUT = "/tmp/wecom_evp.log"
open(OUT,"w").close()
def emit(t): open(OUT,"a").write(t+"\n")
DIR = os.path.dirname(os.path.abspath(__file__))
HOOK = open(os.path.join(DIR,"hook_evp.js")).read()
s = frida.attach(PID)
sc = s.create_script(HOOK)
sc.set_log_handler(lambda l,t: emit(t))
sc.on("message", lambda m,d: emit(str(m.get("payload",m))))
sc.load()
emit("[*] attached")
t=time.time()
while time.time()-t < WAIT: time.sleep(2)
emit("[*] done")
