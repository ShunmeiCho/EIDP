"""EIDP CLI entrypoint."""

from pathlib import Path

import typer

app = typer.Typer(name="eidp", help="Education Institution Data Pipeline")


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
    from eidp.matcher.school_matcher import apply_matches, match_schools
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        report = match_schools(session, data_dir)

        typer.echo(f"\nMatch Results:")
        typer.echo(f"  Exact:        {len(report.exact)}")
        typer.echo(f"  NFKC:         {len(report.nfkc)}")
        typer.echo(f"  Pref+Partial: {len(report.pref_partial)}")
        typer.echo(f"  Unmatched:    {len(report.unmatched)}")
        typer.echo(f"  Match rate:   {report.total_matched / report.total * 100:.1f}%")

        if not dry_run:
            stats = apply_matches(session, report)
            session.commit()
            typer.echo(f"\nApplied:")
            typer.echo(f"  Codes assigned: {stats['codes_assigned']}")
            typer.echo(f"  Aliases created: {stats['aliases_created']}")
            typer.echo(f"  Conflicts:      {stats['conflicts']}")
        else:
            typer.echo("\n(dry run — no DB writes)")
            session.rollback()

        if report.unmatched:
            typer.echo(f"\nTop unmatched corporations:")
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
    from eidp.matcher.reconciler import apply_reconciliation, reconcile as do_reconcile

    session = SessionLocal()
    try:
        report = do_reconcile(session, data_dir)

        typer.echo(f"\nReconciliation Results:")
        typer.echo(f"  Already resolved:   {report.already_resolved}")
        typer.echo(f"  Auto-assigned:      {len(report.auto_assigned)}")
        typer.echo(f"  Excluded:           {len(report.excluded)}")
        typer.echo(f"  Needs manual:       {len(report.needs_manual)}")
        typer.echo(f"  Missing from DB:    {len(report.missing_from_db)}")

        if not dry_run:
            stats = apply_reconciliation(session, report)
            session.commit()
            typer.echo(f"\nApplied:")
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
        typer.echo(f"\nIdentity Verification:")
        for k, v in result.items():
            typer.echo(f"  {k}: {v}")
        if result["pass"]:
            typer.echo("\nGATE: PASS")
        else:
            typer.echo(f"\nGATE: FAIL (truly_unresolved={result['truly_unresolved']}, target_gap={result['target_list_gap']})")
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
            typer.echo(f"ERROR: Unknown search_provider '{settings.search_provider}'. Valid: {list(provider_key_map.keys())}")
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
        typer.echo(f"\nURL Discovery Stats:")
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
) -> None:
    """Discover and download PDFs from school disclosure pages (Step 8)."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    storage_dir.mkdir(parents=True, exist_ok=True)

    methods = [m.strip() for m in discovery_method.split(",") if m.strip()] or None

    session = SessionLocal()
    try:
        stats = run_pdf_discovery(
            session, storage_dir,
            batch_size=batch_size, rate_limit=rate_limit,
            discovery_methods=methods,
        )
        session.commit()
        typer.echo(f"\nPDF Discovery Results:")
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
) -> None:
    """Parse downloaded PDFs and write data to database (Step 9 -> DB)."""
    try:
        from eidp.pipeline.ingest import run_ingestion
    except ImportError as e:
        typer.echo(f"Missing dependency: {e}. Run: uv sync --extra pdf")
        raise typer.Exit(1)

    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        stats = run_ingestion(session, batch_size=batch_size, document_ids=document_id)
        session.commit()
        typer.echo(f"\nIngestion Results:")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def db_info() -> None:
    """Show database statistics."""
    from sqlalchemy import func

    from eidp.db.models import CrawlJob, Department, DepartmentYearly, Document, School, SchoolAlias, SchoolSite, SchoolYearStatus, SupportRecipient
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        typer.echo(f"Schools:            {session.query(func.count(School.id)).scalar()}")
        typer.echo(f"  with school_code: {session.query(func.count(School.id)).filter(School.school_code.isnot(None)).scalar()}")
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
        typer.echo(f"\nReview Items Populated:")
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
    from eidp.scraper.url_discovery import verify_urls_sync, get_discovery_stats

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
        typer.echo(f"\n=== Summary ===")
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
        typer.echo(f"\nFirecrawl Discovery:")
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
    """Launch the Streamlit review UI for school identity resolution (Step 6)."""
    import subprocess
    import sys

    app_path = Path(__file__).parent / "review" / "app.py"
    typer.echo(f"Launching review UI on http://localhost:{port}")
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
    fiscal_year: int = typer.Option(2026, help="Fiscal year column to add/update"),
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
        stats = export_competition_workbook(
            session, template, output, fiscal_year, gap_report
        )
        typer.echo(f"Exported to: {output}")
        typer.echo(f"  matched:        {stats['matched']}")
        typer.echo(f"  unmatched:      {stats['unmatched']}")
        typer.echo(f"  cells_written:  {stats['cells_written']}")
        if stats["unmatched"]:
            typer.echo(f"  gap report:    {gap_report}")
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


if __name__ == "__main__":
    app()
