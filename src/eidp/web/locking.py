"""Shared single-writer lock for Linux/Web mutation paths."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

from eidp.config import settings
from eidp.db.locking import acquire_lock


def web_write_lock_path(intake_root: Path, *, data_dir: Path | None = None) -> Path:
    """Return the app-wide lock when intake lives below the configured data root."""

    root = Path(intake_root).resolve()
    resolved_data_dir = Path(data_dir or settings.data_dir).resolve()
    if root == resolved_data_dir or resolved_data_dir in root.parents:
        return resolved_data_dir / ".lock"
    return root / ".lock"


@contextlib.contextmanager
def acquire_web_write_lock(
    intake_root: Path,
    *,
    owner: str,
    data_dir: Path | None = None,
) -> Iterator[None]:
    """Serialize a Web mutation with CLI and background SQLite writers."""

    with acquire_lock(web_write_lock_path(intake_root, data_dir=data_dir), owner=owner):
        yield
