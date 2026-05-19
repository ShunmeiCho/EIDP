"""Streamlit page: school x target fiscal-year task board.

This page is the operator-facing replacement for a raw PDF document queue.
It renders one row per school for the configured target fiscal year and tells
the operator the next concrete action.
"""

from __future__ import annotations

import csv
import io
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

from eidp.db.audit import log_manual_action
from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Document, ManualActionLog, School, SchoolFiscalYearStatus, SchoolSite
from eidp.pipeline.school_fiscal_year_status import SchoolFiscalYearStatusStats
from eidp.scraper.discovery_evidence_summary import PdfDiscoveryEvidenceSummary


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
    publication_lag: int = 0
    strict_target_parsed: int = 0
    image_pending: int = 0

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
    details: dict[str, Any] | None = None


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


REVIEW_OR_PARSE_BLOCKERS = {
    "ocr_pending",
    "parse_failed",
    "not_extracted",
    "review_required",
    "target_year_unverified",
}
SCHOOL_TYPE_FILTER_LABELS = ("すべて", "専門学校", "大学")
URL_SUBMISSION_PAGE_ID = "url"
URL_SUBMISSION_QUERY_STATE_KEY = "url_submission_school_query"
URL_SUBMISSION_SCHOOL_ID_STATE_KEY = "url_submission_school_id"
MANUAL_ENTRY_PAGE_ID = "manual_entry"
MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY = "pdf_manual_entry_document_id"
EXCEL_PREVIEW_PAGE_ID = "excel_preview"
SETTINGS_PAGE_ID = "settings"
MANUAL_ENTRY_ACTIONS = {"OCR/手入力", "手入力", "PDF確認", "前年差分確認"}
WEEKLY_DISCOVERY_METHODS = (
    "prefecture_aggregator",
    "seed_csv",
    "corporation_pattern",
    "school_domain_override",
    "web_search",
    "operator_manual",
    "scrapling_stealth",
)
WEEKLY_TASK_REGISTRATION_WARNING_FILE = Path("data") / "weekly-task-registration-warning.txt"
TASK_SCOPE_STATE_KEY = "school_task_scope_filter"
TASK_REASON_STATE_KEY = "school_task_reason_filter"
TASK_PREFECTURE_STATE_KEY = "school_task_prefecture_filter"
TASK_SEARCH_STATE_KEY = "school_task_search_filter"
TASK_DISCOVERY_EVIDENCE_STATE_KEY = "school_task_discovery_evidence_filter"
TASK_SCOPE_LABELS = ("要対応", "Excel出力可", "全校")
TASK_REASON_ALL_LABEL = "すべて"
TASK_PREFECTURE_ALL_LABEL = "すべて"
TASK_DISCOVERY_EVIDENCE_ALL_LABEL = "すべて"
TASK_SCOPE_TO_CODE = {"要対応": "needs_action", "Excel出力可": "excel_ready", "全校": "all"}
TASK_CODE_TO_SCOPE_LABEL = {value: key for key, value in TASK_SCOPE_TO_CODE.items()}

