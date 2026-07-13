from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from streamlit.testing.v1 import AppTest

from eidp.db.locking import acquire_lock
from eidp.db.models import (
    Base,
    DoubleCheckResolution,
    ExternalComparisonResult,
    ExternalComparisonRun,
    ManualActionLog,
)
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType
from eidp.pipeline.review_decision import ReviewDecision, apply_review_decision

EXTERNAL_CSV = """school_name,school_id,field_category,course_name,department_name,fiscal_year,metric,value
東京テスト専門学校,S-001,文化教養,専門課程,テスト学科,2026,capacity,40
""".encode()
TEST_IDENTITY = ResolvedIdentity("app-test-reviewer", IdentitySource.CONFIGURED_FALLBACK)


@dataclass(frozen=True)
class DoubleCheckAppFixture:
    intake_root: Path
    engine: Engine
    session_factory: sessionmaker[Session]


def _render_double_check_for_test(intake_root, session_factory):  # noqa: ANN001, ANN201
    from eidp.identity import IdentitySource, ResolvedIdentity
    from eidp.web.views.double_check import render_double_check_page

    render_double_check_page(
        identity=ResolvedIdentity("app-test-reviewer", IdentitySource.CONFIGURED_FALLBACK),
        intake_root=intake_root,
        session_factory=session_factory,
    )


def _record() -> ExtractionReviewRecord:
    return ExtractionReviewRecord(
        review_id="metric-review-1",
        task_type=ReviewTaskType.EXTRACTED_METRIC,
        intake_record_id="intake-1",
        school_name="東京テスト専門学校",
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        source_pdf="source.pdf",
        department_name="テスト学科",
        field_category="文化教養",
        course_name="専門課程",
        metric="capacity",
        extracted_value=37,
        corrected_value=999,
        confidence=0.9,
        page_no=0,
        table_index=1,
        row_index=2,
        col_index=3,
        raw_label="収容定員",
        raw_value="37",
        canonical_metric="capacity",
        review_status=ReviewStatus.CORRECTED,
        review_note="untrusted base JSON decision",
        reviewed_by="untrusted-json-actor",
        reviewed_at="2026-07-13T00:00:00+00:00",
        next_action=None,
        created_at_utc="2026-07-13T00:00:00+00:00",
        updated_at_utc="2026-07-13T00:00:00+00:00",
    )


def _write_base_review_record(intake_root: Path, record: ExtractionReviewRecord) -> None:
    payload = asdict(record)
    payload["task_type"] = record.task_type.value
    payload["review_status"] = record.review_status.value
    payload["next_action"] = record.next_action.value if record.next_action is not None else None
    reviews_dir = intake_root / "extraction" / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / f"{record.review_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


@pytest.fixture()
def double_check_app(tmp_path: Path):  # noqa: ANN201
    intake_root = tmp_path / "intake"
    record = _record()
    _write_base_review_record(intake_root, record)
    engine = create_engine(f"sqlite:///{tmp_path / 'double-check-app.sqlite3'}", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # noqa: ANN001, ANN202
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        apply_review_decision(
            session,
            record=record,
            decision=ReviewDecision.CORRECT,
            corrected_value=41,
            note="official table checked",
            identity=TEST_IDENTITY,
        )
        session.commit()
    yield DoubleCheckAppFixture(intake_root, engine, factory)
    engine.dispose()


def _run_app(fixture: DoubleCheckAppFixture) -> AppTest:
    app = AppTest.from_function(
        _render_double_check_for_test,
        args=(fixture.intake_root, fixture.session_factory),
    ).run(timeout=10)
    assert not app.exception
    return app


def _button(app: AppTest, label: str):  # noqa: ANN202
    return next(button for button in app.button if button.label == label)


def _upload_external(app: AppTest) -> None:
    next(widget for widget in app.file_uploader if widget.label == "External extraction CSV/XLSX").upload(
        "copilot.csv",
        EXTERNAL_CSV,
        "text/csv",
    )
    app.run(timeout=10)
    assert not app.exception


def _create_run(app: AppTest) -> None:
    _upload_external(app)
    _button(app, "Create comparison run").click()
    app.run(timeout=10)
    assert not app.exception


def _persisted_rows(app: AppTest) -> list[dict[str, object]]:
    for dataframe in app.dataframe:
        if "comparison_result_id" in dataframe.value.columns:
            return dataframe.value.to_dict("records")
    raise AssertionError("persisted comparison result table is not rendered")


def _configure_resolution(
    app: AppTest,
    *,
    outcome: str,
    reason: str,
    value: int | None,
) -> None:
    next(widget for widget in app.selectbox if widget.label == "resolution_outcome").select(outcome)
    app.run(timeout=10)
    assert not app.exception
    next(widget for widget in app.text_area if widget.label == "resolution_reason").set_value(reason)
    if value is not None:
        next(widget for widget in app.number_input if widget.label == "resolution_value").set_value(value)


def _resolution_audits(session: Session) -> list[ManualActionLog]:
    return list(
        session.scalars(
            select(ManualActionLog).where(ManualActionLog.action_type == "double_check_resolution")
        ).all()
    )


def test_double_check_app_accepts_temporary_session_factory_for_persistent_runs(
    double_check_app: DoubleCheckAppFixture,
) -> None:
    app = _run_app(double_check_app)
    assert all(widget.label not in {"reviewer", "reviewed_by", "actor"} for widget in app.text_input)

    _upload_external(app)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(func.count()).select_from(ExternalComparisonRun)) == 0

    _button(app, "Create comparison run").click()
    app.run(timeout=10)

    assert not app.exception
    with Session(double_check_app.engine) as session:
        run = session.scalar(select(ExternalComparisonRun))
        result = session.scalar(select(ExternalComparisonResult))
        assert run is not None
        assert result is not None
        assert result.run_id == run.run_id
        assert result.eidp_value == 41
        assert result.external_value == 40
        assert result.comparison_status == "value_mismatch"
        assert (double_check_app.intake_root / run.external_file_path).read_bytes() == EXTERNAL_CSV

    restarted = _run_app(double_check_app)
    visible = _persisted_rows(restarted)
    assert len(visible) == 1
    assert visible[0]["comparison_result_id"] == result.id
    assert visible[0]["comparison_status"] == "value_mismatch"
    assert visible[0]["eidp_value"] == 41
    assert visible[0]["external_value"] == 40


