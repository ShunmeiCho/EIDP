"""EIDP CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from eidp.reports.coverage import PrefectureCoverage

app = typer.Typer(name="eidp", help="Education Institution Data Pipeline")
report_app = typer.Typer(name="report", help="Acceptance-criteria reports")
app.add_typer(report_app, name="report")


@app.command()
def import_excel(
    excel_path: Path = typer.Argument(..., help="Path to master Excel file"),
) -> None:
    """Import master Excel into database."""
    from eidp.db.session import SessionLocal
    from eidp.excel.importer import import_all

    session = SessionLocal()
    try:
        results = import_all(excel_path, session)
        session.commit()
        for sheet, stats in results.items():
            typer.echo(f"  {sheet}: {stats}")
        typer.echo("Import complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def match_mext(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
    dry_run: bool = typer.Option(False, help="Show matches without writing to DB"),
) -> None:
    """Match schools against MEXT school codes (Step 3)."""
    from eidp.db.session import SessionLocal
    from eidp.matcher.school_matcher import apply_matches, match_schools

    session = SessionLocal()
    try:
        report = match_schools(session, data_dir)

        typer.echo("\nMatch Results:")
        typer.echo(f"  Exact:        {len(report.exact)}")
        typer.echo(f"  NFKC:         {len(report.nfkc)}")
        typer.echo(f"  Pref+Partial: {len(report.pref_partial)}")
        typer.echo(f"  Unmatched:    {len(report.unmatched)}")
        typer.echo(f"  Match rate:   {report.total_matched / report.total * 100:.1f}%")

        if not dry_run:
            stats = apply_matches(session, report)
            session.commit()
            typer.echo("\nApplied:")
            typer.echo(f"  Codes assigned: {stats['codes_assigned']}")
            typer.echo(f"  Aliases created: {stats['aliases_created']}")
            typer.echo(f"  Conflicts:      {stats['conflicts']}")
        else:
            typer.echo("\n(dry run — no DB writes)")
            session.rollback()

        if report.unmatched:
            typer.echo("\nTop unmatched corporations:")
            from collections import Counter
            corps = Counter(r.corporation_name for r in report.unmatched)
            for corp, count in corps.most_common(10):
                typer.echo(f"  {corp}: {count}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def reconcile(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
    dry_run: bool = typer.Option(False, help="Show results without writing to DB"),
) -> None:
    """Reconcile unmatched schools against target institution list (Step 4)."""
    from eidp.db.session import SessionLocal
    from eidp.matcher.reconciler import apply_reconciliation
    from eidp.matcher.reconciler import reconcile as do_reconcile

    session = SessionLocal()
    try:
        report = do_reconcile(session, data_dir)

        typer.echo("\nReconciliation Results:")
        typer.echo(f"  Already resolved:   {report.already_resolved}")
        typer.echo(f"  Auto-assigned:      {len(report.auto_assigned)}")
        typer.echo(f"  Excluded:           {len(report.excluded)}")
        typer.echo(f"  Needs manual:       {len(report.needs_manual)}")
        typer.echo(f"  Missing from DB:    {len(report.missing_from_db)}")

        if not dry_run:
            stats = apply_reconciliation(session, report)
            session.commit()
            typer.echo("\nApplied:")
            typer.echo(f"  Codes assigned: {stats['codes_assigned']}")
            typer.echo(f"  Aliases created: {stats['aliases_created']}")
        else:
            typer.echo("\n(dry run)")
            session.rollback()

        if report.needs_manual:
            typer.echo(f"\nManual resolution needed ({len(report.needs_manual)}):")
            from collections import Counter
            corps = Counter(c.corporation_name for c in report.needs_manual)
            for corp, count in corps.most_common(10):
                typer.echo(f"  {corp}: {count}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
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


@app.command()
def discover_urls(
    seed_csv: Path = typer.Option(Path("data/url-discovery/discovered-urls-50.csv"), help="Seed URL CSV"),
    verify: bool = typer.Option(False, help="Verify URLs via HTTP HEAD"),
    batch_size: int = typer.Option(50, help="Batch size for verification"),
) -> None:
    """Discover and register school URLs (Step 7)."""
    try:
        from eidp.scraper.url_discovery import (
            get_discovery_stats,
            import_seed_urls,
            infer_corporation_urls,
            verify_urls_sync,
        )
    except ImportError as e:
        typer.echo(f"Missing dependency: {e}. Run: uv sync --extra scraper")
        raise typer.Exit(1)

    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        # Phase 1: Import seed URLs
        if seed_csv.exists():
            seed_stats = import_seed_urls(session, seed_csv)
            typer.echo(f"Seed import: {seed_stats}")

        # Phase 2: Corporation pattern inference
        corp_stats = infer_corporation_urls(session)
        typer.echo(f"Corporation inference: {corp_stats}")

        session.commit()

        # Phase 2.5: Web search discovery
        from eidp.config import settings
        provider_key_map = {
            "brave": bool(settings.brave_api_key),
            "google": bool(settings.google_api_key and settings.google_cx),
            "serper": bool(settings.serper_api_key),
            "duckduckgo": True,  # no key needed
        }
        if settings.search_provider not in provider_key_map:
            typer.echo(
                f"ERROR: Unknown search_provider '{settings.search_provider}'. "
                f"Valid: {list(provider_key_map.keys())}"
            )
            raise typer.Exit(1)
        provider_has_key = provider_key_map[settings.search_provider]
        if provider_has_key:
            from eidp.scraper.url_discovery import search_and_discover
            typer.echo(f"Running web search ({settings.search_provider})...")
            search_stats = search_and_discover(session, batch_size=batch_size)
            session.commit()
            typer.echo(f"Web search: {search_stats}")
        else:
            typer.echo(f"(No API key for {settings.search_provider}, skipping web search)")

        # Phase 3: HTTP verification (optional)
        if verify:
            typer.echo(f"Verifying URLs (batch={batch_size})...")
            verify_stats = verify_urls_sync(session, batch_size=batch_size)
            session.commit()
            typer.echo(f"Verification: {verify_stats}")

        # Report
        stats = get_discovery_stats(session)
        typer.echo("\nURL Discovery Stats:")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def discover_pdfs(
    storage_dir: Path = typer.Option(Path("data/pdfs"), help="PDF storage directory"),
    batch_size: int = typer.Option(50, help="Number of sites to crawl"),
    rate_limit: float = typer.Option(1.0, help="Seconds between requests"),
    discovery_method: str = typer.Option(
        "", help="Comma-separated list of school_site.discovery_method values to "
                 "restrict crawling to. E.g. 'prefecture_aggregator' to crawl only "
                 "prefecture-declared URLs. Empty = all methods (legacy behavior)."
    ),
    school_id: list[int] = typer.Option(
        None, help="Restrict discovery to specific school.id values (repeatable). "
                   "Used for targeted gap-filling, e.g. 滋慶 group."
    ),
    evidence_log: Path = typer.Option(
        Path("output/discovery_rejections.jsonl"),
        help="JSONL file capturing every rejected PDF candidate (URL, score, "
             "anchor, reason). Append-only. Use empty string to disable.",
    ),
) -> None:
    """Discover and download PDFs from school disclosure pages (Step 8)."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    storage_dir.mkdir(parents=True, exist_ok=True)

    methods = [m.strip() for m in discovery_method.split(",") if m.strip()] or None
    school_filter = list(school_id) if school_id else None
    evidence_path = evidence_log if str(evidence_log) else None

    session = SessionLocal()
    try:
        stats = run_pdf_discovery(
            session, storage_dir,
            batch_size=batch_size, rate_limit=rate_limit,
            discovery_methods=methods,
            school_ids=school_filter,
            evidence_path=evidence_path,
        )
        session.commit()
        typer.echo("\nPDF Discovery Results:")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def ingest_pdfs(
    batch_size: int = typer.Option(50, help="Number of documents to process"),
    document_id: list[int] | None = typer.Option(
        None,
        "--document-id",
        help="Specific document id to ingest. Repeat to target known PDFs.",
    ),
    evidence_log: Path = typer.Option(
        Path("output/ingest_rejections.jsonl"),
        help="JSONL file capturing every rejected document (doc_id, reason, "
             "parsed_school_name, etc). Append-only. Use empty string to disable.",
    ),
) -> None:
    """Parse downloaded PDFs and write data to database (Step 9 -> DB)."""
    try:
        from eidp.pipeline.ingest import run_ingestion
    except ImportError as e:
        typer.echo(f"Missing dependency: {e}. Run: uv sync --extra pdf")
        raise typer.Exit(1)

    from eidp.db.session import SessionLocal

    evidence_path = evidence_log if str(evidence_log) else None

    session = SessionLocal()
    try:
        stats = run_ingestion(
            session,
            batch_size=batch_size,
            document_ids=document_id,
            evidence_path=evidence_path,
        )
        session.commit()
        typer.echo("\nIngestion Results:")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def db_bootstrap(
    sqlite: bool = typer.Option(False, "--sqlite", help="Bootstrap a fresh SQLite database (Windows path)."),
) -> None:
    """Bootstrap a database without running PG-only alembic migrations.

    For SQLite (Windows business-user deployment) this builds the schema via
    ORM metadata + adds the null-safe department index + applies PRAGMAs +
    stamps alembic head. Idempotent and safe to re-run.
    """
    if not sqlite:
        typer.echo("Pass --sqlite to bootstrap a SQLite database. PostgreSQL setups should run `alembic upgrade head`.")
        raise typer.Exit(code=2)

    from eidp.db.session import engine
    from eidp.db.sqlite_bootstrap import bootstrap_sqlite, is_sqlite

    if not is_sqlite(engine):
        typer.echo(
            f"ERROR: --sqlite requires EIDP_DATABASE_URL to point at SQLite, "
            f"current dialect={engine.dialect.name!r}, url={engine.url!r}"
        )
        raise typer.Exit(code=1)

    bootstrap_sqlite(engine)
    typer.echo(f"SQLite bootstrap complete: {engine.url}")


