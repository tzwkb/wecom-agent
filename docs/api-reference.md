---
title: Python API Reference
description: Public helpers for WecomTeam CLI calls, documents, standard sheets, smart sheets, and local document access.
---

# Python API Reference

The public modules expose small functions that are directly testable with injected runners. Online writes require `confirmed=True`; read-only metadata calls do not.

## CLI foundation

### `WecomCliError`

```python
class WecomCliError(RuntimeError)
```

Raised when a `wecom-cli` subprocess exits with a nonzero status. The instance retains `argv`, `returncode`, `stdout`, and `stderr`.

### `run_json`

```python
run_json(args, payload=None, timeout=60, cli="wecom-cli", run=subprocess.run)
```

Runs a CLI command, serializes an optional payload after `--json`, and parses JSON stdout. Empty stdout returns `{}`; non-JSON stdout is returned as text.

### `run_text`

```python
run_text(args, timeout=30, cli="wecom-cli", run=subprocess.run)
```

Runs a CLI command and returns stripped text stdout. Raises `WecomCliError` on a nonzero exit.

### `require_confirmation`

```python
require_confirmation(confirmed, action)
```

Raises `PermissionError` when `confirmed` is false. Every wrapped online write calls this function before invoking the CLI.

### `target_payload`

```python
target_payload(docid=None, url=None)
```

Returns either `{"docid": ...}` or `{"url": ...}`. Exactly one argument must be present; otherwise the function raises `ValueError`.

### `doc_call`

```python
doc_call(command, payload=None, runner=None)
```

Dispatches `wecom-cli doc <command>` through `run_json` or an injected runner.

### `auth_status`

```python
auth_status(runner=None)
```

Returns the output of `wecom-cli auth show --auth-status`.

### `version`

```python
version(runner=None)
```

Returns the installed `wecom-cli --version` output.

### `doc_command_supported`

```python
doc_command_supported(command, runner=None)
```

Checks a document command with `--schema`. Returns `False` when the command raises `WecomCliError` and `True` otherwise.

## Normal documents

### `create_document`

```python
create_document(name, confirmed=False, runner=None)
```

Creates a normal document through `create_doc` with document type `3`.

### `write_document_markdown`

```python
write_document_markdown(
    docid=None,
    url=None,
    content="",
    confirmed=False,
    runner=None,
)
```

Replaces a normal document body with Markdown through `edit_doc_content` and `content_type: 1`.

### `create_smartpage`

```python
create_smartpage(title, pages, confirmed=False, auto_file=False, runner=None)
```

Creates a smart page. `auto_file=True` selects the optional `+smartpage_create` CLI extension.

## Local document fallback

### `read_path`

```python
read_path(path, limit=8000)
```

Reads one local file and returns a structured result with source, freshness, path, file metadata, status, and either text content or a visual marker.

### `search`

```python
search(keyword, roots=None, max_results=5, limit=8000)
```

Finds matching local filenames, reads the newest matches, and labels the result as a potentially stale local-cache fallback. An empty keyword raises `ValueError`.

### `find_files`

```python
find_files(keyword, roots=None, max_results=5)
```

Returns supported local paths whose names contain the case-insensitive keyword, sorted by modification time descending.

### `default_roots`

```python
default_roots()
```

Returns roots from `WECOM_LOCAL_DOC_ROOTS` when configured. Otherwise it includes the available WeCom file cache and the user's Downloads, Documents, and Desktop directories.

## Standard online sheets

### `create_sheet`

```python
create_sheet(name, confirmed=False, runner=None)
```

Creates an online sheet through `create_doc` with document type `4`.

### `get_info`

```python
get_info(docid=None, url=None, runner=None)
```

Reads standard sheet metadata and subsheet structure with `sheet_get_info`.

### `add_subsheet`

```python
add_subsheet(
    docid=None,
    url=None,
    title="",
    row_count=100,
    column_count=20,
    index=None,
    confirmed=False,
    runner=None,
)
```

Adds a child sheet with an explicit title and dimensions. The optional index controls its position.

### `delete_subsheet`

```python
delete_subsheet(docid=None, url=None, sheet_id="", confirmed=False, runner=None)
```

