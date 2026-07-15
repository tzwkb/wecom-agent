---
title: Local Reading
description: Decrypt and query authorized WeCom data on macOS or Windows without depending on online history APIs.
---

# Local Reading

The local track reads data from the operator's own signed-in WeCom desktop installation. It supports historical chat search, contact and conversation views, statistics, media export, and local document discovery.

## Choose the platform entry point

| Platform | Entry point | Shared core |
|---|---|---|
| macOS | `decrypt/macos/` | `decrypt/wxwork_crypto.py` and `decrypt/export_wxwork.py` |
| Windows | `decrypt/windows/` | `decrypt/wxwork_crypto.py` and `decrypt/export_wxwork.py` |

The shared crypto module validates candidate keys before decrypting a database. The platform-specific layer locates the WeCom files and coordinates the workflow.

## macOS workflow

The WeCom desktop client must be running and signed in. The first key-capture setup is documented in `docs/解密思路.md`.

```bash
python3 decrypt/macos/read_wecom.py
python3 decrypt/macos/find_key_fast.py
python3 decrypt/macos/decrypt_wxwork.py
python3 decrypt/macos/monitor.py --once
```

Use `read_wecom.py` for the normal end-to-end path. The narrower scripts are useful when diagnosing an individual phase.

## Query local data

```bash
python3 decrypt/macos/wecom_local.py contacts [keyword]
python3 decrypt/macos/wecom_local.py conversations
python3 decrypt/macos/wecom_local.py members <conversation>
python3 decrypt/macos/wecom_local.py search <keyword>
python3 decrypt/macos/wecom_local.py stats
python3 decrypt/macos/wecom_local.py todo
python3 decrypt/macos/wecom_local.py calendar
python3 decrypt/macos/wecom_local.py media
python3 decrypt/macos/wecom_local.py openfile <name-or-keyword>
```

| Command | Result |
|---|---|
| `contacts` | Local contact fields filtered by an optional keyword |
| `conversations` | Conversation names, message counts, and latest timestamps |
| `members` | Participants ranked by message count for a matched conversation |
| `search` | Message time, conversation, sender, and body matches |
| `stats` | Totals and rankings by sender, conversation, message type, hour, and day |
| `todo` / `calendar` | Locally available todo and calendar records |
| `media` | Copies readable cached images and files into an export directory |
| `openfile` | Locates a chat file and extracts text when the format is supported |

## Windows workflow

Install Python and `pycryptodome`, then use the PowerShell coordinator or the Python reader directly:

```powershell
powershell -ExecutionPolicy Bypass -File decrypt/windows/run.ps1 <command>
powershell -ExecutionPolicy Bypass -File decrypt/windows/run_test.ps1
powershell -ExecutionPolicy Bypass -File decrypt/windows/find_key.ps1
python decrypt/windows/wecom_win.py <key> <command>
```

## Document and media behavior

`openfile` and `decrypt/read_doc.py` support plain text, CSV, Markdown, JSON, Excel workbooks, Word documents, and text-based PDFs when the optional parser dependency is available. Image files and scanned PDFs return a visual marker and path instead of fabricated text.

Optional parsing packages include `openpyxl`, `pdfplumber`, and `python-docx`. Optional voice transcription uses the separate `decrypt/macos/voice_transcribe.py` workflow.

## Data handling

Decrypted databases, key files, exports, and local runtime data are ignored by Git. Keep them on the authorized device and review the [security rules](/security) before sharing diagnostics.
