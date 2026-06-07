"""WeCom MCP Server —— 可选薄门面。逻辑在 decrypt/<platform>/wecom_local.py(命令行核心),这里只把工具调用转发过去。

entry 范式与 wechat 对齐:命令行 wecom_local.py 为唯一核心(通用/可测/CI/分发);MCP 是可选层,每工具内部转发。
不要 MCP 也行——直接 `python3 decrypt/macos/wecom_local.py <子命令> [--json]`。
前提:先跑 read_wecom.py 解密(macOS)/ extract+decrypt(Windows)。
"""
import contextlib
import io
import os
import platform
import sqlite3
import sys

from mcp.server.fastmcp import FastMCP

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLAT = "windows" if platform.system() == "Windows" else "macos"
sys.path.insert(0, os.path.join(_HERE, "decrypt", _PLAT))

if _PLAT == "windows":
    import wecom_win as L  # CMDS[cmd](key, args)
else:
    import wecom_local as L  # CMDS[cmd](args, js=False)


def _win_key():
    p = os.path.join(_HERE, "decrypt", "windows", "key.txt")
    if not os.path.exists(p):
        raise SystemExit("缺 key.txt(Windows),先跑 extract_raw_key + decrypt")
    return bytes.fromhex(open(p).read().strip())


def _call(cmd, args):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            if _PLAT == "windows":
                L.CMDS[cmd](_win_key(), args)
            else:
                L.CMDS[cmd](args)
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return "解密 OK,但核心表缺失 → 数据未同步(可能新登录)。先打开企业微信浏览消息,等同步后重试。"
        raise
    except SystemExit as e:
        return (buf.getvalue() + f"\n{e}").strip()
    return buf.getvalue().strip() or "(无输出)"


mcp = FastMCP(
    "wecom",
    instructions=(
        "企业微信本地聊天记录读取与分析(已解密的明文库,全本地无网络)。"
        "查通讯录、会话、成员、全文搜索、统计、待办、日程、媒体导出、文档解析。"
    ),
)


@mcp.tool()
def wecom_contacts(keyword: str = "") -> str:
    """通讯录(姓名/部门/职位/手机/邮箱),keyword 可按词过滤。"""
    return _call("contacts", [keyword] if keyword else [])


@mcp.tool()
def wecom_conversations() -> str:
    """会话列表(名称/消息数/最后时间)。"""
    return _call("conversations", [])


@mcp.tool()
def wecom_members(conversation: str) -> str:
    """某会话的参与者(按发言数)。conversation=会话名或 ID(模糊匹配)。"""
    return _call("members", [conversation])


@mcp.tool()
def wecom_search(keyword: str) -> str:
    """全文搜索消息(时间/会话/发送者/正文)。"""
    return _call("search", [keyword])


@mcp.tool()
def wecom_stats() -> str:
    """统计:总量/发言排行/会话排行/类型/按小时/按天。"""
    return _call("stats", [])


@mcp.tool()
def wecom_todo() -> str:
    """待办(内容/状态/创建者/提醒)。"""
    return _call("todo", [])


@mcp.tool()
def wecom_calendar() -> str:
    """日程(开始/结束/标题)。"""
    return _call("calendar", [])


@mcp.tool()
def wecom_media() -> str:
    """导出明文缓存的图片+文件(按原名)到 export/media。"""
    return _call("media", [])


@mcp.tool()
def wecom_openfile(keyword: str) -> str:
    """聊天里找文档→定位本体→文本解析(txt/csv/md/xlsx/docx/文本PDF)。图片型/扫描PDF 返回 🖼️VISUAL 路径,用 Read 多模态看。"""
    return _call("openfile", [keyword])


if __name__ == "__main__":
    mcp.run()
