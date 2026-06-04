import frida,sys,time,os
PID=int(sys.argv[1]); DIR=os.path.dirname(os.path.abspath(__file__))
OUT="/tmp/wecom_ctx.log"; open(OUT,"w").close()
s=frida.attach(PID)
sc=s.create_script(open(os.path.join(DIR,"hook_ctx_dump.js")).read())
sc.set_log_handler(lambda l,t: open(OUT,"a").write(t+"\n"))
sc.load()
for _ in range(70): time.sleep(2)