@app.command()
def rebuild_school_year_tasks(
    fiscal_year: int | None = typer.Option(
        None,
        help="Target fiscal year. Defaults to settings.target_fiscal_year.",
    ),
    school_type: str | None = typer.Option(
        "専門学校",
        help="School type to rebuild. Use empty string to rebuild every active school.",
    ),
) -> None:
    """Rebuild the operator-facing school x target-year task table."""
    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.pipeline.school_fiscal_year_status import rebuild_school_fiscal_year_status

    target_fy = fiscal_year or settings.target_fiscal_year
    normalized_school_type = school_type.strip() if school_type else None
    if not normalized_school_type:
        normalized_school_type = None

    session = SessionLocal()
    try:
        stats = rebuild_school_fiscal_year_status(
            session,
            fiscal_year=target_fy,
            school_type=normalized_school_type,
        )
        session.commit()
        typer.echo(
            "School year tasks rebuilt: "
            f"fiscal_year={target_fy} "
            f"school_type={normalized_school_type or 'all'} "
            f"rebuilt={stats.rebuilt} "
            f"excel_ready={stats.excel_ready}"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def prefecture_aggregate(
    pref: str = typer.Option(
        ...,
        help=(
            "Comma-separated prefecture keys "
            "(e.g. 'tokyo,kanagawa,saitama,miyagi'). "
            "Use 'all' for every registered parser."
        ),
    ),
    artifact_dir: Path = typer.Option(
        Path("data/prefecture-aggregators/artifacts"),
        help="Directory holding {pref}.pdf, {pref}.xlsx, or {pref}.html artifacts.",
    ),
    output_dir: Path = typer.Option(
        Path("output/pref-aggregator"),
        help="Where to write the per-prefecture writer-plan JSONs.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Persist the writer-plan via SchoolSite inserts/upgrades. Required for any DB write.",
    ),
) -> None:
    """Run the prefecture aggregator: parse → match → writer-plan, optionally apply.

    DB safety contract (Sprint 8.3.1): ``--apply`` is the *single* switch
    that allows a write. Without ``--apply`` the command runs as a strict
    dry-run — JSON writer-plan is emitted to ``output_dir`` and the
    session is rolled back at the end. The previous ``--no-dry-run`` flag
    was removed because it allowed a write without ``--apply`` being
    explicitly stated.
    """
    import json

    from eidp.db.session import SessionLocal
    from eidp.scraper.prefecture_aggregator import (
        PARSERS,
        aggregate,
        apply_writer_plan,
    )

    dry_run = not apply

    requested = [p.strip() for p in pref.split(",") if p.strip()]
    if requested == ["all"]:
        requested = sorted(PARSERS.keys())

    output_dir.mkdir(parents=True, exist_ok=True)

    session = SessionLocal()
    try:
        for p in requested:
            artifact = next(
                (
                    candidate
                    for candidate in (
                        artifact_dir / f"{p}.pdf",
                        artifact_dir / f"{p}.xlsx",
                        artifact_dir / f"{p}.html",
                    )
                    if candidate.exists()
                ),
                None,
            )
            if artifact is None:
                typer.echo(f"[skip] {p}: artifact missing at {artifact_dir / f'{p}.pdf'}")
                continue

            report = aggregate(session, p, artifact)
            out_path = output_dir / f"{p}.json"
            out_path.write_text(
                json.dumps(report.__dict__, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            typer.echo(
                f"[{p}] extracted={report.extracted_total} "
                f"matched={report.db_matched} unmatched={report.db_unmatched} "
                f"actions={report.action_distribution} → {out_path}"
            )

            if not dry_run:
                stats = apply_writer_plan(session, report)
                typer.echo(f"[{p}] applied: {stats}")

        if not dry_run:
            session.commit()
            typer.echo("All applies committed.")
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def audit_flush(
    jsonl_path: Path = typer.Option(
        Path("data/audit/manual-actions.jsonl"),
        help="Where to append JSONL audit entries.",
    ),
) -> None:
    """Flush pending manual_action_log rows to the JSONL outbox.

    Idempotent and dedup-safe: if a row's action_id is already present in the
    file (e.g. a prior flush wrote the line but crashed before stamping the
    column), the row is just stamped, not re-written. Failures stash a short
    reason on jsonl_export_error and remain pending for the next run.
    """
    from eidp.db.audit_outbox import flush_audit_outbox
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        stats = flush_audit_outbox(session, jsonl_path=jsonl_path)
        typer.echo(
            f"Audit flush: exported={stats['exported']} "
            f"already_present={stats['already_present']} "
            f"failed={stats['failed']} → {jsonl_path}"
        )
    finally:
        session.close()


@app.command()
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
    finally:
        session.close()


@app.command()
def populate_reviews(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
) -> None:
    """Populate review_item table with unresolved schools for manual review (Step 6)."""
    from eidp.db.session import SessionLocal
    from eidp.review.populate import populate_review_items

    session = SessionLocal()
    try:
        stats = populate_review_items(session, data_dir)
        session.commit()
        typer.echo("\nReview Items Populated:")
        typer.echo(f"  Created:          {stats['created']}")
        typer.echo(f"  Skipped existing: {stats['skipped_existing']}")
        typer.echo(f"  Skipped excluded: {stats['skipped_excluded']}")
        typer.echo(f"  Total unresolved: {stats['total_unresolved']}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def weekly_update(
    storage_dir: Path = typer.Option(Path("data/pdfs"), help="PDF storage directory"),
    pdf_batch: int = typer.Option(50, help="PDF discovery batch size"),
    ingest_batch: int = typer.Option(50, help="Ingest batch size"),
    export_path: Path = typer.Option(Path("output/weekly-export.xlsx"), help="Export output path"),
) -> None:
    """Run weekly incremental update pipeline (Steps 7-10).

    Idempotent: safe to run multiple times. Skips already-processed items.
    Designed for crontab: 0 2 * * 1 .venv/bin/eidp weekly-update
    """
    from eidp.db.session import SessionLocal
    from eidp.scraper.url_discovery import get_discovery_stats, verify_urls_sync

    session = SessionLocal()
    try:
        typer.echo("=== EIDP Weekly Update ===")

        # Phase 1: Verify unverified URLs
        typer.echo("\n[1/4] Verifying URLs...")
        verify_stats = verify_urls_sync(session, batch_size=200, timeout=10.0)
        session.commit()
        typer.echo(f"  {verify_stats}")

        # Phase 2: PDF Discovery on verified URLs
        typer.echo("\n[2/4] Discovering PDFs...")
        from eidp.scraper.pdf_discovery import run_pdf_discovery
        storage_dir.mkdir(parents=True, exist_ok=True)
        pdf_stats = run_pdf_discovery(session, storage_dir, batch_size=pdf_batch, rate_limit=1.5)
        session.commit()
        typer.echo(f"  {pdf_stats}")

        # Phase 3: Ingest new PDFs
        typer.echo("\n[3/4] Ingesting PDFs...")
        from eidp.pipeline.ingest import run_ingestion
        ingest_stats = run_ingestion(session, batch_size=ingest_batch)
        session.commit()
        typer.echo(f"  {ingest_stats}")

        # Phase 4: Export updated workbook
        typer.echo("\n[4/4] Exporting workbook...")
        from eidp.excel.exporter import export_master_workbook
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_stats = export_master_workbook(session, export_path)
        typer.echo(f"  {export_stats}")

        # Summary
        coverage = get_discovery_stats(session)
        typer.echo("\n=== Summary ===")
        typer.echo(f"  Verified disclosure: {coverage['verified_disclosure']} ({coverage['coverage_verified']})")
        typer.echo(f"  Documents ingested: {ingest_stats.get('processed', 0)}")
        typer.echo(f"  Export: {export_path}")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def firecrawl_discover(
    batch_size: int = typer.Option(30, help="Number of corporations to process"),
) -> None:
    """Discover school URLs from corporation root domains using Firecrawl (one-time)."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.firecrawl_discovery import run_firecrawl_discovery

    session = SessionLocal()
    try:
        stats = run_firecrawl_discovery(session, batch_size=batch_size)
        session.commit()
        typer.echo("\nFirecrawl Discovery:")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def review_ui(
    port: int = typer.Option(8501, help="Port for the Streamlit server"),
) -> None:
    """Launch the Streamlit operator/review UI."""
    import subprocess
    import sys

    app_path = Path(__file__).parent / "review" / "app.py"
    typer.echo(f"Launching review UI on http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


@app.command()
def operator_ui(
    port: int = typer.Option(8501, help="Port for the Streamlit server"),
) -> None:
    """Launch the Streamlit operator console for URL補足, exports, and review."""
    import subprocess
    import sys

    app_path = Path(__file__).parent / "review" / "app.py"
    typer.echo(f"Launching operator UI on http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


@app.command()
def export_excel(
    output: Path = typer.Option(Path("output/専門学校無償化情報公開まとめ.xlsx"), help="Output Excel file path"),
) -> None:
    """Export master Excel workbook from database (Step 10)."""
    from eidp.db.session import SessionLocal
    from eidp.excel.exporter import export_master_workbook

    session = SessionLocal()
    try:
        results = export_master_workbook(session, output)
        typer.echo(f"Exported to: {output}")
        for sheet, count in results.items():
            typer.echo(f"  {sheet}: {count} rows")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
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
        stats = export_competition_workbook(
            session, template, output, fy_arg, gap_report
        )
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


@app.command()
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
    typer.echo(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*8}")
    for sheet, stats in results.items():
        diff_str = f"{stats['diff']:+d}" if stats["diff"] != 0 else "0"
        typer.echo(f"  {sheet:<16} {stats['exported']:>10} {stats['original']:>10} {diff_str:>8}")


@app.command()
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


@report_app.command("coverage")
def report_coverage(
    school_type: str = typer.Option("専門学校", help="Filter by school_type (or 'all')"),
    fiscal_year: int | None = typer.Option(None, help="Fiscal year (defaults to current FY)"),
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


if __name__ == "__main__":
    app()
