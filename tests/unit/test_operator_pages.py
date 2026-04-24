from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.models import Base, School, SchoolAlias, SchoolSite
from eidp.review import operator_pages


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_output_path_allows_output_and_rejects_traversal() -> None:
    path = operator_pages.output_path("output/test.xlsx", (".xlsx",))
    assert path.name == "test.xlsx"

    with pytest.raises(operator_pages.PathPolicyError):
        operator_pages.output_path("../secrets.xlsx", (".xlsx",))


def test_output_path_rejects_wrong_suffix() -> None:
    with pytest.raises(operator_pages.PathPolicyError):
        operator_pages.output_path("output/test.txt", (".xlsx",))


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

        now = datetime.now(timezone.utc)
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
