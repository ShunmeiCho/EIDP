"""Operator-facing Streamlit pages.

担当者 uses these pages weekly:
- Pipeline Status: what was ingested, gaps, pollution
- Exports: one-click Master / Competition Excel generation + download
- Gap Report: competition gap CSV per corporation
- Rejections: browse PDF discovery rejection evidence
- URL 補足: validate and register manually found target PDFs
"""
from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import (
    Department,
    DepartmentChange,
    DepartmentYearly,
    Document,
    School,
    SchoolAlias,
    SchoolSite,
    SchoolYearStatus,
)
from eidp.fiscal_year import format_fiscal_year_label
from eidp.review.target_year_status import target_year_overview
from eidp.scraper.pdf_discovery import _classify_pdf_content, _safe_get
from eidp.scraper.url_discovery import _is_safe_url

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_OUTPUT_DIR = Path("output")
_SAMPLE_DIR = Path("sample")
_DATA_DIR = Path("data")
_DEFAULT_TEMPLATE = Path("sample/20250826更新版_競合校の在校生数.xlsx")
_DEFAULT_MASTER = _OUTPUT_DIR / "専門学校無償化情報公開まとめ.xlsx"
_DEFAULT_COMPETITION = _OUTPUT_DIR / "競合校の在校生数.xlsx"
_DEFAULT_COMPETITION_GAP = _OUTPUT_DIR / "競合校gap-report.csv"
_DEFAULT_REJECTIONS = _OUTPUT_DIR / "discovery_rejections.jsonl"
_DEFAULT_INGEST_REJECTIONS = _OUTPUT_DIR / "ingest_rejections.jsonl"
_DEFAULT_OPERATOR_SUBMISSIONS = _OUTPUT_DIR / "operator_url_submissions.jsonl"
_DEFAULT_PDF_STORAGE = _DATA_DIR / "pdfs"
_DEFAULT_SCHOOL_PROPOSALS = _OUTPUT_DIR / "school_missing_proposals.jsonl"
_DEFAULT_DEPT_PROPOSALS = _OUTPUT_DIR / "dept_unmatched_proposals.jsonl"
_DEFAULT_PROPOSAL_DECISIONS = _OUTPUT_DIR / "proposal_decisions.jsonl"

_MAX_OPERATOR_PDF_SIZE = 50 * 1024 * 1024
_ACCEPTED_OPERATOR_CLASSIFIERS = {"target", "image_only"}
_ACCEPTED_OPERATOR_PAGE_CLASSIFIER = "html_page"


class PathPolicyError(ValueError):
    """Raised when an operator-entered path is outside the allowed workspace roots."""


def _project_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (_PROJECT_ROOT / path).resolve()


def resolve_allowed_path(
    raw_path: str | Path,
    *,
    allowed_roots: tuple[Path, ...],
    suffixes: tuple[str, ...] = (),
    must_exist: bool = False,
) -> Path:
    """Resolve a UI-entered path under a small set of project-local roots.

    The operator UI accepts file paths for exports and evidence logs. Keep those
    paths constrained to known workspace directories so the Streamlit process
    cannot be used to read or overwrite arbitrary files.
    """
    path = Path(str(raw_path).strip()).expanduser()
    if not str(path):
        raise PathPolicyError("path is empty")

    resolved = _project_path(path)
    roots = tuple(_project_path(root) for root in allowed_roots)
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        allowed = ", ".join(str(root.relative_to(_PROJECT_ROOT)) for root in roots)
        raise PathPolicyError(f"path must be under: {allowed}")
    if suffixes and resolved.suffix.lower() not in suffixes:
        raise PathPolicyError(f"path suffix must be one of: {', '.join(suffixes)}")
    if must_exist and not resolved.exists():
        raise PathPolicyError(f"path does not exist: {resolved}")
    return resolved


def output_path(raw_path: str | Path, suffixes: tuple[str, ...]) -> Path:
    return resolve_allowed_path(raw_path, allowed_roots=(_OUTPUT_DIR,), suffixes=suffixes)


def sample_path(raw_path: str | Path, suffixes: tuple[str, ...], *, must_exist: bool = True) -> Path:
    return resolve_allowed_path(raw_path, allowed_roots=(_SAMPLE_DIR,), suffixes=suffixes, must_exist=must_exist)


@dataclass(frozen=True)
class OperatorUrlValidation:
    accepted: bool
    classifier: str
    reason: str
    http_status: int | None = None
    size_bytes: int = 0
    sha256: str | None = None


@dataclass(frozen=True)
class OperatorUrlSubmission:
    accepted: bool
    school_id: int
    school_name: str | None
    url: str
    classifier: str
    reason: str
    http_status: int | None
    size_bytes: int
    sha256: str | None
    site_id: int | None
    site_created: bool
    operator_name: str
    operator_note: str
    timestamp: str


def _fetch_pdf_bytes(url: str) -> tuple[int, bytes]:
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        resp = _safe_get(client, url)
        return resp.status_code, resp.content


def validate_operator_pdf_url(url: str) -> OperatorUrlValidation:
    """Validate an operator-supplied long-lived disclosure page or PDF URL."""
    url = url.strip()
    if not _is_safe_url(url):
        return OperatorUrlValidation(False, "unsafe", "unsafe_url")

    try:
        status, content = _fetch_pdf_bytes(url)
    except httpx.HTTPError as exc:
        return OperatorUrlValidation(False, "fetch_error", type(exc).__name__)

    if status != 200:
        return OperatorUrlValidation(False, "http_error", f"http={status}", http_status=status)
    size = len(content)
    if size < 1000:
        return OperatorUrlValidation(False, "unknown", "too_small", http_status=status, size_bytes=size)
    if size > _MAX_OPERATOR_PDF_SIZE:
        return OperatorUrlValidation(False, "unknown", "too_large", http_status=status, size_bytes=size)

    file_hash = hashlib.sha256(content).hexdigest()
    if content[:5] != b"%PDF-":
        lowered_sample = content[:4096].lower()
        if b"<html" not in lowered_sample and b"<a " not in lowered_sample:
            return OperatorUrlValidation(
                False, "unknown", "not_pdf_or_html", http_status=status, size_bytes=size, sha256=file_hash
            )
        return OperatorUrlValidation(
            True, _ACCEPTED_OPERATOR_PAGE_CLASSIFIER, "accepted_page", status, size, file_hash
        )

    classifier = _classify_pdf_content(content)
    if classifier not in _ACCEPTED_OPERATOR_CLASSIFIERS:
        return OperatorUrlValidation(
            False, classifier, "classified_non_target", status, size, file_hash
        )
    return OperatorUrlValidation(True, classifier, "accepted", status, size, file_hash)


def submit_operator_url(
    session: Session,
    *,
    school_id: int,
    url: str,
    operator_name: str = "",
    operator_note: str = "",
) -> OperatorUrlSubmission:
    """Validate a manually supplied disclosure page/PDF URL and insert/update SchoolSite."""
    clean_url = url.strip()
    timestamp = datetime.now(UTC).isoformat()
    school = session.get(School, school_id)
    if school is None:
        return OperatorUrlSubmission(
            accepted=False,
            school_id=school_id,
            school_name=None,
            url=clean_url,
            classifier="unknown",
            reason="school_not_found",
            http_status=None,
            size_bytes=0,
            sha256=None,
            site_id=None,
            site_created=False,
            operator_name=operator_name.strip(),
            operator_note=operator_note.strip(),
            timestamp=timestamp,
        )

    validation = validate_operator_pdf_url(clean_url)
    if not validation.accepted:
        return OperatorUrlSubmission(
            accepted=False,
            school_id=school_id,
            school_name=school.school_name,
            url=clean_url,
            classifier=validation.classifier,
            reason=validation.reason,
            http_status=validation.http_status,
            size_bytes=validation.size_bytes,
            sha256=validation.sha256,
            site_id=None,
            site_created=False,
            operator_name=operator_name.strip(),
            operator_note=operator_note.strip(),
            timestamp=timestamp,
        )

    now = datetime.now(UTC)
    url_type = "disclosure_page" if validation.classifier == _ACCEPTED_OPERATOR_PAGE_CLASSIFIER else "pdf"
    existing = (
        session.query(SchoolSite)
        .filter(SchoolSite.school_id == school_id, SchoolSite.url == clean_url)
        .first()
    )
    created = existing is None
    if existing is None:
        site = SchoolSite(
            school_id=school_id,
            url=clean_url,
            url_type=url_type,
            discovery_method="operator_manual",
            confidence=1.0,
            verified=True,
            verified_at=now,
            last_checked=now,
            http_status=validation.http_status,
        )
        session.add(site)
    else:
        site = existing
        site.url_type = site.url_type or url_type
        site.discovery_method = site.discovery_method or "operator_manual"
        site.confidence = max(float(site.confidence or 0), 1.0)
        site.verified = True
        site.verified_at = site.verified_at or now
        site.last_checked = now
        site.http_status = validation.http_status

    session.flush()
    return OperatorUrlSubmission(
        accepted=True,
        school_id=school_id,
        school_name=school.school_name,
        url=clean_url,
        classifier=validation.classifier,
        reason="inserted" if created else "existing_verified",
        http_status=validation.http_status,
        size_bytes=validation.size_bytes,
        sha256=validation.sha256,
        site_id=site.id,
        site_created=created,
        operator_name=operator_name.strip(),
        operator_note=operator_note.strip(),
        timestamp=timestamp,
    )