BLOCKING_REASON_LABELS: dict[str, str] = {
    "no_url": "URL追加が必要",
    "no_target_pdf": "対象年度PDF待ち",
    "publication_lag_latest_public": "旧年度候補あり",
    "target_year_unverified": "年度未確認候補",
    "tls_certificate_verify_failed": "証明書エラー",
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
    "publication_lag": "旧年度候補あり",
    "target_year_unverified": "年度未確認候補",
    "site_error": "入口取得エラー",
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
    "tls_certificate_verify_failed": "証明書エラー",
    "target_year_unverified": "年度未確認候補",
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

URL_SEARCH_DECISION_LABELS: dict[str, str] = {
    "accepted": "採用",
    "rejected": "除外",
    "no_result": "候補なし",
    "error": "検索エラー",
}

URL_SEARCH_REASON_LABELS: dict[str, str] = {
    "registered_school_site": "学校サイト登録済み",
    "low_confidence": "信頼度不足",
    "unsafe_url": "安全でないURL",
    "missing_host": "ホスト名なし",
    "third_party_directory_domain": "第三者ディレクトリ",
    "government_index_domain": "行政一覧ページ",
    "provider_returned_no_results": "検索結果なし",
}


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


def settings_page_prefill() -> dict[str, object]:
    """Return Streamlit session_state values that open the operator settings page."""
    return {"selected_page": SETTINGS_PAGE_ID}


def blocking_reason_label(reason: str | None) -> str:
    if reason is None:
        return "対応なし"
    return BLOCKING_REASON_LABELS.get(reason, reason)


def status_label(labels: dict[str, str], code: str | None) -> str:
    if not code:
        return ""
    return labels.get(code, code)


def url_search_decision_label(decision: str | None) -> str:
    return status_label(URL_SEARCH_DECISION_LABELS, decision)


def url_search_reason_label(reason: str | None) -> str:
    return status_label(URL_SEARCH_REASON_LABELS, reason)


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
    if method == "seed_csv":
        return "既知URLシードの入口"
    if method == "corporation_pattern":
        return "法人ドメイン推定の入口"
    if method == "school_domain_override":
        return "学校別URL補正の入口"
    if method == "scrapling_stealth":
        return "学校公式サイト自動発見の入口"
    if method == "operator_manual":
        return "手動登録ページ入口"
    return "登録ページ入口"


def discovery_evidence_table_rows(evidence_rows: list[Any]) -> list[dict[str, object]]:
    """Compact discovery evidence rows for the school task detail panel."""
    return [
        {
            "採否理由": discovery_rejection_reason_label(str(row.reason)),
            "score": row.score,
            "PDF種別": row.pdf_type or "",
            "リンク文字": row.anchor_text,
            "PDF候補": row.pdf_url,
            "掲載ページ": row.page_url,
        }
        for row in evidence_rows
    ]


def discovery_evidence_stale_target_notice(evidence_rows: list[Any]) -> str | None:
    """Return an operator-facing notice when discovery found only stale target forms."""
    if any(str(getattr(row, "reason", "")) == "accepted_downloaded" for row in evidence_rows):
        return None

    counts: dict[int, int] = {}
    for row in evidence_rows:
        reason = str(getattr(row, "reason", ""))
        pdf_type = getattr(row, "pdf_type", None)
        if pdf_type != "target" or not reason.startswith("fiscal_year_mismatch:"):
            continue
        raw_year = reason.removeprefix("fiscal_year_mismatch:").strip()
        try:
            year = int(raw_year)
        except ValueError:
            continue
        counts[year] = counts.get(year, 0) + 1

    if not counts:
        return None

    parts = [f"{year}年度 {count}件" for year, count in sorted(counts.items(), reverse=True)]
    return f"旧年度の確認申請書候補あり: {' / '.join(parts)}。対象年度PDFは未取得です。"


def school_task_source_chain_csv(
    rows: list[SchoolTaskRow],
    *,
    discovery_evidence_buckets: dict[int, str] | None = None,
) -> str:
    """Return a CSV audit export for the visible task rows.

    The UI table is good for scanning, but the operator also needs a durable
    handoff artifact that explains where each crawl entry/PDF came from.
    """
    fieldnames = [
        "fiscal_year",
        "school_id",
        "prefecture",
        "school_name",
        "next_action",
        "blocking_reason",
        "entry_source",
        "entry_kind",
        "entry_discovery_method",
        "entry_url",
        "pdf_discovery_evidence",
        "pdf_document_id",
        "pdf_fiscal_year",
        "pdf_status",
        "pdf_url",
        "url_status",
        "extract_status",
        "yoy_diff_status",
        "evidence_level",
        "excel_ready",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "fiscal_year": row.fiscal_year,
                "school_id": row.school_id,
                "prefecture": row.prefecture,
                "school_name": row.school_name,
                "next_action": row.next_action,
                "blocking_reason": blocking_reason_label(row.blocking_reason),
                "entry_source": site_entry_label(
                    row.latest_site_discovery_method,
                    row.latest_site_url_type,
                    row.latest_site_url,
                ),
                "entry_kind": site_url_type_label(row.latest_site_url_type, row.latest_site_url)
                if row.latest_site_url
                else "",
                "entry_discovery_method": row.latest_site_discovery_method or "",
                "entry_url": row.latest_site_url or "",
                "pdf_discovery_evidence": school_year_discovery_evidence_bucket_label(
                    (discovery_evidence_buckets or {}).get(row.school_id)
                ),
                "pdf_document_id": row.latest_document_id or "",
                "pdf_fiscal_year": row.latest_document_fiscal_year or "",
                "pdf_status": row.latest_document_status or "",
                "pdf_url": row.latest_document_url or "",
                "url_status": status_label(URL_STATUS_LABELS, row.url_status),
                "extract_status": status_label(EXTRACT_STATUS_LABELS, row.extract_status),
                "yoy_diff_status": status_label(YOY_DIFF_STATUS_LABELS, row.yoy_diff_status),
                "evidence_level": status_label(EVIDENCE_LEVEL_LABELS, row.evidence_level),
                "excel_ready": "true" if row.excel_ready else "false",
            }
        )
    return buffer.getvalue()


def latest_url_search_evidence(
    *,
    app_root: Path,
    school_id: int,
    limit: int = 6,
) -> list[dict[str, object]]:
    """Read recent Web-search URL discovery evidence for one school."""
    path = app_root / "output" / "url_search_evidence.jsonl"
    if limit <= 0 or not path.is_file():
        return []

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("school_id") != school_id:
                continue
            rows.append({
                "採否": url_search_decision_label(str(payload.get("decision", ""))),
                "理由": url_search_reason_label(str(payload.get("reason", ""))),
                "score": payload.get("score", 0),
                "query": payload.get("query", ""),
                "候補URL": payload.get("result_url", ""),
                "候補タイトル": payload.get("result_title", ""),
                "provider": payload.get("provider", ""),
                "時刻": payload.get("timestamp", ""),
            })
    return list(reversed(rows[-limit:]))


def task_progress_label(summary: SchoolTaskSummary) -> str:
    if summary.total <= 0:
        return "対象校がありません。"
    return (
        f"Excel出力可 {summary.excel_ready}/{summary.total} 校 / "
        f"要対応 {summary.needs_action} 校"
    )


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "未測定"
    return f"{(numerator / denominator * 100):.1f}%"


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
            key="publication_lag",
            label="旧年度候補あり",
            count=summary.publication_lag,
            description="旧年度または公開待ちの確認申請書候補があります。成果には含めず、対象年度PDFを再確認します。",
            button_label="旧年度候補を表示",
            scope="needs_action",
            blocking_reason="publication_lag_latest_public",
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
    payload[TASK_DISCOVERY_EVIDENCE_STATE_KEY] = ""
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
    if reason == "publication_lag_latest_public":
        return "公示待ち/再取得", "旧年度候補は成果扱いせず、対象年度PDFの公開を再確認"
    if reason == "target_year_unverified":
        return "PDF確認", "確認申請書候補はありますが対象年度を読めません。PDF本文/OCR/公開年度を確認"
    if reason == "tls_certificate_verify_failed":
        return "証明書確認", "学校サイトの証明書チェーンが不完全です。管理者判断で取得方法を確認"
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
        and status.blocking_reason in {"no_target_pdf", "publication_lag_latest_public", "stale_pdf_only"}
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
    strict_target_parsed = 0
    image_pending = 0
    target_pdf_wait = 0
    stale_fallback = 0
    publication_lag = 0
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
            if extract_status == "parsed":
                strict_target_parsed += count
        if pdf_status == "image_pending":
            image_pending += count
        if blocker == "no_target_pdf":
            target_pdf_wait += count
        if blocker == "publication_lag_latest_public":
            publication_lag += count
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
        publication_lag=publication_lag,
        strict_target_parsed=strict_target_parsed,
        image_pending=image_pending,
    )


