import frida, sys, time, os, json
APP="/Applications/企业微信.app/Contents/MacOS/企业微信"
DIR=os.path.dirname(os.path.abspath(__file__))
HOOK=open(os.path.join(DIR,"hook_evp_nid.js")).read()
dev=frida.get_local_device()
pid=dev.spawn([APP])
s=dev.attach(pid)
sc=s.create_script(HOOK)
logs=[]
sc.set_log_handler(lambda l,t: logs.append(t))
sc.load()
dev.resume(pid)
open("/tmp/spawn_evp.log","w").write(f"spawned pid={pid}\n")
for i in range(45):
    time.sleep(2)
    try:
        d=sc.exports_sync.dump()
        # 只存 CBC候选(IV非GCM格式 或 空IV, 排除901 gcm)
        cbc=[r for r in d if r['nid']!=901 and not (r.get('iv','').endswith('00000000') and len(r.get('iv',''))==32)]
        open("/tmp/spawn_evp.json","w").write(json.dumps(d))
        alive = pid in [p.pid for p in dev.enumerate_processes()]
        open("/tmp/spawn_evp.log","a").write(f"t={i*2}s total={len(d)} cbc_cand={len(cbc)} alive={alive}\n")
        if not alive: break
    except Exception as e:
        open("/tmp/spawn_evp.log","a").write(f"t={i*2}s ERR {e}\n")
