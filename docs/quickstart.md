---
title: Quickstart
description: Install the local dependencies, verify WecomTeam authentication, and run the first safe read.
---

# Quickstart

Start with a read-only local command. Add online operations only after the local path is working and the WecomTeam CLI is authenticated.

## Requirements

- Python 3 on macOS or Windows.
- A running, signed-in WeCom desktop client for local data workflows.
- `pycryptodome` for Windows decryption workflows.
- Node.js and `@wecom/cli` only for online document and sheet operations.

## Clone and verify the project

```bash
git clone https://github.com/tzwkb/wecom-agent.git
cd wecom-agent
python3 -m unittest discover -s tests
```

## Run a local read on macOS

<Steps>
  <Step title="Prepare local data">Follow the repository's macOS key and decrypt procedure for your own signed-in WeCom account.</Step>
  <Step title="Build the local export">Run `python3 decrypt/macos/read_wecom.py`.</Step>
  <Step title="Query the export">Run `python3 decrypt/macos/wecom_local.py stats` or a read-only search command.</Step>
</Steps>

```bash
python3 decrypt/macos/wecom_local.py contacts Jackson
python3 decrypt/macos/wecom_local.py conversations
python3 decrypt/macos/wecom_local.py search quarterly
python3 decrypt/macos/wecom_local.py stats
```

See [local reading](/local-reading) for the full command surface and Windows entry points.

## Enable online operations

Install and authenticate the official WecomTeam CLI:

```bash
npm install -g @wecom/cli
wecom-cli init
wecom-cli auth show --auth-status
python3 -m online.selfcheck
```

The self-check reports both authentication state and command availability. An authenticated session does not guarantee that every API category is permitted by the current enterprise.

## Call a confirmed write

```python
from online.docs import create_document

result = create_document("Operations Notes", confirmed=True)
print(result)
```

Without `confirmed=True`, the wrapper raises `PermissionError` before invoking `wecom-cli`.

## Optional MCP facade

On macOS, `bash setup.sh` installs the Python dependencies used by the repository and registers the local MCP server when a supported client command is available. The underlying commands remain usable directly without MCP.

```bash
python3 server.py
```

Use direct Python or CLI calls when you need the most transparent execution path.
