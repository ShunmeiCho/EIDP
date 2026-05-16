from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from eidp.db.locking import acquire_lock
from eidp.db.models import Base, Document, School, SchoolFiscalYearStatus, SchoolSite
from eidp.review._pages import school_year_tasks
from eidp.review._pages.school_year_tasks import (
    SETTINGS_PAGE_ID,
    BootstrapProgress,
    SchoolTaskSummary,
    blocking_reason_label,
    bootstrap_command,
    bootstrap_progress_auto_refresh_html,
    bootstrap_progress_detail_lines,
    bootstrap_progress_stale_reason,
    discovery_evidence_stale_target_notice,
    discovery_evidence_table_rows,
    discovery_rejection_reason_summary,
    filter_rows_by_discovery_evidence_bucket,
    initial_bootstrap_warning_text,
    is_pdf_site_url,
    latest_bootstrap_log,
    latest_bootstrap_progress,
    latest_url_search_evidence,
    list_school_year_tasks,
    manual_entry_prefill_for_row,
    needs_initial_url_bootstrap,
    next_action_for_row,
    next_action_for_status,
    operator_build_label,
    read_bootstrap_progress,
    read_weekly_last_run,
    read_weekly_task_registration_warning,
    school_task_source_chain_csv,
    school_task_summary,
    school_type_from_filter_label,
    school_year_discovery_evidence_bucket_by_school,
    school_year_discovery_evidence_bucket_label,
    school_year_discovery_evidence_bucket_options,
    school_year_discovery_evidence_summary,
    school_year_discovery_evidence_summary_notice,
    select_task_document,
    settings_page_prefill,
    site_entry_label,
    site_url_type_label,
    start_initial_url_bootstrap,
    start_weekly_rediscovery,
    status_label,
    task_lane_prefill,
    task_lanes_for_summary,
    task_progress_label,
    url_search_config_summary,
    url_submission_prefill_for_row,
    weekly_command,
    weekly_task_registration_warning_path,
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


def _render_weekly_last_run_for_test(payload):  # noqa: ANN001, ANN201
    from eidp.review._pages import school_year_tasks as tasks

    tasks._render_weekly_last_run(payload)


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


def test_discovery_rejection_reason_summary_labels_top_reasons() -> None:
    summary = discovery_rejection_reason_summary(
        {
            "rejection_reason_target_fiscal_year_not_detected": 4,
            "rejection_reason_pre_filtered_non_target_hint": 2,
            "rejection_reason_fiscal_year_mismatch": 1,
            "rejection_reason_target_application_not_detected": 0,
        }
    )

    assert summary == "対象年度不明 4 / 対象外ヒント 2 / 旧年度 1"


def test_bootstrap_progress_detail_lines_include_rejection_reason_counts() -> None:
    progress = BootstrapProgress(
        status="running",
        current_step=3,
        total_steps=5,
        percent=0.7,
        message="PDF探索中",
        details={
            "sites_total": 5,
            "crawled": 5,
            "found": 4,
            "downloaded": 0,
            "failed": 0,
            "skipped": 3,
            "prefiltered": 2,
            "rejection_reason_target_fiscal_year_not_detected": 2,
            "rejection_reason_target_application_not_detected": 1,
        },
    )

    lines = bootstrap_progress_detail_lines(progress)

    assert "除外理由: 対象年度不明 2 / 申請書ではない 1" in lines


def test_school_task_summary_groups_operator_counts() -> None:
    session = _session()
    try:
        for school_id in range(1, 6):
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
        _status(
            session,
            5,
            pdf_status="publication_lag",
            evidence_level="publication_lag",
            blocking_reason="publication_lag_latest_public",
        )
        _school(session, 6, name="学校6")
        _status(
            session,
            6,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="dept_change_review",
        )
        session.commit()

        summary = school_task_summary(session, fiscal_year=2026, school_type="専門学校")

        assert summary.total == 6
        assert summary.excel_ready == 1
        assert summary.needs_action == 5
        assert summary.confirmed_target == 2
        assert summary.target_pdf_wait == 0
        assert summary.stale_fallback == 1
        assert summary.publication_lag == 1
        assert summary.no_url == 1
        assert summary.review_or_parse == 1
        assert summary.dept_change_review == 1
    finally:
        session.close()


def test_school_year_discovery_evidence_summary_surfaces_publication_lag_candidates(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "discovery_rejections.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "school_id": 1,
                        "reason": "fiscal_year_mismatch:2025",
                        "pdf_type": "target",
                        "pdf_url": "https://a/2025.pdf",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 2,
                        "reason": "classified_non_target",
                        "pdf_type": "non_target",
                        "pdf_url": "https://b/non-target.pdf",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    session = _session()
    try:
        _school(session, 1, name="学校1", pref="埼玉県")
        _school(session, 2, name="学校2", pref="埼玉県")
        _school(session, 3, name="大学1", pref="埼玉県", school_type="大学")
        _site(session, 1, "https://a/")
        _site(session, 2, "https://b/")
        _site(session, 3, "https://c/")
        session.commit()

        summary = school_year_discovery_evidence_summary(
            session,
            app_root=tmp_path,
            school_type="専門学校",
        )

        assert summary is not None
        assert summary.site_scope_schools == 2
        assert summary.school_bucket_counts == {
            "non_target_candidates_only": 1,
            "publication_lag_or_old_target_pdf": 1,
        }
        assert school_year_discovery_evidence_summary_notice(summary, target_fiscal_year=2026) == (
            "PDF探索ログ: 旧年度または公開待ちの確認申請書候補が 1校あります。"
            "これは2026年度成果には含めず、学校側の更新待ちとして再取得対象に残します。"
        )
        assert school_year_discovery_evidence_bucket_by_school(summary) == {
            1: "publication_lag_or_old_target_pdf",
            2: "non_target_candidates_only",
        }
        assert school_year_discovery_evidence_bucket_label("publication_lag_or_old_target_pdf") == (
            "旧年度候補あり"
        )
        assert school_year_discovery_evidence_bucket_label("tls_certificate_verify_failed") == (
            "証明書エラー"
        )
        assert school_year_discovery_evidence_bucket_options(summary) == [
            "non_target_candidates_only",
            "publication_lag_or_old_target_pdf",
        ]

        rows = [
            school_year_tasks.SchoolTaskRow(
                school_id=1,
                prefecture="埼玉県",
                school_name="学校1",
                fiscal_year=2026,
                url_status="pref_url",
                pdf_status="none",
                extract_status="none",
                yoy_diff_status="unchecked",
                evidence_level="none",
                excel_ready=False,
                blocking_reason="no_target_pdf",
                next_action="PDF探索",
                action_hint="",
                latest_document_id=None,
                latest_document_fiscal_year=None,
                latest_document_status=None,
                latest_document_url=None,
                latest_site_url="https://a/",
                latest_site_url_type="disclosure",
                latest_site_discovery_method="prefecture_aggregator",
            ),
            school_year_tasks.SchoolTaskRow(
                school_id=2,
                prefecture="埼玉県",
                school_name="学校2",
                fiscal_year=2026,
                url_status="pref_url",
                pdf_status="none",
                extract_status="none",
                yoy_diff_status="unchecked",
                evidence_level="none",
                excel_ready=False,
                blocking_reason="no_target_pdf",
                next_action="PDF探索",
                action_hint="",
                latest_document_id=None,
                latest_document_fiscal_year=None,
                latest_document_status=None,
                latest_document_url=None,
                latest_site_url="https://b/",
                latest_site_url_type="disclosure",
                latest_site_discovery_method="prefecture_aggregator",
            ),
        ]
        filtered = filter_rows_by_discovery_evidence_bucket(
            rows,
            school_year_discovery_evidence_bucket_by_school(summary),
            "publication_lag_or_old_target_pdf",
        )
        assert [row.school_id for row in filtered] == [1]
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
        target_pdf_wait=0,
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
        target_pdf_wait=100,
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
    assert "検索 provider" in warning
    assert "専門学校中心" not in warning


def test_url_search_config_summary_surfaces_current_provider_and_limit() -> None:
    assert url_search_config_summary(mode="auto", provider="duckduckgo", batch_size=200) == (
        "不足URL Web検索: 自動 / provider=duckduckgo / 最大 200 校"
    )
    assert url_search_config_summary(mode="off", provider="serper", batch_size=5000) == (
        "不足URL Web検索: 実行しない / provider=serper"
    )
    assert url_search_config_summary(mode="on", provider="", batch_size=0) == (
        "不足URL Web検索: 常に実行 / provider=未設定"
    )


def test_operator_build_label_surfaces_packaged_commit(tmp_path: Path) -> None:
    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "git_commit": "37e7e81fb6a3038bc4d80e619fab66daf6a50109",
                "git_branch": "sprint8-handoff-finalize",
                "git_dirty": "false",
                "built_at_utc": "2026-05-07T04:15:55+00:00",
            }
        ),
        encoding="utf-8",
    )

    assert operator_build_label(tmp_path) == (
        "実行中のパッケージ: commit=37e7e81 / branch=sprint8-handoff-finalize / "
        "dirty=false / built=2026-05-07T04:15:55+00:00"
    )


