"""Verify returned owner/operator Stage 6 artifacts before release approval."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TypeGuard

REQUIRED_EVIDENCE_LABELS = ("build_info", "diagnostics", "last_run", "stage6_recovery", "weekly_run_logs")
REQUIRED_KPI_ROWS = ("ship_readiness_rc", "strict target PDF 自動取得率", "推定手作業率")
REQUIRED_RELEASE_ROWS = ("業務員 PC 1 サイクル完了", "KPI owner 承認", "残 P0/P1 bug")
REQUIRED_RELEASE_VALUES = {
    "業務員 PC 1 サイクル完了": "yes",
    "KPI owner 承認": "yes",
    "残 P0/P1 bug": "none",
}
PLACEHOLDER_RESULTS = {
    "",
    "pass / fail",
    "pass / fail / n/a",
    "pass / watch / fail",
    "yes / no",
    "none / exists",
    "go / no-go / beta continue",
}


def _load_json(path: Path, errors: list[str], label: str) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label} does not exist: {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return value


def _clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _table_row(text: str, label: str) -> list[str] | None:
    normalized_label = _clean_cell(label)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = [_clean_cell(cell) for cell in stripped.strip("|").split("|")]
        if cells and _clean_cell(cells[0]) == normalized_label:
            return cells
    return None


def _fenced_block_after(text: str, marker: str) -> str | None:
    marker_index = text.find(marker)
    if marker_index < 0:
        return None
    match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)\n```", text[marker_index:], flags=re.DOTALL)
    return match.group(1) if match else None


def _block_field_value(block: str, field: str) -> str:
    for line in block.splitlines():
        if line.strip().lower().startswith(f"{field.lower()}:"):
            return line.split(":", 1)[1].strip()
    return ""


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_RESULTS


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _verify_last_run(
    last_run: dict[str, Any],
    *,
    target_fy: int | None,
    require_kpi: bool,
    min_target_pdf_auto_yield: float,
    max_manual_workload: float,
    errors: list[str],
) -> None:
    if last_run.get("status") != "success":
        errors.append("last_run status must be success")
    if not last_run.get("finished_at"):
        errors.append("last_run finished_at is required")
    if last_run.get("dry_run") is not False:
        errors.append("last_run dry_run must be false")
    if target_fy is not None and last_run.get("current_fy") != target_fy:
        errors.append(f"last_run current_fy must be {target_fy}")

    if require_kpi:
        target_yield = last_run.get("target_pdf_auto_yield_pct")
        operator_reviewable_yield = last_run.get("operator_reviewable_yield_pct")
        if not _is_number(target_yield):
            errors.append("last_run target_pdf_auto_yield_pct must be numeric for final return evidence")
        else:
            target_yield_value = float(target_yield)
            if target_yield_value < min_target_pdf_auto_yield:
                errors.append(
                    "last_run target_pdf_auto_yield_pct below release threshold: "
                    f"{target_yield_value:.1f} < {min_target_pdf_auto_yield:.1f}"
                )
        if not _is_number(operator_reviewable_yield):
            errors.append("last_run operator_reviewable_yield_pct must be numeric for final return evidence")
        else:
            operator_reviewable_yield_value = float(operator_reviewable_yield)
            manual_workload = 100.0 - operator_reviewable_yield_value
            if manual_workload > max_manual_workload + 1e-9:
                errors.append(
                    "last_run estimated manual workload above release threshold: "
                    f"{manual_workload:.1f} > {max_manual_workload:.1f}"
                )
        if last_run.get("ship_gate_status") in {None, "", "not_measured"}:
            errors.append("last_run ship_gate_status must be measured")


def _verify_evidence_verify_json(verify_json: dict[str, Any], errors: list[str]) -> None:
    if verify_json.get("ok") is not True:
        errors.append("evidence verifier JSON ok must be true")
    missing = verify_json.get("missing_required_labels")
    if missing not in ([], None):
        errors.append("evidence verifier JSON has missing required labels")
    present = verify_json.get("present_labels")
    if not isinstance(present, list):
        errors.append("evidence verifier JSON present_labels must be a list")
        return
    missing_labels = sorted(label for label in REQUIRED_EVIDENCE_LABELS if label not in set(present))
    if missing_labels:
        errors.append(f"evidence verifier JSON missing labels: {', '.join(missing_labels)}")


def _verify_template(text: str, errors: list[str]) -> None:
    for row_label in REQUIRED_KPI_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 4:
            errors.append(f"E2E template KPI row missing or malformed: {row_label}")
            continue
        actual = row[2]
        verdict = row[3]
        if not actual:
            errors.append(f"E2E template KPI actual is blank: {row_label}")
        if _is_placeholder(verdict):
            errors.append(f"E2E template KPI verdict is still placeholder: {row_label}")
        elif verdict.lower() != "pass":
            errors.append(f"E2E template KPI verdict must be pass: {row_label}")

    for row_label in REQUIRED_RELEASE_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 2:
            errors.append(f"E2E template release row missing or malformed: {row_label}")
            continue
        if _is_placeholder(row[1]):
            errors.append(f"E2E template release row is still placeholder: {row_label}")
        elif row[1].lower() != REQUIRED_RELEASE_VALUES[row_label]:
            errors.append(f"E2E template release row must be {REQUIRED_RELEASE_VALUES[row_label]}: {row_label}")

    conclusion = _fenced_block_after(text, "結論:")
    if conclusion is None or _is_placeholder(conclusion.strip()):
        errors.append("E2E template release conclusion is missing or still placeholder")
    elif conclusion.strip().lower() != "go":
        errors.append("E2E template release conclusion must be go")

    for marker in ("Owner sign-off:", "業務員 sign-off:"):
        block = _fenced_block_after(text, marker)
        if block is None:
            errors.append(f"E2E template missing sign-off block: {marker}")
            continue
        for field in ("Name", "Date", "Decision"):
            if not _block_field_value(block, field):
                errors.append(f"E2E template {marker} {field} is blank")


def verify_stage6_return(
    *,
    e2e_template: Path,
    last_run: Path,
    evidence_verify_json: Path,
    target_fy: int | None = None,
    require_kpi: bool = True,
    min_target_pdf_auto_yield: float = 60.0,
    max_manual_workload: float = 30.0,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    last_run_json = _load_json(last_run, errors, "last_run")
    if last_run_json is not None:
        _verify_last_run(
            last_run_json,
            target_fy=target_fy,
            require_kpi=require_kpi,
            min_target_pdf_auto_yield=min_target_pdf_auto_yield,
            max_manual_workload=max_manual_workload,
            errors=errors,
        )

    verify_json = _load_json(evidence_verify_json, errors, "evidence verifier JSON")
    if verify_json is not None:
        _verify_evidence_verify_json(verify_json, errors)

    if not e2e_template.is_file():
        errors.append(f"E2E template does not exist: {e2e_template}")
    else:
        _verify_template(e2e_template.read_text(encoding="utf-8"), errors)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "inputs": {
            "e2e_template": str(e2e_template),
            "last_run": str(last_run),
            "evidence_verify_json": str(evidence_verify_json),
            "target_fy": target_fy,
            "require_kpi": require_kpi,
            "min_target_pdf_auto_yield": min_target_pdf_auto_yield,
            "max_manual_workload": max_manual_workload,
        },
        "required_evidence_labels": list(REQUIRED_EVIDENCE_LABELS),
        "required_kpi_rows": list(REQUIRED_KPI_ROWS),
        "required_release_rows": list(REQUIRED_RELEASE_ROWS),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e2e-template", required=True, help="Completed eidp-operator-e2e-template.md.")
    parser.add_argument("--last-run", required=True, help="Returned data/output/last_run.json.")
    parser.add_argument("--evidence-verify-json", required=True, help="Returned stage6-evidence-verify-*.json.")
    parser.add_argument("--target-fy", type=int, help="Expected current_fy in last_run.json.")
    parser.add_argument(
        "--min-target-pdf-auto-yield",
        type=float,
        default=60.0,
        help="Minimum target_pdf_auto_yield_pct for release approval.",
    )
    parser.add_argument(
        "--max-manual-workload",
        type=float,
        default=30.0,
        help="Maximum estimated manual workload percentage for release approval.",
    )
    parser.add_argument(
        "--allow-unmeasured-kpi",
        action="store_true",
        help="Allow null/not_measured KPI values. Use only for diagnostic dry support, not release approval.",
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = verify_stage6_return(
        e2e_template=Path(args.e2e_template),
        last_run=Path(args.last_run),
        evidence_verify_json=Path(args.evidence_verify_json),
        target_fy=args.target_fy,
        require_kpi=not args.allow_unmeasured_kpi,
        min_target_pdf_auto_yield=args.min_target_pdf_auto_yield,
        max_manual_workload=args.max_manual_workload,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
