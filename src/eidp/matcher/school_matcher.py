"""MEXT school code matching — Step 3.

Reads MEXT school code CSVs (cp932), matches against school table
using NFKC normalization, updates school.school_code, creates school_alias.
"""

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolAlias

log = structlog.get_logger()


@dataclass(frozen=True)
class MextEntry:
    code: str
    school_type: str
    prefecture: str
    name: str
    address: str
    abolished_date: str


@dataclass
class MatchResult:
    school_id: int
    school_name: str
    prefecture: str
    corporation_name: str
    mext_code: str | None = None
    mext_name: str | None = None
    match_method: str | None = None  # exact, nfkc, pref_partial
    confidence: float = 0.0


@dataclass
class MatchReport:
    exact: list[MatchResult] = field(default_factory=list)
    nfkc: list[MatchResult] = field(default_factory=list)
    pref_partial: list[MatchResult] = field(default_factory=list)
    unmatched: list[MatchResult] = field(default_factory=list)

    @property
    def total_matched(self) -> int:
        return len(self.exact) + len(self.nfkc) + len(self.pref_partial)

    @property
    def total(self) -> int:
        return self.total_matched + len(self.unmatched)


def _normalize(name: str) -> str:
    """NFKC normalize + strip whitespace."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"\s+", "", name)
    return name


# Prefixes/suffixes commonly added in MEXT but absent in Excel (or vice versa)
_STRIP_PREFIXES = [
    "独立行政法人国立病院機構",
    "独立行政法人",
    "国立病院機構",
    "学校法人",
    "公益財団法人",
    "一般財団法人",
    "社会福祉法人",
    "医療法人",
]

_STRIP_INFIXES = [
    "&IT",
    "&スポーツ",
    "&テクノロジー",
    "&デザイン",
    "&ビジネス",
    "&AI",
]


def _normalize_aggressive(name: str) -> str:
    """NFKC + strip known org prefixes and name-change infixes."""
    name = _normalize(name)
    for pfx in _STRIP_PREFIXES:
        npfx = _normalize(pfx)
        if name.startswith(npfx):
            name = name[len(npfx):]
    for infix in _STRIP_INFIXES:
        ninfix = _normalize(infix)
        name = name.replace(ninfix, "")
    return name


def _extract_prefecture(pref_field: str) -> str:
    """Extract prefecture name from MEXT format like '01(北海道)'.

    Appends 県/府/道 suffix to match Excel format (e.g., 青森 -> 青森県).
    """
    m = re.search(r"\((.+?)\)", pref_field)
    name = m.group(1) if m else pref_field

    # MEXT uses short names (青森), Excel uses long names (青森県)
    # Normalize to Excel format
    if name in ("北海道", "東京都", "大阪府", "京都府"):
        return name
    if not name.endswith(("県", "府", "都", "道")):
        return name + "県"
    return name


def load_mext_entries(data_dir: Path) -> list[MextEntry]:
    """Load 専修学校 (H1) entries from MEXT school code CSVs."""
    entries: list[MextEntry] = []

    for fname in ["school_code_east.csv", "school_code_west.csv"]:
        fpath = data_dir / fname
        if not fpath.exists():
            log.warning("mext_csv_missing", path=str(fpath))
            continue

        with open(fpath, encoding="cp932") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                if len(row) < 6:
                    continue
                if "H1" not in row[1]:  # 専修学校 only
                    continue

                entries.append(
                    MextEntry(
                        code=row[0],
                        school_type=row[1],
                        prefecture=_extract_prefecture(row[2]),
                        name=row[5],
                        address=row[6] if len(row) > 6 else "",
                        abolished_date=row[9] if len(row) > 9 else "",
                    )
                )

    active = [e for e in entries if not e.abolished_date]
    log.info("mext_loaded", total=len(entries), active=len(active))
    return active


@dataclass
class MextIndices:
    by_name: dict[str, list[MextEntry]]
    by_normalized: dict[str, list[MextEntry]]
    by_aggressive: dict[str, list[MextEntry]]
    by_pref: dict[str, list[MextEntry]]


def build_indices(entries: list[MextEntry]) -> MextIndices:
    """Build lookup indices for matching."""
    by_name: dict[str, list[MextEntry]] = defaultdict(list)
    by_normalized: dict[str, list[MextEntry]] = defaultdict(list)
    by_aggressive: dict[str, list[MextEntry]] = defaultdict(list)
    by_pref: dict[str, list[MextEntry]] = defaultdict(list)

    for e in entries:
        by_name[e.name].append(e)
        by_normalized[_normalize(e.name)].append(e)
        by_aggressive[_normalize_aggressive(e.name)].append(e)
        by_pref[e.prefecture].append(e)

    return MextIndices(by_name=by_name, by_normalized=by_normalized, by_aggressive=by_aggressive, by_pref=by_pref)


def match_schools(session: Session, data_dir: Path) -> MatchReport:
    """Match all schools in DB against MEXT entries. Returns report."""
    entries = load_mext_entries(data_dir)
    idx = build_indices(entries)

    schools = session.query(School).all()
    report = MatchReport()

    for school in schools:
        result = MatchResult(
            school_id=school.id,
            school_name=school.school_name,
            prefecture=school.prefecture,
            corporation_name=school.corporation_name,
        )

        def _pick(candidates: list[MextEntry]) -> MextEntry:
            pref_hit = [c for c in candidates if c.prefecture == school.prefecture]
            return pref_hit[0] if pref_hit else candidates[0]

        # Strategy A: Exact name match
        if school.school_name in idx.by_name:
            winner = _pick(idx.by_name[school.school_name])
            result.mext_code = winner.code
            result.mext_name = winner.name
            result.match_method = "exact"
            result.confidence = 1.0
            report.exact.append(result)
            continue

        # Strategy B: NFKC normalized match
        norm = _normalize(school.school_name)
        if norm in idx.by_normalized:
            winner = _pick(idx.by_normalized[norm])
            result.mext_code = winner.code
            result.mext_name = winner.name
            result.match_method = "nfkc"
            result.confidence = 0.95
            report.nfkc.append(result)
            continue

        # Strategy C: Aggressive normalization (strip org prefixes + name-change suffixes)
        agg = _normalize_aggressive(school.school_name)
        if agg in idx.by_aggressive:
            candidates = idx.by_aggressive[agg]
            pref_hit = [c for c in candidates if c.prefecture == school.prefecture]
            if pref_hit:
                winner = pref_hit[0]
                result.mext_code = winner.code
                result.mext_name = winner.name
                result.match_method = "aggressive"
                result.confidence = 0.9
                report.pref_partial.append(result)
                continue

        # Strategy D: Prefecture + containment match
        pref_entries = idx.by_pref.get(school.prefecture, [])
        best_entry: MextEntry | None = None
        best_score = 0.0

        for e in pref_entries:
            e_norm = _normalize(e.name)
            if not e_norm or not norm:
                continue
            if norm in e_norm or e_norm in norm:
                score = min(len(norm), len(e_norm)) / max(len(norm), len(e_norm))
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_entry = e

        if best_entry is not None:
            result.mext_code = best_entry.code
            result.mext_name = best_entry.name
            result.match_method = "pref_partial"
            result.confidence = round(best_score, 3)
            report.pref_partial.append(result)
            continue

        report.unmatched.append(result)

    log.info(
        "matching_complete",
        exact=len(report.exact),
        nfkc=len(report.nfkc),
        pref_partial=len(report.pref_partial),
        unmatched=len(report.unmatched),
        total=report.total,
        match_rate=f"{report.total_matched / report.total * 100:.1f}%",
    )
    return report


def apply_matches(session: Session, report: MatchReport) -> dict[str, int]:
    """Write match results to DB: update school.school_code, create school_alias."""
    stats = {"codes_assigned": 0, "aliases_created": 0, "conflicts": 0}

    all_matched = report.exact + report.nfkc + report.pref_partial

    # Detect code conflicts (multiple schools -> same MEXT code)
    code_to_results: dict[str, list[MatchResult]] = defaultdict(list)
    for r in all_matched:
        if r.mext_code:
            code_to_results[r.mext_code].append(r)

    conflict_codes = {code for code, rs in code_to_results.items() if len(rs) > 1}

    # Only auto-apply exact and nfkc matches (validated strategies per design doc).
    # Aggressive and pref_partial go to review queue (Step 4/6).
    auto_apply = report.exact + report.nfkc
    needs_review = report.pref_partial
    stats["needs_review"] = len(needs_review)

    for r in auto_apply:
        if not r.mext_code:
            continue

        if r.mext_code in conflict_codes:
            stats["conflicts"] += 1
            log.warning(
                "code_conflict",
                code=r.mext_code,
                school=r.school_name,
                count=len(code_to_results[r.mext_code]),
            )
            continue

        school = session.get(School, r.school_id)
        if school is None:
            continue

        if school.school_code is None:
            school.school_code = r.mext_code
            stats["codes_assigned"] += 1

        if r.mext_name and r.mext_name != school.school_name:
            existing_alias = (
                session.query(SchoolAlias)
                .filter(SchoolAlias.school_id == r.school_id, SchoolAlias.alias_name == r.mext_name)
                .first()
            )
            if not existing_alias:
                alias = SchoolAlias(
                    school_id=r.school_id,
                    alias_name=r.mext_name,
                    alias_type="formal",
                    source="mext",
                )
                session.add(alias)
                stats["aliases_created"] += 1

    session.flush()
    log.info("matches_applied", **stats)
    return stats
