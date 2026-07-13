from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from streamlit.testing.v1 import AppTest

from eidp.db.locking import acquire_lock
from eidp.db.models import Base, ExtractionReviewDecision, ManualActionLog
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord
from eidp.pipeline.extraction_queue import process_intake_record
from eidp.pipeline.pdf_intake import PdfKind, store_pdf_upload, validate_intake_metadata

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
TEST_IDENTITY = ResolvedIdentity("app-test-reviewer", IdentitySource.CONFIGURED_FALLBACK)


@dataclass(frozen=True)
class ReviewAppFixture:
    intake_root: Path
    engine: Engine
    session_factory: sessionmaker[Session]
    base_json_bytes: dict[Path, bytes]


def _render_extraction_review_for_test(intake_root, session_factory):  # noqa: ANN001, ANN201
    from eidp.identity import IdentitySource, ResolvedIdentity
    from eidp.web.views.extraction_review import render_extraction_review_page

    render_extraction_review_page(
        identity=ResolvedIdentity("app-test-reviewer", IdentitySource.CONFIGURED_FALLBACK),
        intake_root=intake_root,
        session_factory=session_factory,
    )


def _department_record() -> TableDepartmentRecord:
    return TableDepartmentRecord(
        field_category="文化教養",
        course_name="専門課程",
        department_name="テスト学科",
        capacity=40,
        enrollment=None,
        intl_students=None,
        evidence=(
            CellEvidence(
                page_no=0,
                table_index=1,
                row_index=3,
                col_index=4,
                raw_label="収容定員",
                raw_value="40",
                canonical_metric="capacity",
            ),
        ),
    )


