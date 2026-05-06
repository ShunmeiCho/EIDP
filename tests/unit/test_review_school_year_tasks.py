from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from eidp.db.locking import acquire_lock
from eidp.db.models import Base, Document, School, SchoolFiscalYearStatus, SchoolSite
from eidp.review._pages import school_year_tasks
from eidp.review._pages.school_year_tasks import (
    SchoolTaskSummary,
    blocking_reason_label,
    bootstrap_command,
    initial_bootstrap_warning_text,
    is_pdf_site_url,
    latest_bootstrap_log,
    latest_bootstrap_progress,
    list_school_year_tasks,
    manual_entry_prefill_for_row,
    needs_initial_url_bootstrap,
    next_action_for_row,
    next_action_for_status,
    read_bootstrap_progress,
    read_weekly_last_run,
    school_task_summary,
    school_type_from_filter_label,
    select_task_document,
    site_entry_label,
    site_url_type_label,
    start_initial_url_bootstrap,
    start_weekly_rediscovery,
    status_label,
    url_submission_prefill_for_row,
    weekly_command,
)


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _render_school_tasks_for_test(session, lock_path):  # noqa: ANN001, ANN201
    from eidp.review._pages import school_year_tasks as tasks

    tasks.render(session, lock_path=lock_path)


def _school(
    session: Session,
    school_id: int,
    *,
    name: str,
    pref: str = "東京",
    school_type: str = "専門学校",
) -> School:
    school = School(
        id=school_id,
        school_code=f"S{school_id}",
        prefecture=pref,
        corporation_name=f"法人{school_id}",
        school_name=name,
        school_type=school_type,
        status="active",
    )
    session.add(school)
    return school


def _status(
    session: Session,
    school_id: int,
    *,
    fiscal_year: int = 2026,
    url_status: str = "pref_url",
    pdf_status: str = "none",
    extract_status: str = "none",
    excel_ready: bool = False,
    blocking_reason: str | None = "no_target_pdf",
    evidence_level: str = "none",
) -> SchoolFiscalYearStatus:
    row = SchoolFiscalYearStatus(
        school_id=school_id,
        fiscal_year=fiscal_year,
        url_status=url_status,
        pdf_status=pdf_status,
        extract_status=extract_status,
        yoy_diff_status="unchecked",
        excel_ready=excel_ready,
        blocking_reason=blocking_reason,
        evidence_level=evidence_level,
    )
    session.add(row)
    return row


def _site(
    session: Session,
    school_id: int,
    url: str,
    *,
    url_type: str | None = None,
    discovery_method: str = "prefecture_aggregator",
) -> None:
    session.add(
        SchoolSite(
            school_id=school_id,
            url=url,
            url_type=url_type,
            discovery_method=discovery_method,
            http_status=200,
        )
    )


def _doc(
    session: Session,
    doc_id: int,
    school_id: int,
    *,
    fy: int,
    status: str = "ingested",
) -> None:
    session.add(
        Document(
            id=doc_id,
            school_id=school_id,
            source_url=f"https://school{school_id}.example/{doc_id}.pdf",
            file_hash=f"{doc_id:064x}"[-64:],
            fiscal_year=fy,
            pdf_type="target",
            ingest_status=status,
        )
    )


def test_school_task_summary_groups_operator_counts() -> None:
    session = _session()
    try:
        for school_id in range(1, 5):
            _school(session, school_id, name=f"学校{school_id}")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        _status(session, 4, pdf_status="image_pending", extract_status="ocr_pending", blocking_reason="ocr_pending")
        _school(session, 5, name="学校5")
        _status(
            session,
            5,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="dept_change_review",
        )
        session.commit()

        summary = school_task_summary(session, fiscal_year=2026, school_type="専門学校")

        assert summary.total == 5
        assert summary.excel_ready == 1
        assert summary.needs_action == 4
        assert summary.confirmed_target == 2
        assert summary.stale_fallback == 1
        assert summary.no_url == 1
        assert summary.review_or_parse == 1
        assert summary.dept_change_review == 1
    finally:
        session.close()


