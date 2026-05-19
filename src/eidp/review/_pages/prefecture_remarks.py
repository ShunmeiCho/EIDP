"""Streamlit page: official prefecture index remark review.

Prefecture official 確認大学等 indexes are authoritative annual evidence for
school-universe changes. This page keeps that evidence separate from the PDF
manual-entry queue so operators do not have to infer school changes from PDF
rows.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.locking import LockBusyError, acquire_lock
from eidp.db.models import ManualActionLog, ReviewItem, School
from eidp.scraper.prefecture_aggregator import PARSERS


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


@dataclass(frozen=True)
class PrefectureSeedCoverageRow:
    pref_key: str
    prefecture: str
    schools_in_db: int | None
    status: str
    parser_supported: bool
    automatic_target: bool
    school_link_signal: bool
    supplemental_artifacts: int
    as_of_date: str
    artifact_url: str
    notes: str


@dataclass(frozen=True)
class PrefectureSeedCoverageSummary:
    total: int
    automatic_targets: int
    parser_supported: int
    needs_structure_review: int
    school_link_signal: int
    no_school_link_signal: int
    known_school_total: int
    automatic_target_schools: int
    parser_unsupported_schools: int
    structure_review_schools: int
    url_review_schools: int
    no_school_link_signal_schools: int
    unknown_school_rows: int
    supplemental_artifact_rows: int


SCHOOL_TYPE_FILTER_LABELS = ("すべて", "専門学校", "大学")
STATUS_FILTER_LABELS = ("未対応", "解決済", "すべて")
DOWNLOADABLE_SEED_STATUSES = frozenset({"spiked", "downloaded", "url_found"})
SUPPORTED_PREFECTURE_PARSERS = frozenset(PARSERS)

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


def _truthy_seed_value(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return bool(normalized) and normalized not in {"no", "n/a", "unknown", "tbd", "false", "0"}


def _parse_seed_school_count(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw or raw.lower() == "unknown":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _supplemental_artifact_count(value: str | None) -> int:
    raw = value or ""
    return sum(
        1
        for part in raw.replace("\n", "|").replace(";", "|").split("|")
        if part.strip().startswith("http")
    )


def prefecture_seed_status_label(
    *,
    parser_supported: bool,
    verified_status: str,
    artifact_url: str,
) -> str:
    has_artifact = artifact_url.startswith("http")
    if parser_supported and verified_status in DOWNLOADABLE_SEED_STATUSES and has_artifact:
        return "自動取込対象"
    if verified_status in DOWNLOADABLE_SEED_STATUSES and has_artifact:
        return "parser未対応"
    if verified_status == "todo":
        return "構造確認待ち"
    return "URL確認待ち"


def load_prefecture_seed_coverage(
    seed_csv: Path,
) -> tuple[PrefectureSeedCoverageSummary, list[PrefectureSeedCoverageRow]]:
    """Read prefecture official-index seed coverage for the operator UI."""
    rows: list[PrefectureSeedCoverageRow] = []
    try:
        with seed_csv.open("r", encoding="utf-8") as fh:
            records = list(csv.DictReader(fh))
    except OSError:
        return PrefectureSeedCoverageSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), []

    for record in records:
        pref_key = (record.get("pref_key") or "").strip()
        artifact_url = (record.get("artifact_url") or "").strip()
        verified_status = (record.get("verified_status") or "").strip()
        parser_supported = pref_key in SUPPORTED_PREFECTURE_PARSERS
        automatic_target = (
            parser_supported
            and verified_status in DOWNLOADABLE_SEED_STATUSES
            and artifact_url.startswith("http")
        )
        school_link_signal = _truthy_seed_value(record.get("has_url_col")) or _truthy_seed_value(
            record.get("has_hyperlink_annot")
        )
        supplemental_artifacts = _supplemental_artifact_count(record.get("supplemental_artifact_urls"))
        schools_in_db = _parse_seed_school_count(record.get("schools_in_db"))
        status = prefecture_seed_status_label(
            parser_supported=parser_supported,
            verified_status=verified_status,
            artifact_url=artifact_url,
        )
        rows.append(PrefectureSeedCoverageRow(
            pref_key=pref_key,
            prefecture=(record.get("pref_jp") or pref_key).strip(),
            schools_in_db=schools_in_db,
            status=status,
            parser_supported=parser_supported,
            automatic_target=automatic_target,
            school_link_signal=school_link_signal,
            supplemental_artifacts=supplemental_artifacts,
            as_of_date=(record.get("as_of_date") or "").strip(),
            artifact_url=artifact_url,
            notes=(record.get("notes") or "").strip(),
        ))

    summary = PrefectureSeedCoverageSummary(
        total=len(rows),
        automatic_targets=sum(1 for row in rows if row.automatic_target),
        parser_supported=sum(1 for row in rows if row.parser_supported),
        needs_structure_review=sum(1 for row in rows if not row.automatic_target),
        school_link_signal=sum(1 for row in rows if row.school_link_signal),
        no_school_link_signal=sum(1 for row in rows if not row.school_link_signal),
        known_school_total=sum(row.schools_in_db or 0 for row in rows),
        automatic_target_schools=sum(row.schools_in_db or 0 for row in rows if row.automatic_target),
        parser_unsupported_schools=sum(row.schools_in_db or 0 for row in rows if row.status == "parser未対応"),
        structure_review_schools=sum(row.schools_in_db or 0 for row in rows if row.status == "構造確認待ち"),
        url_review_schools=sum(row.schools_in_db or 0 for row in rows if row.status == "URL確認待ち"),
        no_school_link_signal_schools=sum(row.schools_in_db or 0 for row in rows if not row.school_link_signal),
        unknown_school_rows=sum(1 for row in rows if row.schools_in_db is None),
        supplemental_artifact_rows=sum(1 for row in rows if row.supplemental_artifacts > 0),
    )
    return summary, rows


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
    actor: str = "operator",
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

    old_value: dict[str, object | None] = {
        "status": item.status,
        "resolution": item.resolution,
        "notes": item.notes,
    }
    item.status = "resolved"
    item.resolution = resolution
    item.resolved_at = datetime.now(UTC)
    item.notes = notes or None
    audit_prefecture_remark_resolved(session, item=item, old_value=old_value, actor=actor)
    return True


def audit_prefecture_remark_resolved(
    session: Session,
    *,
    item: ReviewItem,
    old_value: dict[str, object | None],
    actor: str = "operator",
) -> ManualActionLog:
    tags, remarks = parse_prefecture_remark_payload(item.proposal_value)
    return log_manual_action(
        session,
        action_type=f"prefecture_remark_{item.resolution}",
        target_table="review_item",
        target_id=item.id,
        old_value=old_value,
        new_value={
            "item_id": item.id,
            "school_id": item.reference_id,
            "resolution": item.resolution,
            "notes": item.notes,
            "tags": tags,
            "remarks": remarks,
            "evidence_url": item.evidence_url,
        },
        reason=item.notes or "Operator resolved prefecture remark review",
        actor=actor,
    )


def _tag_text(tags: tuple[str, ...]) -> str:
    return " / ".join(prefecture_remark_tag_label(tag) for tag in tags)


def _render_seed_coverage(seed_csv: Path) -> None:  # pragma: no cover - Streamlit shell
    import streamlit as st

    summary, rows = load_prefecture_seed_coverage(seed_csv)
    st.subheader("公式インデックス coverage")
    if summary.total == 0:
        st.warning("都道府県 seed.csv を読み込めません。初回取得の前に配布物を確認してください。")
        return

    cols = st.columns(4)
    cols[0].metric("都道府県 seed", summary.total)
    cols[1].metric("自動取込対象", summary.automatic_targets)
    cols[2].metric("parser対応", summary.parser_supported)
    cols[3].metric("構造確認待ち", summary.needs_structure_review)
    school_cols = st.columns(4)
    school_cols[0].metric("seed内 学校数", summary.known_school_total)
    school_cols[1].metric("自動対象校", summary.automatic_target_schools)
    school_cols[2].metric("URL信号なし校", summary.no_school_link_signal_schools)
    school_cols[3].metric("学校数 unknown", summary.unknown_school_rows)
    signal_cols = st.columns(3)
    signal_cols[0].metric("URL信号あり", summary.school_link_signal)
    signal_cols[1].metric("URL信号なし", summary.no_school_link_signal)
    signal_cols[2].metric("複数公式ファイル", summary.supplemental_artifact_rows)
    if summary.no_school_link_signal:
        st.info(
            "URL信号なしの都道府県は、公式一覧から学校URLを直接登録できない可能性があります。"
            "学校別タスクのURLなし行と補助検索の証跡を確認してください。"
        )
    st.caption(
        "ここは初回URL/PDF取得の入口 coverage です。"
        "自動取込対象は seed URL から公式一覧を取得し、学校名リンクやURL列を解析できます。"
    )
    st.dataframe(
        [
            {
                "都道府県": row.prefecture,
                "学校数": row.schools_in_db if row.schools_in_db is not None else "unknown",
                "状態": row.status,
                "parser": "あり" if row.parser_supported else "なし",
                "学校URL信号": "あり" if row.school_link_signal else "なし",
                "補助公式ファイル": row.supplemental_artifacts,
                "基準日": row.as_of_date,
                "公式一覧": row.artifact_url,
                "メモ": row.notes,
            }
            for row in rows
        ],
        hide_index=True,
        width="stretch",
    )


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - Streamlit shell
    import streamlit as st

    from eidp.config import settings

    st.header("都道府県公式インデックス")
    st.caption(
        "確認大学等一覧から、学校URLの自動取得 coverage と、新規認定・名称変更・辞退/取消・統合再編の"
        "備考信号を確認します。"
    )
    _render_seed_coverage(Path(settings.app_root) / "data" / "prefecture-aggregators" / "seed.csv")
    st.divider()

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
        width="stretch",
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
