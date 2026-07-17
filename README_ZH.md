# WeCom Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Codex-blue.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

[Documentation](https://wecom-agent.readthedocs.io/en/latest/) | [English](README.md) | 中文

**Agent Skill** — 企业微信本地解密读取 + WecomTeam 官方 CLI/Bot 操作助手，支持历史聊天读取、通讯录/会话搜索、媒体/文档定位、待办和在线文档/表格流程。

## 能力

| 线 | 能力 | 状态 |
|---|---|---|
| **B 本地读取** | 解密导出聊天记录、增量监控、通讯录/会话/全文搜索/统计画像、语音转写、媒体导出 | 已可用 |
| **A 在线操作** | 通过 WecomTeam `wecom-cli` 操作文档、在线表格、智能表格、待办等在线 API | 分模块可用，受企业权限限制 |
| **实时互动** | WecomTeam Bot SDK WebSocket 收消息、回复、推送 | 后续接入 |

旧自建应用 HTTP API 不再是主线。历史聊天读取默认走本地解密；在线写操作默认复用 WecomTeam `wecom-cli`。

## 快速开始：本地读取

前提：企业微信已登录；首次抓 key 需要按 `docs/解密思路.md` 处理 macOS 签名限制。

```bash
PY=/opt/homebrew/bin/python3
$PY decrypt/macos/read_wecom.py
$PY decrypt/macos/wecom_local.py stats
$PY decrypt/macos/wecom_local.py contacts 张
$PY decrypt/macos/wecom_local.py search 报价
$PY decrypt/macos/wecom_local.py conversations|members <会话>|todo|calendar|media
$PY decrypt/macos/monitor.py --poll 30
$PY decrypt/macos/voice_transcribe.py
```

## 在线文档和表格

```bash
npm install -g @wecom/cli
wecom-cli init
wecom-cli auth show --auth-status

$PY -m online.selfcheck
```

已实现封装：

- `online.docs`：创建普通文档、Markdown 覆写正文、创建智能文档。
- `online.local_docs`：读取本地已缓存/已下载的文档，作为 `get_doc_content` 缺失时的 fallback。
- `online.sheets`：创建在线表格、读取表结构、新增/删除子表、追加行、更新区域。
- `online.smartsheets`：创建智能表格、读取子表/字段、管理子表/字段、在已知 `record_id` 时增删改记录。

当前 `wecom-cli 0.1.9` 未暴露 `get_doc_content`、`sheet_get_data`、`smartsheet_get_records`，所以线上最新版内容读取仍标为不支持；本地缓存 fallback 只能读取本机已下载/已打开过的文件。

## MCP

```bash
bash setup.sh
```

MCP 保留本地读取工具：`wecom_contacts/conversations/members/search/stats/todo/calendar/media/openfile`，并新增 `wecom_local_doc_read_path`、`wecom_local_doc_search` 读取本地缓存/下载文档。

新增在线工具：`wecom_doc_create`、`wecom_doc_write_markdown`、`wecom_sheet_create`、`wecom_sheet_info`、`wecom_sheet_append_row`、`wecom_sheet_update_range`、`wecom_smartsheet_create`、`wecom_smartsheet_fields`、`wecom_smartsheet_add_records` 等。所有线上写操作必须传 `confirmed=True`。

## 结构

```text
decrypt/                          B 线本地解密读取核心
online/                           A 线 WecomTeam CLI 薄封装
server.py                         MCP 薄门面
legacy/self-built-app/            旧自建应用实验代码
docs/                             设计、状态和开发文档
tests/                            单元测试
```

## 隐私与安全

- 仅读本人设备本人账号。
- 解密产物、密钥、凭证和运行时数据均 `.gitignore`，不入库。
- 任何线上写操作必须先确认对象、内容和影响范围。
