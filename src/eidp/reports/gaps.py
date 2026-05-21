"""Unified gap counters by kind.

Acceptance criterion #3 & supporting metric for sprint planning:
- url: schools missing any school_site row
- pdf: schools whose Document state blocks downstream extraction. Reason
  taxonomy is fine-grained so each sprint can attack a distinct cause:
    no_site_no_pdf       — no school_site, no Document
    site_known_no_pdf    — site(s) registered, zero Document
    stale_pdf_only       — has target+ingested Document but only for prev FYs
    non_target_only      — Documents exist, all classified non_target
    mismatch_only        — Documents exist, all flagged school_mismatch
    parse_failed_only    — Documents exist, all in parse_failed
    transient_error_only — only transient errors (retry queue)
    permanent_error_only — only permanent errors (extractor cannot handle)
    no_file_only         — discovery succeeded but file never downloaded
    ocr_pending_only     — OCR pipeline pending; not yet extracted
    support_only         — only support_recipient extracted, no dept_yearly
    in_progress_only     — currently being processed (transient state)
    other_only           — unclassified status (extend taxonomy if seen)
- extraction: documents ingested but DepartmentYearly missing for the doc
- competition: read latest competition gap_report CSV (fast path; auth source)
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import DepartmentYearly, Document, School, SchoolSite

GapKind = Literal["url", "pdf", "extraction", "competition"]

_DEFAULT_COMPETITION_GAP = Path("output/競合校gap-report.csv")


@dataclass(frozen=True)
class GapEntry:
    school_id: int | None
    school_name: str | None
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class GapsReport:
    kind: GapKind
    total: int
    by_reason: dict[str, int]
    sample: tuple[GapEntry, ...]  # first 50 for preview


def _to_report(
    kind: GapKind, entries: list[GapEntry], sample_size: int = 50
) -> GapsReport:
    by_reason: dict[str, int] = {}
    for e in entries:
        by_reason[e.reason] = by_reason.get(e.reason, 0) + 1
    return GapsReport(
        kind=kind,
        total=len(entries),
        by_reason=by_reason,
        sample=tuple(entries[:sample_size]),
    )


def _gaps_url(session: Session, school_type: str | None) -> GapsReport:
    q = session.query(School).filter(School.status == "active")
    if school_type:
        q = q.filter(School.school_type == school_type)
    schools = q.all()

    sids_with_site = {sid for (sid,) in session.query(SchoolSite.school_id).distinct()}
    entries = [
        GapEntry(
            school_id=s.id,
            school_name=s.school_name,
            reason="no_school_site",
            detail=s.prefecture or "",
        )
        for s in schools
        if s.id not in sids_with_site
    ]
    return _to_report("url", entries)


_STATUS_REASON: dict[str, str] = {
    "school_mismatch": "mismatch_only",
    "parse_failed": "parse_failed_only",
    "transient_error": "transient_error_only",
    "permanent_error": "permanent_error_only",
    "no_file": "no_file_only",
    "ocr_pending": "ocr_pending_only",
    "support_only": "support_only",
    "in_progress": "in_progress_only",
    "non_target": "non_target_only",
    "pending": "in_progress_only",
}


def _classify_pdf_state(
    docs: list[tuple[int | None, str | None, str | None]],
    fy: int,
) -> str | None:
    """Return gap reason for a school's Document set, or None if it has a
    valid current-FY target PDF (no gap).

    Priority: ingested-target-current-fy > ingested-target-stale >
    non_target classification > status-based bucketing.
    """
    if not docs:
        return None

    has_target_current = any(
        pdf_type == "target" and status == "ingested" and d_fy == fy
        for d_fy, status, pdf_type in docs
    )
    if has_target_current:
        return None

    has_target_any = any(
        pdf_type == "target" and status == "ingested"
        for _d_fy, status, pdf_type in docs
    )
    if has_target_any:
        return "stale_pdf_only"

    has_non_target_ingested = any(
        status == "ingested" and pdf_type != "target"
        for _d_fy, status, pdf_type in docs
    )
    if has_non_target_ingested:
        return "non_target_only"

    statuses = {status for _d_fy, status, _pt in docs}
    statuses.discard(None)
    statuses.discard("ingested")  # already handled above

    for preferred in (
        "ocr_pending",
        "in_progress",
        "school_mismatch",
        "transient_error",
        "permanent_error",
        "parse_failed",
        "no_file",
        "support_only",
        "non_target",
        "pending",
    ):
        if preferred in statuses:
            return _STATUS_REASON[preferred]

    return "other_only"


def _gaps_pdf(
    session: Session, school_type: str | None, fiscal_year: int | None
) -> GapsReport:
    fy = fiscal_year if fiscal_year is not None else settings.target_fiscal_year
    q = session.query(School).filter(School.status == "active")
    if school_type:
        q = q.filter(School.school_type == school_type)
    schools = q.all()

    sids_with_site = {sid for (sid,) in session.query(SchoolSite.school_id).distinct()}
    docs_by_school: dict[int, list[tuple[int | None, str | None, str | None]]] = {}
    for sid, dfy, status, pdf_type in session.query(
        Document.school_id,
        Document.fiscal_year,
        Document.ingest_status,
        Document.pdf_type,
    ).all():
        docs_by_school.setdefault(sid, []).append((dfy, status, pdf_type))

    entries: list[GapEntry] = []
    for s in schools:
        docs = docs_by_school.get(s.id, [])
        if not docs:
            reason = "site_known_no_pdf" if s.id in sids_with_site else "no_site_no_pdf"
            entries.append(
                GapEntry(s.id, s.school_name, reason, s.prefecture or "")
            )
            continue
        classified = _classify_pdf_state(docs, fy)
        if classified is None:
            continue
        entries.append(
            GapEntry(s.id, s.school_name, classified, s.prefecture or "")
        )
    return _to_report("pdf", entries)


def _gaps_extraction(session: Session, fiscal_year: int) -> GapsReport:
    docs_with_yearly = {
        d
        for (d,) in session.query(DepartmentYearly.document_id)
        .filter(DepartmentYearly.document_id.isnot(None))
        .distinct()
    }
    rows = (
        session.query(Document)
        .filter(
            Document.ingest_status == "ingested",
            Document.fiscal_year == fiscal_year,
        )
        .all()
    )
    entries = [
        GapEntry(
            school_id=d.school_id,
            school_name=None,
            reason="ingested_no_yearly_rows",
            detail=f"document_id={d.id}",
        )
        for d in rows
        if d.id not in docs_with_yearly
    ]
    return _to_report("extraction", entries)


def _gaps_competition(csv_path: Path) -> GapsReport:
    if not csv_path.exists():
        return _to_report(
            "competition",
            [
                GapEntry(
                    school_id=None,
                    school_name=None,
                    reason="_csv_missing",
                    detail=str(csv_path),
                )
            ],
        )
    entries: list[GapEntry] = []
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sid_raw = row.get("school_id") or ""
            try:
                sid = int(sid_raw) if sid_raw else None
            except ValueError:
                sid = None
            entries.append(
                GapEntry(
                    school_id=sid,
                    school_name=row.get("school_name") or None,
                    reason=row.get("gap_reason") or "unknown",
                    detail=row.get("gap_detail") or "",
                )
            )
    return _to_report("competition", entries)


def compute_gaps(
    session: Session,
    kind: GapKind,
    *,
    school_type: str | None = "専門学校",
    fiscal_year: int | None = None,
    competition_csv: Path | None = None,
) -> GapsReport:
    if kind == "url":
        return _gaps_url(session, school_type)
    if kind == "pdf":
        return _gaps_pdf(session, school_type, fiscal_year)
    if kind == "extraction":
        if fiscal_year is None:
            raise ValueError("fiscal_year required for kind=extraction")
        return _gaps_extraction(session, fiscal_year)
    if kind == "competition":
        return _gaps_competition(competition_csv or _DEFAULT_COMPETITION_GAP)
    raise ValueError(f"unknown gap kind: {kind}")
