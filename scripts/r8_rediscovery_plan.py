"""Sprint 4 planner: enumerate stale_pdf_only schools and emit a
ready-to-run discover-pdfs command (read-only).

A school is 'stale' if it has at least one Document with pdf_type=target
and ingest_status=ingested for some fiscal year, but NO such Document
for current_target_year (FY2026 in Apr-Mar 2026).

For these schools, discover-pdfs is expected to revisit each
school_site URL and find any newly-published R8 PDF. The Sprint 1
prefecture_aggregator URLs are the most likely to yield R8 wins because
they are the freshest and most-trusted set.

Output:
  output/r8-rediscovery-plan-{ts}.json — list of {school_id, prefecture,
  current_fys, n_sites, methods}.

Usage:
    uv run python scripts/r8_rediscovery_plan.py
        [--methods prefecture_aggregator]   # restrict to one or more methods
        [--limit N]                          # cap number of schools
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Document, School, SchoolSite  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402

OUT_DIR = REPO_ROOT / "output"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--methods",
        nargs="*",
        default=None,
        help="Restrict to specific discovery_method values "
             "(prefecture_aggregator | web_search | corporation_pattern | "
             "seed_csv | pattern_probe). Default: all methods.",
    )
    parser.add_argument(
        "--current-fy",
        type=int,
        default=2026,
        help="Fiscal year that defines staleness (default 2026).",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        target_docs = (
            session.query(Document)
            .filter(
                Document.pdf_type == "target",
                Document.ingest_status == "ingested",
            )
            .all()
        )
        by_school: dict[int, list[int]] = {}
        for d in target_docs:
            by_school.setdefault(d.school_id, []).append(d.fiscal_year or 0)

        stale_sids = [
            sid for sid, fys in by_school.items() if args.current_fy not in fys
        ]
        if args.limit:
            stale_sids = stale_sids[: args.limit]
        print(f"[plan] stale schools (no FY{args.current_fy} target ingested): {len(stale_sids)}")

        sites = (
            session.query(SchoolSite, School)
            .join(School, SchoolSite.school_id == School.id)
            .filter(SchoolSite.school_id.in_(stale_sids))
            .all()
        )
        per_school: dict[int, dict] = {}
        for site, sch in sites:
            row = per_school.setdefault(site.school_id, {
                "school_id": site.school_id,
                "school_name": sch.school_name,
                "prefecture": sch.prefecture,
                "current_fys": sorted(set(by_school.get(site.school_id, []))),
                "methods": [],
                "n_sites": 0,
            })
            row["n_sites"] += 1
            if site.discovery_method and site.discovery_method not in row["methods"]:
                row["methods"].append(site.discovery_method)

        rows = list(per_school.values())
        if args.methods:
            wanted = set(args.methods)
            rows = [r for r in rows if any(m in wanted for m in r["methods"])]
            print(f"[plan] after --methods filter ({wanted}): {len(rows)} schools")

        # Method tallies
        method_count: Counter = Counter()
        for r in rows:
            for m in r["methods"]:
                method_count[m] += 1
        print("[plan] schools-with-method breakdown:")
        for m, n in method_count.most_common():
            print(f"  {m:<25} {n}")

        # FY tallies
        fy_count: Counter = Counter()
        for r in rows:
            for fy in r["current_fys"]:
                fy_count[fy] += 1
        print("[plan] their existing FY distribution (target ingested):")
        for fy, n in sorted(fy_count.items()):
            print(f"  FY{fy} {n}")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = OUT_DIR / f"r8-rediscovery-plan-{ts}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "current_fy": args.current_fy,
            "methods_filter": args.methods,
            "school_count": len(rows),
            "schools": rows,
        }, ensure_ascii=False, indent=2))
        print(f"\n[plan] -> {out_path}")

        # Convenience: emit ready-to-run discover-pdfs command
        sids = [r["school_id"] for r in rows]
        if sids:
            print("\n[plan] suggested discover command (read-only crawl):")
            method_arg = ""
            if args.methods:
                method_arg = f" --discovery-method {','.join(args.methods)}"
            print(f"  uv run eidp discover-pdfs{method_arg} --batch-size {len(sids)} \\")
            print("  " + " ".join(f"--school-id {s}" for s in sids[:10]) + " ...")
            print(f"  (full {len(sids)} ids in JSON above)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
