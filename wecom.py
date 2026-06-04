#!/usr/bin/env python3
"""企业微信自建应用 API CLI — 零依赖，供 agent 与人调用。

用法:
    python3 wecom.py <category> <method> ['<json_args>']

category: contact | message | schedule | meeting | doc | call
逃生舱:   python3 wecom.py call POST /cgi-bin/任意接口 '{"body":{...}}'

凭证（优先级）: 环境变量 WECOM_CORPID/WECOM_SECRET/WECOM_AGENTID > 同目录 config.json
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://qyapi.weixin.qq.com"
DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_CACHE = os.path.join(DIR, ".token_cache.json")


def _load_config():
    cfg = {
        "corpid": os.environ.get("WECOM_CORPID", ""),
        "secret": os.environ.get("WECOM_SECRET", ""),
        "agentid": os.environ.get("WECOM_AGENTID", ""),
    }
    path = os.path.join(DIR, "config.json")
    if os.path.exists(path):
        with open(path) as f:
            file_cfg = json.load(f)
        for k in cfg:
            if not cfg[k] and file_cfg.get(k):
                cfg[k] = str(file_cfg[k])
    if not cfg["corpid"] or not cfg["secret"]:
        _die("缺少凭证：设置 WECOM_CORPID/WECOM_SECRET 或填写 config.json")
    return cfg


def _http(method, path, params=None, body=None, token=None):
    params = dict(params or {})
    if token:
        params["access_token"] = token
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_token(cfg):
    if os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE) as f:
                c = json.load(f)
            if c.get("corpid") == cfg["corpid"] and c.get("expire_at", 0) > time.time() + 60:
                return c["access_token"]
        except Exception:
            pass
    r = _http("GET", "/cgi-bin/gettoken",
              params={"corpid": cfg["corpid"], "corpsecret": cfg["secret"]})
    if r.get("errcode", 0) != 0:
        _die(f"获取 token 失败: {r}")
    token = r["access_token"]
    with open(TOKEN_CACHE, "w") as f:
        json.dump({"corpid": cfg["corpid"], "access_token": token,
                   "expire_at": time.time() + r.get("expires_in", 7200)}, f)
    try:
        os.chmod(TOKEN_CACHE, 0o600)
    except Exception:
        pass
    return token


def _die(msg):
    print(json.dumps({"error": msg}, ensure_ascii=False, indent=2))
    sys.exit(1)


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def contact(method, args, token, cfg):
    if method == "departments":
        return _http("GET", "/cgi-bin/department/simplelist", token=token)
    if method == "users":
        return _http("GET", "/cgi-bin/user/simplelist",
                     params={"department_id": args.get("department_id", 1),
                             "fetch_child": args.get("fetch_child", 1)}, token=token)
    if method == "get":
        return _http("GET", "/cgi-bin/user/get",
                     params={"userid": args["userid"]}, token=token)
    if method == "search":
        r = _http("GET", "/cgi-bin/user/list",
                  params={"department_id": args.get("department_id", 1),
                          "fetch_child": 1}, token=token)
        kw = args["keyword"]
        return {"errcode": r.get("errcode"), "errmsg": r.get("errmsg"),
                "matched": [u for u in r.get("userlist", []) if kw in u.get("name", "")]}
    _die(f"未知 contact 方法: {method}（可用: departments, users, get, search）")


def message(method, args, token, cfg):
    if not cfg.get("agentid"):
        _die("发消息需要 agentid，请在 config.json 填写")
    body = {"touser": args.get("touser", "@all"), "agentid": int(cfg["agentid"])}
    if method == "text":
        body.update({"msgtype": "text", "text": {"content": args["content"]}})
    elif method == "markdown":
        body.update({"msgtype": "markdown", "markdown": {"content": args["content"]}})
    elif method == "news":
        body.update({"msgtype": "news", "news": {"articles": args["articles"]}})
    else:
        _die(f"未知 message 方法: {method}（可用: text, markdown, news）")
    return _http("POST", "/cgi-bin/message/send", body=body, token=token)


ROUTES = {
    "schedule": {
        "add": "/cgi-bin/oa/schedule/add",
        "update": "/cgi-bin/oa/schedule/update",
        "get": "/cgi-bin/oa/schedule/get",
        "del": "/cgi-bin/oa/schedule/del",
        "list": "/cgi-bin/oa/schedule/get_by_calendar",
    },
    "meeting": {
        "create": "/cgi-bin/meeting/create",
        "update": "/cgi-bin/meeting/update",
        "cancel": "/cgi-bin/meeting/cancel",
        "list": "/cgi-bin/meeting/get_user_meetingid",
        "info": "/cgi-bin/meeting/get_info",
    },
    "doc": {
        "create": "/cgi-bin/wedoc/create_doc",
        "get": "/cgi-bin/wedoc/document/get",
        "del": "/cgi-bin/wedoc/del_doc",
        "rename": "/cgi-bin/wedoc/rename_doc",
    },
}


def _routed(category):
    def handler(method, args, token, cfg):
        routes = ROUTES[category]
        if method not in routes:
            _die(f"未知 {category} 方法: {method}（可用: {', '.join(routes)}）")
        return _http("POST", routes[method], body=args, token=token)
    return handler


def call(method, args, token, cfg):
    if "path" not in args:
        _die('call 需要 args.path，例: call POST /cgi-bin/xxx \'{"path":"/cgi-bin/xxx","body":{}}\'')
    return _http(method, args["path"],
                 params=args.get("params"), body=args.get("body"), token=token)


HANDLERS = {
    "contact": contact,
    "message": message,
    "schedule": _routed("schedule"),
    "meeting": _routed("meeting"),
    "doc": _routed("doc"),
    "call": call,
}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    category, method = sys.argv[1], sys.argv[2]
    args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    handler = HANDLERS.get(category)
    if not handler:
        _die(f"未知 category: {category}（可用: {', '.join(HANDLERS)}）")
    cfg = _load_config()
    token = _get_token(cfg)
    _out(handler(method, args, token, cfg))


if __name__ == "__main__":
    main()
