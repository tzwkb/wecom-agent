#!/usr/bin/env python3
"""Shared media export helpers."""
import hashlib
import shutil
from pathlib import Path


def copy_unique(src, dst_dir):
    """Copy src into dst_dir without overwriting an existing same-name file."""
    src = Path(src)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    if target.exists():
        digest = hashlib.blake2s(str(src).encode("utf-8", "surrogateescape"), digest_size=4).hexdigest()
        stem, suffix = src.stem, src.suffix
        target = dst_dir / f"{stem}_{digest}{suffix}"
        i = 2
        while target.exists():
            target = dst_dir / f"{stem}_{digest}_{i}{suffix}"
            i += 1
    shutil.copy2(src, target)
    return target
