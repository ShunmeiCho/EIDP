"""Unified gap counters by kind.

Acceptance criterion #3 & supporting metric for sprint planning:
- url: schools missing any school_site row
- pdf: schools with site(s) but no Document
- extraction: documents ingested but DepartmentYearly missing for the doc
- competition: read latest competition gap_report CSV (fast path; auth source)
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from eidp.db.models import DepartmentYearly, Document, School, SchoolSite

GapKind = Literal["url", "pdf", "extraction", "competition"]

_DEFAULT_COMPETITION_GAP = Path("output/competition-gap-report.csv")


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


def _gaps_pdf(session: Session, school_type: str | None) -> GapsReport:
    q = session.query(School).filter(School.status == "active")
    if school_type:
        q = q.filter(School.school_type == school_type)
    schools = q.all()

    sids_with_site = {sid for (sid,) in session.query(SchoolSite.school_id).distinct()}
    sids_with_doc = {sid for (sid,) in session.query(Document.school_id).distinct()}

    entries: list[GapEntry] = []
    for s in schools:
        if s.id in sids_with_doc:
            continue
        reason = (
            "site_known_no_pdf" if s.id in sids_with_site else "no_site_no_pdf"
        )
        entries.append(
            GapEntry(
                school_id=s.id,
                school_name=s.school_name,
                reason=reason,
                detail=s.prefecture or "",
            )
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
        return GapsReport(
            kind="competition",
            total=0,
            by_reason={"_csv_missing": 0},
            sample=(),
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
        return _gaps_pdf(session, school_type)
    if kind == "extraction":
        if fiscal_year is None:
            raise ValueError("fiscal_year required for kind=extraction")
        return _gaps_extraction(session, fiscal_year)
    if kind == "competition":
        return _gaps_competition(competition_csv or _DEFAULT_COMPETITION_GAP)
    raise ValueError(f"unknown gap kind: {kind}")
