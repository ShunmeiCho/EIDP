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
    target_pdf_wait: int
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
    latest_site_url_type: str | None
    latest_site_discovery_method: str | None


@dataclass(frozen=True)
class BootstrapLaunchResult:
    started: bool
    message: str
    log_path: Path | None = None
    progress_path: Path | None = None
    last_run_path: Path | None = None
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


@dataclass(frozen=True)
class TaskLane:
    key: str
    label: str
    count: int
    description: str
    button_label: str
    scope: str
    blocking_reason: str | None = None
    page_id: str | None = None


REVIEW_OR_PARSE_BLOCKERS = {"ocr_pending", "parse_failed", "not_extracted", "review_required"}
SCHOOL_TYPE_FILTER_LABELS = ("すべて", "専門学校", "大学")
URL_SUBMISSION_PAGE_ID = "url"
URL_SUBMISSION_QUERY_STATE_KEY = "url_submission_school_query"
URL_SUBMISSION_SCHOOL_ID_STATE_KEY = "url_submission_school_id"
MANUAL_ENTRY_PAGE_ID = "manual_entry"
MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY = "pdf_manual_entry_document_id"
EXCEL_PREVIEW_PAGE_ID = "excel_preview"
MANUAL_ENTRY_ACTIONS = {"OCR/手入力", "手入力", "PDF確認", "前年差分確認"}
WEEKLY_DISCOVERY_METHODS = ("prefecture_aggregator", "operator_manual")
TASK_SCOPE_STATE_KEY = "school_task_scope_filter"
TASK_REASON_STATE_KEY = "school_task_reason_filter"
TASK_PREFECTURE_STATE_KEY = "school_task_prefecture_filter"
TASK_SEARCH_STATE_KEY = "school_task_search_filter"
TASK_SCOPE_LABELS = ("要対応", "Excel出力可", "全校")
TASK_REASON_ALL_LABEL = "すべて"
TASK_PREFECTURE_ALL_LABEL = "すべて"
TASK_SCOPE_TO_CODE = {"要対応": "needs_action", "Excel出力可": "excel_ready", "全校": "all"}
TASK_CODE_TO_SCOPE_LABEL = {value: key for key, value in TASK_SCOPE_TO_CODE.items()}

BLOCKING_REASON_LABELS: dict[str, str] = {
    "no_url": "URL追加が必要",
    "no_target_pdf": "対象年度PDF待ち",
    "stale_pdf_only": "旧年度PDFのみ",
    "ocr_pending": "OCR/手入力待ち",
    "parse_failed": "手入力待ち",
    "not_extracted": "抽出待ち",
    "review_required": "PDF確認待ち",
    "dept_change_review": "学科変更確認",
}

URL_STATUS_LABELS: dict[str, str] = {
    "no_url": "URLなし",
    "pref_url": "都道府県データ由来URLあり",
    "operator_url": "手動登録URLあり",
    "unknown": "URLあり（種別未確認）",
}

PDF_STATUS_LABELS: dict[str, str] = {
    "none": "PDFなし",
    "confirmed_target": "対象年度PDFあり",
    "rejected_stale": "旧年度PDFのみ",
    "image_pending": "画像PDF/OCR待ち",
    "discovered": "PDF候補あり",
}

EXTRACT_STATUS_LABELS: dict[str, str] = {
    "none": "未抽出",
    "parsed": "抽出済",
    "manual_entered": "手入力済",
    "ocr_pending": "OCR待ち",
    "parse_failed": "抽出失敗",
}

YOY_DIFF_STATUS_LABELS: dict[str, str] = {
    "unchecked": "未比較",
    "new_school": "前年データなし",
    "partial_diff": "前年差分あり",
    "identical_to_prev_fy": "前年と同一",
}

EVIDENCE_LEVEL_LABELS: dict[str, str] = {
    "none": "証拠なし",
    "conflict": "年度矛盾",
    "download_time": "取得日だけ",
    "url_hint": "URL年度ヒント",
    "pdf_text": "PDF本文で確認",
    "prev_year_diff": "前年差分で確認",
    "operator_override": "担当者確認済",
}

