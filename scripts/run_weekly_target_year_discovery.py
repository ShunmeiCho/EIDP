"""Weekly target-year rediscovery runner.

This is the Windows Task Scheduler-facing production entrypoint for
Sprint 8. It targets schools that have a crawlable school_site but no
current-FY target PDF, then runs:

1. PDF rediscovery for the selected school_site methods.
2. Ingestion only for documents created during this run.
3. A timestamped JSON summary with before/after report snapshots and
   evidence paths.
4. ``data/output/last_run.json`` for the Streamlit operator UI.

Use --dry-run for a read-only plan/snapshot check.

Excel generation is intentionally NOT part of this runner. Operators
generate Excel from the Streamlit preview page after reviewing queued
items.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.config import settings  # noqa: E402
from eidp.db.locking import acquire_lock  # noqa: E402
from eidp.db.models import Document, School, SchoolSite  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402
from eidp.pipeline.ingest import run_ingestion  # noqa: E402
from eidp.pipeline.school_fiscal_year_status import (  # noqa: E402
    rebuild_school_fiscal_year_status,
    school_fiscal_year_status_counts,
)
from eidp.reports.coverage import compute_coverage  # noqa: E402
from eidp.reports.extraction import compute_extraction  # noqa: E402
from eidp.reports.gaps import compute_gaps  # noqa: E402
from eidp.scraper.pdf_discovery import run_pdf_discovery  # noqa: E402

DEFAULT_METHODS = ("prefecture_aggregator",)


@dataclass(frozen=True)
class WeeklyPaths:
    """Filesystem contract for the Windows operator ZIP."""

    app_root: Path
    storage_dir: Path
    output_dir: Path
    last_run_path: Path
    lock_path: Path
    logs_dir: Path


def resolve_weekly_paths(app_root: Path | None = None) -> WeeklyPaths:
    """Resolve runner paths from the app root, never from ambient cwd.

    ``weekly_run.bat`` sets ``EIDP_APP_ROOT`` before launching Python; in
    tests we pass an explicit ``app_root``. All defaults match the
    Windows ZIP layout.
    """
    root = (app_root or settings.app_root).resolve()
    data_dir = root / "data"
    output_dir = data_dir / "output" / "target-year-discovery"
    return WeeklyPaths(
        app_root=root,
        storage_dir=data_dir / "pdfs",
        output_dir=output_dir,
        last_run_path=data_dir / "output" / "last_run.json",
        lock_path=data_dir / ".lock",
        logs_dir=root / "logs",
    )


def write_last_run(
    summary: dict[str, Any],
    last_run_path: Path,
    *,
    status: str,
    error: str | None = None,
) -> Path:
    """Write the small UI-facing last-run status file.

    The timestamped ``*-summary.json`` remains the detailed evidence
    artifact. ``last_run.json`` is intentionally compact so Streamlit can
    show the latest weekly result without scanning the output directory.
    """
    last_run_path.parent.mkdir(parents=True, exist_ok=True)
    new_document_ids = list(summary.get("new_document_ids") or [])
    payload = {
        "status": status,
        "run_id": summary.get("run_id"),
        "started_at": summary.get("started_at"),
        "finished_at": summary.get("finished_at"),
        "dry_run": bool(summary.get("dry_run", False)),
        "current_fy": summary.get("current_fy"),
        "school_type": summary.get("school_type"),
        "methods": summary.get("methods"),
        "selection_mode": summary.get("selection_mode"),
        "stale_school_count": int(summary.get("stale_school_count") or 0),
        "no_crawlable_url_school_count": int(summary.get("no_crawlable_url_school_count") or 0),
        "target_missing_school_count": int(
            summary.get("target_missing_school_count")
            or summary.get("stale_school_count")
            or 0
        ),
        "new_document_count": len(new_document_ids),
        "new_document_ids": new_document_ids,
        "discovery_stats": summary.get("discovery_stats") or {},
        "ingest_stats": summary.get("ingest_stats") or {},
        "summary_path": summary.get("summary_path"),
        "error": error,
    }
    last_run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return last_run_path


def prune_run_logs(logs_dir: Path, *, keep: int = 12) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Keep only the latest ``run-*.log`` files by filename.

    ``weekly_run.bat`` writes one log per run. The operator PC is a
    single-user laptop/desktop, so a simple filename ringbuffer is enough
    and avoids unbounded growth.

    Returns ``(removed, failed)`` where ``failed`` carries (path, reason)
    pairs so the caller can surface stuck files (per CLAUDE.md no-silent-
    failure rule). Common cause on Windows is the file still being held
    open by a viewer; the operator should close it and rerun.
    """
    if keep < 0:
        raise ValueError("keep must be >= 0")
    if not logs_dir.is_dir():
        return [], []
    logs = sorted(p for p in logs_dir.glob("run-*.log") if p.is_file())
    removable = logs if keep == 0 else logs[:-keep]
    removed: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for path in removable:
        try:
            path.unlink()
            removed.append(path)
        except OSError as exc:
            failed.append((path, str(exc)))
    return removed, failed


