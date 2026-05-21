"""Sprint 8.7 simplify pass — shared helpers for Windows ZIP builders.

`build_windows_zip.py`, `build_ocr_addon_zip.py`, `build_playwright_addon_zip.py`,
`download_windows_runtime.py`, and `verify_windows_distribution.py` all need
the same two operations: stream-hash a file with SHA-256, and walk a tree
yielding only real files (skipping ``__pycache__``). Earlier drops shipped
four distinct copies of each. This module is the single source of truth.

Pure stdlib. No project imports. Safe to call from any builder script.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1 << 20  # 1 MiB matches the existing pattern in download_windows_runtime.py


def sha256_file(path: Path) -> str:
    """Streaming SHA-256 of ``path``. Reuses the same chunk size all
    sister scripts already used so behavior is byte-identical."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_payload_files(root: Path) -> list[Path]:
    """Sorted list of regular files under ``root``, excluding any path
    component named ``__pycache__``. Sorted output keeps ZIP manifests
    deterministic for diff-based release verification."""
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
