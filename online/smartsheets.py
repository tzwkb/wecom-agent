"""Smart sheet helpers backed by wecom-cli doc smartsheet commands."""

from .wecom_cli import doc_call, require_confirmation, target_payload


def create_smartsheet(name, confirmed=False, runner=None):
    require_confirmation(confirmed, "create_smartsheet")
    return doc_call("create_doc", {"doc_name": name, "doc_type": 10}, runner=runner)


def get_sheets(docid=None, url=None, runner=None):
    return doc_call("smartsheet_get_sheet", target_payload(docid=docid, url=url), runner=runner)


def add_sheet(docid=None, url=None, title=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "add_sheet")
    payload = target_payload(docid=docid, url=url)
    if title:
        payload["properties"] = {"title": title}
    return doc_call("smartsheet_add_sheet", payload, runner=runner)


def update_sheet(docid=None, url=None, sheet_id="", title="", confirmed=False, runner=None):
    require_confirmation(confirmed, "update_sheet")
    payload = target_payload(docid=docid, url=url)
    payload["properties"] = {"sheet_id": sheet_id, "title": title}
    return doc_call("smartsheet_update_sheet", payload, runner=runner)


def delete_sheet(docid=None, url=None, sheet_id="", confirmed=False, runner=None):
    require_confirmation(confirmed, "delete_sheet")
    payload = target_payload(docid=docid, url=url)
    payload["sheet_id"] = sheet_id
    return doc_call("smartsheet_delete_sheet", payload, runner=runner)


def get_fields(docid=None, url=None, sheet_id="", runner=None):
    payload = target_payload(docid=docid, url=url)
    payload["sheet_id"] = sheet_id
    return doc_call("smartsheet_get_fields", payload, runner=runner)


def add_fields(docid=None, url=None, sheet_id="", fields=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "add_fields")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "fields": fields or []})
    return doc_call("smartsheet_add_fields", payload, runner=runner)


def update_fields(docid=None, url=None, sheet_id="", fields=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "update_fields")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "fields": fields or []})
    return doc_call("smartsheet_update_fields", payload, runner=runner)


def delete_fields(docid=None, url=None, sheet_id="", field_ids=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "delete_fields")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "field_ids": field_ids or []})
    return doc_call("smartsheet_delete_fields", payload, runner=runner)


def add_records(docid=None, url=None, sheet_id="", records=None, confirmed=False, auto_file=False, runner=None):
    require_confirmation(confirmed, "add_records")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "records": records or []})
    command = "+smartsheet_add_records_auto_file" if auto_file else "smartsheet_add_records"
    return doc_call(command, payload, runner=runner)


def update_records(docid=None, url=None, sheet_id="", records=None, key_type=None, confirmed=False, auto_file=False, runner=None):
    require_confirmation(confirmed, "update_records")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "records": records or []})
    if key_type:
        payload["key_type"] = key_type
    command = "+smartsheet_update_records_auto_file" if auto_file else "smartsheet_update_records"
    return doc_call(command, payload, runner=runner)


def delete_records(docid=None, url=None, sheet_id="", record_ids=None, confirmed=False, runner=None):
    require_confirmation(confirmed, "delete_records")
    payload = target_payload(docid=docid, url=url)
    payload.update({"sheet_id": sheet_id, "record_ids": record_ids or []})
    return doc_call("smartsheet_delete_records", payload, runner=runner)

