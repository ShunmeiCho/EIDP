"""Streamlit page: school x target fiscal-year task board.

This page is the operator-facing replacement for a raw PDF document queue.
It renders one row per school for the configured target fiscal year and tells
the operator the next concrete action.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Document, School, SchoolFiscalYearStatus, SchoolSite


@dataclass(frozen=True)
class SchoolTaskSummary:
    fiscal_year: int
    school_type: str | None
    total: int
    excel_ready: int
    confirmed_target: int
    stale_fallback: int
    no_url: int
    review_or_parse: int
    dept_change_review: int

    @property
    def needs_action(self) -> int:
        return max(self.total - self.excel_ready, 0)


@dataclass(frozen=True)
class SchoolTaskRow:
    school_id: int
    prefecture: str
    school_name: str
    fiscal_year: int
    url_status: str
    pdf_status: str
    extract_status: str
    yoy_diff_status: str
    evidence_level: str
    excel_ready: bool
    blocking_reason: str | None
    next_action: str
    action_hint: str
    latest_document_id: int | None
    latest_document_fiscal_year: int | None
    latest_document_status: str | None
    latest_document_url: str | None
    latest_site_url: str | None


REVIEW_OR_PARSE_BLOCKERS = {"ocr_pending", "parse_failed", "not_extracted", "review_required"}


def next_action_for_status(status: SchoolFiscalYearStatus) -> tuple[str, str]:
    """Map denormalized status into operator language."""
    if status.excel_ready:
        return "Excel出力可", "Excel プレビューで出力前確認"

    if status.yoy_diff_status == "identical_to_prev_fy":
        return "前年差分確認", "前年と同じ数値です。PDF年度と更新有無を確認"

    reason = status.blocking_reason
    if reason == "no_url":
        return "URL追加", "学校または法人の情報公開ページを登録"
    if reason == "no_target_pdf":
        return "PDF探索", "週次再取得、または見つけたPDF URLを追加"
    if reason == "stale_pdf_only":
        return "公示待ち/再取得", "旧年度PDFは成果扱いせず、対象年度PDFを再確認"
    if reason == "ocr_pending":
        return "OCR/手入力", "画像PDFのOCR可否を確認し、必要なら手入力"
    if reason == "parse_failed":
        return "手入力", "PDFを開いて学科別数値を入力"
    if reason == "dept_change_review":
        return "学科変更確認", "新設/廃科/名称変更/統合または別名候補を確認"
    if reason in {"not_extracted", "review_required"}:
        return "PDF確認", "抽出結果とPDF原本を確認"
    return "確認", "状態を確認"


def school_task_summary(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
) -> SchoolTaskSummary:
    q = (
        session.query(
            SchoolFiscalYearStatus.pdf_status,
            SchoolFiscalYearStatus.extract_status,
            SchoolFiscalYearStatus.excel_ready,
            SchoolFiscalYearStatus.blocking_reason,
            func.count(SchoolFiscalYearStatus.school_id),
        )
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(SchoolFiscalYearStatus.fiscal_year == fiscal_year)
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)

    total = 0
    excel_ready = 0
    confirmed_target = 0
    stale_fallback = 0
    no_url = 0
    review_or_parse = 0
    dept_change_review = 0
    for pdf_status, extract_status, ready, blocker, n in q.group_by(
        SchoolFiscalYearStatus.pdf_status,
        SchoolFiscalYearStatus.extract_status,
        SchoolFiscalYearStatus.excel_ready,
        SchoolFiscalYearStatus.blocking_reason,
    ):
        count = int(n or 0)
        total += count
        if ready:
            excel_ready += count
        if pdf_status == "confirmed_target":
            confirmed_target += count
        if blocker == "stale_pdf_only":
            stale_fallback += count
        if blocker == "no_url":
            no_url += count
        if blocker == "dept_change_review":
            dept_change_review += count
        if blocker in REVIEW_OR_PARSE_BLOCKERS or extract_status in {"ocr_pending", "parse_failed"}:
            review_or_parse += count

    return SchoolTaskSummary(
        fiscal_year=fiscal_year,
        school_type=school_type,
        total=total,
        excel_ready=excel_ready,
        confirmed_target=confirmed_target,
        stale_fallback=stale_fallback,
        no_url=no_url,
        review_or_parse=review_or_parse,
        dept_change_review=dept_change_review,
    )


def list_school_year_tasks(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
    scope: str = "needs_action",
    blocking_reason: str | None = None,
    prefecture: str | None = None,
    search: str = "",
    limit: int = 500,
) -> list[SchoolTaskRow]:
    """Return task rows for the target fiscal-year board."""
    q = (
        session.query(SchoolFiscalYearStatus, School)
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(SchoolFiscalYearStatus.fiscal_year == fiscal_year)
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    if scope == "needs_action":
        q = q.filter(SchoolFiscalYearStatus.excel_ready.is_(False))
    elif scope == "excel_ready":
        q = q.filter(SchoolFiscalYearStatus.excel_ready.is_(True))
    if blocking_reason:
        q = q.filter(SchoolFiscalYearStatus.blocking_reason == blocking_reason)
    if prefecture:
        q = q.filter(School.prefecture == prefecture)
    search_text = search.strip()
    if search_text:
        q = q.filter(School.school_name.contains(search_text))

    pairs = (
        q.order_by(
            SchoolFiscalYearStatus.excel_ready.asc(),
            SchoolFiscalYearStatus.blocking_reason.asc().nullslast(),
            School.prefecture.asc(),
            School.school_name.asc(),
        )
        .limit(limit)
        .all()
    )
    school_ids = [int(school.id) for _status, school in pairs]
    docs_by_school = _latest_documents_by_school(session, school_ids)
    sites_by_school = _latest_sites_by_school(session, school_ids)

    rows: list[SchoolTaskRow] = []
    for status, school in pairs:
        action, hint = next_action_for_status(status)
        doc = docs_by_school.get(school.id)
        site = sites_by_school.get(school.id)
        rows.append(
            SchoolTaskRow(
                school_id=school.id,
                prefecture=school.prefecture,
                school_name=school.school_name,
                fiscal_year=status.fiscal_year,
                url_status=status.url_status,
                pdf_status=status.pdf_status,
                extract_status=status.extract_status,
                yoy_diff_status=status.yoy_diff_status,
                evidence_level=status.evidence_level,
                excel_ready=bool(status.excel_ready),
                blocking_reason=status.blocking_reason,
                next_action=action,
                action_hint=hint,
                latest_document_id=doc.id if doc else None,
                latest_document_fiscal_year=doc.fiscal_year if doc else None,
                latest_document_status=doc.ingest_status if doc else None,
                latest_document_url=doc.source_url if doc else None,
                latest_site_url=site.url if site else None,
            )
        )
    return rows


def _latest_documents_by_school(session: Session, school_ids: list[int]) -> dict[int, Document]:
    if not school_ids:
        return {}
    latest_doc_ids = [
        int(doc_id)
        for (doc_id,) in (
            session.query(func.max(Document.id))
            .filter(Document.school_id.in_(school_ids), Document.pdf_type == "target")
            .group_by(Document.school_id)
            .all()
        )
        if doc_id is not None
    ]
    if not latest_doc_ids:
        return {}
    docs = session.query(Document).filter(Document.id.in_(latest_doc_ids)).all()
    return {doc.school_id: doc for doc in docs}


def _latest_sites_by_school(session: Session, school_ids: list[int]) -> dict[int, SchoolSite]:
    if not school_ids:
        return {}
    latest_site_ids = [
        int(site_id)
        for (site_id,) in (
            session.query(func.max(SchoolSite.id))
            .filter(SchoolSite.school_id.in_(school_ids))
            .group_by(SchoolSite.school_id)
            .all()
        )
        if site_id is not None
    ]
    if not latest_site_ids:
        return {}
    sites = session.query(SchoolSite).filter(SchoolSite.id.in_(latest_site_ids)).all()
    return {site.school_id: site for site in sites}


def _prefecture_options(session: Session, *, fiscal_year: int, school_type: str | None) -> list[str]:
    q = (
        session.query(School.prefecture)
        .join(SchoolFiscalYearStatus, SchoolFiscalYearStatus.school_id == School.id)
        .filter(SchoolFiscalYearStatus.fiscal_year == fiscal_year)
        .distinct()
        .order_by(School.prefecture.asc())
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    return [str(pref) for (pref,) in q.all() if pref]


def _blocking_reason_options(session: Session, *, fiscal_year: int, school_type: str | None) -> list[str]:
    q = (
        session.query(SchoolFiscalYearStatus.blocking_reason)
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(
            SchoolFiscalYearStatus.fiscal_year == fiscal_year,
            SchoolFiscalYearStatus.blocking_reason.is_not(None),
        )
        .distinct()
        .order_by(SchoolFiscalYearStatus.blocking_reason.asc())
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    return [str(reason) for (reason,) in q.all() if reason]


def _render_rebuild_button(session: Session, *, fiscal_year: int, school_type: str | None, lock_path: Path) -> None:
    import streamlit as st

    if st.button("年度タスクを再計算", type="primary"):
        from eidp.pipeline.school_fiscal_year_status import rebuild_school_fiscal_year_status

        try:
            with acquire_lock(lock_path, owner="school_year_tasks"):
                stats = rebuild_school_fiscal_year_status(
                    session,
                    fiscal_year=fiscal_year,
                    school_type=school_type,
                )
                session.commit()
        except LockBusyError as exc:
            st.warning(f"週次処理中のため再計算できません: {exc}")
        except Exception:
            session.rollback()
            raise
        else:
            st.success(f"再計算しました: {stats.rebuilt} 校 / Excel出力可 {stats.excel_ready} 校")
            st.rerun()


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin Streamlit shell
    import streamlit as st

    from eidp.config import settings
    from eidp.fiscal_year import format_fiscal_year_label

    fiscal_year = settings.target_fiscal_year
    school_type = "専門学校"
    target_label = format_fiscal_year_label(fiscal_year)

    st.header("① 学校別タスク")
    st.caption(
        f"{target_label} の学校ごとの進捗です。旧年度PDFは成果に含めず、"
        "次に何をするかだけを確認します。"
    )

    lock_status = probe_lock(lock_path)
    if lock_status.held:
        st.warning(
            f"週次処理中、再計算と編集は一時停止しています "
            f"(owner={lock_status.owner}, started_at={lock_status.started_at})"
        )

    summary = school_task_summary(session, fiscal_year=fiscal_year, school_type=school_type)
    if summary.total == 0:
        st.warning("学校別年度タスクがまだ作成されていません。初回は再計算してください。")
        _render_rebuild_button(session, fiscal_year=fiscal_year, school_type=school_type, lock_path=lock_path)
        return

    cols = st.columns(6)
    cols[0].metric("対象校", summary.total)
    cols[1].metric("要対応", summary.needs_action)
    cols[2].metric("Excel出力可", summary.excel_ready)
    cols[3].metric("旧年度fallback", summary.stale_fallback)
    cols[4].metric("URLなし", summary.no_url)
    cols[5].metric("学科変更", summary.dept_change_review)

    _render_rebuild_button(session, fiscal_year=fiscal_year, school_type=school_type, lock_path=lock_path)

    st.divider()
    c1, c2, c3, c4 = st.columns([1.2, 1.4, 1.4, 2])
    scope_label = c1.radio("表示", ["要対応", "Excel出力可", "全校"], horizontal=True)
    scope = {"要対応": "needs_action", "Excel出力可": "excel_ready", "全校": "all"}[scope_label]

    reasons = ["すべて", *_blocking_reason_options(session, fiscal_year=fiscal_year, school_type=school_type)]
    reason_label = c2.selectbox("理由", reasons)
    blocking_reason = None if reason_label == "すべて" else reason_label

    prefectures = ["すべて", *_prefecture_options(session, fiscal_year=fiscal_year, school_type=school_type)]
    pref_label = c3.selectbox("都道府県", prefectures)
    prefecture = None if pref_label == "すべて" else pref_label

    search = c4.text_input("学校名検索", "")

    rows = list_school_year_tasks(
        session,
        fiscal_year=fiscal_year,
        school_type=school_type,
        scope=scope,
        blocking_reason=blocking_reason,
        prefecture=prefecture,
        search=search,
    )
    st.caption(f"表示 {len(rows)} 件")
    if not rows:
        st.info("この条件の学校はありません。")
        return

    table = [
        {
            "次の作業": row.next_action,
            "都道府県": row.prefecture,
            "学校": row.school_name,
            "理由": row.blocking_reason or "",
            "PDF": row.pdf_status,
            "抽出": row.extract_status,
            "証拠": row.evidence_level,
            "最新PDF年度": row.latest_document_fiscal_year,
            "学校ID": row.school_id,
        }
        for row in rows
    ]
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.subheader("上位タスク詳細")
    for row in rows[:25]:
        title = f"{row.next_action} / {row.prefecture} / {row.school_name} / id={row.school_id}"
        with st.expander(title):
            st.write(row.action_hint)
            st.write(
                {
                    "url_status": row.url_status,
                    "pdf_status": row.pdf_status,
                    "extract_status": row.extract_status,
                    "yoy_diff_status": row.yoy_diff_status,
                    "evidence_level": row.evidence_level,
                    "blocking_reason": row.blocking_reason,
                }
            )
            if row.latest_site_url:
                st.caption(f"最新URL: {row.latest_site_url}")
            if row.latest_document_url:
                st.caption(
                    f"最新PDF: doc#{row.latest_document_id} / fy={row.latest_document_fiscal_year} / "
                    f"{row.latest_document_status} / {row.latest_document_url}"
                )
