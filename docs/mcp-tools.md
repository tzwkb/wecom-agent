---
title: MCP Tools
description: Read-only local tools and confirmation-gated online tools exposed by server.py.
---

# MCP Tools

`server.py` exposes the repository's local and online operations through a thin MCP facade. The MCP layer does not replace the underlying Python and CLI commands; it normalizes inputs and returns text or JSON suitable for an agent client.

## Local read tools

| Tool | Purpose |
|---|---|
| `wecom_contacts` | Search local contact fields by optional keyword |
| `wecom_conversations` | List local conversations with message counts and latest timestamps |
| `wecom_members` | List participants for a matched conversation |
| `wecom_search` | Full-text search across locally exported messages |
| `wecom_stats` | Summarize local message, sender, conversation, type, and time distributions |
| `wecom_todo` | Read locally available todo records |
| `wecom_calendar` | Read locally available calendar records |
| `wecom_media` | Export readable cached media and files |
| `wecom_openfile` | Locate and parse a file referenced by local chat data |

## Local document fallback

| Tool | Purpose |
|---|---|
| `wecom_local_doc_read_path` | Parse one local path and report content or a visual marker |
| `wecom_local_doc_search` | Search configured local roots by filename and parse the newest matches |

Fallback results may be stale compared with the online document.

## Normal documents and sheets

| Tool | Operation | Confirmation |
|---|---|---|
| `wecom_doc_create` | Create a normal document | Required |
| `wecom_doc_write_markdown` | Replace normal document content with Markdown | Required |
| `wecom_smartpage_create` | Create a smart page | Required |
| `wecom_sheet_create` | Create an online sheet | Required |
| `wecom_sheet_info` | Read sheet structure | Not required |
| `wecom_sheet_add_sub` | Add a subsheet | Required |
| `wecom_sheet_delete_sub` | Delete a subsheet | Required |
| `wecom_sheet_append_row` | Append one row | Required |
| `wecom_sheet_update_range` | Update a rectangular cell range | Required |

## Smart sheets

| Tool | Operation | Confirmation |
|---|---|---|
| `wecom_smartsheet_create` | Create a smart-sheet document | Required |
| `wecom_smartsheet_sheets` | Read child sheets | Not required |
| `wecom_smartsheet_add_sheet` | Add a child sheet | Required |
| `wecom_smartsheet_update_sheet` | Rename a child sheet | Required |
| `wecom_smartsheet_delete_sheet` | Delete a child sheet | Required |
| `wecom_smartsheet_fields` | Read fields | Not required |
| `wecom_smartsheet_add_fields` | Add fields | Required |
| `wecom_smartsheet_update_fields` | Update fields | Required |
| `wecom_smartsheet_delete_fields` | Delete fields | Required |
| `wecom_smartsheet_add_records` | Add records | Required |
| `wecom_smartsheet_update_records` | Update known records | Required |
| `wecom_smartsheet_delete_records` | Delete known records | Required |

## Confirmation behavior

Every online write tool accepts `confirmed`. The facade returns a confirmation request when the value is false and calls the underlying module only after it is true. Confirm the target, content, and impact in the current interaction; do not reuse stale approval for a different write.

## Run the server

```bash
python3 server.py
```

On macOS, `bash setup.sh` installs the repository's Python dependencies and registers the server when its supported client command is present. Direct module calls remain available for testing and automation.

## JSON inputs

Complex MCP inputs such as sheet rows, pages, fields, records, and record IDs are accepted as JSON strings. Invalid JSON is rejected before the online call. Review the corresponding Python function in the [API reference](/api-reference) for the underlying payload shape.
