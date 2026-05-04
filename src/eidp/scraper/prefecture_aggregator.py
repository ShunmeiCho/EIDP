"""Prefecture-level aggregator parsers (Sprint 8.3.a).

Promoted from ``scripts/spike_pref_aggregator.py``. The spike was a
read-only investigation; this module is the production path consumed by
``eidp prefecture-aggregate`` and other ingest workflows.

What this module does
---------------------
For each Japanese prefecture's official aggregation artifact
(typically a PDF or XLSX listing every 専門学校 in scope of the
高等教育の修学支援新制度), parse out:

  * school_name (raw + NFKC-normalized)
  * address / operator metadata
  * disclosure URL — including hidden URLs that live as PDF
    hyperlink annotations on the school name cell (Saitama, partial
    Aichi). pdfplumber's text-extraction silently misses those, so
    we use PyMuPDF's ``page.get_links()`` to recover them.
  * MEXT 学校番号 when the prefecture publishes one (Osaka).

Match each parsed school to the existing ``school`` row by:

  1. school_code (highest priority, gold standard for Osaka)
  2. exact name within prefecture
  3. NFKC-normalized name
  4. operator + substring overlap
  5. unique substring overlap within prefecture (Aichi index style)

Build a writer-plan describing per-school recommended actions
(``add`` / ``upgrade`` / ``noop`` / ``review``) so the apply step is
auditable.

Out of scope for 8.3.a
----------------------
* Writer-plan execution / DB writes — that lives behind the
  ``prefecture-aggregate --apply`` CLI in 8.3.c.
* Network fetching of prefecture artifacts — assumed downloaded.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pdfplumber

# --- Domain types ---------------------------------------------------------


@dataclass
class PrefSchool:
    """One school as parsed out of a prefecture artifact."""

    pref: str
    school_name_raw: str
    school_name_norm: str
    address: str
    operator_kind: str
    operator_name: str
    operator_address: str
    disclosure_url: str | None
    school_code: str | None = None  # MEXT 学校番号 (Osaka has it)


@dataclass
class MatchResult:
    pref_school: PrefSchool
    db_school_id: int | None
    match_strategy: str  # school_code | exact | nfkc | operator_pref | substring_pref | none
    db_school_name: str | None
    has_existing_url: bool
    is_new_url_candidate: bool


@dataclass
class PrefReport:
    pref: str
    pdf_path: str
    extracted_total: int = 0
    extracted_with_url: int = 0
    db_matched: int = 0
    db_unmatched: int = 0
    match_by_strategy: dict[str, int] = field(default_factory=dict)
    existing_url_coverage: int = 0
    new_url_candidates: int = 0
    url_quality_distribution: dict[str, int] = field(default_factory=dict)
    action_distribution: dict[str, int] = field(default_factory=dict)
    quality_upgrade_candidates: int = 0
    sample_unmatched: list[dict[str, Any]] = field(default_factory=list)
    sample_new_urls: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)


# --- Helpers --------------------------------------------------------------


_URL_RE = re.compile(r"https?://[^\s　 ]+")

# Disclosure-keyword heuristics for URL quality classification.
_DISCLOSURE_KEYWORDS = (
    "disclos", "joho", "kyufu", "shien", "youken", "yoken",
    "info", "support", "schoolguide", "valuation",
    "kakunin", "shinsei", "musho",
)


def norm(s: str | None) -> str:
    """NFKC-normalized + whitespace-stripped string."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("​", "")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def extract_url(cell: str | None) -> str | None:
    """Pull the first URL out of a free-text cell, or None."""
    if not cell:
        return None
    m = _URL_RE.search(cell)
    return m.group(0) if m else None


def clean_cell(cell: str | None) -> str:
    if not cell:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", cell).replace("​", "")).strip()


def is_header(row: list[str | None]) -> bool:
    """Detect repeated header / pref note rows we want to skip."""
    joined = "".join(str(c) for c in row if c)
    return any(k in joined for k in ("確認大学等", "学 校 名", "学校名"))


def classify_url_quality(url: str | None) -> str:
    """Categorise a disclosure URL into direct_pdf / disclosure / homepage / none."""
    if not url:
        return "none"
    lo = url.lower()
    if lo.endswith(".pdf"):
        return "direct_pdf"
    if any(k in lo for k in _DISCLOSURE_KEYWORDS):
        return "disclosure"
    return "homepage"


_QUALITY_RANK = {"direct_pdf": 3, "disclosure": 2, "homepage": 1, "none": 0}