def select_stale_school_ids(
    session: Session,
    *,
    current_fy: int,
    methods: list[str] | None,
    school_type: str | None = "専門学校",
    limit: int | None = None,
) -> list[int]:
    """Return schools with older ingested target PDFs and no current target.

    The method filter is applied at school_site level so the resulting IDs
    are directly crawlable by the matching `discover-pdfs --discovery-method`
    invocation.
    """
    rows = (
        session.query(Document.school_id, Document.fiscal_year)
        .join(School, School.id == Document.school_id)
        .filter(
            School.status == "active",
            Document.pdf_type == "target",
            Document.ingest_status == "ingested",
        )
    )
    if school_type:
        rows = rows.filter(School.school_type == school_type)

    fys_by_school: dict[int, set[int]] = {}
    for school_id, fiscal_year in rows.all():
        if school_id is None or fiscal_year is None:
            continue
        fys_by_school.setdefault(int(school_id), set()).add(int(fiscal_year))

    stale_ids = [
        school_id
        for school_id, fys in sorted(fys_by_school.items())
        if current_fy not in fys
    ]
    if not stale_ids:
        return []

    site_query = session.query(SchoolSite.school_id).filter(
        SchoolSite.school_id.in_(stale_ids),
        or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None)),
    )
    if methods:
        site_query = site_query.filter(SchoolSite.discovery_method.in_(methods))

    eligible_ids = sorted({int(school_id) for (school_id,) in site_query.all()})
    if limit is not None:
        return eligible_ids[:limit]
    return eligible_ids


def select_target_missing_school_ids(
    session: Session,
    *,
    current_fy: int,
    methods: list[str] | None,
    school_type: str | None = "専門学校",
    limit: int | None = None,
) -> list[int]:
    """Return active schools with a crawlable URL and no current-FY target.

    This is intentionally broader than ``select_stale_school_ids``: in a new
    fiscal-year season the most important schools often have no prior target
    PDF in DB at all, so limiting the weekly runner to stale schools silently
    drops the real acquisition queue.
    """
    current_target_school_ids = (
        session.query(Document.school_id)
        .join(School, School.id == Document.school_id)
        .filter(
            School.status == "active",
            Document.fiscal_year == current_fy,
            Document.pdf_type == "target",
            Document.ingest_status == "ingested",
        )
        .distinct()
    )

    site_query = (
        session.query(SchoolSite.school_id)
        .join(School, School.id == SchoolSite.school_id)
        .filter(
            School.status == "active",
            or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None)),
            ~SchoolSite.school_id.in_(current_target_school_ids),
        )
    )
    if school_type:
        site_query = site_query.filter(School.school_type == school_type)
    if methods:
        site_query = site_query.filter(SchoolSite.discovery_method.in_(methods))

    eligible_ids = sorted({int(school_id) for (school_id,) in site_query.all()})
    if limit is not None:
        return eligible_ids[:limit]
    return eligible_ids


