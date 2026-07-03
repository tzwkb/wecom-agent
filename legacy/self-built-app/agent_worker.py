#!/usr/bin/env python3
"""自主处理 worker —— 实时接收闭环的"大脑+手"。

与 recv_server.py 解耦: recv_server 只验签解密+快速ACK+把消息写入 jobs/inbox.jsonl;
本 worker 异步读取新消息 → 决策(LLM 或内置规则) → 经 wecom.py 行动(回复消息 / 建文档)。
慢活(调大模型/写文档)放这里, 不占回调的 5 秒窗口。

决策: config.json 配 llm_base_url/llm_key/llm_model(OpenAI 兼容, 如 VectorEngine) → LLM 自主决策;
      未配则用内置规则(回显 + /help + /doc)。
安全: 默认 auto_reply=false; 设 config.json "auto_reply": true 才会自动回复。
用法: agent_worker.py [--dry-run] [--once] [--poll 2]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(HERE, "jobs", "inbox.jsonl")
OFFSET = os.path.join(HERE, "jobs", "inbox.offset")
WECOM = os.path.join(HERE, "wecom.py")


def load_cfg():
    p = os.path.join(HERE, "config.json")
    return json.load(open(p)) if os.path.exists(p) else {}


# ── 行动: 经 wecom.py 调官方 API ──────────────────────────────────────
def wecom(category, method, args):
    r = subprocess.run([sys.executable, WECOM, category, method, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stdout or r.stderr}


def send_text(touser, content):
    return wecom("message", "text", {"touser": touser, "content": content})


def create_doc(title, content):
    # create_doc 建空文档(无正文参数) → 再 batch_update 写入内容
    r = wecom("doc", "create", {"doc_name": title, "doc_type": 3})
    docid = r.get("docid") or r.get("doc_id") or ""
    if docid and content:
        wecom("doc", "edit", {"docid": docid,
              "requests": [{"insert_text": {"text": content, "location": {"index": 1}}}]})
    return r


# ── 决策 ──────────────────────────────────────────────────────────────
def _llm_chat(cfg, system, user):
    body = json.dumps({"model": cfg.get("llm_model", "gpt-4o-mini"),
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}],
                       "temperature": 0.3}).encode()
    req = urllib.request.Request(cfg["llm_base_url"].rstrip("/") + "/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + cfg["llm_key"],
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


SYS = ("你是企业微信助手。读用户消息, 只输出一个 JSON: "
       '{"action":"reply","content":"回复文字"} 或 {"action":"doc","title":"标题","content":"正文"} '
       '或 {"action":"none"}。不要输出多余文字。')


def decide(msg, cfg):
    if msg.get("msgtype") != "text":
        return []
    text = (msg.get("content") or "").strip()
    if not text:
        return []
    if cfg.get("llm_key") and cfg.get("llm_base_url"):
        try:
            out = _llm_chat(cfg, SYS, text)
            s = out[out.find("{"): out.rfind("}") + 1]
            a = json.loads(s)
            if a.get("action") == "reply":
                return [("reply", a.get("content", ""))]
            if a.get("action") == "doc":
                return [("doc", (a.get("title", "AI文档"), a.get("content", "")))]
            return []
        except Exception as e:
            print(f"[LLM 失败,降级规则] {e}")
    # 内置规则兜底
    if text.startswith("/help"):
        return [("reply", "直接发文字我会回复; 发 `/doc 标题|正文` 我建一篇在线文档。")]
    if text.startswith("/doc"):
        title, _, body = text[4:].strip().partition("|")
        return [("doc", (title.strip() or "AI文档", body.strip()))]
    return [("reply", f"收到：{text}")]


def act(actions, msg, dry):
    for kind, payload in actions:
        if kind == "reply":
            if dry:
                print(f"  DRY reply → {msg['from']}: {payload}")
            else:
                print(f"  reply → {msg['from']}: {payload[:40]}  {send_text(msg['from'], payload)}")
        elif kind == "doc":
            title, content = payload
            if dry:
                print(f"  DRY doc → 《{title}》 {len(content)}字")
            else:
                print(f"  doc → 《{title}》  {create_doc(title, content)}")


def _read_offset():
    try:
        return int(open(OFFSET).read().strip())
    except Exception:
        return 0


def _write_offset(n):
    os.makedirs(os.path.dirname(OFFSET), exist_ok=True)
    open(OFFSET, "w").write(str(n))


def process_new(cfg, dry):
    if not os.path.exists(INBOX):
        return 0
    lines = open(INBOX, encoding="utf-8").read().splitlines()
    start = _read_offset()
    n = 0
    for i in range(start, len(lines)):
        if not lines[i].strip():
            continue
        try:
            msg = json.loads(lines[i])
        except Exception:
            continue
        actions = decide(msg, cfg)
        if actions:
            print(f"[{i}] {msg.get('from')} | {msg.get('content','')[:40]}")
            act(actions, msg, dry or not cfg.get("auto_reply", False))
        n += 1
    _write_offset(len(lines))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印决策不调用 API")
    ap.add_argument("--once", action="store_true", help="处理一次即退出")
    ap.add_argument("--poll", type=float, default=2.0)
    a = ap.parse_args()
    cfg = load_cfg()
    mode = "LLM" if (cfg.get("llm_key") and cfg.get("llm_base_url")) else "内置规则"
    print(f"agent_worker 启动: 决策={mode}, auto_reply={cfg.get('auto_reply', False)}, dry_run={a.dry_run}")
    if a.once:
        print(f"处理 {process_new(cfg, a.dry_run)} 条"); return
    while True:
        process_new(cfg, a.dry_run)
        time.sleep(a.poll)


if __name__ == "__main__":
    main()