def record_operator_submission(result: OperatorUrlSubmission, audit_path: Path) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def run_operator_discovery_ingest(
    session: Session,
    *,
    school_id: int,
    source_url: str,
    storage_dir: Path = _DEFAULT_PDF_STORAGE,
    discovery_evidence_path: Path = _DEFAULT_REJECTIONS,
    ingest_evidence_path: Path = _DEFAULT_INGEST_REJECTIONS,
) -> dict[str, object]:
    """Run the existing pipeline for an accepted operator URL.

    Discovery is limited to operator_manual URLs for the given school. Ingestion
    is then limited to documents whose source_url is the operator-submitted URL,
    avoiding accidental batch ingestion of unrelated pending documents.
    """
    from eidp.pipeline.ingest import run_ingestion
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    doc_matches_source_or_page = (Document.source_url == source_url) | (Document.discovered_from == source_url)
    before_ids = {
        row[0]
        for row in session.query(Document.id)
        .filter(Document.school_id == school_id, doc_matches_source_or_page)
        .all()
    }

    discovery_stats = run_pdf_discovery(
        session,
        storage_dir=storage_dir,
        batch_size=10,
        rate_limit=0.5,
        discovery_methods=["operator_manual"],
        school_ids=[school_id],
        evidence_path=discovery_evidence_path,
        target_fiscal_year=settings.target_fiscal_year,
        strict_target_fiscal_year=True,
    )
    session.flush()

    docs = (
        session.query(Document)
        .filter(Document.school_id == school_id, doc_matches_source_or_page)
        .order_by(Document.id)
        .all()
    )
    document_ids = [doc.id for doc in docs if doc.id not in before_ids or doc.ingest_status != "ingested"]
    ingest_stats: dict[str, int] = {"processed": 0, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}
    if document_ids:
        ingest_stats = run_ingestion(
            session,
            batch_size=len(document_ids),
            document_ids=document_ids,
            evidence_path=ingest_evidence_path,
        )

    return {
        "discovery": discovery_stats,
        "document_ids": document_ids,
        "ingestion": ingest_stats,
    }


# ---------------------------------------------------------------------------
# Pipeline Status
# ---------------------------------------------------------------------------

def _pipeline_stats(session: Session) -> dict[str, object]:
    total_schools = session.query(func.count(School.id)).scalar() or 0
    total_docs = session.query(func.count(Document.id)).scalar() or 0

    docs_by_status = dict(
        session.query(Document.ingest_status, func.count(Document.id))
        .group_by(Document.ingest_status)
        .all()
    )
    docs_by_pdf_type = dict(
        session.query(Document.pdf_type, func.count(Document.id))
        .group_by(Document.pdf_type)
        .all()
    )

    coverage_by_year = dict(
        session.query(Document.fiscal_year, func.count(Document.id))
        .filter(Document.ingest_status == "ingested")
        .group_by(Document.fiscal_year)
        .all()
    )

    dept_yearly_rows = session.query(func.count(DepartmentYearly.id)).scalar() or 0
    dept_rows = session.query(func.count(Department.id)).scalar() or 0

    school_year_rows = session.query(func.count(SchoolYearStatus.id)).scalar() or 0

    return {
        "total_schools": total_schools,
        "total_documents": total_docs,
        "docs_by_status": docs_by_status,
        "docs_by_pdf_type": docs_by_pdf_type,
        "coverage_by_year": coverage_by_year,
        "dept_rows": dept_rows,
        "dept_yearly_rows": dept_yearly_rows,
        "school_year_rows": school_year_rows,
    }


def page_pipeline_status(session: Session) -> None:
    st.header("① データ状況")
    st.caption(
        "週初めの作業開始画面です。上の「今週のやること」で残タスクを、"
        "下の「現在のDB」で全体規模を確認してください。"
    )

    # 今週のTODO tiles — the V1 entry point担当者 sees first
    try:
        todo = compute_todo_counts(session)
    except Exception:
        todo = None

    if todo is not None:
        st.subheader("今週のやること")
        tcols = st.columns(4)
        tcols[0].metric(
            "候補が複数で要承認",
            todo.pending_ambiguous,
            help="② マッチング提案 → 学校タブ で処理",
        )
        tcols[1].metric(
            "URL追加が必要",
            todo.url_needed,
            help="③ URL追加 で補足",
        )
        tcols[2].metric(
            "分校扱い（要確認）",
            todo.pending_branch,
            help="② 学校タブ · 分校扱い",
        )
        tcols[3].metric(
            "自動承認済（累計）",
            todo.auto_approved,
            help="Excel再出力で反映されます",
        )

        if todo.excel_stale:
            st.warning(
                "最近の承認が Excel に反映されていません。④ Excel出力 で再生成してください。",
                icon="⚠️",
            )
        st.divider()

    st.subheader("現在のDB")
    stats = _pipeline_stats(session)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("学校数", stats["total_schools"])
    col2.metric("取得PDF数", stats["total_documents"])
    col3.metric("学科数", stats["dept_rows"])
    col4.metric("年度別データ数", stats["dept_yearly_rows"])

    st.divider()
    target_label = format_fiscal_year_label(settings.target_fiscal_year)
    target = target_year_overview(
        session,
        target_fiscal_year=settings.target_fiscal_year,
        school_type="専門学校",
    )
    st.subheader(f"{target_label} 採録状況")
    st.caption("ここは現在年度の到達度です。旧年度PDFは成果ではなく、再取得待ちとして扱います。")
    ycols = st.columns(4)
    ycols[0].metric("対象校", target.active_schools)
    ycols[1].metric("現在年度PDFあり", target.current_target_schools)
    ycols[2].metric("旧年度fallback", target.stale_target_documents)
    ycols[3].metric("要確認キュー", target.review_queue_documents)
    if target.current_target_documents == 0 and target.stale_target_documents > 0:
        st.error(
            f"{target_label} の採録済PDFが 0 件です。旧年度fallbackをExcel成果として扱わず、"
            "URL追加または週次再取得で現在年度PDFを集めてください。"
        )
    elif target.missing_current_target_schools > 0:
        st.warning(
            f"{target.missing_current_target_schools} 校は {target_label} のPDFが未採録です。"
            "URL追加または週次再取得の対象です。"
        )

    st.divider()
    st.subheader("PDF 取込状態の内訳")
    st.caption(
        "ingested = DBに反映済み / school_mismatch = 校名が合わず未反映 / "
        "ocr_pending = OCR待ち / non_target = 対象外PDF"
    )
    status = stats["docs_by_status"]
    if status:
        st.bar_chart(status)
    else:
        st.info("まだ取込み済のPDFがありません。")

    st.subheader("PDF種別の内訳")
    st.caption(
        "target = 申請書（正しいPDF）/ image_only = 画像のみでOCR必要 / "
        "non_target = 対象外 / unknown = 分類できない"
    )
    pdf_type = stats["docs_by_pdf_type"]
    if pdf_type:
        st.bar_chart(pdf_type)
    else:
        st.info("まだ分類データがありません。")

    st.subheader("年度別のデータ件数（ingested のみ）")
    st.caption("ここで最新年度（例: 2025）のデータ量を確認し、薄ければ URL追加 や 再取得 を検討します。")
    coverage = stats["coverage_by_year"]
    if coverage:
        rows = sorted(coverage.items(), key=lambda kv: (kv[0] or 0))
        st.dataframe(
            {"年度": [r[0] for r in rows], "PDF件数": [r[1] for r in rows]},
            hide_index=True,
        )
    else:
        st.info("まだ反映済みPDFがありません。")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def _run_master_export(session: Session, output: Path) -> dict[str, int]:
    from eidp.excel.exporter import export_master_workbook

    output.parent.mkdir(parents=True, exist_ok=True)
    return export_master_workbook(session, output)


def _run_competition_export(
    session: Session,
    template: Path,
    output: Path,
    gap_report: Path,
    fiscal_year: int | None,
) -> dict[str, object]:
    from eidp.excel.competition_exporter import export_competition_workbook

    output.parent.mkdir(parents=True, exist_ok=True)
    return export_competition_workbook(
        session,
        template_path=template,
        output_path=output,
        fiscal_year=fiscal_year,
        gap_report_path=gap_report,
    )


