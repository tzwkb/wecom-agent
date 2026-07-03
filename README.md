# WeCom Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Codex-blue.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

English | [中文](README_ZH.md)

## Overview

 WeCom local-reading Agent Skill plus WecomTeam official CLI/Bot operation layer for chat decryption, contact/session search, messaging, documents, sheets, schedules, meetings, and todos.

## Key Capabilities

- Reads and analyzes local WeCom chat data.
- Uses WecomTeam `wecom-cli/wecom-unified` for active WeCom operations.
- Keeps a local-agent workflow controlled directly by the user.
- Keeps local decryption as the default path for historical chat reading.

## Usage

 Configure local decryption according to README/SKILL.md. For active operations, install and initialize WecomTeam `wecom-cli`.

## Status

 This repository is maintained or used according to the current README notes.

## Notes

 The self-built app HTTP API path is no longer the main plan. Historical chat reading stays local; WecomTeam CLI/Bot handles active operations.

## Command and Configuration Reference

The following code blocks keep commands, paths, filenames, and configuration keys literal; explanatory comments are translated for the English README.

```bash
PY=/opt/homebrew/bin/python3                      # or the Python printed by setup.sh
$PY decrypt/macos/read_wecom.py                   # one-click: scan key → decrypt → export
$PY decrypt/macos/wecom_local.py stats            # statistics profile
$PY decrypt/macos/wecom_local.py contacts <name>  # search local contacts
$PY decrypt/macos/wecom_local.py search <query>   # full-text local message search
$PY decrypt/macos/wecom_local.py conversations|members <conversation>|todo|calendar|media
$PY decrypt/macos/monitor.py --poll 30            # poll for new local messages incrementally
$PY decrypt/macos/voice_transcribe.py             # transcribe voice messages (requires pilk + mlx-whisper)
```

```bash
npm install -g @wecom/cli
wecom-cli auth show --auth-status
wecom-cli init
wecom-cli todo search_todo_userid --json '{"keyword":"name"}'
wecom-cli todo get_todo_list --json '{"follower_id":"USERID"}'
wecom-cli doc create_doc --json '{"doc_name":"Title","doc_type":3}'
wecom-cli doc edit_doc_content --json '{"docid":"DOCID","content_type":1,"content":"# Title\nBody"}'
```

Message reading defaults to the local decryption path. `wecom-cli msg get_message` is not a normal fallback; use it only when the user explicitly asks for the official online API and local reading is unavailable.

Current enterprise test result: `wecom-cli init` authorizes successfully; `todo search_todo_userid/get_todo_list` works; `contact/msg/schedule/meeting` return enterprise-level unsupported-permission errors; document writes require explicit user confirmation before testing.

```
legacy/self-built-app/            legacy self-built app API/callback experiments
decrypt/                          Track B local decryption and reading (core)
  wxwork_crypto.py                wxSQLite3 AES-128-CBC decryption core (+ self-test)
  export_wxwork.py                structured export (real names, types, cards, files, docs)
  media_export.py                 media export helper without same-name overwrite
  macos/                          macOS key scan, decrypt, query, monitor, voice entry points
  windows/                        Windows key scan and local-reading entry points
  e2e/                            end-to-end checks
docs/                             decryption notes / development plan / legacy self-built app notes
```

## Detailed Technical Notes

The primary README keeps the original technical details, history notes, full commands, and file layout. This file maintains the English version of the core documentation; consult the primary README code blocks and paths when exact commands are needed.
