---
title: Security and Data Handling
description: Authorization, secret handling, confirmation gates, and freshness rules for WeCom Agent.
---

# Security and Data Handling

WeCom Agent can expose sensitive workplace data. Treat local databases, keys, decrypted exports, cached documents, and online write access as confidential operator-controlled material.

## Authorization scope

Only access a device, WeCom account, enterprise, conversation, or document when the operator is authorized to do so. The local tooling is intended for the user's own signed-in desktop account and data on the current device.

Do not use the project to bypass organizational policy, access another person's account, or collect data outside the operator's approved scope.

## Local secret handling

The repository ignores known key and decrypt outputs, including:

```text
**/wxwork_keys.json
decrypt/**/decrypted/
decrypt/**/export/
*.plain.db
*.db
```

Keep these artifacts local. Do not paste keys, decrypted databases, raw conversations, or authentication tokens into issues, logs, documentation, or commits.

## Online write confirmation

All wrapped online writes call `require_confirmation()`. They fail locally unless the caller supplies `confirmed=True`.

Confirm all three items immediately before a write:

1. The exact target document, sheet, or record set.
2. The exact content or structural change.
3. The expected impact, including replacement or deletion.

Read-only methods such as `get_info()`, `get_sheets()`, and `get_fields()` do not require this flag.

## Target validation

Document helpers require exactly one target identifier:

```python
from online.wecom_cli import target_payload

target_payload(docid="DOC_ID")
target_payload(url="https://doc.weixin.qq.com/...")
```

Passing both or neither raises `ValueError`. This prevents an ambiguous operation from reaching the CLI.

## Freshness labels

`online.local_docs` labels its results as `local-cache-fallback` and records that the local file may be stale compared with the online document. Preserve this warning when displaying or forwarding fallback content.

## Operational logging

`WecomCliError` retains the argument vector, return code, stdout, and stderr for diagnosis. Before sharing an error, remove document URLs, identifiers, user data, and any output that may contain enterprise content.

## Public deployment

Publish only source documentation and generated static documentation assets. Never publish local runtime data, secrets, decrypted outputs, private screenshots, or cached WeCom files.
