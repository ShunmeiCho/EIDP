"""Streamlit page: PDF確認・手入力 (Sprint 8.4.c.1).

Business-user main battlefield. Image PDFs / parse_failed / review_pending /
school_mismatch documents land in this page; the operator views the PDF
and types numbers into a form. All saves go through
``pipeline.manual_entry.save_manual_entries`` — the page MUST NOT issue
INSERTs against ``DepartmentYearly`` directly.

Architecture
------------
The render function is a thin Streamlit shell. The testable surface
lives in pure helpers:

  * ``list_pending_documents`` — queue query.
  * ``form_data_to_entries``   — UI dict → ``DepartmentEntry`` list,
    with validation that mirrors ``save_manual_entries`` constraints
    so the user gets feedback before we try to save.
  * ``save_with_lock``         — acquires the shared lock
    non-blocking; on lock-busy returns a status without writing.
  * ``LockBusy`` / ``SaveOk``  — return type for the save call.

Lock contract (8.4.b): UI MUST NOT block on the lock. If the weekly
runner holds it, the page surfaces a banner ("週次処理中、編集は一時停止")
and refuses the save attempt. Read-only listing is unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Document, School
from eidp.pipeline.manual_entry import (
    ALLOWED_METHODS,
    DepartmentEntry,
    ManualEntryResult,
    save_manual_entries,
)


# Statuses we surface in the manual-entry queue. Mirrors
# ``manual_entry._QUEUED_INGEST_STATUSES`` plus ``school_mismatch`` which
# the operator can resolve here too (by reassigning to the correct
# school via override / re-ingest workflows — outside this page's scope,
# but its presence in the queue lets the operator see it).
QUEUE_STATUSES: tuple[str, ...] = (
    "ocr_pending",
    "parse_failed",
    "review_pending",
    "school_mismatch",
)


@dataclass(frozen=True)
class QueueRow:
    """Minimal projection of a queued Document for table display."""

    document_id: int
    school_id: int
    school_name: str
    prefecture: str
    fiscal_year: int | None
    ingest_status: str
    file_path: str | None
    source_url: str


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class FormValidation:
    entries: list[DepartmentEntry] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class SaveOutcome:
    """Return type from save_with_lock."""

    ok: bool
    lock_busy: bool = False
    lock_owner: str | None = None
    lock_started_at: str | None = None
    error: str | None = None
    result: ManualEntryResult | None = None


# ---------------------------------------------------------------------------
# Queue listing
# ---------------------------------------------------------------------------


def list_pending_documents(
    session: Session,
    *,
    statuses: Iterable[str] = QUEUE_STATUSES,
    limit: int = 200,
) -> list[QueueRow]:
    """Return the manual-entry queue, ordered by oldest-first.

    The page calls this on every render. Limited to 200 rows by default
    so a large parse_failed backlog doesn't kill Streamlit's rendering
    budget; the operator can drill in via filters once the basic page
    works.
    """
    rows = (
        session.query(Document, School)
        .join(School, School.id == Document.school_id)
        .filter(Document.ingest_status.in_(list(statuses)))
        .order_by(Document.id.asc())
        .limit(limit)
        .all()
    )
    return [
        QueueRow(
            document_id=doc.id,
            school_id=school.id,
            school_name=school.school_name,
            prefecture=school.prefecture,
            fiscal_year=doc.fiscal_year,
            ingest_status=doc.ingest_status or "",
            file_path=doc.file_path,
            source_url=doc.source_url,
        )
        for doc, school in rows
    ]


# ---------------------------------------------------------------------------
# Form → DepartmentEntry conversion
# ---------------------------------------------------------------------------


def _coerce_int(value: Any, field_name: str, errors: list[ValidationError]) -> int | None:
    if value is None or value == "":
        return None
    try:
        i = int(value)
    except (TypeError, ValueError):
        errors.append(ValidationError(field=field_name, message=f"must be an integer; got {value!r}"))
        return None
    if i < 0:
        errors.append(ValidationError(field=field_name, message=f"must be non-negative; got {i}"))
        return None
    return i


def _coerce_float(value: Any, field_name: str, errors: list[ValidationError], *, lo: float, hi: float) -> float | None:
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        errors.append(ValidationError(field=field_name, message=f"must be numeric; got {value!r}"))
        return None
    if not (lo <= f <= hi):
        errors.append(ValidationError(field=field_name, message=f"must be in [{lo}, {hi}]; got {f}"))
        return None
    return f


_VALID_DEPT_CHANGE = {"新設", "廃科", "名称変更", "統合", None, ""}


def form_data_to_entries(rows: list[dict]) -> FormValidation:
    """Convert the per-department UI form dict list to validated entries.

    Each input row is a dict with keys::

        canonical_name, course_type, course_name, duration_years,
        capacity, enrollment, intl_students, graduates,
        advanced, employed, other, prev_enrollment,
        dropouts, dropout_rate, notes,
        dept_change ('新設'/'廃科'/'名称変更'/'統合'/None),
        old_name, related_dept_id

    Returns a ``FormValidation`` carrying any validation errors so the
    page can render them inline. ``form_validation.ok`` is True iff the
    list is safe to pass to ``save_manual_entries``.
    """
    fv = FormValidation()

    for idx, row in enumerate(rows):
        prefix = f"row[{idx}]"
        canonical = (row.get("canonical_name") or "").strip()
        if not canonical:
            fv.errors.append(ValidationError(
                field=f"{prefix}.canonical_name",
                message="学科名 is required",
            ))
            continue

        dept_change = row.get("dept_change") or None
        if dept_change not in _VALID_DEPT_CHANGE:
            fv.errors.append(ValidationError(
                field=f"{prefix}.dept_change",
                message=f"must be one of 新設/廃科/名称変更/統合/None; got {dept_change!r}",
            ))
            continue

        capacity = _coerce_int(row.get("capacity"), f"{prefix}.capacity", fv.errors)
        enrollment = _coerce_int(row.get("enrollment"), f"{prefix}.enrollment", fv.errors)
        intl_students = _coerce_int(row.get("intl_students"), f"{prefix}.intl_students", fv.errors)
        graduates = _coerce_int(row.get("graduates"), f"{prefix}.graduates", fv.errors)
        advanced = _coerce_int(row.get("advanced"), f"{prefix}.advanced", fv.errors)
        employed = _coerce_int(row.get("employed"), f"{prefix}.employed", fv.errors)
        other = _coerce_int(row.get("other"), f"{prefix}.other", fv.errors)
        prev_enrollment = _coerce_int(row.get("prev_enrollment"), f"{prefix}.prev_enrollment", fv.errors)
        dropouts = _coerce_int(row.get("dropouts"), f"{prefix}.dropouts", fv.errors)
        dropout_rate = _coerce_float(
            row.get("dropout_rate"), f"{prefix}.dropout_rate", fv.errors, lo=0.0, hi=1.0,
        )
        duration_years_raw = row.get("duration_years")
        duration_years: float | None = None
        if duration_years_raw not in (None, ""):
            try:
                duration_years = float(duration_years_raw)
            except (TypeError, ValueError):
                fv.errors.append(ValidationError(
                    field=f"{prefix}.duration_years",
                    message=f"must be numeric; got {duration_years_raw!r}",
                ))

        if any(e.field.startswith(prefix) for e in fv.errors):
            continue

        fv.entries.append(DepartmentEntry(
            canonical_name=canonical,
            course_type=(row.get("course_type") or "").strip() or None,
            course_name=(row.get("course_name") or "").strip() or None,
            duration_years=duration_years,
            capacity=capacity,
            enrollment=enrollment,
            intl_students=intl_students,
            graduates=graduates,
            advanced=advanced,
            employed=employed,
            other=other,
            prev_enrollment=prev_enrollment,
            dropouts=dropouts,
            dropout_rate=dropout_rate,
            notes=(row.get("notes") or "").strip() or None,
            dept_change=dept_change if dept_change else None,  # type: ignore[arg-type]
            old_name=(row.get("old_name") or "").strip() or None,
            related_dept_id=row.get("related_dept_id") or None,
        ))

    return fv


# ---------------------------------------------------------------------------
# Save with lock
# ---------------------------------------------------------------------------


def save_with_lock(
    session: Session,
    *,
    document_id: int,
    fiscal_year: int,
    entries: list[DepartmentEntry],
    method: str = "manual",
    confidence_breakdown: dict | None = None,
    actor: str = "operator",
    reason: str | None = None,
    lock_path: Path,
) -> SaveOutcome:
    """Acquire the shared advisory lock non-blocking, then save.

    Returns ``SaveOutcome``:
      * ``ok=True``                   — lock acquired, save committed.
      * ``lock_busy=True``            — weekly runner has the lock; the
        page renders a banner and tells the operator to retry.
      * ``ok=False, error=...``      — lock was free but the underlying
        ``save_manual_entries`` raised (e.g. invalid method, fiscal
        mismatch, negative numeric). The transaction is rolled back so
        the page can re-render with the error message.

    UI MUST NOT call ``save_manual_entries`` directly — always go
    through this wrapper so lock + commit boundaries stay aligned.
    """
    if method not in ALLOWED_METHODS:
        return SaveOutcome(ok=False, error=f"method must be one of {sorted(ALLOWED_METHODS)}; got {method!r}")

    try:
        with acquire_lock(lock_path, owner="ui_manual_entry"):
            try:
                result = save_manual_entries(
                    session,
                    document_id=document_id,
                    fiscal_year=fiscal_year,
                    entries=entries,
                    method=method,  # type: ignore[arg-type]
                    confidence_breakdown=confidence_breakdown,
                    actor=actor,
                    reason=reason,
                )
            except Exception as exc:
                session.rollback()
                return SaveOutcome(ok=False, error=str(exc))
            session.commit()
            return SaveOutcome(ok=True, result=result)
    except LockBusyError:
        status = probe_lock(lock_path)
        return SaveOutcome(
            ok=False,
            lock_busy=True,
            lock_owner=status.owner,
            lock_started_at=status.started_at,
        )


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin streamlit shell
    """Top-level Streamlit render. Tests cover the helpers above; the
    rendering itself is exercised by the operator via the running app."""
    import streamlit as st

    st.subheader("PDF確認・手入力")
    status = probe_lock(lock_path)
    if status.held:
        st.warning(
            f"週次処理中、編集は一時停止しています "
            f"(owner={status.owner}, started_at={status.started_at})"
        )

    queue = list_pending_documents(session)
    if not queue:
        st.success("待機中の文書はありません。")
        return

    st.caption(f"待機 {len(queue)} 件")
    for row in queue[:20]:
        with st.expander(f"[{row.ingest_status}] {row.school_name} ({row.prefecture}) — fy={row.fiscal_year} doc#{row.document_id}"):
            st.write(f"source_url: {row.source_url}")
            if row.file_path:
                st.write(f"file: {row.file_path}")
            st.info(
                "保存は ``pipeline.manual_entry.save_manual_entries`` を経由します。"
                " UI から直接 DB に書き込みません。"
            )
