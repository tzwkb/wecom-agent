---
title: Online Sheets
description: Create WeCom sheets, inspect sheet structure, add subsheets, append rows, and update ranges.
---

# Online Sheets

`online.sheets` wraps the WecomTeam document commands for standard online sheets. Structure reads are read-only; creation, deletion, row append, and range update operations require explicit confirmation.

## Create and inspect a sheet

```python
from online.sheets import create_sheet, get_info

created = create_sheet("Weekly Metrics", confirmed=True)
info = get_info(docid="DOC_ID")
```

`create_sheet()` uses document type `4`. `get_info()` reads sheet metadata and subsheet structure, not cell values.

## Add and remove a subsheet

```python
from online.sheets import add_subsheet, delete_subsheet

added = add_subsheet(
    docid="DOC_ID",
    title="Week 28",
    row_count=100,
    column_count=12,
    index=0,
    confirmed=True,
)

deleted = delete_subsheet(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    confirmed=True,
)
```

Deletion is irreversible from the wrapper's point of view. Verify the sheet ID and target document immediately before the call.

## Append a row

Primitive Python values are converted into WeCom cell payloads:

```python
from online.sheets import append_row

append_row(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    values=["Completed", 42, None],
    confirmed=True,
)
```

Numbers become `NUMBER` cells. Other primitive values become `TEXT` cells; `None` becomes an empty string.

## Use typed cells

```python
values = [
    {"type": "text", "text": "Issue"},
    {"type": "number", "number": 17},
    {"type": "formula", "formula": "=SUM(B2:B8)"},
    {
        "type": "link",
        "text": "Repository",
        "url": "https://github.com/tzwkb/wecom-agent",
    },
]
```

Already encoded dictionaries containing `data_type`, `cell_value`, or `cell_format` pass through unchanged.

## Update a range

```python
from online.sheets import update_range

update_range(
    docid="DOC_ID",
    sheet_id="SHEET_ID",
    start_row=1,
    start_column=0,
    rows=[
        ["Owner", "Status", "Count"],
        ["Jackson", "Open", 3],
    ],
    confirmed=True,
)
```

Rows are zero-indexed in the payload fields used by the wrapper. Confirm the starting coordinates and full matrix before writing.

## Current read limitation

The repository's tested `wecom-cli 0.1.9` does not expose `sheet_get_data`. `get_info()` can inspect document and subsheet metadata but cannot return current cell values.
