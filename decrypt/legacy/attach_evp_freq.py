import frida, sys, time, os, json
PID = int(sys.argv[1])
DIR = os.path.dirname(os.path.abspath(__file__))
HOOK = open(os.path.join(DIR,"hook_evp_freq.js")).read()
s = frida.attach(PID)
sc = s.create_script(HOOK)
logs=[]
sc.set_log_handler(lambda l,t: logs.append(t))
sc.load()
print("attached, hook loaded. 等待你点击会话读取消息...", flush=True)
# 保持运行，定时 dump top
for _ in range(60):
    time.sleep(2)
    try:
        top = sc.exports_sync.top()
        tot = sc.exports_sync.total()
    except Exception as e:
        continue
    # 写到文件
    open("/tmp/wecom_freq.json","w").write(json.dumps({"total":tot,"top":top}, indent=2))
