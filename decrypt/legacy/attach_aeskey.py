import frida,sys,time,os,json
PID=int(sys.argv[1]); DIR=os.path.dirname(os.path.abspath(__file__))
s=frida.attach(PID)
sc=s.create_script(open(os.path.join(DIR,"hook_aeskey.js")).read())
logs=[]; sc.set_log_handler(lambda l,t:logs.append(t)); sc.load()
print("attached",flush=True)
for _ in range(80):
    time.sleep(2)
    try: open("/tmp/wecom_aeskey.json","w").write(json.dumps(sc.exports_sync.dump()))
    except: pass
