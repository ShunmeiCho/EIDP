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

from datetime import UTC, datetime
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
from eidp.review._pages.pdf_manual_entry import (
    MANUAL_QUEUE_VIEW_ALL,
    MANUAL_QUEUE_VIEW_TARGET,
    MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED,
    QUEUE_STATUSES,
    SaveOutcome,
    build_pdf_preview,
    coerce_focus_document_id,
    form_data_to_entries,
    latest_discovery_evidence,
    list_documents_for_manual_queue_view,
    list_pending_documents,
    manual_queue_view_options,
    prioritize_queue_document,
    resolve_pdf_path,
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
        discovered_from=f"https://example.com/{file_hash_seed}/page.html",
        file_hash=(file_hash_seed.ljust(64, "0"))[:64],
        pdf_type="target",
        content_type="image",
        fiscal_year=fiscal_year,
        ingest_status=status,
        confidence=0.82,
        downloaded_at=datetime.now(UTC),
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
        assert r.discovered_from and r.discovered_from.endswith("/b/page.html")
        assert r.pdf_type == "target"
        assert r.confidence == 0.82


def test_queue_respects_limit(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="L学校")
        for i in range(5):
            _seed_doc(session, school, status="ocr_pending", file_hash_seed=f"ll{i}")
        session.commit()

        rows = list_pending_documents(session, limit=3)
        assert len(rows) == 3


def test_queue_can_filter_to_one_document(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="Doc学校")
        first = _seed_doc(session, school, status="ocr_pending", file_hash_seed="doc1")
        second = _seed_doc(session, school, status="parse_failed", file_hash_seed="doc2")
        session.commit()

        rows = list_pending_documents(session, document_id=second.id)

        assert [r.document_id for r in rows] == [second.id]
        assert first.id not in {r.document_id for r in rows}


def test_queue_can_include_ingested_and_filter_target_year(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="FY学校")
        old_doc = _seed_doc(session, school, status="ingested", file_hash_seed="old", fiscal_year=2025)
        target_doc = _seed_doc(session, school, status="ingested", file_hash_seed="target", fiscal_year=2026)
        review_doc = _seed_doc(session, school, status="review_pending", file_hash_seed="review", fiscal_year=2026)
        _seed_doc(session, school, status="ocr_pending", file_hash_seed="unknown", fiscal_year=None)
        session.commit()

        rows = list_pending_documents(
            session,
            statuses=[*QUEUE_STATUSES, "ingested"],
            fiscal_year=2026,
        )

        assert [r.document_id for r in rows] == [target_doc.id, review_doc.id]
        assert old_doc.id not in {r.document_id for r in rows}


def test_manual_queue_default_hides_old_year_documents(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="Default学校")
        old_doc = _seed_doc(session, school, status="parse_failed", file_hash_seed="old", fiscal_year=2025)
        target_doc = _seed_doc(session, school, status="parse_failed", file_hash_seed="target", fiscal_year=2026)
        unknown_doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="unknown", fiscal_year=None)
        session.commit()

        rows = list_documents_for_manual_queue_view(
            session,
            view=MANUAL_QUEUE_VIEW_TARGET,
            target_fiscal_year=2026,
        )

        assert [row.document_id for row in rows] == [target_doc.id, unknown_doc.id]
        assert old_doc.id not in {row.document_id for row in rows}


def test_manual_queue_target_with_ingested_still_filters_old_year(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="Ingested学校")
        old_doc = _seed_doc(session, school, status="ingested", file_hash_seed="oldi", fiscal_year=2025)
        target_doc = _seed_doc(session, school, status="ingested", file_hash_seed="targeti", fiscal_year=2026)
        review_doc = _seed_doc(session, school, status="review_pending", file_hash_seed="reviewi", fiscal_year=2026)
        session.commit()

        rows = list_documents_for_manual_queue_view(
            session,
            view=MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED,
            target_fiscal_year=2026,
        )

        assert [row.document_id for row in rows] == [target_doc.id, review_doc.id]
        assert old_doc.id not in {row.document_id for row in rows}


def test_manual_queue_all_view_is_explicit_diagnostics(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="All学校")
        old_doc = _seed_doc(session, school, status="ingested", file_hash_seed="oldall", fiscal_year=2025)
        target_doc = _seed_doc(session, school, status="parse_failed", file_hash_seed="targetall", fiscal_year=2026)
        session.commit()

        rows = list_documents_for_manual_queue_view(
            session,
            view=MANUAL_QUEUE_VIEW_ALL,
            target_fiscal_year=2026,
        )

        assert [row.document_id for row in rows] == [old_doc.id, target_doc.id]


