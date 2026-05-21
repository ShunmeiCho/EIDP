"""Evaluate whether a strict-yield run can still reach the ship gate.

This tool is intentionally read-only. It turns partial-run counters or a
strict-yield gap JSON into a small go/no-go proof without touching the EIDP DB.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _rate(count: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(count / denominator * 100.0, 1)


def _required_count(denominator: int, required_strict_yield_pct: float) -> int:
    return math.ceil(denominator * required_strict_yield_pct / 100.0)


def evaluate_bound(
    *,
    denominator: int,
    processed: int,
    strict_successes: int,
    required_strict_yield_pct: float = 60.0,
    target_fiscal_year: int | None = None,
    discovered_target_year_documents: int | None = None,
) -> dict[str, Any]:
    """Return a release-gate upper-bound proof for strict target-PDF yield."""

    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if not 0 <= processed <= denominator:
        raise ValueError("processed must be between 0 and denominator")
    if not 0 <= strict_successes <= processed:
        raise ValueError("strict_successes must be between 0 and processed")
    if not 0.0 < required_strict_yield_pct <= 100.0:
        raise ValueError("required_strict_yield_pct must be in (0, 100]")

    required_count = _required_count(denominator, required_strict_yield_pct)
    remaining = denominator - processed
    max_possible_strict_count = strict_successes + remaining

    if strict_successes >= required_count:
        status = "pass"
        ok = True
    elif max_possible_strict_count < required_count:
        status = "no_go_upper_bound_below_required"
        ok = False
    else:
        status = "still_possible_below_gate"
        ok = False

    result: dict[str, Any] = {
        "ok": ok,
        "proof_type": "strict_yield_upper_bound",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "target_fiscal_year": target_fiscal_year,
        "required_strict_yield_pct": required_strict_yield_pct,
        "required_strict_count": required_count,
        "denominator": denominator,
        "processed_position": processed,
        "remaining_schools": remaining,
        "strict_successes": strict_successes,
        "current_strict_yield_pct": _rate(strict_successes, denominator),
        "max_possible_strict_count_if_all_remaining_pass": max_possible_strict_count,
        "max_possible_strict_yield_pct_if_all_remaining_pass": _rate(max_possible_strict_count, denominator),
        "discovered_target_year_documents": discovered_target_year_documents,
    }
    if status == "no_go_upper_bound_below_required":
        result["conclusion"] = (
            "Strict-yield gate is mathematically unreachable for this denominator: "
            f"max possible {max_possible_strict_count}/{denominator} "
            f"({result['max_possible_strict_yield_pct_if_all_remaining_pass']}%) "
            f"is below required {required_count}/{denominator} ({required_strict_yield_pct}%)."
        )
    elif status == "pass":
        result["conclusion"] = (
            "Strict-yield gate is already met: "
            f"{strict_successes}/{denominator} ({result['current_strict_yield_pct']}%) "
            f"meets required {required_count}/{denominator} ({required_strict_yield_pct}%)."
        )
    else:
        result["conclusion"] = (
            "Strict-yield gate is not met yet, but remains mathematically reachable "
            f"if enough of the {remaining} remaining schools pass."
        )
    return result


def _load_gap_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("strict gap JSON must be an object")
    return payload


def _int_from_gap(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"strict gap JSON field {key!r} must be an integer")
    return value


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-gap-json", type=Path, help="Read denominator and strict count from analyzer JSON.")
    parser.add_argument("--denominator", type=int, help="Total denominator schools.")
    parser.add_argument("--processed", type=int, help="Number of denominator schools already processed.")
    parser.add_argument("--strict-successes", type=int, help="Strict target-PDF/excel-ready successes so far.")
    parser.add_argument("--required-strict-yield-pct", type=float, default=60.0)
    parser.add_argument("--target-fiscal-year", type=int)
    parser.add_argument("--discovered-target-year-documents", type=int)
    parser.add_argument("--output", type=Path, help="Write JSON proof to this path.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    denominator = args.denominator
    processed = args.processed
    strict_successes = args.strict_successes
    target_fiscal_year = args.target_fiscal_year

    if args.strict_gap_json is not None:
        gap = _load_gap_json(args.strict_gap_json)
        denominator = _int_from_gap(gap, "schools_total")
        strict_successes = _int_from_gap(gap, "strict_target_parsed_schools")
        processed = denominator if processed is None else processed
        if target_fiscal_year is None:
            fiscal_year = gap.get("fiscal_year")
            if isinstance(fiscal_year, int):
                target_fiscal_year = fiscal_year

    missing = [
        name
        for name, value in (
            ("--denominator", denominator),
            ("--processed", processed),
            ("--strict-successes", strict_successes),
        )
        if value is None
    ]
    if missing:
        raise SystemExit(f"missing required inputs: {', '.join(missing)}")

    result = evaluate_bound(
        denominator=int(denominator),
        processed=int(processed),
        strict_successes=int(strict_successes),
        required_strict_yield_pct=float(args.required_strict_yield_pct),
        target_fiscal_year=target_fiscal_year,
        discovered_target_year_documents=args.discovered_target_year_documents,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(result["conclusion"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
