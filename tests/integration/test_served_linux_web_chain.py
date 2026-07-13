from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from streamlit.testing.v1 import AppTest

import eidp.db.session as db_session
from eidp.config import settings
from eidp.db.models import (
    Base,
    DoubleCheckResolution,
    ExternalComparisonResult,
    ExternalComparisonRun,
    ExtractionReviewDecision,
    ManualActionLog,
)
from eidp.pdf.master_ground_truth import fy_metric_columns
from eidp.pipeline.extraction_queue import ExtractionStatus, load_extracted_rows, load_extraction_queue
from eidp.pipeline.pdf_intake import IntakeLane, load_intake_queue

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "src/eidp/web/app.py"
SAMPLE_PDF = REPO_ROOT / "data/sample-pdfs/nkz.pdf"
SCHOOL_NAME = "E2Eテスト電子専門学校"
SCHOOL_ID = "S-E2E"
FISCAL_YEAR = 2025
CORPORATION_NAME = "学校法人E2E"
ACTOR = "served-chain-operator"
COURSE_ENROLLMENTS = {
    "ゲーム4年制学科(ゲーム企画コース)": 227,
    "ゲーム4年制学科(ゲーム制作コース)": 714,
    "ゲーム4年制学科(ゲームデザインコース)": 314,
}


@dataclass(frozen=True)
class ServedRuntime:
    root: Path
    data_dir: Path
    intake_root: Path
    engine: Engine
    session_factory: sessionmaker[Session]


@pytest.fixture()
def served_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[ServedRuntime]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_url = f"sqlite:///{data_dir / 'eidp.sqlite3'}"
    engine = create_engine(database_url, echo=False)
    db_session._install_sqlite_connect_hook(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr(settings, "app_root", tmp_path)
    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "identity_mode", "configured_fallback")
    monkeypatch.setattr(settings, "fallback_actor", ACTOR)
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", session_factory)

    yield ServedRuntime(tmp_path, data_dir, data_dir / "web-intake", engine, session_factory)
    engine.dispose()


def _root_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=90).run()
    assert not app.exception
    return app


def _button(app: AppTest, *, label: str):  # noqa: ANN202
    return next(button for button in app.button if button.label == label)


def _review_rows(app: AppTest) -> list[dict[str, object]]:
    return next(
        dataframe.value.to_dict("records")
        for dataframe in app.dataframe
        if "review_id" in dataframe.value.columns and "review_status" in dataframe.value.columns
    )


def _select_review_row(app: AppTest, department_name: str) -> None:
    label = f"{SCHOOL_NAME} / {department_name} / enrollment"
    next(widget for widget in app.selectbox if widget.label == "Review row").select(label)
    app.run(timeout=90)
    assert not app.exception


def _save_review_action(
    app: AppTest,
    *,
    department_name: str,
    action: str,
    note: str,
    corrected_value: int | None = None,
) -> None:
    _select_review_row(app, department_name)
    next(widget for widget in app.text_area if widget.label == "review_note").set_value(note)
    if corrected_value is not None:
        next(widget for widget in app.number_input if widget.label == "corrected_value").set_value(corrected_value)
    _button(app, label=action).click()
    app.run(timeout=90)
    assert not app.exception


def _write_master(path: Path) -> bytes:
    capacity_col, _enrollment_col, intl_col = fy_metric_columns(FISCAL_YEAR)
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "学科別"
    header = [None] * (intl_col + 1)
    header[capacity_col] = f"{FISCAL_YEAR}年度"
    worksheet.append(header)
    worksheet.append(["都道府県", "法人名", "学校名", "課程名", "学科名", "昼夜", "年限"])
    for department_name, enrollment in COURSE_ENROLLMENTS.items():
        row: list[object | None] = [None] * (intl_col + 1)
        row[:7] = ["東京都", CORPORATION_NAME, SCHOOL_NAME, "工業関係", department_name, "昼", "4"]
        row[capacity_col] = None
        row[_enrollment_col] = enrollment
        row[intl_col] = None
        worksheet.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    workbook.close()
    return path.read_bytes()


def _diff_rows(app: AppTest) -> list[dict[str, object]]:
    return next(
        dataframe.value.to_dict("records")
        for dataframe in app.dataframe
        if "match_status" in dataframe.value.columns
    )


