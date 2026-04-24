"""Streamlit review queue for school identity resolution (Step 6).

Launch with: eidp review-ui
Or directly: streamlit run src/eidp/review/app.py
"""

import json
from datetime import datetime, timezone

import streamlit as st
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from eidp.db.models import ReviewItem, School, SchoolAlias, SchoolYearStatus
from eidp.db.session import SessionLocal
from eidp.review import operator_pages


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_session() -> Session:
    """Get or reuse a SQLAlchemy session stored in Streamlit session_state."""
    if "db_session" not in st.session_state:
        st.session_state.db_session = SessionLocal()
    return st.session_state.db_session


def _commit(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_dashboard_stats(session: Session) -> dict[str, int]:
    """Counts for the progress dashboard."""
    total_schools = session.query(func.count(School.id)).scalar() or 0
    with_code = (
        session.query(func.count(School.id))
        .filter(School.school_code.isnot(None))
        .scalar()
        or 0
    )

    # Only exclude if the LATEST fiscal year has excluded_reason
    latest_year_subq = (
        session.query(
            SchoolYearStatus.school_id,
            func.max(SchoolYearStatus.fiscal_year).label("max_fy"),
        )
        .group_by(SchoolYearStatus.school_id)
        .subquery()
    )
    excluded_ids: set[int] = set()
    for row in (
        session.query(SchoolYearStatus.school_id)
        .join(
            latest_year_subq,
            and_(
                SchoolYearStatus.school_id == latest_year_subq.c.school_id,
                SchoolYearStatus.fiscal_year == latest_year_subq.c.max_fy,
            ),
        )
        .filter(SchoolYearStatus.excluded_reason.isnot(None))
    ):
        excluded_ids.add(row[0])
    no_code = session.query(School).filter(School.school_code.is_(None)).all()
    excluded_count = sum(1 for s in no_code if s.id in excluded_ids)
    unresolved_count = sum(1 for s in no_code if s.id not in excluded_ids)

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

    return {
        "total_schools": total_schools,
        "with_code": with_code,
        "excluded": excluded_count,
        "unresolved": unresolved_count,
        "pending_reviews": pending,
        "approved": approved,
        "rejected": rejected,
    }


def _load_pending_items(session: Session) -> list[ReviewItem]:
    """Load pending review items ordered by priority then confidence desc."""
    return (
        session.query(ReviewItem)
        .filter(ReviewItem.item_type == "school_code", ReviewItem.status == "pending")
        .order_by(ReviewItem.priority.asc(), ReviewItem.confidence.desc().nullslast())
        .all()
    )


def _load_school(session: Session, school_id: int) -> School | None:
    return session.get(School, school_id)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _approve_item(session: Session, item: ReviewItem, school: School) -> None:
    """Approve: apply the proposed MEXT code to the school."""
    if item.proposal_value is None:
        st.error("No proposal to approve.")
        return

    proposal = json.loads(item.proposal_value)
    code = proposal.get("candidate_code")
    candidate_name = proposal.get("candidate_name")

    if not code:
        st.error("Proposal has no candidate_code.")
        return

    # Check for code conflict
    existing = session.query(School).filter(School.school_code == code).first()
    if existing and existing.id != school.id:
        st.error(
            f"Code {code} already assigned to school id={existing.id} "
            f"({existing.school_name}). Cannot assign."
        )
        return

    school.school_code = code

    # Create alias if the candidate name differs
    if candidate_name and candidate_name != school.school_name:
        alias_exists = (
            session.query(SchoolAlias)
            .filter(SchoolAlias.school_id == school.id, SchoolAlias.alias_name == candidate_name)
            .first()
        )
        if not alias_exists:
            alias = SchoolAlias(
                school_id=school.id,
                alias_name=candidate_name,
                alias_type="formal",
                source="review_queue",
            )
            session.add(alias)

    item.status = "resolved"
    item.resolution = "approved"
    item.resolved_value = code
    item.resolved_at = datetime.now(timezone.utc)
    _commit(session)


def _approve_with_correction(
    session: Session, item: ReviewItem, school: School, corrected_code: str
) -> None:
    """Approve with a manually corrected MEXT code."""
    corrected_code = corrected_code.strip()
    if not corrected_code:
        st.error("Please enter a valid MEXT code.")
        return

    # Validate MEXT code format: 13-character alphanumeric starting with H (vocational)
    import re
    if not re.match(r"^[A-Z]\d{12}$", corrected_code):
        st.error(f"Invalid MEXT code format: '{corrected_code}'. Expected 13 chars like 'H101310100147'.")
        return

    # Check for code conflict
    existing = session.query(School).filter(School.school_code == corrected_code).first()
    if existing and existing.id != school.id:
        st.error(
            f"Code {corrected_code} already assigned to school id={existing.id} "
            f"({existing.school_name}). Cannot assign."
        )
        return

    school.school_code = corrected_code
    item.status = "resolved"
    item.resolution = "corrected"
    item.resolved_value = corrected_code
    item.resolved_at = datetime.now(timezone.utc)
    _commit(session)


def _reject_item(session: Session, item: ReviewItem, notes: str = "") -> None:
    """Reject: mark the proposal as wrong, leave school_code NULL."""
    item.status = "resolved"
    item.resolution = "rejected"
    item.resolved_at = datetime.now(timezone.utc)
    if notes:
        item.notes = notes
    _commit(session)


def _skip_item(session: Session, item: ReviewItem) -> None:
    """Skip: lower priority so it appears later."""
    item.priority = min(item.priority + 2, 10)
    _commit(session)


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def _render_dashboard(stats: dict[str, int]) -> None:
    """Render the progress dashboard at the top."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resolved", stats["with_code"])
    col2.metric("Pending Review", stats["pending_reviews"])
    col3.metric("Unresolved", stats["unresolved"])
    col4.metric("Excluded", stats["excluded"])

    total_actionable = stats["with_code"] + stats["unresolved"]
    if total_actionable > 0:
        progress = stats["with_code"] / total_actionable
        st.progress(progress, text=f"Resolution progress: {stats['with_code']}/{total_actionable} ({progress:.0%})")

    with st.expander("Detailed statistics"):
        st.write(f"- Total schools in DB: **{stats['total_schools']}**")
        st.write(f"- With MEXT code: **{stats['with_code']}**")
        st.write(f"- Excluded (no code needed): **{stats['excluded']}**")
        st.write(f"- Still unresolved: **{stats['unresolved']}**")
        st.write(f"- Review approved: **{stats['approved']}**")
        st.write(f"- Review rejected: **{stats['rejected']}**")


def _render_review_item(session: Session, item: ReviewItem, idx: int) -> bool:
    """Render a single review item card. Returns True if an action was taken."""
    school = _load_school(session, item.reference_id) if item.reference_id else None
    if school is None:
        st.warning(f"School id={item.reference_id} not found. Skipping review item {item.id}.")
        return False

    # Parse proposal
    proposal: dict[str, str | None] = {}
    if item.proposal_value:
        proposal = json.loads(item.proposal_value)

    candidate_code = proposal.get("candidate_code")
    candidate_name = proposal.get("candidate_name")
    match_method = proposal.get("match_method")

    # Confidence color
    confidence = float(item.confidence) if item.confidence is not None else 0.0
    if confidence >= 0.9:
        conf_color = "green"
    elif confidence >= 0.7:
        conf_color = "orange"
    else:
        conf_color = "red"

    with st.container(border=True):
        # Header
        header_cols = st.columns([3, 1, 1])
        header_cols[0].subheader(f"{school.school_name}")
        header_cols[1].write(f"Priority: **{item.priority}**")
        header_cols[2].write(f"Confidence: :{conf_color}[**{confidence:.0%}**]")

        # School details
        detail_cols = st.columns(3)
        detail_cols[0].write(f"Prefecture: **{school.prefecture}**")
        detail_cols[1].write(f"Corporation: **{school.corporation_name}**")
        detail_cols[2].write(f"DB ID: **{school.id}**")

        # AI Proposal
        if candidate_code:
            st.divider()
            st.write("**AI Proposal:**")
            prop_cols = st.columns(3)
            prop_cols[0].write(f"MEXT Code: `{candidate_code}`")
            prop_cols[1].write(f"MEXT Name: {candidate_name or 'N/A'}")
            prop_cols[2].write(f"Method: {match_method or 'N/A'}")

            if item.proposal_reason:
                st.caption(item.proposal_reason)
        else:
            st.divider()
            st.info("No candidate found by the reconciler. Manual code entry required.")
            if item.proposal_reason:
                st.caption(item.proposal_reason)

        # Action buttons
        st.divider()
        action_cols = st.columns([1, 1, 1, 1, 2])

        # Approve (only if there's a candidate)
        if candidate_code:
            if action_cols[0].button(
                "Approve",
                key=f"approve_{item.id}_{idx}",
                type="primary",
            ):
                _approve_item(session, item, school)
                st.success(f"Approved: {school.school_name} -> {candidate_code}")
                return True

        # Reject
        if action_cols[1].button(
            "Reject",
            key=f"reject_{item.id}_{idx}",
        ):
            _reject_item(session, item)
            st.warning(f"Rejected proposal for {school.school_name}")
            return True

        # Skip
        if action_cols[2].button(
            "Skip",
            key=f"skip_{item.id}_{idx}",
        ):
            _skip_item(session, item)
            st.info(f"Skipped {school.school_name} (lowered priority)")
            return True

        # Manual correction
        corrected = action_cols[4].text_input(
            "Manual MEXT code",
            key=f"manual_{item.id}_{idx}",
            placeholder="e.g. 1131001",
            label_visibility="collapsed",
        )
        if action_cols[3].button(
            "Apply Manual",
            key=f"apply_manual_{item.id}_{idx}",
        ):
            if corrected:
                _approve_with_correction(session, item, school, corrected)
                st.success(f"Applied manual code: {school.school_name} -> {corrected}")
                return True
            else:
                st.error("Enter a MEXT code first.")

    return False


# ---------------------------------------------------------------------------
# Page: Review Queue
# ---------------------------------------------------------------------------

def _page_review_queue(session: Session) -> None:
    """Main review queue page."""
    st.header("School Code Review Queue")

    stats = _load_dashboard_stats(session)
    _render_dashboard(stats)

    st.divider()

    if stats["pending_reviews"] == 0:
        st.success("All review items have been processed. No pending items remain.")
        return

    # Filters
    filter_cols = st.columns(3)
    with filter_cols[0]:
        show_only_with_proposal = st.checkbox("Only show items with proposals", value=True)
    with filter_cols[1]:
        min_confidence = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05)
    with filter_cols[2]:
        items_per_page = st.selectbox("Items per page", [5, 10, 20, 50], index=1)

    items = _load_pending_items(session)

    # Apply filters
    if show_only_with_proposal:
        items = [it for it in items if it.proposal_value is not None]
    if min_confidence > 0:
        items = [
            it for it in items
            if it.confidence is not None and float(it.confidence) >= min_confidence
        ]

    if not items:
        st.info("No items match the current filters.")
        return

    st.write(f"Showing {min(items_per_page, len(items))} of {len(items)} pending items")

    # Pagination
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    if total_pages > 1:
        page_cols = st.columns([1, 3, 1])
        if page_cols[0].button("< Prev", disabled=st.session_state.current_page == 0):
            st.session_state.current_page -= 1
            st.rerun()
        page_cols[1].write(
            f"Page {st.session_state.current_page + 1} / {total_pages}"
        )
        if page_cols[2].button("Next >", disabled=st.session_state.current_page >= total_pages - 1):
            st.session_state.current_page += 1
            st.rerun()

    start = st.session_state.current_page * items_per_page
    end = start + items_per_page
    page_items = items[start:end]

    for idx, item in enumerate(page_items):
        acted = _render_review_item(session, item, start + idx)
        if acted:
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Resolved History
# ---------------------------------------------------------------------------

def _page_history(session: Session) -> None:
    """Show resolved review items."""
    st.header("Resolution History")

    resolved_items = (
        session.query(ReviewItem)
        .filter(ReviewItem.item_type == "school_code", ReviewItem.status == "resolved")
        .order_by(ReviewItem.resolved_at.desc().nullslast())
        .limit(100)
        .all()
    )

    if not resolved_items:
        st.info("No resolved items yet.")
        return

    st.write(f"Showing latest {len(resolved_items)} resolved items")

    for item in resolved_items:
        school = _load_school(session, item.reference_id) if item.reference_id else None
        school_name = school.school_name if school else f"(id={item.reference_id})"
        school_code = school.school_code if school else "N/A"

        resolution_label = item.resolution or "unknown"
        if resolution_label == "approved":
            badge = ":green[APPROVED]"
        elif resolution_label == "rejected":
            badge = ":red[REJECTED]"
        elif resolution_label == "corrected":
            badge = ":blue[CORRECTED]"
        else:
            badge = f":gray[{resolution_label.upper()}]"

        resolved_at_str = item.resolved_at.strftime("%Y-%m-%d %H:%M") if item.resolved_at else "N/A"

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            cols[0].write(f"**{school_name}**")
            cols[1].write(badge)
            cols[2].write(f"Code: `{item.resolved_value or school_code}`")
            cols[3].write(f"{resolved_at_str}")

            if item.notes:
                st.caption(f"Notes: {item.notes}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="EIDP Operator Console",
        page_icon=":material/school:",
        layout="wide",
    )
    st.title("EIDP Operator Console")

    session = _get_session()

    page = st.sidebar.radio(
        "メニュー",
        [
            "① データ状況",
            "② マッチング提案の確認",
            "③ URL追加",
            "④ Excel出力",
            "⑤ マッチング漏れ一覧",
            "⑥ 除外PDF履歴",
            "⑦ 学校コード確認",
            "⑧ 処理履歴",
        ],
        index=0,
    )

    if page == "① データ状況":
        operator_pages.page_pipeline_status(session)
    elif page == "② マッチング提案の確認":
        operator_pages.page_proposals_review(session)
    elif page == "③ URL追加":
        operator_pages.page_url_submission(session)
    elif page == "④ Excel出力":
        operator_pages.page_exports(session)
    elif page == "⑤ マッチング漏れ一覧":
        operator_pages.page_gap_report()
    elif page == "⑥ 除外PDF履歴":
        operator_pages.page_rejections()
    elif page == "⑦ 学校コード確認":
        _page_review_queue(session)
    elif page == "⑧ 処理履歴":
        _page_history(session)

    # Sidebar info
    st.sidebar.divider()
    st.sidebar.caption("週次運用フロー")
    st.sidebar.caption(
        "① 状況確認 → ② 提案承認 → ③ URL追加 → ④ Excel出力 → ⑤ 漏れ確認"
    )


if __name__ == "__main__":
    main()
