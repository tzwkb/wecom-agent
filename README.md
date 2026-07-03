# WeCom Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Codex-blue.svg)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

English | [中文](README_ZH.md)

## Overview

 WeCom local-reading and official API operation Agent Skill for chat decryption, contact/session search, messaging, calendar meetings, and online documents.

## Key Capabilities

- Reads and analyzes local WeCom chat data.
- Uses self-built app APIs for messaging, contacts, calendar, and document operations.
- Keeps a local-agent workflow controlled directly by the user.

## Usage

 Configure local decryption, WeCom app parameters, and available APIs according to README/SKILL.md.

## Notes

 Official API operations depend on trusted domains, IP settings, and application permissions.

## Command and Configuration Reference

The following code blocks keep commands, paths, filenames, and configuration keys literal; explanatory comments are translated for the English README.

```bash
python3 decrypt/read_wecom.py               # one-click: scan key → decrypt → export to decrypt/export/messages.csv|json
python3 decrypt/wecom_local.py stats        # statistics profile (messages, conversation ranking, hourly/daily breakdown)
python3 decrypt/wecom_local.py contacts <name>  # search contacts (name, department, title, phone, email)
python3 decrypt/wecom_local.py search <query>  # full-text message search
python3 decrypt/wecom_local.py conversations|members <conversation>|todo|calendar|media
python3 decrypt/monitor.py --poll 30        # poll for new messages incrementally
python3 decrypt/voice_transcribe.py         # transcribe voice messages (requires pilk + mlx-whisper)
```

```bash
cp config.example.json config.json   # fill credentials (gitignored)
python3 selfcheck.py                  # integration self-check (read-only first)
python3 wecom.py message text '{"touser":"x","content":"hi"}'
python3 wecom.py doc edit '{"docid":"..","requests":[..]}'
```

```
wecom.py                          Track A API CLI (contact/message/doc/schedule/meeting/call)
selfcheck.py                      Track A credential integration self-check
recv_server.py / agent_worker.py  real-time receive path (archived)
decrypt/                          Track B local decryption and reading (core)
  wxwork_crypto.py                wxSQLite3 AES-128-CBC decryption core (+ self-test)
  wecom_paths.py                  automatic profile path detection
  find_key_fast.py + validate.c   live-process memory scan for the 16B key (C accelerated)
  find_key_offline.py             offline fallback key search
  decrypt_wxwork.py               full database decryption
  export_wxwork.py                structured export (real names, types, cards, files, docs)
  monitor.py                      incremental monitor
  wecom_local.py                  local queries (contacts, conversations, search, stats, todo, calendar, media)
  voice_transcribe.py             cached voice SILK→Whisper transcription
  read_wecom.py                   one-click wrapper
  NOTES.md                        decryption investigation timeline
  legacy/                         deprecated explorations (old carve/frida/injection approaches)
docs/                             decryption notes / self-built app setup / IT config request / development plan
```