def page_exports(session: Session) -> None:
    st.header("Excel出力（管理者向け）")
    st.caption(
        "通常の週次業務では「Excel プレビュー」から確認・ダウンロードします。"
        "この詳細ページは、保存先やテンプレートを管理者が明示して出力するための画面です。"
    )

    st.subheader("マスターExcel（全体一覧）")
    st.caption("テンプレート不要。DB の現在データから新しい全体ワークブックを生成します。")
    master_out = st.text_input(
        "マスターExcelの保存先（output/配下のみ可）",
        value=str(_DEFAULT_MASTER),
        key="master_out",
    )
    if st.button("マスターExcelを生成", type="primary", key="btn_master"):
        try:
            master_path = output_path(master_out, (".xlsx",))
            stats = _run_master_export(session, master_path)
            st.success(f"出力完了: {master_out}")
            st.json(stats)
        except PathPolicyError as exc:
            st.error(f"パス不正（許可された出力先外）: {exc}")
        except Exception as exc:
            st.error(f"Export failed: {exc}")

    _offer_download_safe(master_out, (".xlsx",))

    st.divider()

    st.subheader("競合校Excel（16シート・テンプレ形式）")
    st.caption(
        "既存の「競合校の在校生数」テンプレートを読み込み、対象年度の数値だけを埋めて"
        "新しい Excel として保存します。通常の業務員は変更しません。"
    )
    comp_cols = st.columns(2)
    template_in = comp_cols[0].text_input(
        "前年配布されたテンプレートExcel（sample/配下の管理用ファイル）",
        value=str(_DEFAULT_TEMPLATE),
        key="comp_template",
    )
    comp_out = comp_cols[1].text_input(
        "出力先Excelのパス（output/配下）",
        value=str(_DEFAULT_COMPETITION),
        key="comp_out",
    )
    gap_out = st.text_input(
        "マッチング漏れCSVの保存先",
        value=str(_DEFAULT_COMPETITION_GAP),
        key="comp_gap",
    )
    fy_pick = st.number_input(
        f"対象年度（通常は {format_fiscal_year_label(settings.target_fiscal_year)}）",
        min_value=2019,
        value=settings.target_fiscal_year,
        step=1,
        key="comp_fy",
    )
    selected_fy = int(fy_pick)
    if selected_fy != settings.target_fiscal_year:
        st.warning(
            "対象年度以外の出力は管理者向けの履歴/検証用途です。"
            "通常業務の成果物は対象年度で出力してください。"
        )
    if st.button("競合校Excelを生成", type="primary", key="btn_comp"):
        try:
            fy = None if selected_fy == settings.target_fiscal_year else selected_fy
            template_path = sample_path(template_in, (".xlsx",))
            comp_path = output_path(comp_out, (".xlsx",))
            gap_path = output_path(gap_out, (".csv",))
            result = _run_competition_export(
                session,
                template_path,
                comp_path,
                gap_path,
                fy,
            )
            st.success(f"出力完了: {comp_out}")
            st.json(result)
        except PathPolicyError as exc:
            st.error(f"パス不正（許可された出力先外）: {exc}")
        except Exception as exc:
            st.error(f"Export failed: {exc}")

    _offer_download_safe(comp_out, (".xlsx",))


def _offer_download(path: Path) -> None:
    if not path.exists():
        st.caption(f"（未生成: `{path}`）")
        return
    data = path.read_bytes()
    st.caption(
        f"`{path}` — {len(data) / 1024:.1f} KB — "
        f"mtime {datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d %H:%M}"
    )
    st.download_button(
        label=f"Download {path.name}",
        data=data,
        file_name=path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{path.name}",
    )


def _offer_download_safe(raw_path: str | Path, suffixes: tuple[str, ...]) -> None:
    try:
        path = output_path(raw_path, suffixes)
    except PathPolicyError as exc:
        st.caption(f"(download path rejected: {exc})")
        return
    _offer_download(path)


# ---------------------------------------------------------------------------
# URL 補足
# ---------------------------------------------------------------------------

_URL_NEEDED_REASONS = {
    "school_no_document": "学校はあるがPDFがない",
    "school_doc_old_year_only": "PDFが古い年度のみ",
}


def _render_url_needed_worklist() -> None:
    """Read gap-report CSV and render the list of schools that need a URL.

    Shown above the submission form so担当者 sees the concrete worklist
    (which 21 schools, with school_id to paste into the form) instead of
    only a TODO count on the sidebar.
    """
    if not _DEFAULT_COMPETITION_GAP.exists():
        st.info(
            "gap-report がまだ生成されていません。④ Excel出力 を一度実行すると "
            "ここに「URL追加が必要な学校」の一覧が出ます。"
        )
        return

    import csv

    # Aggregate by school_id: a single school may appear in many template rows.
    # Some rows have no school_id (school_missing / no_fy_data) — we skip those
    # here since the URL form requires school_id; they're visible in ⑤ instead.
    agg: dict[str, dict[str, object]] = {}
    by_name_only: list[dict[str, object]] = []

    with _DEFAULT_COMPETITION_GAP.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            reason = row.get("gap_reason", "")
            if reason not in _URL_NEEDED_REASONS:
                continue
            sid = (row.get("school_id") or "").strip()
            entry = {
                "school_id": sid,
                "school_name": row.get("school_name", ""),
                "reason": reason,
                "reason_label": _URL_NEEDED_REASONS[reason],
                "detail": row.get("gap_detail", ""),
                "rows": 1,
            }
            if sid:
                key = sid
                if key in agg:
                    agg[key]["rows"] = int(agg[key]["rows"]) + 1  # type: ignore[operator]
                else:
                    agg[key] = entry
            else:
                by_name_only.append(entry)

    items = list(agg.values()) + by_name_only
    total = len(items)

    if total == 0:
        st.success("URL追加が必要な学校はありません。", icon="✅")
        return

    items.sort(key=lambda e: (str(e.get("reason", "")), str(e.get("school_name", ""))))

    with st.expander(
        f"URL追加が必要な学校一覧（{total}件）",
        expanded=True,
    ):
        st.caption(
            "下の表から school_id を確認し、フォームに入力して「登録 + 検証」してください。"
            "原因が「古い年度のみ」なら最新年度のPDF URL、「PDFがない」なら任意の申請書URL を探します。"
        )
        # Compact table — column labels in Japanese
        display_rows = [
            {
                "学校ID": e["school_id"] or "—",
                "学校名": e["school_name"],
                "原因": e["reason_label"],
                "影響行数": e["rows"],
                "詳細": e["detail"],
            }
            for e in items
        ]
        st.dataframe(
            display_rows,
            hide_index=True,
            use_container_width=True,
            height=min(40 + 35 * total, 420),
        )


def page_url_submission(session: Session) -> None:
    st.header("③ URL追加")
    st.caption(
        "担当者が自分で見つけた情報公開ページまたは申請書PDFを登録する画面です。"
        "ページURLは来年度以降も再取得の入口として使います。"
    )

    _render_url_needed_worklist()

    with st.expander("使い方", expanded=False):
        st.markdown(
            """
**こういう時に使う**：
- ⑤「マッチング漏れ一覧」で `学校はあるが対象PDFがまだない` の行を見つけた時
- 学校または法人の公式サイトで情報公開ページ、または対象年度の申請書PDFを見つけた時

**操作手順**：
1. 学校ID（`school.id`）を入力 — データ状況ページで確認できます
2. 情報公開ページURL、または申請書PDFのURLを貼り付け
3. 担当者名を入力（監査用）
4. 「登録 + 検証」を押す

**自動チェック**：
URLは登録前に以下のチェックを通します。
- 社内ネットワーク等の不正URL除外（SSRF対策）
- HTTP 200 で取得可能
- サイズが妥当（1KB〜50MB）
- PDF直リンクの場合は、PDFの署名（%PDF-）と申請書内容（機関要件・様式第2号など）を検証
- ページURLの場合は、長期利用する情報公開ページとして登録し、取込み時に対象年度PDFを探索

検証に失敗した場合はDB登録されません。
            """
        )

    with st.form("operator_url_submission"):
        school_id = st.number_input("学校ID（school.id）", min_value=1, step=1, value=1)
        url = st.text_input(
            "情報公開ページまたは申請書PDFのURL",
            placeholder="https://example.ac.jp/school/public_info/",
        )
        operator_name = st.text_input("担当者名（監査用）", placeholder="例: 山田")
        operator_note = st.text_area(
            "メモ（任意）",
            placeholder="掲載ページのURL、判断理由、年度メモなど",
            height=80,
        )
        run_now = st.checkbox(
            "登録後に自動で取込みまで行う（discovery + ingest）",
            value=False,
            help="オンにするとURL登録 → PDFダウンロード → DB反映まで一気に実行します。",
        )
        submitted = st.form_submit_button("登録 + 検証", type="primary")

    if not submitted:
        st.info(
            "URL は登録前に SSRF 対策・HTTP検証・PDF内容分類またはHTML確認を通過する必要があります。"
            "検証に失敗した場合はDBに書き込まれません。"
        )
        return

    audit_path = output_path(_DEFAULT_OPERATOR_SUBMISSIONS, (".jsonl",))
    try:
        result = submit_operator_url(
            session,
            school_id=int(school_id),
            url=url,
            operator_name=operator_name,
            operator_note=operator_note,
        )
        if not result.accepted:
            session.rollback()
            record_operator_submission(result, audit_path)
            st.error(f"Rejected: {result.reason} ({result.classifier})")
            st.json(asdict(result))
            return

        pipeline_result: dict[str, object] | None = None
        if run_now:
            pipeline_result = run_operator_discovery_ingest(
                session,
                school_id=int(school_id),
                source_url=url.strip(),
                storage_dir=resolve_allowed_path(
                    _DEFAULT_PDF_STORAGE,
                    allowed_roots=(_DATA_DIR,),
                ),
                discovery_evidence_path=output_path(_DEFAULT_REJECTIONS, (".jsonl",)),
                ingest_evidence_path=output_path(_DEFAULT_INGEST_REJECTIONS, (".jsonl",)),
            )

        session.commit()
        try:
            record_operator_submission(result, audit_path)
        except OSError as exc:
            st.warning(f"Accepted, but audit log write failed: {exc}")
        label = "created" if result.site_created else "verified existing"
        st.success(
            f"Accepted {result.classifier}: SchoolSite {label}"
            f" (site_id={result.site_id}, size={result.size_bytes / 1024:.1f} KB)"
        )
        st.json(asdict(result))
        if pipeline_result is not None:
            st.subheader("Pipeline result")
            st.json(pipeline_result)
    except PathPolicyError as exc:
        session.rollback()
        st.error(f"Path rejected: {exc}")
    except Exception as exc:
        session.rollback()
        st.error(f"URL submission failed: {exc}")