SITE_URL_TYPE_LABELS: dict[str, str] = {
    "disclosure_page": "情報公開ページ",
    "disclosure": "情報公開ページ",
    "homepage": "学校/法人ページ",
    "school_page": "学校ページ",
    "direct_pdf": "PDF直リンク",
    "pdf": "PDF直リンク",
}
PDF_SITE_URL_TYPES = {"direct_pdf", "pdf"}


def school_type_from_filter_label(label: str) -> str | None:
    return None if label == "すべて" else label


def url_submission_prefill_for_row(row: SchoolTaskRow) -> dict[str, object]:
    """Return Streamlit session_state values that prefill URL追加."""
    return {
        "selected_page": URL_SUBMISSION_PAGE_ID,
        URL_SUBMISSION_QUERY_STATE_KEY: row.school_name,
        URL_SUBMISSION_SCHOOL_ID_STATE_KEY: row.school_id,
    }


def manual_entry_prefill_for_row(row: SchoolTaskRow) -> dict[str, object]:
    """Return Streamlit session_state values that focus PDF確認・手入力."""
    payload: dict[str, object] = {"selected_page": MANUAL_ENTRY_PAGE_ID}
    if row.latest_document_id is not None:
        payload[MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY] = row.latest_document_id
    return payload


def blocking_reason_label(reason: str | None) -> str:
    if reason is None:
        return "対応なし"
    return BLOCKING_REASON_LABELS.get(reason, reason)


def status_label(labels: dict[str, str], code: str | None) -> str:
    if not code:
        return ""
    return labels.get(code, code)


def site_url_type_label(url_type: str | None, url: str | None) -> str:
    """Explain whether the registered URL is reusable for future fiscal years."""
    normalized_type = (url_type or "").strip().lower()
    base = SITE_URL_TYPE_LABELS.get(normalized_type)
    if base is None:
        base = "PDF直リンク" if is_pdf_site_url(url_type, url) else "ページURL"
    if base == "PDF直リンク":
        return "PDF直リンク（対象年度ごとに更新確認が必要）"
    return f"{base}（来年度以降も再取得入口として再利用）"


def site_entry_label(
    discovery_method: str | None,
    url_type: str | None,
    url: str | None,
) -> str:
    """Explain the crawl entry's origin and long-term reuse quality."""
    if not url:
        return "入口なし"
    if is_pdf_site_url(url_type, url):
        return "PDF直リンク（今年度だけ弱い）"

    method = (discovery_method or "").strip().lower()
    if method == "prefecture_aggregator":
        return "都道府県公式一覧の入口"
    if method == "operator_manual":
        return "手動登録ページ入口"
    return "登録ページ入口"


def discovery_evidence_table_rows(evidence_rows: list[Any]) -> list[dict[str, object]]:
    """Compact discovery evidence rows for the school task detail panel."""
    return [
        {
            "採否理由": row.reason,
            "score": row.score,
            "PDF種別": row.pdf_type or "",
            "リンク文字": row.anchor_text,
            "PDF候補": row.pdf_url,
            "掲載ページ": row.page_url,
        }
        for row in evidence_rows
    ]


def task_progress_label(summary: SchoolTaskSummary) -> str:
    if summary.total <= 0:
        return "対象校がありません。"
    return (
        f"Excel出力可 {summary.excel_ready}/{summary.total} 校 / "
        f"要対応 {summary.needs_action} 校"
    )