def school_year_discovery_evidence_summary(
    session: Session,
    *,
    app_root: Path,
    school_type: str | None = "専門学校",
) -> PdfDiscoveryEvidenceSummary | None:
    """Summarize recent PDF discovery evidence for the visible school type."""
    from eidp.scraper.discovery_evidence_summary import (
        load_pdf_discovery_evidence,
        load_pdf_discovery_site_scope,
        summarize_pdf_discovery_evidence,
    )

    evidence_path = app_root / "output" / "discovery_rejections.jsonl"
    if not evidence_path.is_file():
        return None
    site_scope = load_pdf_discovery_site_scope(session, school_type=school_type)
    return summarize_pdf_discovery_evidence(
        load_pdf_discovery_evidence(evidence_path),
        site_scope=site_scope,
    )


def school_year_discovery_evidence_summary_notice(
    summary: PdfDiscoveryEvidenceSummary | None,
    *,
    target_fiscal_year: int,
) -> str | None:
    """Operator-facing notice for strict-mode publication-lag evidence."""
    if summary is None:
        return None
    count = summary.school_bucket_counts.get("publication_lag_or_old_target_pdf", 0)
    if count <= 0:
        return None
    return (
        f"PDF探索ログ: 旧年度または公開待ちの確認申請書候補が {count}校あります。"
        f"これは{target_fiscal_year}年度成果には含めず、学校側の更新待ちとして再取得対象に残します。"
    )


def school_year_discovery_evidence_bucket_by_school(
    summary: PdfDiscoveryEvidenceSummary | None,
) -> dict[int, str]:
    """Return recent discovery evidence bucket by school id."""
    if summary is None:
        return {}
    return {
        school_summary.school_id: school_summary.bucket
        for school_summary in summary.school_summaries
        if school_summary.bucket != "no_evidence"
    }


def school_year_discovery_evidence_bucket_label(bucket: str | None) -> str:
    """Return compact table label for recent discovery evidence buckets."""
    labels = {
        "accepted_target_pdf": "取得済",
        "publication_lag_or_old_target_pdf": "旧年度候補あり",
        "tls_certificate_verify_failed": "証明書エラー",
        "target_form_without_year_evidence": "年度未確認候補",
        "no_pdf_candidates": "候補なし",
        "site_fetch_error_only": "入口取得エラー",
        "mixed_with_site_fetch_error": "一部取得エラー",
        "school_identity_mismatch": "学校名不一致",
        "non_target_candidates_only": "対象外候補のみ",
    }
    return labels.get(bucket or "", "")


def school_year_discovery_evidence_bucket_options(
    summary: PdfDiscoveryEvidenceSummary | None,
) -> list[str]:
    """Return bucket codes available in the current discovery evidence summary."""
    if summary is None:
        return []
    return sorted(
        bucket
        for bucket in summary.school_bucket_counts
        if bucket != "no_evidence" and school_year_discovery_evidence_bucket_label(bucket)
    )


def filter_rows_by_discovery_evidence_bucket(
    rows: list[SchoolTaskRow],
    bucket_by_school: dict[int, str],
    selected_bucket: str,
) -> list[SchoolTaskRow]:
    """Filter task rows by recent PDF discovery evidence bucket."""
    if not selected_bucket:
        return rows
    return [row for row in rows if bucket_by_school.get(row.school_id) == selected_bucket]


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
        "一覧にURLが無い学校は、設定された検索 provider で学校の情報公開ページを補完します。"
        "未対応の都道府県や未掲載校だけ、学校別タスクのURL追加から公式の情報公開ページを補足してください。"
    )


def url_search_config_summary(*, mode: str, provider: str, batch_size: int) -> str:
    """Return a short operator caption for the current URL search fallback setting."""
    mode_label = {
        "auto": "自動",
        "on": "常に実行",
        "off": "実行しない",
    }.get(mode, mode or "未設定")
    provider_label = provider or "未設定"
    if mode == "off" or batch_size <= 0:
        return f"不足URL Web検索: {mode_label} / provider={provider_label}"
    return f"不足URL Web検索: {mode_label} / provider={provider_label} / 最大 {batch_size} 校"


def operator_build_label(app_root: Path) -> str | None:
    """Return package identity for screenshots of the main task board."""
    from eidp.review._pages.settings_page import build_info_summary, read_build_info

    build_info = read_build_info(app_root)
    if not build_info:
        return None
    return f"実行中のパッケージ: {build_info_summary(build_info)}"


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
    details = payload.get("details")
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
        details=details if isinstance(details, dict) else None,
    )


def _parse_progress_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def bootstrap_progress_stale_reason(
    progress: BootstrapProgress,
    *,
    lock_held: bool,
    now: datetime | None = None,
    stale_after_seconds: int = 180,
) -> str | None:
    """Return an operator-facing reason when a running progress file is no longer credible."""
    if progress.status != "running":
        return None

    updated_at = _parse_progress_datetime(progress.updated_at)
    if updated_at is None:
        if lock_held:
            return (
                "処理は実行中ですが、進行状況の更新時刻を読めません。"
                "診断ログが増えているか確認してください。"
            )
        return (
            "進行状況ファイルは実行中のままですが、処理ロックは解除されています。"
            "前回処理が停止した可能性があります。"
        )

    current_time = now or datetime.now(tz=updated_at.tzinfo)
    age = (current_time - updated_at).total_seconds()
    if age >= stale_after_seconds:
        if lock_held:
            return (
                "処理はまだ実行中ですが、進行状況がしばらく更新されていません。"
                "学校サイトの応答待ち、通信待ち、または大きなPDF確認中の可能性があります。"
                "数分後に更新しても変わらない場合は診断ログを確認してください。"
            )
        return (
            "進行状況ファイルは実行中のままですが、処理ロックは解除されています。"
            "前回処理が途中で停止した可能性があります。診断ログを確認して、もう一度開始してください。"
        )
    return None


