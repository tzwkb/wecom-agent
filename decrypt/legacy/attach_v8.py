import frida,sys,time,json
PID=int(sys.argv[1])
s=frida.attach(PID)
sc=s.create_script(open("hook_v8.js").read())
sc.set_log_handler(lambda l,t:print(t,flush=True));sc.load()
for _ in range(60):
    time.sleep(2)
    try:
        d=sc.exports_sync.dump()
        if d:json.dump(d,open("/tmp/wecom_v8.json","w"))
    except:pass
