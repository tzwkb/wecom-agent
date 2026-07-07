"""WeCom MCP Server —— 可选薄门面。逻辑在 decrypt/<platform>/wecom_local.py(命令行核心),这里只把工具调用转发过去。

entry 范式与 wechat 对齐:命令行 wecom_local.py 为唯一核心(通用/可测/CI/分发);MCP 是可选层,每工具内部转发。
不要 MCP 也行——直接 `$PY decrypt/macos/wecom_local.py <子命令> [--json]`。
前提:先跑 read_wecom.py 解密(macOS)/ extract+decrypt(Windows)。
"""
import contextlib
import io
import json
import os
import platform
import sqlite3
import sys

from mcp.server.fastmcp import FastMCP
from online import docs as online_docs
from online import local_docs as online_local_docs
from online import sheets as online_sheets
from online import smartsheets as online_smartsheets
from online.wecom_cli import WecomCliError

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


def _json(text, default):
    if not text:
        return default
    return json.loads(text)


def _target(docid, url):
    return {"docid": docid or None, "url": url or None}


def _render(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _online(fn, *args, **kwargs):
    try:
        return _render(fn(*args, **kwargs))
    except (PermissionError, ValueError, json.JSONDecodeError, WecomCliError) as e:
        return str(e)


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


@mcp.tool()
def wecom_local_doc_read_path(path: str, limit: int = 8000) -> str:
    """本地缓存/已下载文档 fallback:按路径读取文件。结果可能不是线上最新版。"""
    return _online(online_local_docs.read_path, path, limit=limit)


@mcp.tool()
def wecom_local_doc_search(keyword: str, roots_json: str = "", max_results: int = 5, limit: int = 8000) -> str:
    """本地缓存/已下载文档 fallback:按文件名关键词搜索并读取。结果可能不是线上最新版。"""
    roots = _json(roots_json, None) if roots_json else None
    return _online(online_local_docs.search, keyword, roots=roots, max_results=max_results, limit=limit)


@mcp.tool()
def wecom_doc_create(title: str, confirmed: bool = False) -> str:
    """在线普通文档:创建文档。写操作,confirmed=True 后执行。"""
    return _online(online_docs.create_document, title, confirmed=confirmed)


@mcp.tool()
def wecom_doc_write_markdown(content: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """在线普通文档:用 Markdown 覆写正文。写操作,confirmed=True 后执行。"""
    return _online(online_docs.write_document_markdown, content=content, confirmed=confirmed, **_target(docid, url))


@mcp.tool()
def wecom_smartpage_create(title: str, pages_json: str, confirmed: bool = False, auto_file: bool = False) -> str:
    """在线智能文档:创建智能文档/智能主页。pages_json 为页面数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_docs.create_smartpage,
        title,
        _json(pages_json, []),
        confirmed=confirmed,
        auto_file=auto_file,
    )


@mcp.tool()
def wecom_sheet_create(title: str, confirmed: bool = False) -> str:
    """在线表格:创建表格。写操作,confirmed=True 后执行。"""
    return _online(online_sheets.create_sheet, title, confirmed=confirmed)


@mcp.tool()
def wecom_sheet_info(docid: str = "", url: str = "") -> str:
    """在线表格:读取表格基本信息和子表结构。"""
    return _online(online_sheets.get_info, **_target(docid, url))


@mcp.tool()
def wecom_sheet_add_sub(
    title: str,
    docid: str = "",
    url: str = "",
    row_count: int = 100,
    column_count: int = 20,
    index: int = 0,
    confirmed: bool = False,
) -> str:
    """在线表格:新增子表。写操作,confirmed=True 后执行。"""
    return _online(
        online_sheets.add_subsheet,
        title=title,
        row_count=row_count,
        column_count=column_count,
        index=index,
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_sheet_delete_sub(sheet_id: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """在线表格:删除子表。写操作,confirmed=True 后执行。"""
    return _online(online_sheets.delete_subsheet, sheet_id=sheet_id, confirmed=confirmed, **_target(docid, url))


@mcp.tool()
def wecom_sheet_append_row(sheet_id: str, values_json: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """在线表格:追加一行。values_json 为单元格数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_sheets.append_row,
        sheet_id=sheet_id,
        values=_json(values_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_sheet_update_range(
    sheet_id: str,
    rows_json: str,
    docid: str = "",
    url: str = "",
    start_row: int = 0,
    start_column: int = 0,
    confirmed: bool = False,
) -> str:
    """在线表格:更新指定区域。rows_json 为二维数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_sheets.update_range,
        sheet_id=sheet_id,
        start_row=start_row,
        start_column=start_column,
        rows=_json(rows_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_create(title: str, confirmed: bool = False) -> str:
    """智能表格:创建智能表格。写操作,confirmed=True 后执行。"""
    return _online(online_smartsheets.create_smartsheet, title, confirmed=confirmed)


@mcp.tool()
def wecom_smartsheet_sheets(docid: str = "", url: str = "") -> str:
    """智能表格:读取子表列表。"""
    return _online(online_smartsheets.get_sheets, **_target(docid, url))


@mcp.tool()
def wecom_smartsheet_add_sheet(docid: str = "", url: str = "", title: str = "", confirmed: bool = False) -> str:
    """智能表格:新增子表。写操作,confirmed=True 后执行。"""
    return _online(online_smartsheets.add_sheet, title=title or None, confirmed=confirmed, **_target(docid, url))


@mcp.tool()
def wecom_smartsheet_update_sheet(sheet_id: str, title: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:重命名子表。写操作,confirmed=True 后执行。"""
    return _online(online_smartsheets.update_sheet, sheet_id=sheet_id, title=title, confirmed=confirmed, **_target(docid, url))


@mcp.tool()
def wecom_smartsheet_delete_sheet(sheet_id: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:删除子表。写操作,confirmed=True 后执行。"""
    return _online(online_smartsheets.delete_sheet, sheet_id=sheet_id, confirmed=confirmed, **_target(docid, url))


@mcp.tool()
def wecom_smartsheet_fields(sheet_id: str, docid: str = "", url: str = "") -> str:
    """智能表格:读取字段列表。"""
    return _online(online_smartsheets.get_fields, sheet_id=sheet_id, **_target(docid, url))


@mcp.tool()
def wecom_smartsheet_add_fields(sheet_id: str, fields_json: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:添加字段。fields_json 为字段数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.add_fields,
        sheet_id=sheet_id,
        fields=_json(fields_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_update_fields(sheet_id: str, fields_json: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:更新字段名。fields_json 为字段数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.update_fields,
        sheet_id=sheet_id,
        fields=_json(fields_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_delete_fields(sheet_id: str, field_ids_json: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:删除字段。field_ids_json 为字段 ID 数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.delete_fields,
        sheet_id=sheet_id,
        field_ids=_json(field_ids_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_add_records(
    sheet_id: str,
    records_json: str,
    docid: str = "",
    url: str = "",
    confirmed: bool = False,
    auto_file: bool = False,
) -> str:
    """智能表格:添加记录。records_json 为记录数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.add_records,
        sheet_id=sheet_id,
        records=_json(records_json, []),
        confirmed=confirmed,
        auto_file=auto_file,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_update_records(
    sheet_id: str,
    records_json: str,
    docid: str = "",
    url: str = "",
    key_type: str = "",
    confirmed: bool = False,
    auto_file: bool = False,
) -> str:
    """智能表格:按 record_id 更新记录。records_json 为记录数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.update_records,
        sheet_id=sheet_id,
        records=_json(records_json, []),
        key_type=key_type or None,
        confirmed=confirmed,
        auto_file=auto_file,
        **_target(docid, url),
    )


@mcp.tool()
def wecom_smartsheet_delete_records(sheet_id: str, record_ids_json: str, docid: str = "", url: str = "", confirmed: bool = False) -> str:
    """智能表格:删除记录。record_ids_json 为记录 ID 数组。写操作,confirmed=True 后执行。"""
    return _online(
        online_smartsheets.delete_records,
        sheet_id=sheet_id,
        record_ids=_json(record_ids_json, []),
        confirmed=confirmed,
        **_target(docid, url),
    )


if __name__ == "__main__":
    mcp.run()
