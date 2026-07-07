---
name: wecom-agent
description: Use when 处理企业微信/企微/wecom 任务，包括本地聊天记录解密读取、离线搜索导出、媒体/文档定位，以及通过 WecomTeam 官方 CLI/Bot 能力发消息、查通讯录、读写文档、表格、日程、会议、待办。
allowed-tools: Bash
---

# wecom-agent

本 skill 的主线是 **本地解密读取 + WecomTeam 官方操作层**。

| 线 | 默认方案 | 能力边界 |
|---|---|---|
| **B 本地读取** | 本仓库 `decrypt/` | 历史聊天、离线全文搜索、会话/成员/统计、媒体导出、聊天文件定位。默认优先使用。 |
| **A 主动操作** | 本仓库 `online/` + WecomTeam `wecom-cli` | 文档/在线表格/智能表格已封装；发消息、查通讯录、日程、会议、待办仍按企业权限探测。 |
| **实时互动** | WecomTeam Bot SDK（后续接入） | WebSocket 收消息、流式回复、主动推送、文件下载解密。 |

旧的自建应用 HTTP API 方案不再是主线；不要为普通 A 线任务要求用户配置 CorpID/Secret/AgentId、可信域名或可信 IP。

## 决策规则

| 用户需求 | 默认调用 |
|---|---|
| 读/导出/搜索历史聊天、统计会话、找本地聊天文件 | B 本地读取 |
| 读任何聊天消息/历史/近期增量 | B 本地读取 |
| 用户明确要求官方在线接口且本地读取不可用 | 可应急使用 `wecom-cli msg get_message` |
| 发消息、通知某人/群 | `wecom-cli msg ...`；若返回“当前企业暂不支持授权机器人「消息」使用权限”，说明该企业不可用 |
| 查人、找 userid | 优先 B 本地通讯录；A 线可用时用 `wecom-cli contact ...` |
| 读/建/改企业微信文档、表格、智能表格 | 优先用 `online/` 或新增 MCP 工具；写操作先确认 |
| 查/建/改/取消日程 | `wecom-cli schedule ...`；若企业不支持则说明权限边界 |
| 查/建/取消会议 | `wecom-cli meeting ...`；若企业不支持则说明权限边界 |
| 查/建/更新/删除待办 | `wecom-cli todo ...`；写操作先确认 |
| 自动回复/流式回复 | Bot SDK；未接入前说明暂未落地 |

**写操作执行前先向用户确认对象、内容和影响范围。**

## A 主动操作（WecomTeam CLI）

首次使用先检查并初始化：

```bash
wecom-cli --version || npm install -g @wecom/cli
wecom-cli auth show --auth-status
wecom-cli init
```

通用格式：

```bash
wecom-cli <category> <method> '<json参数>'
```

常用入口：

| category | 例子 |
|---|---|
| `doc` | `wecom-cli doc create_doc --json '{"doc_name":"标题","doc_type":3}'` |
| `doc` | `wecom-cli doc edit_doc_content --json '{"docid":"DOCID","content_type":1,"content":"# 标题\\n正文"}'` |
| `todo` | `wecom-cli todo search_todo_userid --json '{"keyword":"姓名"}'` |
| `todo` | `wecom-cli todo get_todo_list --json '{"follower_id":"USERID"}'` |
| `contact` / `msg` / `schedule` / `meeting` | 当前企业实测返回“不支持授权机器人对应权限”；遇到该错误时不要继续重试，直接说明权限边界 |

遇到具体参数不确定时，优先查 `wecom-cli <category> --help` 或 WecomTeam `wecom-unified` references。

## A 在线文档/表格（已封装）

本仓库新增 `online/` 薄封装，底层仍调用 `wecom-cli doc`。写操作全部需要 `confirmed=True`。

```bash
PY=${WECOM_PYTHON:-/opt/homebrew/bin/python3}
$PY -m online.selfcheck
```

| 模块 | 能力 |
|---|---|
| `online.docs` | 创建普通文档、Markdown 覆写正文、创建智能文档 |
| `online.local_docs` | 读取本地已缓存/已下载文档，作为线上读取接口缺失时的 fallback |
| `online.sheets` | 创建在线表格、读取表结构、新增/删除子表、追加行、更新区域 |
| `online.smartsheets` | 创建智能表格、读取子表/字段、管理子表/字段、增删改记录 |

