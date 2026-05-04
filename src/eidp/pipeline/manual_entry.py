"""Business-user manual entry contract (Sprint 8.4.a).

When the operator types numbers into the Streamlit "PDF確認・手入力" page
(image PDFs, parse_failed docs, low-confidence rows), the data MUST land
in the same DB tables as the auto-parser path AND must satisfy a stricter
contract:

  1. ``extraction_method`` is set to ``"manual"`` (operator typed) or
     ``"ocr_tesseract"`` (operator confirmed an OCR pre-fill — Sprint
     8.6 will populate this branch).
  2. ``verified=True`` — the row is human-confirmed.
  3. ``extraction_confidence=1.0`` for manual entries (operator's own
     eyes), or carries the OCR confidence breakdown when applicable.
  4. ``document_id`` is required and bound on every yearly row so
     audit can trace back to the source PDF.
  5. Every save emits a ``manual_action_log`` row via
     ``eidp.db.audit.log_manual_action`` with ``action_type='manual_entry'``.
  6. Append-only: the prior current revision (if any) is demoted, a new
     revision is inserted with ``revision = max + 1`` and
     ``is_current=True``.
  7. ``DepartmentChange`` is **only** written when the operator
     explicitly says "this is a 新設/廃科/名称変更/統合" by setting
     ``dept_change`` on the per-department record. Plain number
     corrections do not write DepartmentChange — preventing the
     reconciler from mis-detecting churn as institutional change.

The function does NOT commit. The caller (Streamlit page or CLI)
controls the transaction boundary so manual_action_log + the actual
data row sit inside the same TX.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.models import (
    Department,
    DepartmentChange,
    DepartmentYearly,
    Document,
)


ManualMethod = Literal["manual", "ocr_tesseract"]
DeptChangeType = Literal["新設", "廃科", "名称変更", "統合"]

ALLOWED_METHODS: frozenset[str] = frozenset({"manual", "ocr_tesseract"})

# Sprint 8.4.a.1: ingest statuses that mean "this document is sitting in
# a manual-review queue waiting for the operator". A successful
# save_manual_entries call clears the queue by promoting the document
# to ``ingested``.
_QUEUED_INGEST_STATUSES: frozenset[str] = frozenset({
    "ocr_pending",
    "parse_failed",
    "review_pending",
})

# Numeric fields whose value must be non-negative integers.
_NON_NEGATIVE_INT_FIELDS: tuple[str, ...] = (
    "capacity",
    "enrollment",
    "intl_students",
    "graduates",
    "advanced",
    "employed",
    "other",
    "prev_enrollment",
    "dropouts",
)


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).strip()


@dataclass(frozen=True)
class DepartmentEntry:
    """One department's enrolment numbers entered by the operator.

    All numeric fields are nullable — the operator may know enrolment
    but not graduates, etc. Whatever is supplied lands in the new
    DepartmentYearly revision.
    """

    canonical_name: str
    course_type: str | None = None
    course_name: str | None = None
    duration_years: float | None = None
    capacity: int | None = None
    enrollment: int | None = None
    intl_students: int | None = None
    graduates: int | None = None
    advanced: int | None = None
    employed: int | None = None
    other: int | None = None
    prev_enrollment: int | None = None
    dropouts: int | None = None
    dropout_rate: float | None = None
    notes: str | None = None
    # If the operator explicitly classified this row as a department
    # change, set ``dept_change`` to the type and (optionally)
    # ``old_name`` / ``related_dept_id``. Plain number corrections
    # MUST leave this None — DepartmentChange is reserved for genuine
    # 新設/廃科/名称変更/統合.
    dept_change: DeptChangeType | None = None
    old_name: str | None = None
    related_dept_id: int | None = None


@dataclass
class ManualEntryResult:
    document_id: int
    fiscal_year: int
    rows_written: int = 0
    departments_created: int = 0
    department_changes_written: int = 0
    audit_actions: list[int] = field(default_factory=list)
    document_status_changed_to: str | None = None


def _validate_entry_numeric_fields(entry: DepartmentEntry) -> None:
    """Reject negative counts and out-of-range dropout_rate.

    Pipeline-level guardrail so a future CLI / OCR path cannot bypass
    UI-side validation.
    """
    for field_name in _NON_NEGATIVE_INT_FIELDS:
        value = getattr(entry, field_name)
        if value is not None and value < 0:
            raise ValueError(
                f"DepartmentEntry.{field_name} must be non-negative; got {value}"
            )
    if entry.dropout_rate is not None and not (0.0 <= entry.dropout_rate <= 1.0):
        raise ValueError(
            f"DepartmentEntry.dropout_rate must be within [0, 1]; got {entry.dropout_rate}"
        )


# ---------------------------------------------------------------------------
# Department resolution / creation
# ---------------------------------------------------------------------------


def _resolve_or_create_department(
    session: Session,
    school_id: int,
    entry: DepartmentEntry,
) -> tuple[Department, bool]:
    """Find an existing Department by natural key or create a new one.

    The natural key matches the unique constraint defined on the table:
    ``(school_id, canonical_name, course_type, course_name, duration_years)``.
    canonical_name is NFKC-normalised before lookup so "ABC学科" and
    "ＡＢＣ学科" collapse to the same row.

    Returns ``(dept, created)``.
    """
    canonical = _norm(entry.canonical_name)
    if not canonical:
        raise ValueError("DepartmentEntry.canonical_name must not be empty")

    course_type = _norm(entry.course_type) or None
    course_name = _norm(entry.course_name) or None

    existing = (
        session.query(Department)
        .filter(
            Department.school_id == school_id,
            Department.canonical_name == canonical,
            Department.course_type == course_type,
            Department.course_name == course_name,
            Department.duration_years == entry.duration_years,
        )
        .one_or_none()
    )
    if existing is not None:
        return existing, False

    dept = Department(
        school_id=school_id,
        canonical_name=canonical,
        course_type=course_type,
        course_name=course_name,
        duration_years=entry.duration_years,
    )
    session.add(dept)
    session.flush()
    return dept, True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_manual_entries(
    session: Session,
    *,
    document_id: int,
    fiscal_year: int,
    entries: list[DepartmentEntry],
    method: ManualMethod = "manual",
    confidence_breakdown: dict | None = None,
    actor: str = "operator",
    reason: str | None = None,
) -> ManualEntryResult:
    """Persist operator-entered department numbers for one document/fiscal year.

    Append-only: each entry produces a new ``DepartmentYearly`` revision
    with ``is_current=True``; any prior current row for the same
    (department_id, fiscal_year) is demoted. Every change emits a
    manual_action_log row. Department creation is logged separately
    when it happens.

    Returns a stats summary. Does NOT commit.
    """
    import json as _json

    # 8.4.a.1: enforce the method whitelist at the pipeline boundary so a
    # future CLI / OCR caller cannot silently inject e.g. method="bogus".
    if method not in ALLOWED_METHODS:
        raise ValueError(
            f"method must be one of {sorted(ALLOWED_METHODS)}; got {method!r}"
        )

    doc = session.get(Document, document_id)
    if doc is None:
        raise ValueError(f"Document id={document_id} not found")

    # 8.4.a.2: empty entries is a strict no-op. Short-circuit BEFORE any
    # DB mutation (fiscal_year backfill, status promotion) and BEFORE
    # validation runs. Otherwise an empty save would silently mutate
    # Document.fiscal_year without an audit row, breaking the contract.
    if not entries:
        return ManualEntryResult(document_id=document_id, fiscal_year=fiscal_year)

    # 8.4.a.1: fiscal_year coherence. If the Document already has a
    # fiscal_year and the caller supplies a different one, refuse — that
    # is a R8-override situation and must go through
    # ``pipeline.fiscal_year_override.override_fiscal_year`` so all four
    # tables move atomically. If the Document has no fiscal_year yet
    # (typical for ocr_pending / parse_failed first manual confirmation),
    # we backfill it on the document and audit the move.
    fy_backfilled = False
    if doc.fiscal_year is not None and doc.fiscal_year != fiscal_year:
        raise ValueError(
            f"Document id={document_id} fiscal_year={doc.fiscal_year} != "
            f"requested fiscal_year={fiscal_year}. Use "
            "pipeline.fiscal_year_override.override_fiscal_year to move "
            "all four tables atomically."
        )
    if doc.fiscal_year is None:
        doc.fiscal_year = fiscal_year
        fy_backfilled = True

    for entry in entries:
        _validate_entry_numeric_fields(entry)

    if method == "manual":
        extraction_confidence = 1.0
    else:
        # OCR — caller supplies a breakdown; surface its synthesized score.
        extraction_confidence = (
            float(confidence_breakdown.get("score", 0.85))
            if confidence_breakdown else 0.85
        )

    breakdown_text = (
        _json.dumps(confidence_breakdown, ensure_ascii=False, sort_keys=True)
        if confidence_breakdown is not None
        else _json.dumps({"method": method}, ensure_ascii=False, sort_keys=True)
    )

    result = ManualEntryResult(document_id=document_id, fiscal_year=fiscal_year)

    for entry in entries:
        dept, created = _resolve_or_create_department(session, doc.school_id, entry)
        if created:
            result.departments_created += 1
            audit_row = log_manual_action(
                session,
                action_type="manual_entry",
                target_table="department",
                target_id=dept.id,
                document_id=document_id,
                old_value=None,
                new_value={
                    "school_id": doc.school_id,
                    "canonical_name": dept.canonical_name,
                    "course_type": dept.course_type,
                    "course_name": dept.course_name,
                    "duration_years": (
                        float(dept.duration_years) if dept.duration_years is not None else None
                    ),
                },
                reason=reason,
                actor=actor,
            )
            result.audit_actions.append(audit_row.id)

        # Demote any prior current revision at this (dept, fiscal_year).
        existing_rows = (
            session.query(DepartmentYearly)
            .filter(
                DepartmentYearly.department_id == dept.id,
                DepartmentYearly.fiscal_year == fiscal_year,
            )
            .all()
        )
        prior_current = next((r for r in existing_rows if r.is_current), None)
        max_rev = max((r.revision for r in existing_rows), default=0)

        if prior_current is not None:
            session.query(DepartmentYearly).filter(
                DepartmentYearly.department_id == dept.id,
                DepartmentYearly.fiscal_year == fiscal_year,
                DepartmentYearly.is_current == True,  # noqa: E712
            ).update({"is_current": False}, synchronize_session="fetch")

        new_row = DepartmentYearly(
            department_id=dept.id,
            document_id=document_id,
            fiscal_year=fiscal_year,
            revision=max_rev + 1,
            is_current=True,
            capacity=entry.capacity,
            enrollment=entry.enrollment,
            intl_students=entry.intl_students,
            graduates=entry.graduates,
            advanced=entry.advanced,
            employed=entry.employed,
            other=entry.other,
            prev_enrollment=entry.prev_enrollment,
            dropouts=entry.dropouts,
            dropout_rate=entry.dropout_rate,
            extraction_confidence=extraction_confidence,
            extraction_method=method,
            confidence_breakdown=breakdown_text,
            verified=True,
            notes=entry.notes,
        )
        session.add(new_row)
        session.flush()

        old_state = (
            {
                "revision": prior_current.revision,
                "is_current": True,
                "enrollment": prior_current.enrollment,
                "graduates": prior_current.graduates,
            }
            if prior_current is not None
            else None
        )
        new_state = {
            "revision": new_row.revision,
            "is_current": True,
            "method": method,
            "enrollment": entry.enrollment,
            "graduates": entry.graduates,
            "verified": True,
        }
        audit_row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=new_row.id,
            document_id=document_id,
            old_value=old_state,
            new_value=new_state,
            reason=reason,
            actor=actor,
        )
        result.audit_actions.append(audit_row.id)
        result.rows_written += 1

        # DepartmentChange ONLY when the operator explicitly classified this
        # entry as a 新設/廃科/名称変更/統合. Number corrections must NOT
        # emit a change row — that would pollute the reconciler's view of
        # institutional churn.
        if entry.dept_change is not None:
            change_row = DepartmentChange(
                department_id=dept.id,
                change_type=entry.dept_change,
                fiscal_year=fiscal_year,
                old_name=entry.old_name,
                new_name=dept.canonical_name,
                related_dept_id=entry.related_dept_id,
                confidence=1.0,
                verified=True,
                verified_by=actor,
                notes=reason,
            )
            session.add(change_row)
            session.flush()
            result.department_changes_written += 1
            audit_row = log_manual_action(
                session,
                action_type="manual_entry",
                target_table="department_change",
                target_id=change_row.id,
                document_id=document_id,
                old_value=None,
                new_value={
                    "change_type": entry.dept_change,
                    "old_name": entry.old_name,
                    "new_name": dept.canonical_name,
                    "related_dept_id": entry.related_dept_id,
                },
                reason=reason,
                actor=actor,
            )
            result.audit_actions.append(audit_row.id)

    # 8.4.a.1: if the document was sitting in a manual-review queue
    # (ocr_pending / parse_failed / review_pending), promote it to
    # ingested now that the operator has supplied the data. Audit the
    # transition so the queue change is traceable.
    prior_status = doc.ingest_status
    if prior_status in _QUEUED_INGEST_STATUSES:
        doc.ingest_status = "ingested"
        result.document_status_changed_to = "ingested"
        audit_row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="document",
            target_id=doc.id,
            document_id=document_id,
            old_value={"ingest_status": prior_status, **(
                {"fiscal_year_backfilled_to": fiscal_year} if fy_backfilled else {}
            )},
            new_value={"ingest_status": "ingested", **(
                {"fiscal_year": fiscal_year} if fy_backfilled else {}
            )},
            reason=reason,
            actor=actor,
        )
        result.audit_actions.append(audit_row.id)
    elif fy_backfilled:
        # Document wasn't in a queued status but we still backfilled
        # fiscal_year — audit that fact on its own so the move is
        # traceable.
        audit_row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="document",
            target_id=doc.id,
            document_id=document_id,
            old_value={"fiscal_year": None},
            new_value={"fiscal_year": fiscal_year},
            reason=reason,
            actor=actor,
        )
        result.audit_actions.append(audit_row.id)

    return result