def test_manual_queue_focus_document_can_surface_school_task_selection(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="FocusView学校")
        old_doc = _seed_doc(session, school, status="parse_failed", file_hash_seed="focusold", fiscal_year=2025)
        target_doc = _seed_doc(session, school, status="parse_failed", file_hash_seed="focustarget", fiscal_year=2026)
        session.commit()

        rows = list_documents_for_manual_queue_view(
            session,
            view=MANUAL_QUEUE_VIEW_TARGET,
            target_fiscal_year=2026,
            focus_document_id=old_doc.id,
        )

        assert [row.document_id for row in rows] == [old_doc.id, target_doc.id]


def test_manual_queue_view_options_keep_stable_keys():
    options = manual_queue_view_options("2026年度（令和8年度）")

    assert set(options) == {
        MANUAL_QUEUE_VIEW_TARGET,
        MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED,
        MANUAL_QUEUE_VIEW_ALL,
    }
    assert options[MANUAL_QUEUE_VIEW_TARGET].startswith("2026年度")


def test_focus_document_helpers_move_requested_row_to_top(engine):
    with Session(engine) as session:
        school = _seed_school(session, name="Focus学校")
        first = _seed_doc(session, school, status="ocr_pending", file_hash_seed="focus1")
        second = _seed_doc(session, school, status="parse_failed", file_hash_seed="focus2")
        session.commit()

        rows = list_pending_documents(session)
        focused = prioritize_queue_document(rows, document_id=second.id)

        assert coerce_focus_document_id(str(second.id)) == second.id
        assert coerce_focus_document_id("bad") is None
        assert [row.document_id for row in focused] == [second.id, first.id]
        assert prioritize_queue_document(rows, document_id=None) == rows


def test_latest_discovery_evidence_reads_recent_candidate_decisions(tmp_path: Path):
    out = tmp_path / "output"
    out.mkdir()
    log = out / "discovery_rejections.jsonl"
    log.write_text(
        "\n".join([
            "{bad json",
            (
                '{"school_id": 1, "pdf_url": "https://example.ac.jp/old.pdf", '
                '"page_url": "https://example.ac.jp/", "reason": "fiscal_year_mismatch:2025", '
                '"anchor_text": "2025年度", "pattern_type": "direct", "score": 3.0, '
                '"pdf_type": "target", "timestamp": "2026-05-06T00:00:00Z"}'
            ),
            (
                '{"school_id": 1, "pdf_url": "https://example.ac.jp/r8.pdf", '
                '"page_url": "https://example.ac.jp/disclosure/", "reason": "accepted_downloaded", '
                '"anchor_text": "2026年度", "pattern_type": "direct", "score": 9.0, '
                '"pdf_type": "target", "timestamp": "2026-05-06T00:01:00Z"}'
            ),
            (
                '{"school_id": 2, "pdf_url": "https://other.ac.jp/r8.pdf", '
                '"page_url": "https://other.ac.jp/", "reason": "accepted_downloaded"}'
            ),
        ]),
        encoding="utf-8",
    )

    rows = latest_discovery_evidence(
        app_root=tmp_path,
        school_id=1,
        source_url="https://example.ac.jp/r8.pdf",
    )

    assert len(rows) == 2
    assert rows[0].reason == "accepted_downloaded"
    assert rows[0].pdf_url == "https://example.ac.jp/r8.pdf"
    assert rows[1].reason == "fiscal_year_mismatch:2025"


# ---------------------------------------------------------------------------
# PDF preview
# ---------------------------------------------------------------------------


def _make_pdf(path: Path, *, text: str = "hello") -> None:
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_resolve_pdf_path_handles_missing_absolute_and_relative(tmp_path):
    assert resolve_pdf_path(None, app_root=tmp_path) is None

    absolute = tmp_path / "a.pdf"
    assert resolve_pdf_path(str(absolute), app_root=tmp_path) == absolute
    assert resolve_pdf_path("data/pdfs/a.pdf", app_root=tmp_path) == tmp_path / "data/pdfs/a.pdf"


def test_build_pdf_preview_returns_png_and_download_bytes(tmp_path):
    pdf = tmp_path / "sample.pdf"
    _make_pdf(pdf, text="preview")

    preview = build_pdf_preview(str(pdf), dpi=72)
    assert preview.exists is True
    assert preview.error is None
    assert preview.page_count == 1
    assert preview.filename == "sample.pdf"
    assert preview.pdf_bytes is not None and preview.pdf_bytes.startswith(b"%PDF")
    assert preview.image_png is not None and preview.image_png.startswith(b"\x89PNG")


def test_build_pdf_preview_resolves_relative_path_from_app_root(tmp_path):
    pdf = tmp_path / "data" / "pdfs" / "sample.pdf"
    pdf.parent.mkdir(parents=True)
    _make_pdf(pdf)

    preview = build_pdf_preview("data/pdfs/sample.pdf", app_root=tmp_path, dpi=72)
    assert preview.error is None
    assert preview.path == pdf
    assert preview.image_png is not None


