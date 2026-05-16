from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "prune_pdf_storage.py"
spec = importlib.util.spec_from_file_location("prune_pdf_storage", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _touch(path: Path, body: bytes = b"%PDF") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _sqlite_with_document(path: Path, *, file_path: str, fiscal_year: int, is_current_year: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE document (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                fiscal_year INTEGER,
                fiscal_year_override INTEGER,
                is_current_year BOOLEAN
            )
            """
        )
        conn.execute(
            """
            INSERT INTO document (id, file_path, fiscal_year, fiscal_year_override, is_current_year)
            VALUES (1, ?, ?, NULL, ?)
            """,
            (file_path, fiscal_year, int(is_current_year)),
        )


def test_collect_candidates_lists_unreferenced_pdfs_only(tmp_path: Path) -> None:
    referenced = tmp_path / "data" / "pdfs" / "1" / "keep.pdf"
    orphan = tmp_path / "data" / "pdfs" / "2" / "orphan.pdf"
    _touch(referenced)
    _touch(orphan)
    _sqlite_with_document(tmp_path / "data" / "eidp.sqlite3", file_path="data/pdfs/1/keep.pdf", fiscal_year=2026)

    candidates = module.collect_candidates(app_root=tmp_path)

    assert [candidate.path for candidate in candidates] == ["data/pdfs/2/orphan.pdf"]


def test_apply_cleanup_deletes_reported_orphan_pdf(tmp_path: Path) -> None:
    orphan = tmp_path / "data" / "pdfs" / "2" / "orphan.pdf"
    keep = tmp_path / "data" / "pdfs" / "2" / "keep.txt"
    _touch(orphan)
    _touch(keep, b"not pdf")

    candidates = module.collect_candidates(app_root=tmp_path)
    actions = module.apply_cleanup(tmp_path, candidates)

    assert actions[0]["deleted"] is True
    assert not orphan.exists()
    assert keep.exists()


def test_collect_candidates_requires_flag_for_obsolete_referenced_pdfs(tmp_path: Path) -> None:
    pdf = tmp_path / "data" / "pdfs" / "1" / "old.pdf"
    _touch(pdf)
    _sqlite_with_document(tmp_path / "data" / "eidp.sqlite3", file_path="data/pdfs/1/old.pdf", fiscal_year=2023)

    default_candidates = module.collect_candidates(app_root=tmp_path, keep_from_fiscal_year=2025)
    flagged_candidates = module.collect_candidates(
        app_root=tmp_path,
        keep_from_fiscal_year=2025,
        include_obsolete_referenced=True,
    )

    assert default_candidates == []
    assert [candidate.path for candidate in flagged_candidates] == ["data/pdfs/1/old.pdf"]
    assert flagged_candidates[0].document_id == 1
    assert flagged_candidates[0].fiscal_year == 2023


def test_collect_candidates_keeps_current_referenced_pdf_even_when_flagged(tmp_path: Path) -> None:
    pdf = tmp_path / "data" / "pdfs" / "1" / "current.pdf"
    _touch(pdf)
    _sqlite_with_document(
        tmp_path / "data" / "eidp.sqlite3",
        file_path="data/pdfs/1/current.pdf",
        fiscal_year=2023,
        is_current_year=True,
    )

    candidates = module.collect_candidates(
        app_root=tmp_path,
        keep_from_fiscal_year=2025,
        include_obsolete_referenced=True,
    )

    assert candidates == []


def test_collect_candidates_skips_symlink_pdf(tmp_path: Path) -> None:
    outside = tmp_path / "outside.pdf"
    _touch(outside)
    link = tmp_path / "data" / "pdfs" / "1" / "link.pdf"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)

    candidates = module.collect_candidates(app_root=tmp_path)

    assert candidates == []