def _external_csv() -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "school_name",
            "school_id",
            "corporation_name",
            "prefecture",
            "field_category",
            "course_name",
            "department_name",
            "fiscal_year",
            "metric",
            "value",
        ],
    )
    writer.writeheader()
    for department_name, enrollment in COURSE_ENROLLMENTS.items():
        writer.writerow(
            {
                "school_name": SCHOOL_NAME,
                "school_id": SCHOOL_ID,
                "corporation_name": CORPORATION_NAME,
                "prefecture": "東京都",
                "field_category": "工業関係",
                "course_name": "デジタル専門課程",
                "department_name": department_name,
                "fiscal_year": FISCAL_YEAR,
                "metric": "enrollment",
                "value": enrollment,
            }
        )
    return output.getvalue().encode("utf-8")


def _persisted_comparison_rows(app: AppTest) -> list[dict[str, object]]:
    return next(
        dataframe.value.to_dict("records")
        for dataframe in app.dataframe
        if "comparison_result_id" in dataframe.value.columns
    )


def test_served_linux_web_chain_persists_review_and_double_check_audit(served_runtime: ServedRuntime) -> None:
    app = _root_app()
    next(widget for widget in app.text_input if widget.key == "pdf_school_name").set_value(SCHOOL_NAME)
    next(widget for widget in app.text_input if widget.key == "pdf_school_id").set_value(SCHOOL_ID)
    next(widget for widget in app.number_input if widget.key == "pdf_fiscal_year").set_value(FISCAL_YEAR)
    next(widget for widget in app.text_input if widget.key == "pdf_source_page_url").set_value(
        "https://example.ac.jp/disclosure/"
    )
    next(widget for widget in app.file_uploader if widget.label == "PDF file").upload(
        "nkz.pdf",
        SAMPLE_PDF.read_bytes(),
        "application/pdf",
    )
    _button(app, label="Register PDF").click()
    app.run(timeout=90)

    assert not app.exception
    assert any("Registered" in message.value for message in app.success)
    intake_records = load_intake_queue(served_runtime.intake_root)
    assert len(intake_records) == 1
    intake_record = intake_records[0]
    assert intake_record.lane is IntakeLane.TEXT_MAIN

    app.switch_page("pages/02_extraction_queue.py").run(timeout=90)
    assert not app.exception
    next(button for button in app.button if button.key == f"run_extraction_{intake_record.record_id}").click()
    app.run(timeout=90)

    assert not app.exception
    queue_items = load_extraction_queue(served_runtime.intake_root)
    assert len(queue_items) == 1
    assert queue_items[0].status is ExtractionStatus.EXTRACTION_COMPLETED
    assert queue_items[0].rows_written == 84
    extracted_rows = load_extracted_rows(served_runtime.intake_root, intake_record.record_id)
    assert len(extracted_rows) == 84
    assert Counter(row.metric for row in extracted_rows) == {
        "capacity": 28,
        "enrollment": 28,
        "intl_students": 28,
    }
    enrollment_rows = [row for row in extracted_rows if row.metric == "enrollment"]
    source_nodes = {
        (row.page_no, row.table_index, row.row_index, row.field_category, row.course_name, row.department_name)
        for row in enrollment_rows
    }
    assert len(source_nodes) == 28
    assert all(
        row.page_no >= 0
        and row.table_index >= 0
        and row.row_index >= 0
        and row.col_index >= 0
        and row.raw_label
        and row.raw_value
        for row in extracted_rows
    )
    course_rows = {row.department_name: row for row in enrollment_rows if row.department_name in COURSE_ENROLLMENTS}
    assert {name: row.value for name, row in course_rows.items()} == COURSE_ENROLLMENTS
    assert all(row.field_category == "工業関係" for row in course_rows.values())
    assert all(row.course_name == "デジタル専門課程" for row in course_rows.values())
    with served_runtime.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ManualActionLog)) == 0
    assert not (served_runtime.data_dir / "audit/manual-actions.jsonl").exists()

    app.switch_page("pages/03_extraction_review.py").run(timeout=90)
    assert not app.exception
    initial_review_rows = _review_rows(app)
    review_ids = {
        str(row["department_name"]): str(row["review_id"])
        for row in initial_review_rows
        if row["metric"] == "enrollment" and row["department_name"] in COURSE_ENROLLMENTS
    }
    assert set(review_ids) == set(COURSE_ENROLLMENTS)
    reviews_dir = served_runtime.intake_root / "extraction/reviews"
    base_json_bytes = {path: path.read_bytes() for path in reviews_dir.glob("*.json")}
    assert len(base_json_bytes) == 84

    _save_review_action(
        app,
        department_name="ゲーム4年制学科(ゲーム企画コース)",
        action="Accept",
        note="official source checked",
    )
    _save_review_action(
        app,
        department_name="ゲーム4年制学科(ゲーム制作コース)",
        action="Correct",
        corrected_value=715,
        note="official enrollment correction",
    )
    _save_review_action(
        app,
        department_name="ゲーム4年制学科(ゲームデザインコース)",
        action="Exclude",
        note="outside approved scope",
    )
    assert {path: path.read_bytes() for path in base_json_bytes} == base_json_bytes

    fresh_review = _root_app()
    fresh_review.switch_page("pages/03_extraction_review.py").run(timeout=90)
    assert not fresh_review.exception
    visible_by_id = {str(row["review_id"]): row for row in _review_rows(fresh_review)}
    assert visible_by_id[review_ids["ゲーム4年制学科(ゲーム企画コース)"]]["review_status"] == "accepted"
    corrected = visible_by_id[review_ids["ゲーム4年制学科(ゲーム制作コース)"]]
    assert corrected["review_status"] == "corrected"
    assert int(str(corrected["corrected_value"])) == 715
    assert visible_by_id[review_ids["ゲーム4年制学科(ゲームデザインコース)"]]["review_status"] == "excluded"
    assert next(metric.value for metric in fresh_review.metric if metric.label == "Reviewed") == "3"

    master_path = served_runtime.data_dir / "master.xlsx"
    master_bytes = _write_master(master_path)
    fresh_review.switch_page("pages/04_review_diff.py").run(timeout=90)
    assert not fresh_review.exception
    assert not any(widget.label == "master.xlsx" for widget in fresh_review.text_input)
    next(widget for widget in fresh_review.text_input if widget.label == "corporation_name").set_value(
        CORPORATION_NAME
    )
    fresh_review.run(timeout=90)

    assert not fresh_review.exception
    target_statuses = {
        str(row["department_name"]): str(row["match_status"])
        for row in _diff_rows(fresh_review)
        if row["metric"] == "enrollment" and row["department_name"] in COURSE_ENROLLMENTS
    }
    assert target_statuses == {
        "ゲーム4年制学科(ゲーム企画コース)": "match",
        "ゲーム4年制学科(ゲーム制作コース)": "value_mismatch",
        "ゲーム4年制学科(ゲームデザインコース)": "excluded_not_comparable",
    }
    assert master_path.read_bytes() == master_bytes

    fresh_review.switch_page("pages/05_double_check.py").run(timeout=90)
    assert not fresh_review.exception
    external_csv = _external_csv()
    next(
        widget
        for widget in fresh_review.file_uploader
        if widget.label == "External extraction CSV/XLSX"
    ).upload("copilot.csv", external_csv, "text/csv")
    fresh_review.run(timeout=90)
    assert not fresh_review.exception
    _button(fresh_review, label="Create comparison run").click()
    fresh_review.run(timeout=90)
    assert not fresh_review.exception

    with served_runtime.session_factory() as session:
        runs = list(session.scalars(select(ExternalComparisonRun)).all())
        assert len(runs) == 1
        run = runs[0]
        results = list(
            session.scalars(
                select(ExternalComparisonResult).where(ExternalComparisonResult.run_id == run.run_id)
            ).all()
        )
        targets = {result.review_id: result for result in results if result.review_id in set(review_ids.values())}
        assert len(targets) == 3
        assert targets[review_ids["ゲーム4年制学科(ゲーム企画コース)"]].comparison_status == "match"
        mismatch = targets[review_ids["ゲーム4年制学科(ゲーム制作コース)"]]
        assert mismatch.comparison_status == "value_mismatch"
        assert mismatch.eidp_value == 715
        assert mismatch.external_value == 714
        assert targets[review_ids["ゲーム4年制学科(ゲームデザインコース)"]].comparison_status == (
            "excluded_not_comparable"
        )
        assert len({result.id for result in targets.values()}) == 3
        assert len({result.row_key for result in targets.values()}) == 3
        mismatch_id = mismatch.id

    fresh_double_check = _root_app()
    fresh_double_check.switch_page("pages/05_double_check.py").run(timeout=90)
    assert not fresh_double_check.exception
    persisted_rows = _persisted_comparison_rows(fresh_double_check)
    assert any(int(str(row["comparison_result_id"])) == mismatch_id for row in persisted_rows)
    result_selector = next(
        widget for widget in fresh_double_check.selectbox if widget.label == "comparison_result"
    )
    mismatch_option = next(
        option for option in result_selector.options if str(option).startswith(f"{mismatch_id} /")
    )
    result_selector.select(mismatch_option)
    fresh_double_check.run(timeout=90)
    assert not fresh_double_check.exception
    next(
        widget for widget in fresh_double_check.selectbox if widget.label == "resolution_outcome"
    ).select("accept_eidp")
    fresh_double_check.run(timeout=90)
    assert not fresh_double_check.exception
    next(widget for widget in fresh_double_check.text_area if widget.label == "resolution_reason").set_value(
        "official PDF decision retained"
    )
    next(
        button
        for button in fresh_double_check.button
        if button.key == f"save_double_check_resolution_{mismatch_id}"
    ).click()
    fresh_double_check.run(timeout=90)
    assert not fresh_double_check.exception

    final_app = _root_app()
    final_app.switch_page("pages/05_double_check.py").run(timeout=90)
    assert not final_app.exception
    persisted_mismatch = next(
        row
        for row in _persisted_comparison_rows(final_app)
        if int(str(row["comparison_result_id"])) == mismatch_id
    )
    assert persisted_mismatch["resolution_outcome"] == "accept_eidp"
    assert int(float(str(persisted_mismatch["effective_value"]))) == 715

    with served_runtime.session_factory() as session:
        decisions = list(session.scalars(select(ExtractionReviewDecision)).all())
        resolutions = list(session.scalars(select(DoubleCheckResolution)).all())
        audits = list(session.scalars(select(ManualActionLog)).all())
        assert len(decisions) == 3
        assert {(decision.review_id, decision.revision) for decision in decisions} == {
            (review_ids["ゲーム4年制学科(ゲーム企画コース)"], 1),
            (review_ids["ゲーム4年制学科(ゲーム制作コース)"], 1),
            (review_ids["ゲーム4年制学科(ゲームデザインコース)"], 1),
        }
        decisions_by_review_id = {decision.review_id: decision for decision in decisions}
        assert decisions_by_review_id[review_ids["ゲーム4年制学科(ゲーム企画コース)"]].decision == "accept"
        corrected_decision = decisions_by_review_id[review_ids["ゲーム4年制学科(ゲーム制作コース)"]]
        assert corrected_decision.decision == "correct"
        assert corrected_decision.corrected_value == 715
        excluded_decision = decisions_by_review_id[review_ids["ゲーム4年制学科(ゲームデザインコース)"]]
        assert excluded_decision.decision == "exclude"
        assert excluded_decision.note == "outside approved scope"
        assert len(resolutions) == 1
        resolution = resolutions[0]
        assert resolution.comparison_result_id == mismatch_id
        assert resolution.outcome == "accept_eidp"
        assert resolution.effective_value == 715
        assert resolution.reason == "official PDF decision retained"
        assert len(audits) == 4
        assert Counter(audit.action_type for audit in audits) == {
            "extraction_review_decision": 3,
            "double_check_resolution": 1,
        }
        assert {decision.audit_action_id for decision in decisions} | {resolution.audit_action_id} == {
            audit.action_id for audit in audits
        }
        assert all(decision.actor == ACTOR for decision in decisions)
        assert resolution.actor == ACTOR
        assert all(audit.actor == ACTOR for audit in audits)
        assert all(decision.identity_source == "configured_fallback" for decision in decisions)
        assert resolution.identity_source == "configured_fallback"
        assert all(audit.identity_source == "configured_fallback" for audit in audits)
        assert all(audit.jsonl_exported_at is not None for audit in audits)
        assert all(audit.jsonl_export_error is None for audit in audits)
        db_audit_ids = {audit.action_id for audit in audits}

    audit_path = served_runtime.data_dir / "audit/manual-actions.jsonl"
    payloads = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert len(payloads) == 4
    assert len({payload["action_id"] for payload in payloads}) == 4
    assert {payload["action_id"] for payload in payloads} == db_audit_ids
    assert all(payload["actor"] == ACTOR for payload in payloads)
    assert all(payload["identity_source"] == "configured_fallback" for payload in payloads)
    assert Counter(payload["action_type"] for payload in payloads) == {
        "extraction_review_decision": 3,
        "double_check_resolution": 1,
    }
    assert master_path.read_bytes() == master_bytes
    assert {path: path.read_bytes() for path in base_json_bytes} == base_json_bytes