def test_build_pdf_preview_missing_file_returns_error(tmp_path):
    preview = build_pdf_preview("missing.pdf", app_root=tmp_path)
    assert preview.exists is False
    assert preview.image_png is None
    assert "does not exist" in (preview.error or "")


def test_build_pdf_preview_out_of_range_returns_error(tmp_path):
    pdf = tmp_path / "sample.pdf"
    _make_pdf(pdf)

    preview = build_pdf_preview(str(pdf), page_index=5, dpi=72)
    assert preview.exists is True
    assert preview.page_count == 1
    assert preview.image_png is None
    assert "out of range" in (preview.error or "")


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


# ---------------------------------------------------------------------------
# submit_form — UI wiring contract (Sprint 8.4.c.1.1)
# ---------------------------------------------------------------------------


def test_submit_form_routes_through_save_with_lock(engine, tmp_path, monkeypatch):
    """The page MUST go through save_with_lock — that is the single
    enforcement point for the shared advisory lock + the manual_entry
    contract. This regression monkeypatches save_with_lock and asserts
    submit_form calls it with the validated entries."""
    from eidp.review._pages import pdf_manual_entry as page_mod

    captured: dict = {}

    def fake_save_with_lock(session, **kwargs):
        captured.update(kwargs)
        return SaveOutcome(ok=True)

    monkeypatch.setattr(page_mod, "save_with_lock", fake_save_with_lock)

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="W学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="w", fiscal_year=2026)
        session.commit()

        validation, outcome = page_mod.submit_form(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            rows=[{"canonical_name": "A学科", "enrollment": 10}],
            reason="image PDF",
            lock_path=lock,
        )

    assert validation.ok, validation.errors
    assert outcome is not None
    assert outcome.ok is True
    assert captured["document_id"] == doc.id
    assert captured["fiscal_year"] == 2026
    assert captured["lock_path"] == lock
    assert captured["reason"] == "image PDF"
    assert len(captured["entries"]) == 1
    assert captured["entries"][0].canonical_name == "A学科"


def test_submit_form_returns_validation_errors_without_calling_save(engine, tmp_path, monkeypatch):
    """If form validation fails, save_with_lock must NOT be called.
    Pins the contract that the lock is never held while the operator
    is fixing input errors."""
    from eidp.review._pages import pdf_manual_entry as page_mod

    called = {"count": 0}

    def fake_save_with_lock(session, **kwargs):
        called["count"] += 1
        return SaveOutcome(ok=True)

    monkeypatch.setattr(page_mod, "save_with_lock", fake_save_with_lock)

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="V学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="v", fiscal_year=2026)
        session.commit()

        validation, outcome = page_mod.submit_form(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            rows=[{"canonical_name": "", "enrollment": 10}],  # missing name
            reason=None,
            lock_path=lock,
        )

    assert not validation.ok
    assert any("canonical_name" in e.field for e in validation.errors)
    assert outcome is None
    assert called["count"] == 0


def test_submit_form_rejects_when_no_valid_rows_remain(engine, tmp_path, monkeypatch):
    """If every row has at least one error, submit_form must NOT call
    save_with_lock even though the validation list happens to be empty
    of *successful* entries — that's a degenerate save."""
    from eidp.review._pages import pdf_manual_entry as page_mod

    called = {"count": 0}
    monkeypatch.setattr(
        page_mod, "save_with_lock",
        lambda *a, **kw: (called.__setitem__("count", called["count"] + 1) or SaveOutcome(ok=True)),
    )

    lock = tmp_path / ".lock"
    with Session(engine) as session:
        school = _seed_school(session, name="U学校")
        doc = _seed_doc(session, school, status="ocr_pending", file_hash_seed="u", fiscal_year=2026)
        session.commit()

        validation, outcome = page_mod.submit_form(
            session,
            document_id=doc.id,
            fiscal_year=2026,
            rows=[
                {"canonical_name": "", "enrollment": 1},
                {"canonical_name": "A", "enrollment": -5},
            ],
            reason=None,
            lock_path=lock,
        )

    assert not validation.ok
    assert outcome is None
    assert called["count"] == 0


def test_save_eligible_statuses_excludes_school_mismatch():
    """``school_mismatch`` documents are listed in the queue but must
    NOT have a save form rendered — the operator must fix the school
    binding first. This test pins the policy constant so a future
    page-mod change can't silently flip it."""
    from eidp.review._pages.pdf_manual_entry import SAVE_ELIGIBLE_STATUSES

    assert "school_mismatch" not in SAVE_ELIGIBLE_STATUSES
    assert SAVE_ELIGIBLE_STATUSES == frozenset({
        "ocr_pending", "parse_failed", "review_pending",
    })