@pytest.mark.parametrize(
    ("outcome", "value", "effective_value"),
    [
        ("accept_eidp", None, 41),
        ("accept_external", 40, 40),
        ("correct", 43, 43),
        ("exclude", None, None),
    ],
)
def test_all_resolution_outcomes_commit_decision_and_audit_then_project_jsonl(
    double_check_app: DoubleCheckAppFixture,
    outcome: str,
    value: int | None,
    effective_value: int | None,
) -> None:
    app = _run_app(double_check_app)
    _create_run(app)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome=outcome, reason="source evidence checked", value=value)

    _button(restarted, "Save resolution").click()
    restarted.run(timeout=10)

    assert not restarted.exception
    with Session(double_check_app.engine) as session:
        resolution = session.scalar(select(DoubleCheckResolution))
        audits = _resolution_audits(session)
        assert resolution is not None
        assert len(audits) == 1
        assert resolution.audit_action_id == audits[0].action_id
        assert resolution.outcome == outcome
        assert resolution.corrected_value == value
        assert resolution.effective_value == effective_value
        assert resolution.reason == "source evidence checked"
        assert resolution.actor == TEST_IDENTITY.actor
        assert resolution.identity_source == TEST_IDENTITY.source.value

    payloads = [
        json.loads(line)
        for line in (double_check_app.intake_root / "audit" / "manual-actions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    payload = next(item for item in payloads if item["action_type"] == "double_check_resolution")
    assert payload["actor"] == TEST_IDENTITY.actor
    assert payload["identity_source"] == TEST_IDENTITY.source.value
    assert payload["reason"] == "source evidence checked"
    assert payload["new_value"]["outcome"] == outcome
    assert payload["new_value"]["effective_value"] == effective_value

    newest = _run_app(double_check_app)
    assert _persisted_rows(newest)[0]["resolution_outcome"] == outcome
    assert _persisted_rows(newest)[0]["effective_value"] == effective_value


@pytest.mark.parametrize(
    ("outcome", "reason", "value", "expected_error"),
    [
        ("accept_eidp", "", None, "reason is required"),
        ("accept_eidp", " " * 3, None, "reason is required"),
        ("accept_external", "checked", 99, "must equal the snapshot external value"),
        ("correct", "checked", -1, "must be non-negative"),
    ],
)
def test_blank_or_invalid_resolution_writes_nothing(
    double_check_app: DoubleCheckAppFixture,
    outcome: str,
    reason: str,
    value: int | None,
    expected_error: str,
) -> None:
    app = _run_app(double_check_app)
    _create_run(app)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome=outcome, reason=reason, value=value)

    _button(restarted, "Save resolution").click()
    restarted.run(timeout=10)

    assert not restarted.exception
    assert any(expected_error in message.value for message in restarted.error)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(DoubleCheckResolution)) is None
        assert _resolution_audits(session) == []
    assert not (double_check_app.intake_root / "audit" / "manual-actions.jsonl").exists()


