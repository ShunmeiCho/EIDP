"""Verify returned owner/operator Stage 6 artifacts before release approval."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypeGuard

REQUIRED_EVIDENCE_LABELS = ("build_info", "diagnostics", "last_run", "stage6_recovery", "weekly_run_logs")
REQUIRED_KPI_ROWS = ("ship_readiness_rc", "strict target PDF 自動取得率", "推定手作業率", "Excel ready 率")
REQUIRED_ALWAYS_PASS_KPI_ROWS = ("Excel 整合性",)
REQUIRED_EXCEPTION_ROWS = ("release exception reason", "mature-year proof JSON", "mature-year proof years")
REQUIRED_EXCEPTION_RECORD_ROWS = (
    "Exception reason",
    "Decision",
    "Approver",
    "Approval date",
    "Release scope",
    "FY2026/R8 status acknowledged",
    "Required follow-up",
)
REQUIRED_RELEASE_ROWS = (
    "Stage 2-5c Windows VM gate 済み",
    "業務員 PC 1 サイクル完了",
    "KPI owner 承認",
    "Runbook 修正反映済み",
    "残 P0/P1 bug",
)
REQUIRED_AUDIT_ROWS = (
    "監査ログページ表示",
    "manual_action_log 件数",
    "JSONL outbox 未送信件数",
    "audit-flush 実行",
    "JSONL action_id 重複",
)
REQUIRED_RELEASE_VALUES = {
    "Stage 2-5c Windows VM gate 済み": "yes",
    "業務員 PC 1 サイクル完了": "yes",
    "KPI owner 承認": "yes",
    "Runbook 修正反映済み": "yes",
    "残 P0/P1 bug": "none",
}
RELEASE_CONCLUSIONS = ("READY", "RC_ONLY", "NOT_READY")
RELEASE_APPROVAL_CONCLUSION = "READY"
PLACEHOLDER_RESULTS = {
    "",
    "pass / fail",
    "pass / fail / n/a",
    "pass / watch / fail",
    "yes / no",
    "none / exists",
    "go / no-go / beta continue",
    "ready / rc_only / not_ready",
}
EXCEPTION_KPI_VERDICTS = frozenset({"pass", "watch"})


def _load_ship_gate_contract() -> Any:
    script = Path(__file__).resolve().parent / "ship_gate_contract.py"
    spec = importlib.util.spec_from_file_location("ship_gate_contract", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load ship gate contract: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SHIP_GATE_CONTRACT = _load_ship_gate_contract()
SHIP_GATE_EXCEPTION_REASONS = _SHIP_GATE_CONTRACT.SHIP_GATE_EXCEPTION_REASONS
SHIP_GATE_STATUSES = _SHIP_GATE_CONTRACT.SHIP_GATE_STATUSES
MATURE_YEAR_SHIP_GATE_METRIC_BASIS = _SHIP_GATE_CONTRACT.MATURE_YEAR_SHIP_GATE_METRIC_BASIS
MATURE_YEAR_PROOF_MIN_DENOMINATOR = _SHIP_GATE_CONTRACT.MATURE_YEAR_PROOF_MIN_DENOMINATOR
WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE = _SHIP_GATE_CONTRACT.WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE
is_ship_gate_exception_reason = _SHIP_GATE_CONTRACT.is_ship_gate_exception_reason
ship_gate_status_from_weekly_metrics = _SHIP_GATE_CONTRACT.ship_gate_status_from_weekly_metrics


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


def _status_value(text: str) -> str:
    for line in text.splitlines():
        if line.strip().lower().startswith("status:"):
            return _clean_cell(line.split(":", 1)[1])
    return ""


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_RESULTS


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _release_conclusion_value(value: str) -> str:
    return value.strip().upper()


def _parse_nonnegative_int(value: str) -> int | None:
    normalized = value.replace(",", "").strip()
    if not re.fullmatch(r"\d+", normalized):
        return None
    return int(normalized)


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def _is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _outbox_flushed(value: str) -> bool:
    normalized = value.lower().replace("`", "").strip()
    return normalized == "0" or "after flush 0" in normalized


def _has_generated_excel_output_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return ".xlsx" in normalized and "data/output/" in normalized


def _years_from_text(value: str) -> set[int]:
    return {int(match) for match in re.findall(r"\b(?:19|20)\d{2}\b", value)}


def _verify_last_run(
    last_run: dict[str, Any],
    *,
    target_fy: int | None,
    require_kpi: bool,
    min_target_pdf_auto_yield: float,
    max_manual_workload: float,
    release_exception_reason: str | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    if last_run.get("status") != "success":
        errors.append("last_run status must be success")
    finished_at = last_run.get("finished_at")
    if not isinstance(finished_at, str) or not finished_at:
        errors.append("last_run finished_at is required")
    elif not _is_iso_datetime(finished_at):
        errors.append("last_run finished_at must be ISO datetime")
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
                message = (
                    "last_run target_pdf_auto_yield_pct below release threshold: "
                    f"{target_yield_value:.1f} < {min_target_pdf_auto_yield:.1f}"
                )
                if release_exception_reason:
                    warnings.append(f"release exception {release_exception_reason} accepted {message}")
                else:
                    errors.append(message)
        if not _is_number(operator_reviewable_yield):
            errors.append("last_run operator_reviewable_yield_pct must be numeric for final return evidence")
        else:
            operator_reviewable_yield_value = float(operator_reviewable_yield)
            manual_workload = 100.0 - operator_reviewable_yield_value
            if manual_workload > max_manual_workload + 1e-9:
                message = (
                    "last_run estimated manual workload above release threshold: "
                    f"{manual_workload:.1f} > {max_manual_workload:.1f}"
                )
                if release_exception_reason:
                    warnings.append(f"release exception {release_exception_reason} accepted {message}")
                else:
                    errors.append(message)
        ship_gate_status = last_run.get("ship_gate_status")
        if ship_gate_status in {None, "", "not_measured"}:
            errors.append("last_run ship_gate_status must be measured")
        elif not isinstance(ship_gate_status, str) or ship_gate_status not in SHIP_GATE_STATUSES:
            errors.append("last_run ship_gate_status must be pass, below_gate, or not_measured")
        elif _is_number(target_yield) and _is_number(operator_reviewable_yield):
            expected_ship_gate_status = ship_gate_status_from_weekly_metrics(
                target_pdf_auto_yield_pct=float(target_yield),
                operator_reviewable_yield_pct=float(operator_reviewable_yield),
            )
            if ship_gate_status != expected_ship_gate_status:
                errors.append(
                    "last_run ship_gate_status does not match target_pdf_auto_yield_pct/operator_reviewable_yield_pct: "
                    f"{ship_gate_status} != {expected_ship_gate_status}"
                )


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


def _verify_release_exception_record(text: str, reason: str, errors: list[str]) -> None:
    status = _status_value(text)
    if status != "APPROVED":
        errors.append("release exception record Status must be APPROVED")

    for row_label in REQUIRED_EXCEPTION_RECORD_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 2:
            errors.append(f"release exception record row missing or malformed: {row_label}")
            continue
        value = row[1]
        if _is_placeholder(value):
            errors.append(f"release exception record row is still placeholder: {row_label}")
        if row_label == "Exception reason" and value != reason:
            errors.append(f"release exception record Exception reason mismatch: {value} != {reason}")
        elif row_label == "Decision" and value != "APPROVED":
            errors.append("release exception record Decision must be APPROVED")
        elif row_label == "Approval date" and not _is_placeholder(value) and not _is_iso_date(value):
            errors.append("release exception record Approval date must be YYYY-MM-DD")
        elif row_label == "FY2026/R8 status acknowledged" and value.lower() != "yes":
            errors.append("release exception record FY2026/R8 status acknowledged must be yes")


def _case_fiscal_year(case: dict[str, Any]) -> int | None:
    fiscal_year = case.get("fiscal_year")
    if _is_number(fiscal_year):
        return int(fiscal_year)
    return None


def _case_ok(case: dict[str, Any]) -> bool:
    if case.get("ok") is not True:
        return False
    returncode = case.get("returncode")
    return returncode in (None, 0)


def _case_metric(case: dict[str, Any], field: str) -> Any:
    for source in (case, case.get("metrics"), case.get("last_run"), case.get("summary")):
        if isinstance(source, dict) and field in source:
            return source[field]
    return None


def _case_denominator(case: dict[str, Any]) -> Any:
    denominator = _case_metric(case, "target_pdf_auto_denominator_count")
    if denominator is None:
        denominator = _case_metric(case, "target_missing_school_count")
    return denominator


def _mature_year_cases(proof_json: dict[str, Any]) -> list[dict[str, Any]]:
    cases = proof_json.get("cases")
    if isinstance(cases, list):
        return [case for case in cases if isinstance(case, dict)]
    results = proof_json.get("results")
    if isinstance(results, list):
        return [case for case in results if isinstance(case, dict)]
    return []


def _verify_mature_year_proof(
    proof_json: dict[str, Any],
    *,
    target_fy: int | None,
    min_target_pdf_auto_yield: float,
    min_target_pdf_auto_denominator_count: int,
    max_manual_workload: float,
    errors: list[str],
) -> list[int]:
    if proof_json.get("ok") is not True:
        errors.append("mature-year proof JSON ok must be true")
    basis = proof_json.get("basis") or proof_json.get("metric_basis")
    if basis != MATURE_YEAR_SHIP_GATE_METRIC_BASIS:
        errors.append(
            "mature-year proof JSON basis must be "
            f"{MATURE_YEAR_SHIP_GATE_METRIC_BASIS}: {basis!r}"
        )
    cases = _mature_year_cases(proof_json)
    if not cases:
        errors.append("mature-year proof JSON must contain cases or results")
        return []
    passing_years: list[int] = []
    for case in cases:
        fiscal_year = _case_fiscal_year(case)
        if fiscal_year is None or not _case_ok(case):
            continue
        if target_fy is not None and fiscal_year >= target_fy:
            continue

        target_yield = _case_metric(case, "target_pdf_auto_yield_pct")
        denominator = _case_denominator(case)
        denominator_scope = _case_metric(case, "target_pdf_auto_denominator_scope")
        operator_reviewable_yield = _case_metric(case, "operator_reviewable_yield_pct")
        ship_gate_status = _case_metric(case, "ship_gate_status")
        case_ok = True
        if not _is_number(target_yield):
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_yield_pct must be numeric"
            )
            case_ok = False
        elif float(target_yield) < min_target_pdf_auto_yield:
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_yield_pct below release threshold: "
                f"{float(target_yield):.1f} < {min_target_pdf_auto_yield:.1f}"
            )
            case_ok = False
        if not _is_number(denominator):
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_denominator_count must be numeric"
            )
            case_ok = False
        elif float(denominator) < min_target_pdf_auto_denominator_count:
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_denominator_count below "
                f"production-scale threshold: {float(denominator):.0f} < "
                f"{min_target_pdf_auto_denominator_count}"
            )
            case_ok = False
        if denominator_scope != WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE:
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_denominator_scope must be "
                f"{WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE}: {denominator_scope!r}"
            )
            case_ok = False
        if not _is_number(operator_reviewable_yield):
            errors.append(
                f"mature-year proof case FY{fiscal_year} operator_reviewable_yield_pct must be numeric"
            )
            case_ok = False
        else:
            manual_workload = 100.0 - float(operator_reviewable_yield)
            if manual_workload > max_manual_workload + 1e-9:
                errors.append(
                    f"mature-year proof case FY{fiscal_year} estimated manual workload above release threshold: "
                    f"{manual_workload:.1f} > {max_manual_workload:.1f}"
                )
                case_ok = False
            expected_ship_gate_status = ship_gate_status_from_weekly_metrics(
                target_pdf_auto_yield_pct=float(target_yield) if _is_number(target_yield) else None,
                operator_reviewable_yield_pct=float(operator_reviewable_yield),
            )
            if ship_gate_status != expected_ship_gate_status:
                errors.append(
                    f"mature-year proof case FY{fiscal_year} ship_gate_status does not match "
                    "target_pdf_auto_yield_pct/operator_reviewable_yield_pct: "
                    f"{ship_gate_status} != {expected_ship_gate_status}"
                )
                case_ok = False
        if case_ok:
            passing_years.append(fiscal_year)
    if not passing_years:
        errors.append("mature-year proof JSON must include at least one passing fiscal year before target_fy")
    return sorted(set(passing_years), reverse=True)


def _verify_template(
    text: str,
    release_exception_reason: str | None,
    mature_year_proof_years: list[int],
    errors: list[str],
    warnings: list[str],
) -> None:
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
        elif release_exception_reason and verdict.lower() in EXCEPTION_KPI_VERDICTS:
            if verdict.lower() == "watch":
                warnings.append(f"release exception {release_exception_reason} accepted KPI verdict watch: {row_label}")
        elif verdict.lower() != "pass":
            errors.append(f"E2E template KPI verdict must be pass: {row_label}")

    for row_label in REQUIRED_ALWAYS_PASS_KPI_ROWS:
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

    output_file_block = _fenced_block_after(text, "出力ファイル:")
    if output_file_block is None or not output_file_block.strip():
        errors.append("E2E template Excel output file proof is missing or blank")
    elif not _has_generated_excel_output_path(output_file_block):
        errors.append("E2E template Excel output file proof must include a generated data/output/*.xlsx workbook path")

    if release_exception_reason:
        for row_label in REQUIRED_EXCEPTION_ROWS:
            row = _table_row(text, row_label)
            if row is None or len(row) < 4:
                errors.append(f"E2E template release-exception row missing or malformed: {row_label}")
                continue
            actual = row[2]
            verdict = row[3]
            if not actual:
                errors.append(f"E2E template release-exception actual is blank: {row_label}")
            if _is_placeholder(verdict):
                errors.append(f"E2E template release-exception verdict is still placeholder: {row_label}")
            elif verdict.lower() != "pass":
                errors.append(f"E2E template release-exception verdict must be pass: {row_label}")
            if row_label == "release exception reason" and actual != release_exception_reason:
                errors.append(
                    "E2E template release exception reason must match verifier argument: "
                    f"{actual} != {release_exception_reason}"
                )
            elif row_label == "mature-year proof years" and mature_year_proof_years:
                actual_years = _years_from_text(actual)
                expected_years = set(mature_year_proof_years)
                if actual_years != expected_years:
                    errors.append(
                        "E2E template mature-year proof years must match passing proof JSON years: "
                        f"{sorted(actual_years, reverse=True)} != {sorted(expected_years, reverse=True)}"
                    )

    for row_label in REQUIRED_RELEASE_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 2:
            errors.append(f"E2E template release row missing or malformed: {row_label}")
            continue
        if _is_placeholder(row[1]):
            errors.append(f"E2E template release row is still placeholder: {row_label}")
        elif row[1].lower() != REQUIRED_RELEASE_VALUES[row_label]:
            errors.append(f"E2E template release row must be {REQUIRED_RELEASE_VALUES[row_label]}: {row_label}")

    for row_label in REQUIRED_AUDIT_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 2:
            errors.append(f"E2E template audit row missing or malformed: {row_label}")
            continue
        value = row[1].strip()
        value_lower = value.lower()
        if _is_placeholder(value):
            errors.append(f"E2E template audit row is blank or placeholder: {row_label}")
            continue
        if row_label == "監査ログページ表示" and value_lower != "pass":
            errors.append("E2E template audit row must be pass: 監査ログページ表示")
        elif row_label == "manual_action_log 件数" and _parse_nonnegative_int(value) is None:
            errors.append("E2E template audit row must be a non-negative integer: manual_action_log 件数")
        elif row_label == "JSONL outbox 未送信件数" and not _outbox_flushed(value):
            errors.append("E2E template audit row must prove after-flush outbox count is 0: JSONL outbox 未送信件数")
        elif row_label == "audit-flush 実行" and value_lower not in {"pass", "not needed"}:
            errors.append("E2E template audit row must be pass or not needed: audit-flush 実行")
        elif row_label == "JSONL action_id 重複" and value_lower != "none":
            errors.append("E2E template audit row must be none: JSONL action_id 重複")

    conclusion = _fenced_block_after(text, "結論:")
    if conclusion is None or _is_placeholder(conclusion.strip()):
        errors.append("E2E template release conclusion is missing or still placeholder")
    else:
        normalized_conclusion = _release_conclusion_value(conclusion)
        if normalized_conclusion not in RELEASE_CONCLUSIONS:
            errors.append("E2E template release conclusion must be one of READY, RC_ONLY, NOT_READY")
        elif normalized_conclusion != RELEASE_APPROVAL_CONCLUSION:
            errors.append("E2E template release conclusion must be READY for release approval")

    for marker in ("Owner sign-off:", "業務員 sign-off:"):
        block = _fenced_block_after(text, marker)
        if block is None:
            errors.append(f"E2E template missing sign-off block: {marker}")
            continue
        for field in ("Name", "Date", "Decision"):
            value = _block_field_value(block, field)
            if not value:
                errors.append(f"E2E template {marker} {field} is blank")
            elif field == "Date" and not _is_iso_date(value):
                errors.append(f"E2E template {marker} Date must be YYYY-MM-DD")
            elif field == "Decision":
                normalized_decision = _release_conclusion_value(value)
                if normalized_decision not in RELEASE_CONCLUSIONS:
                    errors.append(f"E2E template {marker} Decision must be one of READY, RC_ONLY, NOT_READY")
                elif normalized_decision != RELEASE_APPROVAL_CONCLUSION:
                    errors.append(f"E2E template {marker} Decision must be READY for release approval")


def verify_stage6_return(
    *,
    e2e_template: Path,
    last_run: Path,
    evidence_verify_json: Path,
    target_fy: int | None = None,
    require_kpi: bool = True,
    min_target_pdf_auto_yield: float = 60.0,
    min_target_pdf_auto_denominator_count: int = MATURE_YEAR_PROOF_MIN_DENOMINATOR,
    max_manual_workload: float = 30.0,
    release_exception_reason: str | None = None,
    mature_year_proof_json: Path | None = None,
    release_exception_record: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    active_release_exception_reason: str | None = None
    mature_year_proof_years: list[int] = []

    if release_exception_reason:
        if is_ship_gate_exception_reason(release_exception_reason):
            active_release_exception_reason = release_exception_reason
        else:
            errors.append(f"unsupported release exception reason: {release_exception_reason}")
        if not require_kpi:
            errors.append("release exception cannot be combined with allow-unmeasured KPI mode")

    if active_release_exception_reason:
        if mature_year_proof_json is None:
            errors.append("release exception requires --mature-year-proof-json")
        else:
            proof_json = _load_json(mature_year_proof_json, errors, "mature-year proof JSON")
            if proof_json is not None:
                mature_year_proof_years = _verify_mature_year_proof(
                    proof_json,
                    target_fy=target_fy,
                    min_target_pdf_auto_yield=min_target_pdf_auto_yield,
                    min_target_pdf_auto_denominator_count=min_target_pdf_auto_denominator_count,
                    max_manual_workload=max_manual_workload,
                    errors=errors,
                )
        if release_exception_record is None:
            errors.append("release exception requires --release-exception-record")
        elif not release_exception_record.is_file():
            errors.append(f"release exception record does not exist: {release_exception_record}")
        else:
            _verify_release_exception_record(
                release_exception_record.read_text(encoding="utf-8"),
                active_release_exception_reason,
                errors,
            )

    last_run_json = _load_json(last_run, errors, "last_run")
    if last_run_json is not None:
        _verify_last_run(
            last_run_json,
            target_fy=target_fy,
            require_kpi=require_kpi,
            min_target_pdf_auto_yield=min_target_pdf_auto_yield,
            max_manual_workload=max_manual_workload,
            release_exception_reason=active_release_exception_reason,
            errors=errors,
            warnings=warnings,
        )

    verify_json = _load_json(evidence_verify_json, errors, "evidence verifier JSON")
    if verify_json is not None:
        _verify_evidence_verify_json(verify_json, errors)

    if not e2e_template.is_file():
        errors.append(f"E2E template does not exist: {e2e_template}")
    else:
        _verify_template(
            e2e_template.read_text(encoding="utf-8"),
            active_release_exception_reason,
            mature_year_proof_years,
            errors,
            warnings,
        )

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
            "min_target_pdf_auto_denominator_count": min_target_pdf_auto_denominator_count,
            "max_manual_workload": max_manual_workload,
            "release_exception_reason": active_release_exception_reason,
            "mature_year_proof_json": str(mature_year_proof_json) if mature_year_proof_json else None,
            "release_exception_record": str(release_exception_record) if release_exception_record else None,
        },
        "mature_year_proof_years": mature_year_proof_years,
        "required_evidence_labels": list(REQUIRED_EVIDENCE_LABELS),
        "required_kpi_rows": list(REQUIRED_KPI_ROWS),
        "required_always_pass_kpi_rows": list(REQUIRED_ALWAYS_PASS_KPI_ROWS),
        "required_exception_rows": list(REQUIRED_EXCEPTION_ROWS),
        "required_audit_rows": list(REQUIRED_AUDIT_ROWS),
        "required_release_rows": list(REQUIRED_RELEASE_ROWS),
        "release_conclusions": list(RELEASE_CONCLUSIONS),
        "release_exception_reasons": sorted(SHIP_GATE_EXCEPTION_REASONS),
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
        "--min-target-pdf-auto-denominator-count",
        type=int,
        default=MATURE_YEAR_PROOF_MIN_DENOMINATOR,
        help="Minimum mature-year target-missing denominator required for production-scale proof.",
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
    parser.add_argument(
        "--release-exception-reason",
        choices=sorted(SHIP_GATE_EXCEPTION_REASONS),
        help="Explicit release exception for measured KPI misses caused by a known external publication window.",
    )
    parser.add_argument(
        "--mature-year-proof-json",
        help="Required with --release-exception-reason: JSON proof that a mature fiscal-year matrix passed.",
    )
    parser.add_argument(
        "--release-exception-record",
        help="Required with --release-exception-reason: approved release exception Markdown record.",
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
        min_target_pdf_auto_denominator_count=args.min_target_pdf_auto_denominator_count,
        max_manual_workload=args.max_manual_workload,
        release_exception_reason=args.release_exception_reason,
        mature_year_proof_json=Path(args.mature_year_proof_json) if args.mature_year_proof_json else None,
        release_exception_record=Path(args.release_exception_record) if args.release_exception_record else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