def bootstrap_progress_blocks_start(
    progress: BootstrapProgress | None,
    *,
    lock_held: bool,
    now: datetime | None = None,
) -> bool:
    """Return True when a recent running progress file should block duplicate launches."""
    if progress is None or progress.status != "running":
        return False
    return bootstrap_progress_stale_reason(progress, lock_held=lock_held, now=now) is None


def bootstrap_progress_detail_lines(progress: BootstrapProgress) -> list[str]:
    details = progress.details or {}
    lines: list[str] = []
    if "prefectures_total" in details:
        done = details.get("prefectures_done", 0)
        total = details.get("prefectures_total", 0)
        ok = details.get("prefectures_ok")
        failed = details.get("prefectures_failed")
        suffix = []
        if ok is not None:
            suffix.append(f"成功 {ok}")
        if failed is not None:
            suffix.append(f"失敗 {failed}")
        extra = f" / {' / '.join(suffix)}" if suffix else ""
        lines.append(f"都道府県データ: {done}/{total}{extra}")
    if "official_index_rows_extracted" in details:
        lines.append(
            "都道府県公式一覧: "
            f"抽出 {details.get('official_index_rows_extracted', 0)} / "
            f"DB照合 {details.get('official_index_rows_matched', 0)} / "
            f"URL追加 {details.get('official_school_sites_added', 0)} / "
            f"URL更新 {details.get('official_school_sites_upgraded', 0)} / "
            f"URL増加なし {details.get('official_prefectures_without_new_urls', 0)}県"
        )
    if "sites_total" in details:
        crawled = details.get("crawled", 0)
        total = details.get("sites_total", 0)
        found = details.get("found", 0)
        downloaded = details.get("downloaded", 0)
        failed = details.get("failed", 0)
        skipped = details.get("discovery_skipped", details.get("skipped", 0))
        prefiltered = details.get("prefiltered")
        cached_rejections = details.get("cached_rejections")
        lines.append(
            f"学校サイト探索: {crawled}/{total}確認済み / 候補 {found} / PDF取得 {downloaded} / "
            f"失敗 {failed} / 対象外・旧年度 {skipped}"
        )
        rejection_breakdown: list[str] = []
        if prefiltered is not None:
            rejection_breakdown.append(f"事前除外 {prefiltered}")
        if cached_rejections is not None:
            rejection_breakdown.append(f"既知除外 {cached_rejections}")
        if rejection_breakdown:
            lines.append(f"除外内訳: {' / '.join(rejection_breakdown)}")
        rejection_reasons = discovery_rejection_reason_summary(details)
        if rejection_reasons:
            lines.append(f"除外理由: {rejection_reasons}")
    if "seed_imported" in details or "corporation_inferred" in details:
        lines.append(
            "補助URL登録: "
            f"既知URL {details.get('seed_imported', 0)} / "
            f"学校別補正 {details.get('school_override_inferred', 0)} / "
            f"法人ドメイン推定 {details.get('corporation_inferred', 0)}"
        )
    if details.get("search_enabled") or "search_searched" in details:
        lines.append(
            "不足URL Web検索: "
            f"{details.get('search_searched', 0)}校 / 入口候補 {details.get('search_found', 0)} / "
            f"見つからず {details.get('search_no_result', 0)} / エラー {details.get('search_errors', 0)}"
        )
    if details.get("school_url_crawl_enabled") or "school_url_crawl_attempted" in details:
        lines.append(
            "学校公式サイト探索: "
            f"{details.get('school_url_crawl_attempted', 0)}校 / "
            f"自動登録 {details.get('school_url_crawl_auto_registered', 0)} / "
            f"確認候補 {details.get('school_url_crawl_review_enqueued', 0)} / "
            f"手入力キュー {details.get('school_url_crawl_manual_required_enqueued', 0)} / "
            f"エラー {details.get('school_url_crawl_errors', 0)}"
        )
        if details.get("school_url_crawl_unavailable"):
            lines.append("学校公式サイト探索: Scrapling add-on が未導入のためスキップしました。")
    if "target_pdf_auto_yield_pct" in details:
        auto_yield = details.get("target_pdf_auto_yield_pct")
        acquired = _int_or_default(details.get("target_pdf_auto_acquired_count"), 0)
        denominator = _int_or_default(details.get("target_pdf_auto_denominator_count"), 0)
        strict_yield = details.get("strict_target_pdf_auto_yield_pct")
        strict_acquired = _int_or_default(details.get("strict_target_pdf_auto_acquired_count"), acquired)
        excel_ready_yield = details.get("target_pdf_excel_ready_yield_pct")
        excel_ready = _int_or_default(details.get("target_pdf_excel_ready_acquired_count"), 0)
        broad_yield = details.get("broad_target_pdf_auto_yield_pct")
        broad_acquired = _int_or_default(details.get("broad_target_pdf_auto_acquired_count"), acquired)
        reviewable_yield = details.get("operator_reviewable_yield_pct", auto_yield)
        reviewable = _int_or_default(details.get("operator_reviewable_count"), acquired)
        gate = details.get("ship_gate_operator_coverage_pct", details.get("ship_gate_auto_yield_pct"))
        gate_status = str(details.get("ship_gate_status") or "unknown")
        if isinstance(reviewable_yield, (int, float)):
            line = f"操作員レビュー可能率: {reviewable_yield:.1f}% ({reviewable}/{denominator}校)"
            if isinstance(strict_yield, (int, float)):
                line += f" / strict自動取得 {strict_yield:.1f}% ({strict_acquired}/{denominator}校)"
            elif isinstance(auto_yield, (int, float)) and (auto_yield != reviewable_yield or acquired != reviewable):
                line += f" / 自動取得 {auto_yield:.1f}% ({acquired}/{denominator}校)"
            if isinstance(excel_ready_yield, (int, float)):
                line += f" / Excel出力可能 {excel_ready_yield:.1f}% ({excel_ready}/{denominator}校)"
            if isinstance(broad_yield, (int, float)) and (
                broad_yield != strict_yield or broad_acquired != strict_acquired
            ):
                line += f" / broad発見 {broad_yield:.1f}% ({broad_acquired}/{denominator}校)"
            if isinstance(gate, (int, float)):
                gate_label = "達成" if gate_status == "pass" else "未達"
                line += f" / レビュー目安 {gate:.0f}% {gate_label}"
            lines.append(line)
        else:
            lines.append(f"操作員レビュー可能率: 未測定 ({reviewable}/{denominator}校)")
    batch_plan_path = str(details.get("discovery_rca_batch_plan_path") or "")
    if batch_plan_path:
        item_count = _int_or_default(details.get("discovery_rca_batch_plan_item_count"), 0)
        total_candidates = _int_or_default(details.get("discovery_rca_batch_plan_total_candidates"), item_count)
        lines.append(f"Codex RCAキュー: {batch_plan_path} (候補 {item_count}/{total_candidates})")
    if details.get("discovery_rca_error"):
        lines.append(f"Codex RCA生成エラー: {details['discovery_rca_error']}")
    return lines


