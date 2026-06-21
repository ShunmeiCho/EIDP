"""Map owner short-form decisions back to the canonical false-reject worksheet.

The owner short form is an intake convenience only. This helper updates the
canonical worksheet's mutable review columns, then the existing false-reject
review validator must still be used for release evidence.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _load_false_reject_audit_module() -> Any:
    script = Path(__file__).resolve().parent / "build_false_reject_audit.py"
    spec = importlib.util.spec_from_file_location("build_false_reject_audit", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load false-reject audit builder: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_FALSE_REJECT_AUDIT = _load_false_reject_audit_module()
REVIEW_CSV_COLUMNS = _FALSE_REJECT_AUDIT.REVIEW_CSV_COLUMNS
VALID_REVIEW_DECISIONS = _FALSE_REJECT_AUDIT.VALID_REVIEW_DECISIONS

SHORT_FORM_REQUIRED_COLUMNS = {
    "audit_row_id",
    "school_id",
    "page_url",
    "pdf_url",
    "rejection_bucket",
    "system_suggested_decision",
    "owner_decision",
    "owner_notes",
}
SHORT_TO_CANONICAL_CONTEXT = {
    "school_id": "school_id",
    "page_url": "page_url",
    "pdf_url": "pdf_url",
    "rejection_bucket": "bucket",
    "system_suggested_decision": "suggested_decision",
}
DECISIONS_REQUIRING_NOTES = {"false_reject", "needs_operator_review"}


def _read_csv_rows(csv_text: str) -> tuple[list[dict[str, str]], list[str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader], list(reader.fieldnames or [])


def _render_review_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REVIEW_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _summary(
    *,
    errors: list[str],
    expected_rows: int,
    short_form_rows: int,
    decision_counts: Counter[str],
    require_complete: bool,
) -> dict[str, Any]:
    completed_decisions = sum(count for decision, count in decision_counts.items() if decision)
    blank_decisions = decision_counts.get("", 0)
    return {
        "ok": not errors,
        "basis": "owner_short_form_to_false_reject_review_mapping",
        "release_forecast": "NOT_READY",
        "expected_rows": expected_rows,
        "short_form_rows": short_form_rows,
        "completed_decisions": completed_decisions,
        "blank_decisions": blank_decisions,
        "require_complete": require_complete,
        "decision_counts": {key or "blank": value for key, value in sorted(decision_counts.items())},
        "errors": errors,
        "excel_gate_warning": (
            "This mapping only prepares the canonical review CSV. It does not approve release, "
            "does not write audit logs, and does not allow rejected rows into Excel."
        ),
        "next_action": (
            "Run scripts/build_false_reject_audit.py with --validate-review-csv and --require-decisions, "
            "then generate the matching review audit log only after validation passes."
        ),
    }


def apply_owner_short_form_return(
    *,
    canonical_csv_text: str,
    short_form_csv_text: str,
    reviewer: str,
    reviewed_at: str,
    require_complete: bool = False,
) -> tuple[str, dict[str, Any]]:
    canonical_rows, canonical_columns = _read_csv_rows(canonical_csv_text)
    short_rows, short_columns = _read_csv_rows(short_form_csv_text)
    errors: list[str] = []

    missing_canonical = sorted(set(REVIEW_CSV_COLUMNS) - set(canonical_columns))
    if missing_canonical:
        errors.append(f"canonical review CSV is missing required columns: {', '.join(missing_canonical)}")

    missing_short = sorted(SHORT_FORM_REQUIRED_COLUMNS - set(short_columns))
    if missing_short:
        errors.append(f"owner short form is missing required columns: {', '.join(missing_short)}")

    canonical_by_id: dict[str, dict[str, str]] = {}
    duplicate_canonical_ids: set[str] = set()
    for row in canonical_rows:
        audit_row_id = str(row.get("audit_row_id") or "").strip()
        if not audit_row_id:
            errors.append("canonical review CSV contains a row with blank audit_row_id")
            continue
        if audit_row_id in canonical_by_id:
            duplicate_canonical_ids.add(audit_row_id)
        canonical_by_id[audit_row_id] = row
    for audit_row_id in sorted(duplicate_canonical_ids):
        errors.append(f"canonical review CSV contains duplicate audit_row_id {audit_row_id}")

    short_by_id: dict[str, dict[str, str]] = {}
    duplicate_short_ids: set[str] = set()
    for line_number, row in enumerate(short_rows, start=2):
        audit_row_id = str(row.get("audit_row_id") or "").strip()
        if not audit_row_id:
            errors.append(f"short form line {line_number}: audit_row_id is blank")
            continue
        if audit_row_id in short_by_id:
            duplicate_short_ids.add(audit_row_id)
        short_by_id[audit_row_id] = row
    for audit_row_id in sorted(duplicate_short_ids):
        errors.append(f"owner short form contains duplicate audit_row_id {audit_row_id}")

    canonical_ids = set(canonical_by_id)
    short_ids = set(short_by_id)
    unknown_ids = sorted(short_ids - canonical_ids)
    if unknown_ids:
        preview = ", ".join(unknown_ids[:5])
        suffix = "" if len(unknown_ids) <= 5 else f", ... ({len(unknown_ids)} total)"
        errors.append(f"owner short form contains unknown audit_row_id values: {preview}{suffix}")
    missing_ids = sorted(canonical_ids - short_ids)
    if missing_ids:
        preview = ", ".join(missing_ids[:5])
        suffix = "" if len(missing_ids) <= 5 else f", ... ({len(missing_ids)} total)"
        errors.append(f"owner short form is missing expected audit_row_id values: {preview}{suffix}")

    if errors:
        return "", _summary(
            errors=errors,
            expected_rows=len(canonical_rows),
            short_form_rows=len(short_rows),
            decision_counts=Counter(),
            require_complete=require_complete,
        )

    decision_counts: Counter[str] = Counter()
    mapped_rows: list[dict[str, str]] = []
    for line_number, canonical_row in enumerate(canonical_rows, start=2):
        audit_row_id = str(canonical_row.get("audit_row_id") or "").strip()
        short_row = short_by_id[audit_row_id]
        for short_column, canonical_column in SHORT_TO_CANONICAL_CONTEXT.items():
            expected_value = str(canonical_row.get(canonical_column) or "")
            actual_value = str(short_row.get(short_column) or "")
            if actual_value != expected_value:
                errors.append(
                    f"short form audit_row_id {audit_row_id}: {short_column} changed; "
                    f"expected {expected_value!r}, got {actual_value!r}"
                )

        owner_decision = str(short_row.get("owner_decision") or "").strip()
        owner_notes = str(short_row.get("owner_notes") or "").strip()
        if owner_decision not in VALID_REVIEW_DECISIONS:
            errors.append(
                f"short form audit_row_id {audit_row_id}: invalid owner_decision {owner_decision!r}; "
                f"expected one of {', '.join(repr(item) for item in VALID_REVIEW_DECISIONS[1:])}"
            )
        if require_complete and not owner_decision:
            errors.append(f"short form audit_row_id {audit_row_id}: owner_decision is required")
        if owner_decision and not reviewer:
            errors.append(f"short form audit_row_id {audit_row_id}: reviewer is required when owner_decision is set")
        if owner_decision and not reviewed_at:
            errors.append(f"short form audit_row_id {audit_row_id}: reviewed_at is required when owner_decision is set")
        if owner_decision in DECISIONS_REQUIRING_NOTES and not owner_notes:
            errors.append(f"short form audit_row_id {audit_row_id}: owner_notes are required for {owner_decision!r}")

        mapped = dict(canonical_row)
        mapped["decision"] = owner_decision
        mapped["reviewer"] = reviewer if owner_decision else ""
        mapped["reviewed_at"] = reviewed_at if owner_decision else ""
        mapped["notes"] = owner_notes if owner_decision else ""
        decision_counts[owner_decision] += 1
        mapped_rows.append(mapped)

    summary = _summary(
        errors=errors,
        expected_rows=len(canonical_rows),
        short_form_rows=len(short_rows),
        decision_counts=decision_counts,
        require_complete=require_complete,
    )
    return ("" if errors else _render_review_csv(mapped_rows)), summary


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-review-csv", type=Path, required=True)
    parser.add_argument("--owner-short-form-csv", type=Path, required=True)
    parser.add_argument("--reviewer", default="", help="Reviewer name applied to nonblank owner decisions.")
    parser.add_argument("--reviewed-at", default="", help="ISO timestamp applied to nonblank owner decisions.")
    parser.add_argument("--require-complete", action="store_true", help="Fail if any owner_decision is blank.")
    parser.add_argument("--output", type=Path, help="Write the mapped canonical review CSV to this path.")
    parser.add_argument("--json", action="store_true", help="Print the mapping summary as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    mapped_csv, summary = apply_owner_short_form_return(
        canonical_csv_text=args.canonical_review_csv.read_text(encoding="utf-8-sig"),
        short_form_csv_text=args.owner_short_form_csv.read_text(encoding="utf-8-sig"),
        reviewer=args.reviewer.strip(),
        reviewed_at=args.reviewed_at.strip(),
        require_complete=args.require_complete,
    )
    if summary["ok"] and args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(mapped_csv, encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.output is None and mapped_csv:
        print(mapped_csv, end="")
    elif not summary["ok"]:
        for error in summary["errors"]:
            print(error, file=sys.stderr)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
