#!/usr/bin/env python3
"""企业微信自建应用「接收消息」回调服务(实时接收) —— 零三方依赖(仅标准库 + cryptography)。

职责: ① GET 验证回调 URL(解密 echostr 原样返回); ② POST 收消息(验签+AES解密 XML),
解析 发送者/类型/正文/会话, **快速 ACK** 并把消息追加到 jobs/inbox.jsonl 供异步 agent 处理
(自主回复/写文档见 agent_worker.py)。5 秒内必须响应, 故重活不在此处做。

配置: 同目录 config.json 的 corpid / recv_token / recv_aeskey。
公网暴露: cloudflared tunnel --url http://localhost:8000 (详见 ../../docs/legacy/自建应用配置教程.md)。
自测(不需真凭证): python3 recv_server.py --selftest
运行:        python3 recv_server.py [--port 8000] [--path /wecom]
"""
import argparse
import base64
import hashlib
import json
import os
import struct
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree as ET

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(HERE, "jobs", "inbox.jsonl")


class WXBizMsgCrypt:
    """移植官方企业微信回调加解密(AES-256-CBC, IV=key[:16], 自定义补位到32; sha1 签名)。"""

    def __init__(self, token, encoding_aeskey, corpid):
        self.token = token
        self.key = base64.b64decode(encoding_aeskey + "=")
        if len(self.key) != 32:
            raise ValueError("EncodingAESKey 解码后须为 32 字节")
        self.corpid = corpid

    def _sign(self, timestamp, nonce, encrypt):
        return hashlib.sha1("".join(sorted([self.token, str(timestamp), str(nonce), encrypt]))
                            .encode()).hexdigest()

    def _decrypt(self, b64text):
        raw = base64.b64decode(b64text)
        d = Cipher(algorithms.AES(self.key), modes.CBC(self.key[:16])).decryptor()
        plain = d.update(raw) + d.finalize()
        plain = plain[:-plain[-1]]                       # 去补位
        content = plain[16:]                             # 去前16随机字节
        xml_len = struct.unpack(">I", content[:4])[0]
        xml = content[4:4 + xml_len]
        from_corp = content[4 + xml_len:].decode("utf-8")
        if from_corp != self.corpid:
            raise ValueError(f"corpid 不匹配: {from_corp}")
        return xml.decode("utf-8")

    def _encrypt(self, xml):
        msg = xml.encode("utf-8")
        text = os.urandom(16) + struct.pack(">I", len(msg)) + msg + self.corpid.encode("utf-8")
        pad = 32 - (len(text) % 32)
        text += bytes([pad]) * pad
        e = Cipher(algorithms.AES(self.key), modes.CBC(self.key[:16])).encryptor()
        return base64.b64encode(e.update(text) + e.finalize()).decode()

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        if self._sign(timestamp, nonce, echostr) != msg_signature:
            raise ValueError("echostr 签名校验失败")
        return self._decrypt(echostr)

    def decrypt_message(self, msg_signature, timestamp, nonce, post_body):
        encrypt = ET.fromstring(post_body).find("Encrypt").text
        if self._sign(timestamp, nonce, encrypt) != msg_signature:
            raise ValueError("消息签名校验失败")
        return self._decrypt(encrypt)

    def encrypt_reply(self, reply_xml, timestamp, nonce):
        enc = self._encrypt(reply_xml)
        sig = self._sign(timestamp, nonce, enc)
        return (f"<xml><Encrypt><![CDATA[{enc}]]></Encrypt>"
                f"<MsgSignature><![CDATA[{sig}]]></MsgSignature>"
                f"<TimeStamp>{timestamp}</TimeStamp>"
                f"<Nonce><![CDATA[{nonce}]]></Nonce></xml>")


def parse_message(xml):
    root = ET.fromstring(xml)
    g = lambda t: (root.findtext(t) or "")
    return {
        "ts": int(time.time()),
        "from": g("FromUserName"),
        "to": g("ToUserName"),
        "agentid": g("AgentID"),
        "msgtype": g("MsgType"),
        "event": g("Event"),
        "content": g("Content"),
        "msgid": g("MsgId"),
        "raw_xml": xml,
    }


