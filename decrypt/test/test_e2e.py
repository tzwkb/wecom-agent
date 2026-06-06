#!/usr/bin/env python3
"""wecom-agent 解密模块端到端自测 —— macOS(wecom_local)/Windows(wecom_win) 全功能。

跑法: python test_e2e.py [--full]
前提:
  macOS  : 已 read_wecom.py 解密(decrypt/macos/decrypted/ + wxwork_keys.json)
  Windows: 已 run.ps1/解密(Documents\\WXWork\\<id>\\Data 明文缓存 + key)
输出: 逐项 ✓/✗ + 末尾 N/N PASS。对齐 wechat-decrypt/test_e2e.py。9 子命令 + --json。
"""
import sys
import os
import json
import glob
import platform
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # test/ 上一级 = decrypt/
IS_MAC = platform.system() == "Darwin"
FULL = "--full" in sys.argv
PY = sys.executable
results = []


def check(name, fn):
    try:
        ok, d = fn()
    except Exception as e:
        ok, d = False, f"{type(e).__name__}: {e}"
    results.append((name, ok))
    print(f"  {'✓' if ok else '✗'} {name}: {d}")


if IS_MAC:
    LOCAL = os.path.join(HERE, "macos", "wecom_local.py")

    def wl(sub, *a, timeout=180):
        r = subprocess.run([PY, LOCAL, sub, *a], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
else:
    WIN = os.path.join(HERE, "windows", "wecom_win.py")
    _kf = glob.glob(os.path.join(HERE, "**", "wxwork_keys.json"), recursive=True)
    KEY = ""
    if _kf:
        _d = json.load(open(_kf[0]))
        KEY = list(_d.values())[0] if _d else ""

    def wl(sub, *a, timeout=180):
        r = subprocess.run([PY, WIN, KEY, sub, *a], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode


def _last(out, err):
    return out.split("\n")[-1] if out else (err[:80] or "ok")


def t_contacts():
    out, err, rc = wl("contacts")
    return rc == 0, _last(out, err)


def t_contacts_json():
    out, err, rc = wl("contacts", "--json")
    d = json.loads(out)
    return rc == 0 and "contacts" in d, f"{d.get('count')} 人(结构化)"


def t_conversations():
    out, err, rc = wl("conversations")
    return rc == 0, _last(out, err)


def t_conv_json():
    out, err, rc = wl("conversations", "--json")
    d = json.loads(out)
    return rc == 0 and "conversations" in d, f"{d.get('count')} 会话(结构化)"


def t_search():
    out, err, rc = wl("search", "的")
    return rc == 0, _last(out, err)


def t_stats_json():
    out, err, rc = wl("stats", "--json", timeout=300)
    d = json.loads(out)
    return rc == 0 and "total" in d and "by_type" in d, f"{d.get('total')} 条, {len(d.get('by_type', []))} 类型"


def t_todo():
    out, err, rc = wl("todo")
    return rc == 0, _last(out, err)


def t_calendar():
    out, err, rc = wl("calendar")
    return rc == 0, _last(out, err)


def t_openfile():
    out, err, rc = wl("openfile", "试")
    return rc == 0 or "没找到" in (out + err), "ok(查文件类消息)"


def t_media():
    out, err, rc = wl("media", timeout=300)
    return rc == 0, _last(out, err)


def main():
    print(f"=== wecom 解密端到端自测 ({platform.system()}, {'FULL' if FULL else '轻量'}) ===")
    if not IS_MAC and not KEY:
        print("  ✗ Windows 缺 wxwork_keys.json 的 key, 先跑提 key")
    for name, fn in [
        ("contacts", t_contacts), ("contacts --json", t_contacts_json),
        ("conversations", t_conversations), ("conversations --json", t_conv_json),
        ("search", t_search), ("stats --json", t_stats_json),
        ("todo", t_todo), ("calendar", t_calendar), ("openfile", t_openfile),
    ]:
        check(name, fn)
    if FULL:
        check("media 导出", t_media)
    n = sum(1 for _, ok in results if ok)
    print(f"\n{'='*40}\n{n}/{len(results)} PASS" + ("  ✅ 全通过" if n == len(results) else "  ⚠️ 有失败"))
    sys.exit(0 if n == len(results) else 1)


if __name__ == "__main__":
    main()
