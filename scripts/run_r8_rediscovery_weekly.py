"""Weekly R8 rediscovery runner.

This is the systemd-facing production entrypoint for Sprint 7.  It
targets schools that already have a target PDF for an older fiscal year
but no current-FY target PDF, then runs:

1. PDF rediscovery for the selected school_site methods.
2. Ingestion only for documents created during this run.
3. A JSON summary with before/after report snapshots and evidence paths.

Use --dry-run for a read-only plan/snapshot check.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Document, School, SchoolSite  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402
from eidp.pipeline.ingest import run_ingestion  # noqa: E402
from eidp.reports.coverage import compute_coverage  # noqa: E402
from eidp.reports.extraction import compute_extraction  # noqa: E402
from eidp.reports.gaps import compute_gaps  # noqa: E402
from eidp.scraper.pdf_discovery import run_pdf_discovery  # noqa: E402

DEFAULT_METHODS = ("prefecture_aggregator",)


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
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    run_id = _timestamp()
    discovery_evidence = output_dir / f"{run_id}-discovery-rejections.jsonl"
    ingest_evidence = output_dir / f"{run_id}-ingest-rejections.jsonl"
    summary_path = output_dir / f"{run_id}-summary.json"

    session = SessionLocal()
    try:
        stale_school_ids = select_stale_school_ids(
            session,
            current_fy=current_fy,
            methods=methods,
            school_type=school_type,
            limit=limit,
        )
        before = _snapshot_reports(session, current_fy, school_type)

        max_doc_id_before = session.query(func.max(Document.id)).scalar() or 0
        discovery_stats: dict[str, int] = {}
        ingest_stats: dict[str, int] = {}
        new_document_ids: list[int] = []

        if dry_run or not stale_school_ids:
            session.rollback()
        else:
            effective_batch_size = max(batch_size, len(stale_school_ids))
            discovery_stats = run_pdf_discovery(
                session,
                storage_dir=storage_dir,
                batch_size=effective_batch_size,
                rate_limit=rate_limit,
                discovery_methods=methods,
                school_ids=stale_school_ids,
                evidence_path=discovery_evidence,
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

        after = _snapshot_reports(session, current_fy, school_type)
        summary = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "dry_run": dry_run,
            "current_fy": current_fy,
            "school_type": school_type,
            "methods": methods,
            "stale_school_count": len(stale_school_ids),
            "school_ids": stale_school_ids,
            "new_document_ids": new_document_ids,
            "discovery_stats": discovery_stats,
            "ingest_stats": ingest_stats,
            "before": before,
            "after": after,
            "delta": _delta(before, after),
            "evidence": {
                "discovery_rejections": str(discovery_evidence),
                "ingest_rejections": str(ingest_evidence),
            },
            "summary_path": str(summary_path),
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-fy", type=int, default=2026)
    parser.add_argument("--methods", nargs="+", default=list(DEFAULT_METHODS))
    parser.add_argument("--school-type", default="専門学校")
    parser.add_argument("--storage-dir", type=Path, default=Path("data/pdfs"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/r8-rediscovery-weekly"))
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--rate-limit", type=float, default=1.5)
    parser.add_argument("--ingest-batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_weekly(
        current_fy=args.current_fy,
        methods=args.methods,
        school_type=args.school_type,
        storage_dir=args.storage_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
        ingest_batch_size=args.ingest_batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    print(json.dumps({
        "summary_path": summary["summary_path"],
        "dry_run": summary["dry_run"],
        "stale_school_count": summary["stale_school_count"],
        "new_document_ids": summary["new_document_ids"],
        "discovery_stats": summary["discovery_stats"],
        "ingest_stats": summary["ingest_stats"],
        "coverage_delta": summary["delta"]["coverage"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