def enqueue(msg):
    os.makedirs(os.path.dirname(INBOX), exist_ok=True)
    with open(INBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def make_handler(crypt, path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _q(self):
            return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        def do_GET(self):
            if urlparse(self.path).path != path:
                self.send_response(404); self.end_headers(); return
            q = self._q()
            try:
                echo = crypt.verify_url(q["msg_signature"], q["timestamp"], q["nonce"], q["echostr"])
                body = echo.encode()
                self.send_response(200); self.end_headers(); self.wfile.write(body)
                print(f"[OK] URL 验证通过, 回 echostr")
            except Exception as e:
                self.send_response(400); self.end_headers()
                print(f"[ERR] URL 验证失败: {e}")

        def do_POST(self):
            if urlparse(self.path).path != path:
                self.send_response(404); self.end_headers(); return
            q = self._q()
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            try:
                xml = crypt.decrypt_message(q["msg_signature"], q["timestamp"], q["nonce"], body)
                msg = parse_message(xml)
                enqueue(msg)                              # 入队, 交给 agent_worker 异步处理
                print(f"[MSG] {msg['from']} [{msg['msgtype']}] {msg['content'][:60]}")
                self.send_response(200); self.end_headers()   # 空 200 = 已收, 异步回
            except Exception as e:
                self.send_response(400); self.end_headers()
                print(f"[ERR] 解析消息失败: {e}")
    return H


def _load_cfg():
    p = os.path.join(HERE, "config.json")
    if not os.path.exists(p):
        sys.exit("缺 config.json(填 corpid/recv_token/recv_aeskey), 见 ../../docs/legacy/自建应用配置教程.md")
    c = json.load(open(p))
    for k in ("corpid", "recv_token", "recv_aeskey"):
        if not c.get(k):
            sys.exit(f"config.json 缺 {k}")
    return c


def _selftest():
    token = "testtoken"
    aeskey = base64.b64encode(os.urandom(32)).decode()[:43]   # 43 位 EncodingAESKey
    corpid = "ww1234567890"
    c = WXBizMsgCrypt(token, aeskey, corpid)
    xml = "<xml><FromUserName>zhangsan</FromUserName><MsgType>text</MsgType><Content>你好 agent</Content></xml>"
    ts, nonce = "1700000000", "abc123"
    # 模拟企业微信下发: 加密 + 签名 → 服务端解密还原
    enc = c._encrypt(xml)
    sig = c._sign(ts, nonce, enc)
    body = f"<xml><Encrypt><![CDATA[{enc}]]></Encrypt></xml>"
    got = c.decrypt_message(sig, ts, nonce, body)
    assert got == xml, "解密结果不一致"
    m = parse_message(got)
    assert m["from"] == "zhangsan" and m["content"] == "你好 agent", m
    # echostr 验证回环
    echo_plain = "1234567890123456789"
    echo_enc = c._encrypt(echo_plain)
    echo_sig = c._sign(ts, nonce, echo_enc)
    assert c.verify_url(echo_sig, ts, nonce, echo_enc) == echo_plain
    # 被动回复加密结构
    reply = c.encrypt_reply("<xml><Content>收到</Content></xml>", ts, nonce)
    assert "<Encrypt>" in reply and "<MsgSignature>" in reply
    print("self-test PASS: WXBizMsgCrypt 验签/解密/echostr/回复加密 均正确")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--path", default="/wecom")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest(); return
    cfg = _load_cfg()
    crypt = WXBizMsgCrypt(cfg["recv_token"], cfg["recv_aeskey"], cfg["corpid"])
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), make_handler(crypt, a.path))
    print(f"接收服务启动: http://0.0.0.0:{a.port}{a.path}  (公网用 cloudflared 暴露)")
    print(f"收到的消息 → {INBOX} (由 agent_worker.py 异步处理)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
