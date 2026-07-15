---
title: Smart Sheets
description: Manage smart-sheet containers, fields, and records through confirmed WecomTeam CLI operations.
---

# Smart Sheets

`online.smartsheets` covers the smart-sheet operations currently exposed by the WecomTeam CLI: create a document, inspect sheets and fields, manage schema, and add, update, or delete records.

## Create and inspect

```python
from online.smartsheets import create_smartsheet, get_fields, get_sheets

created = create_smartsheet("Localization Tracker", confirmed=True)
sheets = get_sheets(docid="DOC_ID")
fields = get_fields(docid="DOC_ID", sheet_id="SHEET_ID")
```

`get_sheets()` and `get_fields()` are read-only. Creating a smart sheet uses document type `10`.

## Manage child sheets

```python
from online.smartsheets import add_sheet, delete_sheet, update_sheet

added = add_sheet(docid="DOC_ID", title="Backlog", confirmed=True)
renamed = update_sheet(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    title="Ready",
    confirmed=True,
)
removed = delete_sheet(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    confirmed=True,
)
```

## Manage fields

Field payloads are passed to the CLI without inventing a schema. Build them from the installed command's schema output:

```bash
wecom-cli doc smartsheet_add_fields --schema
```

```python
from online.smartsheets import add_fields, delete_fields, update_fields

add_fields(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    fields=[{"field_title": "Status", "field_type": "TEXT"}],
    confirmed=True,
)

update_fields(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    fields=[{"field_id": "FIELD_ID", "field_title": "Workflow Status"}],
    confirmed=True,
)

delete_fields(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    field_ids=["FIELD_ID"],
    confirmed=True,
)
```

## Manage records

```python
from online.smartsheets import add_records, delete_records, update_records

add_records(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    records=[{"values": {"Status": "Ready"}}],
    confirmed=True,
)

update_records(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    records=[{"record_id": "RECORD_ID", "values": {"Status": "Done"}}],
    key_type="FIELD_TITLE",
    confirmed=True,
)

delete_records(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    record_ids=["RECORD_ID"],
    confirmed=True,
)
```

Set `auto_file=True` for add or update only when the installed CLI supports the corresponding `+smartsheet_*_auto_file` extension command.

## Current read limitation

The repository's tested `wecom-cli 0.1.9` does not expose `smartsheet_get_records`. The wrapper can inspect sheets and fields, but it cannot list current records before an update. Record mutations therefore require known record IDs and a separately verified payload.