# ---------------------------------------------------------------------------
# Gap Report
# ---------------------------------------------------------------------------

def page_gap_report() -> None:
    st.header("⑤ マッチング漏れ一覧")
    st.caption(
        "競合校Excelでマッチングできなかった行の一覧です。"
        "漏れの種類（原因）でグループ化されているので、どこに手を入れれば改善するかが分かります。"
    )
    with st.expander("漏れ種別の意味", expanded=False):
        st.markdown(
            """
- **学校がDBに登録されていない** (`school_missing`) → ② で別名追加 or 新規登録
- **PDFが古い年度のみ** (`school_doc_old_year_only`) → ③ でURL追加
- **PDFは取り込んだが校名が違う** (`school_mismatch_doc_rejected`) → ② で別名追加
- **学校はあるがPDFがない** (`school_no_document`) → ③ でURL追加
- **学科名が一致しない** (`dept_unmatched`) → ② の学科タブで別名追加
- **本年度のデータがない** (`no_fy_data`) → ③ でURL追加
            """
        )

    gap_path = st.text_input(
        "漏れレポートCSVのパス",
        value=str(_DEFAULT_COMPETITION_GAP),
        key="gap_path",
    )
    try:
        path = output_path(gap_path, (".csv",))
    except PathPolicyError as exc:
        st.error(f"パス不正: {exc}")
        return
    if not path.exists():
        st.info(
            f"漏れレポートがまだありません: `{path}`。"
            "先に ④ 競合校Excelを出力してください。"
        )
        return

    import csv

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    st.write(f"漏れ行の合計: **{len(rows)}** 行")
    if not rows:
        return

    # Filters
    sheet_names = sorted({r.get("sheet", "") for r in rows})
    school_terms = st.text_input(
        "学校名で絞り込み（部分一致）", key="gap_filter_school",
    )
    sheets_pick = st.multiselect(
        "シートで絞り込み",
        sheet_names,
        default=sheet_names,
        key="gap_filter_sheet",
    )

    filtered = [
        r for r in rows
        if r.get("sheet", "") in sheets_pick
        and (not school_terms or school_terms in r.get("school_name", ""))
    ]
    st.write(f"表示件数: {len(filtered)} 行")
    st.dataframe(filtered, hide_index=True)


# ---------------------------------------------------------------------------
# Rejections (discovery evidence)
# ---------------------------------------------------------------------------

def page_rejections() -> None:
    st.header("⑥ 除外PDF履歴")
    st.caption(
        "自動収集で「対象外」と判定されて取り込まれなかったPDFの履歴です。"
        "「この学校のPDFが取れていないのはなぜ？」を調べる時に使います。"
    )
    with st.expander("除外理由の意味", expanded=False):
        st.markdown(
            """
- **classified_non_target** → 内容分類で申請書でないと判定
- **no_candidates_found** → そもそもPDFリンクが見つからなかった
- **all_negative_score** → 候補はあったが全て除外キーワード該当
- **http_error / too_small / not_pdf_magic** → HTTPまたはファイル形式の問題
- **unsafe_url** → 社内ネットワーク等の不正URLをブロック

同じ学校ID（school_id）が何度も出てくる場合、③「URL追加」で手動補足すれば解決します。
            """
        )

    log_path = st.text_input(
        "履歴ファイルのパス",
        value=str(_DEFAULT_REJECTIONS),
        key="rej_path",
    )
    try:
        path = output_path(log_path, (".jsonl",))
    except PathPolicyError as exc:
        st.error(f"パス不正: {exc}")
        return
    if not path.exists():
        st.info(f"履歴ファイルがありません: `{path}`")
        return

    limit = st.slider(
        "最新N件を表示", 10, 1000, 200, 10, key="rej_limit",
    )
    records = _tail_jsonl(path, limit)

    if not records:
        st.info("履歴が空です。")
        return

    reason_counts: dict[str, int] = {}
    school_counts: dict[int, int] = {}
    for r in records:
        reason_counts[r.get("reason", "?")] = reason_counts.get(r.get("reason", "?"), 0) + 1
        sid = r.get("school_id")
        if isinstance(sid, int):
            school_counts[sid] = school_counts.get(sid, 0) + 1

    cols = st.columns(2)
    with cols[0]:
        st.subheader("理由別の件数")
        st.bar_chart(reason_counts)
    with cols[1]:
        st.subheader("除外回数が多い学校（上位15）")
        top = sorted(school_counts.items(), key=lambda kv: kv[1], reverse=True)[:15]
        st.dataframe(
            {"学校ID": [t[0] for t in top], "除外回数": [t[1] for t in top]},
            hide_index=True,
        )

    st.divider()
    st.subheader("最近の除外履歴")
    school_filter = st.text_input(
        "学校IDで絞り込み（空白=全件）", key="rej_school_filter",
    )
    reason_filter = st.multiselect(
        "除外理由で絞り込み",
        sorted(reason_counts.keys()),
        default=sorted(reason_counts.keys()),
        key="rej_reason_filter",
    )
    shown = [
        r for r in records
        if (not school_filter or str(r.get("school_id", "")) == school_filter)
        and r.get("reason") in reason_filter
    ]
    st.write(f"表示件数: {len(shown)} 件")
    st.dataframe(shown, hide_index=True)


# ---------------------------------------------------------------------------
# V1 theme injection — pull Streamlit close to the Linear-style mockup
# ---------------------------------------------------------------------------