def test_operator_build_label_hidden_for_source_checkout(tmp_path: Path) -> None:
    assert operator_build_label(tmp_path) is None


def test_task_lanes_make_operator_routes_explicit() -> None:
    summary = SchoolTaskSummary(
        fiscal_year=2026,
        school_type=None,
        total=10,
        excel_ready=2,
        confirmed_target=4,
        target_pdf_wait=3,
        stale_fallback=1,
        no_url=2,
        review_or_parse=1,
        dept_change_review=1,
    )

    lanes = {lane.key: lane for lane in task_lanes_for_summary(summary)}

    assert task_progress_label(summary) == "Excel出力可 2/10 校 / 要対応 8 校"
    assert lanes["no_url"].count == 2
    assert lanes["no_url"].blocking_reason == "no_url"
    assert lanes["target_wait"].count == 3
    assert lanes["target_wait"].blocking_reason == "no_target_pdf"
    assert lanes["review_or_parse"].page_id == school_year_tasks.MANUAL_ENTRY_PAGE_ID
    assert lanes["excel_ready"].page_id == school_year_tasks.EXCEL_PREVIEW_PAGE_ID


def test_task_lane_prefill_sets_filter_or_page_state() -> None:
    summary = SchoolTaskSummary(
        fiscal_year=2026,
        school_type="専門学校",
        total=5,
        excel_ready=1,
        confirmed_target=1,
        target_pdf_wait=0,
        stale_fallback=2,
        no_url=0,
        review_or_parse=0,
        dept_change_review=0,
    )
    stale_lane = {lane.key: lane for lane in task_lanes_for_summary(summary)}["stale_pdf"]
    excel_lane = {lane.key: lane for lane in task_lanes_for_summary(summary)}["excel_ready"]

    assert task_lane_prefill(stale_lane) == {
        school_year_tasks.TASK_SCOPE_STATE_KEY: "要対応",
        school_year_tasks.TASK_REASON_STATE_KEY: "stale_pdf_only",
        school_year_tasks.TASK_PREFECTURE_STATE_KEY: "すべて",
        school_year_tasks.TASK_DISCOVERY_EVIDENCE_STATE_KEY: "",
        school_year_tasks.TASK_SEARCH_STATE_KEY: "",
    }
    assert task_lane_prefill(excel_lane) == {"selected_page": school_year_tasks.EXCEL_PREVIEW_PAGE_ID}


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
        "seed_csv",
        "corporation_pattern",
        "school_domain_override",
        "web_search",
        "operator_manual",
        "scrapling_stealth",
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


