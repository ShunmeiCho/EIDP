"""Consistent SQLite backup helpers for single-PC Windows operation."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url


def sqlite_path_from_database_url(database_url: str) -> Path:
    """Return the filesystem path for a SQLite database URL."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError(f"SQLite backup requires a sqlite database URL, got {url.get_backend_name()!r}")
    if not url.database or url.database == ":memory:":
        raise ValueError("SQLite backup requires a file-backed database, not :memory:")
    return Path(url.database).expanduser()


def default_sqlite_backup_path(data_dir: Path, *, now: datetime | None = None) -> Path:
    """Build the operator-visible default backup path under data/."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return Path(data_dir) / f"eidp-backup-{timestamp}.sqlite3"


def backup_sqlite_database(database_path: Path, backup_path: Path) -> Path:
    """Create a consistent SQLite backup using WAL checkpoint + VACUUM INTO."""
    source = Path(database_path).expanduser()
    target = Path(backup_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {source}")
    if target.exists():
        raise FileExistsError(f"SQLite backup already exists: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(source))
    try:
        integrity_rows = con.execute("PRAGMA integrity_check").fetchall()
        problems = [str(row[0]) for row in integrity_rows if row and str(row[0]).lower() != "ok"]
        if problems:
            raise RuntimeError(f"SQLite integrity_check failed: {'; '.join(problems)}")

        checkpoint_rows = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        if checkpoint_rows and int(checkpoint_rows[0][0]) != 0:
            raise RuntimeError(f"SQLite WAL checkpoint was busy: {checkpoint_rows[0]}")

        con.execute("VACUUM INTO ?", (str(target),))
    finally:
        con.close()
    return target