def inject_v1_theme() -> None:
    """Inject the V1 Linear-shell design tokens into Streamlit.

    Streamlit's default theme is generic SaaS. This override pulls it
    toward the mockup担当者 reviewed: #FAFAFA bg, Inter sans, Source Serif
    display, dense metrics, dark primary buttons, pill-style horizontal
    radio, sidebar with proper border. Call once from app.py main().
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
          --eidp-bg: #FAFAFA;
          --eidp-surface: #FFFFFF;
          --eidp-surface-alt: #F3F3F3;
          --eidp-ink: #0C0C0D;
          --eidp-ink-mid: #4E4E52;
          --eidp-ink-low: #8C8C92;
          --eidp-border: #E5E7EB;
          --eidp-border-strong: #D1D1D6;
          --eidp-accent: #5E6AD2;
          --eidp-accent-soft: #EEF0FB;
          --eidp-ok: #1F8B4C;
          --eidp-warn: #A65A00;
          --eidp-danger: #B42318;
        }

        /* App background + top chrome */
        .stApp { background: var(--eidp-bg) !important; color: var(--eidp-ink) !important; }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1180px; }

        /* Force readable text color on all primary surfaces */
        .stApp, .stApp p, .stApp li, .stApp span, .stApp div,
        .stApp label, .stApp [data-testid="stMarkdownContainer"] {
          color: var(--eidp-ink) !important;
        }
        /* But preserve muted tones on known muted classes */
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p,
        .stApp .stCaption {
          color: var(--eidp-ink-low) !important;
        }

        /* Global font — target only text elements, NEVER use universal selector.
           Streamlit renders icons (expander chevron, sidebar toggle, number-input
           +/−) via Material Symbols Rounded font + CSS ligatures. If we force
           font-family on every span, the ligature fails and the icon name
           ("keyboard_double_arrow_right", "arrow_right") renders as raw text. */
        html, body, .stApp {
          font-family: 'Inter', 'Hiragino Kaku Gothic ProN', 'Yu Gothic UI', sans-serif;
          -webkit-font-smoothing: antialiased;
          text-rendering: optimizeLegibility;
        }
        .stApp p, .stApp label, .stApp button,
        .stApp input, .stApp textarea, .stApp select,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] * {
          font-family: 'Inter', 'Hiragino Kaku Gothic ProN', 'Yu Gothic UI', sans-serif;
        }

        /* Title brand */
        .eidp-title { margin-bottom: 24px; display: flex; align-items: baseline; gap: 10px; }
        .eidp-brand {
          font-weight: 600 !important;
          font-size: 20px !important;
          color: var(--eidp-ink) !important;
          letter-spacing: -0.01em;
        }
        .eidp-brand-sub { font-size: 13px !important; color: var(--eidp-ink-low) !important; }

        /* Serif on headings for Muji-flavored touch */
        .stApp h1, .stApp h2, .stApp h3,
        .stApp h1 *, .stApp h2 *, .stApp h3 * {
          font-family: 'Source Serif 4', 'Hiragino Mincho ProN', 'Yu Mincho', serif !important;
          font-weight: 500;
          letter-spacing: -0.01em;
          color: var(--eidp-ink) !important;
        }
        .stApp h1 { font-size: 30px !important; }
        .stApp h2 { font-size: 22px !important; }
        .stApp h3 { font-size: 17px !important; }

        /* Sidebar */
        section[data-testid="stSidebar"] {
          background: var(--eidp-surface) !important;
          border-right: 1px solid var(--eidp-border);
        }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] * {
          color: var(--eidp-ink) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
        section[data-testid="stSidebar"] [data-testid="stCaption"] {
          color: var(--eidp-ink-low) !important;
          font-size: 11px;
        }
        section[data-testid="stSidebar"] > div { padding-top: 18px; }
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stRadio label { font-size: 13px; }
        section[data-testid="stSidebar"] hr { border-color: var(--eidp-border); }

        /* Sidebar radio (nav) */
        section[data-testid="stSidebar"] .stRadio [role="radiogroup"] {
          gap: 2px;
        }
        section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label {
          padding: 6px 10px;
          border-radius: 5px;
        }
        section[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:has(input:checked) {
          background: var(--eidp-accent-soft);
          color: var(--eidp-accent);
          font-weight: 500;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
          background: var(--eidp-surface) !important;
          border: 1px solid var(--eidp-border);
          border-radius: 8px;
          padding: 14px 16px;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * {
          color: var(--eidp-ink-low) !important;
          font-size: 11px !important;
          letter-spacing: 0.04em;
        }
        [data-testid="stMetricLabel"] p { font-size: 11px !important; }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * {
          font-family: 'Source Serif 4', 'Hiragino Mincho ProN', serif !important;
          font-weight: 600 !important;
          font-size: 28px !important;
          letter-spacing: -0.02em;
          color: var(--eidp-ink) !important;
          line-height: 1.2 !important;
        }
        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] * {
          color: var(--eidp-ink-low) !important;
          font-size: 11px !important;
        }
        [data-testid="stMetricDelta"] svg { display: none; }

        /* Primary button = dark, secondary = outline */
        .stButton > button {
          border-radius: 5px;
          font-size: 13px;
          font-weight: 500;
          padding: 6px 14px;
          transition: background 120ms ease, border 120ms ease;
        }
        .stButton > button[kind="primary"],
        .stButton > button[kind="primary"] * {
          background: var(--eidp-ink) !important;
          color: #FFFFFF !important;
          border: 1px solid var(--eidp-ink) !important;
        }
        .stButton > button[kind="primary"]:hover { background: #000000 !important; border-color: #000 !important; }
        .stButton > button:not([kind="primary"]) {
          background: var(--eidp-surface) !important;
          color: var(--eidp-ink) !important;
          border: 1px solid var(--eidp-border) !important;
        }
        .stButton > button:not([kind="primary"]) * { color: var(--eidp-ink) !important; }
        .stButton > button:not([kind="primary"]):hover {
          background: var(--eidp-surface-alt) !important;
          border-color: var(--eidp-border-strong) !important;
        }
        .stButton > button:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        /* Container (st.container(border=True)) */
        [data-testid="stVerticalBlockBorderWrapper"] {
          background: var(--eidp-surface);
          border: 1px solid var(--eidp-border) !important;
          border-radius: 8px !important;
        }

        /* Alerts / info / warning / success / error */
        [data-testid="stAlert"] {
          border-radius: 6px;
          border: 1px solid var(--eidp-border);
          padding: 10px 14px;
          background: var(--eidp-surface) !important;
        }
        [data-testid="stAlert"] * { color: var(--eidp-ink) !important; font-size: 13px; }
        [data-testid="stAlert"] svg { color: var(--eidp-ink-mid) !important; }

        /* Horizontal radio → pill toggle */
        .stRadio > div:not([role="radiogroup"]) > div[role="radiogroup"][aria-orientation="horizontal"] {
          display: inline-flex;
          border: 1px solid var(--eidp-border);
          border-radius: 6px;
          padding: 3px;
          background: var(--eidp-surface);
          gap: 0;
        }
        .stRadio > div:not([role="radiogroup"]) > div[role="radiogroup"][aria-orientation="horizontal"] > label {
          margin: 0;
          padding: 5px 14px;
          border-radius: 4px;
          font-size: 13px;
          color: var(--eidp-ink-mid);
        }
        .stRadio > div:not([role="radiogroup"])
          > div[role="radiogroup"][aria-orientation="horizontal"]
          > label:has(input:checked) {
          background: var(--eidp-ink);
          color: #FFFFFF;
        }

        /* Progress bar */
        .stProgress > div > div > div > div { background: var(--eidp-accent) !important; }
        .stProgress > div > div > div { background: var(--eidp-surface-alt) !important; height: 3px; }

        /* Divider */
        hr { border-color: var(--eidp-border); margin: 16px 0; }

        /* Caption */
        [data-testid="stCaptionContainer"], .stCaption {
          color: var(--eidp-ink-low);
          font-size: 12px;
        }

        /* Focus-mode custom hero (rendered via markdown html) */
        .eidp-focus-hero {
          padding: 32px 40px 24px;
          background: var(--eidp-surface) !important;
          border: 1px solid var(--eidp-border);
          border-radius: 10px;
          margin-bottom: 12px;
        }
        .eidp-focus-meta {
          display: flex; gap: 22px; font-size: 12px;
          color: var(--eidp-ink-low) !important;
          text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 16px;
        }
        .eidp-focus-meta > span { color: var(--eidp-ink-low) !important; }
        .eidp-focus-meta b {
          color: var(--eidp-ink) !important; font-weight: 500;
          font-family: 'JetBrains Mono', monospace; text-transform: none; letter-spacing: 0;
        }
        .eidp-focus-name {
          font-family: 'Source Serif 4', 'Hiragino Mincho ProN', serif !important;
          font-size: 34px !important; line-height: 1.25 !important; letter-spacing: -0.01em;
          color: var(--eidp-ink) !important; font-weight: 500 !important;
          margin: 0 0 6px !important;
        }
        .eidp-focus-rows {
          font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
          color: var(--eidp-ink-mid) !important;
        }
        .eidp-focus-divider {
          display: flex; align-items: center; gap: 12px; margin: 20px 0;
          color: var(--eidp-ink-low) !important; font-size: 11px; letter-spacing: 0.08em;
        }
        .eidp-focus-divider > span { color: var(--eidp-ink-low) !important; }
        .eidp-focus-divider .line { flex: 1; border-top: 1px dashed var(--eidp-border-strong); }

        /* Subtle input styling */
        input, .stTextInput input, .stTextArea textarea {
          border-radius: 5px !important;
          border-color: var(--eidp-border) !important;
          font-size: 13px !important;
        }
        input:focus, .stTextInput input:focus { border-color: var(--eidp-accent) !important; }

        /* Checkbox */
        .stCheckbox label { font-size: 13px; color: var(--eidp-ink-mid); }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 今週のTODO counters (sidebar + ① page)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TodoCounts:
    pending_ambiguous: int  # ② で人間の判断待ち（候補複数）
    pending_branch: int     # ② 分校要注意で未処理
    pending_dept: int       # ② 学科タブで未処理
    url_needed: int         # ③ URL追加が必要（school_no_document / old_year）
    auto_approved: int      # 自動承認済（先週処理）
    excel_stale: bool       # Excel再出力推奨（最新承認がExcelより新しい）


def compute_todo_counts(session: Session) -> TodoCounts:
    """Aggregate counts担当者 needs at a glance. Read-only."""
    # School/Dept proposals with pending status (not in decisions JSONL)
    decisions = _load_decision_index(_DEFAULT_PROPOSAL_DECISIONS)
    school_proposals = _read_proposals(_DEFAULT_SCHOOL_PROPOSALS)
    dept_proposals = _read_proposals(_DEFAULT_DEPT_PROPOSALS)

    pending_ambiguous = 0
    pending_branch = 0
    for p in school_proposals:
        key = ("school_alias", p.get("template_name", ""))
        if key in decisions:
            continue
        ptype = p.get("proposal_type", "")
        if ptype == "ambiguous_candidates":
            pending_ambiguous += 1
        elif ptype == "branch_of_existing":
            pending_branch += 1

    pending_dept = 0
    for p in dept_proposals:
        key = ("dept_alias", p.get("template_dept", ""))
        if key in decisions:
            continue
        ptype = p.get("proposal_type", "")
        # Only dept_alias_existing is approve-able in current UI; other dept
        # types are read-only so don't count as担当者 work.
        if ptype == "dept_alias_existing":
            pending_dept += 1

    # URL needed: count from gap report
    url_needed = 0
    if _DEFAULT_COMPETITION_GAP.exists():
        import csv
        with _DEFAULT_COMPETITION_GAP.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("gap_reason") in (
                    "school_no_document",
                    "school_doc_old_year_only",
                ):
                    url_needed += 1

    # Auto approved cumulatively (SchoolAlias rows from resolver / review queue).
    auto_approved = (
        session.query(func.count(SchoolAlias.id))
        .filter(
            SchoolAlias.source.in_(
                ("school_missing_resolver", "proposal_review_queue")
            ),
        )
        .scalar()
        or 0
    )

    # Excel staleness: are there approved-but-not-exported aliases?
    excel_path = _DEFAULT_COMPETITION
    if excel_path.exists():
        excel_mtime = datetime.fromtimestamp(
            excel_path.stat().st_mtime, tz=UTC
        )
        latest_alias_created = (
            session.query(func.max(SchoolAlias.created_at))
            .filter(
                SchoolAlias.source.in_(
                    ("school_missing_resolver", "proposal_review_queue")
                ),
            )
            .scalar()
        )
        if latest_alias_created is None:
            excel_stale = False
        else:
            latest_alias_created = _as_utc(latest_alias_created)
            now = datetime.now(UTC)
            excel_stale = (
                latest_alias_created > excel_mtime
                and now - latest_alias_created >= timedelta(minutes=30)
            )
    else:
        excel_stale = auto_approved > 0

    return TodoCounts(
        pending_ambiguous=pending_ambiguous,
        pending_branch=pending_branch,
        pending_dept=pending_dept,
        url_needed=url_needed,
        auto_approved=auto_approved,
        excel_stale=excel_stale,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def render_sidebar_todo(session: Session) -> None:
    """Render the live 今週のTODO block in Streamlit sidebar.

    Called from app.py AFTER the page radio so it always stays visible.
    """
    target_needs_action = 0
    try:
        from eidp.review._pages.school_year_tasks import school_task_summary

        target = school_task_summary(
            session,
            fiscal_year=settings.target_fiscal_year,
            school_type="専門学校",
        )
    except Exception:
        target = None

    try:
        counts = compute_todo_counts(session)
    except Exception as exc:  # pragma: no cover — UI must never crash
        st.sidebar.caption(f"TODO 計算失敗: {exc}")
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("**今週のやること**")
    if target is not None and target.total > 0:
        target_needs_action = target.needs_action
        _todo_line(
            "対象年度 要対応",
            target.needs_action,
            hint="① 学校別タスク",
            urgent=target.needs_action > 0,
        )
        _todo_line(
            "Excel出力可",
            target.excel_ready,
            hint="④ Excel",
            urgent=False,
            done=True,
        )
        _todo_line(
            "旧年度fallback",
            target.stale_fallback,
            hint="① 再取得",
            urgent=target.stale_fallback > 0,
        )

    total_pending = (
        counts.pending_ambiguous + counts.pending_branch + counts.pending_dept
    )
    _todo_line(
        "候補が複数で要承認",
        counts.pending_ambiguous,
        hint="詳細: 提案",
        urgent=counts.pending_ambiguous > 0,
    )
    _todo_line(
        "分校扱い（要確認）",
        counts.pending_branch,
        hint="詳細: 提案",
        urgent=False,
    )
    _todo_line(
        "学科の別名承認",
        counts.pending_dept,
        hint="詳細: 提案",
        urgent=counts.pending_dept > 0,
    )
    _todo_line(
        "URL追加が必要",
        counts.url_needed,
        hint="③ URL追加",
        urgent=counts.url_needed > 0,
    )
    _todo_line(
        "自動承認済（累計）",
        counts.auto_approved,
        hint=None,
        urgent=False,
        done=True,
    )

    if counts.excel_stale:
        st.sidebar.warning("新しい承認あり · ④ で再出力推奨", icon="⚠️")
    elif total_pending == 0 and counts.url_needed == 0 and target_needs_action == 0:
        st.sidebar.success("今週のTODOは完了", icon="✅")


def _todo_line(
    label: str,
    count: int,
    *,
    hint: str | None,
    urgent: bool,
    done: bool = False,
) -> None:
    """One line in sidebar TODO. Uses Streamlit columns for alignment."""
    c1, c2 = st.sidebar.columns([3, 1])
    if urgent:
        c1.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
        c2.markdown(
            f"<div style='text-align:right;color:#5E6AD2;font-weight:600;'>{count}</div>",
            unsafe_allow_html=True,
        )
    elif done:
        c1.markdown(
            f"<small style='color:#888'>{label}</small>", unsafe_allow_html=True
        )
        c2.markdown(
            f"<div style='text-align:right;color:#1F8B4C;'>{count}</div>",
            unsafe_allow_html=True,
        )
    else:
        c1.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
        c2.markdown(
            f"<div style='text-align:right;color:#4E4E52;'>{count}</div>",
            unsafe_allow_html=True,
        )
    if hint:
        st.sidebar.caption(hint)


# ---------------------------------------------------------------------------
# Proposals Review Queue (Phase 2 — School/Dept gap resolver approvals)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProposalDecision:
    decision: str  # approved | deferred | rejected
    proposal_kind: str  # school_alias | dept_alias
    template_name: str
    target_id: int | None
    operator_name: str
    note: str
    timestamp: str


def _read_proposals(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _record_decision(decision: ProposalDecision, audit_path: Path) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(decision), ensure_ascii=False) + "\n")


def _load_decision_index(audit_path: Path) -> dict[tuple[str, str], str]:
    """Return {(proposal_kind_prefix, template_name): latest_decision}.

    Keys use a kind PREFIX ('school_alias' or 'dept_alias') so both the
    auto-approved 'school_alias' and the picker-driven
    'school_alias_ambiguous_candidates' roll up to the same dedup key.
    """
    if not audit_path.exists():
        return {}
    out: dict[tuple[str, str], str] = {}
    try:
        with audit_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                kind_full = row.get("proposal_kind", "")
                kind_prefix = (
                    "dept_alias"
                    if kind_full.startswith("dept_alias")
                    else "school_alias"
                )
                key = (kind_prefix, row.get("template_name", ""))
                out[key] = row.get("decision", "")
    except OSError:
        return {}
    return out


def apply_school_alias_proposal(
    session: Session,
    *,
    school_id: int,
    alias_name: str,
    source: str = "proposal_review_queue",
) -> tuple[bool, str]:
    """Idempotent SchoolAlias insert with cross-school conflict check.

    Returns (created, reason). 'reason' values:
      - inserted                       : new row added
      - already_exists                 : same (school_id, alias_name) present
      - conflict_other_school:<id>     : alias is registered to a different
                                         school; refuse to insert. Matcher's
                                         ambiguity guard would otherwise flip
                                         the row to school_name_ambiguous.
      - empty_alias                    : alias_name is blank after strip
    """
    alias_name = alias_name.strip()
    if not alias_name:
        return False, "empty_alias"
    existing_same = (
        session.query(SchoolAlias)
        .filter(
            SchoolAlias.school_id == school_id,
            SchoolAlias.alias_name == alias_name,
        )
        .first()
    )
    if existing_same is not None:
        return False, "already_exists"
    conflict = (
        session.query(SchoolAlias)
        .filter(
            SchoolAlias.alias_name == alias_name,
            SchoolAlias.school_id != school_id,
        )
        .first()
    )
    if conflict is not None:
        return False, f"conflict_other_school:{conflict.school_id}"
    session.add(
        SchoolAlias(
            school_id=school_id,
            alias_name=alias_name,
            alias_type="competition_template",
            source=source,
        )
    )
    session.commit()
    return True, "inserted"


def apply_dept_alias_proposal(
    session: Session,
    *,
    department_id: int,
    old_name: str,
    source: str = "proposal_review_queue",
) -> tuple[bool, str]:
    """Record a dept alias as DepartmentChange(change_type='alias')."""
    old_name = old_name.strip()
    if not old_name:
        return False, "empty_old_name"
    dept = session.get(Department, department_id)
    if dept is None:
        return False, "dept_not_found"
    exists = (
        session.query(DepartmentChange)
        .filter(
            DepartmentChange.department_id == department_id,
            DepartmentChange.old_name == old_name,
            DepartmentChange.change_type == "alias",
        )
        .first()
    )
    if exists is not None:
        return False, "already_exists"
    session.add(
        DepartmentChange(
            department_id=department_id,
            change_type="alias",
            fiscal_year=datetime.now(UTC).year,
            old_name=old_name,
            new_name=dept.canonical_name,
            verified=False,
            verified_by=source,
            notes="competition_template dept alias proposed by resolver",
        )
    )
    session.commit()
    return True, "inserted"


_SCHOOL_PROPOSAL_LABEL = {
    "alias_existing_school": "一致候補が1つ（別名追加で即マッチ）",
    "ambiguous_candidates": "候補が複数（選択が必要）",
    "branch_of_existing": "分校扱いの行（本校はDBにあり・要注意）",
    "truly_missing": "DBに該当校なし（法人情報が必要・対応外）",
}


def _render_school_proposals_tab(session: Session) -> None:
    proposals = _read_proposals(_DEFAULT_SCHOOL_PROPOSALS)
    if not proposals:
        st.info(
            f"提案ファイルがありません: `{_DEFAULT_SCHOOL_PROPOSALS}`。"
            "先に `uv run python scripts/school_missing_resolver.py` を実行してください。"
        )
        return

    decisions = _load_decision_index(_DEFAULT_PROPOSAL_DECISIONS)
    hide_processed = st.session_state.get("hide_processed", True)

    by_type: dict[str, list[dict]] = {}
    for p in proposals:
        key = ("school_alias", p.get("template_name", ""))
        if hide_processed and key in decisions:
            continue
        by_type.setdefault(p.get("proposal_type", "?"), []).append(p)

    counts = {k: (len(v), sum(int(x.get("template_rows", 0)) for x in v))
              for k, v in by_type.items()}
    cols = st.columns(4)
    for idx, ptype in enumerate([
        "alias_existing_school",
        "ambiguous_candidates",
        "branch_of_existing",
        "truly_missing",
    ]):
        n, rows = counts.get(ptype, (0, 0))
        cols[idx].metric(
            _SCHOOL_PROPOSAL_LABEL.get(ptype, ptype),
            f"{n} 校",
            f"テンプレ {rows} 行",
        )

    # --- Mode toggle ---
    focus_items = (
        by_type.get("ambiguous_candidates", [])
        + by_type.get("branch_of_existing", [])
    )
    mode = st.radio(
        "モード",
        ["一覧モード（まとめて見る）", "集中モード（1件ずつ判断）"],
        horizontal=True,
        key="school_mode",
        help=(
            "一覧モードはスキャン用、集中モードは1件ずつじっくり判断したい時に使います。"
            f"集中モード対象: {len(focus_items)} 件"
        ),
    )
    if mode.startswith("集中"):
        _render_school_focus_mode(session, focus_items)
        return

    st.divider()
    st.subheader("自動承認OK：一致候補が1つだけの行")
    st.caption(
        "DB内に同じ学校が1つだけ見つかっている行です。"
        "「承認」を押すと別名として登録され、次のExcel出力で一致します。"
    )
    items_single = by_type.get("alias_existing_school", [])
    if not items_single:
        st.info("対象なし（処理済みの可能性あり）")
    for p in items_single:
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].write(
                f"**テンプレ名**: {p['template_name']}　"
                f"（テンプレ内 {p['template_rows']} 行）"
            )
            cols[0].caption(
                f"→ DBの一致校: id={p['matched_school_id']}　"
                f"`{p['matched_school_name']}`　"
                f"（法人: {p['matched_corporation']}）"
            )
            if cols[1].button(
                "承認",
                key=f"approve_sch_{p['matched_school_id']}_{p['template_name']}",
                type="primary",
            ):
                created, reason = apply_school_alias_proposal(
                    session,
                    school_id=p["matched_school_id"],
                    alias_name=p["template_name"],
                )
                _record_decision(
                    ProposalDecision(
                        decision="approved" if created else "already",
                        proposal_kind="school_alias",
                        template_name=p["template_name"],
                        target_id=p["matched_school_id"],
                        operator_name=st.session_state.get("operator_name", ""),
                        note=reason,
                        timestamp=datetime.now(UTC).isoformat(),
                    ),
                    _DEFAULT_PROPOSAL_DECISIONS,
                )
                if created:
                    st.success(
                        f"別名を登録しました: "
                        f"「{p['template_name']}」→ id={p['matched_school_id']}"
                    )
                elif reason == "already_exists":
                    st.info("すでに登録済みです（重複しません）")
                elif reason.startswith("conflict_other_school:"):
                    other_id = reason.split(":")[1]
                    st.error(
                        f"この別名はすでに別の学校 (id={other_id}) に使われています。"
                        "このまま登録すると照合が曖昧になるため中止しました。"
                    )
                else:
                    st.info(f"未実行: {reason}")

    st.divider()
    st.subheader("担当者の判断が必要な行")
    st.caption(
        "候補が複数ある場合は、正しいDBの学校を選んでから「承認」を押します。"
        "わからなければ「保留」でOK — あとで再確認できます。"
    )
    for ptype in ("ambiguous_candidates", "branch_of_existing"):
        items = by_type.get(ptype, [])
        if not items:
            continue
        st.markdown(
            f"### {_SCHOOL_PROPOSAL_LABEL.get(ptype, ptype)} — {len(items)}校"
        )
        if ptype == "branch_of_existing":
            st.warning(
                "⚠ **分校扱いの行**：テンプレートが本当に分校を指す場合、本校に別名を "
                "付けると分校のデータが本校に混ざります。分校がDB上の本校の一部として "
                "扱われているか確信が持てなければ「保留」にしてください。"
            )
        for p in items:
            _render_school_candidate_picker(session, p, ptype)

    truly = by_type.get("truly_missing", [])
    if truly:
        st.markdown(
            f"### {_SCHOOL_PROPOSAL_LABEL['truly_missing']} — {len(truly)}校（操作不可）"
        )
        st.caption(
            "これらの学校はDBに存在しません。新規登録には法人名・都道府県・文科省コード "
            "などの正確な情報が必要です。対応は次期作業に回します。"
        )
        for p in truly:
            st.caption(
                f"　・ {p['template_name']}（テンプレ内 {p['template_rows']} 行）"
            )


def _render_school_focus_mode(
    session: Session, focus_items: list[dict]
) -> None:
    """V2-inspired single-proposal focus card.

    One proposal at a time. Large template name, recommended candidate with
    reasoning, approve/defer/prev/next. Advances automatically after decision.
    """
    if not focus_items:
        st.success(
            "候補が複数の行 / 分校扱いの行は全て処理済みです。お疲れさまでした。",
            icon="✅",
        )
        return

    # Session-scoped pointer; clamp on re-render
    ptr = st.session_state.get("school_focus_idx", 0)
    ptr = max(0, min(ptr, len(focus_items) - 1))
    item = focus_items[ptr]

    total = len(focus_items)
    ptype = item.get("proposal_type", "")
    candidates = item.get("candidates") or []

    # Progress strip
    st.progress(
        (ptr + 1) / total,
        text=f"{ptr + 1} / {total} 件目",
    )

    safe_type_label = html.escape(_SCHOOL_PROPOSAL_LABEL.get(ptype, ptype), quote=True)
    safe_template_name = html.escape(str(item["template_name"]), quote=True)
    safe_template_rows = html.escape(str(item.get("template_rows", 0)), quote=True)

    # Custom V1 hero card — Streamlit's default container can't do serif 34px
    st.markdown(
        f"""
        <div class="eidp-focus-hero">
          <div class="eidp-focus-meta">
            <span>種別 · <b>{safe_type_label}</b></span>
            <span>影響 · <b>{safe_template_rows} 行</b></span>
            <span>候補 · <b>{len(candidates)} 件</b></span>
          </div>
          <div class="eidp-focus-name">{safe_template_name}</div>
          <div class="eidp-focus-rows">テンプレート内で {safe_template_rows} 行に登場</div>
          <div class="eidp-focus-divider">
            <span class="line"></span><span>正しい DB 学校を選択</span><span class="line"></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if ptype == "branch_of_existing":
            st.warning(
                "これは分校を指している可能性があります。本校に別名を付けると "
                "分校データが本校に混ざります。確信がなければ「保留」にしてください。",
                icon="⚠️",
            )

        if not candidates:
            st.caption("DB候補が見つかりませんでした。保留のみ選択できます。")
            choice = None
            picked = None
        else:
            # Build option labels + recommendation
            options = [
                f"id={c['school_id']}　·　{c['school_name']}　"
                f"（法人: {c['corporation']} / {c['prefecture']}）"
                for c in candidates
            ]
            # Default selection: 「まだ選んでいない」 for safety, forces operator intent
            choice = st.radio(
                "正しいDBの学校を選択",
                ["（まだ選んでいない）"] + options,
                key=f"focus_pick_{ptr}_{item.get('template_name', '')}",
                index=0,
            )
            if choice != "（まだ選んでいない）":
                picked = candidates[options.index(choice)]
            else:
                picked = None

            # Recommendation card (heuristic: first candidate is highest-ranked)
            rec = candidates[0]
            st.info(
                f"**推奨候補**　id={rec['school_id']}　{rec['school_name']}"
                f"　（{rec['corporation']} / {rec['prefecture']}）\n\n"
                "テンプレ名に最も近い法人系列・地名・学校種別から推定。"
                "確信がなければ他候補を選んでください。"
            )

        # Action row
        action_cols = st.columns([2, 1, 1, 1])
        if action_cols[0].button(
            "承認して次へ",
            type="primary",
            disabled=(picked is None),
            key=f"focus_approve_{ptr}",
            use_container_width=True,
        ):
            if picked is not None:
                created, reason = apply_school_alias_proposal(
                    session,
                    school_id=int(picked["school_id"]),
                    alias_name=item["template_name"],
                )
                _record_decision(
                    ProposalDecision(
                        decision="approved" if created else "already",
                        proposal_kind=f"school_alias_{ptype}",
                        template_name=item["template_name"],
                        target_id=int(picked["school_id"]),
                        operator_name=st.session_state.get("operator_name", ""),
                        note=reason,
                        timestamp=datetime.now(UTC).isoformat(),
                    ),
                    _DEFAULT_PROPOSAL_DECISIONS,
                )
                if reason.startswith("conflict_other_school:"):
                    other = reason.split(":")[1]
                    st.error(
                        f"別名はすでに別の学校 (id={other}) に使われています。"
                        "保留を選ぶか、別の候補を選んでください。"
                    )
                    return
                # The current item disappears after the decision is recorded.
                # Keep the same index so the next unprocessed item moves into view.
                st.session_state.school_focus_idx = _next_focus_idx_after_decision(ptr, total)
                st.rerun()

        if action_cols[1].button(
            "保留",
            key=f"focus_defer_{ptr}",
            use_container_width=True,
        ):
            _record_decision(
                ProposalDecision(
                    decision="deferred",
                    proposal_kind=f"school_alias_{ptype}",
                    template_name=item["template_name"],
                    target_id=None,
                    operator_name=st.session_state.get("operator_name", ""),
                    note="operator deferred (focus mode)",
                    timestamp=datetime.now(UTC).isoformat(),
                ),
                _DEFAULT_PROPOSAL_DECISIONS,
            )
            st.session_state.school_focus_idx = _next_focus_idx_after_decision(ptr, total)
            st.rerun()

        if action_cols[2].button(
            "← 前へ",
            disabled=(ptr == 0),
            key=f"focus_prev_{ptr}",
            use_container_width=True,
        ):
            st.session_state.school_focus_idx = max(0, ptr - 1)
            st.rerun()

        if action_cols[3].button(
            "スキップ →",
            disabled=(ptr >= total - 1),
            key=f"focus_skip_{ptr}",
            use_container_width=True,
        ):
            st.session_state.school_focus_idx = min(ptr + 1, total - 1)
            st.rerun()


