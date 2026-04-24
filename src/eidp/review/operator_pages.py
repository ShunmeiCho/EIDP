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
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    """Run the same safety/content gates used by discovery before DB insert."""
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
    if content[:5] != b"%PDF-":
        return OperatorUrlValidation(False, "unknown", "not_pdf_magic", http_status=status, size_bytes=size)

    file_hash = hashlib.sha256(content).hexdigest()
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
    """Validate a manually supplied PDF URL and insert/update SchoolSite."""
    clean_url = url.strip()
    timestamp = datetime.now(timezone.utc).isoformat()
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

    now = datetime.now(timezone.utc)
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
            url_type="pdf",
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
        site.url_type = site.url_type or "pdf"
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

    before_ids = {
        row[0]
        for row in session.query(Document.id)
        .filter(Document.school_id == school_id, Document.source_url == source_url)
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
    )
    session.flush()

    docs = (
        session.query(Document)
        .filter(Document.school_id == school_id, Document.source_url == source_url)
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
    st.header("Pipeline Status")
    st.caption("End-to-end ingestion health for the weekly担当者 run.")

    stats = _pipeline_stats(session)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Schools", stats["total_schools"])
    col2.metric("Documents", stats["total_documents"])
    col3.metric("Departments", stats["dept_rows"])
    col4.metric("Yearly rows", stats["dept_yearly_rows"])

    st.divider()
    st.subheader("Documents by ingest_status")
    status = stats["docs_by_status"]
    if status:
        st.bar_chart(status)
    else:
        st.info("No documents yet.")

    st.subheader("Documents by pdf_type")
    pdf_type = stats["docs_by_pdf_type"]
    if pdf_type:
        st.bar_chart(pdf_type)
    else:
        st.info("No pdf_type distribution yet.")

    st.subheader("Fiscal year coverage (ingested)")
    coverage = stats["coverage_by_year"]
    if coverage:
        rows = sorted(coverage.items(), key=lambda kv: (kv[0] or 0))
        st.dataframe(
            {"fiscal_year": [r[0] for r in rows], "docs": [r[1] for r in rows]},
            hide_index=True,
        )
    else:
        st.info("No ingested documents yet.")


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
    st.header("Excel Exports")
    st.caption("One-click regeneration for the two担当者 deliverables.")

    st.subheader("Master workbook")
    master_out = st.text_input(
        "Master output path",
        value=str(_DEFAULT_MASTER),
        key="master_out",
    )
    if st.button("Export Master Excel", type="primary", key="btn_master"):
        try:
            master_path = output_path(master_out, (".xlsx",))
            stats = _run_master_export(session, master_path)
            st.success(f"Exported: {master_out}")
            st.json(stats)
        except PathPolicyError as exc:
            st.error(f"Path rejected: {exc}")
        except Exception as exc:
            st.error(f"Export failed: {exc}")

    _offer_download_safe(master_out, (".xlsx",))

    st.divider()

    st.subheader("Competition workbook")
    comp_cols = st.columns(2)
    template_in = comp_cols[0].text_input(
        "Template path",
        value=str(_DEFAULT_TEMPLATE),
        key="comp_template",
    )
    comp_out = comp_cols[1].text_input(
        "Output path",
        value=str(_DEFAULT_COMPETITION),
        key="comp_out",
    )
    gap_out = st.text_input(
        "Gap report CSV",
        value=str(_DEFAULT_COMPETITION_GAP),
        key="comp_gap",
    )
    fy_pick = st.number_input(
        "Fiscal year (0 = auto-detect year with most rows)",
        min_value=0,
        value=0,
        step=1,
        key="comp_fy",
    )
    if st.button("Export Competition Excel", type="primary", key="btn_comp"):
        try:
            fy = None if int(fy_pick) == 0 else int(fy_pick)
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
            st.success(f"Exported: {comp_out}")
            st.json(result)
        except PathPolicyError as exc:
            st.error(f"Path rejected: {exc}")
        except Exception as exc:
            st.error(f"Export failed: {exc}")

    _offer_download_safe(comp_out, (".xlsx",))


def _offer_download(path: Path) -> None:
    if not path.exists():
        st.caption(f"(not generated yet: `{path}`)")
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

def page_url_submission(session: Session) -> None:
    st.header("URL 補足")
    st.caption("担当者が見つけた申請書 PDF を検証して SchoolSite に登録します。")

    with st.form("operator_url_submission"):
        school_id = st.number_input("school.id", min_value=1, step=1, value=1)
        url = st.text_input("PDF URL", placeholder="https://example.ac.jp/.../confirmation_application.pdf")
        operator_name = st.text_input("Operator", placeholder="担当者名 or initials")
        operator_note = st.text_area("Note", placeholder="掲載ページ、判断理由、年度メモなど", height=80)
        run_now = st.checkbox("登録後にこの school の operator_manual URL を discovery + ingest する", value=False)
        submitted = st.form_submit_button("Validate and register", type="primary")

    if not submitted:
        st.info("URL は入庫前に SSRF guard、HTTP/PDF validation、PDF content classifier を通します。")
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
    st.header("Competition Gap Report")
    st.caption(
        "Rows in the 競合校 template that did not match any DB school+dept. "
        "Use this to prioritise discovery / ingestion work."
    )

    gap_path = st.text_input(
        "Gap CSV path",
        value=str(_DEFAULT_COMPETITION_GAP),
        key="gap_path",
    )
    try:
        path = output_path(gap_path, (".csv",))
    except PathPolicyError as exc:
        st.error(f"Path rejected: {exc}")
        return
    if not path.exists():
        st.info(f"No gap report at `{path}`. Run Competition Excel export first.")
        return

    import csv

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    st.write(f"Total unmatched rows: **{len(rows)}**")
    if not rows:
        return

    # Filters
    sheet_names = sorted({r.get("sheet", "") for r in rows})
    school_terms = st.text_input("Filter by school name substring", key="gap_filter_school")
    sheets_pick = st.multiselect(
        "Sheet filter",
        sheet_names,
        default=sheet_names,
        key="gap_filter_sheet",
    )

    filtered = [
        r for r in rows
        if r.get("sheet", "") in sheets_pick
        and (not school_terms or school_terms in r.get("school_name", ""))
    ]
    st.write(f"Showing {len(filtered)} rows")
    st.dataframe(filtered, hide_index=True)


# ---------------------------------------------------------------------------
# Rejections (discovery evidence)
# ---------------------------------------------------------------------------

def page_rejections() -> None:
    st.header("Discovery Rejections")
    st.caption(
        "Every PDF candidate that discover-pdfs rejected (non_target, HTTP "
        "error, all-negative score, no candidates, etc.). Append-only JSONL."
    )

    log_path = st.text_input(
        "Rejection JSONL path",
        value=str(_DEFAULT_REJECTIONS),
        key="rej_path",
    )
    try:
        path = output_path(log_path, (".jsonl",))
    except PathPolicyError as exc:
        st.error(f"Path rejected: {exc}")
        return
    if not path.exists():
        st.info(f"No rejection log at `{path}`.")
        return

    limit = st.slider("Tail lines", 10, 1000, 200, 10, key="rej_limit")
    records = _tail_jsonl(path, limit)

    if not records:
        st.info("Log file is empty.")
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
        st.subheader("By reason")
        st.bar_chart(reason_counts)
    with cols[1]:
        st.subheader("Top 15 schools by rejection count")
        top = sorted(school_counts.items(), key=lambda kv: kv[1], reverse=True)[:15]
        st.dataframe(
            {"school_id": [t[0] for t in top], "rejections": [t[1] for t in top]},
            hide_index=True,
        )

    st.divider()
    st.subheader("Recent records")
    school_filter = st.text_input("Filter by school_id (blank = all)", key="rej_school_filter")
    reason_filter = st.multiselect(
        "Reason filter",
        sorted(reason_counts.keys()),
        default=sorted(reason_counts.keys()),
        key="rej_reason_filter",
    )
    shown = [
        r for r in records
        if (not school_filter or str(r.get("school_id", "")) == school_filter)
        and r.get("reason") in reason_filter
    ]
    st.write(f"Showing {len(shown)} records")
    st.dataframe(shown, hide_index=True)


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
            fiscal_year=datetime.now(timezone.utc).year,
            old_name=old_name,
            new_name=dept.canonical_name,
            verified=False,
            verified_by=source,
            notes="competition_template dept alias proposed by resolver",
        )
    )
    session.commit()
    return True, "inserted"