@pytest.fixture()
def review_app(tmp_path: Path):
    metadata = validate_intake_metadata(
        school_name="東京テスト専門学校",
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        uploaded_filename="form.pdf",
    )
    intake = store_pdf_upload(
        metadata=metadata,
        pdf_bytes=PDF_BYTES,
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.TEXT,
    )
    process_intake_record(
        intake_root=tmp_path,
        intake_record_id=intake.record_id,
        extractor_func=lambda _path: [_department_record()],
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'review-app.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    # The first render creates immutable base review candidates.
    from eidp.pipeline.extraction_review import ensure_review_records

    ensure_review_records(tmp_path)
    base_json_bytes = {path: path.read_bytes() for path in (tmp_path / "extraction" / "reviews").glob("*.json")}
    yield ReviewAppFixture(tmp_path, engine, factory, base_json_bytes)
    engine.dispose()


def _run_review_app(
    fixture: ReviewAppFixture,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> AppTest:
    app = AppTest.from_function(
        _render_extraction_review_for_test,
        args=(fixture.intake_root, session_factory or fixture.session_factory),
    ).run(timeout=10)
    assert not app.exception
    return app


def _button(app: AppTest, label: str):  # noqa: ANN202
    return next(button for button in app.button if button.label == label)


def _assert_base_json_unchanged(fixture: ReviewAppFixture) -> None:
    assert {path: path.read_bytes() for path in fixture.base_json_bytes} == fixture.base_json_bytes


@pytest.mark.parametrize(
    ("button_label", "expected_decision", "expected_status", "corrected_value", "note", "expected_note"),
    [
        ("Accept", "accept", "accepted", None, "source checked", "source checked"),
        ("Correct", "correct", "corrected", 47, "official correction", "official correction"),
        ("Needs review", "needs_review", "needs_review", None, "second reviewer", "second reviewer"),
        ("Exclude", "exclude", "excluded", None, f"  {'x' * 500}  ", "x" * 500),
    ],
)
def test_all_review_actions_commit_decision_and_audit_then_export_identity_without_reviewed_by(
    review_app: ReviewAppFixture,
    button_label: str,
    expected_decision: str,
    expected_status: str,
    corrected_value: int | None,
    note: str,
    expected_note: str,
) -> None:
    app = _run_review_app(review_app)
    assert all(widget.label != "reviewed_by" for widget in app.text_input)
    next(widget for widget in app.text_area if widget.label == "review_note").set_value(note)
    if corrected_value is not None:
        next(widget for widget in app.number_input if widget.label == "corrected_value").set_value(corrected_value)

    _button(app, button_label).click()
    app.run(timeout=10)

    assert not app.exception
    with Session(review_app.engine) as session:
        decision = session.scalar(select(ExtractionReviewDecision))
        audit = session.scalar(select(ManualActionLog))
        assert decision is not None
        assert audit is not None
        assert decision.audit_action_id == audit.action_id
        assert decision.decision == expected_decision
        assert decision.corrected_value == corrected_value
        assert decision.note == expected_note
        assert decision.actor == TEST_IDENTITY.actor
        assert decision.identity_source == TEST_IDENTITY.source.value
    payload = json.loads(
        (review_app.intake_root / "audit" / "manual-actions.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert payload["actor"] == TEST_IDENTITY.actor
    assert payload["identity_source"] == TEST_IDENTITY.source.value
    assert payload["reason"] == expected_note
    rows = app.dataframe[0].value.to_dict("records")
    assert next(row for row in rows if row["review_id"] == decision.review_id)["review_status"] == expected_status
    _assert_base_json_unchanged(review_app)


def test_busy_lock_writes_neither_decision_audit_json_nor_jsonl(review_app: ReviewAppFixture) -> None:
    app = _run_review_app(review_app)

    with acquire_lock(review_app.intake_root / ".lock", owner="background_job"):
        _button(app, "Accept").click()
        app.run(timeout=10)

    assert not app.exception
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is None
        assert session.scalar(select(ManualActionLog)) is None
    assert not (review_app.intake_root / "audit" / "manual-actions.jsonl").exists()
    _assert_base_json_unchanged(review_app)


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_exclude_invalid_reason_shows_error_and_writes_nothing(
    review_app: ReviewAppFixture,
    reason: str,
) -> None:
    app = _run_review_app(review_app)
    next(widget for widget in app.text_area if widget.label == "review_note").set_value(reason)

    _button(app, "Exclude").click()
    app.run(timeout=10)

    assert not app.exception
    assert any("reason must be between 1 and 500 characters" in message.value for message in app.error)
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is None
        assert session.scalar(select(ManualActionLog)) is None
    assert not (review_app.intake_root / "audit" / "manual-actions.jsonl").exists()
    _assert_base_json_unchanged(review_app)


def test_new_app_sessions_overlay_the_highest_database_revision(review_app: ReviewAppFixture) -> None:
    first_app = _run_review_app(review_app)
    _button(first_app, "Accept").click()
    first_app.run(timeout=10)

    with Session(review_app.engine) as session:
        first_decision = session.scalar(select(ExtractionReviewDecision))
        assert first_decision is not None
        review_id = first_decision.review_id

    second_app = _run_review_app(review_app)
    second_rows = second_app.dataframe[0].value.to_dict("records")
    assert next(row for row in second_rows if row["review_id"] == review_id)["review_status"] == "accepted"
    next(widget for widget in second_app.number_input if widget.label == "corrected_value").set_value(49)
    _button(second_app, "Correct").click()
    second_app.run(timeout=10)

    third_app = _run_review_app(review_app)
    third_rows = third_app.dataframe[0].value.to_dict("records")
    visible = next(row for row in third_rows if row["review_id"] == review_id)
    assert visible["review_status"] == "corrected"
    assert visible["corrected_value"] == 49
    with Session(review_app.engine) as session:
        decisions = session.scalars(
            select(ExtractionReviewDecision)
            .where(ExtractionReviewDecision.review_id == review_id)
            .order_by(ExtractionReviewDecision.revision)
        ).all()
        assert [decision.revision for decision in decisions] == [1, 2]
    _assert_base_json_unchanged(review_app)


def test_audit_outbox_runs_only_after_the_decision_commit(
    review_app: ReviewAppFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eidp.web.views import extraction_review as page

    real_flush = page.flush_audit_outbox
    committed_before_flush: list[bool] = []

    def assert_committed_then_flush(session: Session, *, jsonl_path: Path | None = None) -> dict[str, int]:
        with Session(review_app.engine) as probe:
            committed_before_flush.append(probe.scalar(select(ExtractionReviewDecision)) is not None)
        return real_flush(session, jsonl_path=jsonl_path)

    monkeypatch.setattr(page, "flush_audit_outbox", assert_committed_then_flush)
    app = _run_review_app(review_app)

    _button(app, "Accept").click()
    app.run(timeout=10)

    assert not app.exception
    assert committed_before_flush == [True]


def test_outbox_failure_preserves_committed_decision_and_records_error(
    review_app: ReviewAppFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fsync(_fd: int) -> None:
        raise OSError("disk flush failed")

    monkeypatch.setattr("eidp.db.audit_outbox.os.fsync", fail_fsync)
    app = _run_review_app(review_app)

    _button(app, "Accept").click()
    app.run(timeout=10)

    assert not app.exception
    assert any("database decision is preserved" in message.value for message in app.warning)
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is not None
        audit = session.scalar(select(ManualActionLog))
        assert audit is not None
        assert audit.jsonl_exported_at is None
        assert audit.jsonl_export_error == "disk flush failed"
    _assert_base_json_unchanged(review_app)


def test_outbox_initial_open_failure_preserves_decision_and_reports_projection_pending(
    review_app: ReviewAppFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outbox_path = review_app.intake_root / "audit" / "manual-actions.jsonl"
    original_open = Path.open

    def fail_target_open(self: Path, *args: object, **kwargs: object):  # noqa: ANN202
        mode = args[0] if args else kwargs.get("mode", "r")
        if self == outbox_path and "a" in str(mode):
            raise PermissionError("outbox open denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_target_open)
    app = _run_review_app(review_app)

    _button(app, "Accept").click()
    app.run(timeout=10)

    assert not app.exception
    assert not any("No decision was recorded" in message.value for message in app.error)
    assert any("database decision is preserved" in message.value for message in app.warning)
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is not None
        audit = session.scalar(select(ManualActionLog))
        assert audit is not None
        assert audit.jsonl_exported_at is None
        assert audit.jsonl_export_error == "outbox open denied"
    _assert_base_json_unchanged(review_app)


def test_audit_insert_failure_rolls_back_both_rows(review_app: ReviewAppFixture) -> None:
    def fail_audit_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected audit insert failure")

    event.listen(ManualActionLog, "before_insert", fail_audit_insert)
    try:
        app = _run_review_app(review_app)
        _button(app, "Accept").click()
        app.run(timeout=10)
    finally:
        event.remove(ManualActionLog, "before_insert", fail_audit_insert)

    assert not app.exception
    assert any("No decision was recorded" in message.value for message in app.error)
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is None
        assert session.scalar(select(ManualActionLog)) is None
    assert not (review_app.intake_root / "audit" / "manual-actions.jsonl").exists()
    _assert_base_json_unchanged(review_app)


def test_commit_failure_rolls_back_both_rows(review_app: ReviewAppFixture) -> None:
    class CommitFailingSession(Session):
        def commit(self) -> None:
            raise RuntimeError("injected commit failure")

    failing_factory = sessionmaker(
        bind=review_app.engine,
        class_=CommitFailingSession,
        expire_on_commit=False,
    )
    app = _run_review_app(review_app, session_factory=failing_factory)

    _button(app, "Accept").click()
    app.run(timeout=10)

    assert not app.exception
    assert any("No decision was recorded" in message.value for message in app.error)
    with Session(review_app.engine) as session:
        assert session.scalar(select(ExtractionReviewDecision)) is None
        assert session.scalar(select(ManualActionLog)) is None
    assert not (review_app.intake_root / "audit" / "manual-actions.jsonl").exists()
    _assert_base_json_unchanged(review_app)
