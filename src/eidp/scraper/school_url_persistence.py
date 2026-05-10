"""Persist SchoolUrlDiscovery results into the operator DB (v104+).

Seam between the orchestrator (school_website_crawl.py) and the
SchoolSite / ReviewItem / ManualActionLog tables. Kept separate so the
orchestrator stays pure and the persistence rules are testable against
an in-memory SQLite without any HTTP.

Decision contract (must stay aligned with v1.1 charter):

* "auto"          -> insert SchoolSite (discovery_method=
                     'scrapling_stealth', confidence=0.85), audit
* "review"        -> insert ReviewItem(item_type='url_candidate',
                     status='pending', priority=2), audit
* "reject"        -> no DB write, only structured log
* "circuit_open"  -> no DB write
* "no_candidates" -> no DB write

Idempotency:

* SchoolSite is unique per (school_id, url); duplicate auto results are
  skipped without raising.
* ReviewItem dedup is keyed on (item_type, reference_table, reference_id,
  proposal_source, evidence_url, status='pending') so re-running the
  crawler does not flood the operator queue.

Caller is responsible for committing the session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

import structlog
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.models import ReviewItem, SchoolSite
from eidp.scraper.school_website_crawl import SchoolUrlDiscovery
from eidp.scraper.url_scoring import UrlScore

log = structlog.get_logger()

DISCOVERY_METHOD: Final = "scrapling_stealth"
AUTO_CONFIDENCE: Final = 0.85
REVIEW_ITEM_TYPE: Final = "url_candidate"
REVIEW_PROPOSAL_SOURCE: Final = "scrapling_stealth"
REVIEW_PRIORITY: Final = 2

ACTION_AUTO_REGISTER: Final = "url_auto_discovery"
ACTION_REVIEW_ENQUEUE: Final = "url_candidate_proposed"


@dataclass(frozen=True)
class PersistenceOutcome:
    """What was actually written for one school discovery result."""

    school_id: int
    decision: str
    school_site_id: int | None = None
    review_item_id: int | None = None
    audit_log_id: int | None = None
    skipped_reason: str | None = None


def persist_discovery(
    session: Session,
    discovery: SchoolUrlDiscovery,
) -> PersistenceOutcome:
    """Apply a single SchoolUrlDiscovery to the operator DB."""
    if discovery.decision == "auto":
        return _persist_auto(session, discovery)
    if discovery.decision == "review":
        return _persist_review(session, discovery)
    return PersistenceOutcome(
        school_id=discovery.school_id,
        decision=discovery.decision,
        skipped_reason=f"non_actionable:{discovery.decision}",
    )


def _persist_auto(
    session: Session,
    discovery: SchoolUrlDiscovery,
) -> PersistenceOutcome:
    best = discovery.best
    if best is None:
        return PersistenceOutcome(
            school_id=discovery.school_id,
            decision=discovery.decision,
            skipped_reason="auto_without_best_candidate",
        )

    existing = (
        session.query(SchoolSite)
        .filter(
            SchoolSite.school_id == discovery.school_id,
            SchoolSite.url == best.candidate_url,
        )
        .one_or_none()
    )
    if existing is not None:
        return PersistenceOutcome(
            school_id=discovery.school_id,
            decision=discovery.decision,
            school_site_id=existing.id,
            skipped_reason="school_site_already_exists",
        )

    site = SchoolSite(
        school_id=discovery.school_id,
        url=best.candidate_url,
        url_type="disclosure_or_homepage",
        discovery_method=DISCOVERY_METHOD,
        confidence=AUTO_CONFIDENCE,
        verified=False,
    )
    session.add(site)
    session.flush()

    audit = log_manual_action(
        session,
        action_type=ACTION_AUTO_REGISTER,
        target_table="school_site",
        target_id=site.id,
        old_value=None,
        new_value={
            "url": best.candidate_url,
            "score": best.score,
            "breakdown": best.breakdown,
        },
        reason=(
            f"Auto-found by {DISCOVERY_METHOD}: score={best.score:.2f}, "
            f"decision={best.decision}"
        ),
        actor=DISCOVERY_METHOD,
    )

    return PersistenceOutcome(
        school_id=discovery.school_id,
        decision=discovery.decision,
        school_site_id=site.id,
        audit_log_id=audit.id,
    )


def _persist_review(
    session: Session,
    discovery: SchoolUrlDiscovery,
) -> PersistenceOutcome:
    best = discovery.best
    if best is None:
        return PersistenceOutcome(
            school_id=discovery.school_id,
            decision=discovery.decision,
            skipped_reason="review_without_best_candidate",
        )

    existing = _existing_review_item(session, discovery.school_id, best.candidate_url)
    if existing is not None:
        return PersistenceOutcome(
            school_id=discovery.school_id,
            decision=discovery.decision,
            review_item_id=existing.id,
            skipped_reason="review_item_already_pending",
        )

    item = ReviewItem(
        item_type=REVIEW_ITEM_TYPE,
        reference_table="school",
        reference_id=discovery.school_id,
        status="pending",
        priority=REVIEW_PRIORITY,
        confidence=_score_to_confidence(best.score),
        proposal_value=json.dumps(
            {
                "url": best.candidate_url,
                "score": best.score,
                "decision": best.decision,
                "breakdown": best.breakdown,
                "notes": list(best.notes),
                "alternates": [
                    _summarize_candidate(c)
                    for c in discovery.candidates
                    if c.candidate_url != best.candidate_url
                ][:5],
            },
            ensure_ascii=False,
        ),
        proposal_reason=(
            f"Auto-suggested by {DISCOVERY_METHOD}; "
            f"score below auto threshold."
        ),
        proposal_source=REVIEW_PROPOSAL_SOURCE,
        evidence_url=best.candidate_url,
    )
    session.add(item)
    session.flush()

    audit = log_manual_action(
        session,
        action_type=ACTION_REVIEW_ENQUEUE,
        target_table="review_item",
        target_id=item.id,
        old_value=None,
        new_value={"url": best.candidate_url, "score": best.score},
        reason=(
            f"Pending review for school_id={discovery.school_id}: "
            f"score={best.score:.2f}"
        ),
        actor=REVIEW_PROPOSAL_SOURCE,
    )

    return PersistenceOutcome(
        school_id=discovery.school_id,
        decision=discovery.decision,
        review_item_id=item.id,
        audit_log_id=audit.id,
    )


def _existing_review_item(
    session: Session,
    school_id: int,
    candidate_url: str,
) -> ReviewItem | None:
    return (
        session.query(ReviewItem)
        .filter(
            ReviewItem.item_type == REVIEW_ITEM_TYPE,
            ReviewItem.reference_table == "school",
            ReviewItem.reference_id == school_id,
            ReviewItem.proposal_source == REVIEW_PROPOSAL_SOURCE,
            ReviewItem.evidence_url == candidate_url,
            ReviewItem.status == "pending",
        )
        .first()
    )


def _summarize_candidate(c: UrlScore) -> dict[str, object]:
    return {
        "url": c.candidate_url,
        "score": c.score,
        "decision": c.decision,
    }


def _score_to_confidence(score: float) -> float:
    """Map an additive 0..10 URL score onto a 0..1 confidence column.

    The DB column is Numeric(3, 2) so we cap to two decimals.
    """
    capped = max(0.0, min(score, 10.0))
    return round(capped / 10.0, 2)