def count_no_crawlable_url_schools(
    session: Session,
    *,
    methods: list[str] | None,
    school_type: str | None = "専門学校",
) -> int:
    """Count active schools the weekly runner cannot crawl yet.

    ``target_missing_school_count`` only includes schools with a crawlable
    SchoolSite. A fresh Windows setup has master schools but no URLs, so this
    count explains why the runner has nothing to crawl until the UI initial
    acquisition flow seeds SchoolSite rows.
    """
    crawlable_ids = session.query(SchoolSite.school_id).filter(
        or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None))
    )
    if methods:
        crawlable_ids = crawlable_ids.filter(SchoolSite.discovery_method.in_(methods))

    q = session.query(func.count(School.id)).filter(
        School.status == "active",
        ~School.id.in_(crawlable_ids.distinct()),
    )
    if school_type:
        q = q.filter(School.school_type == school_type)
    return int(q.scalar() or 0)


def _coverage_snapshot(session: Session, current_fy: int, school_type: str | None) -> dict[str, Any]:
    totals = compute_coverage(session, school_type=school_type, fiscal_year=current_fy).totals
    return {
        "schools_total": totals.schools_total,
        "schools_with_url": totals.schools_with_url,
        "schools_with_any_pdf": totals.schools_with_any_pdf,
        "schools_with_target_pdf_any_fy": totals.schools_with_target_pdf_any_fy,
        "schools_with_target_pdf_current_fy": totals.schools_with_target_pdf_current_fy,
        "schools_with_current_fy_doc": totals.schools_with_current_fy_doc,
        "schools_with_current_fy_extracted": totals.schools_with_current_fy_extracted,
    }


def _snapshot_reports(session: Session, current_fy: int, school_type: str | None) -> dict[str, Any]:
    gaps = compute_gaps(session, "pdf", school_type=school_type, fiscal_year=current_fy)
    extraction = compute_extraction(session, fiscal_year=current_fy)
    return {
        "coverage": _coverage_snapshot(session, current_fy, school_type),
        "pdf_gaps": {
            "total": gaps.total,
            "by_reason": dict(sorted(gaps.by_reason.items())),
        },
        "extraction": {
            "documents_ingested": extraction.documents_ingested,
            "documents_with_yearly_rows": extraction.documents_with_yearly_rows,
            "yearly_rows_total": extraction.yearly_rows_total,
            "yearly_rows_with_capacity": extraction.yearly_rows_with_capacity,
            "yearly_rows_with_enrollment": extraction.yearly_rows_with_enrollment,
            "extraction_rate": extraction.extraction_rate,
        },
        "school_fiscal_year_status": school_fiscal_year_status_counts(
            session,
            fiscal_year=current_fy,
            school_type=school_type,
        ),
    }


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    coverage_before = before["coverage"]
    coverage_after = after["coverage"]
    extraction_before = before["extraction"]
    extraction_after = after["extraction"]
    gap_before = before["pdf_gaps"]["by_reason"]
    gap_after = after["pdf_gaps"]["by_reason"]
    gap_reasons = sorted(set(gap_before) | set(gap_after))

    return {
        "coverage": {
            key: coverage_after[key] - coverage_before[key]
            for key in coverage_after
            if isinstance(coverage_after[key], int)
        },
        "extraction": {
            key: extraction_after[key] - extraction_before[key]
            for key in extraction_after
            if isinstance(extraction_after[key], int)
        },
        "pdf_gap_by_reason": {
            reason: gap_after.get(reason, 0) - gap_before.get(reason, 0)
            for reason in gap_reasons
        },
    }


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def run_weekly(
    *,
    current_fy: int,
    methods: list[str] | None,
    school_type: str | None,
    storage_dir: Path,
    output_dir: Path,
    batch_size: int,
    rate_limit: float,
    ingest_batch_size: int,
    limit: int | None,
    dry_run: bool,
    lock_path: Path | None = None,
    last_run_path: Path | None = None,
    stale_only: bool = False,
) -> dict[str, Any]:
    """Public entry. Acquires the shared UI lock when ``lock_path`` is
    provided, then delegates to ``_run_weekly_inner``. Splitting the
    body removes the parameter-sprawl recursion the prior shape used to
    re-take the lock and made pdb traces confusing."""
    inner_kwargs: dict[str, Any] = dict(
        current_fy=current_fy,
        methods=methods,
        school_type=school_type,
        storage_dir=storage_dir,
        output_dir=output_dir,
        batch_size=batch_size,
        rate_limit=rate_limit,
        ingest_batch_size=ingest_batch_size,
        limit=limit,
        dry_run=dry_run,
        last_run_path=last_run_path,
        stale_only=stale_only,
    )
    if lock_path is None:
        return _run_weekly_inner(**inner_kwargs)
    with acquire_lock(lock_path, owner="weekly_runner"):
        return _run_weekly_inner(**inner_kwargs)


