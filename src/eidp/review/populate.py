"""Populate review_item table with unresolved schools for manual review.

Runs the reconciler to get fuzzy match candidates, then inserts one
ReviewItem per unresolved school with the best candidate proposal.
"""

import json
from pathlib import Path

import structlog
from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.models import ReviewItem, School
from eidp.matcher.reconciler import ReconcileCandidate, reconcile

log = structlog.get_logger()


def _candidate_to_proposal(candidate: ReconcileCandidate) -> dict[str, str | None]:
    """Serialize a ReconcileCandidate's match info into a JSON-safe dict."""
    return {
        "candidate_code": candidate.candidate_code,
        "candidate_name": candidate.candidate_name,
        "match_method": candidate.match_method,
    }


def populate_review_items(session: Session, data_dir: Path) -> dict[str, int]:
    """Create ReviewItem rows for all unresolved schools needing manual MEXT code mapping.

    Returns stats dict with counts of items created, skipped, and total unresolved.
    """
    stats = {"created": 0, "skipped_existing": 0, "skipped_excluded": 0, "total_unresolved": 0}

    # Excluded schools — Sprint 8.2.1 helper centralises the
    # current-revision + latest-fiscal-year filter so historical revisions
    # cannot silently keep a school out of the review queue.
    from eidp.db.current_helpers import latest_excluded_school_ids

    excluded_ids: set[int] = {row[0] for row in latest_excluded_school_ids(session)}

    # Run reconciler to get fuzzy match candidates
    report = reconcile(session, data_dir)

    # Build lookup: school_id -> best candidate from reconciler
    candidate_by_school: dict[int, ReconcileCandidate] = {}
    for c in report.needs_manual:
        candidate_by_school[c.school_id] = c

    # Get all schools without school_code
    unresolved_schools = session.query(School).filter(School.school_code.is_(None)).all()

    # Check which schools already have pending review items
    existing_school_ids: set[int] = set()
    existing_rows = (
        session.query(ReviewItem.reference_id)
        .filter(
            ReviewItem.reference_table == "school",
            ReviewItem.item_type == "school_code",
            ReviewItem.status == "pending",
        )
        .all()
    )
    for row in existing_rows:
        if row[0] is not None:
            existing_school_ids.add(row[0])

    for school in unresolved_schools:
        if school.id in excluded_ids:
            stats["skipped_excluded"] += 1
            continue

        stats["total_unresolved"] += 1

        if school.id in existing_school_ids:
            stats["skipped_existing"] += 1
            continue

        candidate = candidate_by_school.get(school.id)

        proposal_value: str | None = None
        proposal_reason: str | None = None
        proposal_source: str | None = None
        confidence: float | None = None
        priority = 5

        if candidate is not None and candidate.candidate_code is not None:
            proposal_value = json.dumps(_candidate_to_proposal(candidate), ensure_ascii=False)
            proposal_reason = (
                f"Fuzzy match: '{school.school_name}' -> '{candidate.candidate_name}' "
                f"via {candidate.match_method} (score={candidate.confidence})"
            )
            proposal_source = "reconciler"
            confidence = candidate.confidence
            # Higher confidence = higher priority (lower number = more urgent)
            if confidence >= 0.9:
                priority = 2
            elif confidence >= 0.7:
                priority = 3
            else:
                priority = 5
        else:
            proposal_reason = (
                f"No fuzzy match found for '{school.school_name}' "
                f"(prefecture={school.prefecture}, corp={school.corporation_name})"
            )
            proposal_source = "reconciler"
            priority = 8  # Lower priority -- no candidate to review

        item = ReviewItem(
            item_type="school_code",
            reference_id=school.id,
            reference_table="school",
            status="pending",
            priority=priority,
            confidence=confidence,
            proposal_value=proposal_value,
            proposal_reason=proposal_reason,
            proposal_source=proposal_source,
        )
        session.add(item)
        stats["created"] += 1

    session.flush()
    log.info("review_items_populated", **stats)
    return stats


def get_review_stats(session: Session) -> dict[str, int]:
    """Get summary counts for the review queue."""
    total = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.item_type == "school_code")
        .scalar()
        or 0
    )
    pending = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.item_type == "school_code", ReviewItem.status == "pending")
        .scalar()
        or 0
    )
    approved = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.item_type == "school_code", ReviewItem.resolution == "approved")
        .scalar()
        or 0
    )
    rejected = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.item_type == "school_code", ReviewItem.resolution == "rejected")
        .scalar()
        or 0
    )
    corrected = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.item_type == "school_code", ReviewItem.resolution == "corrected")
        .scalar()
        or 0
    )
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "corrected": corrected,
    }
