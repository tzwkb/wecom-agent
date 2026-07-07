"""Read locally cached or downloaded WeCom documents as a fallback."""

import os
from pathlib import Path

from decrypt import read_doc


DOC_EXTS = read_doc.TEXT_EXT | {"pdf", "xlsx", "xlsm", "xls", "docx"} | read_doc.IMAGE_EXT
DEFAULT_LIMIT = 8000


def read_path(path, limit=DEFAULT_LIMIT):
    p = Path(path).expanduser()
    body = read_doc.read_file(str(p), limit=limit)
    base = {
        "source": "local-cache-fallback",
        "freshness": "local file; may be stale vs online document",
        "path": str(p.resolve()) if p.exists() else str(p),
        "name": p.name,
        "size": p.stat().st_size if p.exists() and p.is_file() else None,
        "mtime": p.stat().st_mtime if p.exists() and p.is_file() else None,
        "content": None,
        "visual": None,
    }
    if body.startswith(read_doc.VISUAL_MARK):
        base.update({"status": "visual", "visual": body})
    elif body.startswith("[文件不存在:"):
        base.update({"status": "not_found", "content": body})
    elif body.startswith("[不是文件:"):
        base.update({"status": "not_file", "content": body})
    else:
        base.update({"status": "ok", "content": body})
    return base


def search(keyword, roots=None, max_results=5, limit=DEFAULT_LIMIT):
    if not keyword:
        raise ValueError("keyword is required")
    matches = find_files(keyword, roots=roots, max_results=max_results)
    files = [read_path(path, limit=limit) for path in matches]
    if not files:
        return {
            "status": "not_found",
            "source": "local-cache-fallback",
            "freshness": "local file; may be stale vs online document",
            "keyword": keyword,
            "count": 0,
            "files": [],
            "message": "No local cached/downloaded document matched; it is not downloaded or was not opened on this device.",
        }
    return {
        "status": "ok",
        "source": "local-cache-fallback",
        "freshness": "local file; may be stale vs online document",
        "keyword": keyword,
        "count": len(files),
        "files": files,
    }


def find_files(keyword, roots=None, max_results=5):
    lower = keyword.lower()
    found = []
    for root in roots or default_roots():
        r = Path(root).expanduser()
        if not r.exists():
            continue
        for path in _walk(r):
            if lower in path.name.lower() and _supported(path):
                found.append(path)
    found.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return found[:max_results]


def default_roots():
    env = os.environ.get("WECOM_LOCAL_DOC_ROOTS")
    if env:
        return [p for p in env.split(os.pathsep) if p]

    roots = []
    try:
        from decrypt.macos import wecom_paths

        roots.append(Path(wecom_paths.caches()) / "Files")
    except BaseException:
        pass

    home = Path.home()
    roots.extend([home / "Downloads", home / "Documents", home / "Desktop"])
    return roots


def _walk(root):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and path.name != ".DS_Store":
            yield path


def _supported(path):
    suffix = path.suffix.lower().lstrip(".")
    return suffix in DOC_EXTS or suffix == ""