def test_school_task_summary_can_include_universities_or_filter_to_them() -> None:
    session = _session()
    try:
        _school(session, 1, name="専門A", school_type="専門学校")
        _school(session, 2, name="大学B", school_type="大学")
        _status(session, 1, blocking_reason="no_target_pdf")
        _status(session, 2, blocking_reason="no_url", url_status="no_url")
        session.commit()

        all_summary = school_task_summary(session, fiscal_year=2026, school_type=None)
        university_summary = school_task_summary(session, fiscal_year=2026, school_type="大学")

        assert all_summary.total == 2
        assert all_summary.no_url == 1
        assert university_summary.total == 1
        assert university_summary.no_url == 1
        assert school_type_from_filter_label("すべて") is None
        assert school_type_from_filter_label("大学") == "大学"
    finally:
        session.close()


def test_initial_url_bootstrap_hint_only_when_every_school_has_no_url() -> None:
    all_no_url = SchoolTaskSummary(
        fiscal_year=2026,
        school_type="専門学校",
        total=2418,
        excel_ready=0,
        confirmed_target=0,
        stale_fallback=0,
        no_url=2418,
        review_or_parse=0,
        dept_change_review=0,
    )
    mixed = SchoolTaskSummary(
        fiscal_year=2026,
        school_type="専門学校",
        total=2418,
        excel_ready=0,
        confirmed_target=0,
        stale_fallback=0,
        no_url=100,
        review_or_parse=0,
        dept_change_review=0,
    )

    assert needs_initial_url_bootstrap(all_no_url) is True
    assert needs_initial_url_bootstrap(mixed) is False
    warning = initial_bootstrap_warning_text(all_no_url)
    assert "確認大学等一覧" in warning
    assert "学校名リンクに埋め込まれたURL" in warning
    assert "専門学校中心" not in warning