def recommend_action(pref_quality: str, existing_qualities: list[str]) -> str:
    """Decide writer-plan action per matched school.

    Returns one of:
      * ``add``     — matched + PDF URL present + no existing URL
      * ``upgrade`` — matched + PDF URL strictly better quality than existing
      * ``noop``    — matched + PDF URL same/worse than existing, or no URL
    Caller handles ``review`` for unmatched schools.
    """
    if pref_quality == "none":
        return "noop"
    best_existing = max(
        (_QUALITY_RANK.get(q, 0) for q in existing_qualities), default=0,
    )
    if best_existing == 0:
        return "add"
    if _QUALITY_RANK[pref_quality] > best_existing:
        return "upgrade"
    return "noop"


# --- Hyperlink annotation extraction (Saitama-style) ----------------------


def extract_pdf_annotation_links(pdf_path: Path) -> dict[str, str]:
    """Extract hyperlink annotations keyed by anchor text (school name).

    Some prefecture PDFs (Saitama, partial Aichi) embed disclosure URLs as
    clickable hyperlink annotations on the school name cell rather than as
    plain text in the 備考 column. pdfplumber's text extraction does not
    surface those annotations; PyMuPDF's ``page.get_links()`` does.

    This is THE owner-mandated path for Saitama in Sprint 8.3 — without
    it, the 36 schools whose URLs are annotation-only would be silently
    dropped on every run.
    """
    import fitz  # type: ignore[import-not-found]  # pymupdf

    out: dict[str, str] = {}
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri") or ""
                rect = link.get("from")
                if not uri or not rect:
                    continue
                anchor_text = page.get_text("text", clip=rect).strip()
                if not anchor_text:
                    continue
                key = norm(anchor_text)
                if key and key not in out:
                    out[key] = uri
    finally:
        doc.close()
    return out


# --- Per-prefecture parsers -----------------------------------------------


def parse_tokyo(pdf_path: Path) -> list[PrefSchool]:
    """Tokyo: 8-column tables. URL = col[7]."""
    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 8 or is_header(row):
                        continue
                    school_name = (row[2] or "").strip()
                    if not school_name or school_name.isdigit():
                        continue
                    out.append(PrefSchool(
                        pref="tokyo",
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[3] or "").strip(),
                        operator_kind=(row[4] or "").strip(),
                        operator_name=(row[5] or "").strip(),
                        operator_address=(row[6] or "").strip(),
                        disclosure_url=extract_url(row[7]),
                    ))
    return out


def parse_5col(pdf_path: Path, pref: str) -> list[PrefSchool]:
    """Kanagawa / Saitama / Miyagi style: 5-column tables.

    URL priority:
      1. plain-text URL in 備考 column (col 4)
      2. PDF hyperlink annotation on the school-name cell — recovers
         ~36 Saitama schools that pdfplumber alone cannot see.
    """
    annotation_links = extract_pdf_annotation_links(pdf_path)

    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 5 or is_header(row):
                        continue
                    school_name = (row[0] or "").strip()
                    if not school_name:
                        continue

                    url = extract_url(row[4])
                    if not url:
                        url = annotation_links.get(norm(school_name))

                    out.append(PrefSchool(
                        pref=pref,
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[1] or "").strip(),
                        operator_kind="",
                        operator_name=(row[2] or "").strip(),
                        operator_address=(row[3] or "").strip(),
                        disclosure_url=url,
                    ))
    return out


def parse_7col_hokkaido(pdf_path: Path, pref: str = "hokkaido") -> list[PrefSchool]:
    """Hokkaido style: 7-col table, URL in col[5] (ホームページURL column)."""
    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 7 or is_header(row):
                        continue
                    school_name = (row[0] or "").strip()
                    if not school_name or "確認大学" in school_name:
                        continue
                    out.append(PrefSchool(
                        pref=pref,
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[1] or "").strip(),
                        operator_kind="",
                        operator_name=(row[2] or "").strip(),
                        operator_address=(row[3] or "").strip(),
                        disclosure_url=extract_url(row[5]),
                    ))
    return out


# --- Parser registry ------------------------------------------------------

# Public registry of supported prefectures and their parser callables. A
# CLI / pipeline layer can iterate this dict; each value is
# (parser_callable, expected_pref_key).
PARSERS: dict[str, Callable[[Path], list[PrefSchool]]] = {
    "tokyo": parse_tokyo,
    "kanagawa": lambda p: parse_5col(p, "kanagawa"),
    "saitama": lambda p: parse_5col(p, "saitama"),
    "miyagi": lambda p: parse_5col(p, "miyagi"),
    "fukuoka": lambda p: parse_5col(p, "fukuoka"),
    "hyogo": lambda p: parse_5col(p, "hyogo"),
    "shizuoka": lambda p: parse_5col(p, "shizuoka"),
    "okinawa": lambda p: parse_5col(p, "okinawa"),
    "hokkaido": parse_7col_hokkaido,
}


