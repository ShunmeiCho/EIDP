"""Build operator-review school-alias proposals from PDF school-name mismatches.

This script is intentionally read-only with respect to the database. It turns
``pdf_school_mismatch`` discovery evidence into the same proposal JSONL shape
that the existing operator UI already knows how to review. Approval still goes
through ``apply_school_alias_proposal`` and writes ``ManualActionLog``.

Usage:
    uv run python scripts/pdf_school_mismatch_alias_proposals.py \
        --rejections output/target-year-discovery/latest-discovery-rejections.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from eidp.db.models import School, SchoolAlias
from eidp.db.session import SessionLocal
from eidp.review.pdf_school_mismatch_alias_proposals import (
    PdfSchoolMismatchAliasProposal,
    build_proposals,
    load_rejection_rows,
    write_merged_proposals,
)

__all__ = [
    "PdfSchoolMismatchAliasProposal",
    "build_proposals",
    "load_rejection_rows",
    "write_merged_proposals",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rejections",
        type=Path,
        default=Path("output/discovery_rejections.jsonl"),
        help="Discovery rejection JSONL containing pdf_school_mismatch rows.",
    )
    parser.add_argument(
        "--out-jsonl",
        type=Path,
        default=Path("output/school_missing_proposals.jsonl"),
        help="Existing operator proposal JSONL consumed by the review UI.",
    )
    args = parser.parse_args()

    rows = load_rejection_rows(args.rejections)
    session = SessionLocal()
    try:
        schools = session.query(School).all()
        aliases = session.query(SchoolAlias).all()
        proposals, stats = build_proposals(rows, schools, aliases)
    except SQLAlchemyError as exc:
        session.rollback()
        raise SystemExit(
            "Database is not initialized or not reachable. Run this inside an EIDP operator environment "
            "with a valid EIDP_DATABASE_URL/EIDP_DATA_DIR before generating alias proposals."
        ) from exc
    finally:
        session.close()

    write_stats = write_merged_proposals(args.out_jsonl, proposals)
    print(json.dumps({"proposal_stats": stats, "write_stats": write_stats}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
