import frida,sys,time,os,json
PID=int(sys.argv[1]); DIR=os.path.dirname(os.path.abspath(__file__))
s=frida.attach(PID)
sc=s.create_script(open(os.path.join(DIR,"carve_pages.js")).read())
logs=[]; sc.set_log_handler(lambda l,t:(logs.append(t),print(t,flush=True)))
sc.load()
time.sleep(8)
try:
    hits=sc.exports_sync.hits()
    json.dump(hits, open("/tmp/wecom_carve.json","w"), indent=2)
    print("HITS:", len(hits))
except Exception as e:
    print("ERR", e)
