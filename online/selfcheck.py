"""Probe current wecom-cli online document support."""

import json

from . import wecom_cli


SUPPORTED_DOC_COMMANDS = [
    "+smartpage_create",
    "+smartsheet_add_records_auto_file",
    "+smartsheet_update_records_auto_file",
    "create_doc",
    "edit_doc_content",
    "smartpage_create",
    "smartsheet_add_sheet",
    "smartsheet_get_sheet",
    "smartsheet_add_fields",
    "smartsheet_update_fields",
    "smartsheet_get_fields",
    "smartsheet_add_records",
    "smartsheet_update_sheet",
    "smartsheet_delete_sheet",
    "smartsheet_delete_fields",
    "smartsheet_update_records",
    "smartsheet_delete_records",
    "sheet_get_info",
    "sheet_add_sub",
    "sheet_delete_sub",
    "sheet_update_range_data",
    "sheet_append_data",
]

KNOWN_UNSUPPORTED_DOC_COMMANDS = [
    "get_doc_content",
    "sheet_get_data",
    "smartsheet_get_records",
]


def collect():
    report = {
        "version": _safe_text(wecom_cli.version),
        "auth_status": _safe_text(wecom_cli.auth_status),
        "doc_commands": {},
    }
    for command in SUPPORTED_DOC_COMMANDS + KNOWN_UNSUPPORTED_DOC_COMMANDS:
        report["doc_commands"][command] = "supported" if wecom_cli.doc_command_supported(command) else "unsupported"
    return report


def _safe_text(func):
    try:
        return func()
    except Exception as exc:
        return f"error: {exc}"


def main():
    print(json.dumps(collect(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
