"""Business-user fiscal year override (Sprint 8.2.c.2).

When the operator UI re-classifies a Document's fiscal year (for example,
confirming the target年度 PDF after the parser guessed the previous year), four
tables must move together so coverage and Excel agree afterwards:

  1. ``department_yearly``       (Department × fiscal_year × revision)
  2. ``support_recipient``       (school × fiscal_year × revision)
  3. ``school_year_status``      (school × fiscal_year × revision)
  4. ``document``                (fiscal_year + fiscal_year_override)

This module implements the **rewrite** strategy owner chose in v6: the
underlying rows are physically copied to the target fiscal_year (as new
``revision = max + 1`` entries with ``is_current=True``), the source-fy rows
get flipped to ``is_current=False``, and ``Document.fiscal_year`` itself is
overwritten alongside an explicit ``fiscal_year_override`` marker. Coverage,
exporter, and ingest therefore continue to read raw ``fiscal_year`` and
report consistent numbers without an ``effective_fiscal_year()`` shim being
sprinkled across the codebase.

``effective_fiscal_year()`` IS exported here, but its mandate is narrow:
override operation internals + UI display only. Don't import it into
coverage / exporter / ingest — the rewrite has already done the work.

Audit
-----
Every per-row table edit emits a ``manual_action_log`` entry via
``eidp.db.audit.log_manual_action``. The DB row is authoritative; the
JSONL outbox is flushed by the caller after commit (or by
``eidp audit-flush`` later) per the v6 audit contract.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.models import (
    DepartmentYearly,
    Document,
    SchoolYearStatus,
    SupportRecipient,
)


def effective_fiscal_year(doc: Document) -> int | None:
    """Return the operator-confirmed fiscal year for a Document.

    LIMITED USE: override operation internals + UI display only. Coverage,
    exporter, ingest, and any other read-path code MUST continue to read
    ``Document.fiscal_year`` directly — the rewrite path keeps that field
    accurate.
    """
    if doc.fiscal_year_override is not None:
        return doc.fiscal_year_override
    return doc.fiscal_year


# Field names whose values are physically carried over to the new revision
# rows. Selected so the rewrite is value-preserving across the move.
_DEPT_YEARLY_CARRY = (
    "capacity",
    "enrollment",
    "intl_students",
    "graduates",
    "advanced",
    "employed",
    "other",
    "prev_enrollment",
    "dropouts",
    "dropout_rate",
    "extraction_confidence",
    "extraction_method",
    "confidence_breakdown",
    "verified",
    "notes",
)
_SR_CARRY = (
    "school_number",
    "first_half_total",
    "first_half_cat1",
    "first_half_cat2",
    "first_half_cat3",
    "first_half_cat4",
    "second_half_total",
    "second_half_cat1",
    "second_half_cat2",
    "second_half_cat3",
    "second_half_cat4",
    "annual_total",
    "household_change",
    "grand_total",
    "prev_enrollment",
    "recipient_rate",
    "extraction_confidence",
    "confidence_breakdown",
    "notes",
)
_SYS_CARRY = (
    "status",
    "legacy_status",
    "excluded_reason",
    "last_checked",
    "collected_at",
    "notes",
)


def _max_revision[T: (DepartmentYearly, SchoolYearStatus, SupportRecipient)](
    session: Session,
    model: type[T],
    **filters: Any,
) -> int:
    """Return max revision for a (model, filters) selection, or 0."""
    from sqlalchemy import func

    return (
        session.query(func.max(model.revision)).filter_by(**filters).scalar()
    ) or 0


def _carry_dict(src: object, fields: tuple[str, ...]) -> dict[str, Any]:
    return {f: getattr(src, f) for f in fields}


def override_fiscal_year(
    session: Session,
    doc_id: int,
    target_fy: int,
    *,
    actor: str = "operator",
    reason: str | None = None,
) -> dict[str, int]:
    """Rewrite a Document and its 3 yearly-keyed satellites to ``target_fy``.

    The operation is a single SQL transaction from the caller's perspective:
    this function does NOT commit, so the audit rows it inserts via
    ``log_manual_action`` sit in the same transaction as the rewrites. Caller
    is responsible for ``session.commit()`` + (optionally)
    ``flush_audit_outbox(session)``.

    Returns a stats dict with per-table counts.
    """
    doc = session.get(Document, doc_id)
    if doc is None:
        raise ValueError(f"Document id={doc_id} not found")

    source_fy = doc.fiscal_year
    if source_fy is None:
        raise ValueError(
            f"Document id={doc_id} has no fiscal_year; cannot override to {target_fy}"
        )
    if source_fy == target_fy and doc.fiscal_year_override == target_fy:
        return {"department_yearly": 0, "support_recipient": 0, "school_year_status": 0, "document": 0}

    stats = {
        "department_yearly": 0,
        "support_recipient": 0,
        "school_year_status": 0,
        "document": 0,
    }

    # --- 1. department_yearly ---------------------------------------------
    # Move every current row that this document owns at source_fy.
    src_dy_rows = (
        session.query(DepartmentYearly)
        .filter(
            DepartmentYearly.document_id == doc_id,
            DepartmentYearly.fiscal_year == source_fy,
            DepartmentYearly.is_current.is_(True),
        )
        .all()
    )
    for src_dy in src_dy_rows:
        # Demote any prior current row at the target fiscal year for this
        # department (different document or older override). The new
        # rewritten row will become current.
        session.query(DepartmentYearly).filter(
            DepartmentYearly.department_id == src_dy.department_id,
            DepartmentYearly.fiscal_year == target_fy,
            DepartmentYearly.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        max_rev = _max_revision(
            session, DepartmentYearly,
            department_id=src_dy.department_id, fiscal_year=target_fy,
        )

        old_state = {
            "fiscal_year": source_fy,
            "revision": src_dy.revision,
            "is_current": True,
        }
        # Demote the source row.
        src_dy.is_current = False

        new_dy_row = DepartmentYearly(
            department_id=src_dy.department_id,
            document_id=src_dy.document_id,
            fiscal_year=target_fy,
            revision=max_rev + 1,
            is_current=True,
            **_carry_dict(src_dy, _DEPT_YEARLY_CARRY),
        )
        session.add(new_dy_row)
        session.flush()

        log_manual_action(
            session,
            action_type="fiscal_year_override",
            target_table="department_yearly",
            target_id=src_dy.id,
            document_id=doc_id,
            old_value=old_state,
            new_value={
                "fiscal_year": target_fy,
                "revision": new_dy_row.revision,
                "is_current": True,
                "new_id": new_dy_row.id,
            },
            reason=reason,
            actor=actor,
        )
        stats["department_yearly"] += 1

    # --- 2. support_recipient ---------------------------------------------
    src_sr_rows = (
        session.query(SupportRecipient)
        .filter(
            SupportRecipient.document_id == doc_id,
            SupportRecipient.fiscal_year == source_fy,
            SupportRecipient.is_current.is_(True),
        )
        .all()
    )
    for src_sr in src_sr_rows:
        session.query(SupportRecipient).filter(
            SupportRecipient.school_id == src_sr.school_id,
            SupportRecipient.fiscal_year == target_fy,
            SupportRecipient.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        max_rev = _max_revision(
            session, SupportRecipient,
            school_id=src_sr.school_id, fiscal_year=target_fy,
        )

        old_state = {
            "fiscal_year": source_fy,
            "revision": src_sr.revision,
            "is_current": True,
        }
        src_sr.is_current = False

        new_sr_row = SupportRecipient(
            school_id=src_sr.school_id,
            document_id=src_sr.document_id,
            fiscal_year=target_fy,
            revision=max_rev + 1,
            is_current=True,
            **_carry_dict(src_sr, _SR_CARRY),
        )
        session.add(new_sr_row)
        session.flush()

        log_manual_action(
            session,
            action_type="fiscal_year_override",
            target_table="support_recipient",
            target_id=src_sr.id,
            document_id=doc_id,
            old_value=old_state,
            new_value={
                "fiscal_year": target_fy,
                "revision": new_sr_row.revision,
                "is_current": True,
                "new_id": new_sr_row.id,
            },
            reason=reason,
            actor=actor,
        )
        stats["support_recipient"] += 1

    # --- 3. school_year_status --------------------------------------------
    src_sys_rows = (
        session.query(SchoolYearStatus)
        .filter(
            SchoolYearStatus.document_id == doc_id,
            SchoolYearStatus.fiscal_year == source_fy,
            SchoolYearStatus.is_current.is_(True),
        )
        .all()
    )
    for src_sys in src_sys_rows:
        session.query(SchoolYearStatus).filter(
            SchoolYearStatus.school_id == src_sys.school_id,
            SchoolYearStatus.fiscal_year == target_fy,
            SchoolYearStatus.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        max_rev = _max_revision(
            session, SchoolYearStatus,
            school_id=src_sys.school_id, fiscal_year=target_fy,
        )

        old_state = {
            "fiscal_year": source_fy,
            "revision": src_sys.revision,
            "is_current": True,
        }
        src_sys.is_current = False

        new_sys_row = SchoolYearStatus(
            school_id=src_sys.school_id,
            document_id=src_sys.document_id,
            fiscal_year=target_fy,
            revision=max_rev + 1,
            is_current=True,
            **_carry_dict(src_sys, _SYS_CARRY),
        )
        session.add(new_sys_row)
        session.flush()

        log_manual_action(
            session,
            action_type="fiscal_year_override",
            target_table="school_year_status",
            target_id=src_sys.id,
            document_id=doc_id,
            old_value=old_state,
            new_value={
                "fiscal_year": target_fy,
                "revision": new_sys_row.revision,
                "is_current": True,
                "new_id": new_sys_row.id,
            },
            reason=reason,
            actor=actor,
        )
        stats["school_year_status"] += 1

    # --- 4. document ------------------------------------------------------
    old_doc_state = {
        "fiscal_year": source_fy,
        "fiscal_year_override": doc.fiscal_year_override,
    }
    doc.fiscal_year = target_fy
    doc.fiscal_year_override = target_fy
    log_manual_action(
        session,
        action_type="fiscal_year_override",
        target_table="document",
        target_id=doc.id,
        document_id=doc.id,
        old_value=old_doc_state,
        new_value={
            "fiscal_year": target_fy,
            "fiscal_year_override": target_fy,
        },
        reason=reason,
        actor=actor,
    )
    stats["document"] = 1
    return stats
