"""Top-level read-only/tool CLI command handlers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import typer
from sqlalchemy.exc import SQLAlchemyError


def register_tool_commands(app: typer.Typer) -> None:
    app.command()(verify_identity)
    app.command()(db_info)
    app.command()(review_ui)
    app.command()(operator_ui)
    app.command()(export_excel)
    app.command()(export_competition_excel)
    app.command()(diff_excel)
    app.command()(eval_pdf)


def _echo_excel_export_results(output: Path, results: dict[str, int]) -> None:
    """Print workbook sheet counts separately from export quality counters."""
    typer.echo(f"Exported to: {output}")
    sheet_counts = {name: count for name, count in results.items() if not name.startswith("quality_")}
    quality_warnings = {
        name.removeprefix("quality_"): count for name, count in results.items() if name.startswith("quality_")
    }
    for sheet, count in sheet_counts.items():
        typer.echo(f"  {sheet}: {count} rows")
    nonzero_quality = {name: count for name, count in quality_warnings.items() if count}
    if nonzero_quality:
        typer.echo("Quality warnings:")
        for name, count in nonzero_quality.items():
            typer.echo(f"  {name}: {count}")


_DATABASE_NOT_READY_DETAIL = "database is not initialized or the schema is incomplete"


def _exit_database_not_ready_error(exc: SQLAlchemyError, *, output_json: bool, command_label: str) -> NoReturn:
    message = (
        f"{command_label} query failed; {_DATABASE_NOT_READY_DETAIL}. "
        "Run setup/db-bootstrap/import before using EIDP read/report commands."
    )
    detail = str(exc).splitlines()[0]
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": "database_not_ready",
                    "message": message,
                    "detail": detail,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        typer.echo(f"ERROR: {message}", err=True)
        typer.echo(f"DETAIL: {detail}", err=True)
    raise typer.Exit(2) from exc


def verify_identity(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
) -> None:
    """Verify all schools have stable IDs (Step 4 gate)."""
    from eidp.db.session import SessionLocal
    from eidp.matcher.reconciler import verify_identity as do_verify

    session = SessionLocal()
    try:
        result = do_verify(session, data_dir)
        typer.echo("\nIdentity Verification:")
        for k, v in result.items():
            typer.echo(f"  {k}: {v}")
        if result["pass"]:
            typer.echo("\nGATE: PASS")
        else:
            typer.echo(
                "\nGATE: FAIL "
                f"(truly_unresolved={result['truly_unresolved']}, "
                f"target_gap={result['target_list_gap']})"
            )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_info() -> None:
    """Show database statistics."""
    from sqlalchemy import func

    from eidp.db.models import (
        CrawlJob,
        Department,
        DepartmentYearly,
        Document,
        School,
        SchoolAlias,
        SchoolSite,
        SchoolYearStatus,
        SupportRecipient,
    )
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        typer.echo(f"Schools:            {session.query(func.count(School.id)).scalar()}")
        school_code_count = session.query(func.count(School.id)).filter(School.school_code.isnot(None)).scalar()
        typer.echo(f"  with school_code: {school_code_count}")
        typer.echo(f"Departments:        {session.query(func.count(Department.id)).scalar()}")
        typer.echo(f"DepartmentYearly:   {session.query(func.count(DepartmentYearly.id)).scalar()}")
        typer.echo(f"SchoolYearStatus:   {session.query(func.count(SchoolYearStatus.id)).scalar()}")
        typer.echo(f"SupportRecipient:   {session.query(func.count(SupportRecipient.id)).scalar()}")
        typer.echo(f"SchoolAlias:        {session.query(func.count(SchoolAlias.id)).scalar()}")
        typer.echo(f"SchoolSite:         {session.query(func.count(SchoolSite.id)).scalar()}")
        typer.echo(f"Document:           {session.query(func.count(Document.id)).scalar()}")
        typer.echo(f"CrawlJob:           {session.query(func.count(CrawlJob.id)).scalar()}")
    except SQLAlchemyError as exc:
        _exit_database_not_ready_error(exc, output_json=False, command_label="db-info")
    finally:
        session.close()


def review_ui(
    port: int = typer.Option(8501, help="Port for the Streamlit server"),
) -> None:
    """Launch the Streamlit operator/review UI."""
    app_path = Path(__file__).parent / "review" / "app.py"
    typer.echo(f"Launching review UI on http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


def operator_ui(
    port: int = typer.Option(8501, help="Port for the Streamlit server"),
) -> None:
    """Launch the Streamlit operator console for URL補足, exports, and review."""
    app_path = Path(__file__).parent / "review" / "app.py"
    typer.echo(f"Launching operator UI on http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


def export_excel(
    output: Path = typer.Option(Path("output/専門学校無償化情報公開まとめ.xlsx"), help="Output Excel file path"),
) -> None:
    """Export master Excel workbook from database (Step 10)."""
    from eidp.db.session import SessionLocal
    from eidp.excel.exporter import export_master_workbook

    session = SessionLocal()
    try:
        results = export_master_workbook(session, output)
        _echo_excel_export_results(output, results)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def export_competition_excel(
    template: Path = typer.Option(
        Path("sample/20250826更新版_競合校の在校生数.xlsx"),
        help="Template workbook to overlay (16-sheet 競合校 layout)",
    ),
    output: Path = typer.Option(
        Path("output/競合校の在校生数.xlsx"),
        help="Output workbook path",
    ),
    fiscal_year: int = typer.Option(
        0,
        help="Fiscal year column to add/update; 0 = configured target fiscal year",
    ),
    gap_report: Path = typer.Option(
        Path("output/競合校gap-report.csv"),
        help="CSV listing template rows that could not be matched",
    ),
) -> None:
    """Generate 競合校の在校生数 workbook from template + DB (Step 10b)."""
    from eidp.db.session import SessionLocal
    from eidp.excel.competition_exporter import export_competition_workbook

    session = SessionLocal()
    try:
        fy_arg: int | None = fiscal_year if fiscal_year > 0 else None
        stats = export_competition_workbook(session, template, output, fy_arg, gap_report)
        typer.echo(f"Exported to: {output}")
        typer.echo(f"  fiscal_year:        {stats['fiscal_year']}")
        typer.echo(f"  matched:            {stats['matched']}")
        typer.echo(f"  unmatched:          {stats['unmatched']}")
        typer.echo(f"  cells_written:      {stats['cells_written']}")
        typer.echo(f"  ratio_cells:        {stats['ratio_cells_written']}")
        typer.echo(f"  target_yearly_rows: {stats.get('target_yearly_rows', 0)}")
        typer.echo(f"  excel_ready_schools:{stats.get('excel_ready_schools', 0)}")
        if stats["unmatched"]:
            typer.echo(f"  gap report:         {gap_report}")
    finally:
        session.close()


def diff_excel(
    exported: Path = typer.Argument(..., help="Path to exported Excel file"),
    original: Path = typer.Option(
        Path("sample/◆2025専門学校無償化情報公開まとめ.xlsx"),
        help="Path to original reference Excel",
    ),
) -> None:
    """Compare exported vs original Excel row counts per sheet."""
    from eidp.excel.exporter import diff_workbooks

    results = diff_workbooks(exported, original)
    typer.echo("Sheet comparison (exported vs original):")
    typer.echo(f"  {'Sheet':<16} {'Exported':>10} {'Original':>10} {'Diff':>8}")
    typer.echo(f"  {'-' * 16} {'-' * 10} {'-' * 10} {'-' * 8}")
    for sheet, stats in results.items():
        diff_str = f"{stats['diff']:+d}" if stats["diff"] != 0 else "0"
        typer.echo(f"  {sheet:<16} {stats['exported']:>10} {stats['original']:>10} {diff_str:>8}")


def eval_pdf(
    gold_dir: Path = typer.Option(Path("data/gold-set"), help="Gold annotation directory"),
    pdf_dir: Path = typer.Option(Path("data/sample-pdfs"), help="Sample PDF directory"),
) -> None:
    """Evaluate PDF parser against gold set (Step 5 / Step 9)."""
    from eidp.pdf.eval_harness import load_all_gold_annotations, print_eval_report, run_full_evaluation
    from eidp.pdf.extractor import parse_pdf

    annotations = load_all_gold_annotations(gold_dir)
    typer.echo(f"Gold set: {len(annotations)} annotations loaded")
    for key, ann in annotations.items():
        typer.echo(f"  {key}: {ann.school_name} ({len(ann.departments)} departments)")

    results = run_full_evaluation(parse_pdf, gold_dir, pdf_dir)
    print_eval_report(results)
