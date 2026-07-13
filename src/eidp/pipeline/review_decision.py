"""DB-authoritative, append-only extraction review decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.models import ExtractionReviewDecision
from eidp.identity import ResolvedIdentity
from eidp.pipeline.extraction_review import (
    ExtractionReviewRecord,
    ReviewStatus,
    ReviewTaskType,
    ReviewValidationError,
)


class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    CORRECT = "correct"
    NEEDS_REVIEW = "needs_review"
    EXCLUDE = "exclude"


class ReviewDecisionError(ReviewValidationError):
    """Raised when a review decision violates the persisted decision contract."""


_STATUS_BY_DECISION = {
    ReviewDecision.ACCEPT: ReviewStatus.ACCEPTED,
    ReviewDecision.CORRECT: ReviewStatus.CORRECTED,
    ReviewDecision.NEEDS_REVIEW: ReviewStatus.NEEDS_REVIEW,
    ReviewDecision.EXCLUDE: ReviewStatus.EXCLUDED,
}


def apply_review_decision(
    session: Session,
    *,
    record: ExtractionReviewRecord,
    decision: ReviewDecision,
    corrected_value: int | None,
    note: str | None,
    identity: ResolvedIdentity,
) -> ExtractionReviewDecision:
    """Insert the next decision revision and matching audit row without committing."""
    normalized_note = _normalize_note(note)
    _validate_decision(
        record=record,
        decision=decision,
        corrected_value=corrected_value,
        note=normalized_note,
    )

    max_revision = session.scalar(
        select(func.max(ExtractionReviewDecision.revision)).where(
            ExtractionReviewDecision.review_id == record.review_id
        )
    )
    revision = int(max_revision or 0) + 1
    decision_id = str(uuid4())
    audit_payload: dict[str, object] = {
        "decision_id": decision_id,
        "review_id": record.review_id,
        "revision": revision,
        "decision": decision.value,
        "corrected_value": corrected_value,
    }
    if decision is ReviewDecision.EXCLUDE:
        audit_payload["reason"] = normalized_note
    elif normalized_note is not None:
        audit_payload["note"] = normalized_note

    audit = log_manual_action(
        session,
        action_type="extraction_review_decision",
        target_table="extraction_review_decision",
        new_value=audit_payload,
        reason=normalized_note,
        identity=identity,
    )
    persisted = ExtractionReviewDecision(
        decision_id=decision_id,
        review_id=record.review_id,
        revision=revision,
        decision=decision.value,
        corrected_value=corrected_value,
        note=normalized_note,
        actor=identity.actor,
        identity_source=identity.source.value,
        audit_action_id=audit.action_id,
    )
    session.add(persisted)
    session.flush()
    return persisted


def overlay_review_decisions(
    session: Session,
    records: Sequence[ExtractionReviewRecord],
) -> list[ExtractionReviewRecord]:
    """Return base records overlaid with each review ID's highest decision revision."""
    review_ids = {record.review_id for record in records}
    if not review_ids:
        return []

    latest: dict[str, ExtractionReviewDecision] = {}
    decisions = session.scalars(
        select(ExtractionReviewDecision)
        .where(ExtractionReviewDecision.review_id.in_(review_ids))
        .order_by(ExtractionReviewDecision.review_id, ExtractionReviewDecision.revision)
    ).all()
    for decision in decisions:
        current = latest.get(decision.review_id)
        if current is None or decision.revision > current.revision:
            latest[decision.review_id] = decision

    candidates = [_immutable_candidate_truth(record) for record in records]
    return [
        _overlay_record(record, latest[record.review_id])
        if record.review_id in latest
        else record
        for record in candidates
    ]


def _immutable_candidate_truth(record: ExtractionReviewRecord) -> ExtractionReviewRecord:
    initial_status = (
        ReviewStatus.NEEDS_REVIEW
        if record.task_type is ReviewTaskType.EXCEPTION_MANUAL_OCR
        else ReviewStatus.UNREVIEWED
    )
    return replace(
        record,
        corrected_value=None,
        review_status=initial_status,
        review_note=None,
        reviewed_by=None,
        reviewed_at=None,
        updated_at_utc=record.created_at_utc,
    )


def _overlay_record(
    record: ExtractionReviewRecord,
    decision: ExtractionReviewDecision,
) -> ExtractionReviewRecord:
    decided_at = decision.decided_at.isoformat()
    return replace(
        record,
        corrected_value=decision.corrected_value,
        review_status=_STATUS_BY_DECISION[ReviewDecision(decision.decision)],
        review_note=decision.note,
        reviewed_by=decision.actor,
        reviewed_at=decided_at,
        updated_at_utc=decided_at,
    )


def _normalize_note(note: str | None) -> str | None:
    normalized = (note or "").strip()
    return normalized or None


def _validate_decision(
    *,
    record: ExtractionReviewRecord,
    decision: ReviewDecision,
    corrected_value: int | None,
    note: str | None,
) -> None:
    if (
        decision in {ReviewDecision.ACCEPT, ReviewDecision.CORRECT}
        and record.task_type != ReviewTaskType.EXTRACTED_METRIC
    ):
        raise ReviewDecisionError("manual/OCR exception tasks cannot be accepted as extracted data")
    if decision is ReviewDecision.CORRECT and corrected_value is None:
        raise ReviewDecisionError("corrected_value is required for correct")
    if decision is not ReviewDecision.CORRECT and corrected_value is not None:
        raise ReviewDecisionError(f"corrected_value is not allowed for {decision.value}")
    if decision is ReviewDecision.EXCLUDE and (note is None or len(note) > 500):
        raise ReviewDecisionError("reason must be between 1 and 500 characters")
