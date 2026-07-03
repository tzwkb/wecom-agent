#!/usr/bin/env python3
"""凭证联调自检 —— 填好 config.json 后, 一条命令验证各能力通不通。

默认**只读**(gettoken + 通讯录), 不外发。外发=发给真人/真建文档, 须你显式开关:
  --send-self USERID   给指定成员(建议先发你自己)发一条测试消息
  --create-doc         建一篇测试在线文档并写入一行(顺带验证 编辑/读取)
用法: python3 selfcheck.py [--send-self USERID] [--create-doc]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WECOM = os.path.join(HERE, "wecom.py")


def call(cat, method, args=None):
    r = subprocess.run([sys.executable, WECOM, cat, method, json.dumps(args or {}, ensure_ascii=False)],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": (r.stdout or r.stderr).strip()[:200]}


def ok(r):
    return isinstance(r, dict) and r.get("errcode", 0) == 0 and "error" not in r


def main():
    args = sys.argv[1:]
    results = []
    results.append(("token+部门列表 (contact departments)", call("contact", "departments")))
    results.append(("部门成员 (contact users)", call("contact", "users", {"department_id": 1})))

    if "--send-self" in args:
        uid = args[args.index("--send-self") + 1]
        results.append((f"发消息给 {uid} (message text)",
                        call("message", "text", {"touser": uid, "content": "✅ wecom-agent 自检：发送通路正常"})))

    if "--create-doc" in args:
        rc = call("doc", "create", {"doc_name": "wecom-agent自检文档", "doc_type": 3})
        results.append(("建文档 (doc create)", rc))
        docid = rc.get("docid") or rc.get("doc_id")
        if docid:
            results.append(("编辑文档 (doc edit)",
                            call("doc", "edit", {"docid": docid,
                                 "requests": [{"insert_text": {"text": "自检写入一行\n",
                                                               "location": {"index": 1}}}]})))
            results.append(("读取文档 (doc get)", call("doc", "get", {"docid": docid})))

    print("=" * 56)
    print("  wecom-agent 联调自检")
    print("=" * 56)
    all_ok = True
    for name, r in results:
        good = ok(r)
        all_ok = all_ok and good
        extra = "" if good else f"  → errcode={r.get('errcode')} {r.get('errmsg') or r.get('error', '')}"
        print(f"{'✅' if good else '❌'} {name}{extra}")
    print("-" * 56)
    if "--send-self" not in args and "--create-doc" not in args:
        print("只读自检完成。外发测试(发给真人/真建文档,需你确认): --send-self <你的userid> [--create-doc]")

    flat = json.dumps([r for _, r in results], ensure_ascii=False)
    if "60020" in flat:
        print("⚠️ 60020: 出口IP不在『企业可信IP』→ 应用→Company's Trusted IP 添加你的公网IP")
    if "60011" in flat or "48002" in flat:
        print("⚠️ 60011/48002: 通讯录权限/可见范围不足(该成员需在应用可见范围内)")
    if "40001" in flat or "42001" in flat:
        print("⚠️ 40001/42001: token无效 → 检查 config.json 的 corpid/secret")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
