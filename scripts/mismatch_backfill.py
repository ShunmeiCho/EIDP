"""Sprint 5 D'-1: backfill parsed_school_name for legacy school_mismatch docs.

For each Document with ingest_status='school_mismatch' that has no
parsed_school_name in output/ingest_rejections.jsonl yet, re-parse the
local PDF read-only (no DB writes, no ingest_status changes) and emit
the parsed name to output/mismatch-backfill-{ts}.jsonl. This file can be
merged with the existing rejection log when running mismatch_audit V2.

Output schema (1 row per legacy doc):
  {doc_id, school_id, parsed_school_name, parse_path, error}

Usage:
    uv run python scripts/mismatch_backfill.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Document  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402

REJECTION_LOG = REPO_ROOT / "output/ingest_rejections.jsonl"
OUT_DIR = REPO_ROOT / "output"


def load_logged_doc_ids() -> set[int]:
    """Doc IDs that already have parsed_school_name in the rejection log."""
    out: set[int] = set()
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
            detail = d.get("detail") or {}
            if detail.get("parsed_school_name"):
                doc_id = d.get("doc_id")
                if doc_id is not None:
                    out.add(int(doc_id))
    return out


def parse_one(pdf_path: Path) -> tuple[str | None, str, str | None]:
    """Returns (parsed_school_name, parse_path, error)."""
    from eidp.pdf.extractor import parse_pdf

    try:
        annotation = parse_pdf(pdf_path)
    except Exception as e:
        return None, "parse_pdf_error", f"{type(e).__name__}: {e}"
    name = annotation.school_name or ""
    if not name:
        # Could be image_only PDF — text extraction yields nothing
        return None, "text_only", "empty_school_name"
    return name, "text_only", None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Process only first N legacy docs")
    args = parser.parse_args()

    logged = load_logged_doc_ids()
    print(f"[backfill] doc_ids already in log: {len(logged)}")

    session = SessionLocal()
    try:
        all_mismatch = (
            session.query(Document)
            .filter(Document.ingest_status == "school_mismatch")
            .order_by(Document.id)
            .all()
        )
        legacy = [d for d in all_mismatch if d.id not in logged]
        if args.limit:
            legacy = legacy[: args.limit]
        print(f"[backfill] total mismatch: {len(all_mismatch)}, legacy targets: {len(legacy)}")
    finally:
        session.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"mismatch-backfill-{ts}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_with_name = 0
    n_empty = 0
    n_error = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for d in legacy:
            if not d.file_path:
                rec = {
                    "doc_id": d.id,
                    "school_id": d.school_id,
                    "parsed_school_name": None,
                    "parse_path": "no_file_path",
                    "error": "Document.file_path is null",
                }
                n_error += 1
            else:
                pdf_path = REPO_ROOT / d.file_path
                if not pdf_path.exists():
                    rec = {
                        "doc_id": d.id,
                        "school_id": d.school_id,
                        "parsed_school_name": None,
                        "parse_path": "file_missing",
                        "error": f"file not found: {pdf_path}",
                    }
                    n_error += 1
                else:
                    name, path_kind, err = parse_one(pdf_path)
                    rec = {
                        "doc_id": d.id,
                        "school_id": d.school_id,
                        "parsed_school_name": name,
                        "parse_path": path_kind,
                        "error": err,
                    }
                    if name:
                        n_with_name += 1
                    elif err:
                        n_error += 1
                    else:
                        n_empty += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[backfill] processed: {len(legacy)}")
    print(f"[backfill]   with parsed_name (text PDFs): {n_with_name}")
    print(f"[backfill]   empty (likely image_only, OCR needed): {n_empty}")
    print(f"[backfill]   error / no file: {n_error}")
    print(f"[backfill] output -> {out_path}")


if __name__ == "__main__":
    main()
