"""Sprint 8.2.c.2 — fiscal_year_override 4-table append-only rewrite.

Owner-pinned data integrity contract:

  * Document.fiscal_year is physically updated to target_fy AND
    fiscal_year_override is set to the same value.
  * department_yearly / support_recipient / school_year_status rows that the
    document owned at source_fy are demoted (is_current=False) and recreated
    at target_fy as new revision=max+1 rows with is_current=True. Values are
    carried over, not zeroed.
  * Coverage and exporter (which read raw fiscal_year) see the new fiscal
    year afterwards — no effective_fiscal_year() shim is needed in those
    paths.
  * Every per-row change emits a manual_action_log entry with action_type
    'fiscal_year_override'; old_value captures the source state, new_value
    captures the target state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    ManualActionLog,
    School,
    SchoolYearStatus,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.pipeline.fiscal_year_override import effective_fiscal_year, override_fiscal_year


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "fy_override.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed_one_doc(session: Session, *, fiscal_year: int) -> tuple[School, Document, Department]:
    school = School(
        prefecture="東京都",
        corporation_name="テスト法人",
        school_name="テスト専門学校",
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    session.flush()

    doc = Document(
        school_id=school.id,
        source_url="https://example.com/test.pdf",
        file_hash=("a" * 64),
        pdf_type="target",
        content_type="text",
        fiscal_year=fiscal_year,
        ingest_status="ingested",
        downloaded_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    session.flush()

    dept = Department(school_id=school.id, canonical_name="テスト学科")
    session.add(dept)
    session.flush()

    session.add(
        DepartmentYearly(
            department_id=dept.id,
            document_id=doc.id,
            fiscal_year=fiscal_year,
            revision=1,
            is_current=True,
            capacity=40,
            enrollment=42,
            graduates=10,
            extraction_method="pdf_parse",
        )
    )
    session.add(
        SupportRecipient(
            school_id=school.id,
            document_id=doc.id,
            fiscal_year=fiscal_year,
            revision=1,
            is_current=True,
            annual_total=120,
            grand_total=120,
        )
    )
    session.add(
        SchoolYearStatus(
            school_id=school.id,
            document_id=doc.id,
            fiscal_year=fiscal_year,
            revision=1,
            is_current=True,
            status="collected",
        )
    )
    session.flush()
    return school, doc, dept


# ---------------------------------------------------------------------------
# effective_fiscal_year helper
# ---------------------------------------------------------------------------


def test_effective_fiscal_year_prefers_override():
    doc = Document(school_id=1, source_url="x", fiscal_year=2025, fiscal_year_override=2026)
    assert effective_fiscal_year(doc) == 2026


def test_effective_fiscal_year_falls_back_to_fiscal_year():
    doc = Document(school_id=1, source_url="x", fiscal_year=2025, fiscal_year_override=None)
    assert effective_fiscal_year(doc) == 2025


def test_effective_fiscal_year_returns_none_when_both_unset():
    doc = Document(school_id=1, source_url="x", fiscal_year=None, fiscal_year_override=None)
    assert effective_fiscal_year(doc) is None


# ---------------------------------------------------------------------------
# 4-table rewrite
# ---------------------------------------------------------------------------


def test_override_rewrites_all_four_tables(engine):
    with Session(engine) as session:
        _, doc, dept = _seed_one_doc(session, fiscal_year=2025)
        session.commit()

        stats = override_fiscal_year(
            session, doc.id, target_fy=2026,
            actor="operator", reason="parser said FY2025; PDF cover says R8",
        )
        session.commit()

        assert stats == {
            "department_yearly": 1,
            "support_recipient": 1,
            "school_year_status": 1,
            "document": 1,
        }

        # Document
        session.refresh(doc)
        assert doc.fiscal_year == 2026
        assert doc.fiscal_year_override == 2026

        # DepartmentYearly: revision 1 source-fy demoted, revision 1 target-fy current
        dy_rows = (
            session.query(DepartmentYearly)
            .filter(DepartmentYearly.department_id == dept.id)
            .order_by(DepartmentYearly.id)
            .all()
        )
        assert len(dy_rows) == 2
        src_dy = next(r for r in dy_rows if r.fiscal_year == 2025)
        new_dy = next(r for r in dy_rows if r.fiscal_year == 2026)
        assert src_dy.is_current is False
        assert new_dy.is_current is True
        assert new_dy.revision == 1
        # Values carried over
        assert new_dy.capacity == 40
        assert new_dy.enrollment == 42
        assert new_dy.graduates == 10
        assert new_dy.extraction_method == "pdf_parse"

        # SupportRecipient: same pattern
        sr_rows = session.query(SupportRecipient).order_by(SupportRecipient.id).all()
        assert len(sr_rows) == 2
        assert next(r for r in sr_rows if r.fiscal_year == 2025).is_current is False
        new_sr = next(r for r in sr_rows if r.fiscal_year == 2026)
        assert new_sr.is_current is True
        assert new_sr.annual_total == 120

        # SchoolYearStatus: same pattern
        sys_rows = session.query(SchoolYearStatus).order_by(SchoolYearStatus.id).all()
        assert len(sys_rows) == 2
        assert next(r for r in sys_rows if r.fiscal_year == 2025).is_current is False
        new_sys = next(r for r in sys_rows if r.fiscal_year == 2026)
        assert new_sys.is_current is True
        assert new_sys.status == "collected"


def test_override_writes_audit_log_for_each_table(engine):
    with Session(engine) as session:
        _, doc, _ = _seed_one_doc(session, fiscal_year=2025)
        session.commit()

        override_fiscal_year(session, doc.id, target_fy=2026,
                             actor="operator", reason="confirm R8 from cover page")
        session.commit()

        actions = session.query(ManualActionLog).all()
        # 1 per table = 4 rows for a single dept document
        assert len(actions) == 4
        assert {a.action_type for a in actions} == {"fiscal_year_override"}
        assert {a.target_table for a in actions} == {
            "department_yearly", "support_recipient", "school_year_status", "document",
        }
        for a in actions:
            assert a.actor == "operator"
            assert a.reason == "confirm R8 from cover page"
            old = json.loads(a.old_value)
            new = json.loads(a.new_value)
            assert "fiscal_year" in old and "fiscal_year" in new
            if a.target_table == "document":
                assert old["fiscal_year"] == 2025
                assert new["fiscal_year"] == 2026
                assert new["fiscal_year_override"] == 2026
            else:
                assert old["fiscal_year"] == 2025
                assert new["fiscal_year"] == 2026
                assert old["is_current"] is True
                assert new["is_current"] is True


def test_override_is_idempotent_when_already_at_target(engine):
    """If the doc is already at target_fy AND fiscal_year_override matches,
    the rewrite is a no-op so the operator can tap the button twice safely."""
    with Session(engine) as session:
        _, doc, _ = _seed_one_doc(session, fiscal_year=2026)
        doc.fiscal_year_override = 2026
        session.commit()

        stats = override_fiscal_year(session, doc.id, target_fy=2026)
        session.commit()
        assert stats == {
            "department_yearly": 0, "support_recipient": 0,
            "school_year_status": 0, "document": 0,
        }
        assert session.query(ManualActionLog).count() == 0


def test_override_back_creates_revision_2_at_original_year(engine):
    """If the operator overrides FY2025 → FY2026 and then back to FY2025, the
    second rewrite must produce revision 2 at FY2025 (because revision 1 was
    demoted by the first rewrite). No unique-constraint collisions."""
    with Session(engine) as session:
        _, doc, dept = _seed_one_doc(session, fiscal_year=2025)
        session.commit()

        override_fiscal_year(session, doc.id, target_fy=2026,
                             actor="operator", reason="first override")
        session.commit()

        override_fiscal_year(session, doc.id, target_fy=2025,
                             actor="operator", reason="changed my mind")
        session.commit()

        dy_rows = (
            session.query(DepartmentYearly)
            .filter(DepartmentYearly.department_id == dept.id)
            .order_by(DepartmentYearly.id)
            .all()
        )
        # Original FY2025 rev1 (demoted), FY2026 rev1 (now demoted),
        # FY2025 rev2 (current).
        assert len(dy_rows) == 3
        currents = [r for r in dy_rows if r.is_current]
        assert len(currents) == 1
        assert currents[0].fiscal_year == 2025
        assert currents[0].revision == 2

        session.refresh(doc)
        assert doc.fiscal_year == 2025
        assert doc.fiscal_year_override == 2025


def test_override_raises_when_document_missing(engine):
    with Session(engine) as session:
        with pytest.raises(ValueError, match="not found"):
            override_fiscal_year(session, doc_id=999, target_fy=2026)


def test_override_raises_when_document_has_no_fiscal_year(engine):
    with Session(engine) as session:
        school, _, _ = _seed_one_doc(session, fiscal_year=2025)
        # New doc with no fiscal_year
        doc2 = Document(
            school_id=school.id,
            source_url="https://example.com/v2.pdf",
            file_hash=("b" * 64),
            pdf_type="target",
            content_type="text",
            fiscal_year=None,
        )
        session.add(doc2)
        session.commit()

        with pytest.raises(ValueError, match="no fiscal_year"):
            override_fiscal_year(session, doc2.id, target_fy=2026)
