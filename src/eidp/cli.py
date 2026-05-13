"""EIDP CLI entrypoint."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NoReturn, cast

import typer
from sqlalchemy.exc import SQLAlchemyError

from eidp.cli_discovery import register_discovery_commands
from eidp.cli_reports import report_app


def _configure_utf8_stdio(stdout: Any = sys.stdout, stderr: Any = sys.stderr) -> None:
    """Keep Windows console code pages from crashing Japanese CLI logs."""

    for stream in (stdout, stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


_configure_utf8_stdio()

app = typer.Typer(name="eidp", help="Education Institution Data Pipeline")
app.add_typer(report_app, name="report")
register_discovery_commands(app)


@contextmanager
def _require_app_lock(owner: str) -> Iterator[None]:
    """Acquire the shared single-user DB lock for CLI write commands."""
    from eidp.config import settings
    from eidp.db.locking import LockBusyError, acquire_lock

    lock_path = Path(settings.data_dir) / ".lock"
    try:
        with acquire_lock(lock_path, owner=owner):
            yield
    except LockBusyError as exc:
        typer.echo(f"ERROR: another EIDP process is running: {exc}", err=True)
        raise typer.Exit(5) from exc


def _echo_excel_export_results(output: Path, results: dict[str, int]) -> None:
    """Print workbook sheet counts separately from export quality counters."""
    typer.echo(f"Exported to: {output}")
    sheet_counts = {name: count for name, count in results.items() if not name.startswith("quality_")}
    quality_warnings = {
        name.removeprefix("quality_"): count
        for name, count in results.items()
        if name.startswith("quality_")
    }
    for sheet, count in sheet_counts.items():
        typer.echo(f"  {sheet}: {count} rows")
    nonzero_quality = {name: count for name, count in quality_warnings.items() if count}
    if nonzero_quality:
        typer.echo("Quality warnings:")
        for name, count in nonzero_quality.items():
            typer.echo(f"  {name}: {count}")


def _echo_import_excel_results(results: dict[str, dict[str, int]]) -> None:
    """Print import stats and make silent-row-drop counters visible."""
    for sheet, stats in results.items():
        typer.echo(f"  {sheet}: {stats}")
        invalid_year = int(stats.get("invalid_year") or 0)
        if invalid_year:
            typer.echo(
                f"WARNING: {sheet} で想定外の年度の行を {invalid_year} 件スキップしました。",
                err=True,
            )


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


@app.command()
def import_excel(
    excel_path: Path = typer.Argument(..., help="Path to master Excel file"),
) -> None:
    """Import master Excel into database."""
    with _require_app_lock("cli_import_excel"):
        from eidp.db.session import SessionLocal
        from eidp.excel.importer import import_all

        session = SessionLocal()
        try:
            results = import_all(excel_path, session)
            session.commit()
            _echo_import_excel_results(results)
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

    with _require_app_lock("cli_match_mext"):
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

    with _require_app_lock("cli_reconcile"):
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

    with _require_app_lock("cli_discover_urls"):
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
def crawl_school_urls(
    limit: int = typer.Option(25, "--limit", min=1, help="Maximum URL-missing schools to process."),
    school_id: int | None = typer.Option(None, "--school-id", help="Restrict to one school id."),
    prefecture: str | None = typer.Option(None, "--prefecture", help="Restrict to one prefecture name."),
    fetch_mode: str = typer.Option(
        "static",
        "--fetch-mode",
        help="Scrapling fetch mode: static, dynamic, or stealthy.",
    ),
    evidence_log: Path = typer.Option(
        Path("output/school_url_crawl_evidence.jsonl"),
        "--evidence-log",
        help="Append-only JSONL evidence output.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Dry-run fetches network; DB writes are rolled back.",
    ),
) -> None:
    """Find school website URLs for schools still missing SchoolSite rows (v104)."""
    if fetch_mode not in {"static", "dynamic", "stealthy"}:
        typer.echo("ERROR: --fetch-mode must be one of: static, dynamic, stealthy")
        raise typer.Exit(1)

    from eidp.db.session import SessionLocal
    from eidp.scraper.school_url_pipeline import run_school_url_auto_crawl
    from eidp.scraper.scrapling_fetcher import ScraplingFetchMode

    with _require_app_lock("cli_crawl_school_urls"):
        session = SessionLocal()
        try:
            fetch_mode_value = cast(ScraplingFetchMode, fetch_mode)
            stats = run_school_url_auto_crawl(
                session,
                batch_size=limit,
                school_id=school_id,
                prefecture=prefecture,
                dry_run=dry_run,
                evidence_path=evidence_log,
                fetch_mode=fetch_mode_value,
            )
            if dry_run:
                session.rollback()
            else:
                session.commit()
            typer.echo(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))
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
    request_timeout: float = typer.Option(30.0, help="Per HTTP request timeout in seconds"),
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
    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    storage_dir.mkdir(parents=True, exist_ok=True)

    methods = [m.strip() for m in discovery_method.split(",") if m.strip()] or None
    school_filter = list(school_id) if school_id else None
    evidence_path = evidence_log if str(evidence_log) else None

    with _require_app_lock("cli_discover_pdfs"):
        session = SessionLocal()
        try:
            stats = run_pdf_discovery(
                session, storage_dir,
                batch_size=batch_size, rate_limit=rate_limit, request_timeout=request_timeout,
                discovery_methods=methods,
                school_ids=school_filter,
                evidence_path=evidence_path,
                target_fiscal_year=settings.target_fiscal_year,
                strict_target_fiscal_year=True,
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

    with _require_app_lock("cli_ingest_pdfs"):
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

    with _require_app_lock("cli_db_bootstrap"):
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
    discovery_evidence_log: Path = typer.Option(
        Path("output/discovery_rejections.jsonl"),
        help="PDF discovery evidence JSONL used to mark publication-lag target candidates.",
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

    with _require_app_lock("cli_rebuild_school_year_tasks"):
        session = SessionLocal()
        try:
            stats = rebuild_school_fiscal_year_status(
                session,
                fiscal_year=target_fy,
                school_type=normalized_school_type,
                discovery_evidence_path=discovery_evidence_log,
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
        resolve_prefecture_artifacts,
    )

    dry_run = not apply

    requested = [p.strip() for p in pref.split(",") if p.strip()]
    if requested == ["all"]:
        requested = sorted(PARSERS.keys())

    output_dir.mkdir(parents=True, exist_ok=True)

    with _require_app_lock("cli_prefecture_aggregate"):
        session = SessionLocal()
        try:
            for p in requested:
                artifacts = resolve_prefecture_artifacts(artifact_dir, p)
                if not artifacts:
                    typer.echo(f"[skip] {p}: artifact missing at {artifact_dir / f'{p}.pdf'}")
                    continue

                for artifact in artifacts:
                    report = aggregate(session, p, artifact)
                    suffix = "" if len(artifacts) == 1 else f"__{artifact.stem.removeprefix(p).strip('_') or 'primary'}"
                    out_path = output_dir / f"{p}{suffix}.json"
                    out_path.write_text(
                        json.dumps(report.__dict__, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8",
                    )
                    typer.echo(
                        f"[{p}/{artifact.name}] extracted={report.extracted_total} "
                        f"matched={report.db_matched} unmatched={report.db_unmatched} "
                        f"actions={report.action_distribution} → {out_path}"
                    )

                    if not dry_run:
                        stats = apply_writer_plan(session, report)
                        typer.echo(f"[{p}/{artifact.name}] applied: {stats}")

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

    with _require_app_lock("cli_audit_flush"):
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
    except SQLAlchemyError as exc:
        _exit_database_not_ready_error(exc, output_json=False, command_label="db-info")
    finally:
        session.close()


@app.command()
def populate_reviews(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
) -> None:
    """Populate review_item table with unresolved schools for manual review (Step 6)."""
    from eidp.db.session import SessionLocal
    from eidp.review.populate import populate_review_items

    with _require_app_lock("cli_populate_reviews"):
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
    with _require_app_lock("cli_weekly_update"):
        from eidp.config import settings
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
            pdf_stats = run_pdf_discovery(
                session,
                storage_dir,
                batch_size=pdf_batch,
                rate_limit=1.5,
                target_fiscal_year=settings.target_fiscal_year,
                strict_target_fiscal_year=True,
            )
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

    with _require_app_lock("cli_firecrawl_discover"):
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
        _echo_excel_export_results(output, results)
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


@app.command("seed-discovery-gold-sites")
def seed_discovery_gold_sites(
    gold_set_dir: Path = typer.Option(Path("data/discovery-gold-set"), help="Discovery gold-set directory"),
    apply: bool = typer.Option(False, "--apply", help="Write missing schools and SchoolSite rows to the DB"),
) -> None:
    """Seed discovery gold-set disclosure sites into the configured DB."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.discovery_gold_set import (
        load_discovery_gold_entries,
    )
    from eidp.scraper.discovery_gold_set import (
        seed_discovery_gold_sites as seed_sites,
    )

    with _require_app_lock("cli_seed_discovery_gold_sites"):
        session = SessionLocal()
        try:
            stats = seed_sites(session, load_discovery_gold_entries(gold_set_dir), apply=apply)
            if apply:
                session.commit()
            else:
                session.rollback()
            typer.echo(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    app()