def task_lanes_for_summary(summary: SchoolTaskSummary) -> list[TaskLane]:
    """Return the operator's top-level work lanes in recommended order."""
    return [
        TaskLane(
            key="no_url",
            label="URL入口なし",
            count=summary.no_url,
            description="都道府県公式一覧、学校、または法人の情報公開ページを再取得入口として登録します。",
            button_label="URLなしを表示",
            scope="needs_action",
            blocking_reason="no_url",
        ),
        TaskLane(
            key="target_wait",
            label="対象年度PDF待ち",
            count=summary.target_pdf_wait,
            description="登録済み入口から対象年度PDFを再探索します。学校側の公開待ちもここに残ります。",
            button_label="PDF待ちを表示",
            scope="needs_action",
            blocking_reason="no_target_pdf",
        ),
        TaskLane(
            key="stale_pdf",
            label="旧年度PDFのみ",
            count=summary.stale_fallback,
            description="旧年度PDFは成果に含めません。次回再取得、または対象年度PDFの入口確認に回します。",
            button_label="旧年度のみを表示",
            scope="needs_action",
            blocking_reason="stale_pdf_only",
        ),
        TaskLane(
            key="review_or_parse",
            label="PDF確認・手入力",
            count=summary.review_or_parse,
            description="PDF原本、OCR待ち、抽出失敗、前年差分確認をまとめて確認します。",
            button_label="PDF確認を開く",
            scope="needs_action",
            page_id=MANUAL_ENTRY_PAGE_ID,
        ),
        TaskLane(
            key="dept_change",
            label="学科変更",
            count=summary.dept_change_review,
            description="新設、廃科、名称変更、統合再編など、単純転記できない学校を確認します。",
            button_label="学科変更を表示",
            scope="needs_action",
            blocking_reason="dept_change_review",
        ),
        TaskLane(
            key="excel_ready",
            label="Excel確認へ",
            count=summary.excel_ready,
            description="対象年度PDFと抽出が揃った学校だけを Excel プレビューで確認します。",
            button_label="Excelプレビュー",
            scope="excel_ready",
            page_id=EXCEL_PREVIEW_PAGE_ID,
        ),
    ]


def task_lane_prefill(lane: TaskLane) -> dict[str, object]:
    """Return Streamlit state that focuses the school task table or another page."""
    payload: dict[str, object] = {}
    if lane.page_id is not None:
        payload["selected_page"] = lane.page_id
        return payload
    payload[TASK_SCOPE_STATE_KEY] = TASK_CODE_TO_SCOPE_LABEL.get(lane.scope, "要対応")
    payload[TASK_REASON_STATE_KEY] = lane.blocking_reason or TASK_REASON_ALL_LABEL
    payload[TASK_PREFECTURE_STATE_KEY] = TASK_PREFECTURE_ALL_LABEL
    payload[TASK_SEARCH_STATE_KEY] = ""
    return payload


def is_pdf_site_url(url_type: str | None, url: str | None) -> bool:
    """Return True when a SchoolSite row points directly at a PDF file."""
    normalized_type = (url_type or "").strip().lower()
    if normalized_type in PDF_SITE_URL_TYPES:
        return True
    cleaned_url = (url or "").strip().lower().split("?", 1)[0].split("#", 1)[0]
    return cleaned_url.endswith(".pdf")


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


def next_action_for_row(status: SchoolFiscalYearStatus, site: SchoolSite | None) -> tuple[str, str]:
    """Map status plus registered URL shape into operator language.

    A direct PDF URL can unblock this year's emergency ingestion, but it is a
    weak long-lived crawl entry for next fiscal year. Route current-year gaps
    with only a PDF direct link back to URL追加 so operators add a reusable
    disclosure/homepage URL instead of repeatedly replacing yearly PDF links.
    """
    action, hint = next_action_for_status(status)
    if (
        site is not None
        and is_pdf_site_url(site.url_type, site.url)
        and status.blocking_reason in {"no_target_pdf", "stale_pdf_only"}
    ):
        return (
            "URL追加",
            "PDF直リンクだけでは来年度以降の再取得入口になりません。学校または法人の情報公開ページURLを追加",
        )
    return action, hint


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
    target_pdf_wait = 0
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
        if blocker == "no_target_pdf":
            target_pdf_wait += count
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
        target_pdf_wait=target_pdf_wait,
        stale_fallback=stale_fallback,
        no_url=no_url,
        review_or_parse=review_or_parse,
        dept_change_review=dept_change_review,
    )


def needs_initial_url_bootstrap(summary: SchoolTaskSummary) -> bool:
    """Return True when setup has schools but no known crawl URLs yet."""
    return summary.total > 0 and summary.no_url == summary.total