def _next_focus_idx_after_decision(ptr: int, total: int) -> int:
    """Return the next index after the current proposal is removed."""
    if total <= 1:
        return 0
    return max(0, min(ptr, total - 2))


def _render_school_candidate_picker(
    session: Session, proposal: dict, ptype: str
) -> None:
    """Render one picker card with Approve / Defer buttons."""
    candidates = proposal.get("candidates") or []
    template = proposal["template_name"]
    rows = proposal.get("template_rows", 0)
    key_root = f"pick_{ptype}_{template}"

    with st.container(border=True):
        st.write(f"**テンプレ名**: {template}　（テンプレ内 {rows} 行）")
        if not candidates:
            st.caption("（DB候補なし — 保留推奨）")
            return

        options = [
            f"id={c['school_id']}　{c['school_name']}　"
            f"（法人: {c['corporation']} / {c['prefecture']}）"
            for c in candidates
        ]
        choice = st.selectbox(
            "正しいDB学校を選んでください：",
            ["（選択してください）"] + options,
            key=f"{key_root}_select",
        )

        col_a, col_d = st.columns(2)
        if col_a.button(
            "承認",
            key=f"{key_root}_approve",
            type="primary",
            disabled=choice == "（選択してください）",
        ):
            # Parse back to candidate dict
            idx = options.index(choice)
            picked = candidates[idx]
            created, reason = apply_school_alias_proposal(
                session,
                school_id=int(picked["school_id"]),
                alias_name=template,
            )
            _record_decision(
                ProposalDecision(
                    decision="approved" if created else "already",
                    proposal_kind=f"school_alias_{ptype}",
                    template_name=template,
                    target_id=int(picked["school_id"]),
                    operator_name=st.session_state.get("operator_name", ""),
                    note=reason,
                    timestamp=datetime.now(UTC).isoformat(),
                ),
                _DEFAULT_PROPOSAL_DECISIONS,
            )
            if created:
                st.success(
                    f"別名を登録しました: 「{template}」 → id={picked['school_id']} "
                    f"（{picked['school_name']}）"
                )
            elif reason == "already_exists":
                st.info("すでに登録済みです（重複しません）")
            elif reason.startswith("conflict_other_school:"):
                other_id = reason.split(":")[1]
                st.error(
                    f"この別名はすでに別の学校 (id={other_id}) に使われています。"
                    "競合を避けるため登録を中止しました。"
                )
            else:
                st.info(f"未実行: {reason}")

        if col_d.button("保留", key=f"{key_root}_defer"):
            _record_decision(
                ProposalDecision(
                    decision="deferred",
                    proposal_kind=f"school_alias_{ptype}",
                    template_name=template,
                    target_id=None,
                    operator_name=st.session_state.get("operator_name", ""),
                    note="operator deferred — needs more research",
                    timestamp=datetime.now(UTC).isoformat(),
                ),
                _DEFAULT_PROPOSAL_DECISIONS,
            )
            st.caption(f"保留しました: {template}")