当前 `wecom-cli 0.1.9` 未暴露 `get_doc_content`、`sheet_get_data`、`smartsheet_get_records`。不要承诺读取线上最新版普通文档正文、在线表格单元格数据或智能表格记录列表；只能读取当前 CLI 支持的 metadata、sheet 和 field。本地缓存 fallback 只能读取本机已下载/已打开过的文件，可能不是线上最新版本。

## B 本地读取聊天记录

按系统分流：macOS → `decrypt/macos/`，Windows → `decrypt/windows/`。解密核心 `decrypt/wxwork_crypto.py` 与解析 `decrypt/export_wxwork.py` 两端共用。

### macOS

前提：企业微信运行并登录；首次抓 key 需要已对企微 adhoc 重签，见 `docs/解密思路.md`。

```bash
PY=${WECOM_PYTHON:-/opt/homebrew/bin/python3}
$PY decrypt/macos/read_wecom.py
$PY decrypt/macos/find_key_fast.py
$PY decrypt/macos/decrypt_wxwork.py
$PY decrypt/macos/monitor.py --once
```

本地查询：

```bash
$PY decrypt/macos/wecom_local.py <contacts|conversations|members|search|stats|todo|calendar|media|openfile>
```

| 子命令 | 作用 |
|---|---|
| `contacts [词]` | 本地通讯录搜索 |
| `conversations` | 会话列表 |
| `members <会话>` | 群成员与发言数 |
| `search <词>` | 全文搜索消息 |
| `stats` | 发言/会话/类型/时间统计 |
| `todo` / `calendar` | 本地待办 / 日程 |
| `media [--out]` | 导出明文缓存图片和文件 |
| `openfile <名/词>` | 从聊天记录定位并解析本地文件 |

可选语音转写：

```bash
$PY decrypt/macos/voice_transcribe.py
```

### Windows

前提：企业微信运行并登录，安装 Python 与 `pycryptodome`。

```powershell
powershell -ExecutionPolicy Bypass -File decrypt/windows/run.ps1 <子命令>
powershell -ExecutionPolicy Bypass -File decrypt/windows/run_test.ps1
powershell -ExecutionPolicy Bypass -File decrypt/windows/find_key.ps1
python decrypt/windows/wecom_win.py <key> <子命令>
```

## MCP（可选）

本地读取 MCP 只是 `wecom_local.py --json` 的薄门面。不要为了本地查询强制走 MCP；直接跑 CLI 更透明。

```bash
bash setup.sh
```

本地读取工具：`wecom_contacts/conversations/members/search/stats/todo/calendar/media/openfile`。

本地文档 fallback：

| 工具 | 作用 |
|---|---|
| `wecom_local_doc_read_path` | 按本地路径解析文件，支持 txt/csv/md/json/xlsx/xls/docx/pdf，图片型内容返回 visual 标记 |
| `wecom_local_doc_search` | 按文件名关键词在 WeCom 文件缓存、Downloads、Documents、Desktop 中查找并解析 |

在线工具：

| 工具 | 作用 |
|---|---|
| `wecom_doc_create` / `wecom_doc_write_markdown` | 创建普通文档、覆写 Markdown 正文 |
| `wecom_smartpage_create` | 创建智能文档 |
| `wecom_sheet_create` / `wecom_sheet_info` | 创建在线表格、读取表结构 |
| `wecom_sheet_add_sub` / `wecom_sheet_delete_sub` | 新增/删除在线表格子表 |
| `wecom_sheet_append_row` / `wecom_sheet_update_range` | 追加行、更新区域 |
| `wecom_smartsheet_create` / `wecom_smartsheet_sheets` / `wecom_smartsheet_fields` | 创建智能表格、读取子表/字段 |
| `wecom_smartsheet_add_*` / `update_*` / `delete_*` | 管理智能表格子表、字段、记录 |

## 状态

- **B 本地读取**：已实跑验证，覆盖本地历史聊天、会话、发送者、文本/图片/语音/文件/文档/卡片等解析。
- **A 主动操作**：文档/在线表格/智能表格已通过 `online/` 和 MCP 工具封装；当前企业 `wecom-cli` 授权成功，`todo search_todo_userid/get_todo_list` 可用；`contact/msg/schedule/meeting` 返回企业不支持授权机器人权限。
- **实时互动**：后续接 WecomTeam Bot SDK；旧回调实验代码在 `legacy/self-built-app/`。
