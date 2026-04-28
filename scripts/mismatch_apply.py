"""Sprint 5 D'-2: classify school_mismatch documents and (with --apply) act on them.

Reads:
  - DB: Document.ingest_status='school_mismatch'
  - output/ingest_rejections.jsonl  (parsed_school_name from recent ingests)
  - output/mismatch-backfill-*.jsonl (parsed_school_name backfilled for legacy)

Classifies each mismatch doc into:
  safe_alias      — parsed_name normalizes to expected name (NFKC + space
                    + paren strip); auto-aliasable if no conflict.
  normalize_fix   — parsed_name == expected_name after _norm() strip; the
                    real fix is to canonicalise _norm in the parser, not
                    add an alias. Reported but not applied here.
  twin_doc_dup    — same source_url already ingested for a different
                    sibling school; doc is a duplicate, not a real
                    mismatch. Suggest moving school_id or marking as
                    'support_only'.
  similar_alias   — parsed_name has high (>= 0.85) char-similarity to
                    expected; likely OCR/typo. Aliasable with explicit
                    --accept-similar gate.
  parser_error    — parsed_name is junk (e.g. '設置認可年月日',
                    '校名は不明'); no aliasing possible.
  wrong_school    — parsed_name clearly belongs to a different school in
                    the same DB; needs school_id reassignment.
  defer           — anything else; manual review.

By default this script is read-only and writes
output/mismatch-classification-{ts}.csv. Pass --apply to actually create
SchoolAlias rows for the safe_alias bucket; --accept-similar widens
apply to similar_alias too. --apply requires explicit owner authorization.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Document, School, SchoolAlias  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402

REJECTION_LOG = REPO_ROOT / "output/ingest_rejections.jsonl"
OUT_DIR = REPO_ROOT / "output"

JUNK_PARSED_PATTERNS = [
    "設置認可年月日",
    "学校教育法",
    "設置者",
    "学則",
    "校名は不明",
    "様式第",
]


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("​", "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[（）()【】「」『』\"　]", "", s)
    return s.strip()


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def load_parsed_names() -> dict[int, str]:
    """Return doc_id -> parsed_school_name from both rejection log and backfill."""
    out: dict[int, str] = {}

    if REJECTION_LOG.exists():
        with REJECTION_LOG.open() as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("reason") != "school_mismatch":
                    continue
                detail = d.get("detail") or {}
                name = detail.get("parsed_school_name")
                if name:
                    out[int(d["doc_id"])] = name

    for backfill_path in sorted(OUT_DIR.glob("mismatch-backfill-*.jsonl")):
        with backfill_path.open() as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = d.get("parsed_school_name")
                if name and d.get("doc_id") not in out:
                    out[int(d["doc_id"])] = name

    return out


def classify(
    parsed: str,
    expected: str,
    twin_already_ingested: bool,
    name_collision_other_school: str | None,
) -> tuple[str, str]:
    """Return (bucket, note)."""
    if not parsed:
        return "defer", "no parsed_name in any log"

    if any(j in parsed for j in JUNK_PARSED_PATTERNS):
        return "parser_error", f"parsed contains junk pattern: {parsed[:30]}"

    if twin_already_ingested:
        return "twin_doc_dup", "same source_url already ingested for sibling school"

    np = _norm(parsed)
    ne = _norm(expected)

    if np == ne:
        return "normalize_fix", "exact match after NFKC + space/paren strip"

    if np in ne or ne in np:
        # Substring: missing a few chars, e.g. '古屋医専' vs '名古屋医専'
        sim = similarity(np, ne)
        if sim >= 0.80:
            return "safe_alias", f"substring containment, sim={sim:.2f}"
        return "similar_alias", f"substring containment, sim={sim:.2f} (low)"

    sim = similarity(np, ne)
    if sim >= 0.92:
        return "safe_alias", f"high similarity {sim:.2f}"
    if sim >= 0.85:
        return "similar_alias", f"medium similarity {sim:.2f}"

    if name_collision_other_school:
        return "wrong_school", f"parsed matches sibling: {name_collision_other_school}"

    return "defer", f"low similarity {sim:.2f} and no obvious twin/sibling"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write SchoolAlias rows for safe_alias bucket",
    )
    parser.add_argument(
        "--accept-similar",
        action="store_true",
        help="Also write rows for similar_alias bucket (requires --apply)",
    )
    args = parser.parse_args()

    parsed_map = load_parsed_names()
    print(f"[classify] loaded parsed_names for {len(parsed_map)} docs")

    session = SessionLocal()
    try:
        all_mismatch = (
            session.query(Document)
            .filter(Document.ingest_status == "school_mismatch")
            .order_by(Document.school_id, Document.id)
            .all()
        )

        # Twin detection: same source_url ingested for a different school
        ingested_urls = {
            row.source_url
            for row in session.query(Document)
            .filter(Document.ingest_status == "ingested")
            .all()
        }

        # School name -> id index for collision detection
        all_schools = session.query(School).all()
        norm_name_index: dict[str, int] = {}
        for sch in all_schools:
            norm_name_index[_norm(sch.school_name)] = sch.id

        rows: list[dict] = []
        bucket_counts: dict[str, int] = defaultdict(int)

        for d in all_mismatch:
            sch = session.get(School, d.school_id)
            expected = sch.school_name if sch else ""
            parsed = parsed_map.get(d.id, "")
            twin = d.source_url in ingested_urls
            np = _norm(parsed)
            collision_sid = norm_name_index.get(np)
            collision_name = None
            if collision_sid and collision_sid != d.school_id:
                other = session.get(School, collision_sid)
                collision_name = f"sid={collision_sid} name={other.school_name if other else '?'}"

            bucket, note = classify(parsed, expected, twin, collision_name)
            bucket_counts[bucket] += 1
            rows.append({
                "doc_id": d.id,
                "school_id": d.school_id,
                "expected_school": expected,
                "parsed_school_name": parsed,
                "bucket": bucket,
                "note": note,
                "source_url": d.source_url,
            })

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = OUT_DIR / f"mismatch-classification-{ts}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
                "doc_id", "school_id", "expected_school", "parsed_school_name",
                "bucket", "note", "source_url",
            ])
            writer.writeheader()
            writer.writerows(rows)
        print(f"[classify] CSV -> {out_path}")
        print("[classify] bucket counts:")
        for k, v in sorted(bucket_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {k:<16} {v}")

        if not args.apply:
            print("\n[dry-run] no DB writes. Pass --apply to write SchoolAlias rows for safe_alias.")
            return

        # Apply phase: only safe_alias (and similar_alias if --accept-similar)
        apply_buckets = {"safe_alias"}
        if args.accept_similar:
            apply_buckets.add("similar_alias")

        added = 0
        skipped_dup = 0
        conflicts = 0
        for r in rows:
            if r["bucket"] not in apply_buckets:
                continue
            sid = r["school_id"]
            alias_name = r["parsed_school_name"].strip()
            if not alias_name:
                continue
            existing = (
                session.query(SchoolAlias)
                .filter(SchoolAlias.alias_name == alias_name)
                .first()
            )
            if existing and existing.school_id == sid:
                skipped_dup += 1
                continue
            if existing and existing.school_id != sid:
                conflicts += 1
                continue
            session.add(SchoolAlias(
                school_id=sid,
                alias_name=alias_name,
                alias_type="pdf_school_name",
                source="mismatch_apply",
            ))
            added += 1
        session.commit()
        print(f"\n[apply] added={added} skipped_existing={skipped_dup} conflicts={conflicts}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