def test_bootstrap_command_uses_pipeline_script_and_lock_path(tmp_path) -> None:
    cmd = bootstrap_command(
        tmp_path,
        lock_path=tmp_path / "data" / ".lock",
        progress_path=tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json",
        python_executable="python.exe",
    )

    assert cmd == [
        "python.exe",
        str(tmp_path / "scripts" / "bootstrap_pdf_pipeline.py"),
        "--lock-path",
        str(tmp_path / "data" / ".lock"),
        "--progress-file",
        str(tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"),
    ]


def test_weekly_command_uses_target_year_runner_for_all_schools(tmp_path) -> None:
    cmd = weekly_command(tmp_path, python_executable="python.exe")

    assert cmd == [
        "python.exe",
        str(tmp_path / "scripts" / "run_weekly_target_year_discovery.py"),
        "--methods",
        "prefecture_aggregator",
        "operator_manual",
        "--school-type",
        "all",
    ]


def test_latest_bootstrap_log_and_progress_return_newest_files(tmp_path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    older = logs / "bootstrap-pdfs-20260506-090000.log"
    newer = logs / "bootstrap-pdfs-20260506-100000.log"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    progress = logs / "bootstrap-pdfs-20260506-100000.json"
    progress.write_text(
        json.dumps(
            {
                "status": "running",
                "current_step": 3,
                "total_steps": 5,
                "percent": 0.45,
                "message": "学校サイトから対象年度PDFを探索しています。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert latest_bootstrap_log(tmp_path) == newer
    latest_progress = latest_bootstrap_progress(tmp_path)
    assert latest_progress is not None
    assert latest_progress.current_step == 3
    assert latest_progress.percent == 0.45
    assert latest_progress.message == "学校サイトから対象年度PDFを探索しています。"


def test_read_bootstrap_progress_clamps_bad_payload(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "running",
                "current_step": 99,
                "total_steps": 5,
                "percent": 2,
                "message": "too far",
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert progress.current_step == 5
    assert progress.percent == 1.0


def test_start_initial_url_bootstrap_starts_background_process(tmp_path, monkeypatch) -> None:
    script = tmp_path / "scripts" / "bootstrap_pdf_pipeline.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('boot')", encoding="utf-8")
    lock_path = tmp_path / "data" / ".lock"
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 1234

    def fake_popen(cmd, **kwargs):  # noqa: ANN001
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(school_year_tasks.subprocess, "Popen", fake_popen)

    result = start_initial_url_bootstrap(
        tmp_path,
        lock_path=lock_path,
        python_executable="python.exe",
        now=datetime(2026, 5, 6, 10, 30, 0),
    )

    assert result.started is True
    assert result.pid == 1234
    assert result.log_path == tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.log"
    assert result.progress_path == tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"
    assert captured["cmd"] == [
        "python.exe",
        str(script),
        "--lock-path",
        str(lock_path),
        "--progress-file",
        str(result.progress_path),
    ]
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["EIDP_APP_ROOT"] == str(tmp_path)
    progress = read_bootstrap_progress(result.progress_path)
    assert progress is not None
    assert progress.status == "running"
    assert progress.message == "初回取得を準備中です。"


def test_start_weekly_rediscovery_starts_background_process(tmp_path, monkeypatch) -> None:
    script = tmp_path / "scripts" / "run_weekly_target_year_discovery.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('weekly')", encoding="utf-8")
    lock_path = tmp_path / "data" / ".lock"
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 5678

    def fake_popen(cmd, **kwargs):  # noqa: ANN001
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(school_year_tasks.subprocess, "Popen", fake_popen)

    result = start_weekly_rediscovery(
        tmp_path,
        lock_path=lock_path,
        python_executable="python.exe",
        now=datetime(2026, 5, 6, 11, 0, 0),
    )

    assert result.started is True
    assert result.pid == 5678
    assert result.log_path == tmp_path / "logs" / "weekly-rediscovery-20260506-110000.log"
    assert result.last_run_path == tmp_path / "data" / "output" / "last_run.json"
    assert captured["cmd"] == [
        "python.exe",
        str(script),
        "--methods",
        "prefecture_aggregator",
        "operator_manual",
        "--school-type",
        "all",
    ]
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["EIDP_APP_ROOT"] == str(tmp_path)


def test_start_initial_url_bootstrap_refuses_when_app_lock_is_held(tmp_path) -> None:
    script = tmp_path / "scripts" / "bootstrap_pdf_pipeline.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('boot')", encoding="utf-8")
    lock_path = tmp_path / "data" / ".lock"

    with acquire_lock(lock_path, owner="weekly_runner"):
        result = start_initial_url_bootstrap(tmp_path, lock_path=lock_path)

    assert result.started is False
    assert "別の処理" in result.message


def test_start_weekly_rediscovery_refuses_when_app_lock_is_held(tmp_path) -> None:
    script = tmp_path / "scripts" / "run_weekly_target_year_discovery.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('weekly')", encoding="utf-8")
    lock_path = tmp_path / "data" / ".lock"

    with acquire_lock(lock_path, owner="bootstrap_pdfs"):
        result = start_weekly_rediscovery(tmp_path, lock_path=lock_path)

    assert result.started is False
    assert "別の処理" in result.message


def test_read_weekly_last_run_returns_payload_or_none(tmp_path) -> None:
    assert read_weekly_last_run(tmp_path) is None

    last_run = tmp_path / "data" / "output" / "last_run.json"
    last_run.parent.mkdir(parents=True)
    last_run.write_text(
        json.dumps(
            {
                "status": "success",
                "target_missing_school_count": 10,
                "new_document_count": 2,
            }
        ),
        encoding="utf-8",
    )

    payload = read_weekly_last_run(tmp_path)

    assert payload is not None
    assert payload["status"] == "success"
    assert payload["new_document_count"] == 2


def test_list_school_year_tasks_defaults_to_actionable_rows_and_enriches_latest_context() -> None:
    session = _session()
    try:
        _school(session, 1, name="出力可学校")
        _school(session, 2, name="旧年度学校")
        _school(session, 3, name="URLなし学校")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        _site(session, 2, "https://school2.example/info", url_type="disclosure_page")
        _doc(session, 20, 2, fy=2025)
        _doc(session, 21, 2, fy=2024)
        session.commit()

        rows = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校")

        assert [row.school_id for row in rows] == [3, 2]
        by_id = {row.school_id: row for row in rows}
        assert by_id[3].next_action == "URL追加"
        assert url_submission_prefill_for_row(by_id[3]) == {
            "selected_page": school_year_tasks.URL_SUBMISSION_PAGE_ID,
            school_year_tasks.URL_SUBMISSION_QUERY_STATE_KEY: "URLなし学校",
            school_year_tasks.URL_SUBMISSION_SCHOOL_ID_STATE_KEY: 3,
        }
        assert by_id[2].next_action == "公示待ち/再取得"
        assert by_id[2].latest_site_url == "https://school2.example/info"
        assert by_id[2].latest_site_url_type == "disclosure_page"
        assert by_id[2].latest_site_discovery_method == "prefecture_aggregator"
        assert by_id[2].latest_document_id == 20
        assert by_id[2].latest_document_fiscal_year == 2025
    finally:
        session.close()


def test_task_document_selection_prefers_target_year_over_later_stale_doc() -> None:
    current_doc = Document(id=10, school_id=1, fiscal_year=2026, pdf_type="target", ingest_status="ingested")
    stale_doc = Document(id=99, school_id=1, fiscal_year=2025, pdf_type="target", ingest_status="ingested")

    selected = select_task_document([stale_doc, current_doc], fiscal_year=2026)

    assert selected is current_doc


def test_task_document_selection_uses_newest_old_fiscal_year_before_id() -> None:
    older_fy_later_id = Document(id=99, school_id=1, fiscal_year=2024, pdf_type="target", ingest_status="ingested")
    newer_fy_earlier_id = Document(id=10, school_id=1, fiscal_year=2025, pdf_type="target", ingest_status="ingested")

    selected = select_task_document([older_fy_later_id, newer_fy_earlier_id], fiscal_year=2026)

    assert selected is newer_fy_earlier_id


def test_list_school_year_tasks_prefers_operator_relevant_pdf_context() -> None:
    session = _session()
    try:
        _school(session, 7, name="現年度あり学校")
        _status(
            session,
            7,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _doc(session, 10, 7, fy=2026)
        _doc(session, 99, 7, fy=2025)
        session.commit()

        row = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校", scope="all")[0]

        assert row.latest_document_id == 10
        assert row.latest_document_fiscal_year == 2026
    finally:
        session.close()


def test_pdf_direct_link_without_reusable_page_routes_back_to_url_addition() -> None:
    session = _session()
    try:
        _school(session, 5, name="PDF直リンク学校")
        _status(session, 5, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _site(session, 5, "https://school5.example/r8.pdf", url_type="pdf", discovery_method="operator_manual")
        session.commit()

        row = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校")[0]

        assert row.next_action == "URL追加"
        assert "情報公開ページURL" in row.action_hint
        assert row.latest_site_url == "https://school5.example/r8.pdf"
        assert row.latest_site_url_type == "pdf"
    finally:
        session.close()


def test_task_context_prefers_reusable_page_over_newer_pdf_direct_link() -> None:
    session = _session()
    try:
        _school(session, 6, name="入口あり学校")
        _status(session, 6, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _site(session, 6, "https://school6.example/public_info/", url_type="disclosure_page")
        _site(session, 6, "https://school6.example/r8.pdf", url_type="pdf", discovery_method="operator_manual")
        session.commit()

        row = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校")[0]

        assert row.next_action == "公示待ち/再取得"
        assert row.latest_site_url == "https://school6.example/public_info/"
        assert row.latest_site_url_type == "disclosure_page"
    finally:
        session.close()


def test_manual_entry_prefill_for_row_focuses_latest_document() -> None:
    session = _session()
    try:
        _school(session, 4, name="手入力学校")
        _status(
            session,
            4,
            pdf_status="confirmed_target",
            extract_status="parse_failed",
            blocking_reason="parse_failed",
        )
        _doc(session, 40, 4, fy=2026, status="parse_failed")
        session.commit()

        row = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校")[0]

        assert row.next_action == "手入力"
        assert manual_entry_prefill_for_row(row) == {
            "selected_page": school_year_tasks.MANUAL_ENTRY_PAGE_ID,
            school_year_tasks.MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY: 40,
        }
    finally:
        session.close()


def test_operator_labels_hide_internal_status_codes() -> None:
    assert blocking_reason_label("no_url") == "URL追加が必要"
    assert blocking_reason_label("stale_pdf_only") == "旧年度PDFのみ"
    assert blocking_reason_label(None) == "対応なし"
    assert status_label(school_year_tasks.PDF_STATUS_LABELS, "confirmed_target") == "対象年度PDFあり"
    assert status_label(school_year_tasks.EVIDENCE_LEVEL_LABELS, "operator_override") == "担当者確認済"
    assert status_label(school_year_tasks.EVIDENCE_LEVEL_LABELS, "future_code") == "future_code"


def test_site_url_type_label_explains_future_year_reuse() -> None:
    assert site_url_type_label("disclosure_page", "https://school.example/public_info/") == (
        "情報公開ページ（来年度以降も再取得入口として再利用）"
    )
    assert site_url_type_label("pdf", "https://school.example/r8.pdf") == (
        "PDF直リンク（対象年度ごとに更新確認が必要）"
    )
    assert site_url_type_label(None, "https://school.example/info") == (
        "ページURL（来年度以降も再取得入口として再利用）"
    )
    assert site_url_type_label(None, "https://school.example/r8.pdf?download=1") == (
        "PDF直リンク（対象年度ごとに更新確認が必要）"
    )


def test_site_entry_label_explains_source_and_reuse_quality() -> None:
    assert site_entry_label("prefecture_aggregator", "disclosure_page", "https://school.example/info/") == (
        "都道府県公式一覧の入口"
    )
    assert site_entry_label("operator_manual", "homepage", "https://school.example/") == "手動登録ページ入口"
    assert site_entry_label("operator_manual", "pdf", "https://school.example/r8.pdf") == (
        "PDF直リンク（今年度だけ弱い）"
    )
    assert site_entry_label(None, None, None) == "入口なし"


def test_pdf_site_url_detection_uses_type_or_url_suffix() -> None:
    assert is_pdf_site_url("pdf", "https://school.example/public_info/")
    assert is_pdf_site_url(None, "https://school.example/r8.pdf#page=1")
    assert not is_pdf_site_url("disclosure_page", "https://school.example/public_info/")


def test_row_action_uses_pdf_site_context_for_long_term_reuse() -> None:
    status = SchoolFiscalYearStatus(
        school_id=1,
        fiscal_year=2026,
        url_status="operator_url",
        pdf_status="rejected_stale",
        extract_status="none",
        yoy_diff_status="unchecked",
        excel_ready=False,
        blocking_reason="stale_pdf_only",
        evidence_level="conflict",
    )
    site = SchoolSite(
        school_id=1,
        url="https://school.example/r8.pdf",
        url_type="pdf",
        discovery_method="operator_manual",
        http_status=200,
    )

    action, hint = next_action_for_row(status, site)

    assert action == "URL追加"
    assert "来年度以降" in hint


def test_task_board_url_action_prefills_url_submission_state(tmp_path: Path) -> None:
    session = _session()
    try:
        _school(session, 3, name="URLなし学校")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        session.commit()

        app = AppTest.from_function(
            _render_school_tasks_for_test,
            args=(session, tmp_path / "data" / ".lock"),
        )
        app.run(timeout=15)

        assert not app.exception
        url_buttons = [button for button in app.button if button.label == "この学校のURLを追加"]
        assert len(url_buttons) == 1

        url_buttons[0].click().run(timeout=15)

        assert app.session_state["selected_page"] == school_year_tasks.URL_SUBMISSION_PAGE_ID
        assert (
            app.session_state[school_year_tasks.URL_SUBMISSION_QUERY_STATE_KEY]
            == "URLなし学校"
        )
        assert app.session_state[school_year_tasks.URL_SUBMISSION_SCHOOL_ID_STATE_KEY] == 3
    finally:
        session.close()


def test_list_school_year_tasks_filters_scope_reason_prefecture_and_search() -> None:
    session = _session()
    try:
        _school(session, 1, name="東京Ready", pref="東京")
        _school(session, 2, name="大阪Stale", pref="大阪")
        _school(session, 3, name="東京Missing", pref="東京")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, blocking_reason="no_target_pdf")
        session.commit()

        ready = list_school_year_tasks(session, fiscal_year=2026, scope="excel_ready")
        stale = list_school_year_tasks(session, fiscal_year=2026, blocking_reason="stale_pdf_only")
        tokyo = list_school_year_tasks(session, fiscal_year=2026, scope="all", prefecture="東京")
        searched = list_school_year_tasks(session, fiscal_year=2026, scope="all", search="Missing")

        assert [row.school_id for row in ready] == [1]
        assert [row.school_id for row in stale] == [2]
        assert {row.school_id for row in tokyo} == {1, 3}
        assert [row.school_id for row in searched] == [3]
    finally:
        session.close()


def test_next_action_labels_are_operator_tasks() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(session, 1, blocking_reason="parse_failed")
        action, hint = next_action_for_status(row)
        assert action == "手入力"
        assert "PDF" in hint

        row.excel_ready = True
        row.blocking_reason = None
        action, hint = next_action_for_status(row)
        assert action == "Excel出力可"
        assert "Excel" in hint
    finally:
        session.close()


def test_next_action_surfaces_identical_previous_year_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="review_required",
            evidence_level="pdf_text",
        )
        row.yoy_diff_status = "identical_to_prev_fy"

        action, hint = next_action_for_status(row)

        assert action == "前年差分確認"
        assert "前年" in hint
    finally:
        session.close()


def test_next_action_surfaces_department_change_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="dept_change_review",
            evidence_level="pdf_text",
        )

        action, hint = next_action_for_status(row)

        assert action == "学科変更確認"
        assert "名称変更" in hint
    finally:
        session.close()
