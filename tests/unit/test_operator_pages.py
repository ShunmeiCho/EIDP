from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.models import Base, Document, ReviewItem, School, SchoolAlias, SchoolSite
from eidp.review import operator_pages


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _render_url_submission_for_test(session):  # noqa: ANN001, ANN201
    from eidp.review import operator_pages as pages

    pages.page_url_submission(session)


def test_output_path_allows_output_and_rejects_traversal() -> None:
    path = operator_pages.output_path("output/test.xlsx", (".xlsx",))
    assert path.name == "test.xlsx"

    with pytest.raises(operator_pages.PathPolicyError):
        operator_pages.output_path("../secrets.xlsx", (".xlsx",))


def test_output_path_rejects_wrong_suffix() -> None:
    with pytest.raises(operator_pages.PathPolicyError):
        operator_pages.output_path("output/test.txt", (".xlsx",))


def test_v1_theme_css_uses_streamlit_theme_tokens() -> None:
    css = operator_pages.v1_theme_css()

    assert "--eidp-bg: var(--background-color)" in css
    assert "--eidp-ink: var(--text-color)" in css
    assert "--eidp-accent: var(--primary-color)" in css
    assert 'button[data-testid="stBaseButton-primary"]' in css
    assert 'button[data-testid="stBaseButton-secondary"]' in css
    assert "#FAFAFA" not in css
    assert "#FFFFFF" not in css
    assert "#000000" not in css


def test_search_school_url_options_searches_names_corporations_and_prefecture() -> None:
    session = _session()
    try:
        session.add_all(
            [
                School(
                    id=100,
                    prefecture="東京",
                    corporation_name="滋慶",
                    school_name="東京アニメ",
                    school_type="専門学校",
                ),
                School(
                    id=200,
                    prefecture="神奈川",
                    corporation_name="電子学園",
                    school_name="日本電子大学",
                    school_type="大学",
                ),
            ]
        )
        session.flush()

        by_name = operator_pages.search_school_url_options(session, "アニメ")
        by_corporation = operator_pages.search_school_url_options(session, "電子学園")
        by_prefecture = operator_pages.search_school_url_options(session, "神奈川")

        assert [option.school_id for option in by_name] == [100]
        assert [option.school_id for option in by_corporation] == [200]
        assert [option.school_id for option in by_prefecture] == [200]
        assert "ID 100" in by_name[0].label
        assert "専門学校" in by_name[0].label
    finally:
        session.close()


def test_search_school_url_options_requires_search_term() -> None:
    session = _session()
    try:
        session.add(School(id=100, prefecture="東京", corporation_name="滋慶", school_name="東京アニメ"))
        session.flush()

        assert operator_pages.search_school_url_options(session, "  ") == []
    finally:
        session.close()


def test_school_option_index_prefers_task_board_school_id() -> None:
    options = [
        operator_pages.SchoolUrlOption(school_id=100, label="A"),
        operator_pages.SchoolUrlOption(school_id=200, label="B"),
    ]

    assert operator_pages.school_option_index(options, 200) == 1
    assert operator_pages.school_option_index(options, "200") == 1
    assert operator_pages.school_option_index(options, "missing") == 0
    assert operator_pages.school_option_index(options, None) == 0


def test_url_submission_page_prefills_school_from_task_board_state() -> None:
    session = _session()
    try:
        session.add(
            School(
                id=100,
                prefecture="東京",
                corporation_name="滋慶",
                school_name="東京アニメ",
                school_type="専門学校",
            )
        )
        session.flush()

        app = AppTest.from_function(_render_url_submission_for_test, args=(session,))
        app.session_state["url_submission_school_query"] = "東京アニメ"
        app.session_state["url_submission_school_id"] = 100
        app.run(timeout=5)

        assert not app.exception
        assert app.text_input[0].value == "東京アニメ"
        assert app.selectbox[0].value == 100
        assert any("選択中: 東京アニメ" in caption.value for caption in app.caption)
    finally:
        session.close()


