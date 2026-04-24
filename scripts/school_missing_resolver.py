"""Propose resolutions for every school_missing row in the 競合校 gap CSV.

Does NOT write to DB. Produces:
  1. stdout per-school proposal table
  2. output/school_missing_proposals.jsonl — audit trail
  3. SQL INSERT block for proposals classified as 'alias_existing_school'

Proposal types (descending confidence / descending automation):

  alias_existing_school
      Template name resolves to exactly one existing School row via
      paren-strip, suffix-strip, or substring. Emit SchoolAlias row.

  branch_of_existing
      Template name has a branch marker (澁谷/渋谷/キャンパス) and a
      parent school with the same stem exists. Operator must confirm
      whether to CREATE a new branch School row or alias to parent.

  ambiguous_candidates
      Multiple School rows could match (e.g. same name, different
      corporation). Operator must pick.

  truly_missing
      No existing School matches. Requires fresh School INSERT with
      corporation / prefecture provided by operator.

The script deliberately STOPS at propose; nothing is committed to DB.
Review the JSONL, then approve via Web UI 'School Resolver' page (next
sprint) or run the SQL block manually with BEGIN/COMMIT.

Usage:
    uv run python scripts/school_missing_resolver.py
    uv run python scripts/school_missing_resolver.py --gap output/競合校gap-report.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from eidp.db.models import School, SchoolAlias
from eidp.db.session import SessionLocal


_BRANCH_MARKERS = ("渋谷", "キャンパス", "分校", "本校")
_PAREN_RE = re.compile(r"[(（]([^)）]{1,20})[)）]")
_SUFFIX_TRIM = ("専門学校", "高等専門学校", "専修学校", "大学校", "学校", "大学", "専門")

# 旧字体 → 新字体 (common educational institution name variants)
# NFKC does NOT fold these — schools frequently use the historical form
# in branch names (澁谷 instead of 渋谷) so operators pick up both.
_KYUJITAI_MAP = str.maketrans({
    "澁": "渋",
    "櫻": "桜",
    "廣": "広",
    "舊": "旧",
    "學": "学",
    "藝": "芸",
    "體": "体",
    "國": "国",
})


def _nfkc_strip(s: str) -> str:
    text = unicodedata.normalize("NFKC", s or "")
    text = text.translate(_KYUJITAI_MAP)
    return re.sub(r"\s+", "", text)


def _strip_paren(s: str) -> tuple[str, str | None]:
    """Return (name_without_paren_content, paren_content_if_any)."""
    m = _PAREN_RE.search(s)
    if not m:
        return s, None
    return _PAREN_RE.sub("", s), m.group(1)


def _strip_suffix(s: str) -> str:
    """Trim one education-institution suffix if the result stays non-trivial."""
    for suf in _SUFFIX_TRIM:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            return s[: -len(suf)]
    return s


def _branch_marker(s: str) -> str | None:
    """Detect branch marker after kyujitai fold (澁→渋 etc.)."""
    normalized = _nfkc_strip(s)
    for m in _BRANCH_MARKERS:
        if m in normalized:
            return m
    return None


@dataclass
class Proposal:
    template_name: str
    template_rows: int
    proposal_type: str
    matched_school_id: int | None = None
    matched_school_name: str | None = None
    matched_corporation: str | None = None
    candidates: list[dict[str, object]] = field(default_factory=list)
    reasoning: str = ""
    paren_content: str | None = None


def _candidate_schools(
    template_name: str, schools: list[School]
) -> list[tuple[int, str, str, str]]:
    """Return list of (school_id, school_name, corporation, prefecture).

    Priority-ordered matching: if a stronger heuristic finds hits, skip
    weaker ones to avoid inflating candidates with irrelevant parents.
    """
    tmpl = _nfkc_strip(template_name)
    tmpl_paren_stripped, paren = _strip_paren(template_name)
    tmpl_paren_stripped = _nfkc_strip(tmpl_paren_stripped)
    tmpl_short = _strip_suffix(tmpl_paren_stripped)
    paren_norm = _nfkc_strip(paren) if paren else None

    def _tuple(s: School) -> tuple[int, str, str, str]:
        return s.id, s.school_name, s.corporation_name, s.prefecture

    # Tier 1: exact / paren-stripped equality
    tier1 = [s for s in schools
             if _nfkc_strip(s.school_name) in (tmpl, tmpl_paren_stripped)]
    if tier1:
        return [_tuple(s) for s in tier1]

    # Tier 2: paren content disambiguates — DB must contain stem AND paren
    if paren_norm:
        tier2 = [
            s for s in schools
            if paren_norm in _nfkc_strip(s.school_name)
            and tmpl_short and tmpl_short in _nfkc_strip(s.school_name)
        ]
        if tier2:
            return [_tuple(s) for s in tier2]

    # Tier 3: substring both ways on suffix-stripped form.
    # Branch-marker guard: if template has a branch marker (渋谷 etc.), the
    # DB school must contain the SAME branch marker, otherwise we'd
    # silently alias a branch to its parent main campus (unsafe).
    tmpl_branch = _branch_marker(_nfkc_strip(template_name))
    tier3: list[School] = []
    for s in schools:
        db_norm = _nfkc_strip(s.school_name)
        db_short = _strip_suffix(db_norm)
        if not (tmpl_short and db_short):
            continue
        if not (tmpl_short in db_short or db_short in tmpl_short):
            continue
        if tmpl_branch and tmpl_branch not in db_norm:
            # Template references a branch; DB candidate lacks it → reject.
            continue
        tier3.append(s)
    return [_tuple(s) for s in tier3]


def classify(template_name: str, rows: int, schools: list[School]) -> Proposal:
    branch = _branch_marker(template_name)
    candidates = _candidate_schools(template_name, schools)

    if len(candidates) == 1:
        sid, sname, corp, _pref = candidates[0]
        p = Proposal(
            template_name=template_name,
            template_rows=rows,
            proposal_type="alias_existing_school",
            matched_school_id=sid,
            matched_school_name=sname,
            matched_corporation=corp,
            reasoning=(
                f"single DB candidate matched via paren/suffix/substring; "
                f"propose SchoolAlias '{template_name}' → school_id={sid}"
            ),
        )
        _, paren = _strip_paren(template_name)
        p.paren_content = paren
        return p

    if len(candidates) > 1:
        return Proposal(
            template_name=template_name,
            template_rows=rows,
            proposal_type="ambiguous_candidates",
            candidates=[
                {"school_id": sid, "school_name": sname, "corporation": corp, "prefecture": pref}
                for sid, sname, corp, pref in candidates
            ],
            reasoning=f"{len(candidates)} DB candidates match; operator must pick",
        )

    if branch:
        # No direct match, but has branch marker. Try parent search by
        # stripping every kyujitai-equivalent form of the branch marker.
        parent_name = template_name
        for form in {branch, *(k for k, v in {"澁": "渋"}.items() if v == branch[0]) }:
            parent_name = parent_name.replace(form, "")
        # Also handle 澁谷 → 渋谷 in raw form
        if branch == "渋谷":
            parent_name = parent_name.replace("澁谷", "")
        parent_candidates = _candidate_schools(parent_name, schools)
        return Proposal(
            template_name=template_name,
            template_rows=rows,
            proposal_type="branch_of_existing" if parent_candidates else "truly_missing",
            candidates=[
                {"school_id": sid, "school_name": sname, "corporation": corp, "prefecture": pref}
                for sid, sname, corp, pref in parent_candidates
            ],
            reasoning=(
                f"branch marker '{branch}' detected; "
                f"{len(parent_candidates)} parent candidates found"
                if parent_candidates
                else f"branch marker '{branch}' detected, no parent in DB"
            ),
        )

    return Proposal(
        template_name=template_name,
        template_rows=rows,
        proposal_type="truly_missing",
        reasoning="no DB School matches by any heuristic",
    )


def _read_missing_rows(gap_path: Path) -> Counter:
    counts: Counter = Counter()
    with gap_path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["gap_reason"] == "school_missing":
                counts[r["school_name"]] += 1
    return counts


def _emit_report(proposals: list[Proposal]) -> None:
    by_type: dict[str, list[Proposal]] = {}
    for p in proposals:
        by_type.setdefault(p.proposal_type, []).append(p)

    print(f"# School Missing Resolver — {len(proposals)} distinct template names")
    for ptype in (
        "alias_existing_school",
        "ambiguous_candidates",
        "branch_of_existing",
        "truly_missing",
    ):
        items = by_type.get(ptype, [])
        total_rows = sum(p.template_rows for p in items)
        print(
            f"\n## {ptype} — {len(items)} names, {total_rows} template rows"
        )
        for p in sorted(items, key=lambda x: x.template_rows, reverse=True):
            header = f"  [{p.template_rows:>3} rows] {p.template_name}"
            if p.matched_school_id:
                header += (
                    f"  →  id={p.matched_school_id} "
                    f"{p.matched_school_name} ({p.matched_corporation})"
                )
            print(header)
            if p.candidates:
                for c in p.candidates:
                    print(
                        f"        candidate: id={c['school_id']} "
                        f"{c['school_name']} ({c['corporation']}, {c['prefecture']})"
                    )

    aliases = by_type.get("alias_existing_school", [])
    if aliases:
        total = sum(p.template_rows for p in aliases)
        # Emit two blocks: preflight conflict check + idempotent INSERT.
        # SchoolAlias has NO UniqueConstraint(school_id, alias_name) in
        # models.py — a plain 'ON CONFLICT DO NOTHING' would not deduplicate.
        proposed_values = []
        for p in aliases:
            esc = (p.template_name or "").replace("'", "''")
            proposed_values.append(f"  ({p.matched_school_id}, '{esc}')")
        values_block = ",\n".join(proposed_values)

        print(
            f"\n# PREFLIGHT — expect 0 rows; any row means the alias is "
            f"already pointing to a different school:"
        )
        print("WITH proposed(school_id, alias_name) AS (VALUES")
        print(values_block)
        print(")")
        print(
            "SELECT p.alias_name, p.school_id AS proposed_school_id,"
            " sa.school_id AS existing_school_id"
        )
        print("FROM proposed p")
        print("JOIN school_alias sa ON sa.alias_name = p.alias_name")
        print("WHERE sa.school_id <> p.school_id;")

        print(
            f"\n# Idempotent INSERT — recovers up to {total} template rows:"
        )
        print(
            "INSERT INTO school_alias (school_id, alias_name, alias_type, source)"
        )
        print(
            "SELECT p.school_id, p.alias_name,"
            " 'competition_template', 'school_missing_resolver'"
        )
        print("FROM (VALUES")
        print(values_block)
        print(") AS p(school_id, alias_name)")
        print("WHERE NOT EXISTS (")
        print(
            "  SELECT 1 FROM school_alias sa"
            " WHERE sa.school_id = p.school_id AND sa.alias_name = p.alias_name"
        )
        print(");")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gap",
        type=Path,
        default=Path("output/競合校gap-report.csv"),
    )
    parser.add_argument(
        "--out-jsonl",
        type=Path,
        default=Path("output/school_missing_proposals.jsonl"),
    )
    args = parser.parse_args()

    missing = _read_missing_rows(args.gap)
    if not missing:
        print(f"No school_missing rows in {args.gap}")
        return

    session = SessionLocal()
    try:
        schools = session.query(School).all()

        proposals: list[Proposal] = []
        for name, count in missing.most_common():
            proposals.append(classify(name, count, schools))

        _emit_report(proposals)

        args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.out_jsonl.open("w", encoding="utf-8") as fh:
            for p in proposals:
                rec = asdict(p)
                rec["timestamp"] = datetime.now(timezone.utc).isoformat()
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"\nFull evidence: {args.out_jsonl}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