def initial_bootstrap_warning_text(summary: SchoolTaskSummary) -> str:
    """Explain the first acquisition scope without implying university coverage."""
    return (
        "まだ学校URLの初期取得が終わっていません。"
        f"{summary.total}校を手作業で追加する状態ではありません。"
        "下のボタンから初回取得を開始すると、対応済みの都道府県の確認大学等一覧から学校URLを登録し、"
        "対象年度PDFの探索を開始します。"
        "一覧PDF内の学校名リンクに埋め込まれたURLも自動で読み取ります。"
        "未対応の都道府県や未掲載校だけ、学校別タスクのURL追加から公式の情報公開ページを補足してください。"
    )


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


def latest_weekly_last_run_path(app_root: Path) -> Path:
    return app_root / "data" / "output" / "last_run.json"


def read_weekly_last_run(app_root: Path) -> dict[str, Any] | None:
    path = latest_weekly_last_run_path(app_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


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


def weekly_command(
    app_root: Path,
    *,
    python_executable: str | None = None,
) -> list[str]:
    return [
        python_executable or sys.executable,
        str(app_root / "scripts" / "run_weekly_target_year_discovery.py"),
        "--methods",
        *WEEKLY_DISCOVERY_METHODS,
        "--school-type",
        "all",
    ]


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


def start_weekly_rediscovery(
    app_root: Path,
    *,
    lock_path: Path,
    python_executable: str | None = None,
    now: datetime | None = None,
) -> BootstrapLaunchResult:
    """Start the target-fiscal-year weekly runner from the operator UI."""
    lock_status = probe_lock(lock_path)
    if lock_status.held:
        return BootstrapLaunchResult(
            started=False,
            message=f"別の処理が実行中です。完了後にもう一度開始してください。owner={lock_status.owner}",
        )

    script = app_root / "scripts" / "run_weekly_target_year_discovery.py"
    if not script.is_file():
        return BootstrapLaunchResult(
            started=False,
            message="週次再取得プログラムが見つかりません。ZIPをもう一度展開してください。",
        )

    logs_dir = app_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    started_at = now or datetime.now()
    log_path = logs_dir / f"weekly-rediscovery-{started_at.strftime('%Y%m%d-%H%M%S')}.log"
    last_run_path = latest_weekly_last_run_path(app_root)

    env = os.environ.copy()
    env["EIDP_APP_ROOT"] = str(app_root)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = weekly_command(app_root, python_executable=python_executable)

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
        return BootstrapLaunchResult(
            started=False,
            message=f"週次再取得を開始できませんでした: {exc}",
            log_path=log_path,
            last_run_path=last_run_path,
        )
    return BootstrapLaunchResult(
        started=True,
        message="週次URL/PDF再取得を開始しました。完了後、この画面を更新してください。",
        log_path=log_path,
        last_run_path=last_run_path,
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
    docs_by_school = _latest_documents_by_school(session, school_ids, fiscal_year=fiscal_year)
    sites_by_school = _latest_sites_by_school(session, school_ids)

    rows: list[SchoolTaskRow] = []
    for status, school in pairs:
        doc = docs_by_school.get(school.id)
        site = sites_by_school.get(school.id)
        action, hint = next_action_for_row(status, site)
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
                latest_site_url_type=site.url_type if site else None,
                latest_site_discovery_method=site.discovery_method if site else None,
            )
        )
    return rows


def _latest_documents_by_school(
    session: Session,
    school_ids: list[int],
    *,
    fiscal_year: int,
) -> dict[int, Document]:
    if not school_ids:
        return {}
    docs = (
        session.query(Document)
        .filter(Document.school_id.in_(school_ids), Document.pdf_type == "target")
        .all()
    )
    docs_by_school: dict[int, list[Document]] = {}
    for doc in docs:
        docs_by_school.setdefault(doc.school_id, []).append(doc)
    selected: dict[int, Document] = {}
    for school_id, school_docs in docs_by_school.items():
        selected_doc = select_task_document(school_docs, fiscal_year=fiscal_year)
        if selected_doc is not None:
            selected[school_id] = selected_doc
    return selected


