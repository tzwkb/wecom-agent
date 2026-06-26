#!/usr/bin/env python3
"""企业微信 Windows 版 · 端到端测试 —— 跑全部命令, 逐个校验, 报告写到桌面。
用法: python test_e2e.py <key_hex> [报告日期]
"""
import contextlib
import io
import os
import sys
import time

_H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_H, os.path.dirname(_H)]
import wecom_win as W

key = bytes.fromhex(sys.argv[1].strip())
stamp = sys.argv[2] if len(sys.argv) > 2 else ""

TESTS = [
    ("read", [], ["条", "messages.json"]),
    ("contacts", ["张"], ["张三"]),
    ("conversations", [], ["个会话"]),
    ("members", ["测试项目组"], ["成员"]),
    ("search", ["解耦"], ["命中"]),
    ("stats", [], ["发言最多"]),
    ("todo", [], ["待办"]),
    ("calendar", [], ["日程"]),
    ("media", [], ["媒体文件"]),
    ("openfile", ["zhangsan"], ["📄"]),
    ("voice", [], ["缓存语音"]),
    ("monitor", [], ["消息"]),
]


def run(cmd, args, must):
    buf = io.StringIO()
    ok, t0 = False, time.time()
    try:
        with contextlib.redirect_stdout(buf):
            W.CMDS[cmd](key, args)
        out = buf.getvalue()
        ok = all(m in out for m in must) if must else bool(out.strip())
        lines = [l for l in out.splitlines() if l.strip()]
        note = (lines[-1] if lines else "(无输出)")[:72]
    except SystemExit as e:
        note = f"SystemExit: {e}"
    except Exception as e:
        note = f"{type(e).__name__}: {e}"
    return {"cmd": (cmd + " " + " ".join(args)).strip(), "ok": ok,
            "ms": int((time.time() - t0) * 1000), "note": note}


results = [run(c, a, m) for c, a, m in TESTS]
npass = sum(r["ok"] for r in results)

L = ["# 企业微信 Windows 版 · 端到端测试报告", ""]
if stamp:
    L.append(f"> 时间：{stamp}")
L += [
    f"> 环境：UTM Win11 ARM · 全程在 VM 上跑（抓 key → 解密 → 各命令）。",
    f"> 解密核心 `wxwork_crypto` / 解析 `export_wxwork` / `read_doc` 与 macOS 共用、零改。",
    "",
    f"## 结果：**{npass}/{len(TESTS)} 通过**",
    "",
    "| # | 命令 | 结果 | 耗时 | 输出样本 |",
    "|---|---|---|---|---|",
]
for i, r in enumerate(results, 1):
    L.append(f"| {i} | `{r['cmd']}` | {'✅' if r['ok'] else '❌'} | {r['ms']}ms | {r['note']} |")
L += [
    "",
    "## 覆盖能力",
    "- **读取**：read（全量消息，含真名/会话名/类型）",
    "- **查询**：contacts / conversations / members / search / stats（全部名字解析）",
    "- **事务**：todo（待办）/ calendar（日程）",
    "- **媒体**：media（明文缓存图片+文件导出）/ openfile（按名定位文档→解析 xlsx/pdf/docx/文本）",
    "- **语音**：voice（定位 SILK；转写需 faster-whisper）",
    "- **增量**：monitor（水位增量取新消息）",
    "",
    "## 名字解析",
    "`user.db.user_table`(uid→名/手机/邮箱) + `session.db.conversation_table`(会话→名)；1:1 取对方。",
]
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
out = os.path.join(desktop, "wecom_windows_端到端测试报告.md")
open(out, "w", encoding="utf-8").write("\n".join(L))

print(f"\n{'=' * 52}")
print(f"  {npass}/{len(TESTS)} 通过  →  {out}")
print('=' * 52)
for r in results:
    print(f"  {'✅' if r['ok'] else '❌'} {r['cmd']:<24} {r['ms']:>5}ms  {r['note'][:46]}")
