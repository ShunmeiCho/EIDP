from __future__ import annotations

import json
import sqlite3

from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from eidp.cli import app
from eidp.reports.coverage import CoverageReport, PrefectureCoverage
from eidp.reports.extraction import DeltaOutlier, ExtractionReport
from eidp.reports.gaps import GapEntry, GapsReport
from eidp.reports.ship_readiness import ShipReadinessCriterion, ShipReadinessReport


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class MissingSchemaQuery:
    def scalar(self) -> int:
        raise OperationalError("SELECT * FROM school", {}, Exception("no such table: school"))


class MissingSchemaSession(FakeSession):
    def query(self, *_args, **_kwargs) -> MissingSchemaQuery:  # noqa: ANN002, ANN003
        return MissingSchemaQuery()


def test_db_info_fails_cleanly_when_database_schema_is_missing(monkeypatch) -> None:
    fake_session = MissingSchemaSession()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)

    result = CliRunner().invoke(app, ["db-info"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert "ERROR: db-info query failed" in result.output
    assert "schema is incomplete" in result.output
    assert "DETAIL:" in result.output
    assert fake_session.closed is True


def test_db_backup_cli_creates_consistent_sqlite_backup(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "data" / "eidp.sqlite3"
    backup_path = tmp_path / "backup.sqlite3"
    db_path.parent.mkdir()
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE sample (name TEXT NOT NULL)")
    con.execute("INSERT INTO sample (name) VALUES ('cli')")
    con.commit()
    con.close()

    import eidp.config as config

    monkeypatch.setattr(config.settings, "database_url", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(config.settings, "data_dir", db_path.parent)

    result = CliRunner().invoke(app, ["db-backup", "--output", str(backup_path)])

    assert result.exit_code == 0
    assert "SQLite backup written:" in result.output
    backup = sqlite3.connect(backup_path)
    try:
        rows = backup.execute("SELECT name FROM sample").fetchall()
    finally:
        backup.close()
    assert rows == [("cli",)]


def test_report_coverage_json_fails_cleanly_when_database_schema_is_missing(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.coverage as coverage

    def fake_compute_coverage(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise OperationalError("SELECT * FROM school", {}, Exception("no such table: school"))

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(coverage, "compute_coverage", fake_compute_coverage)

    result = CliRunner().invoke(app, ["report", "coverage", "--json"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "database_not_ready"
    assert "schema is incomplete" in payload["message"]
    assert "no such table: school" in payload["detail"]
    assert fake_session.closed is True


def test_report_coverage_text_fails_cleanly_when_database_schema_is_missing(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.coverage as coverage

    def fake_compute_coverage(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise OperationalError("SELECT * FROM school", {}, Exception("no such table: school"))

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(coverage, "compute_coverage", fake_compute_coverage)

    result = CliRunner().invoke(app, ["report", "coverage"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert "ERROR: report query failed" in result.output
    assert "DETAIL:" in result.output
    assert fake_session.closed is True


def _coverage_report() -> CoverageReport:
    tokyo = PrefectureCoverage(
        prefecture="東京都",
        schools_total=10,
        schools_with_url=8,
        schools_with_verified_url=7,
        schools_with_any_pdf=6,
        schools_with_target_pdf_any_fy=5,
        schools_with_target_pdf_current_fy=4,
        schools_with_current_fy_doc=4,
        schools_with_current_fy_extracted=3,
    )
    osaka = PrefectureCoverage(
        prefecture="大阪府",
        schools_total=5,
        schools_with_url=5,
        schools_with_verified_url=4,
        schools_with_any_pdf=4,
        schools_with_target_pdf_any_fy=3,
        schools_with_target_pdf_current_fy=2,
        schools_with_current_fy_doc=2,
        schools_with_current_fy_extracted=2,
    )
    totals = PrefectureCoverage(
        prefecture="ALL",
        schools_total=15,
        schools_with_url=13,
        schools_with_verified_url=11,
        schools_with_any_pdf=10,
        schools_with_target_pdf_any_fy=8,
        schools_with_target_pdf_current_fy=6,
        schools_with_current_fy_doc=6,
        schools_with_current_fy_extracted=5,
    )
    return CoverageReport(
        fiscal_year=2026,
        school_type="専門学校",
        by_prefecture=(tokyo, osaka),
        totals=totals,
    )


def test_report_coverage_success_outputs_json_and_prefecture_table(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.coverage as coverage

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(coverage, "compute_coverage", lambda *_args, **_kwargs: _coverage_report())

    json_result = CliRunner().invoke(app, ["report", "coverage", "--json"])
    text_result = CliRunner().invoke(app, ["report", "coverage", "--by-prefecture"])

    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["fiscal_year"] == 2026
    assert payload["totals"]["schools_total"] == 15
    assert payload["totals"]["target_pdf_current_fy_rate"] == 0.4
    assert payload["by_prefecture"][0]["prefecture"] == "東京都"
    assert text_result.exit_code == 0, text_result.output
    assert "FY: 2026  school_type: 専門学校" in text_result.output
    assert "Schools: 15  url=13" in text_result.output
    assert "東京都" in text_result.output
    assert "大阪府" in text_result.output
    assert fake_session.closed is True


def test_report_extraction_success_outputs_json_and_outlier_text(monkeypatch) -> None:
    fake_session = FakeSession()
    report = ExtractionReport(
        fiscal_year=2026,
        documents_ingested=4,
        documents_with_yearly_rows=3,
        yearly_rows_total=5,
        yearly_rows_with_capacity=4,
        yearly_rows_with_enrollment=4,
        delta_outliers=(
            DeltaOutlier(
                school_id=1,
                department_id=10,
                department_name="AI学科",
                prev_value=100,
                curr_value=160,
                delta_pct=60.0,
            ),
        ),
        delta_threshold_pct=50.0,
    )

    import eidp.db.session as db_session
    import eidp.reports.extraction as extraction

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(extraction, "compute_extraction", lambda *_args, **_kwargs: report)

    json_result = CliRunner().invoke(app, ["report", "extraction", "--fy", "2026", "--json"])
    text_result = CliRunner().invoke(app, ["report", "extraction", "--fy", "2026"])

    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["extraction_rate"] == 0.75
    assert payload["capacity_fill_rate"] == 0.8
    assert payload["delta_outliers"][0]["department_name"] == "AI学科"
    assert text_result.exit_code == 0, text_result.output
    assert "FY2026 extraction:" in text_result.output
    assert "documents ingested: 4" in text_result.output
    assert "AI学科: 100 -> 160 (+60.0%)" in text_result.output
    assert fake_session.closed is True


def test_report_gaps_success_outputs_json_and_reason_table(monkeypatch, tmp_path) -> None:
    fake_session = FakeSession()
    report = GapsReport(
        kind="pdf",
        total=2,
        by_reason={"stale_pdf_only": 1, "parse_failed_only": 1},
        sample=(
            GapEntry(school_id=1, school_name="A専門学校", reason="stale_pdf_only", detail="FY2025"),
            GapEntry(school_id=2, school_name="B専門学校", reason="parse_failed_only", detail="parse error"),
        ),
    )

    import eidp.db.session as db_session
    import eidp.reports.gaps as gaps

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(gaps, "compute_gaps", lambda *_args, **_kwargs: report)

    json_result = CliRunner().invoke(app, ["report", "gaps", "--kind", "pdf", "--json"])
    text_result = CliRunner().invoke(app, ["report", "gaps", "--kind", "pdf", "--fy", "2026"])

    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["kind"] == "pdf"
    assert payload["total"] == 2
    assert payload["sample"][0]["school_name"] == "A専門学校"
    assert text_result.exit_code == 0, text_result.output
    assert "Gap kind: pdf  total: 2" in text_result.output
    assert "stale_pdf_only: 1" in text_result.output
    assert "#1 A専門学校" in text_result.output
    assert fake_session.closed is True


def test_report_ship_readiness_json_uses_operator_review_gate(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.ship_readiness as ship_readiness

    def fake_compute_ship_readiness(*_args, **_kwargs):  # noqa: ANN002, ANN003
        operator_review_criteria = (
            ShipReadinessCriterion("estimated_manual_workload", 0.3, 0.3, True),
        )
        strict_data_criteria = (
            ShipReadinessCriterion("strict_target_pdf", 0.5, 0.6, False),
            ShipReadinessCriterion("excel_ready", 0.4, 0.6, False),
        )
        return ShipReadinessReport(
            fiscal_year=2026,
            school_type="専門学校",
            total_schools=10,
            strict_target_pdf_schools=5,
            strict_target_pdf_rate=0.5,
            operator_reviewable_schools=7,
            operator_reviewable_rate=0.7,
            estimated_manual_workload_rate=0.3,
            excel_ready_schools=4,
            excel_ready_rate=0.4,
            extracted_schools=5,
            extracted_rate=0.5,
            strict_auto_target_pdf_min=0.6,
            manual_workload_max=0.3,
            operator_review_criteria=operator_review_criteria,
            strict_data_criteria=strict_data_criteria,
            criteria=operator_review_criteria + strict_data_criteria,
        )

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(ship_readiness, "compute_ship_readiness", fake_compute_ship_readiness)

    result = CliRunner().invoke(app, ["report", "ship-readiness", "--json", "--fail-on-missing-goal"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["ok_operator_review"] is True
    assert payload["ok_strict"] is False
    assert payload["strict_target_pdf_rate"] == 0.5
    assert payload["estimated_manual_workload_rate"] == 0.3
    assert [criterion["name"] for criterion in payload["criteria"]] == ["estimated_manual_workload"]
    assert payload["operator_review_criteria"][0]["name"] == "estimated_manual_workload"
    assert [criterion["name"] for criterion in payload["strict_data_criteria"]] == ["strict_target_pdf", "excel_ready"]
    assert fake_session.closed is True


def test_report_ship_readiness_json_marks_retroactive_fiscal_year(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.cli_reports as cli_reports
    import eidp.db.session as db_session
    import eidp.reports.ship_readiness as ship_readiness

    seen_kwargs: dict[str, object] = {}

    def fake_compute_ship_readiness(*_args, **kwargs):  # noqa: ANN002, ANN003
        seen_kwargs.update(kwargs)
        operator_review_criteria = (
            ShipReadinessCriterion("estimated_manual_workload", 0.2, 0.3, True),
        )
        strict_data_criteria = (
            ShipReadinessCriterion("strict_target_pdf", 0.7, 0.6, True),
            ShipReadinessCriterion("excel_ready", 0.7, 0.6, True),
        )
        return ShipReadinessReport(
            fiscal_year=int(kwargs["fiscal_year"]),
            school_type="専門学校",
            total_schools=10,
            strict_target_pdf_schools=7,
            strict_target_pdf_rate=0.7,
            operator_reviewable_schools=8,
            operator_reviewable_rate=0.8,
            estimated_manual_workload_rate=0.2,
            excel_ready_schools=7,
            excel_ready_rate=0.7,
            extracted_schools=7,
            extracted_rate=0.7,
            strict_auto_target_pdf_min=0.6,
            manual_workload_max=0.3,
            operator_review_criteria=operator_review_criteria,
            strict_data_criteria=strict_data_criteria,
            criteria=operator_review_criteria + strict_data_criteria,
        )

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(ship_readiness, "compute_ship_readiness", fake_compute_ship_readiness)
    monkeypatch.setattr(cli_reports, "current_fiscal_year", lambda: 2026)
    monkeypatch.setattr(cli_reports.settings, "target_fiscal_year", 2026)

    result = CliRunner().invoke(app, ["report", "ship-readiness", "--fy", "2025", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert seen_kwargs["fiscal_year"] == 2025
    assert payload["fiscal_year"] == 2025
    assert payload["configured_target_fiscal_year"] == 2026
    assert payload["calendar_current_fiscal_year"] == 2026
    assert payload["is_configured_target_fiscal_year"] is False
    assert payload["is_retroactive_fiscal_year"] is True
    assert fake_session.closed is True


def test_report_ship_readiness_json_can_fail_when_operator_review_gate_missing(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.ship_readiness as ship_readiness

    def fake_compute_ship_readiness(*_args, **_kwargs):  # noqa: ANN002, ANN003
        operator_review_criteria = (
            ShipReadinessCriterion("estimated_manual_workload", 0.4, 0.3, False),
        )
        strict_data_criteria = (
            ShipReadinessCriterion("strict_target_pdf", 0.8, 0.6, True),
            ShipReadinessCriterion("excel_ready", 0.8, 0.6, True),
        )
        return ShipReadinessReport(
            fiscal_year=2026,
            school_type="専門学校",
            total_schools=10,
            strict_target_pdf_schools=8,
            strict_target_pdf_rate=0.8,
            operator_reviewable_schools=6,
            operator_reviewable_rate=0.6,
            estimated_manual_workload_rate=0.4,
            excel_ready_schools=8,
            excel_ready_rate=0.8,
            extracted_schools=8,
            extracted_rate=0.8,
            strict_auto_target_pdf_min=0.6,
            manual_workload_max=0.3,
            operator_review_criteria=operator_review_criteria,
            strict_data_criteria=strict_data_criteria,
            criteria=operator_review_criteria + strict_data_criteria,
        )

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(ship_readiness, "compute_ship_readiness", fake_compute_ship_readiness)

    result = CliRunner().invoke(app, ["report", "ship-readiness", "--json", "--fail-on-missing-goal"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["ok_operator_review"] is False
    assert payload["ok_strict"] is True
    assert fake_session.closed is True