Deletes the specified child sheet with `sheet_delete_sub`.

### `append_row`

```python
append_row(
    docid=None,
    url=None,
    sheet_id="",
    values=None,
    confirmed=False,
    runner=None,
)
```

Converts a sequence with `row_data()` and appends it through `sheet_append_data`.

### `update_range`

```python
update_range(
    docid=None,
    url=None,
    sheet_id="",
    start_row=0,
    start_column=0,
    rows=None,
    confirmed=False,
    runner=None,
)
```

Writes a two-dimensional matrix beginning at the supplied zero-based row and column.

### `row_data`

```python
row_data(values)
```

Returns an existing `{"values": ...}` row unchanged or converts a sequence into a WeCom row payload.

### `cell_data`

```python
cell_data(value)
```

Converts Python numbers, text, `None`, links, formulas, and explicitly typed dictionaries into WeCom cell payloads. Unsupported typed dictionaries raise `ValueError`.

## Smart sheets

### `create_smartsheet`

```python
create_smartsheet(name, confirmed=False, runner=None)
```

Creates a smart-sheet document through `create_doc` with document type `10`.

### `get_sheets`

```python
get_sheets(docid=None, url=None, runner=None)
```

Returns child-sheet metadata through `smartsheet_get_sheet`.

### `add_sheet`

```python
add_sheet(docid=None, url=None, title=None, confirmed=False, runner=None)
```

Adds a child sheet. When a title is supplied, it is sent inside `properties`.

### `update_sheet`

```python
update_sheet(
    docid=None,
    url=None,
    sheet_id="",
    title="",
    confirmed=False,
    runner=None,
)
```

Renames a child sheet by sending its ID and new title in `properties`.

### `delete_sheet`

```python
delete_sheet(docid=None, url=None, sheet_id="", confirmed=False, runner=None)
```

Deletes a smart-sheet child sheet.

### `get_fields`

```python
get_fields(docid=None, url=None, sheet_id="", runner=None)
```

Returns field metadata for a child sheet through `smartsheet_get_fields`.

### `add_fields`

```python
add_fields(
    docid=None,
    url=None,
    sheet_id="",
    fields=None,
    confirmed=False,
    runner=None,
)
```

Adds the supplied field payloads to a child sheet.

### `update_fields`

```python
update_fields(
    docid=None,
    url=None,
    sheet_id="",
    fields=None,
    confirmed=False,
    runner=None,
)
```

Updates the supplied field payloads for a child sheet.

### `delete_fields`

```python
delete_fields(
    docid=None,
    url=None,
    sheet_id="",
    field_ids=None,
    confirmed=False,
    runner=None,
)
```

Deletes the listed field IDs from a child sheet.

### `add_records`

```python
add_records(
    docid=None,
    url=None,
    sheet_id="",
    records=None,
    confirmed=False,
    auto_file=False,
    runner=None,
)
```

Adds records. `auto_file=True` selects `+smartsheet_add_records_auto_file` when that CLI extension is installed.

### `update_records`

```python
update_records(
    docid=None,
    url=None,
    sheet_id="",
    records=None,
    key_type=None,
    confirmed=False,
    auto_file=False,
    runner=None,
)
```

Updates known records and optionally sends `key_type`. `auto_file=True` selects the corresponding extension command.

### `delete_records`

```python
delete_records(
    docid=None,
    url=None,
    sheet_id="",
    record_ids=None,
    confirmed=False,
    runner=None,
)
```

Deletes the listed known record IDs.

## Local file utilities

### `read_file`

```python
read_file(path, limit=8000)
```

Reads supported text, workbook, Word, PDF, and image paths. It returns diagnostic text for missing paths or unavailable optional parsers and returns a visual marker for image-only content.

### `copy_unique`

```python
copy_unique(src, dst_dir)
```

Copies a media file into a destination directory without overwriting an existing same-name file.

## Testability

Online helpers accept an optional `runner`. Unit tests use this seam to inspect the exact command and payload without contacting WeCom. Run the repository suite with:

```bash
python3 -m unittest discover -s tests
```