def _render_dept_proposals_tab(session: Session) -> None:
    proposals = _read_proposals(_DEFAULT_DEPT_PROPOSALS)
    if not proposals:
        st.info(
            f"No proposals at `{_DEFAULT_DEPT_PROPOSALS}`. "
            "Run `uv run python scripts/dept_unmatched_resolver.py` first."
        )
        return

    decisions = _load_decision_index(_DEFAULT_PROPOSAL_DECISIONS)
    hide_processed = st.session_state.get("hide_processed", True)

    by_type: dict[str, list[dict]] = {}
    for p in proposals:
        key = ("dept_alias", p.get("template_dept", ""))
        if hide_processed and key in decisions:
            continue
        by_type.setdefault(p.get("proposal_type", "?"), []).append(p)

    _dept_proposal_label = {
        "dept_alias_existing": "別名追加で即マッチ（候補1つ）",
        "dept_group_candidate": "複数学科の合算行（今期は対応外）",
        "dept_ambiguous": "候補が複数（選択が必要）",
        "dept_truly_missing": "DBに該当学科なし",
    }

    cols = st.columns(4)
    for idx, ptype in enumerate([
        "dept_alias_existing",
        "dept_group_candidate",
        "dept_ambiguous",
        "dept_truly_missing",
    ]):
        items = by_type.get(ptype, [])
        cols[idx].metric(_dept_proposal_label.get(ptype, ptype), len(items))

    st.divider()
    st.subheader("自動承認OK：一致候補が1つだけの学科")
    items_single = by_type.get("dept_alias_existing", [])
    if not items_single:
        st.info("対象なし（処理済みか該当なし）")
    for p in items_single:
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].write(
                f"**{p['template_school']} / {p['template_dept']}**"
            )
            cols[0].caption(
                f"→ DBの一致学科: dept_id={p['db_dept_ids'][0]}　"
                f"`{p['db_dept_names'][0]}`"
            )
            key = f"approve_dept_{p['db_dept_ids'][0]}_{p['template_dept']}"
            if cols[1].button("承認", key=key, type="primary"):
                created, reason = apply_dept_alias_proposal(
                    session,
                    department_id=p["db_dept_ids"][0],
                    old_name=p["template_dept"],
                )
                _record_decision(
                    ProposalDecision(
                        decision="approved" if created else "already",
                        proposal_kind="dept_alias",
                        template_name=p["template_dept"],
                        target_id=p["db_dept_ids"][0],
                        operator_name=st.session_state.get("operator_name", ""),
                        note=reason,
                        timestamp=datetime.now(UTC).isoformat(),
                    ),
                    _DEFAULT_PROPOSAL_DECISIONS,
                )
                if created:
                    st.success(
                        f"学科別名を登録しました: 「{p['template_dept']}」 → "
                        f"dept_id={p['db_dept_ids'][0]}"
                    )
                elif reason == "already_exists":
                    st.info("すでに登録済みです（重複しません）")
                else:
                    st.info(f"未実行: {reason}")

    st.divider()
    st.subheader("担当者の判断が必要な学科（現時点では表示のみ）")
    st.caption(
        "複数学科の合算行 (例: HALの「高度情報学科(情報処理・WEB開発・AI)」) は "
        "合算ルールを別テーブルで管理する必要があるため、今期は対応外です。"
    )
    for ptype, items in by_type.items():
        if ptype == "dept_alias_existing":
            continue
        st.write(f"**{_dept_proposal_label.get(ptype, ptype)}** — {len(items)}件")
        for p in items[:10]:
            names = " ／ ".join(p.get("db_dept_names", [])[:3])
            st.caption(
                f"　・ [{p['template_school'][:20]}] {p['template_dept']}  → "
                f"候補: {names if names else '（なし）'}"
            )