def test_bootstrap_progress_exposes_discovery_details(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "running",
                "current_step": 3,
                "total_steps": 5,
                "percent": 0.52,
                "message": "学校サイトから対象年度PDFを探索しています。",
                "details": {
                    "sites_total": 100,
                    "crawled": 25,
                    "found": 8,
                    "downloaded": 3,
                    "failed": 2,
                    "skipped": 0,
                    "discovery_skipped": 20,
                    "prefiltered": 7,
                    "cached_rejections": 4,
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert progress.details is not None
    assert progress.details["sites_total"] == 100
    assert bootstrap_progress_detail_lines(progress) == [
        "学校サイト探索: 25/100確認済み / 候補 8 / PDF取得 3 / 失敗 2 / 対象外・旧年度 20",
        "除外内訳: 事前除外 7 / 既知除外 4",
    ]


def test_bootstrap_progress_exposes_url_search_details(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "running",
                "current_step": 2,
                "total_steps": 5,
                "percent": 0.45,
                "message": "既知URL、法人ドメイン、不足URL検索を補助的に登録しています。",
                "details": {
                    "seed_imported": 5,
                    "corporation_inferred": 7,
                    "search_enabled": 1,
                    "search_searched": 25,
                    "search_found": 9,
                    "search_no_result": 15,
                    "search_errors": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert bootstrap_progress_detail_lines(progress) == [
        "補助URL登録: 既知URL 5 / 学校別補正 0 / 法人ドメイン推定 7",
        "不足URL Web検索: 25校 / 入口候補 9 / 見つからず 15 / エラー 1",
    ]


def test_bootstrap_progress_exposes_school_url_crawl_details(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "running",
                "current_step": 2,
                "total_steps": 5,
                "percent": 0.58,
                "message": "不足URLの学校公式サイト探索を確認しています。",
                "details": {
                    "school_url_crawl_enabled": 1,
                    "school_url_crawl_attempted": 10,
                    "school_url_crawl_auto_registered": 3,
                    "school_url_crawl_review_enqueued": 2,
                    "school_url_crawl_manual_required_enqueued": 4,
                    "school_url_crawl_errors": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert bootstrap_progress_detail_lines(progress) == [
        "学校公式サイト探索: 10校 / 自動登録 3 / 確認候補 2 / 手入力キュー 4 / エラー 1",
    ]


def test_bootstrap_progress_exposes_official_index_yield_details(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "succeeded",
                "current_step": 5,
                "total_steps": 5,
                "percent": 1.0,
                "message": "初回URL/PDF取得が完了しました。",
                "details": {
                    "official_index_rows_extracted": 364,
                    "official_index_rows_matched": 349,
                    "official_school_sites_added": 40,
                    "official_school_sites_upgraded": 5,
                    "official_prefectures_without_new_urls": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert bootstrap_progress_detail_lines(progress) == [
        "都道府県公式一覧: 抽出 364 / DB照合 349 / URL追加 40 / URL更新 5 / URL増加なし 1県"
    ]


def test_bootstrap_progress_exposes_target_pdf_yield_gate(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "succeeded",
                "current_step": 5,
                "total_steps": 5,
                "percent": 1.0,
                "message": "初回URL/PDF取得が完了しました。",
                "details": {
                    "target_pdf_auto_acquired_count": 1020,
                    "target_pdf_auto_denominator_count": 1700,
                    "target_pdf_auto_yield_pct": 60.0,
                    "operator_reviewable_count": 1020,
                    "operator_reviewable_yield_pct": 60.0,
                    "ship_gate_auto_yield_pct": 60.0,
                    "ship_gate_operator_coverage_pct": 60.0,
                    "ship_gate_status": "pass",
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert bootstrap_progress_detail_lines(progress) == [
        "操作員レビュー可能率: 60.0% (1020/1700校) / レビュー目安 60% 達成"
    ]


def test_bootstrap_progress_exposes_discovery_rca_queue(tmp_path) -> None:
    progress_path = tmp_path / "progress.json"
    progress_path.write_text(
        json.dumps(
            {
                "status": "succeeded",
                "current_step": 5,
                "total_steps": 5,
                "percent": 1.0,
                "message": "初回URL/PDF取得が完了しました。",
                "details": {
                    "discovery_rca_batch_plan_path": (
                        "data/output/target-year-discovery/bootstrap-discovery-rca-batch-plan.json"
                    ),
                    "discovery_rca_batch_plan_item_count": 4,
                    "discovery_rca_batch_plan_total_candidates": 12,
                },
            }
        ),
        encoding="utf-8",
    )

    progress = read_bootstrap_progress(progress_path)

    assert progress is not None
    assert bootstrap_progress_detail_lines(progress) == [
        "Codex RCAキュー: "
        "data/output/target-year-discovery/bootstrap-discovery-rca-batch-plan.json (候補 4/12)"
    ]


def test_bootstrap_progress_auto_refresh_html_uses_bounded_delay() -> None:
    too_fast = bootstrap_progress_auto_refresh_html(seconds=1)
    normal = bootstrap_progress_auto_refresh_html(seconds=20)
    too_slow = bootstrap_progress_auto_refresh_html(seconds=999)

    assert "5000" in too_fast
    assert "20秒ごとに自動更新" in normal
    assert "20000" in normal
    assert "300000" in too_slow
    assert "window.location.reload()" in normal


def test_bootstrap_progress_stale_when_running_but_lock_released() -> None:
    progress = BootstrapProgress(
        status="running",
        current_step=3,
        total_steps=5,
        percent=0.45,
        message="学校サイトから対象年度PDFを探索しています。",
        updated_at="2026-05-07T00:47:25",
    )

    reason = bootstrap_progress_stale_reason(
        progress,
        lock_held=False,
        now=datetime(2026, 5, 7, 0, 52, 25),
        stale_after_seconds=180,
    )

    assert reason is not None
    assert "処理ロックは解除されています" in reason


def test_bootstrap_progress_warns_when_lock_held_but_not_updating() -> None:
    progress = BootstrapProgress(
        status="running",
        current_step=3,
        total_steps=5,
        percent=0.45,
        message="学校サイトから対象年度PDFを探索しています。",
        updated_at="2026-05-07T00:47:25",
    )

    reason = bootstrap_progress_stale_reason(
        progress,
        lock_held=True,
        now=datetime(2026, 5, 7, 0, 52, 25),
        stale_after_seconds=180,
    )

    assert reason is not None
    assert "処理はまだ実行中" in reason
    assert "診断ログ" in reason


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
        "seed_csv",
        "corporation_pattern",
        "school_domain_override",
        "web_search",
        "operator_manual",
        "scrapling_stealth",
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


def test_weekly_last_run_surfaces_discovery_rca_batch_plan() -> None:
    payload = {
        "status": "success",
        "target_missing_school_count": 10,
        "new_document_count": 0,
        "no_crawlable_url_school_count": 2,
        "stale_school_count": 1,
        "target_pdf_auto_acquired_count": 6,
        "target_pdf_auto_yield_pct": 60.0,
        "operator_reviewable_count": 6,
        "operator_reviewable_yield_pct": 60.0,
        "ship_gate_auto_yield_pct": 60.0,
        "ship_gate_operator_coverage_pct": 60.0,
        "ship_gate_status": "pass",
        "discovery_rca": {
            "batch_plan_path": "data/output/target-year-discovery/run-discovery-rca-batch-plan.json",
            "batch_plan_item_count": 7,
            "batch_plan_total_candidates": 12,
        },
    }

    app = AppTest.from_function(_render_weekly_last_run_for_test, args=(payload,))
    app.run(timeout=30)

    assert not app.exception
    captions = [str(caption.value) for caption in app.caption]
    assert any("Codex RCAキュー" in caption for caption in captions)
    assert any("候補 7/12" in caption for caption in captions)
    assert any("run-discovery-rca-batch-plan.json" in caption for caption in captions)
    assert any("レビュー可能率: 60.0%" in caption for caption in captions)
    assert any("レビュー判定: pass" in caption for caption in captions)


def test_weekly_task_registration_warning_reads_setup_marker(tmp_path) -> None:
    path = weekly_task_registration_warning_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("Task Scheduler registration failed during setup.\n", encoding="utf-8")

    assert path == tmp_path / "data" / "weekly-task-registration-warning.txt"
    assert read_weekly_task_registration_warning(tmp_path) == "Task Scheduler registration failed during setup."
    assert read_weekly_task_registration_warning(tmp_path / "missing") is None


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
    assert blocking_reason_label("tls_certificate_verify_failed") == "証明書エラー"
    assert blocking_reason_label("target_year_unverified") == "年度未確認候補"
    assert blocking_reason_label(None) == "対応なし"
    assert status_label(school_year_tasks.PDF_STATUS_LABELS, "confirmed_target") == "対象年度PDFあり"
    assert status_label(school_year_tasks.PDF_STATUS_LABELS, "target_year_unverified") == "年度未確認候補"
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
    assert site_entry_label("seed_csv", "disclosure_page", "https://school.example/info/") == (
        "既知URLシードの入口"
    )
    assert site_entry_label("corporation_pattern", "homepage", "https://school.example/") == (
        "法人ドメイン推定の入口"
    )
    assert site_entry_label("school_domain_override", "homepage", "https://school.example/") == (
        "学校別URL補正の入口"
    )
    assert site_entry_label("operator_manual", "homepage", "https://school.example/") == "手動登録ページ入口"
    assert site_entry_label("operator_manual", "pdf", "https://school.example/r8.pdf") == (
        "PDF直リンク（今年度だけ弱い）"
    )
    assert site_entry_label("scrapling_stealth", "homepage", "https://school.example/") == (
        "学校公式サイト自動発見の入口"
    )
    assert site_entry_label(None, None, None) == "入口なし"


def test_discovery_evidence_table_rows_show_candidate_reason_and_source() -> None:
    rows = discovery_evidence_table_rows([
        SimpleNamespace(
            reason="fiscal_year_mismatch:2025",
            score=3.2,
            pdf_type="target",
            anchor_text="2025年度 確認申請書",
            pdf_url="https://school.example/2025.pdf",
            page_url="https://school.example/disclosure/",
        ),
        SimpleNamespace(
            reason="target_fiscal_year_not_detected",
            score=2.4,
            pdf_type="target",
            anchor_text="確認申請書",
            pdf_url="https://school.example/yearless.pdf",
            page_url="https://school.example/disclosure/",
        ),
    ])

    assert rows == [
        {
            "採否理由": "旧年度 (2025年度)",
            "score": 3.2,
            "PDF種別": "target",
            "リンク文字": "2025年度 確認申請書",
            "PDF候補": "https://school.example/2025.pdf",
            "掲載ページ": "https://school.example/disclosure/",
        },
        {
            "採否理由": "対象年度不明",
            "score": 2.4,
            "PDF種別": "target",
            "リンク文字": "確認申請書",
            "PDF候補": "https://school.example/yearless.pdf",
            "掲載ページ": "https://school.example/disclosure/",
        },
    ]


def test_discovery_evidence_stale_target_notice_summarizes_old_year_target_candidates() -> None:
    notice = discovery_evidence_stale_target_notice([
        SimpleNamespace(reason="classified_non_target", pdf_type="non_target"),
        SimpleNamespace(reason="fiscal_year_mismatch:2025", pdf_type="target"),
        SimpleNamespace(reason="fiscal_year_mismatch:2025", pdf_type="target"),
        SimpleNamespace(reason="fiscal_year_mismatch:2024", pdf_type="target"),
    ])

    assert notice == "旧年度の確認申請書候補あり: 2025年度 2件 / 2024年度 1件。対象年度PDFは未取得です。"


def test_discovery_evidence_stale_target_notice_hides_when_current_pdf_was_accepted() -> None:
    notice = discovery_evidence_stale_target_notice([
        SimpleNamespace(reason="fiscal_year_mismatch:2025", pdf_type="target"),
        SimpleNamespace(reason="accepted_downloaded", pdf_type="target"),
    ])

    assert notice is None


def test_school_task_source_chain_csv_exports_visible_row_evidence() -> None:
    row = school_year_tasks.SchoolTaskRow(
        school_id=12,
        prefecture="東京",
        school_name="東京テスト専門学校",
        fiscal_year=2026,
        url_status="operator_url",
        pdf_status="rejected_stale",
        extract_status="none",
        yoy_diff_status="unchecked",
        evidence_level="conflict",
        excel_ready=False,
        blocking_reason="stale_pdf_only",
        next_action="公示待ち/再取得",
        action_hint="対象年度PDFを待つ",
        latest_document_id=99,
        latest_document_fiscal_year=2025,
        latest_document_status="review_pending",
        latest_document_url="https://school.example/r7.pdf",
        latest_site_url="https://school.example/public_info/",
        latest_site_url_type="disclosure_page",
        latest_site_discovery_method="prefecture_aggregator",
    )

    csv_body = school_task_source_chain_csv(
        [row],
        discovery_evidence_buckets={12: "publication_lag_or_old_target_pdf"},
    )

    assert "school_id,prefecture,school_name" in csv_body
    assert "東京テスト専門学校" in csv_body
    assert "都道府県公式一覧の入口" in csv_body
    assert "情報公開ページ（来年度以降も再取得入口として再利用）" in csv_body
    assert "旧年度候補あり" in csv_body
    assert "https://school.example/r7.pdf" in csv_body


def test_latest_url_search_evidence_reads_school_rows(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "url_search_evidence.jsonl").write_text(
        json.dumps(
            {
                "school_id": 1,
                "school_name": "東京テスト大学",
                "provider": "fake",
                "query": "東京テスト大学 情報公開",
                "result_url": "https://example.edu/disclosure/",
                "result_title": "情報公開",
                "score": 0.95,
                "decision": "accepted",
                "reason": "registered_school_site",
                "timestamp": "2026-05-07T00:00:00+00:00",
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps(
            {
                "school_id": 1,
                "query": "東京テスト大学 学校概要",
                "decision": "rejected",
                "reason": "low_confidence",
                "score": 0.42,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    rows = latest_url_search_evidence(app_root=tmp_path, school_id=1)

    assert rows == [{
        "採否": "除外",
        "理由": "信頼度不足",
        "score": 0.42,
        "query": "東京テスト大学 学校概要",
        "候補URL": "",
        "候補タイトル": "",
        "provider": "",
        "時刻": "",
    }, {
        "採否": "採用",
        "理由": "学校サイト登録済み",
        "score": 0.95,
        "query": "東京テスト大学 情報公開",
        "候補URL": "https://example.edu/disclosure/",
        "候補タイトル": "情報公開",
        "provider": "fake",
        "時刻": "2026-05-07T00:00:00+00:00",
    }]


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
        app.run(timeout=30)

        assert not app.exception
        url_buttons = [button for button in app.button if button.label == "この学校のURLを追加"]
        assert len(url_buttons) == 1

        url_buttons[0].click().run(timeout=30)

        assert app.session_state["selected_page"] == school_year_tasks.URL_SUBMISSION_PAGE_ID
        assert (
            app.session_state[school_year_tasks.URL_SUBMISSION_QUERY_STATE_KEY]
            == "URLなし学校"
        )
        assert app.session_state[school_year_tasks.URL_SUBMISSION_SCHOOL_ID_STATE_KEY] == 3
    finally:
        session.close()


def test_task_board_settings_button_opens_settings_page(tmp_path: Path) -> None:
    session = _session()
    try:
        _school(session, 3, name="URLなし学校")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        session.commit()

        app = AppTest.from_function(
            _render_school_tasks_for_test,
            args=(session, tmp_path / "data" / ".lock"),
        )
        app.run(timeout=30)

        assert not app.exception
        settings_buttons = [button for button in app.button if button.label == "設定を開く（年度・OCR・API）"]
        assert len(settings_buttons) == 1

        settings_buttons[0].click().run(timeout=30)

        assert app.session_state["selected_page"] == SETTINGS_PAGE_ID
        assert settings_page_prefill() == {"selected_page": SETTINGS_PAGE_ID}
    finally:
        session.close()


def test_task_board_explains_target_year_publication_window(tmp_path: Path) -> None:
    session = _session()
    try:
        _school(session, 3, name="URLなし学校")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        session.commit()

        app = AppTest.from_function(
            _render_school_tasks_for_test,
            args=(session, tmp_path / "data" / ".lock"),
        )
        app.run(timeout=30)

        assert not app.exception
        info_texts = [str(info.value) for info in app.info]
        assert any("6〜8月ごろ順次公開" in text for text in info_texts)
        assert any("旧年度PDF・募集要項・学生向け申請書は成果に含めません" in text for text in info_texts)
    finally:
        session.close()


def test_task_board_surfaces_package_identity_caption(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    from eidp.config import settings

    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "git_commit": "d4f096873ee04b9d851e919868e6e3877117e898",
                "git_branch": "sprint8-handoff-finalize",
                "git_dirty": "false",
                "built_at_utc": "2026-05-07T04:25:04+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "app_root", tmp_path)
    session = _session()
    try:
        _school(session, 3, name="URLなし学校")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        session.commit()

        app = AppTest.from_function(
            _render_school_tasks_for_test,
            args=(session, tmp_path / "data" / ".lock"),
        )
        app.run(timeout=30)

        assert not app.exception
        captions = [str(caption.value) for caption in app.caption]
        assert any("実行中のパッケージ: commit=d4f0968" in caption for caption in captions)
    finally:
        session.close()


def test_task_lane_button_focuses_matching_filter(tmp_path: Path) -> None:
    session = _session()
    try:
        _school(session, 2, name="旧年度学校")
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        session.commit()

        app = AppTest.from_function(
            _render_school_tasks_for_test,
            args=(session, tmp_path / "data" / ".lock"),
        )
        app.run(timeout=30)

        assert not app.exception
        stale_buttons = [button for button in app.button if button.label == "旧年度のみを表示"]
        assert len(stale_buttons) == 1

        stale_buttons[0].click().run(timeout=30)

        assert app.session_state[school_year_tasks.TASK_SCOPE_STATE_KEY] == "要対応"
        assert app.session_state[school_year_tasks.TASK_REASON_STATE_KEY] == "stale_pdf_only"
        assert app.session_state[school_year_tasks.TASK_PREFECTURE_STATE_KEY] == "すべて"
        assert app.session_state[school_year_tasks.TASK_SEARCH_STATE_KEY] == ""
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


def test_next_action_surfaces_publication_lag_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="publication_lag",
            evidence_level="publication_lag",
            blocking_reason="publication_lag_latest_public",
        )

        action, hint = next_action_for_status(row)

        assert action == "公示待ち/再取得"
        assert "成果扱い" in hint
    finally:
        session.close()


def test_next_action_surfaces_target_year_unverified_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="target_year_unverified",
            evidence_level="target_year_unverified",
            blocking_reason="target_year_unverified",
        )

        action, hint = next_action_for_status(row)

        assert action == "PDF確認"
        assert "年度" in hint
    finally:
        session.close()
