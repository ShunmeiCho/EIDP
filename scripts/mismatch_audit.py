"""Sprint 5 V1: read-only audit of school_mismatch documents.

Produces a CSV that owner can review and annotate with one of:
  alias        — confirm parsed_name as alias for the target school_id
                 (will re-ingest on V2 apply)
  wrong_school — doc actually belongs to a different school; needs
                 manual school_id reassignment
  defer        — needs deeper investigation

Inputs:
  - DB: Document.ingest_status='school_mismatch'
  - output/ingest_rejections.jsonl: parsed_name when available

Output:
  - output/mismatch-audit-{ts}.csv

Usage:
    uv run python scripts/mismatch_audit.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Document, School, SchoolAlias  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402

REJECTION_LOG = REPO_ROOT / "output/ingest_rejections.jsonl"
OUT_DIR = REPO_ROOT / "output"


def load_rejection_log() -> dict[int, dict]:
    """Map doc_id -> latest mismatch detail dict."""
    out: dict[int, dict] = {}
    if not REJECTION_LOG.exists():
        return out
    with REJECTION_LOG.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("reason") != "school_mismatch":
                continue
            doc_id = d.get("doc_id")
            if doc_id is None:
                continue
            out[int(doc_id)] = d.get("detail") or {}
    return out


def main() -> None:
    rej_log = load_rejection_log()

    session = SessionLocal()
    try:
        docs = (
            session.query(Document)
            .filter(Document.ingest_status == "school_mismatch")
            .order_by(Document.school_id, Document.id)
            .all()
        )
        rows: list[dict] = []
        for d in docs:
            sch = session.get(School, d.school_id)
            detail = rej_log.get(d.id, {})
            parsed_name = detail.get("parsed_school_name", "")
            alias_count = detail.get("alias_count", "")
            existing_aliases = (
                session.query(SchoolAlias)
                .filter(SchoolAlias.school_id == d.school_id)
                .all()
            )
            rows.append({
                "doc_id": d.id,
                "school_id": d.school_id,
                "expected_school": sch.school_name if sch else "?",
                "expected_corp": sch.corporation_name if sch else "?",
                "expected_pref": sch.prefecture if sch else "?",
                "parsed_school_name_from_pdf": parsed_name,
                "existing_alias_count": len(existing_aliases),
                "existing_aliases": "|".join(a.alias_name for a in existing_aliases[:5]),
                "log_alias_count_at_mismatch": alias_count,
                "source_url": d.source_url,
                "fiscal_year": d.fiscal_year or "",
                "pdf_type": d.pdf_type or "",
                "decision": "",  # operator fills: alias|wrong_school|defer
                "decision_note": "",
            })
    finally:
        session.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"mismatch-audit-{ts}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "doc_id", "school_id", "expected_school", "expected_corp",
        "expected_pref", "parsed_school_name_from_pdf",
        "existing_alias_count", "existing_aliases",
        "log_alias_count_at_mismatch", "source_url", "fiscal_year",
        "pdf_type", "decision", "decision_note",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with_parsed = sum(1 for r in rows if r["parsed_school_name_from_pdf"])
    print(f"[audit] total mismatch docs: {len(rows)}")
    print(f"[audit] with parsed_name in log (Sprint 5 actionable now): {with_parsed}")
    print(f"[audit] without parsed_name (legacy, need re-discover or manual): {len(rows) - with_parsed}")
    print(f"[audit] CSV -> {out_path}")
    print()
    print("Top 5 with parsed_name (Sprint 5 V2 apply candidates):")
    actionable = [r for r in rows if r["parsed_school_name_from_pdf"]][:5]
    for r in actionable:
        print(
            f"  doc={r['doc_id']} sid={r['school_id']} "
            f"expected='{r['expected_school']}' parsed='{r['parsed_school_name_from_pdf']}'"
        )


if __name__ == "__main__":
    main()
