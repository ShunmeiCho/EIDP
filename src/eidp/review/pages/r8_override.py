"""Streamlit page: R8 判定 override (Sprint 8.4.c.2).

When the auto-parser put a document on the wrong fiscal_year (e.g.
classified an R8 PDF as R7), the operator confirms the correct
year here. The save path goes through
``pipeline.fiscal_year_override.override_fiscal_year`` so all four
tables (Document / DepartmentYearly / SupportRecipient /
SchoolYearStatus) move atomically and every per-table change is
audited.

Architecture
------------
Same shape as 8.4.c.1: render() is a thin Streamlit shell, the
testable surface lives in pure helpers (``list_override_candidates``,
``submit_override_form``, ``override_with_lock``).

Lock contract: UI MUST NOT block. If weekly_runner holds the lock,
``override_with_lock`` short-circuits with ``OverrideOutcome(
lock_busy=True)`` and the page renders the banner.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Document, School
from eidp.pipeline.fiscal_year_override import override_fiscal_year

# Documents in any of these statuses are eligible for R8 override:
# they have data the operator can re-classify. Documents not yet
# ingested (pending / failed / mismatch) are excluded — those go to
# the manual-entry page (8.4.c.1) first.
OVERRIDE_ELIGIBLE_STATUSES: frozenset[str] = frozenset({
    "ingested",
    "support_only",
})


@dataclass(frozen=True)
class CandidateRow:
    document_id: int
    school_id: int
    school_name: str
    prefecture: str
    current_fiscal_year: int
    fiscal_year_override: int | None
    ingest_status: str
    source_url: str


@dataclass
class OverrideOutcome:
    ok: bool
    lock_busy: bool = False
    lock_owner: str | None = None
    lock_started_at: str | None = None
    error: str | None = None
    stats: dict[str, int] | None = None


# ---------------------------------------------------------------------------
# Candidate listing
# ---------------------------------------------------------------------------


def list_override_candidates(
    session: Session,
    *,
    statuses: Iterable[str] = OVERRIDE_ELIGIBLE_STATUSES,
    limit: int = 200,
) -> list[CandidateRow]:
    """Return ingested documents whose fiscal_year the operator may want
    to override. Limited and ordered for stable display."""
    rows = (
        session.query(Document, School)
        .join(School, School.id == Document.school_id)
        .filter(Document.ingest_status.in_(list(statuses)))
        .filter(Document.fiscal_year.isnot(None))
        .order_by(Document.id.desc())
        .limit(limit)
        .all()
    )
    return [
        CandidateRow(
            document_id=doc.id,
            school_id=school.id,
            school_name=school.school_name,
            prefecture=school.prefecture,
            current_fiscal_year=int(doc.fiscal_year) if doc.fiscal_year is not None else 0,
            fiscal_year_override=doc.fiscal_year_override,
            ingest_status=doc.ingest_status or "",
            source_url=doc.source_url,
        )
        for doc, school in rows
    ]


# ---------------------------------------------------------------------------
# Override + lock
# ---------------------------------------------------------------------------


def override_with_lock(
    session: Session,
    *,
    document_id: int,
    target_fy: int,
    actor: str = "operator",
    reason: str | None = None,
    lock_path: Path,
) -> OverrideOutcome:
    """Acquire the shared lock non-blocking, then apply the override.

    UI MUST NOT call override_fiscal_year directly — always go through
    this wrapper so lock + commit + rollback boundaries stay aligned.
    """
    if target_fy < 2019 or target_fy > 2099:
        return OverrideOutcome(
            ok=False,
            error=f"target fiscal_year {target_fy} out of supported range [2019, 2099]",
        )

    try:
        with acquire_lock(lock_path, owner="ui_r8_override"):
            try:
                stats = override_fiscal_year(
                    session,
                    doc_id=document_id,
                    target_fy=target_fy,
                    actor=actor,
                    reason=reason,
                )
            except Exception as exc:
                session.rollback()
                return OverrideOutcome(ok=False, error=str(exc))
            session.commit()
            return OverrideOutcome(ok=True, stats=stats)
    except LockBusyError:
        status = probe_lock(lock_path)
        return OverrideOutcome(
            ok=False,
            lock_busy=True,
            lock_owner=status.owner,
            lock_started_at=status.started_at,
        )


# ---------------------------------------------------------------------------
# Submit handler — tested via monkeypatch
# ---------------------------------------------------------------------------


def submit_override_form(
    session: Session,
    *,
    document_id: int,
    target_fy: int,
    reason: str | None,
    lock_path: Path,
) -> OverrideOutcome:
    """Single function the Streamlit form posts to. Tests monkeypatch
    override_with_lock to assert the wiring."""
    if document_id <= 0:
        return OverrideOutcome(ok=False, error="document must be selected")
    if target_fy < 2019 or target_fy > 2099:
        return OverrideOutcome(
            ok=False, error=f"target fiscal_year {target_fy} out of [2019, 2099]",
        )
    return override_with_lock(
        session,
        document_id=document_id,
        target_fy=target_fy,
        reason=reason,
        lock_path=lock_path,
    )


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin streamlit shell
    """Top-level Streamlit render for the R8 判定 override page."""
    import streamlit as st

    from eidp.config import settings

    st.subheader("R8 判定 (年度 override)")
    status = probe_lock(lock_path)
    if status.held:
        st.warning(
            f"週次処理中、編集は一時停止しています "
            f"(owner={status.owner}, started_at={status.started_at})"
        )

    candidates = list_override_candidates(session)
    if not candidates:
        st.info("override 対象の文書はありません。")
        return

    label_to_doc: dict[str, CandidateRow] = {}
    for c in candidates:
        override_label = f"(override→{c.fiscal_year_override})" if c.fiscal_year_override else ""
        key = (
            f"doc#{c.document_id} {c.school_name} ({c.prefecture}) "
            f"fy={c.current_fiscal_year}{override_label} [{c.ingest_status}]"
        )
        label_to_doc[key] = c

    with st.form(key="r8_override_form"):
        selected_label = st.selectbox(
            "対象文書", options=list(label_to_doc.keys()),
        )
        target_fy = st.number_input(
            "新しい年度 (target_fy)", min_value=2019, max_value=2099,
            value=settings.target_fiscal_year, step=1,
        )
        reason = st.text_input("操作メモ (reason)")
        submitted = st.form_submit_button("年度を確定", type="primary")

    if submitted:
        candidate = label_to_doc[selected_label]
        outcome = submit_override_form(
            session,
            document_id=candidate.document_id,
            target_fy=int(target_fy),
            reason=reason or None,
            lock_path=lock_path,
        )
        if outcome.lock_busy:
            st.warning(
                f"週次処理中、編集は一時停止しています。"
                f"少し待ってから再度確定してください "
                f"(owner={outcome.lock_owner}, started_at={outcome.lock_started_at})"
            )
            return
        if not outcome.ok:
            st.error(f"override に失敗しました: {outcome.error}")
            return
        st.success(
            f"override 完了。"
            f"DepartmentYearly={outcome.stats['department_yearly']} "
            f"SupportRecipient={outcome.stats['support_recipient']} "
            f"SchoolYearStatus={outcome.stats['school_year_status']} "
            f"Document={outcome.stats['document']}"
        )
        st.rerun()