def select_task_document(docs: list[Document], *, fiscal_year: int) -> Document | None:
    """Pick the document the task board should send the operator to.

    ``max(id)`` is not enough: a later old-year discovery can arrive after a
    valid target-year PDF and would make the UI look stale. Prefer target-year
    PDFs first, then the newest old fiscal year as fallback evidence.
    """
    if not docs:
        return None

    def sort_key(doc: Document) -> tuple[int, int, int, int]:
        if doc.fiscal_year == fiscal_year:
            year_bucket = 3
        elif doc.fiscal_year is not None and doc.fiscal_year < fiscal_year:
            year_bucket = 2
        elif doc.fiscal_year is None:
            year_bucket = 1
        else:
            year_bucket = 0
        status_bucket = {
            "ingested": 3,
            "review_pending": 2,
            "parse_failed": 2,
            "ocr_pending": 2,
        }.get(doc.ingest_status or "", 1)
        return (
            year_bucket,
            int(doc.fiscal_year or 0),
            status_bucket,
            int(doc.id or 0),
        )

    return max(docs, key=sort_key)


def _latest_sites_by_school(session: Session, school_ids: list[int]) -> dict[int, SchoolSite]:
    if not school_ids:
        return {}
    sites = (
        session.query(SchoolSite)
        .filter(SchoolSite.school_id.in_(school_ids))
        .order_by(SchoolSite.id.desc())
        .all()
    )
    latest_by_school: dict[int, SchoolSite] = {}
    reusable_by_school: dict[int, SchoolSite] = {}
    for site in sites:
        latest_by_school.setdefault(site.school_id, site)
        if site.http_status not in (None, 200):
            continue
        if is_pdf_site_url(site.url_type, site.url):
            continue
        reusable_by_school.setdefault(site.school_id, site)
    return {
        school_id: reusable_by_school.get(school_id) or latest
        for school_id, latest in latest_by_school.items()
    }


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
    st.warning(initial_bootstrap_warning_text(summary))
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


def _render_weekly_last_run(payload: dict[str, Any]) -> None:
    import streamlit as st

    status = str(payload.get("status") or "unknown")
    if status == "success":
        st.success("前回の週次再取得は完了しています。")
    elif status == "failed":
        st.error("前回の週次再取得はエラーで停止しました。")
    else:
        st.info(f"前回の週次再取得状態: {status}")

    cols = st.columns(4)
    cols[0].metric("探索対象", _int_or_default(payload.get("target_missing_school_count"), 0))
    cols[1].metric("新規PDF", _int_or_default(payload.get("new_document_count"), 0))
    cols[2].metric("URLなし", _int_or_default(payload.get("no_crawlable_url_school_count"), 0))
    cols[3].metric("旧年度あり", _int_or_default(payload.get("stale_school_count"), 0))

    meta = []
    if payload.get("current_fy"):
        meta.append(f"対象年度: {payload['current_fy']}")
    if payload.get("started_at"):
        meta.append(f"開始: {payload['started_at']}")
    if payload.get("finished_at"):
        meta.append(f"終了: {payload['finished_at']}")
    if payload.get("selection_mode"):
        meta.append(f"探索方式: {payload['selection_mode']}")
    if meta:
        st.caption(" / ".join(str(item) for item in meta))
    if payload.get("summary_path"):
        st.caption(f"詳細ログ: {payload['summary_path']}")
    if payload.get("error"):
        st.caption(f"エラー詳細: {payload['error']}")


