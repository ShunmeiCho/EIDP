"""Stage 2 dry-run: generate writer plan from spike records.

Reads output/pref-aggregator/{pref}.json (from spike_pref_aggregator.py),
produces output/pref-aggregator/{pref}-writer-plan.json — the authoritative
Stage-2 instruction set for `eidp pref-apply` (not yet implemented).

The plan is the SOURCE OF TRUTH for what Stage 2 `--apply` will do to
school_site. This script does NOT touch the DB.

Per-operation format:
    op=add      — school matched, has no existing URL → insert new SchoolSite
    op=upgrade  — school matched, PDF URL strictly better quality than best
                  existing URL → insert new SchoolSite (preserve old rows)
    op=noop     — PDF URL not better than existing (or PDF URL missing) →
                  skip; no DB change
    op=review   — PDF school not matched to DB → queue for manual triage

Confidence calibration (per Codex #4 feedback):
    direct_pdf  → 0.95  (one hop to 様式第2号, strongest signal)
    disclosure  → 0.90  (disclosure hub page, 1-2 hops to target)
    homepage    → 0.70  (school root, multiple hops)

url_type calibration:
    direct_pdf  → "direct_pdf"
    disclosure  → "disclosure"
    homepage    → "homepage"
    none        → n/a (no plan entry)

verified=false on all new rows — Stage 3 will HTTP-verify before flipping.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPIKE_OUT_DIR = REPO_ROOT / "output" / "pref-aggregator"

CONFIDENCE_BY_QUALITY = {
    "direct_pdf": 0.95,
    "disclosure": 0.90,
    "homepage": 0.70,
    "none": 0.0,
}

URL_TYPE_BY_QUALITY = {
    "direct_pdf": "direct_pdf",
    "disclosure": "disclosure",
    "homepage": "homepage",
    "none": "unknown",
}


@dataclass
class Operation:
    op: str  # add | upgrade | noop | review
    reason: str | None = None
    school_id: int | None = None
    school_name: str | None = None
    pdf_school_name: str | None = None
    pdf_school_code: str | None = None
    pdf_operator: str | None = None
    match_strategy: str | None = None
    new_url: str | None = None
    new_url_type: str | None = None
    new_confidence: float | None = None
    existing_urls_preserved: list[str] = field(default_factory=list)
    existing_url_quality: list[str] = field(default_factory=list)


@dataclass
class WriterPlan:
    pref: str
    source_pdf: str
    generated_at: str
    operations: list[Operation] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def record_to_operation(rec: dict) -> Operation:
    action = rec.get("recommended_action", "noop")
    quality = rec.get("url_quality", "none")

    # review: no DB match
    if action == "review":
        return Operation(
            op="review",
            reason="no DB match" if rec.get("match_strategy") == "none" else "ambiguous match",
            pdf_school_name=rec.get("pdf_school_name"),
            pdf_school_code=rec.get("pdf_school_code"),
            pdf_operator=rec.get("pdf_operator"),
            match_strategy=rec.get("match_strategy"),
            new_url=rec.get("pref_url"),
            new_url_type=URL_TYPE_BY_QUALITY.get(quality),
        )

    # noop: matched but not actionable
    if action == "noop":
        return Operation(
            op="noop",
            reason="PDF URL absent or not strictly better than existing",
            school_id=rec.get("db_school_id"),
            school_name=rec.get("db_school_name"),
            match_strategy=rec.get("match_strategy"),
            existing_urls_preserved=rec.get("existing_urls") or [],
            existing_url_quality=rec.get("existing_url_quality") or [],
        )

    # add/upgrade: matched + actionable
    return Operation(
        op=action,
        reason={
            "add": "school has no existing URL; insert from prefecture PDF",
            "upgrade": "PDF URL is strictly higher quality than any existing",
        }.get(action, ""),
        school_id=rec.get("db_school_id"),
        school_name=rec.get("db_school_name"),
        pdf_school_name=rec.get("pdf_school_name"),
        pdf_school_code=rec.get("pdf_school_code"),
        match_strategy=rec.get("match_strategy"),
        new_url=rec.get("pref_url"),
        new_url_type=URL_TYPE_BY_QUALITY.get(quality),
        new_confidence=CONFIDENCE_BY_QUALITY.get(quality, 0.0),
        existing_urls_preserved=rec.get("existing_urls") or [],
        existing_url_quality=rec.get("existing_url_quality") or [],
    )


def build_plan(pref: str) -> WriterPlan:
    spike_path = SPIKE_OUT_DIR / f"{pref}.json"
    if not spike_path.exists():
        raise FileNotFoundError(f"spike output missing: {spike_path} — run spike_pref_aggregator.py first")
    spike = json.loads(spike_path.read_text())

    plan = WriterPlan(
        pref=pref,
        source_pdf=spike["pdf_path"],
        generated_at=datetime.now().isoformat(),
    )

    op_counts: dict[str, int] = {"add": 0, "upgrade": 0, "noop": 0, "review": 0}
    for rec in spike.get("records", []):
        op = record_to_operation(rec)
        plan.operations.append(op)
        op_counts[op.op] = op_counts.get(op.op, 0) + 1

    plan.summary = {
        "total_operations": len(plan.operations),
        "op_counts": op_counts,
        "actionable_dml": op_counts["add"] + op_counts["upgrade"],
        "manual_review_queue": op_counts["review"],
        "no_change": op_counts["noop"],
        "extracted_total": spike.get("extracted_total"),
        "db_match_rate": round(
            spike.get("db_matched", 0) / max(spike.get("extracted_total", 1), 1), 4
        ),
    }
    return plan


def main() -> None:
    SPIKE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Discover all prefs with spike output (exclude summary.json and any -writer-plan.json)
    prefs = sorted(
        p.stem for p in SPIKE_OUT_DIR.glob("*.json")
        if p.stem != "summary" and not p.stem.endswith("-writer-plan")
    )

    master_summary: dict = {"prefectures": {}, "totals": {"add": 0, "upgrade": 0, "noop": 0, "review": 0}}
    for pref in prefs:
        try:
            plan = build_plan(pref)
        except FileNotFoundError as e:
            print(f"[skip] {pref}: {e}", file=sys.stderr)
            continue

        out_path = SPIKE_OUT_DIR / f"{pref}-writer-plan.json"
        out_path.write_text(json.dumps(asdict(plan), ensure_ascii=False, indent=2))

        s = plan.summary
        print(
            f"[plan] {pref}: add={s['op_counts']['add']:>3} "
            f"upgrade={s['op_counts']['upgrade']:>3} "
            f"noop={s['op_counts']['noop']:>3} "
            f"review={s['op_counts']['review']:>3} "
            f"actionable={s['actionable_dml']:>3} "
            f"-> {out_path.name}",
            flush=True,
        )
        master_summary["prefectures"][pref] = s
        for k in master_summary["totals"]:
            master_summary["totals"][k] += s["op_counts"].get(k, 0)

    master_summary["totals"]["actionable_dml"] = (
        master_summary["totals"]["add"] + master_summary["totals"]["upgrade"]
    )

    master_path = SPIKE_OUT_DIR / "writer-plan-summary.json"
    master_path.write_text(json.dumps(master_summary, ensure_ascii=False, indent=2))
    print(f"\n=== MASTER PLAN -> {master_path} ===")
    print(json.dumps(master_summary["totals"], indent=2))


if __name__ == "__main__":
    main()
