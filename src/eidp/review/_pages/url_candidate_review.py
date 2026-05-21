"""Operator page for reviewing Scrapling-discovered school URL candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import streamlit as st
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import ReviewItem, School, SchoolSite
from eidp.review.operator_actor import operator_actor_from_state
from eidp.scraper.school_url_persistence import REVIEW_ITEM_TYPE, REVIEW_PROPOSAL_SOURCE
from eidp.scraper.url_normalization import normalize_candidate_url

URL_TYPE_CHOICES: Final = ("school", "disclosure", "corporation")
URL_TYPE_LABELS: Final = {
    "school": "学校トップ",
    "disclosure": "情報公開ページ",
    "corporation": "法人ページ",
}


@dataclass(frozen=True)
class UrlCandidateReviewRow:
    item_id: int
    school_id: int
    school_name: str
    prefecture: str
    url: str
    score: float | None
    confidence: float | None
    decision: str | None
    manual_required: bool
    breakdown: dict[str, object]
    notes: list[str]
    alternates: list[dict[str, object]]
    proposal_reason: str | None
    evidence_url: str | None


@dataclass(frozen=True)
class UrlCandidateActionOutcome:
    item_id: int
    decision: str
    school_site_id: int | None = None
    audit_log_id: int | None = None
    skipped_reason: str | None = None


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _proposal_dict(item: ReviewItem) -> dict[str, Any]:
    try:
        payload = json.loads(item.proposal_value or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _row_from_item(item: ReviewItem, school: School) -> UrlCandidateReviewRow | None:
    proposal = _proposal_dict(item)
    raw_url = proposal.get("url") or item.evidence_url
    manual_required = proposal.get("manual_required") is True
    if (not isinstance(raw_url, str) or not raw_url.strip()) and not manual_required:
        return None
    breakdown = proposal.get("breakdown")
    notes = proposal.get("notes")
    alternates = proposal.get("alternates")
    decision = proposal.get("decision")
    return UrlCandidateReviewRow(
        item_id=int(item.id),
        school_id=int(school.id),
        school_name=school.school_name,
        prefecture=school.prefecture or "",
        url=normalize_candidate_url(raw_url) if isinstance(raw_url, str) and raw_url.strip() else "",
        score=_as_float(proposal.get("score")),
        confidence=_as_float(item.confidence),
        decision=str(decision) if decision is not None else None,
        manual_required=manual_required,
        breakdown=breakdown if isinstance(breakdown, dict) else {},
        notes=[str(note) for note in notes] if isinstance(notes, list) else [],
        alternates=[
            alt for alt in alternates
            if isinstance(alt, dict) and isinstance(alt.get("url"), str)
        ] if isinstance(alternates, list) else [],
        proposal_reason=item.proposal_reason,
        evidence_url=item.evidence_url,
    )


def list_url_candidate_reviews(
    session: Session,
    *,
    status: str = "pending",
    limit: int = 100,
) -> list[UrlCandidateReviewRow]:
    rows = (
        session.query(ReviewItem, School)
        .join(
            School,
            (ReviewItem.reference_table == "school")
            & (ReviewItem.reference_id == School.id),
        )
        .filter(
            ReviewItem.item_type == REVIEW_ITEM_TYPE,
            ReviewItem.status == status,
        )
        .order_by(ReviewItem.priority.asc(), ReviewItem.created_at.asc())
        .limit(limit)
        .all()
    )
    parsed: list[UrlCandidateReviewRow] = []
    for item, school in rows:
        row = _row_from_item(item, school)
        if row is not None:
            parsed.append(row)
    return parsed


def _pending_url_candidate(session: Session, item_id: int) -> ReviewItem | None:
    return (
        session.query(ReviewItem)
        .filter(
            ReviewItem.id == item_id,
            ReviewItem.item_type == REVIEW_ITEM_TYPE,
            ReviewItem.status == "pending",
        )
        .one_or_none()
    )


def _existing_site(session: Session, school_id: int, url: str) -> SchoolSite | None:
    normalized = normalize_candidate_url(url)
    for site in session.query(SchoolSite).filter(SchoolSite.school_id == school_id).all():
        if normalize_candidate_url(site.url) == normalized:
            return site
    return None


def approve_url_candidate(
    session: Session,
    *,
    item_id: int,
    url_override: str | None = None,
    url_type: str = "school",
    actor: str = "operator",
    lock_path: Path | None = None,
) -> UrlCandidateActionOutcome:
    if lock_path is not None:
        try:
            with acquire_lock(lock_path, owner="ui_url_candidate_review"):
                outcome = approve_url_candidate(
                    session,
                    item_id=item_id,
                    url_override=url_override,
                    url_type=url_type,
                    actor=actor,
                    lock_path=None,
                )
                session.commit()
                return outcome
        except LockBusyError:
            return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="lock_busy")

    item = _pending_url_candidate(session, item_id)
    if item is None or item.reference_id is None:
        return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="not_pending")

    proposal = _proposal_dict(item)
    raw_url = url_override or proposal.get("url") or item.evidence_url
    if not isinstance(raw_url, str) or not raw_url.strip():
        return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="missing_url")
    url = normalize_candidate_url(raw_url)
    if url_type not in URL_TYPE_CHOICES:
        return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="invalid_url_type")

    site = _existing_site(session, int(item.reference_id), url)
    old_value: dict[str, object] | None = None
    if site is None:
        site = SchoolSite(
            school_id=int(item.reference_id),
            url=url,
            url_type=url_type,
            discovery_method=REVIEW_PROPOSAL_SOURCE,
            confidence=item.confidence,
            verified=False,
        )
        session.add(site)
        session.flush()
    elif site.url_type != url_type:
        old_value = {"school_id": item.reference_id, "url": url, "url_type": site.url_type}
        site.url_type = url_type

    now = datetime.now(UTC)
    item.status = "resolved"
    item.resolution = "approved"
    item.resolved_at = now
    item.resolved_value = url

    audit = log_manual_action(
        session,
        action_type="url_candidate_approved",
        target_table="school_site",
        target_id=site.id,
        old_value=old_value,
        new_value={
            "school_id": item.reference_id,
            "url": url,
            "url_type": url_type,
            "review_item_id": item.id,
        },
        reason="Operator approved Scrapling URL candidate",
        actor=actor,
    )
    return UrlCandidateActionOutcome(
        item_id=item_id,
        decision="approved",
        school_site_id=site.id,
        audit_log_id=audit.id,
    )


def reject_url_candidate(
    session: Session,
    *,
    item_id: int,
    notes: str = "",
    actor: str = "operator",
    lock_path: Path | None = None,
) -> UrlCandidateActionOutcome:
    if lock_path is not None:
        try:
            with acquire_lock(lock_path, owner="ui_url_candidate_review"):
                outcome = reject_url_candidate(
                    session,
                    item_id=item_id,
                    notes=notes,
                    actor=actor,
                    lock_path=None,
                )
                session.commit()
                return outcome
        except LockBusyError:
            return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="lock_busy")

    item = _pending_url_candidate(session, item_id)
    if item is None:
        return UrlCandidateActionOutcome(item_id=item_id, decision="missing", skipped_reason="not_pending")

    item.status = "resolved"
    item.resolution = "rejected"
    item.resolved_at = datetime.now(UTC)
    item.notes = notes

    audit = log_manual_action(
        session,
        action_type="url_candidate_rejected",
        target_table="review_item",
        target_id=item.id,
        old_value={"url": item.evidence_url},
        new_value={"resolution": "rejected", "notes": notes},
        reason=notes or "Operator rejected Scrapling URL candidate",
        actor=actor,
    )
    return UrlCandidateActionOutcome(
        item_id=item_id,
        decision="rejected",
        audit_log_id=audit.id,
    )


def _render_breakdown(row: UrlCandidateReviewRow) -> str:
    if not row.breakdown:
        return ""
    return " / ".join(f"{key}: {value}" for key, value in sorted(row.breakdown.items()))


def action_warning_message(outcome: UrlCandidateActionOutcome) -> str | None:
    """Operator-facing warning for action outcomes that did not write."""
    if outcome.skipped_reason == "lock_busy":
        return "週次処理中です。完了後にもう一度実行してください。"
    if outcome.skipped_reason:
        return f"URL候補を更新できませんでした: {outcome.skipped_reason}"
    return None


def render(session: Session, *, lock_path: Path | None = None) -> None:
    st.title("URL候補レビュー")
    if lock_path is not None and probe_lock(lock_path).held:
        st.warning("初回取得または週次処理中です。完了後に確認してください。")
        return

    rows = list_url_candidate_reviews(session, limit=100)
    if not rows:
        st.info("確認待ちのURL候補はありません。")
        return

    st.caption(f"確認待ち {len(rows)} 件")
    for row in rows:
        with st.container(border=True):
            st.subheader(row.school_name)
            st.caption(f"{row.prefecture} / school_id={row.school_id}")
            if row.manual_required:
                st.warning("自動URL候補が見つかりませんでした。URLを手入力して承認してください。")
            if row.url:
                st.link_button("候補URLを開く", row.url)
                st.code(row.url, language=None)
            cols = st.columns(3)
            cols[0].metric("score", "-" if row.score is None else f"{row.score:.2f}")
            cols[1].metric("confidence", "-" if row.confidence is None else f"{row.confidence:.2f}")
            cols[2].metric("alternates", str(len(row.alternates)))
            breakdown = _render_breakdown(row)
            if breakdown:
                st.caption(breakdown)
            if row.notes:
                st.caption(" / ".join(row.notes))
            edited_url = st.text_input(
                "URL",
                value=row.url,
                key=f"url_candidate_edit_{row.item_id}",
            )
            selected_url_type = st.radio(
                "URL種別",
                options=URL_TYPE_CHOICES,
                format_func=lambda key: URL_TYPE_LABELS.get(key, key),
                horizontal=True,
                key=f"url_candidate_type_{row.item_id}",
            )
            action_cols = st.columns(2)
            actor = operator_actor_from_state(st.session_state)
            if action_cols[0].button("承認", key=f"url_candidate_approve_{row.item_id}"):
                outcome = approve_url_candidate(
                    session,
                    item_id=row.item_id,
                    url_override=edited_url,
                    url_type=selected_url_type,
                    actor=actor,
                    lock_path=lock_path,
                )
                warning = action_warning_message(outcome)
                if warning is not None:
                    st.warning(warning)
                    return
                if lock_path is None:
                    session.commit()
                st.rerun()
            reject_notes = st.text_input(
                "却下理由",
                key=f"url_candidate_reject_notes_{row.item_id}",
                label_visibility="collapsed",
                placeholder="却下理由",
            )
            if action_cols[1].button("却下", key=f"url_candidate_reject_{row.item_id}"):
                outcome = reject_url_candidate(
                    session,
                    item_id=row.item_id,
                    notes=reject_notes,
                    actor=actor,
                    lock_path=lock_path,
                )
                warning = action_warning_message(outcome)
                if warning is not None:
                    st.warning(warning)
                    return
                if lock_path is None:
                    session.commit()
                st.rerun()
