"""Build mature-year acquisition proof JSON from mature-year evidence artifacts."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, TypeGuard


def _load_ship_gate_contract() -> Any:
    script = Path(__file__).resolve().parent / "ship_gate_contract.py"
    spec = importlib.util.spec_from_file_location("ship_gate_contract", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load ship gate contract: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SHIP_GATE_CONTRACT = _load_ship_gate_contract()
PROOF_TOOL_NAME = "build_mature_year_acquisition_proof"
STRICT_GAP_ANALYSIS_BASIS = "strict_yield_gap_analysis"
MATURE_YEAR_SHIP_GATE_METRIC_BASIS = _SHIP_GATE_CONTRACT.MATURE_YEAR_SHIP_GATE_METRIC_BASIS
MATURE_YEAR_PROOF_MIN_DENOMINATOR = _SHIP_GATE_CONTRACT.MATURE_YEAR_PROOF_MIN_DENOMINATOR
MATURE_YEAR_PROOF_SCHOOL_TYPE = _SHIP_GATE_CONTRACT.MATURE_YEAR_PROOF_SCHOOL_TYPE
WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE = _SHIP_GATE_CONTRACT.WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE
SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT = _SHIP_GATE_CONTRACT.SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT
SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT = _SHIP_GATE_CONTRACT.SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT
ship_gate_status_from_weekly_metrics = _SHIP_GATE_CONTRACT.ship_gate_status_from_weekly_metrics
ship_gate_threshold_gaps = _SHIP_GATE_CONTRACT.ship_gate_threshold_gaps


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_integer_count(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"last_run does not exist: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"last_run is not valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["last_run must contain a JSON object"]
    return payload, []


def _load_strict_gap_analysis(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"strict_gap_analysis does not exist: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"strict_gap_analysis is not valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["strict_gap_analysis must contain a JSON object"]
    return payload, []


def parse_case(value: str) -> tuple[int, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("case must use FY=path format")
    fiscal_year_text, path_text = value.split("=", 1)
    try:
        fiscal_year = int(fiscal_year_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"case fiscal year must be an integer: {fiscal_year_text}") from exc
    if not path_text:
        raise argparse.ArgumentTypeError("case path must not be blank")
    return fiscal_year, Path(path_text)


def _validate_numeric_threshold(
    *,
    errors: list[str],
    name: str,
    value: object,
    min_value: float,
) -> float | None:
    if not _is_number(value):
        errors.append(f"{name} must be numeric")
        return None
    numeric = float(value)
    if numeric < min_value:
        errors.append(f"{name} below release threshold: {numeric:.1f} < {min_value:.1f}")
    return numeric


def build_case(
    *,
    fiscal_year: int,
    last_run_path: Path,
    min_target_pdf_auto_yield: float,
    min_target_pdf_auto_denominator_count: int,
    max_manual_workload: float,
) -> dict[str, Any]:
    payload, errors = _load_json(last_run_path)
    case: dict[str, Any] = {
        "fiscal_year": fiscal_year,
        "last_run": str(last_run_path),
        "ok": False,
        "errors": errors,
    }
    if payload is None:
        return case

    target_yield = payload.get("target_pdf_auto_yield_pct")
    denominator = payload.get("target_pdf_auto_denominator_count")
    if denominator is None:
        denominator = payload.get("target_missing_school_count")
    operator_reviewable_yield = payload.get("operator_reviewable_yield_pct")
    ship_gate_status = payload.get("ship_gate_status")
    case.update(
        {
            "status": payload.get("status"),
            "finished_at": payload.get("finished_at"),
            "dry_run": payload.get("dry_run"),
            "current_fy": payload.get("current_fy"),
            "target_pdf_auto_denominator_count": denominator,
            "target_pdf_auto_denominator_scope": payload.get("target_pdf_auto_denominator_scope"),
            "target_missing_school_count": payload.get("target_missing_school_count"),
            "target_pdf_auto_yield_pct": target_yield,
            "operator_reviewable_yield_pct": operator_reviewable_yield,
            "ship_gate_status": ship_gate_status,
        }
    )

    if payload.get("status") != "success":
        errors.append("last_run status must be success")
    if not payload.get("finished_at"):
        errors.append("last_run finished_at is required")
    if payload.get("dry_run") is not False:
        errors.append("last_run dry_run must be false")
    if payload.get("current_fy") != fiscal_year:
        errors.append(f"last_run current_fy must be {fiscal_year}")

    if not _is_number(target_yield):
        errors.append("target_pdf_auto_yield_pct must be numeric")
    elif float(target_yield) < min_target_pdf_auto_yield:
        errors.append(
            "target_pdf_auto_yield_pct below release threshold: "
            f"{float(target_yield):.1f} < {min_target_pdf_auto_yield:.1f}"
        )

    if not _is_number(denominator):
        errors.append("target_pdf_auto_denominator_count must be numeric")
    elif not _is_integer_count(denominator):
        errors.append("target_pdf_auto_denominator_count must be an integer")
    elif float(denominator) < min_target_pdf_auto_denominator_count:
        errors.append(
            "target_pdf_auto_denominator_count below production-scale threshold: "
            f"{float(denominator):.0f} < {min_target_pdf_auto_denominator_count}"
        )
    if payload.get("target_pdf_auto_denominator_scope") != WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE:
        errors.append(
            "target_pdf_auto_denominator_scope must be "
            f"{WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE}"
        )

    if not _is_number(operator_reviewable_yield):
        errors.append("operator_reviewable_yield_pct must be numeric")
    else:
        manual_workload = 100.0 - float(operator_reviewable_yield)
        case["estimated_manual_workload_pct"] = manual_workload
        if manual_workload > max_manual_workload + 1e-9:
            errors.append(
                "estimated manual workload above release threshold: "
                f"{manual_workload:.1f} > {max_manual_workload:.1f}"
            )
        expected_ship_gate_status = ship_gate_status_from_weekly_metrics(
            target_pdf_auto_yield_pct=float(target_yield) if _is_number(target_yield) else None,
            operator_reviewable_yield_pct=float(operator_reviewable_yield),
        )
        if ship_gate_status != expected_ship_gate_status:
            errors.append(
                "ship_gate_status does not match target_pdf_auto_yield_pct/operator_reviewable_yield_pct: "
                f"{ship_gate_status} != {expected_ship_gate_status}"
            )

    case["threshold_gaps"] = list(
        ship_gate_threshold_gaps(
            target_pdf_auto_yield_pct=float(target_yield) if _is_number(target_yield) else None,
            operator_reviewable_yield_pct=(
                float(operator_reviewable_yield) if _is_number(operator_reviewable_yield) else None
            ),
            min_target_pdf_auto_yield_pct=min_target_pdf_auto_yield,
            max_manual_workload_pct=max_manual_workload,
        )
    )

    case["ok"] = not errors
    return case


def build_strict_gap_analysis_case(
    *,
    fiscal_year: int,
    strict_gap_analysis_path: Path,
    min_target_pdf_auto_yield: float,
    min_target_pdf_auto_denominator_count: int,
    max_manual_workload: float,
) -> dict[str, Any]:
    payload, errors = _load_strict_gap_analysis(strict_gap_analysis_path)
    case: dict[str, Any] = {
        "fiscal_year": fiscal_year,
        "strict_gap_analysis": str(strict_gap_analysis_path),
        "evidence_source": "strict_gap_analysis",
        "ok": False,
        "errors": errors,
    }
    if payload is None:
        return case

    basis = payload.get("basis")
    source_fiscal_year = payload.get("fiscal_year")
    finished_at = payload.get("finished_at") or payload.get("generated_at")
    denominator = payload.get("schools_total")
    target_yield = payload.get("strict_target_parsed_rate_pct")
    excel_ready_yield = payload.get("excel_ready_rate_pct")
    operator_reviewable_yield = payload.get("operator_reviewable_rate_pct")
    source_manual_workload = payload.get("estimated_manual_workload_rate_pct")

    case.update(
        {
            "source_basis": basis,
            "database": payload.get("database"),
            "finished_at": finished_at,
            "school_type": payload.get("school_type"),
            "source_fiscal_year": source_fiscal_year,
            "target_pdf_auto_denominator_count": denominator,
            "target_pdf_auto_denominator_scope": WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE,
            "target_missing_school_count": denominator,
            "target_pdf_auto_yield_pct": target_yield,
            "excel_ready_yield_pct": excel_ready_yield,
            "operator_reviewable_yield_pct": operator_reviewable_yield,
            "source_estimated_manual_workload_pct": source_manual_workload,
        }
    )

    if basis != STRICT_GAP_ANALYSIS_BASIS:
        errors.append(f"strict_gap_analysis basis must be {STRICT_GAP_ANALYSIS_BASIS}: {basis!r}")
    if not finished_at:
        errors.append("strict_gap_analysis finished_at is required")
    if source_fiscal_year != fiscal_year:
        errors.append(f"strict_gap_analysis fiscal_year must be {fiscal_year}")
    if payload.get("school_type") != MATURE_YEAR_PROOF_SCHOOL_TYPE:
        errors.append(f"strict_gap_analysis school_type must be {MATURE_YEAR_PROOF_SCHOOL_TYPE}")

    if not _is_number(denominator):
        errors.append("schools_total must be numeric")
    elif not _is_integer_count(denominator):
        errors.append("schools_total must be an integer")
    elif float(denominator) < min_target_pdf_auto_denominator_count:
        errors.append(
            "schools_total below production-scale threshold: "
            f"{float(denominator):.0f} < {min_target_pdf_auto_denominator_count}"
        )

    target_yield_value = _validate_numeric_threshold(
        errors=errors,
        name="strict_target_parsed_rate_pct",
        value=target_yield,
        min_value=min_target_pdf_auto_yield,
    )
    _validate_numeric_threshold(
        errors=errors,
        name="excel_ready_rate_pct",
        value=excel_ready_yield,
        min_value=min_target_pdf_auto_yield,
    )

    if not _is_number(operator_reviewable_yield):
        errors.append("operator_reviewable_rate_pct must be numeric")
        operator_reviewable_yield_value = None
    else:
        operator_reviewable_yield_value = float(operator_reviewable_yield)
        manual_workload = 100.0 - operator_reviewable_yield_value
        case["estimated_manual_workload_pct"] = round(manual_workload, 10)
        if manual_workload > max_manual_workload + 1e-9:
            errors.append(
                "estimated manual workload above release threshold: "
                f"{manual_workload:.1f} > {max_manual_workload:.1f}"
            )

    expected_ship_gate_status = ship_gate_status_from_weekly_metrics(
        target_pdf_auto_yield_pct=target_yield_value,
        operator_reviewable_yield_pct=operator_reviewable_yield_value,
    )
    case["ship_gate_status"] = expected_ship_gate_status
    case["threshold_gaps"] = list(
        ship_gate_threshold_gaps(
            target_pdf_auto_yield_pct=target_yield_value,
            operator_reviewable_yield_pct=operator_reviewable_yield_value,
            min_target_pdf_auto_yield_pct=min_target_pdf_auto_yield,
            max_manual_workload_pct=max_manual_workload,
        )
    )
    if _is_number(excel_ready_yield) and float(excel_ready_yield) < min_target_pdf_auto_yield:
        case["threshold_gaps"].append("excel_ready")

    case["ok"] = not errors
    return case


def build_proof(
    cases: list[tuple[int, Path]],
    strict_gap_analysis_cases: list[tuple[int, Path]] | None = None,
    *,
    min_target_pdf_auto_yield: float = SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT,
    min_target_pdf_auto_denominator_count: int = MATURE_YEAR_PROOF_MIN_DENOMINATOR,
    max_manual_workload: float = SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT,
) -> dict[str, Any]:
    proof_cases = [
        build_case(
            fiscal_year=fiscal_year,
            last_run_path=last_run_path,
            min_target_pdf_auto_yield=min_target_pdf_auto_yield,
            min_target_pdf_auto_denominator_count=min_target_pdf_auto_denominator_count,
            max_manual_workload=max_manual_workload,
        )
        for fiscal_year, last_run_path in cases
    ]
    proof_cases.extend(
        build_strict_gap_analysis_case(
            fiscal_year=fiscal_year,
            strict_gap_analysis_path=strict_gap_analysis_path,
            min_target_pdf_auto_yield=min_target_pdf_auto_yield,
            min_target_pdf_auto_denominator_count=min_target_pdf_auto_denominator_count,
            max_manual_workload=max_manual_workload,
        )
        for fiscal_year, strict_gap_analysis_path in (strict_gap_analysis_cases or [])
    )
    return {
        "ok": bool(proof_cases) and all(case["ok"] for case in proof_cases),
        "basis": MATURE_YEAR_SHIP_GATE_METRIC_BASIS,
        "min_target_pdf_auto_yield": min_target_pdf_auto_yield,
        "min_target_pdf_auto_denominator_count": min_target_pdf_auto_denominator_count,
        "max_manual_workload": max_manual_workload,
        "cases": proof_cases,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        type=parse_case,
        help="Mature-year proof case in FY=path/to/last_run.json format. Repeatable.",
    )
    parser.add_argument(
        "--strict-gap-analysis-case",
        action="append",
        default=[],
        type=parse_case,
        help="Mature-year proof case in FY=path/to/strict-gap-analysis.json format. Repeatable.",
    )
    parser.add_argument("--output", help="Write proof JSON to this path. Defaults to stdout only.")
    parser.add_argument("--min-target-pdf-auto-yield", type=float, default=SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT)
    parser.add_argument(
        "--min-target-pdf-auto-denominator-count",
        type=int,
        default=MATURE_YEAR_PROOF_MIN_DENOMINATOR,
        help="Minimum mature-year target-missing denominator required for production-scale proof.",
    )
    parser.add_argument("--max-manual-workload", type=float, default=SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    proof = build_proof(
        args.case,
        strict_gap_analysis_cases=args.strict_gap_analysis_case,
        min_target_pdf_auto_yield=args.min_target_pdf_auto_yield,
        min_target_pdf_auto_denominator_count=args.min_target_pdf_auto_denominator_count,
        max_manual_workload=args.max_manual_workload,
    )
    text = json.dumps(
        proof,
        ensure_ascii=False,
        sort_keys=True if args.json else False,
        indent=None if args.json else 2,
    )
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if proof["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