def _render_school_proposals_tab(session: Session) -> None:
    proposals = _read_proposals(_DEFAULT_SCHOOL_PROPOSALS)
    if not proposals:
        st.info(
            f"No proposals at `{_DEFAULT_SCHOOL_PROPOSALS}`. "
            "Run `uv run python scripts/school_missing_resolver.py` first."
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
        cols[idx].metric(ptype, f"{n} names", f"{rows} rows")

    st.divider()
    st.subheader("Auto-approvable: alias_existing_school")
    for p in by_type.get("alias_existing_school", []):
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].write(
                f"**{p['template_name']}** — {p['template_rows']} rows → "
                f"id={p['matched_school_id']} `{p['matched_school_name']}` "
                f"({p['matched_corporation']})"
            )
            if cols[1].button(
                "Approve",
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
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    _DEFAULT_PROPOSAL_DECISIONS,
                )
                if created:
                    st.success(f"Alias inserted: {p['template_name']} → id={p['matched_school_id']}")
                else:
                    st.info(f"No-op: {reason}")

    st.divider()
    st.subheader(
        "Operator decision required: ambiguous_candidates / branch_of_existing"
    )
    st.caption(
        "Pick the correct DB school from the candidates. Truly-missing rows "
        "stay read-only — creating a new school needs authoritative source "
        "data (corporation, prefecture, school_code)."
    )
    for ptype in ("ambiguous_candidates", "branch_of_existing"):
        items = by_type.get(ptype, [])
        if not items:
            continue
        st.markdown(f"### {ptype} — {len(items)} names")
        if ptype == "branch_of_existing":
            st.warning(
                "Branch rows detected. If the template refers to an actual "
                "branch campus, aliasing to the parent may lump branch data "
                "into parent. Prefer defer unless you know the branch is "
                "part of the parent in DB."
            )
        for p in items:
            _render_school_candidate_picker(session, p, ptype)

    truly = by_type.get("truly_missing", [])
    if truly:
        st.markdown(f"### truly_missing — {len(truly)} names (read-only)")
        for p in truly:
            st.caption(
                f"  [{p['template_rows']} rows] {p['template_name']}  "
                f"— needs authoritative corp + prefecture to insert"
            )


