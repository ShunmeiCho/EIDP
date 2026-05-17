"""Sprint 8.4.c.2 — 年度修正 page helper regression.

Same shape as 8.4.c.1's PDF確認・手入力 tests: render shell is
exercised by the running app; helpers are unit-tested here.

Helpers under test:
  * list_override_candidates
  * override_with_lock
  * submit_override_form
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.config import SUPPORTED_TARGET_FISCAL_YEAR_RANGE_LABEL
from eidp.db.locking import acquire_lock
from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    School,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.review._pages.fiscal_year_override import (
    OVERRIDE_ELIGIBLE_STATUSES,
    OverrideOutcome,
    list_override_candidates,
    override_with_lock,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "fiscal_year_override.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed_full_doc(
    session: Session,
    *,
    name: str,
    fiscal_year: int = 2025,
    file_hash_seed: str = "x",
    status: str = "ingested",
) -> tuple[School, Document, Department]:
    school = School(
        prefecture="東京都", corporation_name="法人", school_name=name,
        school_type="専門学校", status="active",
    )
    session.add(school)
    session.flush()

    doc = Document(
        school_id=school.id,
        source_url=f"https://example.com/{file_hash_seed}.pdf",
        file_hash=(file_hash_seed.ljust(64, "0"))[:64],
        pdf_type="target",
        content_type="text",
        fiscal_year=fiscal_year,
        ingest_status=status,
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()

    dept = Department(school_id=school.id, canonical_name="A学科")
    session.add(dept)
    session.flush()

    session.add(DepartmentYearly(
        department_id=dept.id, document_id=doc.id,
        fiscal_year=fiscal_year, revision=1, is_current=True,
        enrollment=10, extraction_method="pdf_parse",
    ))
    session.flush()
    return school, doc, dept


# ---------------------------------------------------------------------------
# list_override_candidates
# ---------------------------------------------------------------------------


def test_candidates_includes_only_eligible_statuses(engine):
    with Session(engine) as session:
        _, ingested_doc, _ = _seed_full_doc(session, name="A", file_hash_seed="ing", status="ingested")
        _, support_doc, _ = _seed_full_doc(session, name="B", file_hash_seed="sup", status="support_only")
        # not eligible:
        _seed_full_doc(session, name="C", file_hash_seed="ocr", status="ocr_pending")
        _seed_full_doc(session, name="D", file_hash_seed="pf", status="parse_failed")
        session.commit()

        rows = list_override_candidates(session)
        ids = {r.document_id for r in rows}
        assert ids == {ingested_doc.id, support_doc.id}
        assert all(r.ingest_status in OVERRIDE_ELIGIBLE_STATUSES for r in rows)


def test_candidates_carry_school_metadata_and_override_flag(engine):
    with Session(engine) as session:
        _, doc, _ = _seed_full_doc(session, name="X", file_hash_seed="x", fiscal_year=2025)
        doc.fiscal_year_override = 2026
        session.commit()

        rows = list_override_candidates(session)
        assert len(rows) == 1
        r = rows[0]
        assert r.current_fiscal_year == 2025
        assert r.fiscal_year_override == 2026
        assert r.school_name == "X"


def test_candidates_skip_documents_with_no_fiscal_year(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都", corporation_name="法人", school_name="N",
            school_type="専門学校", status="active",
        )
        session.add(school)
        session.flush()
        session.add(Document(
            school_id=school.id,
            source_url="https://example.com/none.pdf",
            file_hash=("n" * 64),
            pdf_type="target", content_type="text",
            fiscal_year=None,
            ingest_status="ingested",
        ))
        session.commit()
        rows = list_override_candidates(session)
        assert rows == []


# ---------------------------------------------------------------------------
# override_with_lock
# ---------------------------------------------------------------------------


def test_override_with_lock_writes_when_lock_free(engine, tmp_path):
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _, doc, dept = _seed_full_doc(session, name="OK", file_hash_seed="ok", fiscal_year=2025)
        session.commit()

        outcome = override_with_lock(
            session,
            document_id=doc.id,
            target_fy=2026,
            reason="confirmed target fiscal year",
            lock_path=lock,
        )
        assert outcome.ok is True
        assert outcome.lock_busy is False
        assert outcome.stats == {
            "department_yearly": 1,
            "support_recipient": 0,
            "school_year_status": 0,
            "document": 1,
        }

        session.refresh(doc)
        assert doc.fiscal_year == 2026
        assert doc.fiscal_year_override == 2026


def test_override_with_lock_returns_lock_busy_without_writing(engine, tmp_path):
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _, doc, _ = _seed_full_doc(session, name="LB", file_hash_seed="lb", fiscal_year=2025)
        session.commit()

        with acquire_lock(lock, owner="weekly_runner"):
            outcome = override_with_lock(
                session,
                document_id=doc.id,
                target_fy=2026,
                lock_path=lock,
            )

        assert outcome.ok is False
        assert outcome.lock_busy is True
        assert outcome.lock_owner == "weekly_runner"

        session.refresh(doc)
        assert doc.fiscal_year == 2025  # unchanged


def test_override_with_lock_rolls_back_on_pipeline_error(engine, tmp_path):
    """If override_fiscal_year raises (e.g. document missing),
    override_with_lock must roll back and return ok=False."""
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        outcome = override_with_lock(
            session,
            document_id=99999,  # does not exist
            target_fy=2026,
            lock_path=lock,
        )
        assert outcome.ok is False
        assert outcome.lock_busy is False
        assert "not found" in (outcome.error or "")


def test_override_with_lock_rejects_invalid_target_fy_without_lock(engine, tmp_path):
    """Out-of-range target_fy must short-circuit BEFORE lock acquisition."""
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _, doc, _ = _seed_full_doc(session, name="R", file_hash_seed="r", fiscal_year=2025)
        session.commit()

        outcome = override_with_lock(
            session, document_id=doc.id, target_fy=1900, lock_path=lock,
        )
        assert outcome.ok is False
        assert outcome.lock_busy is False
        assert "out of supported range" in (outcome.error or "")


# ---------------------------------------------------------------------------
# submit_override_form
# ---------------------------------------------------------------------------


def test_submit_form_routes_through_override_with_lock(engine, tmp_path, monkeypatch):
    from eidp.review._pages import fiscal_year_override as page_mod

    captured: dict = {}

    def fake_override(session, **kwargs):
        captured.update(kwargs)
        return OverrideOutcome(ok=True, stats={"document": 1, "department_yearly": 0,
                                                "support_recipient": 0, "school_year_status": 0})

    monkeypatch.setattr(page_mod, "override_with_lock", fake_override)

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _, doc, _ = _seed_full_doc(session, name="S", file_hash_seed="s", fiscal_year=2025)
        session.commit()

        outcome = page_mod.submit_override_form(
            session,
            document_id=doc.id,
            target_fy=2026,
            reason="cover page says target fiscal year",
            actor="山田",
            lock_path=lock,
        )

    assert outcome.ok is True
    assert captured["document_id"] == doc.id
    assert captured["target_fy"] == 2026
    assert captured["reason"] == "cover page says target fiscal year"
    assert captured["actor"] == "山田"
    assert captured["lock_path"] == lock


def test_submit_form_rejects_invalid_document_without_lock(engine, tmp_path, monkeypatch):
    from eidp.review._pages import fiscal_year_override as page_mod

    called = {"count": 0}
    monkeypatch.setattr(
        page_mod, "override_with_lock",
        lambda *a, **kw: (called.__setitem__("count", called["count"] + 1) or OverrideOutcome(ok=True)),
    )

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        outcome = page_mod.submit_override_form(
            session, document_id=0, target_fy=2026, reason=None, lock_path=lock,
        )
    assert outcome.ok is False
    assert "document" in (outcome.error or "")
    assert called["count"] == 0


def test_submit_form_rejects_out_of_range_target_fy(engine, tmp_path, monkeypatch):
    from eidp.review._pages import fiscal_year_override as page_mod

    called = {"count": 0}
    monkeypatch.setattr(
        page_mod, "override_with_lock",
        lambda *a, **kw: (called.__setitem__("count", called["count"] + 1) or OverrideOutcome(ok=True)),
    )

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        outcome = page_mod.submit_override_form(
            session, document_id=1, target_fy=1850, reason=None, lock_path=lock,
        )
    assert outcome.ok is False
    assert f"out of {SUPPORTED_TARGET_FISCAL_YEAR_RANGE_LABEL}" in (outcome.error or "")
    assert called["count"] == 0


def test_override_eligible_statuses_pinned():
    """Policy lock — override candidates are only ingested / support_only,
    not ocr_pending / parse_failed (those go to manual entry first)."""
    assert OVERRIDE_ELIGIBLE_STATUSES == frozenset({"ingested", "support_only"})
