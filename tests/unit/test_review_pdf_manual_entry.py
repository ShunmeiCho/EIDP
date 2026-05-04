"""Sprint 8.4.c.1 — PDF確認・手入力 page helper regression.

The Streamlit render shell is intentionally thin and not unit-tested
here (it exercises through the running app). This file pins the
*pure* helper contracts the page depends on:

  * list_pending_documents — queue projection (statuses, ordering, JOIN).
  * form_data_to_entries   — UI dict → DepartmentEntry, with validation
    that mirrors save_manual_entries' guardrails so the user gets
    inline feedback before we try the DB.
  * save_with_lock         — non-blocking lock acquisition; lock-busy
    short-circuits without writing; lock-free passes through to
    save_manual_entries with a commit; underlying errors roll back.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.locking import acquire_lock
from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    School,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.review.pages.pdf_manual_entry import (
    QUEUE_STATUSES,
    SaveOutcome,
    form_data_to_entries,
    list_pending_documents,
    save_with_lock,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "page_helpers.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed_school(session: Session, *, name: str, pref: str = "東京都") -> School:
    school = School(
        prefecture=pref, corporation_name="法人", school_name=name,
        school_type="専門学校", status="active",
    )
    session.add(school)
    session.flush()
    return school


def _seed_doc(
    session: Session, school: School, *, status: str, file_hash_seed: str,
    fiscal_year: int | None = None,
) -> Document:
    doc = Document(
        school_id=school.id,
        source_url=f"https://example.com/{file_hash_seed}.pdf",
        file_hash=(file_hash_seed.ljust(64, "0"))[:64],
        pdf_type="target",
        content_type="image",
        fiscal_year=fiscal_year,
        ingest_status=status,
        downloaded_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    session.flush()
    return doc


# ---------------------------------------------------------------------------
# list_pending_documents
# ---------------------------------------------------------------------------


def test_queue_returns_only_queued_statuses(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="A学校")
        d_ocr = _seed_doc(session, school, status="ocr_pending", file_hash_seed="ocr")
        d_pf = _seed_doc(session, school, status="parse_failed", file_hash_seed="pf")
        d_rev = _seed_doc(session, school, status="review_pending", file_hash_seed="rev")
        d_mis = _seed_doc(session, school, status="school_mismatch", file_hash_seed="mis")
        # not in queue
        _seed_doc(session, school, status="ingested", file_hash_seed="ing")
        _seed_doc(session, school, status="non_target", file_hash_seed="nt")
        session.commit()

        rows = list_pending_documents(session)
        ids = [r.document_id for r in rows]
        assert ids == [d_ocr.id, d_pf.id, d_rev.id, d_mis.id]
        assert all(r.ingest_status in QUEUE_STATUSES for r in rows)


def test_queue_carries_school_join_and_metadata(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="B学校", pref="大阪府")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="b", fiscal_year=2026)
        session.commit()

        rows = list_pending_documents(session)
        assert len(rows) == 1
        r = rows[0]
        assert r.document_id == doc.id
        assert r.school_id == school.id
        assert r.school_name == "B学校"
        assert r.prefecture == "大阪府"
        assert r.fiscal_year == 2026
        assert r.source_url.endswith("b.pdf")


def test_queue_respects_limit(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="L学校")
        for i in range(5):
            _seed_doc(session, school, status="ocr_pending", file_hash_seed=f"ll{i}")
        session.commit()

        rows = list_pending_documents(session, limit=3)
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# form_data_to_entries
# ---------------------------------------------------------------------------


def test_form_minimal_required_only_canonical_name():
    fv = form_data_to_entries([{"canonical_name": "A学科"}])
    assert fv.ok, fv.errors
    assert len(fv.entries) == 1
    assert fv.entries[0].canonical_name == "A学科"
    assert fv.entries[0].enrollment is None


def test_form_missing_canonical_name_errors():
    fv = form_data_to_entries([{"enrollment": 10}])
    assert not fv.ok
    assert any(e.field.endswith(".canonical_name") for e in fv.errors)


def test_form_negative_enrollment_errors():
    fv = form_data_to_entries([{"canonical_name": "A学科", "enrollment": -1}])
    assert not fv.ok
    assert any("enrollment" in e.field and "non-negative" in e.message for e in fv.errors)


def test_form_dropout_rate_out_of_range_errors():
    fv = form_data_to_entries([{"canonical_name": "A学科", "dropout_rate": 1.5}])
    assert not fv.ok
    assert any("dropout_rate" in e.field for e in fv.errors)


def test_form_invalid_dept_change_errors():
    fv = form_data_to_entries([{"canonical_name": "A学科", "dept_change": "bogus"}])
    assert not fv.ok
    assert any("dept_change" in e.field for e in fv.errors)


def test_form_duration_years_accepts_floats():
    fv = form_data_to_entries([{"canonical_name": "A学科", "duration_years": "2.5"}])
    assert fv.ok, fv.errors
    assert fv.entries[0].duration_years == 2.5


def test_form_multiple_rows_partial_failure_isolated():
    """One bad row must not contaminate the others — the page renders
    inline errors per row, valid rows still appear in the entries list
    so the operator can save what's correct (caller's policy)."""
    fv = form_data_to_entries([
        {"canonical_name": "A学科", "enrollment": 10},
        {"canonical_name": "", "enrollment": 5},
        {"canonical_name": "C学科", "enrollment": -3},
    ])
    assert not fv.ok
    # Row 0 succeeds, rows 1 + 2 fail.
    assert len(fv.entries) == 1
    assert fv.entries[0].canonical_name == "A学科"


# ---------------------------------------------------------------------------
# save_with_lock
# ---------------------------------------------------------------------------


def test_save_with_lock_writes_when_lock_free(engine, tmp_path):
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="X学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="x", fiscal_year=2026)
        session.commit()

        outcome = save_with_lock(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            entries=[__import__("eidp.pipeline.manual_entry", fromlist=["DepartmentEntry"]).DepartmentEntry(
                canonical_name="A学科", enrollment=10,
            )],
            lock_path=lock,
        )
        assert outcome.ok is True
        assert outcome.lock_busy is False
        assert outcome.result is not None
        assert outcome.result.rows_written == 1

        # Verify a DepartmentYearly row landed and the document was promoted.
        dy = session.query(DepartmentYearly).one()
        assert dy.enrollment == 10
        session.refresh(doc)
        assert doc.ingest_status == "ingested"


def test_save_with_lock_returns_lock_busy_without_writing(engine, tmp_path):
    """If the weekly runner holds the lock, the UI helper must NOT
    write — it should return SaveOutcome(lock_busy=True) so the page
    can render the banner and refuse the save."""
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="Y学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="y", fiscal_year=2026)
        session.commit()

        from eidp.pipeline.manual_entry import DepartmentEntry

        # Hold the lock while attempting the UI save.
        with acquire_lock(lock, owner="weekly_runner"):
            outcome = save_with_lock(
                session,
                document_id=doc.id,
                fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
                lock_path=lock,
            )

        assert outcome.ok is False
        assert outcome.lock_busy is True
        assert outcome.lock_owner == "weekly_runner"

        # No rows must have been written.
        assert session.query(DepartmentYearly).count() == 0
        session.refresh(doc)
        assert doc.ingest_status == "ocr_pending"


def test_save_with_lock_rolls_back_on_pipeline_error(engine, tmp_path):
    """If save_manual_entries raises (e.g. negative enrollment),
    save_with_lock must roll back and return ok=False with the error
    message — no partial mutation, no audit row."""
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="Z学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="z", fiscal_year=2026)
        session.commit()

        from eidp.pipeline.manual_entry import DepartmentEntry

        # Bypass the form-validation layer and feed a negative number
        # directly to save_manual_entries via save_with_lock.
        outcome = save_with_lock(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=-1)],
            lock_path=lock,
        )
        assert outcome.ok is False
        assert outcome.lock_busy is False
        assert "non-negative" in (outcome.error or "")

        assert session.query(DepartmentYearly).count() == 0
        assert session.query(Department).count() == 0
        session.refresh(doc)
        assert doc.ingest_status == "ocr_pending"


def test_save_with_lock_rejects_invalid_method_without_taking_lock(engine, tmp_path):
    """Methods outside the whitelist must short-circuit before we even
    try to acquire the lock — a typo in the wiring shouldn't queue
    behind the weekly runner."""
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="M学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="m", fiscal_year=2026)
        session.commit()

        from eidp.pipeline.manual_entry import DepartmentEntry

        outcome = save_with_lock(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
            method="bogus",
            lock_path=lock,
        )
        assert outcome.ok is False
        assert outcome.lock_busy is False
        assert "method must be one of" in (outcome.error or "")


def test_save_outcome_default_shape():
    """Defensive sanity — ``SaveOutcome`` defaults are explicit so the
    page can rely on every field being present."""
    o = SaveOutcome(ok=True)
    assert o.lock_busy is False
    assert o.lock_owner is None
    assert o.error is None