def _render_school_candidate_picker(
    session: Session, proposal: dict, ptype: str
) -> None:
    """Render one picker card with Approve / Defer buttons."""
    candidates = proposal.get("candidates") or []
    template = proposal["template_name"]
    rows = proposal.get("template_rows", 0)
    key_root = f"pick_{ptype}_{template}"

    with st.container(border=True):
        st.write(f"**{template}** — {rows} rows")
        if not candidates:
            st.caption("(no candidates — defer)")
            return

        options = [
            f"id={c['school_id']}  {c['school_name']}  ({c['corporation']}, {c['prefecture']})"
            for c in candidates
        ]
        choice = st.selectbox(
            "Select the correct DB school:",
            ["(pick one)"] + options,
            key=f"{key_root}_select",
        )

        col_a, col_d = st.columns(2)
        if col_a.button("Approve", key=f"{key_root}_approve", type="primary",
                        disabled=choice == "(pick one)"):
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
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                _DEFAULT_PROPOSAL_DECISIONS,
            )
            if created:
                st.success(
                    f"Alias inserted: {template} → id={picked['school_id']} "
                    f"({picked['school_name']})"
                )
            else:
                st.info(f"No-op: {reason}")

        if col_d.button("Defer", key=f"{key_root}_defer"):
            _record_decision(
                ProposalDecision(
                    decision="deferred",
                    proposal_kind=f"school_alias_{ptype}",
                    template_name=template,
                    target_id=None,
                    operator_name=st.session_state.get("operator_name", ""),
                    note="operator deferred — needs more research",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                _DEFAULT_PROPOSAL_DECISIONS,
            )
            st.caption(f"Deferred: {template}")


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

    cols = st.columns(4)
    for idx, ptype in enumerate([
        "dept_alias_existing",
        "dept_group_candidate",
        "dept_ambiguous",
        "dept_truly_missing",
    ]):
        items = by_type.get(ptype, [])
        cols[idx].metric(ptype, len(items))

    st.divider()
    st.subheader("Auto-approvable: dept_alias_existing")
    for p in by_type.get("dept_alias_existing", []):
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].write(
                f"**{p['template_school']} / {p['template_dept']}** → "
                f"dept_id={p['db_dept_ids'][0]} `{p['db_dept_names'][0]}`"
            )
            key = f"approve_dept_{p['db_dept_ids'][0]}_{p['template_dept']}"
            if cols[1].button("Approve", key=key, type="primary"):
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
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    _DEFAULT_PROPOSAL_DECISIONS,
                )
                if created:
                    st.success(f"DepartmentChange alias inserted: {p['template_dept']} → dept_id={p['db_dept_ids'][0]}")
                else:
                    st.info(f"No-op: {reason}")

    st.divider()
    st.subheader("Operator-decision required (read-only in this MVP)")
    for ptype, items in by_type.items():
        if ptype == "dept_alias_existing":
            continue
        st.write(f"**{ptype}** — {len(items)} rows")
        for p in items[:10]:
            names = " | ".join(p.get("db_dept_names", [])[:3])
            st.caption(
                f"  [{p['template_school'][:20]}] {p['template_dept']}  → {names}"
            )


def page_proposals_review(session: Session) -> None:
    st.header("Proposals Review Queue")
    st.caption(
        "Approve-or-defer gap resolution proposals from "
        "school_missing_resolver and dept_unmatched_resolver."
    )
    st.text_input(
        "Operator name (audit tag)",
        key="operator_name",
        value=st.session_state.get("operator_name", ""),
    )
    st.checkbox(
        "Hide already-processed proposals (approved/deferred)",
        key="hide_processed",
        value=st.session_state.get("hide_processed", True),
    )
    tab_school, tab_dept = st.tabs(
        ["School Missing", "Dept Unmatched"]
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