DISCOVERY_REJECTION_REASON_LABELS = {
    "target_fiscal_year_not_detected": "対象年度不明",
    "fiscal_year_mismatch": "旧年度",
    "target_application_not_detected": "申請書ではない",
    "pre_filtered_non_target_hint": "対象外ヒント",
    "classified_non_target": "対象外PDF",
    "no_candidates_found": "PDF候補なし",
    "all_negative_score": "低スコア",
    "duplicate_hash": "重複PDF",
    "duplicate_hash_other_school": "他校重複",
    "duplicate_hash_integrity_error": "重複PDF競合",
}


def discovery_rejection_reason_label(reason: str) -> str:
    """Return an operator-facing label for one discovery evidence reason."""
    if reason.startswith("fiscal_year_mismatch:"):
        raw_year = reason.removeprefix("fiscal_year_mismatch:").strip()
        return f"旧年度 ({raw_year}年度)" if raw_year else DISCOVERY_REJECTION_REASON_LABELS["fiscal_year_mismatch"]
    return DISCOVERY_REJECTION_REASON_LABELS.get(reason, reason)


def discovery_rejection_reason_summary(details: dict[str, object], *, limit: int = 3) -> str:
    counts: list[tuple[str, int]] = []
    prefix = "rejection_reason_"
    for key, value in details.items():
        if not key.startswith(prefix):
            continue
        if isinstance(value, bool):
            count = int(value)
        elif isinstance(value, int):
            count = value
        elif isinstance(value, str):
            try:
                count = int(value)
            except ValueError:
                continue
        else:
            continue
        if count <= 0:
            continue
        reason = key.removeprefix(prefix)
        label = discovery_rejection_reason_label(reason)
        counts.append((label, count))
    counts.sort(key=lambda item: item[1], reverse=True)
    return " / ".join(f"{label} {count}" for label, count in counts[:limit])


def bootstrap_progress_auto_refresh_html(seconds: int = 20) -> str:
    """Return a safe auto-refresh snippet for long-running bootstrap progress."""
    safe_seconds = min(max(seconds, 5), 300)
    delay_ms = safe_seconds * 1000
    return f"""
    <div style="font-size: 12px; opacity: 0.68; margin: 0.25rem 0 0.5rem;">
      {safe_seconds}秒ごとに自動更新します。すぐ確認する場合は下のボタンを押してください。
    </div>
    <script>
      window.setTimeout(function () {{
        window.location.reload();
      }}, {delay_ms});
    </script>
    """


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


def latest_weekly_progress_path(app_root: Path) -> Path | None:
    logs_dir = app_root / "logs"
    if not logs_dir.is_dir():
        return None
    progress_files = sorted(logs_dir.glob("weekly-rediscovery-*.json"), key=lambda path: path.stat().st_mtime)
    return progress_files[-1] if progress_files else None


def latest_weekly_progress(app_root: Path) -> BootstrapProgress | None:
    path = latest_weekly_progress_path(app_root)
    if path is None:
        return None
    return read_bootstrap_progress(path)


def weekly_task_registration_warning_path(app_root: Path) -> Path:
    return app_root / WEEKLY_TASK_REGISTRATION_WARNING_FILE


def read_weekly_task_registration_warning(app_root: Path) -> str | None:
    path = weekly_task_registration_warning_path(app_root)
    try:
        body = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return body or None


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


