# WeCom Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Codex-blue.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

English | [中文](README_ZH.md)

WeCom local-decrypt reading plus WecomTeam CLI/Bot operation layer for local chat search, media/file discovery, todos, and online documents/sheets.

## Capabilities

| Track | Capability | Status |
|---|---|---|
| B local reading | Decrypt/export local chats, contacts, conversations, full-text search, stats, media export, local file discovery | Available |
| A online operations | WecomTeam `wecom-cli` wrapper for documents, online sheets, smart sheets, todos, and other supported online APIs | Partially available, permission-dependent |
| Realtime interaction | WecomTeam Bot SDK WebSocket receive/reply path | Planned |

The legacy self-built app HTTP API is no longer the main path. Historical chat reading defaults to local decrypt; online write operations go through WecomTeam `wecom-cli`.

## Local Reading

```bash
PY=/opt/homebrew/bin/python3
$PY decrypt/macos/read_wecom.py
$PY decrypt/macos/wecom_local.py stats
$PY decrypt/macos/wecom_local.py contacts <name>
$PY decrypt/macos/wecom_local.py search <query>
$PY decrypt/macos/wecom_local.py conversations|members <conversation>|todo|calendar|media
$PY decrypt/macos/monitor.py --poll 30
$PY decrypt/macos/voice_transcribe.py
```

## Online Documents And Sheets

```bash
npm install -g @wecom/cli
wecom-cli init
wecom-cli auth show --auth-status

$PY -m online.selfcheck
```

Implemented wrappers:

- `online.docs`: create normal documents, overwrite Markdown content, create smart pages.
- `online.local_docs`: read locally cached/downloaded documents as a fallback when online content APIs are unavailable.
- `online.sheets`: create online sheets, read sheet metadata, add/delete subsheets, append rows, update ranges.
- `online.smartsheets`: create smart sheets, read sheets/fields, manage sheets/fields, add/update/delete records when record IDs are known.

Current `wecom-cli 0.1.9` does not expose `get_doc_content`, `sheet_get_data`, or `smartsheet_get_records`; latest online content reads are therefore marked unsupported by `online.selfcheck`. Local cache fallback can only read files already downloaded or opened on this device.

## MCP

```bash
bash setup.sh
```

MCP keeps local tools (`wecom_contacts`, `wecom_search`, `wecom_openfile`, etc.), adds local document fallback tools (`wecom_local_doc_read_path`, `wecom_local_doc_search`), and adds online tools such as `wecom_doc_create`, `wecom_doc_write_markdown`, `wecom_sheet_append_row`, and `wecom_smartsheet_add_records`. Online write tools require `confirmed=True`.

## Structure

```text
decrypt/                          Track B local decrypt/read core
online/                           Track A WecomTeam CLI wrappers
server.py                         MCP thin facade
legacy/self-built-app/            legacy self-built app experiments
docs/                             design notes, status, and development docs
tests/                            unit tests
```

## Safety

- Read only the user's own device/account.
- Decryption outputs, keys, credentials, and runtime data stay gitignored.
- Every online write operation must confirm target, content, and impact before execution.
