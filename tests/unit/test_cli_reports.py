from __future__ import annotations

import json
import sqlite3

from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from eidp.cli import app
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


def test_report_ship_readiness_json_uses_operator_review_gate(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.ship_readiness as ship_readiness

    def fake_compute_ship_readiness(*_args, **_kwargs):  # noqa: ANN002, ANN003
        operator_review_criteria = (
            ShipReadinessCriterion("estimated_manual_workload", 0.3, 0.3, True),
        )
        strict_data_criteria = (
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
    assert payload["criteria"][0]["name"] == "estimated_manual_workload"
    assert payload["operator_review_criteria"][0]["name"] == "estimated_manual_workload"
    assert payload["strict_data_criteria"][0]["name"] == "excel_ready"
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