def test_busy_lock_prevents_comparison_run_creation(double_check_app: DoubleCheckAppFixture) -> None:
    app = _run_app(double_check_app)
    _upload_external(app)

    with acquire_lock(double_check_app.intake_root / ".lock", owner="background_job"):
        _button(app, "Create comparison run").click()
        app.run(timeout=10)

    assert not app.exception
    assert any("background_job" in message.value for message in app.error)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(ExternalComparisonRun)) is None
        assert session.scalar(select(ExternalComparisonResult)) is None
    assert not (double_check_app.intake_root / "external").exists()


def test_busy_lock_prevents_resolution_and_audit(double_check_app: DoubleCheckAppFixture) -> None:
    app = _run_app(double_check_app)
    _create_run(app)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome="accept_eidp", reason="checked", value=None)

    with acquire_lock(double_check_app.intake_root / ".lock", owner="background_job"):
        _button(restarted, "Save resolution").click()
        restarted.run(timeout=10)

    assert not restarted.exception
    assert any("background_job" in message.value for message in restarted.error)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(DoubleCheckResolution)) is None
        assert _resolution_audits(session) == []
    assert not (double_check_app.intake_root / "audit" / "manual-actions.jsonl").exists()


@pytest.mark.parametrize("tamper_mode", ["symlink", "replacement"])
def test_persisted_report_download_rejects_symlink_or_hash_mismatch(
    double_check_app: DoubleCheckAppFixture,
    tamper_mode: str,
) -> None:
    app = _run_app(double_check_app)
    _create_run(app)
    with Session(double_check_app.engine) as session:
        run = session.scalar(select(ExternalComparisonRun))
        assert run is not None
        report_path = double_check_app.intake_root / run.report_path

    if tamper_mode == "symlink":
        replacement = double_check_app.intake_root / "not-the-persisted-report.csv"
        replacement.write_bytes(b"unrelated local content")
        report_path.unlink()
        report_path.symlink_to(replacement)
    else:
        report_path.write_bytes(b"substituted report bytes")

    restarted = _run_app(double_check_app)

    assert any("report is unavailable" in message.value for message in restarted.warning)
    assert not [
        button
        for button in restarted.get("download_button")
        if button.label == "Download double_check_report.csv"
    ]


def test_audit_projection_runs_only_after_resolution_commit(
    double_check_app: DoubleCheckAppFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eidp.web.views import double_check as page

    app = _run_app(double_check_app)
    _create_run(app)
    real_flush = page.flush_audit_outbox
    committed_before_flush: list[bool] = []

    def assert_committed_then_flush(session: Session, *, jsonl_path: Path | None = None) -> dict[str, int]:
        with Session(double_check_app.engine) as probe:
            committed_before_flush.append(probe.scalar(select(DoubleCheckResolution)) is not None)
        return real_flush(session, jsonl_path=jsonl_path)

    monkeypatch.setattr(page, "flush_audit_outbox", assert_committed_then_flush)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome="accept_eidp", reason="checked", value=None)

    _button(restarted, "Save resolution").click()
    restarted.run(timeout=10)

    assert not restarted.exception
    assert committed_before_flush == [True]


def test_projection_failure_preserves_committed_resolution_and_reports_pending_retry(
    double_check_app: DoubleCheckAppFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(double_check_app)
    _create_run(app)

    def fail_fsync(_fd: int) -> None:
        raise OSError("disk flush failed")

    monkeypatch.setattr("eidp.db.audit_outbox.os.fsync", fail_fsync)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome="accept_external", reason="external source checked", value=40)

    _button(restarted, "Save resolution").click()
    restarted.run(timeout=10)

    assert not restarted.exception
    assert any("database decision is preserved" in message.value for message in restarted.warning)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(DoubleCheckResolution)) is not None
        audit = session.scalar(
            select(ManualActionLog).where(ManualActionLog.action_type == "double_check_resolution")
        )
        assert audit is not None
        assert audit.jsonl_exported_at is None
        assert audit.jsonl_export_error == "disk flush failed"


def test_audit_insert_failure_rolls_back_resolution(double_check_app: DoubleCheckAppFixture) -> None:
    app = _run_app(double_check_app)
    _create_run(app)
    restarted = _run_app(double_check_app)
    _configure_resolution(restarted, outcome="accept_eidp", reason="checked", value=None)

    def fail_audit_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected audit insert failure")

    event.listen(ManualActionLog, "before_insert", fail_audit_insert)
    try:
        _button(restarted, "Save resolution").click()
        restarted.run(timeout=10)
    finally:
        event.remove(ManualActionLog, "before_insert", fail_audit_insert)

    assert not restarted.exception
    assert any("No resolution was recorded" in message.value for message in restarted.error)
    with Session(double_check_app.engine) as session:
        assert session.scalar(select(DoubleCheckResolution)) is None
        assert _resolution_audits(session) == []
    assert not (double_check_app.intake_root / "audit" / "manual-actions.jsonl").exists()
