---
title: Troubleshooting
description: Diagnose missing CLI commands, enterprise permission boundaries, local file fallbacks, and confirmation failures.
---

# Troubleshooting

Start with the narrowest failing layer: repository tests, local WeCom data, WecomTeam authentication, command availability, then enterprise permission.

## Repository tests fail

Run the full standard-library test suite from the repository root:

```bash
python3 -m unittest discover -s tests
```

Install only the optional parser or platform package required by the failing workflow. Core online-wrapper tests inject fake runners and do not need a live WeCom session.

## `wecom-cli` is not found

```bash
npm install -g @wecom/cli
wecom-cli --version
```

Confirm that the npm global binary directory is on `PATH` before running `python3 -m online.selfcheck`.

## Authentication is missing

```bash
wecom-cli init
wecom-cli auth show --auth-status
```

Complete the official authentication flow in the same user environment that runs the Python process.

## The enterprise does not support an API category

Some enterprises reject `contact`, `msg`, `schedule`, or `meeting` permissions even after authentication. Treat the returned permission error as final for that enterprise configuration. Repeating the same request does not expand access.

Use local contacts for identity lookup and the repository's supported document or sheet operations where appropriate.

## An online document body cannot be read

The tested `wecom-cli 0.1.9` does not expose `get_doc_content`. Search a locally cached or downloaded copy instead:

```python
from online.local_docs import search

result = search("document title")
```

A fallback result may be stale. No local match means only that the file is absent from the searched roots.

## Sheet cells or smart-sheet records cannot be listed

The tested CLI does not expose `sheet_get_data` or `smartsheet_get_records`. The wrappers can read standard sheet structure and smart-sheet field metadata, but they cannot verify current cell or record values online.

Do not perform an update unless the target coordinates or record IDs have been verified through another authorized source.

## `PermissionError` requests confirmation

The call is an online write and `confirmed` is false. Review the exact target, content, and impact, then repeat the same intended operation with `confirmed=True`.

Do not set the flag globally or reuse confirmation for a different operation.

## `ValueError: Pass exactly one of docid or url`

Supply one document target:

```python
get_info(docid="DOC_ID")
# or
get_info(url="https://doc.weixin.qq.com/...")
```

Passing both is ambiguous; passing neither leaves no target.

## A local document returns `visual`

The file is an image or a scanned PDF without extractable text. Use an authorized visual inspection or OCR workflow on the returned local path. The reader deliberately does not invent text.

## A local document parser is unavailable

Install the optional package needed by the format:

```bash
python3 -m pip install openpyxl pdfplumber python-docx
```

Keep optional dependencies limited to the formats required by the current task.

## No local chat results appear

Confirm that WeCom is running and signed in, then rebuild the authorized local export before querying it. On macOS, use `decrypt/macos/read_wecom.py`; on Windows, use the provided PowerShell coordinator and validation script.

## Share a safe diagnostic

Include the command name, exit code, sanitized error message, platform, Python version, and `wecom-cli` version. Remove keys, tokens, document URLs, IDs, contact data, message content, decrypted database paths, and enterprise payloads.