# Mapping pref-key (URL-safe) -> Japanese prefecture name as stored on
# School.prefecture.
PREF_KEY_TO_DB = {
    "tokyo": "東京都",
    "kanagawa": "神奈川県",
    "saitama": "埼玉県",
    "osaka": "大阪府",
    "fukuoka": "福岡県",
    "hyogo": "兵庫県",
    "shizuoka": "静岡県",
    "okinawa": "沖縄県",
    "miyagi": "宮城県",
    "hokkaido": "北海道",
    "niigata": "新潟県",
    "aichi": "愛知県",
}


def parse(pref: str, artifact_path: Path) -> list[PrefSchool]:
    """Public entry point — dispatch on ``pref`` to the right parser."""
    parser = PARSERS.get(pref)
    if parser is None:
        raise ValueError(
            f"No parser registered for prefecture {pref!r}. "
            f"Available: {sorted(PARSERS)}"
        )
    return parser(artifact_path)


# --- Matching (DB lookup) -------------------------------------------------


def build_indices(session, pref: str) -> tuple[dict[str, Any], dict[int, list[str]]]:
    """Pre-build (school_index, site_index) for a single prefecture.

    Done once per pref so per-school ``match_school`` is O(1) lookup
    instead of O(N) DB hits — the spike's perf work, preserved.
    """
    from eidp.db.models import School, SchoolSite

    db_pref = PREF_KEY_TO_DB.get(pref, pref)
    schools = (
        session.query(School)
        .filter(School.prefecture == db_pref, School.status == "active")
        .all()
    )
    school_index: dict[str, Any] = {"_all": schools}
    for s in schools:
        school_index[f"name:{s.school_name}"] = s
        school_index[f"nfkc:{norm(s.school_name)}"] = s
        if s.school_code:
            school_index[f"code:{s.school_code}"] = s

    school_ids = [s.id for s in schools]
    sites = (
        session.query(SchoolSite)
        .filter(SchoolSite.school_id.in_(school_ids))
        .all() if school_ids else []
    )
    site_index: dict[int, list[str]] = {}
    for site in sites:
        site_index.setdefault(site.school_id, []).append(site.url)
    return school_index, site_index


def match_school(
    pref_school: PrefSchool,
    school_index: dict[str, Any],
    site_index: dict[int, list[str]],
) -> MatchResult:
    """Cascading match: school_code → exact → nfkc → operator+substring →
    substring(unique). Returns the strongest hit or ``strategy='none'``."""
    match = None
    strategy = "none"

    if pref_school.school_code:
        by_code = school_index.get(f"code:{pref_school.school_code}")
        if by_code is not None:
            match, strategy = by_code, "school_code"

    if match is None:
        exact = school_index.get(f"name:{pref_school.school_name_raw}")
        if exact is not None:
            match, strategy = exact, "exact"

    if match is None:
        nfkc = school_index.get(f"nfkc:{pref_school.school_name_norm}")
        if nfkc is not None:
            match, strategy = nfkc, "nfkc"

    if match is None and pref_school.operator_name:
        op_norm = norm(pref_school.operator_name)
        cand = [
            s for s in school_index["_all"]
            if norm(s.corporation_name) == op_norm
            and (norm(s.school_name) in pref_school.school_name_norm
                 or pref_school.school_name_norm in norm(s.school_name))
        ]
        if len(cand) == 1:
            match, strategy = cand[0], "operator_pref"

    if match is None:
        cand = [
            s for s in school_index["_all"]
            if len(norm(s.school_name)) >= 6
            and (norm(s.school_name) in pref_school.school_name_norm
                 or pref_school.school_name_norm in norm(s.school_name))
        ]
        if len(cand) == 1:
            match, strategy = cand[0], "substring_pref"

    existing_urls = site_index.get(match.id, []) if match else []
    has_url = bool(existing_urls)
    is_new = bool(pref_school.disclosure_url and match and not has_url)

    return MatchResult(
        pref_school=pref_school,
        db_school_id=match.id if match else None,
        match_strategy=strategy,
        db_school_name=match.school_name if match else None,
        has_existing_url=has_url,
        is_new_url_candidate=is_new,
    )


# --- Writer-plan ----------------------------------------------------------


