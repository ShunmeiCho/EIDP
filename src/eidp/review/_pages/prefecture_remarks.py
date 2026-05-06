"""Streamlit page: official prefecture index remark review.

Prefecture official 確認大学等 indexes are authoritative annual evidence for
school-universe changes. This page keeps that evidence separate from the PDF
manual-entry queue so operators do not have to infer school changes from PDF
rows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock
from eidp.db.models import ReviewItem, School


@dataclass(frozen=True)
class PrefectureRemarkReviewRow:
    item_id: int
    school_id: int
    prefecture: str
    school_name: str
    school_type: str | None
    tags: tuple[str, ...]
    remarks: str
    evidence_url: str | None
    status: str
    resolution: str | None
    notes: str | None
    created_at: datetime | None
    resolved_at: datetime | None


SCHOOL_TYPE_FILTER_LABELS = ("すべて", "専門学校", "大学")
STATUS_FILTER_LABELS = ("未対応", "解決済", "すべて")

PREFECTURE_REMARK_TAG_LABELS: dict[str, str] = {
    "new_accreditation": "新規認定",
    "name_change": "名称変更",
    "withdrawal": "辞退/取消/対象外",
    "merger_reorg": "統合/再編",
}

RESOLUTION_LABELS: dict[str, str] = {
    "approved": "確認済",
    "rejected": "対象外",
}


def school_type_from_filter_label(label: str) -> str | None:
    return None if label == "すべて" else label


def status_from_filter_label(label: str) -> str | None:
    if label == "未対応":
        return "pending"
    if label == "解決済":
        return "resolved"
    return None


def prefecture_remark_tag_label(tag: str) -> str:
    return PREFECTURE_REMARK_TAG_LABELS.get(tag, tag)


def parse_prefecture_remark_payload(raw: str | None) -> tuple[tuple[str, ...], str]:
    """Parse ReviewItem.proposal_value for prefecture remark review rows."""
    if not raw:
        return (), ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return (), raw
    if not isinstance(payload, dict):
        return (), raw

    tags: tuple[str, ...] = ()
    raw_tags = payload.get("tags")
    if isinstance(raw_tags, list):
        tags = tuple(str(tag) for tag in raw_tags if tag)
    return tags, str(payload.get("remarks") or "")


def count_pending_prefecture_remark_reviews(
    session: Session,
    *,
    school_type: str | None = "専門学校",
) -> int:
    q = (
        session.query(func.count(ReviewItem.id))
        .join(
            School,
            (ReviewItem.reference_table == "school")
            & (ReviewItem.reference_id == School.id),
        )
        .filter(
            ReviewItem.item_type == "prefecture_remark",
            ReviewItem.status == "pending",
            School.status == "active",
        )
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    return int(q.scalar() or 0)


def list_prefecture_remark_reviews(
    session: Session,
    *,
    school_type: str | None = "専門学校",
    status: str | None = "pending",
    limit: int = 50,
) -> list[PrefectureRemarkReviewRow]:
    """List official-index school-change signals."""
    q = (
        session.query(ReviewItem, School)
        .join(
            School,
            (ReviewItem.reference_table == "school")
            & (ReviewItem.reference_id == School.id),
        )
        .filter(
            ReviewItem.item_type == "prefecture_remark",
            School.status == "active",
        )
    )
    if status is not None:
        q = q.filter(ReviewItem.status == status)
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    q = q.order_by(ReviewItem.priority.asc(), ReviewItem.created_at.asc()).limit(limit)

    rows: list[PrefectureRemarkReviewRow] = []
    for item, school in q.all():
        tags, remarks = parse_prefecture_remark_payload(item.proposal_value)
        rows.append(PrefectureRemarkReviewRow(
            item_id=item.id,
            school_id=school.id,
            prefecture=school.prefecture,
            school_name=school.school_name,
            school_type=school.school_type,
            tags=tags,
            remarks=remarks,
            evidence_url=item.evidence_url,
            status=item.status,
            resolution=item.resolution,
            notes=item.notes,
            created_at=item.created_at,
            resolved_at=item.resolved_at,
        ))
    return rows


def resolve_prefecture_remark_review(
    session: Session,
    *,
    item_id: int,
    resolution: str,
    notes: str = "",
) -> bool:
    """Close a pending prefecture remark review item."""
    if resolution not in RESOLUTION_LABELS:
        raise ValueError(f"unsupported prefecture remark resolution: {resolution}")
    item = (
        session.query(ReviewItem)
        .filter(
            ReviewItem.id == item_id,
            ReviewItem.item_type == "prefecture_remark",
            ReviewItem.status == "pending",
        )
        .one_or_none()
    )
    if item is None:
        return False

    item.status = "resolved"
    item.resolution = resolution
    item.resolved_at = datetime.now(UTC)
    item.notes = notes or None
    return True


def _tag_text(tags: tuple[str, ...]) -> str:
    return " / ".join(prefecture_remark_tag_label(tag) for tag in tags)


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - Streamlit shell
    import streamlit as st

    st.header("都道府県公式インデックス")
    st.caption(
        "確認大学等一覧の備考欄から、新規認定・名称変更・辞退/取消・統合再編の信号を確認します。"
    )

    c1, c2 = st.columns([1, 1])
    school_type_label = c1.selectbox("対象", SCHOOL_TYPE_FILTER_LABELS, index=0)
    status_label = c2.radio("状態", STATUS_FILTER_LABELS, horizontal=True)
    school_type = school_type_from_filter_label(school_type_label)
    status = status_from_filter_label(status_label)

    pending_count = count_pending_prefecture_remark_reviews(session, school_type=school_type)
    st.metric("未対応の公式備考", pending_count)

    rows = list_prefecture_remark_reviews(session, school_type=school_type, status=status)
    if not rows:
        st.info("この条件の備考レビューはありません。")
        return

    st.dataframe(
        [
            {
                "状態": (
                    "未対応"
                    if row.status == "pending"
                    else RESOLUTION_LABELS.get(row.resolution or "", row.status)
                ),
                "都道府県": row.prefecture,
                "学校": row.school_name,
                "信号": _tag_text(row.tags),
                "備考": row.remarks,
                "学校ID": row.school_id,
            }
            for row in rows
        ],
        hide_index=True,
        use_container_width=True,
    )

    if status == "resolved":
        return

    st.subheader("備考詳細")
    for row in rows[:20]:
        title = f"{row.prefecture} / {row.school_name} / {row.remarks or _tag_text(row.tags)}"
        with st.expander(title):
            if row.tags:
                st.write({"信号": _tag_text(row.tags)})
            if row.evidence_url:
                st.caption(f"都道府県一覧: {row.evidence_url}")
            note = st.text_input("確認メモ", key=f"prefecture_remark_note_{row.item_id}")
            c1, c2 = st.columns(2)
            if c1.button("確認済みにする", key=f"prefecture_remark_approve_{row.item_id}"):
                try:
                    with acquire_lock(lock_path, owner="ui_prefecture_remark_review"):
                        resolve_prefecture_remark_review(
                            session,
                            item_id=row.item_id,
                            resolution="approved",
                            notes=note,
                        )
                        session.commit()
                    st.success("確認済みにしました。")
                    st.rerun()
                except LockBusyError as exc:
                    session.rollback()
                    st.warning(str(exc))
            if c2.button("対象外として閉じる", key=f"prefecture_remark_reject_{row.item_id}"):
                try:
                    with acquire_lock(lock_path, owner="ui_prefecture_remark_review"):
                        resolve_prefecture_remark_review(
                            session,
                            item_id=row.item_id,
                            resolution="rejected",
                            notes=note,
                        )
                        session.commit()
                    st.success("対象外として閉じました。")
                    st.rerun()
                except LockBusyError as exc:
                    session.rollback()
                    st.warning(str(exc))
