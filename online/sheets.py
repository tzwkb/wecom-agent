"""Online spreadsheet helpers backed by wecom-cli doc sheet commands."""

from numbers import Number

from .wecom_cli import doc_call, require_confirmation, target_payload


def create_sheet(name, confirmed=False, runner=None):
    require_confirmation(confirmed, "create_sheet")
    return doc_call("create_doc", {"doc_name": name, "doc_type": 4}, runner=runner)


def get_info(docid=None, url=None, runner=None):
    payload = target_payload(docid=docid, url=url)
    return doc_call("sheet_get_info", payload, runner=runner)


def add_subsheet(docid=None, url=None, title="", row_count=100, column_count=20, index=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "add_subsheet")
    payload = target_payload(docid=docid, url=url)
    payload["sheet"] = {"title": title, "row_count": row_count, "column_count": column_count}
    if index is not None:
        payload["index"] = index
    return doc_call("sheet_add_sub", payload, runner=runner)


def delete_subsheet(docid=None, url=None, sheet_id="", confirmed=False, runner=None):
    require_confirmation(confirmed, "delete_subsheet")
    payload = target_payload(docid=docid, url=url)
    payload["sheet_id"] = sheet_id
    return doc_call("sheet_delete_sub", payload, runner=runner)


def append_row(docid=None, url=None, sheet_id="", values=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "append_row")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "row": row_data(values or [])})
    return doc_call("sheet_append_data", payload, runner=runner)


def update_range(docid=None, url=None, sheet_id="", start_row=0, start_column=0, rows=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "update_range")
    payload = target_payload(docid=docid, url=url)
    payload.update(
        {
            "sheet_id": sheet_id,
            "grid_data": {
                "start_row": start_row,
                "start_column": start_column,
                "rows": [row_data(row) for row in (rows or [])],
            },
        }
    )
    return doc_call("sheet_update_range_data", payload, runner=runner)


def row_data(values):
    if isinstance(values, dict) and "values" in values:
        return values
    return {"values": [cell_data(value) for value in values]}


def cell_data(value):
    if isinstance(value, dict):
        if "data_type" in value or "cell_value" in value or "cell_format" in value:
            return value
        kind = value.get("type")
        if kind == "link":
            return {
                "data_type": "LINK",
                "cell_value": {
                    "link": {
                        "text": value.get("text"),
                        "url": value.get("url"),
                        "overwrite": value.get("overwrite", True),
                    }
                },
            }
        if kind == "formula":
            return {"data_type": "FORMUAL", "cell_value": {"formula": value.get("formula")}}
        if kind == "number":
            return {"data_type": "NUMBER", "cell_value": {"number": value.get("number")}}
        if kind == "text":
            return {"data_type": "TEXT", "cell_value": {"text": value.get("text", "")}}
        raise ValueError(f"Unsupported sheet cell dict: {value}")

    if isinstance(value, Number) and not isinstance(value, bool):
        return {"data_type": "NUMBER", "cell_value": {"number": value}}
    return {"data_type": "TEXT", "cell_value": {"text": "" if value is None else str(value)}}