def page_proposals_review(session: Session) -> None:
    st.header("② マッチング提案の確認")
    st.caption(
        "競合校テンプレートと DB の学校名・学科名を自動照合した結果です。"
        "「承認」するとその行は以降のExcel出力に反映されます。"
        "「保留」はDBに何も書かず、記録だけ残します。"
    )
    with st.expander("このページの使い方（初回は必読）", expanded=False):
        st.markdown(
            """
**目的**：競合校テンプレートの各行（= 学校×学科）をDBの正しいレコードに紐付ける。

**画面の見方**：
- **学校タブ**：テンプレートに書いてあるけどDBに一致しない「学校名」の一覧。
- **学科タブ**：学校は一致したが、学科名だけ合わない行の一覧。

**操作の流れ**：
1. 担当者名を入力（監査用 — 誰が承認したか記録されます）
2. 候補が1つだけ → 「承認」を押すだけ
3. 候補が複数 → セレクトで正しいものを選んでから「承認」
4. 自信がない → 「保留」（あとで再確認）

**注意**：
- `分校扱いの行` は警告が出ます。本校に紐付けると分校のデータが混ざるので、不確かなら保留してください。
- `DBに該当校なし` の行は法人情報が必要なため、現時点では対応外です（上長に報告）。
            """
        )
    st.text_input(
        "担当者名（監査ログに記録）",
        key="operator_name",
        value=st.session_state.get("operator_name", ""),
        placeholder="例: 山田",
    )
    st.checkbox(
        "処理済み（承認/保留）の行を隠す",
        key="hide_processed",
        value=st.session_state.get("hide_processed", True),
    )
    tab_school, tab_dept = st.tabs(
        ["学校タブ（学校名のマッチング）", "学科タブ（学科名のマッチング）"]
    )
    with tab_school:
        _render_school_proposals_tab(session)
    with tab_dept:
        _render_dept_proposals_tab(session)


def _decision_badge(decision: str) -> str:
    if decision == "approved":
        return ":green[APPROVED]"
    if decision == "deferred":
        return ":orange[DEFERRED]"
    if decision == "already":
        return ":gray[ALREADY]"
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tail_jsonl(path: Path, limit: int) -> list[dict]:
    out: list[dict] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out[-limit:]
