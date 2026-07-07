"""Online document helpers backed by wecom-cli doc commands."""

from .wecom_cli import doc_call, require_confirmation, target_payload


def create_document(name, confirmed=False, runner=None):
    require_confirmation(confirmed, "create_document")
    return doc_call("create_doc", {"doc_name": name, "doc_type": 3}, runner=runner)


def write_document_markdown(docid=None, url=None, content="", confirmed=False, runner=None):
    require_confirmation(confirmed, "write_document_markdown")
    payload = target_payload(docid=docid, url=url)
    payload.update({"content": content, "content_type": 1})
    return doc_call("edit_doc_content", payload, runner=runner)


def create_smartpage(title, pages, confirmed=False, auto_file=False, runner=None):
    require_confirmation(confirmed, "create_smartpage")
    command = "+smartpage_create" if auto_file else "smartpage_create"
    return doc_call(command, {"title": title, "pages": pages}, runner=runner)

