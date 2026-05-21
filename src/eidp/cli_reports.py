"""Typer subcommands for EIDP acceptance reports."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NoReturn

import typer
from sqlalchemy.exc import SQLAlchemyError

from eidp.config import settings
from eidp.fiscal_year import current_fiscal_year
from eidp.reports.coverage import PrefectureCoverage

report_app = typer.Typer(name="report", help="Acceptance-criteria reports")

_REPORT_DATABASE_NOT_READY_MESSAGE = (
    "report query failed; database is not initialized or the schema is incomplete. "
    "Run setup/db-bootstrap/import before using eidp report commands."
)


def _exit_report_db_error(exc: SQLAlchemyError, *, output_json: bool) -> NoReturn:
    detail = str(exc).splitlines()[0]
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": "database_not_ready",
                    "message": _REPORT_DATABASE_NOT_READY_MESSAGE,
                    "detail": detail,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        typer.echo(f"ERROR: {_REPORT_DATABASE_NOT_READY_MESSAGE}", err=True)
        typer.echo(f"DETAIL: {detail}", err=True)
    raise typer.Exit(2) from exc


@report_app.command("coverage")
def report_coverage(
    school_type: str = typer.Option("専門学校", help="Filter by school_type (or 'all')"),
    fiscal_year: int | None = typer.Option(None, help="Fiscal year (defaults to configured target FY)"),
    by_prefecture: bool = typer.Option(False, "--by-prefecture", help="Show per-prefecture breakdown"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
) -> None:
    """Coverage rollup: schools / URLs / PDFs / extracted, by prefecture."""
    from eidp.db.session import SessionLocal
    from eidp.reports.coverage import compute_coverage

    session = SessionLocal()
    try:
        st = None if school_type == "all" else school_type
        report = compute_coverage(session, school_type=st, fiscal_year=fiscal_year)
    except SQLAlchemyError as exc:
        _exit_report_db_error(exc, output_json=output_json)
    finally:
        session.close()

    if output_json:
        payload = {
            "fiscal_year": report.fiscal_year,
            "school_type": report.school_type,
            "totals": _coverage_row_to_dict(report.totals),
            "by_prefecture": [_coverage_row_to_dict(r) for r in report.by_prefecture],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    t = report.totals
    typer.echo(f"FY: {report.fiscal_year}  school_type: {report.school_type or 'all'}")
    typer.echo(
        f"Schools: {t.schools_total}  url={t.schools_with_url} ({t.url_rate:.1%}) "
        f"any_pdf={t.schools_with_any_pdf} ({t.any_pdf_rate:.1%}) "
        f"target_any_fy={t.schools_with_target_pdf_any_fy} ({t.target_pdf_any_fy_rate:.1%}) "
        f"target_FY{report.fiscal_year}={t.schools_with_target_pdf_current_fy} "
        f"({t.target_pdf_current_fy_rate:.1%})  "
        f"extracted={t.schools_with_current_fy_extracted} ({t.current_fy_rate:.1%})"
    )
    if by_prefecture:
        typer.echo(
            f"\n{'Pref':<10} {'Total':>6} {'URL':>6} {'AnyPDF':>7} {'TgtAny':>7} "
            f"{'TgtFY':>6} {'Extr':>6} {'TgtFY%':>7}"
        )
        for r in report.by_prefecture:
            typer.echo(
                f"{r.prefecture:<10} {r.schools_total:>6} {r.schools_with_url:>6} "
                f"{r.schools_with_any_pdf:>7} {r.schools_with_target_pdf_any_fy:>7} "
                f"{r.schools_with_target_pdf_current_fy:>6} "
                f"{r.schools_with_current_fy_extracted:>6} "
                f"{r.target_pdf_current_fy_rate:>6.1%}"
            )


def _coverage_row_to_dict(r: PrefectureCoverage) -> dict[str, object]:
    return {
        "prefecture": r.prefecture,
        "schools_total": r.schools_total,
        "schools_with_url": r.schools_with_url,
        "schools_with_verified_url": r.schools_with_verified_url,
        "schools_with_any_pdf": r.schools_with_any_pdf,
        "schools_with_target_pdf_any_fy": r.schools_with_target_pdf_any_fy,
        "schools_with_target_pdf_current_fy": r.schools_with_target_pdf_current_fy,
        "schools_with_current_fy_doc": r.schools_with_current_fy_doc,
        "schools_with_current_fy_extracted": r.schools_with_current_fy_extracted,
        "url_rate": round(r.url_rate, 4),
        "any_pdf_rate": round(r.any_pdf_rate, 4),
        "target_pdf_any_fy_rate": round(r.target_pdf_any_fy_rate, 4),
        "target_pdf_current_fy_rate": round(r.target_pdf_current_fy_rate, 4),
        "current_fy_rate": round(r.current_fy_rate, 4),
    }


@report_app.command("extraction")
def report_extraction(
    fiscal_year: int = typer.Option(..., "--fy", help="Fiscal year, e.g. 2026"),
    delta_threshold: float = typer.Option(50.0, help="Delta % threshold for outlier flag"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
) -> None:
    """Extraction rate for FY + prev-year delta outliers."""
    from eidp.db.session import SessionLocal
    from eidp.reports.extraction import compute_extraction

    session = SessionLocal()
    try:
        report = compute_extraction(session, fiscal_year, delta_threshold)
    except SQLAlchemyError as exc:
        _exit_report_db_error(exc, output_json=output_json)
    finally:
        session.close()

    if output_json:
        payload = {
            "fiscal_year": report.fiscal_year,
            "documents_ingested": report.documents_ingested,
            "documents_with_yearly_rows": report.documents_with_yearly_rows,
            "extraction_rate": round(report.extraction_rate, 4),
            "yearly_rows_total": report.yearly_rows_total,
            "yearly_rows_with_capacity": report.yearly_rows_with_capacity,
            "yearly_rows_with_enrollment": report.yearly_rows_with_enrollment,
            "capacity_fill_rate": round(report.capacity_fill_rate, 4),
            "delta_threshold_pct": report.delta_threshold_pct,
            "delta_outliers": [
                {
                    "school_id": o.school_id,
                    "department_id": o.department_id,
                    "department_name": o.department_name,
                    "prev_value": o.prev_value,
                    "curr_value": o.curr_value,
                    "delta_pct": o.delta_pct,
                }
                for o in report.delta_outliers
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    typer.echo(f"FY{report.fiscal_year} extraction:")
    typer.echo(
        f"  documents ingested: {report.documents_ingested}  "
        f"with yearly rows: {report.documents_with_yearly_rows}  "
        f"rate: {report.extraction_rate:.1%}"
    )
    typer.echo(
        f"  yearly rows: {report.yearly_rows_total}  "
        f"capacity: {report.yearly_rows_with_capacity} ({report.capacity_fill_rate:.1%})  "
        f"enrollment: {report.yearly_rows_with_enrollment}"
    )
    typer.echo(
        f"  outliers vs FY{report.fiscal_year - 1} "
        f"(>= {report.delta_threshold_pct}%): {len(report.delta_outliers)}"
    )
    for o in report.delta_outliers[:10]:
        typer.echo(
            f"    school#{o.school_id} dept#{o.department_id} {o.department_name}: "
            f"{o.prev_value} -> {o.curr_value} ({o.delta_pct:+.1f}%)"
        )


@report_app.command("gaps")
def report_gaps(
    kind: str = typer.Option(..., "--kind", help="url|pdf|extraction|competition"),
    school_type: str = typer.Option("専門学校", help="Filter by school_type (or 'all')"),
    fiscal_year: int | None = typer.Option(None, "--fy", help="Required for kind=extraction"),
    competition_csv: Path | None = typer.Option(None, help="Override path for kind=competition"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
) -> None:
    """Unified gap counters by kind."""
    from eidp.db.session import SessionLocal
    from eidp.reports.gaps import compute_gaps

    session = SessionLocal()
    try:
        st = None if school_type == "all" else school_type
        report = compute_gaps(
            session,
            kind,  # type: ignore[arg-type]
            school_type=st,
            fiscal_year=fiscal_year,
            competition_csv=competition_csv,
        )
    except SQLAlchemyError as exc:
        _exit_report_db_error(exc, output_json=output_json)
    finally:
        session.close()

    if output_json:
        payload = {
            "kind": report.kind,
            "total": report.total,
            "by_reason": report.by_reason,
            "sample": [
                {
                    "school_id": e.school_id,
                    "school_name": e.school_name,
                    "reason": e.reason,
                    "detail": e.detail,
                }
                for e in report.sample
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    typer.echo(f"Gap kind: {report.kind}  total: {report.total}")
    for reason, count in sorted(report.by_reason.items(), key=lambda x: -x[1]):
        typer.echo(f"  {reason}: {count}")
    if report.sample:
        typer.echo(f"\nSample (first {len(report.sample)}):")
        for e in report.sample[:20]:
            typer.echo(f"  #{e.school_id or '-'} {e.school_name or '-'}  [{e.reason}]  {e.detail}")


@report_app.command("ship-readiness")
def report_ship_readiness(
    school_type: str = typer.Option("専門学校", help="Filter by school_type (or 'all')"),
    fiscal_year: int | None = typer.Option(None, "--fy", help="Fiscal year (defaults to configured target FY)"),
    strict_target_pdf_min: float = typer.Option(
        0.60,
        "--strict-target-pdf-min",
        help="Minimum strict target-FY PDF and Excel-ready data rate",
    ),
    manual_workload_max: float = typer.Option(
        0.30,
        "--manual-workload-max",
        help="Maximum estimated remaining manual workload rate",
    ),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
    fail_on_missing_goal: bool = typer.Option(
        False,
        "--fail-on-missing-goal",
        help="Exit non-zero when the operator-reviewable ship line is not met",
    ),
) -> None:
    """Final objective readiness: operator review coverage plus strict data diagnostics."""
    from eidp.db.session import SessionLocal
    from eidp.reports.ship_readiness import compute_ship_readiness

    session = SessionLocal()
    try:
        st = None if school_type == "all" else school_type
        report = compute_ship_readiness(
            session,
            fiscal_year=fiscal_year,
            school_type=st,
            strict_auto_target_pdf_min=strict_target_pdf_min,
            manual_workload_max=manual_workload_max,
        )
    except SQLAlchemyError as exc:
        _exit_report_db_error(exc, output_json=output_json)
    finally:
        session.close()

    payload = _ship_readiness_to_dict(report)
    if output_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"FY: {report.fiscal_year}  school_type: {report.school_type or 'all'}")
        if payload["is_retroactive_fiscal_year"]:
            typer.echo(
                "Evidence scope: retroactive fiscal-year validation "
                f"(calendar_current_fiscal_year={payload['calendar_current_fiscal_year']})"
            )
        typer.echo(f"Operator-review status: {'pass' if report.ok_operator_review else 'missing'}")
        typer.echo(f"Strict data status: {'pass' if report.ok_strict else 'missing'}")
        typer.echo(
            f"  strict target PDF: {report.strict_target_pdf_schools}/{report.total_schools} "
            f"({report.strict_target_pdf_rate:.1%})"
        )
        typer.echo(
            f"  operator-reviewable: {report.operator_reviewable_schools}/{report.total_schools} "
            f"({report.operator_reviewable_rate:.1%})"
        )
        typer.echo(f"  estimated manual workload: {report.estimated_manual_workload_rate:.1%}")
        typer.echo(
            f"  Excel ready: {report.excel_ready_schools}/{report.total_schools} "
            f"({report.excel_ready_rate:.1%})"
        )
    if fail_on_missing_goal and not report.ok:
        raise typer.Exit(1)


def _ship_readiness_to_dict(report: Any) -> dict[str, object]:
    calendar_current_fy = current_fiscal_year()
    return {
        "ok": report.ok,
        "ok_operator_review": report.ok_operator_review,
        "ok_strict": report.ok_strict,
        "fiscal_year": report.fiscal_year,
        "configured_target_fiscal_year": int(settings.target_fiscal_year),
        "calendar_current_fiscal_year": calendar_current_fy,
        "is_configured_target_fiscal_year": report.fiscal_year == int(settings.target_fiscal_year),
        "is_retroactive_fiscal_year": report.fiscal_year < calendar_current_fy,
        "school_type": report.school_type,
        "total_schools": report.total_schools,
        "strict_target_pdf_schools": report.strict_target_pdf_schools,
        "strict_target_pdf_rate": round(report.strict_target_pdf_rate, 4),
        "operator_reviewable_schools": report.operator_reviewable_schools,
        "operator_reviewable_rate": round(report.operator_reviewable_rate, 4),
        "estimated_manual_workload_rate": round(report.estimated_manual_workload_rate, 4),
        "excel_ready_schools": report.excel_ready_schools,
        "excel_ready_rate": round(report.excel_ready_rate, 4),
        "extracted_schools": report.extracted_schools,
        "extracted_rate": round(report.extracted_rate, 4),
        "strict_auto_target_pdf_min": report.strict_auto_target_pdf_min,
        "manual_workload_max": report.manual_workload_max,
        "criteria": _ship_readiness_criteria_to_dicts(report.criteria),
        "operator_review_criteria": _ship_readiness_criteria_to_dicts(report.operator_review_criteria),
        "strict_data_criteria": _ship_readiness_criteria_to_dicts(report.strict_data_criteria),
    }


def _ship_readiness_criteria_to_dicts(criteria: Iterable[Any]) -> list[dict[str, object]]:
    return [
        {
            "name": criterion.name,
            "value": round(criterion.value, 4),
            "threshold": criterion.threshold,
            "passed": criterion.passed,
        }
        for criterion in criteria
    ]
