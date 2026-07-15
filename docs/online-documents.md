---
title: Online Documents
description: Create WeCom documents, replace Markdown content, and use local cache fallback when online body reads are unavailable.
---

# Online Documents

The `online.docs` module is a thin Python wrapper around authenticated `wecom-cli doc` commands. It creates normal documents, replaces normal document content with Markdown, and creates smart pages.

## Authenticate and inspect support

```bash
npm install -g @wecom/cli
wecom-cli init
wecom-cli auth show --auth-status
python3 -m online.selfcheck
```

An authenticated session can still lack an API category. Treat an enterprise permission error as a capability boundary instead of retrying the same command.

## Create a normal document

```python
from online.docs import create_document

created = create_document("Release Checklist", confirmed=True)
```

`create_document()` sends `create_doc` with `doc_type: 3`.

## Replace document content

Target a document by either `docid` or `url`, never both:

```python
from online.docs import write_document_markdown

updated = write_document_markdown(
    docid="DOC_ID",
    content="# Release Checklist\n\n- Verify build\n- Publish notes",
    confirmed=True,
)
```

The wrapper sends `edit_doc_content` with `content_type: 1`. This is a replacement operation, so confirm the full resulting body before execution.

## Create a smart page

```python
from online.docs import create_smartpage

result = create_smartpage(
    "Project Hub",
    pages=[{"title": "Overview", "content": "Current status"}],
    confirmed=True,
)
```

Set `auto_file=True` only when the installed CLI supports the `+smartpage_create` extension command.

## Local document fallback

The installed `wecom-cli 0.1.9` does not expose online normal-document body reads. `online.local_docs` can inspect files already cached, downloaded, or opened on the current device:

```python
from online.local_docs import read_path, search

one = read_path("~/Downloads/Release Checklist.docx")
matches = search("Release Checklist", max_results=5)
```

Every result identifies itself as `local-cache-fallback` and records that the file may be stale relative to the online document. A missing match means the file was not found in the searched local roots; it does not prove that the online document does not exist.

## Default search roots

When `WECOM_LOCAL_DOC_ROOTS` is unset, the fallback checks the WeCom cache when available and then the user's Downloads, Documents, and Desktop directories. Set custom roots with the platform path separator:

```bash
export WECOM_LOCAL_DOC_ROOTS="$HOME/WorkDocs:$HOME/Downloads"
```