def test_submit_operator_url_inserts_verified_school_site(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    try:
        session.add(School(id=100, prefecture="東京", corporation_name="滋慶", school_name="東京アニメ"))
        session.flush()

        content = b"%PDF-" + b"x" * 2000
        monkeypatch.setattr(operator_pages, "_is_safe_url", lambda url: True)
        monkeypatch.setattr(operator_pages, "_fetch_pdf_bytes", lambda url: (200, content))
        monkeypatch.setattr(operator_pages, "_classify_pdf_content", lambda content: "target")

        result = operator_pages.submit_operator_url(
            session,
            school_id=100,
            url="https://anime.ac.jp/school/public_info/pdf/11_confirmation_application.pdf",
            operator_name="op",
            operator_note="manual check",
        )

        assert result.accepted is True
        assert result.classifier == "target"
        assert result.site_created is True

        site = session.query(SchoolSite).one()
        assert site.school_id == 100
        assert site.url_type == "pdf"
        assert site.discovery_method == "operator_manual"
        assert site.verified is True
        assert float(site.confidence) == 1.0
        assert site.http_status == 200
    finally:
        session.close()


def test_submit_operator_url_accepts_disclosure_page_for_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    try:
        session.add(School(id=100, prefecture="東京", corporation_name="滋慶", school_name="東京アニメ"))
        session.flush()

        content = "<html><body><a href='/r8.pdf'>令和8年度 確認申請書</a></body></html>".encode()
        content += b"x" * 1000
        monkeypatch.setattr(operator_pages, "_is_safe_url", lambda url: True)
        monkeypatch.setattr(operator_pages, "_fetch_pdf_bytes", lambda url: (200, content))

        result = operator_pages.submit_operator_url(
            session,
            school_id=100,
            url="https://anime.ac.jp/school/public_info/",
            operator_name="op",
        )

        assert result.accepted is True
        assert result.classifier == "html_page"
        assert result.site_created is True

        site = session.query(SchoolSite).one()
        assert site.school_id == 100
        assert site.url_type == "disclosure_page"
        assert site.discovery_method == "operator_manual"
        assert site.verified is True
    finally:
        session.close()


def test_operator_url_reuse_notice_explains_disclosure_page_reuse() -> None:
    level, message = operator_pages.operator_url_reuse_notice("html_page")

    assert level == "success"
    assert "来年度以降" in message
    assert "再取得" in message


def test_operator_url_reuse_notice_warns_pdf_direct_link_is_this_year_only() -> None:
    level, message = operator_pages.operator_url_reuse_notice("target")

    assert level == "warning"
    assert "PDF直リンク" in message
    assert "今年度" in message
    assert "情報公開ページURL" in message


def test_operator_url_kind_label_hides_classifier_codes() -> None:
    assert operator_pages.operator_url_kind_label("html_page") == "情報公開ページ"
    assert operator_pages.operator_url_kind_label("target") == "申請書PDF"
    assert operator_pages.operator_url_kind_label("image_only") == "画像PDF"
    assert operator_pages.operator_url_kind_label("future_classifier") == "URL"


def test_is_storable_operator_url_avoids_network_dependent_dns_checks() -> None:
    assert operator_pages.is_storable_operator_url("https://univ.example.ac.jp/public_info/")
    assert operator_pages.is_storable_operator_url("https://senmon.example.ac.jp/r8.pdf")
    assert not operator_pages.is_storable_operator_url("http://localhost/public_info/")
    assert not operator_pages.is_storable_operator_url("http://127.0.0.1/public_info/")
    assert not operator_pages.is_storable_operator_url("not-a-url")


def test_import_operator_url_csv_inserts_reusable_manual_urls() -> None:
    session = _session()
    try:
        session.add_all(
            [
                School(
                    id=100, prefecture="東京", corporation_name="A法人",
                    school_name="A大学", school_type="大学",
                ),
                School(
                    id=200, prefecture="東京", corporation_name="B法人",
                    school_name="B専門学校", school_type="専門学校",
                ),
            ]
        )
        session.flush()

        result = operator_pages.import_operator_url_csv(
            session,
            "school_id,url\n"
            "100,https://univ.example.ac.jp/public_info/\n"
            "200,https://senmon.example.ac.jp/r8.pdf\n",
        )

        assert result.inserted == 2
        assert result.updated == 0
        assert result.skipped == 0
        sites = session.query(SchoolSite).order_by(SchoolSite.school_id).all()
        assert [site.discovery_method for site in sites] == ["operator_manual", "operator_manual"]
        assert [site.url_type for site in sites] == ["disclosure_page", "pdf"]
        assert [bool(site.verified) for site in sites] == [False, False]
        assert [site.http_status for site in sites] == [None, None]
    finally:
        session.close()


def test_import_operator_url_csv_updates_existing_and_reports_skips() -> None:
    session = _session()
    try:
        session.add(
            School(
                id=100, prefecture="東京", corporation_name="A法人",
                school_name="A大学", school_type="大学",
            )
        )
        session.add(
            SchoolSite(
                school_id=100,
                url="https://univ.example.ac.jp/public_info/",
                url_type=None,
                discovery_method=None,
                confidence=0.1,
            )
        )
        session.flush()

        result = operator_pages.import_operator_url_csv(
            session,
            "学校名,URL\n"
            "A大学,https://univ.example.ac.jp/public_info/\n"
            "不明大学,https://missing.example.ac.jp/public_info/\n"
            "A大学,not-a-url\n",
        )

        assert result.inserted == 0
        assert result.updated == 1
        assert result.skipped == 2
        assert any("school_name not found" in error for error in result.errors)
        assert any("unsafe URL" in error for error in result.errors)
        site = session.query(SchoolSite).one()
        assert site.url_type == "disclosure_page"
        assert site.discovery_method == "operator_manual"
        assert float(site.confidence) == 0.8
    finally:
        session.close()


def test_submit_operator_url_rejects_non_target_without_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    try:
        session.add(School(id=100, prefecture="東京", corporation_name="滋慶", school_name="東京アニメ"))
        session.flush()

        content = b"%PDF-" + b"x" * 2000
        monkeypatch.setattr(operator_pages, "_is_safe_url", lambda url: True)
        monkeypatch.setattr(operator_pages, "_fetch_pdf_bytes", lambda url: (200, content))
        monkeypatch.setattr(operator_pages, "_classify_pdf_content", lambda content: "non_target")

        result = operator_pages.submit_operator_url(
            session,
            school_id=100,
            url="https://anime.ac.jp/not-target.pdf",
        )

        assert result.accepted is False
        assert result.reason == "classified_non_target"
        assert session.query(SchoolSite).count() == 0
    finally:
        session.close()


def test_run_operator_discovery_ingest_uses_strict_target_and_page_discovered_docs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    page_url = "https://anime.ac.jp/school/public_info/"
    try:
        session.add(School(id=100, prefecture="東京", corporation_name="滋慶", school_name="東京アニメ"))
        session.add(
            SchoolSite(
                school_id=100,
                url=page_url,
                url_type="disclosure_page",
                discovery_method="operator_manual",
                http_status=200,
            )
        )
        session.flush()

        calls: dict[str, object] = {}

        def fake_run_pdf_discovery(session_arg, **kwargs):  # noqa: ANN001
            calls["discovery_kwargs"] = kwargs
            session_arg.add(
                Document(
                    school_id=100,
                    source_url="https://anime.ac.jp/r8.pdf",
                    discovered_from=page_url,
                    file_hash="h" * 64,
                    file_path=str(tmp_path / "r8.pdf"),
                    pdf_type="target",
                    ingest_status="pending",
                    fiscal_year=2026,
                )
            )
            session_arg.flush()
            return {"downloaded": 1, "skipped": 0, "failed": 0}

        def fake_run_ingestion(session_arg, **kwargs):  # noqa: ANN001
            calls["ingest_kwargs"] = kwargs
            return {"processed": 1, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

        monkeypatch.setattr("eidp.scraper.pdf_discovery.run_pdf_discovery", fake_run_pdf_discovery)
        monkeypatch.setattr("eidp.pipeline.ingest.run_ingestion", fake_run_ingestion)
        monkeypatch.setattr(operator_pages.settings, "target_fiscal_year", 2026)

        result = operator_pages.run_operator_discovery_ingest(
            session,
            school_id=100,
            source_url=page_url,
            storage_dir=tmp_path,
            discovery_evidence_path=tmp_path / "discovery.jsonl",
            ingest_evidence_path=tmp_path / "ingest.jsonl",
        )

        discovery_kwargs = calls["discovery_kwargs"]
        assert discovery_kwargs["target_fiscal_year"] == 2026
        assert discovery_kwargs["strict_target_fiscal_year"] is True
        assert discovery_kwargs["discovery_methods"] == ["operator_manual"]
        assert result["document_ids"] == [1]
        assert calls["ingest_kwargs"]["document_ids"] == [1]
    finally:
        session.close()


def test_record_operator_submission_appends_jsonl(tmp_path: Path) -> None:
    result = operator_pages.OperatorUrlSubmission(
        accepted=True,
        school_id=100,
        school_name="東京アニメ",
        url="https://example.ac.jp/x.pdf",
        classifier="target",
        reason="inserted",
        http_status=200,
        size_bytes=1234,
        sha256="abc",
        site_id=1,
        site_created=True,
        operator_name="op",
        operator_note="note",
        timestamp="2026-04-24T00:00:00+00:00",
    )
    log_path = tmp_path / "operator.jsonl"

    operator_pages.record_operator_submission(result, log_path)
    operator_pages.record_operator_submission(result, log_path)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["operator_note"] == "note"


def test_operator_ui_cli_launches_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        calls.append(cmd)
        assert check is True

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = CliRunner().invoke(app, ["operator-ui", "--port", "8765"])

    assert result.exit_code == 0
    assert calls
    assert calls[0][-2:] == ["--server.port", "8765"]
    assert calls[0][1:4] == ["-m", "streamlit", "run"]


def test_next_focus_idx_after_decision_keeps_next_item_visible() -> None:
    assert operator_pages._next_focus_idx_after_decision(0, 3) == 0
    assert operator_pages._next_focus_idx_after_decision(1, 3) == 1
    assert operator_pages._next_focus_idx_after_decision(2, 3) == 1
    assert operator_pages._next_focus_idx_after_decision(0, 1) == 0


def test_compute_todo_counts_marks_excel_stale_only_after_new_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session()
    try:
        empty_school = tmp_path / "school.jsonl"
        empty_dept = tmp_path / "dept.jsonl"
        empty_decisions = tmp_path / "decisions.jsonl"
        empty_gap = tmp_path / "gap.csv"
        excel = tmp_path / "competition.xlsx"
        for path in (empty_school, empty_dept, empty_decisions):
            path.write_text("", encoding="utf-8")
        empty_gap.write_text("gap_reason\n", encoding="utf-8")
        excel.write_bytes(b"xlsx")

        now = datetime.now(UTC)
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(
            SchoolAlias(
                school_id=1,
                alias_name="学校Aテンプレ",
                alias_type="competition_template",
                source="proposal_review_queue",
                created_at=now - timedelta(hours=1),
            )
        )
        session.commit()

        monkeypatch.setattr(operator_pages, "_DEFAULT_SCHOOL_PROPOSALS", empty_school)
        monkeypatch.setattr(operator_pages, "_DEFAULT_DEPT_PROPOSALS", empty_dept)
        monkeypatch.setattr(operator_pages, "_DEFAULT_PROPOSAL_DECISIONS", empty_decisions)
        monkeypatch.setattr(operator_pages, "_DEFAULT_COMPETITION_GAP", empty_gap)
        monkeypatch.setattr(operator_pages, "_DEFAULT_COMPETITION", excel)

        os.utime(excel, ((now - timedelta(hours=2)).timestamp(), (now - timedelta(hours=2)).timestamp()))
        assert operator_pages.compute_todo_counts(session).excel_stale is True

        os.utime(excel, (now.timestamp(), now.timestamp()))
        assert operator_pages.compute_todo_counts(session).excel_stale is False
    finally:
        session.close()


def test_compute_todo_counts_includes_prefecture_remark_reviews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session()
    try:
        empty_school = tmp_path / "school.jsonl"
        empty_dept = tmp_path / "dept.jsonl"
        empty_decisions = tmp_path / "decisions.jsonl"
        empty_gap = tmp_path / "gap.csv"
        excel = tmp_path / "competition.xlsx"
        for path in (empty_school, empty_dept, empty_decisions):
            path.write_text("", encoding="utf-8")
        empty_gap.write_text("gap_reason\n", encoding="utf-8")
        excel.write_bytes(b"xlsx")

        session.add(
            ReviewItem(
                item_type="prefecture_remark",
                reference_table="school",
                reference_id=1,
                status="pending",
            )
        )
        session.commit()

        monkeypatch.setattr(operator_pages, "_DEFAULT_SCHOOL_PROPOSALS", empty_school)
        monkeypatch.setattr(operator_pages, "_DEFAULT_DEPT_PROPOSALS", empty_dept)
        monkeypatch.setattr(operator_pages, "_DEFAULT_PROPOSAL_DECISIONS", empty_decisions)
        monkeypatch.setattr(operator_pages, "_DEFAULT_COMPETITION_GAP", empty_gap)
        monkeypatch.setattr(operator_pages, "_DEFAULT_COMPETITION", excel)

        assert operator_pages.compute_todo_counts(session).pending_prefecture_remarks == 1
    finally:
        session.close()
