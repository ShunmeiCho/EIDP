"""Propose resolutions for every dept_unmatched row in the 競合校 gap CSV.

Does NOT write to DB. Outputs evidence for human review.

Proposal types:

  dept_alias_existing
      Template dept name has a single close DB dept. Minor variation
      like 学科↔科, full-width↔half-width. Emit DepartmentChange row
      with change_type='alias', old_name=template, related_dept_id=db.

  dept_group_candidate
      Template lumps multiple DB depts (e.g. HAL
      '高度情報学科(情報処理・WEB開発・AI)' maps to 3 DB sub-depts).
      Operator must create a 'dept group' mapping: template_name → list
      of dept_id. Competition exporter would SUM their yearly data.

  dept_truly_missing
      No DB dept matches. Usually means the dept was removed from the
      school's lineup or the PDF doesn't include it yet.

Heuristics:
  1. Exact / NFKC-NFKC match
  2. Suffix swap 学科↔科, strip full-half-width parens
  3. Paren content split: '高度情報学科(A・B・C)' → look for DB depts
     sharing stem '高度情報学科'
  4. Kana fold (ー/イ/ィ) reuse from matcher

Usage:
    uv run python scripts/dept_unmatched_resolver.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from eidp.db.models import Department, School, SchoolAlias
from eidp.db.session import SessionLocal
from eidp.excel.competition_exporter import _norm, _norm_dept_kana


_PAREN_RE = re.compile(r"[(（]([^)）]{1,80})[)）]")
_DEPT_SUFFIX_VARIANTS = ("学科", "科")


def _strip_suffix_pair(name: str) -> list[str]:
    """Return variants with 学科↔科 swapped so templates 'X学科' align with DB 'X科'."""
    variants = [name]
    for old, new in (("学科", "科"), ("科", "学科")):
        if name.endswith(old):
            variants.append(name[: -len(old)] + new)
    return variants


def _paren_tracks(name: str) -> tuple[str, list[str]]:
    """Split '高度情報学科(情報処理・WEB開発・AI)' into ('高度情報学科', ['情報処理','WEB開発','AI'])."""
    m = _PAREN_RE.search(name)
    if not m:
        return name, []
    stem = _PAREN_RE.sub("", name).strip()
    inside = m.group(1)
    tracks = [t.strip() for t in re.split(r"[・,、/／]", inside) if t.strip()]
    return stem, tracks


@dataclass
class DeptProposal:
    sheet: str
    template_school: str
    template_school_id: int
    template_dept: str
    template_rows: int
    proposal_type: str
    db_dept_ids: list[int] = field(default_factory=list)
    db_dept_names: list[str] = field(default_factory=list)
    reasoning: str = ""


def _dept_alias_search(
    template_dept: str, depts: list[Department]
) -> list[Department]:
    """Find DB depts that might be the same as template_dept (1-to-1)."""
    t = _norm(template_dept)
    t_kana = _norm_dept_kana(template_dept)
    hits: list[Department] = []
    seen: set[int] = set()

    # Tier 1: exact or suffix-swap equal
    variants = set(_strip_suffix_pair(t))
    for d in depts:
        dn = _norm(d.canonical_name)
        if dn in variants or t in variants and any(_norm(v) == dn for v in variants):
            if d.id not in seen:
                hits.append(d)
                seen.add(d.id)
    if hits:
        return hits

    # Tier 2: suffix swap + substring
    for d in depts:
        dn = _norm(d.canonical_name)
        for v in variants:
            if v and dn and (v == dn or (len(v) >= 4 and (v in dn or dn in v))):
                if d.id not in seen:
                    hits.append(d)
                    seen.add(d.id)
                    break
    if hits:
        return hits

    # Tier 3: kana fold equal
    for d in depts:
        if _norm_dept_kana(d.canonical_name) == t_kana and d.id not in seen:
            hits.append(d)
            seen.add(d.id)
    return hits


def _dept_group_search(
    template_dept: str, depts: list[Department]
) -> list[Department]:
    """Find DB depts that collectively represent the lumped template dept.

    Template '高度情報学科(情報処理・WEB開発・AI)' → DB depts whose
    canonical_name starts with '高度情報学科' AND whose paren content
    overlaps one of the tracks.
    """
    stem, tracks = _paren_tracks(template_dept)
    if not tracks:
        return []
    stem_norm = _norm(stem)
    stem_variants = set(_strip_suffix_pair(stem_norm))

    matches: list[Department] = []
    for d in depts:
        dn = _norm(d.canonical_name)
        if not any(dn.startswith(v) for v in stem_variants if v):
            continue
        # DB dept must have some paren content overlapping template tracks.
        db_stem, db_tracks_list = _paren_tracks(d.canonical_name)
        if not db_tracks_list:
            continue
        db_track_text = _norm(" ".join(db_tracks_list))
        for t in tracks:
            if _norm(t) and _norm(t) in db_track_text:
                matches.append(d)
                break
            # Also try substring in the other direction for short tokens
            if _norm(t) and db_track_text in _norm(t):
                matches.append(d)
                break
    return matches


def _resolve_school_id(
    session, school_name: str, school_id_hint: str
) -> tuple[int | None, str]:
    if school_id_hint and school_id_hint.isdigit():
        return int(school_id_hint), "hint"
    # fallback to School.school_name substring
    norm = _norm(school_name)
    for s in session.query(School).all():
        if _norm(s.school_name) == norm:
            return s.id, "exact"
    for s in session.query(School).all():
        if _norm(s.school_name) and norm and (_norm(s.school_name) in norm or norm in _norm(s.school_name)):
            return s.id, "substring"
    return None, "none"


def classify(session, row: dict) -> DeptProposal | None:
    school_id, via = _resolve_school_id(session, row["school_name"], row.get("school_id", ""))
    if school_id is None:
        return None
    depts = session.query(Department).filter(Department.school_id == school_id).all()
    if not depts:
        return DeptProposal(
            sheet=row["sheet"],
            template_school=row["school_name"],
            template_school_id=school_id,
            template_dept=row["dept_name"],
            template_rows=1,
            proposal_type="dept_truly_missing",
            reasoning=f"school resolved via {via} but has no departments",
        )

    alias_hits = _dept_alias_search(row["dept_name"], depts)
    group_hits = _dept_group_search(row["dept_name"], depts)

    if len(alias_hits) == 1:
        d = alias_hits[0]
        return DeptProposal(
            sheet=row["sheet"],
            template_school=row["school_name"],
            template_school_id=school_id,
            template_dept=row["dept_name"],
            template_rows=1,
            proposal_type="dept_alias_existing",
            db_dept_ids=[d.id],
            db_dept_names=[d.canonical_name],
            reasoning=f"single DB dept match via suffix/kana heuristics",
        )

    if group_hits:
        return DeptProposal(
            sheet=row["sheet"],
            template_school=row["school_name"],
            template_school_id=school_id,
            template_dept=row["dept_name"],
            template_rows=1,
            proposal_type="dept_group_candidate",
            db_dept_ids=[d.id for d in group_hits],
            db_dept_names=[d.canonical_name for d in group_hits],
            reasoning=(
                f"{len(group_hits)} DB depts share stem and paren-track content; "
                f"aggregate via dept group"
            ),
        )

    if len(alias_hits) > 1:
        return DeptProposal(
            sheet=row["sheet"],
            template_school=row["school_name"],
            template_school_id=school_id,
            template_dept=row["dept_name"],
            template_rows=1,
            proposal_type="dept_ambiguous",
            db_dept_ids=[d.id for d in alias_hits],
            db_dept_names=[d.canonical_name for d in alias_hits],
            reasoning=f"{len(alias_hits)} DB depts match; operator picks",
        )

    return DeptProposal(
        sheet=row["sheet"],
        template_school=row["school_name"],
        template_school_id=school_id,
        template_dept=row["dept_name"],
        template_rows=1,
        proposal_type="dept_truly_missing",
        reasoning="no DB dept matches by any heuristic",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gap", type=Path, default=Path("output/競合校gap-report.csv"))
    parser.add_argument(
        "--out-jsonl", type=Path,
        default=Path("output/dept_unmatched_proposals.jsonl"),
    )
    args = parser.parse_args()

    with args.gap.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["gap_reason"] == "dept_unmatched"]

    if not rows:
        print("no dept_unmatched rows")
        return

    session = SessionLocal()
    proposals: list[DeptProposal] = []
    try:
        for row in rows:
            p = classify(session, row)
            if p:
                proposals.append(p)
    finally:
        session.close()

    by_type: dict[str, list[DeptProposal]] = defaultdict(list)
    for p in proposals:
        by_type[p.proposal_type].append(p)

    print(f"# Dept Unmatched Resolver — {len(proposals)} rows")
    for ptype in (
        "dept_alias_existing",
        "dept_group_candidate",
        "dept_ambiguous",
        "dept_truly_missing",
    ):
        items = by_type.get(ptype, [])
        if not items:
            continue
        print(f"\n## {ptype} — {len(items)} rows")
        for p in items:
            print(
                f"  [{p.template_school[:20]:20s}] {p.template_dept[:40]:40s}"
            )
            for name in p.db_dept_names[:5]:
                print(f"      → {name}")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for p in proposals:
            rec = asdict(p)
            rec["timestamp"] = datetime.now(timezone.utc).isoformat()
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nFull evidence: {args.out_jsonl}")


if __name__ == "__main__":
    main()
