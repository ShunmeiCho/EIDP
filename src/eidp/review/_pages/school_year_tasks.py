"""Streamlit page: school x target fiscal-year task board.

This page is the operator-facing replacement for a raw PDF document queue.
It renders one row per school for the configured target fiscal year and tells
the operator the next concrete action.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class BootstrapLaunchResult:
    started: bool
    message: str
    log_path: Path | None = None
    progress_path: Path | None = None
    pid: int | None = None


@dataclass(frozen=True)
class BootstrapProgress:
    status: str
    current_step: int
    total_steps: int
    percent: float
    message: str
    started_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    log_path: str | None = None
    error: str | None = None


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


def needs_initial_url_bootstrap(summary: SchoolTaskSummary) -> bool:
    """Return True when setup has schools but no known crawl URLs yet."""
    return summary.total > 0 and summary.no_url == summary.total


def latest_bootstrap_log(app_root: Path) -> Path | None:
    logs_dir = app_root / "logs"
    if not logs_dir.is_dir():
        return None
    logs = sorted(logs_dir.glob("bootstrap-pdfs-*.log"), key=lambda path: path.stat().st_mtime)
    return logs[-1] if logs else None


def latest_bootstrap_progress_path(app_root: Path) -> Path | None:
    logs_dir = app_root / "logs"
    if not logs_dir.is_dir():
        return None
    progress_files = sorted(logs_dir.glob("bootstrap-pdfs-*.json"), key=lambda path: path.stat().st_mtime)
    return progress_files[-1] if progress_files else None


def _float_or_default(value: object, default: float) -> float:
    if not isinstance(value, int | float | str | bytes | bytearray):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_or_default(value: object, default: int) -> int:
    if not isinstance(value, int | float | str | bytes | bytearray):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def bootstrap_progress_from_payload(payload: dict[str, Any]) -> BootstrapProgress:
    total_steps = max(_int_or_default(payload.get("total_steps"), 5), 1)
    current_step = max(_int_or_default(payload.get("current_step"), 0), 0)
    default_percent = min(current_step / total_steps, 1.0)
    percent = min(max(_float_or_default(payload.get("percent"), default_percent), 0.0), 1.0)
    return BootstrapProgress(
        status=str(payload.get("status") or "unknown"),
        current_step=min(current_step, total_steps),
        total_steps=total_steps,
        percent=percent,
        message=str(payload.get("message") or "進行状況を確認中"),
        started_at=str(payload["started_at"]) if payload.get("started_at") else None,
        updated_at=str(payload["updated_at"]) if payload.get("updated_at") else None,
        completed_at=str(payload["completed_at"]) if payload.get("completed_at") else None,
        log_path=str(payload["log_path"]) if payload.get("log_path") else None,
        error=str(payload["error"]) if payload.get("error") else None,
    )


def read_bootstrap_progress(path: Path) -> BootstrapProgress | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return bootstrap_progress_from_payload(payload)


def latest_bootstrap_progress(app_root: Path) -> BootstrapProgress | None:
    path = latest_bootstrap_progress_path(app_root)
    if path is None:
        return None
    return read_bootstrap_progress(path)


def _write_initial_bootstrap_progress(*, progress_path: Path, log_path: Path, started_at: datetime) -> None:
    payload = {
        "status": "running",
        "current_step": 0,
        "total_steps": 5,
        "percent": 0.0,
        "message": "初回取得を準備中です。",
        "started_at": started_at.isoformat(timespec="seconds"),
        "updated_at": started_at.isoformat(timespec="seconds"),
        "log_path": str(log_path),
    }
    tmp_path = progress_path.with_suffix(progress_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(progress_path)


def _write_failed_bootstrap_progress(
    *,
    progress_path: Path,
    log_path: Path,
    started_at: datetime,
    message: str,
) -> None:
    now = datetime.now()
    payload = {
        "status": "failed",
        "current_step": 0,
        "total_steps": 5,
        "percent": 0.0,
        "message": message,
        "started_at": started_at.isoformat(timespec="seconds"),
        "updated_at": now.isoformat(timespec="seconds"),
        "completed_at": now.isoformat(timespec="seconds"),
        "log_path": str(log_path),
        "error": message,
    }
    tmp_path = progress_path.with_suffix(progress_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(progress_path)


def bootstrap_command(
    app_root: Path,
    *,
    lock_path: Path,
    progress_path: Path | None = None,
    python_executable: str | None = None,
) -> list[str]:
    cmd = [
        python_executable or sys.executable,
        str(app_root / "scripts" / "bootstrap_pdf_pipeline.py"),
        "--lock-path",
        str(lock_path),
    ]
    if progress_path is not None:
        cmd.extend(["--progress-file", str(progress_path)])
    return cmd


def start_initial_url_bootstrap(
    app_root: Path,
    *,
    lock_path: Path,
    python_executable: str | None = None,
    now: datetime | None = None,
) -> BootstrapLaunchResult:
    """Start the online URL/PDF bootstrap in the background from the UI."""
    lock_status = probe_lock(lock_path)
    if lock_status.held:
        return BootstrapLaunchResult(
            started=False,
            message=f"別の処理が実行中です。完了後にもう一度開始してください。owner={lock_status.owner}",
        )

    script = app_root / "scripts" / "bootstrap_pdf_pipeline.py"
    if not script.is_file():
        return BootstrapLaunchResult(
            started=False,
            message="初回取得プログラムが見つかりません。ZIPをもう一度展開してください。",
        )

    logs_dir = app_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    started_at = now or datetime.now()
    log_path = logs_dir / f"bootstrap-pdfs-{started_at.strftime('%Y%m%d-%H%M%S')}.log"
    progress_path = log_path.with_suffix(".json")
    _write_initial_bootstrap_progress(progress_path=progress_path, log_path=log_path, started_at=started_at)

    env = os.environ.copy()
    env["EIDP_APP_ROOT"] = str(app_root)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = bootstrap_command(
        app_root,
        lock_path=lock_path,
        progress_path=progress_path,
        python_executable=python_executable,
    )

    try:
        with log_path.open("ab") as stream:
            if sys.platform == "win32":  # pragma: no cover - covered by Windows VM E2E
                proc = subprocess.Popen(  # noqa: S603 - command is built from bundled app paths only.
                    cmd,
                    cwd=app_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                proc = subprocess.Popen(  # noqa: S603 - command is built from bundled app paths only.
                    cmd,
                    cwd=app_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
    except OSError as exc:
        message = f"初回取得を開始できませんでした: {exc}"
        _write_failed_bootstrap_progress(
            progress_path=progress_path,
            log_path=log_path,
            started_at=started_at,
            message=message,
        )
        return BootstrapLaunchResult(
            started=False,
            message=message,
            log_path=log_path,
            progress_path=progress_path,
        )
    return BootstrapLaunchResult(
        started=True,
        message="初回URL/PDF取得を開始しました。完了後、この画面を更新してください。",
        log_path=log_path,
        progress_path=progress_path,
        pid=proc.pid,
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


def _render_bootstrap_progress(progress: BootstrapProgress) -> None:
    import streamlit as st

    percent_label = f"{progress.percent:.0%}"
    step_label = f"{progress.current_step}/{progress.total_steps}"
    text = f"{percent_label}  {progress.message}（{step_label}）"
    st.progress(progress.percent, text=text)

    if progress.status == "succeeded":
        st.success("初回URL/PDF取得が完了しました。この画面を更新すると最新の学校別タスクを確認できます。")
    elif progress.status == "failed":
        st.error(progress.message)
        if progress.error:
            st.caption(f"エラー詳細: {progress.error}")
    elif progress.status == "running":
        st.info("初回URL/PDF取得を実行中です。数分おきに進行状況を更新してください。")
    else:
        st.info(progress.message)

    meta = []
    if progress.started_at:
        meta.append(f"開始: {progress.started_at}")
    if progress.updated_at:
        meta.append(f"更新: {progress.updated_at}")
    if progress.completed_at:
        meta.append(f"完了: {progress.completed_at}")
    if meta:
        st.caption(" / ".join(meta))
    if progress.log_path:
        st.caption(f"診断ログ: {progress.log_path}")
    key_suffix = progress.started_at or progress.updated_at or progress.message
    if st.button("進行状況を更新", key=f"bootstrap_progress_refresh_{key_suffix}"):
        st.rerun()


def _render_initial_bootstrap_controls(summary: SchoolTaskSummary, *, lock_path: Path) -> None:
    import streamlit as st

    from eidp.config import settings

    app_root = settings.app_root
    st.warning(
        "まだ学校URLの初期取得が終わっていません。"
        f"{summary.total}校を手作業で追加する状態ではありません。"
        "下のボタンから初回取得を開始すると、都道府県の公開データから学校URLを登録し、"
        "対象年度PDFの探索を開始します。"
    )
    st.caption("初回取得はオンライン処理です。学校数が多いため、数十分かかることがあります。")

    latest_progress = latest_bootstrap_progress(app_root)
    if latest_progress is not None:
        _render_bootstrap_progress(latest_progress)

    latest_log = latest_bootstrap_log(app_root)
    if latest_log is not None and (latest_progress is None or latest_progress.log_path != str(latest_log)):
        st.caption(f"最新の初回取得ログ: {latest_log}")

    lock_status = probe_lock(lock_path)
    if st.button(
        "初回URL/PDF取得を開始",
        type="primary",
        disabled=lock_status.held,
    ):
        result = start_initial_url_bootstrap(app_root, lock_path=lock_path)
        if result.started:
            st.success(result.message)
            if result.log_path is not None:
                st.caption(f"進行状況ログ: {result.log_path}")
            if result.progress_path is not None:
                progress = read_bootstrap_progress(result.progress_path)
                if progress is not None:
                    _render_bootstrap_progress(progress)
        else:
            st.warning(result.message)


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin Streamlit shell
    import streamlit as st

    from eidp.config import settings
    from eidp.fiscal_year import format_fiscal_year_label

    fiscal_year = settings.target_fiscal_year
    school_type = "専門学校"
    target_label = format_fiscal_year_label(fiscal_year)

    st.header("① 学校別タスク")
    st.caption(f"{target_label} の学校ごとの進捗です。旧年度PDFは成果に含めず、次に何をするかだけを確認します。")

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

    if needs_initial_url_bootstrap(summary):
        _render_initial_bootstrap_controls(summary, lock_path=lock_path)

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