def _render_weekly_rediscovery_controls(summary: SchoolTaskSummary, *, lock_path: Path) -> None:
    import streamlit as st

    from eidp.config import settings

    app_root = settings.app_root
    st.subheader("週次URL/PDF再取得")
    st.caption(
        "登録済みの情報公開ページや学校ページを入口に、現在の対象年度PDFを再探索します。"
        "今年登録したページURLは来年度以降も入口として使われます。"
    )
    needs_bootstrap = needs_initial_url_bootstrap(summary)
    if needs_bootstrap:
        st.info("先に初回URL/PDF取得を実行してください。URL登録後に週次再取得を使えます。")

    last_run = read_weekly_last_run(app_root)
    if last_run is not None:
        _render_weekly_last_run(last_run)

    lock_status = probe_lock(lock_path)
    if st.button(
        "週次URL/PDF再取得を開始",
        disabled=lock_status.held or needs_bootstrap,
    ):
        result = start_weekly_rediscovery(app_root, lock_path=lock_path)
        if result.started:
            st.success(result.message)
            if result.log_path is not None:
                st.caption(f"進行ログ: {result.log_path}")
            if result.last_run_path is not None:
                st.caption(f"完了後の結果: {result.last_run_path}")
        else:
            st.warning(result.message)


def _render_task_lanes(summary: SchoolTaskSummary) -> None:
    import streamlit as st

    lanes = task_lanes_for_summary(summary)
    st.subheader("次に進める作業")
    st.caption(
        "対象年度の成果に近い順ではなく、詰まりを解消する順に並べています。"
        "数字を見て、必要なレーンだけ開いてください。"
    )
    lane_columns = st.columns(3)
    for index, lane in enumerate(lanes):
        with lane_columns[index % 3]:
            with st.container(border=True):
                st.metric(lane.label, lane.count)
                st.caption(lane.description)
                if st.button(
                    lane.button_label,
                    key=f"school_task_lane_{lane.key}",
                    disabled=lane.count == 0,
                    width="stretch",
                ):
                    st.session_state.update(task_lane_prefill(lane))
                    st.rerun()


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin Streamlit shell
    import streamlit as st

    from eidp.config import settings
    from eidp.fiscal_year import format_fiscal_year_label
    from eidp.review._pages.pdf_manual_entry import latest_discovery_evidence

    fiscal_year = settings.target_fiscal_year
    target_label = format_fiscal_year_label(fiscal_year)

    st.header("① 学校別タスク")
    school_type_label = st.selectbox("対象", SCHOOL_TYPE_FILTER_LABELS, index=0)
    school_type = school_type_from_filter_label(school_type_label)
    st.caption(
        f"{target_label} の学校ごとの進捗です。旧年度PDFは成果に含めず、"
        f"{school_type_label} の次に何をするかだけを確認します。"
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
    st.progress(
        summary.excel_ready / summary.total,
        text=task_progress_label(summary),
    )

    if needs_initial_url_bootstrap(summary):
        _render_initial_bootstrap_controls(summary, lock_path=lock_path)

    _render_rebuild_button(session, fiscal_year=fiscal_year, school_type=school_type, lock_path=lock_path)
    _render_weekly_rediscovery_controls(summary, lock_path=lock_path)

    st.divider()
    _render_task_lanes(summary)

    st.divider()
    c1, c2, c3, c4 = st.columns([1.2, 1.4, 1.4, 2])
    if st.session_state.get(TASK_SCOPE_STATE_KEY) not in TASK_SCOPE_LABELS:
        st.session_state[TASK_SCOPE_STATE_KEY] = "要対応"
    scope_label = c1.radio(
        "表示",
        TASK_SCOPE_LABELS,
        horizontal=True,
        key=TASK_SCOPE_STATE_KEY,
    )
    scope = TASK_SCOPE_TO_CODE[str(scope_label)]

    reasons = [
        TASK_REASON_ALL_LABEL,
        *_blocking_reason_options(session, fiscal_year=fiscal_year, school_type=school_type),
    ]
    if st.session_state.get(TASK_REASON_STATE_KEY) not in reasons:
        st.session_state[TASK_REASON_STATE_KEY] = TASK_REASON_ALL_LABEL
    reason_label = c2.selectbox(
        "理由",
        reasons,
        format_func=lambda reason: TASK_REASON_ALL_LABEL
        if reason == TASK_REASON_ALL_LABEL
        else blocking_reason_label(str(reason)),
        key=TASK_REASON_STATE_KEY,
    )
    blocking_reason = None if reason_label == TASK_REASON_ALL_LABEL else str(reason_label)

    prefectures = [
        TASK_PREFECTURE_ALL_LABEL,
        *_prefecture_options(session, fiscal_year=fiscal_year, school_type=school_type),
    ]
    if st.session_state.get(TASK_PREFECTURE_STATE_KEY) not in prefectures:
        st.session_state[TASK_PREFECTURE_STATE_KEY] = TASK_PREFECTURE_ALL_LABEL
    pref_label = c3.selectbox("都道府県", prefectures, key=TASK_PREFECTURE_STATE_KEY)
    prefecture = None if pref_label == TASK_PREFECTURE_ALL_LABEL else pref_label

    search = c4.text_input("学校名検索", "", key=TASK_SEARCH_STATE_KEY)

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
            "理由": blocking_reason_label(row.blocking_reason),
            "取得入口": site_entry_label(
                row.latest_site_discovery_method,
                row.latest_site_url_type,
                row.latest_site_url,
            ),
            "URL": status_label(URL_STATUS_LABELS, row.url_status),
            "PDF": status_label(PDF_STATUS_LABELS, row.pdf_status),
            "抽出": status_label(EXTRACT_STATUS_LABELS, row.extract_status),
            "証拠": status_label(EVIDENCE_LEVEL_LABELS, row.evidence_level),
            "最新PDF年度": row.latest_document_fiscal_year,
            "学校ID": row.school_id,
        }
        for row in rows
    ]
    st.dataframe(table, hide_index=True, width="stretch")

    st.subheader("上位タスク詳細")
    for row in rows[:25]:
        title = f"{row.next_action} / {row.prefecture} / {row.school_name} / id={row.school_id}"
        with st.expander(title):
            st.write(row.action_hint)
            if row.next_action in {"URL追加", "PDF探索", "公示待ち/再取得"}:
                if st.button(
                    "この学校のURLを追加",
                    key=f"url_submission_prefill_{row.school_id}_{row.fiscal_year}",
                ):
                    st.session_state.update(url_submission_prefill_for_row(row))
                    st.rerun()
            if row.next_action in MANUAL_ENTRY_ACTIONS and row.latest_document_id is not None:
                if st.button(
                    "このPDFを確認・手入力",
                    key=f"manual_entry_prefill_{row.school_id}_{row.latest_document_id}",
                ):
                    st.session_state.update(manual_entry_prefill_for_row(row))
                    st.rerun()
            st.write(
                {
                    "URL": status_label(URL_STATUS_LABELS, row.url_status),
                    "PDF": status_label(PDF_STATUS_LABELS, row.pdf_status),
                    "抽出": status_label(EXTRACT_STATUS_LABELS, row.extract_status),
                    "前年差分": status_label(YOY_DIFF_STATUS_LABELS, row.yoy_diff_status),
                    "証拠": status_label(EVIDENCE_LEVEL_LABELS, row.evidence_level),
                    "理由": blocking_reason_label(row.blocking_reason),
                }
            )
            if row.latest_site_url:
                source_label = site_entry_label(
                    row.latest_site_discovery_method,
                    row.latest_site_url_type,
                    row.latest_site_url,
                )
                site_kind = site_url_type_label(row.latest_site_url_type, row.latest_site_url)
                method = row.latest_site_discovery_method or "不明"
                st.caption(f"取得入口: {source_label} / {site_kind} / 登録方法={method} / {row.latest_site_url}")
            if row.latest_document_url:
                st.caption(
                    f"最新PDF: doc#{row.latest_document_id} / fy={row.latest_document_fiscal_year} / "
                    f"{row.latest_document_status} / {row.latest_document_url}"
                )
            evidence_rows = latest_discovery_evidence(
                app_root=Path(settings.app_root),
                school_id=row.school_id,
                limit=6,
            )
            if evidence_rows:
                with st.expander("PDF探索ログ（候補PDFと採否理由）"):
                    st.dataframe(
                        discovery_evidence_table_rows(evidence_rows),
                        hide_index=True,
                        width="stretch",
                    )