def _write_initial_weekly_progress(*, progress_path: Path, log_path: Path, started_at: datetime) -> None:
    payload = {
        "status": "running",
        "current_step": 0,
        "total_steps": 5,
        "percent": 0.0,
        "message": "週次再取得を準備中です。",
        "started_at": started_at.isoformat(timespec="seconds"),
        "updated_at": started_at.isoformat(timespec="seconds"),
        "log_path": str(log_path),
    }
    tmp_path = progress_path.with_suffix(progress_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(progress_path)


def _write_failed_weekly_progress(
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
    progress_path: Path | None = None,
    progress_log_path: Path | None = None,
    python_executable: str | None = None,
) -> list[str]:
    cmd = [
        python_executable or sys.executable,
        str(app_root / "scripts" / "run_weekly_target_year_discovery.py"),
        "--methods",
        *WEEKLY_DISCOVERY_METHODS,
        "--school-type",
        "all",
    ]
    if progress_path is not None:
        cmd.extend(["--progress-file", str(progress_path)])
    if progress_log_path is not None:
        cmd.extend(["--progress-log-path", str(progress_log_path)])
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
    progress_path = log_path.with_suffix(".json")
    last_run_path = latest_weekly_last_run_path(app_root)
    _write_initial_weekly_progress(progress_path=progress_path, log_path=log_path, started_at=started_at)

    env = os.environ.copy()
    env["EIDP_APP_ROOT"] = str(app_root)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = weekly_command(
        app_root,
        progress_path=progress_path,
        progress_log_path=log_path,
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
        message = f"週次再取得を開始できませんでした: {exc}"
        _write_failed_weekly_progress(
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
            last_run_path=last_run_path,
        )
    return BootstrapLaunchResult(
        started=True,
        message="週次URL/PDF再取得を開始しました。完了後、この画面を更新してください。",
        log_path=log_path,
        progress_path=progress_path,
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


def _render_rebuild_button(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None,
    lock_path: Path,
    lock_held: bool = False,
) -> None:
    import streamlit as st

    if st.button("年度タスクを再計算", type="primary", disabled=lock_held, width="stretch"):
        from eidp.pipeline.school_fiscal_year_status import rebuild_school_fiscal_year_status

        try:
            with acquire_lock(lock_path, owner="school_year_tasks"):
                stats = rebuild_school_fiscal_year_status(
                    session,
                    fiscal_year=fiscal_year,
                    school_type=school_type,
                    discovery_evidence_path=Path("output") / "discovery_rejections.jsonl",
                )
                audit_school_year_tasks_rebuilt(session, stats=stats)
                session.commit()
        except LockBusyError as exc:
            st.warning(f"週次処理中のため再計算できません: {exc}")
        except Exception:
            session.rollback()
            raise
        else:
            st.success(f"再計算しました: {stats.rebuilt} 校 / Excel出力可 {stats.excel_ready} 校")
            st.rerun()


def audit_school_year_tasks_rebuilt(
    session: Session,
    *,
    stats: SchoolFiscalYearStatusStats,
    actor: str = "operator",
) -> ManualActionLog:
    """Audit a manual rebuild of the target-year school task rows."""
    return log_manual_action(
        session,
        action_type="school_year_tasks_rebuilt",
        target_table="school_fiscal_year_status",
        old_value=None,
        new_value={
            "fiscal_year": stats.fiscal_year,
            "school_type": stats.school_type,
            "rebuilt": stats.rebuilt,
            "excel_ready": stats.excel_ready,
        },
        reason="Operator rebuilt school-year task rows",
        actor=actor,
    )


def _render_bootstrap_progress(
    progress: BootstrapProgress,
    *,
    lock_held: bool | None = None,
    process_label: str = "初回URL/PDF取得",
    success_message: str | None = None,
) -> None:
    import streamlit as st

    percent_label = f"{progress.percent:.0%}"
    step_label = f"{progress.current_step}/{progress.total_steps}"
    text = f"{percent_label}  {progress.message}（{step_label}）"
    st.progress(progress.percent, text=text)

    stale_reason = None
    if lock_held is not None:
        stale_reason = bootstrap_progress_stale_reason(progress, lock_held=lock_held)

    if progress.status == "succeeded":
        st.success(
            success_message
            or "初回URL/PDF取得が完了しました。この画面を更新すると最新の学校別タスクを確認できます。"
        )
    elif progress.status == "failed":
        st.error(progress.message)
        if progress.error:
            st.caption(f"エラー詳細: {progress.error}")
    elif stale_reason:
        st.warning(stale_reason)
    elif progress.status == "running":
        st.info(f"{process_label}を実行中です。この画面は自動で進行状況を更新します。")
    else:
        st.info(progress.message)

    for line in bootstrap_progress_detail_lines(progress):
        st.caption(line)

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
    if progress.status == "running":
        st.html(bootstrap_progress_auto_refresh_html(), unsafe_allow_javascript=True)
    key_suffix = progress.started_at or progress.updated_at or progress.message
    if st.button("進行状況を更新", key=f"bootstrap_progress_refresh_{key_suffix}", width="stretch"):
        st.rerun()


def _render_initial_bootstrap_controls(summary: SchoolTaskSummary, *, lock_path: Path) -> None:
    import streamlit as st

    from eidp.config import settings

    app_root = settings.app_root
    lock_status = probe_lock(lock_path)
    st.warning(initial_bootstrap_warning_text(summary))
    st.caption("初回取得はオンライン処理です。学校数が多いため、数十分かかることがあります。")
    st.caption(
        url_search_config_summary(
            mode=str(settings.url_search_auto_enable),
            provider=str(settings.search_provider),
            batch_size=int(settings.url_search_batch_size),
        )
    )

    latest_progress = latest_bootstrap_progress(app_root)
    if latest_progress is not None:
        _render_bootstrap_progress(latest_progress, lock_held=lock_status.held)
    progress_blocks_start = bootstrap_progress_blocks_start(latest_progress, lock_held=lock_status.held)

    latest_log = latest_bootstrap_log(app_root)
    if latest_log is not None and (latest_progress is None or latest_progress.log_path != str(latest_log)):
        st.caption(f"最新の初回取得ログ: {latest_log}")

    if st.button(
        "初回URL/PDF取得を開始",
        type="primary",
        disabled=lock_status.held or progress_blocks_start,
        width="stretch",
    ):
        result = start_initial_url_bootstrap(app_root, lock_path=lock_path)
        if result.started:
            st.success(result.message)
            if result.log_path is not None:
                st.caption(f"進行状況ログ: {result.log_path}")
            if result.progress_path is not None:
                progress = read_bootstrap_progress(result.progress_path)
                if progress is not None:
                    _render_bootstrap_progress(progress, lock_held=probe_lock(lock_path).held)
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
    auto_yield = payload.get("target_pdf_auto_yield_pct")
    if auto_yield is not None:
        acquired = _int_or_default(payload.get("target_pdf_auto_acquired_count"), 0)
        target_missing = _int_or_default(
            payload.get("target_pdf_auto_denominator_count"),
            _int_or_default(payload.get("target_missing_school_count"), 0),
        )
        strict_yield = payload.get("strict_target_pdf_auto_yield_pct")
        strict_acquired = _int_or_default(payload.get("strict_target_pdf_auto_acquired_count"), acquired)
        excel_ready_yield = payload.get("target_pdf_excel_ready_yield_pct")
        excel_ready = _int_or_default(payload.get("target_pdf_excel_ready_acquired_count"), 0)
        broad_yield = payload.get("broad_target_pdf_auto_yield_pct")
        broad_acquired = _int_or_default(payload.get("broad_target_pdf_auto_acquired_count"), acquired)
        reviewable_yield = payload.get("operator_reviewable_yield_pct", auto_yield)
        reviewable = _int_or_default(payload.get("operator_reviewable_count"), acquired)
        gate = payload.get("ship_gate_operator_coverage_pct", payload.get("ship_gate_auto_yield_pct"))
        gate_status = str(payload.get("ship_gate_status") or "unknown")
        gate_text = f" / gate {gate}%" if gate is not None else ""
        strict_text = (
            f" / strict自動取得: {strict_yield}% ({strict_acquired}/{target_missing})"
            if strict_yield is not None
            else ""
        )
        legacy_auto_text = (
            f" / 自動取得率: {auto_yield}% ({acquired}/{target_missing})"
            if strict_yield is None and (auto_yield != reviewable_yield or acquired != reviewable)
            else ""
        )
        excel_text = (
            f" / Excel出力可能: {excel_ready_yield}% ({excel_ready}/{target_missing})"
            if excel_ready_yield is not None
            else ""
        )
        broad_text = (
            f" / broad発見: {broad_yield}% ({broad_acquired}/{target_missing})"
            if broad_yield is not None and (broad_yield != strict_yield or broad_acquired != strict_acquired)
            else ""
        )
        st.caption(
            f"レビュー可能率: {reviewable_yield}% ({reviewable}/{target_missing})"
            f"{strict_text}{legacy_auto_text}{excel_text}{broad_text}{gate_text} / レビュー判定: {gate_status}"
        )
    if payload.get("summary_path"):
        st.caption(f"詳細ログ: {payload['summary_path']}")
    discovery_rca = payload.get("discovery_rca")
    if isinstance(discovery_rca, dict):
        batch_plan_path = str(discovery_rca.get("batch_plan_path") or "")
        if batch_plan_path:
            item_count = _int_or_default(discovery_rca.get("batch_plan_item_count"), 0)
            total_candidates = _int_or_default(discovery_rca.get("batch_plan_total_candidates"), item_count)
            st.caption(f"Codex RCAキュー: {batch_plan_path} (候補 {item_count}/{total_candidates})")
        if discovery_rca.get("error"):
            st.caption(f"Codex RCA生成エラー: {discovery_rca['error']}")
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
    task_warning = read_weekly_task_registration_warning(app_root)
    if task_warning:
        st.warning(
            "Windows の自動週次タスクが登録できていません。"
            "この画面の「週次URL/PDF再取得を開始」ボタンから手動で再取得できます。"
            "毎週の自動実行が必要な場合は管理者に setup ログを共有してください。"
        )
        st.caption(f"Task Scheduler: {task_warning}")
    needs_bootstrap = needs_initial_url_bootstrap(summary)
    if needs_bootstrap:
        st.info("先に初回URL/PDF取得を実行してください。URL登録後に週次再取得を使えます。")

    lock_status = probe_lock(lock_path)
    latest_progress = latest_weekly_progress(app_root)
    if latest_progress is not None:
        _render_bootstrap_progress(
            latest_progress,
            lock_held=lock_status.held,
            process_label="週次URL/PDF再取得",
            success_message="週次URL/PDF再取得が完了しました。この画面を更新すると最新の学校別タスクを確認できます。",
        )
    progress_blocks_start = bootstrap_progress_blocks_start(latest_progress, lock_held=lock_status.held)

    last_run = read_weekly_last_run(app_root)
    if last_run is not None:
        _render_weekly_last_run(last_run)

    if st.button(
        "週次URL/PDF再取得を開始",
        type="primary",
        disabled=lock_status.held or needs_bootstrap or progress_blocks_start,
        width="stretch",
    ):
        result = start_weekly_rediscovery(app_root, lock_path=lock_path)
        if result.started:
            st.success(result.message)
            if result.log_path is not None:
                st.caption(f"進行ログ: {result.log_path}")
            if result.progress_path is not None:
                progress = read_bootstrap_progress(result.progress_path)
                if progress is not None:
                    _render_bootstrap_progress(
                        progress,
                        lock_held=probe_lock(lock_path).held,
                        process_label="週次URL/PDF再取得",
                        success_message=(
                            "週次URL/PDF再取得が完了しました。この画面を更新すると最新の学校別タスクを確認できます。"
                        ),
                    )
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
    from eidp.ocr import detect_ocr_availability
    from eidp.review._pages.pdf_manual_entry import latest_discovery_evidence

    fiscal_year = settings.target_fiscal_year
    target_label = format_fiscal_year_label(fiscal_year)

    st.header("① 学校別タスク")
    build_label = operator_build_label(Path(settings.app_root))
    if build_label:
        st.caption(build_label)
    school_type_label = st.selectbox("対象", SCHOOL_TYPE_FILTER_LABELS, index=0)
    school_type = school_type_from_filter_label(school_type_label)
    st.caption(
        f"{target_label} の学校ごとの進捗です。旧年度PDFは成果に含めず、"
        f"{school_type_label} の次に何をするかだけを確認します。"
    )
    st.info(
        f"{target_label} の確認申請書PDFは、多くの学校で6〜8月ごろ順次公開されます。"
        "公開前の学校は「対象年度PDF待ち」に残し、旧年度PDF・募集要項・学生向け申請書は成果に含めません。"
    )
    settings_col, _spacer = st.columns([1, 3])
    with settings_col:
        if st.button(
            "設定を開く（年度・OCR・API）",
            key="school_tasks_open_settings",
            width="stretch",
        ):
            st.session_state.update(settings_page_prefill())
            st.rerun()

    lock_status = probe_lock(lock_path)
    if lock_status.held:
        st.warning(
            f"週次処理中、再計算と編集は一時停止しています "
            f"(owner={lock_status.owner}, started_at={lock_status.started_at})"
        )

    summary = school_task_summary(session, fiscal_year=fiscal_year, school_type=school_type)
    if summary.total == 0:
        st.warning("学校別年度タスクがまだ作成されていません。初回は再計算してください。")
        _render_rebuild_button(
            session,
            fiscal_year=fiscal_year,
            school_type=school_type,
            lock_path=lock_path,
            lock_held=lock_status.held,
        )
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
    kpi_cols = st.columns(3)
    kpi_cols[0].metric(
        "strict自動取得",
        _format_rate(summary.strict_target_parsed, summary.total),
        f"{summary.strict_target_parsed}/{summary.total} 校",
    )
    kpi_cols[1].metric(
        "broad発見",
        _format_rate(summary.confirmed_target, summary.total),
        f"{summary.confirmed_target}/{summary.total} 校",
    )
    kpi_cols[2].metric(
        "Excel出力可能",
        _format_rate(summary.excel_ready, summary.total),
        f"{summary.excel_ready}/{summary.total} 校",
    )
    st.caption(
        "strict自動取得 = PDF から Excel データ列が抽出できた学校。"
        " broad発見 = 対象年度PDF候補はあるが、Excel 出力可能とは限らない学校。"
    )
    if summary.image_pending > 0:
        ocr_detection = detect_ocr_availability(app_root=Path(settings.app_root))
        if not ocr_detection.can_run:
            st.warning(
                f"画像PDF/OCR待ちが {summary.image_pending} 校あります。"
                "OCR add-on 未導入の環境では自動抽出されないため、PDF確認・手入力で確認してください。"
            )
    evidence_summary = school_year_discovery_evidence_summary(
        session,
        app_root=Path(settings.app_root),
        school_type=school_type,
    )
    evidence_notice = school_year_discovery_evidence_summary_notice(
        evidence_summary,
        target_fiscal_year=fiscal_year,
    )
    if evidence_notice:
        st.info(evidence_notice)
    evidence_bucket_by_school = school_year_discovery_evidence_bucket_by_school(evidence_summary)

    if needs_initial_url_bootstrap(summary):
        _render_initial_bootstrap_controls(summary, lock_path=lock_path)

    _render_rebuild_button(
        session,
        fiscal_year=fiscal_year,
        school_type=school_type,
        lock_path=lock_path,
        lock_held=lock_status.held,
    )
    _render_weekly_rediscovery_controls(summary, lock_path=lock_path)

    st.divider()
    _render_task_lanes(summary)

    st.divider()
    c1, c2, c3, c4, c5 = st.columns([1.1, 1.25, 1.25, 1.45, 2])
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

    evidence_bucket_options = [
        "",
        *school_year_discovery_evidence_bucket_options(evidence_summary),
    ]
    if st.session_state.get(TASK_DISCOVERY_EVIDENCE_STATE_KEY) not in evidence_bucket_options:
        st.session_state[TASK_DISCOVERY_EVIDENCE_STATE_KEY] = ""
    selected_evidence_bucket = c4.selectbox(
        "PDF探索ログ",
        evidence_bucket_options,
        format_func=lambda bucket: TASK_DISCOVERY_EVIDENCE_ALL_LABEL
        if not bucket
        else school_year_discovery_evidence_bucket_label(str(bucket)),
        key=TASK_DISCOVERY_EVIDENCE_STATE_KEY,
    )

    search = c5.text_input("学校名検索", "", key=TASK_SEARCH_STATE_KEY)

    rows = list_school_year_tasks(
        session,
        fiscal_year=fiscal_year,
        school_type=school_type,
        scope=scope,
        blocking_reason=blocking_reason,
        prefecture=prefecture,
        search=search,
    )
    rows = filter_rows_by_discovery_evidence_bucket(
        rows,
        evidence_bucket_by_school,
        str(selected_evidence_bucket),
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
            "PDF探索ログ": school_year_discovery_evidence_bucket_label(evidence_bucket_by_school.get(row.school_id)),
            "抽出": status_label(EXTRACT_STATUS_LABELS, row.extract_status),
            "証拠": status_label(EVIDENCE_LEVEL_LABELS, row.evidence_level),
            "最新PDF年度": row.latest_document_fiscal_year,
            "学校ID": row.school_id,
        }
        for row in rows
    ]
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "表示中の出典チェーンCSVを保存",
        data=school_task_source_chain_csv(rows, discovery_evidence_buckets=evidence_bucket_by_school),
        file_name=f"school-task-source-chain-{fiscal_year}.csv",
        mime="text/csv",
        width="stretch",
    )

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
            url_evidence_rows = latest_url_search_evidence(
                app_root=Path(settings.app_root),
                school_id=row.school_id,
                limit=6,
            )
            if url_evidence_rows:
                with st.expander("URL検索ログ（queryと採否理由）"):
                    st.dataframe(url_evidence_rows, hide_index=True, width="stretch")
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
                stale_notice = discovery_evidence_stale_target_notice(evidence_rows)
                if stale_notice:
                    st.warning(stale_notice)
                with st.expander("PDF探索ログ（候補PDFと採否理由）"):
                    st.dataframe(
                        discovery_evidence_table_rows(evidence_rows),
                        hide_index=True,
                        width="stretch",
                    )
