# WeCom Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Codex-blue.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

[English](README.md) | 中文

**Agent Skill** — 企业微信本地解密读取 + WecomTeam 官方 CLI/Bot 操作助手，支持历史聊天读取、通讯录/会话搜索、发消息、日程会议、待办和在线文档流程。


让本地 agent **读取、分析、(配置后)操作**企业微信。macOS 已验证。

## 能力

| 线 | 能力 | 状态 |
|---|---|---|
| **B 本地读取** | 解密导出聊天记录、增量监控、通讯录/会话/全文搜索/统计画像、语音转写、媒体导出 | ✅ 已可用 |
| **A 主动操作** | 发消息、查通讯录、读写编辑在线文档/表格、日程、会议、待办 | ✅ 采用 WecomTeam `wecom-cli/wecom-unified` |

> 自建应用 HTTP API 方案已砍掉主线：不再要求 CorpID/Secret/AgentId、可信域名或可信 IP。旧实验代码已移到 `legacy/self-built-app/`。

## 快速开始（B 本地读取）

前提：企业微信已登录 + 已对企微做 adhoc 重签（去 hardened runtime，见 `docs/解密思路.md`）。

```bash
PY=/opt/homebrew/bin/python3                      # 或 setup.sh 输出的 Python
$PY decrypt/macos/read_wecom.py                   # 一键: 扫key→解密→导出
$PY decrypt/macos/wecom_local.py stats            # 统计画像(发言/会话排行、按小时/天)
$PY decrypt/macos/wecom_local.py contacts 张      # 查通讯录(姓名/部门/职位/手机/邮箱)
$PY decrypt/macos/wecom_local.py search 报价      # 全文搜索消息
$PY decrypt/macos/wecom_local.py conversations|members <会话>|todo|calendar|media
$PY decrypt/macos/monitor.py --poll 30            # 增量盯新消息
$PY decrypt/macos/voice_transcribe.py             # 语音转文字(需 pilk + mlx-whisper)
```

key 首次需企微在跑、登录态（活进程内存扫 16B key，只读不注入）；之后存盘复用，无需再扫。

## A 主动操作（WecomTeam CLI）

主动操作直接复用 WecomTeam 官方 `wecom-cli/wecom-unified`，不走本仓库旧自建应用方案。实际可用范围取决于企业是否开放授权机器人对应权限。

```bash
npm install -g @wecom/cli
wecom-cli auth show --auth-status
wecom-cli init

wecom-cli todo search_todo_userid --json '{"keyword":"姓名"}'
wecom-cli todo get_todo_list --json '{"follower_id":"USERID"}'
wecom-cli doc create_doc --json '{"doc_name":"标题","doc_type":3}'
wecom-cli doc edit_doc_content --json '{"docid":"DOCID","content_type":1,"content":"# 标题\n正文"}'
```

消息读取全部默认走 B 线本地解密；`wecom-cli msg get_message` 不作为常规 fallback，仅在用户明确要求官方在线接口且本地读取不可用时应急使用。

当前企业实测：`wecom-cli init` 授权成功；`todo search_todo_userid/get_todo_list` 可用；`contact/msg/schedule/meeting` 返回“不支持授权机器人对应权限”；文档写入需用户确认后测试。

## 结构

```
legacy/self-built-app/            旧自建应用 API/回调实验代码（非主线）
decrypt/                          B线 本地解密读取(核心)
  wxwork_crypto.py                wxSQLite3 AES-128-CBC 解密核心(+自测)
  export_wxwork.py                结构化导出(真名/类型/卡片/文件/文档)
  media_export.py                 媒体导出 helper(避免同名覆盖)
  macos/                          macOS 抓 key/解密/查询/增量/语音入口
  windows/                        Windows 抓 key/本地读取入口
  e2e/                            解密链路端到端检查
docs/                             解密思路 / 开发计划 / legacy 自建应用历史文档
```

## 隐私与安全

- **仅读本人设备本人账号。** 解密产物（`decrypt/**/decrypted/`、`decrypt/**/export/`、`jobs/`）、历史自建应用凭证 `config.json`、密钥 `wxwork_keys.json` 均 `.gitignore`，不入库。
- B 线需对企微 adhoc 重签（破坏性；日常使用建议重装恢复原签名）。
- 路径自动探测，不硬编码用户名/profile。
- 依赖：B 核心仅 `cryptography`；`find_key_fast` 首次自动用 `clang` 编译 `validate.c`（需 Xcode 命令行工具）。文档解析(`openfile`)可选 `openpyxl`/`pdfplumber`/`python-docx`/`xlrd`；语音 `pilk`+`mlx-whisper`（Apple Silicon）。缺可选库自动降级提示。

## 原理

消息库 = wxSQLite3 AES-128-CBC（非 SQLCipher）。key 仅在登录后进程内存，读出后离线解密。详见 [`docs/解密思路.md`](docs/解密思路.md)。
