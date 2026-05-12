from __future__ import annotations

import json

from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from eidp.cli import app
from eidp.reports.ship_readiness import ShipReadinessCriterion, ShipReadinessReport


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


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


def test_report_ship_readiness_json_can_fail_on_missing_goal(monkeypatch) -> None:
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.reports.ship_readiness as ship_readiness

    def fake_compute_ship_readiness(*_args, **_kwargs):  # noqa: ANN002, ANN003
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
            criteria=(
                ShipReadinessCriterion("strict_target_pdf_auto_acquisition", 0.5, 0.6, False),
                ShipReadinessCriterion("estimated_manual_workload", 0.3, 0.3, True),
                ShipReadinessCriterion("excel_ready", 0.4, 0.6, False),
            ),
        )

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(ship_readiness, "compute_ship_readiness", fake_compute_ship_readiness)

    result = CliRunner().invoke(app, ["report", "ship-readiness", "--json", "--fail-on-missing-goal"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["strict_target_pdf_rate"] == 0.5
    assert payload["estimated_manual_workload_rate"] == 0.3
    assert payload["criteria"][0]["name"] == "strict_target_pdf_auto_acquisition"
    assert fake_session.closed is True
