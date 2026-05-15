"""Sprint 8.4.a — manual_entry data contract regression.

The contract owner pinned in v6:
  1. extraction_method ∈ {"manual", "ocr_tesseract"}.
  2. verified=True for every row.
  3. document_id always bound (audit traceability).
  4. extraction_confidence=1.0 for "manual"; OCR contributes its own.
  5. manual_action_log row per write.
  6. Append-only — prior current revision demoted.
  7. DepartmentChange ONLY when dept_change explicitly set on the entry.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Query, Session

from eidp.db.models import (
    Department,
    DepartmentChange,
    DepartmentYearly,
    Document,
    ManualActionLog,
    School,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.pipeline.manual_entry import (
    DepartmentEntry,
    save_manual_entries,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "manual_entry.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed(session: Session, *, fiscal_year: int = 2026) -> tuple[School, Document]:
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
        source_url="https://example.com/manual.pdf",
        file_hash=("a" * 64),
        pdf_type="target",
        content_type="image",  # the typical manual-entry trigger
        fiscal_year=fiscal_year,
        ingest_status="ocr_pending",
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    return school, doc


# ---------------------------------------------------------------------------
# Headline contract
# ---------------------------------------------------------------------------


def test_save_manual_entries_creates_dept_yearly_with_manual_metadata(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[
                DepartmentEntry(canonical_name="テスト学科", capacity=40, enrollment=42, graduates=10),
            ],
            reason="image PDF — operator typed enrolment",
        )
        session.commit()

        assert result.rows_written == 1
        assert result.departments_created == 1
        assert result.department_changes_written == 0

        dy = session.query(DepartmentYearly).one()
        assert dy.extraction_method == "manual"
        assert dy.verified is True
        assert dy.document_id == doc.id
        # extraction_confidence is Numeric(4,3) — compare via float()
        assert float(dy.extraction_confidence) == 1.0
        assert dy.is_current is True
        assert dy.revision == 1
        assert dy.enrollment == 42

        # Department was auto-created with NFKC-canonicalised name.
        dept = session.query(Department).one()
        assert dept.canonical_name == "テスト学科"


def test_audit_log_written_per_yearly_row(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
            reason="op note",
        )
        session.commit()

        actions = session.query(ManualActionLog).all()
        # Three actions (8.4.a.1): department create + department_yearly
        # insert + document promotion from ocr_pending → ingested.
        types = sorted(a.target_table for a in actions)
        assert types == ["department", "department_yearly", "document"]
        for a in actions:
            assert a.action_type == "manual_entry"
            assert a.actor == "operator"
            assert a.document_id == doc.id


def test_append_only_demotes_prior_current_revision(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=12)],
        )
        session.commit()

        rows = (
            session.query(DepartmentYearly)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert rows[1].enrollment == 12


def test_manual_entry_locks_existing_yearly_rows_before_append(engine, monkeypatch):
    """Manual entry shares the append-only revision contract with ingest.

    SQLite does not enforce ``FOR UPDATE``, so this pins the SQLAlchemy call
    shape directly. Without the row lock, two Postgres writers can both read
    the same max revision/current row and then race on the insert/demotion pair.
    """
    lock_calls: list[tuple[object, ...]] = []
    original_with_for_update = Query.with_for_update

    def spy_with_for_update(self: Query, *args: object, **kwargs: object) -> Query:
        entities = tuple(desc.get("entity") for desc in self.column_descriptions)
        if DepartmentYearly in entities:
            lock_calls.append(entities)
        return original_with_for_update(self, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", spy_with_for_update)

    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()

    assert lock_calls, "save_manual_entries must lock DepartmentYearly rows before append"


def test_department_change_only_written_when_explicit(engine):
    """Plain number corrections (dept_change=None) MUST NOT emit a
    DepartmentChange row. Owner-pinned contract — otherwise the
    reconciler will mistake operator data fixes for institutional churn."""
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        # First write — creates dept + yearly. Plain entry, no change.
        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()
        assert session.query(DepartmentChange).count() == 0

        # Operator fixes a typo — still no DepartmentChange.
        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=11)],
        )
        session.commit()
        assert session.query(DepartmentChange).count() == 0


def test_department_change_written_on_explicit_classification(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(
                canonical_name="新設学科",
                enrollment=20,
                dept_change="新設",
                old_name=None,
            )],
        )
        session.commit()

        assert result.department_changes_written == 1
        change = session.query(DepartmentChange).one()
        assert change.change_type == "新設"
        assert change.fiscal_year == 2026
        assert change.verified is True
        assert change.verified_by == "operator"

        actions = session.query(ManualActionLog).filter(
            ManualActionLog.target_table == "department_change"
        ).all()
        assert len(actions) == 1


def test_ocr_method_path_uses_breakdown_score(engine):
    """OCR-confirmed manual entries record method='ocr_tesseract' and
    pull confidence from the breakdown the caller supplies."""
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="OCR学科", enrollment=15)],
            method="ocr_tesseract",
            confidence_breakdown={"score": 0.78, "tsv_avg": 0.81, "yoy_sanity": 0.7},
        )
        session.commit()

        dy = session.query(DepartmentYearly).one()
        assert dy.extraction_method == "ocr_tesseract"
        assert dy.verified is True
        # 0.78 is the breakdown score
        assert float(dy.extraction_confidence) == pytest.approx(0.78, abs=0.01)
        assert "ocr_tesseract" not in (dy.confidence_breakdown or "") or "score" in (dy.confidence_breakdown or "")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_raises_when_document_missing(engine):
    with Session(engine) as session:
        with pytest.raises(ValueError, match="not found"):
            save_manual_entries(
                session, document_id=999, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A")],
            )


def test_empty_entries_is_no_op(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()
        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026, entries=[],
        )
        session.commit()
        assert result.rows_written == 0
        assert session.query(DepartmentYearly).count() == 0
        assert session.query(ManualActionLog).count() == 0


def test_empty_entries_does_not_backfill_fiscal_year(engine):
    """Sprint 8.4.a.2 — empty entries must be a strict no-op. The bug
    fixed here was: when Document.fiscal_year was None, the function
    short-circuited on empty entries AFTER backfilling, leaving a
    silent mutation with no audit. Test pins the corrected order:
    short-circuit happens before any mutation."""
    with Session(engine) as session:
        school = School(
            prefecture="東京都", corporation_name="テスト法人",
            school_name="テスト専門学校", school_type="専門学校", status="active",
        )
        session.add(school)
        session.flush()
        doc = Document(
            school_id=school.id,
            source_url="https://example.com/empty.pdf",
            file_hash=("d" * 64),
            pdf_type="target",
            content_type="image",
            fiscal_year=None,                    # null on purpose
            ingest_status="ocr_pending",
        )
        session.add(doc)
        session.commit()

        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026, entries=[],
        )
        session.commit()

        session.refresh(doc)
        assert doc.fiscal_year is None, (
            "empty entries must NOT backfill Document.fiscal_year — that "
            "would be a silent mutation with no audit row"
        )
        assert doc.ingest_status == "ocr_pending", (
            "empty entries must NOT promote ingest_status either"
        )
        assert session.query(ManualActionLog).count() == 0
        assert result.rows_written == 0
        assert result.document_status_changed_to is None


def test_invalid_method_raises(engine):
    """Sprint 8.4.a.1 — method must be in the allowed whitelist; a
    silent ``method='bogus'`` injection is no longer accepted."""
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()
        with pytest.raises(ValueError, match="method must be one of"):
            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
                method="bogus",  # type: ignore[arg-type]
            )


def test_fiscal_year_mismatch_raises(engine):
    """Sprint 8.4.a.1 — if doc.fiscal_year is set and differs from the
    requested fiscal_year, refuse and direct the operator to the
    fiscal-year override flow (which moves all four tables atomically)."""
    with Session(engine) as session:
        _, doc = _seed(session, fiscal_year=2025)
        session.commit()
        with pytest.raises(ValueError, match="fiscal_year_override"):
            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
            )


def test_fiscal_year_backfill_when_document_has_none(engine):
    """Sprint 8.4.a.1 — when Document.fiscal_year is None (typical for
    a fresh ocr_pending entry), save_manual_entries backfills the
    fiscal_year on the Document and audits the move."""
    with Session(engine) as session:
        # _seed default sets fiscal_year=2026; for this case we need a
        # document with fiscal_year=None.
        school = School(
            prefecture="東京都", corporation_name="テスト法人",
            school_name="テスト専門学校", school_type="専門学校", status="active",
        )
        session.add(school)
        session.flush()
        doc = Document(
            school_id=school.id,
            source_url="https://example.com/no-fy.pdf",
            file_hash=("c" * 64),
            pdf_type="target",
            content_type="image",
            fiscal_year=None,
            ingest_status="ocr_pending",
            downloaded_at=datetime.now(UTC),
        )
        session.add(doc)
        session.commit()

        save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()

        session.refresh(doc)
        assert doc.fiscal_year == 2026


def test_negative_numeric_field_raises(engine):
    """Sprint 8.4.a.1 — negative counts must be rejected at the pipeline
    boundary, even if a future caller bypasses UI validation."""
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()
        with pytest.raises(ValueError, match="enrollment.*non-negative"):
            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", enrollment=-1)],
            )


def test_dropout_rate_out_of_range_raises(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()
        with pytest.raises(ValueError, match="dropout_rate"):
            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", dropout_rate=1.5)],
            )


def test_success_clears_ocr_pending_queue(engine):
    """Sprint 8.4.a.1 — after a successful manual entry on an
    ocr_pending document, the Document's ingest_status must transition
    to 'ingested' so the queue surface clears, and the transition
    must be audited."""
    with Session(engine) as session:
        _, doc = _seed(session)  # _seed sets ingest_status='ocr_pending'
        session.commit()

        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()

        session.refresh(doc)
        assert doc.ingest_status == "ingested"
        assert result.document_status_changed_to == "ingested"

        # Audit row for the document target_table records the transition.
        doc_actions = (
            session.query(ManualActionLog)
            .filter(ManualActionLog.target_table == "document")
            .all()
        )
        assert len(doc_actions) == 1
        action = doc_actions[0]
        import json
        assert json.loads(action.old_value)["ingest_status"] == "ocr_pending"
        assert json.loads(action.new_value)["ingest_status"] == "ingested"


def test_success_clears_review_pending_and_parse_failed_queues(engine):
    """All three queued statuses (ocr_pending / parse_failed /
    review_pending) must be cleared by a successful manual entry."""
    for prior_status in ("parse_failed", "review_pending"):
        with Session(engine) as session:
            school = School(
                prefecture="東京都", corporation_name=f"法人_{prior_status}",
                school_name=f"学校_{prior_status}", school_type="専門学校", status="active",
            )
            session.add(school)
            session.flush()
            doc = Document(
                school_id=school.id,
                source_url=f"https://example.com/{prior_status}.pdf",
                file_hash=(prior_status.ljust(64, "0"))[:64],
                pdf_type="target",
                content_type="text",
                fiscal_year=2026,
                ingest_status=prior_status,
            )
            session.add(doc)
            session.commit()

            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
            )
            session.commit()

            session.refresh(doc)
            assert doc.ingest_status == "ingested", (
                f"prior={prior_status} did not clear to ingested"
            )


def test_success_does_not_change_already_ingested_status(engine):
    """If the Document is already 'ingested' (e.g. operator is fixing
    a typo on a confirmed row), the status MUST NOT be re-promoted
    and no document audit row should fire."""
    with Session(engine) as session:
        _, doc = _seed(session)
        doc.ingest_status = "ingested"
        session.commit()

        result = save_manual_entries(
            session, document_id=doc.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="A学科", enrollment=10)],
        )
        session.commit()

        assert result.document_status_changed_to is None
        doc_actions = (
            session.query(ManualActionLog)
            .filter(ManualActionLog.target_table == "document")
            .all()
        )
        assert len(doc_actions) == 0, "no document audit row when status was already ingested"


def test_canonical_name_required(engine):
    with Session(engine) as session:
        _, doc = _seed(session)
        session.commit()
        with pytest.raises(ValueError, match="canonical_name"):
            save_manual_entries(
                session, document_id=doc.id, fiscal_year=2026,
                entries=[DepartmentEntry(canonical_name="")],
            )


def test_nfkc_normalisation_collapses_fullwidth_aliases(engine):
    """Entering 'ＡＢＣ学科' (full-width A B C) and 'ABC学科' (half-width)
    must resolve to the SAME Department, not create two.

    Sprint 8.4.a.1 made fiscal_year-mismatch on a single Document a hard
    error (same PDF cannot be both the previous and target year — that needs override). So
    we use two separate documents, one per fiscal year, to exercise the
    NFKC dedup path."""
    with Session(engine) as session:
        school, doc1 = _seed(session, fiscal_year=2026)
        # Second document targets fiscal_year 2027 — different doc, same
        # school — so the NFKC dedup happens on Department, not via the
        # forbidden cross-year reuse of one Document.
        doc2 = Document(
            school_id=school.id,
            source_url="https://example.com/manual2.pdf",
            file_hash=("b" * 64),
            pdf_type="target",
            content_type="image",
            fiscal_year=2027,
            ingest_status="ocr_pending",
            downloaded_at=datetime.now(UTC),
        )
        session.add(doc2)
        session.commit()

        save_manual_entries(
            session, document_id=doc1.id, fiscal_year=2026,
            entries=[DepartmentEntry(canonical_name="ＡＢＣ学科", enrollment=10)],
        )
        session.commit()
        save_manual_entries(
            session, document_id=doc2.id, fiscal_year=2027,
            entries=[DepartmentEntry(canonical_name="ABC学科", enrollment=12)],
        )
        session.commit()

        depts = session.query(Department).all()
        assert len(depts) == 1, "NFKC-equivalent names must collapse to one Department"
