from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from eidp.db.sqlite_backup import (
    backup_sqlite_database,
    default_sqlite_backup_path,
    sqlite_path_from_database_url,
)


def test_backup_sqlite_database_creates_readable_copy_after_checkpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "eidp.sqlite3"
    backup_path = tmp_path / "backups" / "eidp-backup.sqlite3"

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    con.execute("INSERT INTO sample (name) VALUES ('alpha')")
    con.commit()
    con.close()

    written = backup_sqlite_database(db_path, backup_path)

    assert written == backup_path
    backup = sqlite3.connect(backup_path)
    try:
        rows = backup.execute("SELECT id, name FROM sample").fetchall()
    finally:
        backup.close()
    assert rows == [(1, "alpha")]


def test_backup_sqlite_database_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    db_path = tmp_path / "eidp.sqlite3"
    backup_path = tmp_path / "eidp-backup.sqlite3"
    sqlite3.connect(db_path).close()
    backup_path.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        backup_sqlite_database(db_path, backup_path)


def test_sqlite_path_from_database_url_rejects_non_file_sqlite_urls() -> None:
    assert sqlite_path_from_database_url("sqlite:////tmp/eidp.sqlite3") == Path("/tmp/eidp.sqlite3")

    with pytest.raises(ValueError, match="sqlite database URL"):
        sqlite_path_from_database_url("postgresql://example/eidp")

    with pytest.raises(ValueError, match="file-backed"):
        sqlite_path_from_database_url("sqlite:///:memory:")


def test_default_sqlite_backup_path_uses_operator_timestamp(tmp_path: Path) -> None:
    backup_path = default_sqlite_backup_path(tmp_path, now=datetime(2026, 5, 13, 23, 30, 1))

    assert backup_path == tmp_path / "eidp-backup-20260513-233001.sqlite3"