def build_report(
    pref: str,
    artifact_path: Path,
    results: list[MatchResult],
    site_index: dict[int, list[str]],
) -> PrefReport:
    """Assemble a PrefReport with per-school records + aggregate stats.

    The ``records`` list is the writer-plan: one entry per parsed school
    with ``recommended_action`` set to add / upgrade / noop / review.
    Apply step (Sprint 8.3.c) consumes this without re-running parsing.
    """
    rep = PrefReport(pref=pref, pdf_path=str(artifact_path))
    by_strat: dict[str, int] = {}
    quality_dist: dict[str, int] = {}
    action_dist: dict[str, int] = {}

    for r in results:
        rep.extracted_total += 1
        if r.pref_school.disclosure_url:
            rep.extracted_with_url += 1
        if r.db_school_id is not None:
            rep.db_matched += 1
        else:
            rep.db_unmatched += 1
        by_strat[r.match_strategy] = by_strat.get(r.match_strategy, 0) + 1

        url_quality = classify_url_quality(r.pref_school.disclosure_url)
        quality_dist[url_quality] = quality_dist.get(url_quality, 0) + 1

        existing_urls = site_index.get(r.db_school_id, []) if r.db_school_id else []
        if existing_urls:
            rep.existing_url_coverage += 1
        existing_qualities = [classify_url_quality(u) for u in existing_urls]

        if r.match_strategy == "none":
            action = "review"
        else:
            action = recommend_action(url_quality, existing_qualities)
        action_dist[action] = action_dist.get(action, 0) + 1
        if action == "upgrade":
            rep.quality_upgrade_candidates += 1

        if r.is_new_url_candidate:
            rep.new_url_candidates += 1
            if len(rep.sample_new_urls) < 5:
                rep.sample_new_urls.append({
                    "school": r.db_school_name,
                    "url": r.pref_school.disclosure_url,
                })
        if r.match_strategy == "none" and len(rep.sample_unmatched) < 5:
            rep.sample_unmatched.append({
                "pdf_name": r.pref_school.school_name_raw,
                "operator": r.pref_school.operator_name,
            })

        rep.records.append({
            "db_school_id": r.db_school_id,
            "db_school_name": r.db_school_name,
            "pdf_school_name": r.pref_school.school_name_raw,
            "pdf_school_code": r.pref_school.school_code,
            "pdf_address": r.pref_school.address,
            "pdf_operator": r.pref_school.operator_name,
            "pref_url": r.pref_school.disclosure_url,
            "url_quality": url_quality,
            "match_strategy": r.match_strategy,
            "existing_urls": existing_urls,
            "existing_url_quality": existing_qualities,
            "is_new_url_candidate": r.is_new_url_candidate,
            "quality_upgrade_candidate": (action == "upgrade"),
            "recommended_action": action,
        })

    rep.match_by_strategy = by_strat
    rep.url_quality_distribution = quality_dist
    rep.action_distribution = action_dist
    return rep


def aggregate(
    session,
    pref: str,
    artifact_path: Path,
) -> PrefReport:
    """Top-level entry: parse + match + report. No DB writes — apply in
    Sprint 8.3.c."""
    parsed = parse(pref, artifact_path)
    school_index, site_index = build_indices(session, pref)
    results = [match_school(p, school_index, site_index) for p in parsed]
    return build_report(pref, artifact_path, results, site_index)


def apply_writer_plan(session, report: PrefReport) -> dict[str, int]:
    """Apply ``add`` / ``upgrade`` recommendations from a PrefReport.

    Sprint 8.3 contract: ``add`` inserts a new SchoolSite with
    ``discovery_method='prefecture_aggregator'`` and ``confidence=0.95``.
    ``upgrade`` updates the existing site to point at the better URL
    (preserves historical urls via SchoolSite append? — no, current
    SchoolSite has no revision contract; we just overwrite the URL of
    the lowest-quality existing site, since prefecture data is the
    authoritative source for disclosure URL).

    Caller is responsible for ``session.commit()`` so we sit inside a
    larger transaction if needed.
    """
    from eidp.db.models import SchoolSite

    stats = {"added": 0, "upgraded": 0, "skipped": 0}
    for record in report.records:
        action = record["recommended_action"]
        school_id = record["db_school_id"]
        new_url = record["pref_url"]
        if action == "noop" or action == "review" or not school_id or not new_url:
            stats["skipped"] += 1
            continue

        if action == "add":
            session.add(SchoolSite(
                school_id=school_id,
                url=new_url,
                url_type="disclosure",
                discovery_method="prefecture_aggregator",
                confidence=0.95,
            ))
            stats["added"] += 1
        elif action == "upgrade":
            # Find the lowest-quality existing site for this school and
            # repoint it; alternative would be marking it inactive but
            # SchoolSite has no soft-delete column today.
            existing_sites = (
                session.query(SchoolSite)
                .filter(SchoolSite.school_id == school_id)
                .all()
            )
            if existing_sites:
                worst = min(
                    existing_sites,
                    key=lambda s: _QUALITY_RANK.get(classify_url_quality(s.url), 0),
                )
                worst.url = new_url
                worst.discovery_method = "prefecture_aggregator"
                worst.confidence = 0.95
                worst.url_type = "disclosure"
            stats["upgraded"] += 1
    return stats
