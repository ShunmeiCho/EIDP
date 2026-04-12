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
    finally:
        session.close()


@app.command()
def discover_urls(
    seed_csv: Path = typer.Option(Path("data/url-discovery/discovered-urls-50.csv"), help="Seed URL CSV"),
    verify: bool = typer.Option(False, help="Verify URLs via HTTP HEAD"),
    batch_size: int = typer.Option(50, help="Batch size for verification"),
) -> None:
    """Discover and register school URLs (Step 7)."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.url_discovery import (
        get_discovery_stats,
        import_seed_urls,
        infer_corporation_urls,
        verify_urls_sync,
    )

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
        needs_key = {"brave", "google", "serper"}
        has_key = settings.brave_api_key or settings.google_api_key or settings.serper_api_key
        if settings.search_provider == "duckduckgo" or has_key:
            from eidp.scraper.url_discovery import search_and_discover
            typer.echo(f"Running web search ({settings.search_provider})...")
            search_stats = search_and_discover(session, batch_size=batch_size)
            session.commit()
            typer.echo(f"Web search: {search_stats}")
        elif settings.search_provider in needs_key and not has_key:
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
def db_info() -> None:
    """Show database statistics."""
    from sqlalchemy import func

    from eidp.db.models import Department, DepartmentYearly, School, SchoolAlias, SchoolYearStatus, SupportRecipient
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
def eval_pdf(
    gold_dir: Path = typer.Option(Path("data/gold-set"), help="Gold annotation directory"),
    pdf_dir: Path = typer.Option(Path("data/sample-pdfs"), help="Sample PDF directory"),
) -> None:
    """Evaluate PDF parser against gold set (Step 5 / Step 9)."""
    from eidp.pdf.eval_harness import load_all_gold_annotations, print_eval_report

    annotations = load_all_gold_annotations(gold_dir)
    typer.echo(f"Gold set: {len(annotations)} annotations loaded")
    for key, ann in annotations.items():
        typer.echo(f"  {key}: {ann.school_name} ({len(ann.departments)} departments)")

    typer.echo("\nTo run evaluation, implement a parser and call:")
    typer.echo("  from eidp.pdf.eval_harness import run_full_evaluation, print_eval_report")
    typer.echo("  results = run_full_evaluation(your_parse_fn, gold_dir, pdf_dir)")
    typer.echo("  print_eval_report(results)")


if __name__ == "__main__":
    app()