def _run_weekly_inner(
    *,
    current_fy: int,
    methods: list[str] | None,
    school_type: str | None,
    storage_dir: Path,
    output_dir: Path,
    batch_size: int,
    rate_limit: float,
    ingest_batch_size: int,
    limit: int | None,
    dry_run: bool,
    last_run_path: Path | None,
    stale_only: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    run_id = _timestamp()
    discovery_evidence = output_dir / f"{run_id}-discovery-rejections.jsonl"
    ingest_evidence = output_dir / f"{run_id}-ingest-rejections.jsonl"
    summary_path = output_dir / f"{run_id}-summary.json"

    session = SessionLocal()
    try:
        if stale_only:
            selected_school_ids = select_stale_school_ids(
                session,
                current_fy=current_fy,
                methods=methods,
                school_type=school_type,
                limit=limit,
            )
            selection_mode = "stale_only"
        else:
            selected_school_ids = select_target_missing_school_ids(
                session,
                current_fy=current_fy,
                methods=methods,
                school_type=school_type,
                limit=limit,
            )
            selection_mode = "target_missing"
        stale_reference_ids = set(
            select_stale_school_ids(
                session,
                current_fy=current_fy,
                methods=methods,
                school_type=school_type,
                limit=None,
            )
        )
        stale_school_count = len(set(selected_school_ids) & stale_reference_ids)
        no_crawlable_url_school_count = count_no_crawlable_url_schools(
            session,
            methods=methods,
            school_type=school_type,
        )
        before = _snapshot_reports(session, current_fy, school_type)

        max_doc_id_before = session.query(func.max(Document.id)).scalar() or 0
        discovery_stats: dict[str, int] = {}
        ingest_stats: dict[str, int] = {}
        status_stats: dict[str, int] = {}
        new_document_ids: list[int] = []

        if dry_run or not selected_school_ids:
            session.rollback()
        else:
            effective_batch_size = max(batch_size, len(selected_school_ids))
            discovery_stats = run_pdf_discovery(
                session,
                storage_dir=storage_dir,
                batch_size=effective_batch_size,
                rate_limit=rate_limit,
                discovery_methods=methods,
                school_ids=selected_school_ids,
                evidence_path=discovery_evidence,
                target_fiscal_year=current_fy,
                strict_target_fiscal_year=True,
            )
            session.commit()

            new_document_ids = [
                int(doc_id)
                for (doc_id,) in (
                    session.query(Document.id)
                    .filter(Document.id > max_doc_id_before)
                    .order_by(Document.id)
                    .all()
                )
            ]
            if new_document_ids:
                ingest_stats = run_ingestion(
                    session,
                    batch_size=max(ingest_batch_size, len(new_document_ids)),
                    document_ids=new_document_ids,
                    evidence_path=ingest_evidence,
                )
                session.commit()
            rebuilt = rebuild_school_fiscal_year_status(
                session,
                fiscal_year=current_fy,
                school_type=school_type,
            )
            status_stats = {
                "rebuilt": rebuilt.rebuilt,
                "excel_ready": rebuilt.excel_ready,
            }
            session.commit()

        after = _snapshot_reports(session, current_fy, school_type)
        summary = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "dry_run": dry_run,
            "current_fy": current_fy,
            "school_type": school_type,
            "methods": methods,
            "selection_mode": selection_mode,
            "stale_school_count": stale_school_count,
            "no_crawlable_url_school_count": no_crawlable_url_school_count,
            "target_missing_school_count": len(selected_school_ids),
            "school_ids": selected_school_ids,
            "new_document_ids": new_document_ids,
            "discovery_stats": discovery_stats,
            "ingest_stats": ingest_stats,
            "school_fiscal_year_status_stats": status_stats,
            "before": before,
            "after": after,
            "delta": _delta(before, after),
            "evidence": {
                "discovery_rejections": str(discovery_evidence),
                "ingest_rejections": str(ingest_evidence),
            },
            "summary_path": str(summary_path),
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if last_run_path is not None:
            write_last_run(summary, last_run_path, status="success")
        return summary
    except Exception as exc:
        session.rollback()
        if last_run_path is not None:
            failure_summary = {
                "run_id": run_id,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "dry_run": dry_run,
                "current_fy": current_fy,
                "school_type": school_type,
                "methods": methods,
                "stale_school_count": 0,
                "no_crawlable_url_school_count": 0,
                "target_missing_school_count": 0,
                "new_document_ids": [],
                "discovery_stats": {},
                "ingest_stats": {},
                "summary_path": str(summary_path),
            }
            write_last_run(
                failure_summary,
                last_run_path,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
            )
        raise
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    paths = resolve_weekly_paths()
    parser.add_argument("--current-fy", type=int, default=settings.target_fiscal_year)
    parser.add_argument("--methods", nargs="+", default=list(DEFAULT_METHODS))
    parser.add_argument("--school-type", default="all")
    parser.add_argument("--storage-dir", type=Path, default=paths.storage_dir)
    parser.add_argument("--output-dir", type=Path, default=paths.output_dir)
    parser.add_argument("--last-run-path", type=Path, default=paths.last_run_path)
    parser.add_argument("--lock-path", type=Path, default=paths.lock_path)
    parser.add_argument("--logs-dir", type=Path, default=paths.logs_dir)
    parser.add_argument("--keep-logs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--rate-limit", type=float, default=1.5)
    parser.add_argument("--ingest-batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Legacy mode: crawl only schools with an older ingested target PDF.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_weekly(
        current_fy=args.current_fy,
        methods=args.methods,
        school_type=None if args.school_type == "all" else args.school_type,
        storage_dir=args.storage_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
        ingest_batch_size=args.ingest_batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        lock_path=None if args.no_lock else args.lock_path,
        last_run_path=args.last_run_path,
        stale_only=args.stale_only,
    )
    # Sprint 8.7: prune BEFORE the final print so a closed-pipe error on
    # stdout doesn't leave the ringbuffer unbounded.
    _, prune_failures = prune_run_logs(args.logs_dir, keep=args.keep_logs)
    payload = {
        "summary_path": summary["summary_path"],
        "last_run_path": str(args.last_run_path),
        "dry_run": summary["dry_run"],
        "selection_mode": summary["selection_mode"],
        "stale_school_count": summary["stale_school_count"],
        "no_crawlable_url_school_count": summary["no_crawlable_url_school_count"],
        "target_missing_school_count": summary["target_missing_school_count"],
        "new_document_ids": summary["new_document_ids"],
        "discovery_stats": summary["discovery_stats"],
        "ingest_stats": summary["ingest_stats"],
        "coverage_delta": summary["delta"]["coverage"],
    }
    if prune_failures:
        # Surface stuck files so the operator can close them in Explorer
        # and rerun. CLAUDE.md bans silent failure.
        payload["log_prune_failures"] = [
            {"path": str(p), "reason": reason} for p, reason in prune_failures
        ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
