"""Sprint 8.4.c.3 — Excel preview page helper regression."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    School,
    SchoolYearStatus,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.review._pages.excel_preview import (
    SHEET_ORDER,
    build_preview_workbook,
    count_unmatched_and_gap,
    format_sheet_preview,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "preview.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed(session: Session) -> None:
    """Two schools: A has data, B has none. Used for unmatched count."""
    a = School(prefecture="東京都", corporation_name="法人A", school_name="A学校",
               school_type="専門学校", status="active")
    b = School(prefecture="東京都", corporation_name="法人B", school_name="B学校",
               school_type="専門学校", status="active")
    session.add_all([a, b])
    session.flush()

    doc = Document(
        school_id=a.id,
        source_url="https://example.com/a.pdf",
        file_hash=("a" * 64),
        pdf_type="target", content_type="text",
        fiscal_year=2026, ingest_status="ingested",
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()

    dept = Department(school_id=a.id, canonical_name="A学科")
    session.add(dept)
    session.flush()
    session.add(DepartmentYearly(
        department_id=dept.id, document_id=doc.id,
        fiscal_year=2026, revision=1, is_current=True,
        enrollment=10, capacity=20, graduates=2,
        extraction_method="pdf_parse",
    ))
    # SR: collected status
    session.add(SupportRecipient(
        school_id=a.id, document_id=doc.id, fiscal_year=2026,
        revision=1, is_current=True,
        annual_total=100, grand_total=100,
    ))
    # SchoolYearStatus: A has 'collected', B will have 'partial' (gap)
    session.add(SchoolYearStatus(
        school_id=a.id, document_id=doc.id, fiscal_year=2026,
        revision=1, is_current=True, status="collected",
    ))
    session.add(SchoolYearStatus(
        school_id=b.id, fiscal_year=2026,
        revision=1, is_current=True, status="partial",
    ))
    session.flush()


# ---------------------------------------------------------------------------
# build_preview_workbook
# ---------------------------------------------------------------------------


def test_build_preview_workbook_produces_4_sheets(engine):
    with Session(engine) as session:
        _seed(session)
        session.commit()

        preview = build_preview_workbook(session)
        assert preview.workbook.sheetnames == list(SHEET_ORDER)
        assert preview.counts.keys() == set(SHEET_ORDER)


def test_build_preview_workbook_does_not_touch_filesystem(engine, tmp_path):
    """The page contract is 'no disk write until download click'.
    build_preview_workbook MUST NOT create any file in tmp_path even
    when given a session — it's purely in-memory."""
    import os
    snapshot_before = set(os.listdir(tmp_path))
    with Session(engine) as session:
        _seed(session)
        session.commit()
        preview = build_preview_workbook(session)
        # to_bytes() also stays in-memory.
        b = preview.to_bytes()
        assert isinstance(b, (bytes, bytearray))
        assert len(b) > 0

    snapshot_after = set(os.listdir(tmp_path))
    # Only the SQLite file from the engine fixture should have appeared.
    new_files = snapshot_after - snapshot_before
    assert all(f.endswith(".sqlite3") or f.endswith(".sqlite3-wal") or f.endswith(".sqlite3-shm")
               for f in new_files), f"unexpected files: {new_files}"


def test_to_bytes_round_trip_via_openpyxl(engine):
    """The bytes returned must be a valid xlsx — load them back with
    openpyxl and confirm sheet names round-trip."""
    import io

    import openpyxl

    with Session(engine) as session:
        _seed(session)
        session.commit()
        preview = build_preview_workbook(session)
        b = preview.to_bytes()

    wb2 = openpyxl.load_workbook(io.BytesIO(b))
    assert set(wb2.sheetnames) == set(SHEET_ORDER)


# ---------------------------------------------------------------------------
# format_sheet_preview
# ---------------------------------------------------------------------------


def test_format_sheet_preview_caps_at_max_rows(engine):
    with Session(engine) as session:
        _seed(session)
        session.commit()
        preview = build_preview_workbook(session)
        rows = format_sheet_preview(preview.workbook, "採録状況", max_rows=2)
        assert len(rows) <= 2


def test_format_sheet_preview_unknown_sheet_raises(engine):
    with Session(engine) as session:
        preview = build_preview_workbook(session)
    with pytest.raises(ValueError, match="not in workbook"):
        format_sheet_preview(preview.workbook, "未知シート")


# ---------------------------------------------------------------------------
# count_unmatched_and_gap
# ---------------------------------------------------------------------------


def test_count_unmatched_and_gap_basic(engine):
    with Session(engine) as session:
        _seed(session)
        session.commit()
        counts = count_unmatched_and_gap(session)

    assert counts.total_schools == 2
    assert counts.target_pdf_schools == 1
    assert counts.missing_target_pdf_schools == 1
    assert counts.extracted_schools == 1
    assert counts.target_yearly_rows == 1
    assert counts.has_target_year_data is True


def test_count_excludes_inactive_schools(engine):
    with Session(engine) as session:
        _seed(session)
        # Mark B inactive — it should drop out of schools_total.
        b = session.query(School).filter(School.school_name == "B学校").one()
        b.status = "inactive"
        session.commit()

        counts = count_unmatched_and_gap(session)
        assert counts.total_schools == 1
        assert counts.missing_target_pdf_schools == 0


def test_count_uses_current_target_yearly_rows_only(engine):
    """Export readiness ignores non-current yearly rows."""
    with Session(engine) as session:
        _seed(session)
        b = session.query(School).filter(School.school_name == "B学校").one()
        dept = Department(school_id=b.id, canonical_name="B学科")
        session.add(dept)
        session.flush()
        session.add(
            DepartmentYearly(
                department_id=dept.id,
                fiscal_year=2026,
                revision=1,
                is_current=False,
                enrollment=999,
                capacity=999,
            )
        )
        session.commit()

        counts = count_unmatched_and_gap(session)
        assert counts.target_yearly_rows == 1
        assert counts.extracted_schools == 1
