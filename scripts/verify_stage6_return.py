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
REQUIRED_OCR_SCOPE_ROW = "OCR scope 決定"
OCR_ADDON_SHA_ROW = "OCR add-on ZIP sha256"
OCR_SCOPE_CORE_NON_OCR_ONLY = "core_non_ocr_only"
OCR_SCOPE_ADDON_VERIFIED = "ocr_addon_verified"
OCR_SCOPE_VALUES = frozenset({OCR_SCOPE_CORE_NON_OCR_ONLY, OCR_SCOPE_ADDON_VERIFIED})
PUBLICATION_LAG_DECISION_BRIEF_DEFAULT = Path("docs/release/owner-decisions/publication-lag.md")
OCR_SCOPE_DECISION_BRIEF_DEFAULT = Path("docs/release/owner-decisions/ocr-scope.md")
PUBLICATION_LAG_DECISION_BRIEF_MARKERS = (
    "It is not approval by itself",
    "`APPROVE_RC_ONLY`",
    "at most `RC_ONLY`",
    "unconfirmed rows must not enter final Excel output",
    "successful `scripts/verify_stage6_return.py` result",
)
OCR_SCOPE_DECISION_BRIEF_COMMON_MARKERS = (
    "It is not approval by itself",
    "unreviewed OCR rows must not enter final Excel output",
    "With no OCR scope decision: `NOT_READY`",
)
OCR_SCOPE_DECISION_BRIEF_MARKERS = {
    OCR_SCOPE_CORE_NON_OCR_ONLY: (
        "`CORE_TEXT_PDF_ONLY`",
        "image-only PDFs must be visible as OCR/manual-review work",
    ),
    OCR_SCOPE_ADDON_VERIFIED: (
        "`OCR_ADDON_REQUIRED`",
        "missing OCR runtime proof remains a release blocker",
    ),
}
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
APPROVAL_AFTER_MATURE_YEAR_PROOF_ERROR = (
    "release exception record Approval date must be on or after mature-year proof finished_at date"
)
APPROVAL_AFTER_LAST_RUN_ERROR = (
    "release exception record Approval date must be on or after last_run finished_at date"
)
RELEASE_EXCEPTION_DATE_MATCH_ERROR = "release exception record Date must match Approval date"
SIGNOFF_PLACEHOLDER_NAMES = {
    "approver",
    "approver name",
    "example approver",
    "example operator",
    "example owner",
    "n/a",
    "na",
    "n.a.",
    "operator",
    "operator name",
    "owner",
    "owner name",
    "pending",
    "sample approver",
    "sample operator",
    "sample owner",
    "tbd",
    "to be determined",
    "your name",
    "-",
    "担当者",
    "承認者",
    "業務員",
    "未入力",
    "未定",
}
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
LAST_RUN_EVIDENCE_MATCH_ERROR = "must match last_run evidence"
STRICT_GAP_EVIDENCE_MATCH_ERROR = "must match strict_gap_analysis evidence"
LAST_RUN_EVIDENCE_STATUS_ERROR = "last_run evidence status must be success"
STRICT_GAP_EVIDENCE_BASIS_ERROR = "strict_gap_analysis evidence basis must be strict_yield_gap_analysis"
STRICT_GAP_EVIDENCE_SCHOOL_TYPE_ERROR = "strict_gap_analysis evidence school_type must be 専門学校"
STRICT_TARGET_RATE_COUNT_SCOPE = "strict_target_parsed_schools/schools_total"
EXCEL_READY_RATE_COUNT_SCOPE = "excel_ready_schools/schools_total"
OPERATOR_REVIEWABLE_RATE_COUNT_SCOPE = "operator_reviewable_schools/schools_total"
MANUAL_WORKLOAD_RATE_COUNT_ERROR = (
    "estimated_manual_workload_rate_pct must match operator_reviewable_schools/schools_total"
)


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
MATURE_YEAR_PROOF_SCHOOL_TYPE = _SHIP_GATE_CONTRACT.MATURE_YEAR_PROOF_SCHOOL_TYPE
V1_RELEASE_SCHOOL_TYPE = _SHIP_GATE_CONTRACT.V1_RELEASE_SCHOOL_TYPE
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


def _default_repo_path(relative_path: Path) -> Path:
    return Path(__file__).resolve().parents[1] / relative_path


def _load_text(path: Path, errors: list[str], label: str) -> str | None:
    if not path.is_file():
        errors.append(f"{label} does not exist: {path}")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"{label} is not valid UTF-8: {exc}")
        return None


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


def _header_field_value(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.strip().lower().startswith(f"{field.lower()}:"):
            return _clean_cell(line.split(":", 1)[1])
    return ""


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_RESULTS


def _is_signoff_placeholder(value: str) -> bool:
    normalized = value.strip().strip("`").strip().lower()
    return normalized in SIGNOFF_PLACEHOLDER_NAMES


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_integer_count(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonnegative_integer_count(value: object) -> TypeGuard[int]:
    return _is_integer_count(value) and value >= 0


def _rate_from_counts(count: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(count / total * 100.0, 1)


def _release_conclusion_value(value: str) -> str:
    return value.strip().upper()


def _parse_nonnegative_int(value: str) -> int | None:
    normalized = value.replace(",", "").strip()
    if not re.fullmatch(r"\d+", normalized):
        return None
    return int(normalized)


def _parse_numeric_cell(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if match is None:
        return None
    return float(match.group(0))


def _is_sha256(value: str) -> bool:
    return re.fullmatch(r"[0-9a-fA-F]{64}", _clean_cell(value)) is not None


def _iso_date_value(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _is_iso_date(value: str) -> bool:
    return _iso_date_value(value) is not None


def _is_future_iso_date(value: str) -> bool:
    parsed = _iso_date_value(value)
    if parsed is None:
        return False
    return parsed > date.today()


def _iso_datetime_value(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_iso_datetime(value: str) -> bool:
    return _iso_datetime_value(value) is not None


def _is_future_datetime_value(value: datetime) -> bool:
    if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
        return value > datetime.now(value.tzinfo)
    return value > datetime.now()


def _last_run_finished_date(last_run: dict[str, Any] | None) -> date | None:
    if last_run is None:
        return None
    finished_at = last_run.get("finished_at")
    if not isinstance(finished_at, str) or not finished_at:
        return None
    parsed = _iso_datetime_value(finished_at)
    return parsed.date() if parsed is not None else None


def _outbox_flushed(value: str) -> bool:
    normalized = value.lower().replace("`", "").strip()
    return normalized == "0" or "after flush 0" in normalized


def _has_generated_excel_output_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return ".xlsx" in normalized and "data/output/" in normalized


def _years_from_text(value: str) -> set[int]:
    return {int(match) for match in re.findall(r"\b(?:19|20)\d{2}\b", value)}


def _template_kpi_actual_expectations(last_run: dict[str, Any] | None) -> dict[str, tuple[str, float]]:
    if last_run is None:
        return {}
    expectations: dict[str, tuple[str, float]] = {}
    target_yield = last_run.get("target_pdf_auto_yield_pct")
    if _is_number(target_yield):
        expectations["strict target PDF 自動取得率"] = ("last_run target_pdf_auto_yield_pct", float(target_yield))
    operator_reviewable_yield = last_run.get("operator_reviewable_yield_pct")
    if _is_number(operator_reviewable_yield):
        expectations["推定手作業率"] = (
            "last_run estimated manual workload",
            100.0 - float(operator_reviewable_yield),
        )
    excel_ready_yield = last_run.get("target_pdf_excel_ready_yield_pct")
    if _is_number(excel_ready_yield):
        expectations["Excel ready 率"] = ("last_run target_pdf_excel_ready_yield_pct", float(excel_ready_yield))
    return expectations


def _verify_template_kpi_actual(
    *,
    row_label: str,
    actual: str,
    expectations: dict[str, tuple[str, float]],
    errors: list[str],
) -> None:
    expected = expectations.get(row_label)
    if expected is None:
        return
    source, expected_value = expected
    actual_value = _parse_numeric_cell(actual)
    if actual_value is None:
        errors.append(f"E2E template KPI actual must include numeric value for {row_label}")
        return
    if abs(actual_value - expected_value) > 0.05:
        errors.append(
            "E2E template KPI actual must match "
            f"{source}: {row_label} {actual_value:.1f} != {expected_value:.1f}"
        )


def _verify_template_ocr_scope(text: str, errors: list[str]) -> str | None:
    row = _table_row(text, REQUIRED_OCR_SCOPE_ROW)
    if row is None or len(row) < 2:
        errors.append(f"E2E template release row missing or malformed: {REQUIRED_OCR_SCOPE_ROW}")
        return None

    value = row[1]
    if _is_placeholder(value):
        errors.append(f"E2E template release row is still placeholder: {REQUIRED_OCR_SCOPE_ROW}")
        return None
    if value not in OCR_SCOPE_VALUES:
        errors.append(
            f"E2E template {REQUIRED_OCR_SCOPE_ROW} must be "
            f"{OCR_SCOPE_CORE_NON_OCR_ONLY} or {OCR_SCOPE_ADDON_VERIFIED}: {value}"
        )
        return None

    if value == OCR_SCOPE_ADDON_VERIFIED:
        sha_row = _table_row(text, OCR_ADDON_SHA_ROW)
        if sha_row is None or len(sha_row) < 2:
            errors.append(f"E2E template row missing or malformed: {OCR_ADDON_SHA_ROW}")
        elif not _is_sha256(sha_row[1]):
            errors.append(f"E2E template {OCR_ADDON_SHA_ROW} must be a 64-character SHA256")
    return value


def _verify_publication_lag_decision_brief(text: str, errors: list[str]) -> None:
    for marker in PUBLICATION_LAG_DECISION_BRIEF_MARKERS:
        if marker not in text:
            errors.append(f"publication-lag owner decision brief missing required marker: {marker}")


def _verify_ocr_scope_decision_brief(text: str, selected_scope: str, errors: list[str]) -> None:
    for marker in OCR_SCOPE_DECISION_BRIEF_COMMON_MARKERS:
        if marker not in text:
            errors.append(f"OCR scope owner decision brief missing required marker: {marker}")
    for marker in OCR_SCOPE_DECISION_BRIEF_MARKERS.get(selected_scope, ()):
        if marker not in text:
            errors.append(f"OCR scope owner decision brief missing marker for {selected_scope}: {marker}")


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
    elif (parsed_finished_at := _iso_datetime_value(finished_at)) is None:
        errors.append("last_run finished_at must be ISO datetime")
    elif _is_future_datetime_value(parsed_finished_at):
        errors.append("last_run finished_at must not be in the future")
    if last_run.get("dry_run") is not False:
        errors.append("last_run dry_run must be false")
    if target_fy is not None and last_run.get("current_fy") != target_fy:
        errors.append(f"last_run current_fy must be {target_fy}")
    if last_run.get("school_type") != V1_RELEASE_SCHOOL_TYPE:
        errors.append(f"last_run school_type must be {V1_RELEASE_SCHOOL_TYPE}")

    if require_kpi:
        target_yield = last_run.get("target_pdf_auto_yield_pct")
        operator_reviewable_yield = last_run.get("operator_reviewable_yield_pct")
        excel_ready_yield = last_run.get("target_pdf_excel_ready_yield_pct")
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
        if not _is_number(excel_ready_yield):
            errors.append("last_run target_pdf_excel_ready_yield_pct must be numeric for final return evidence")
        else:
            excel_ready_yield_value = float(excel_ready_yield)
            if excel_ready_yield_value < min_target_pdf_auto_yield:
                message = (
                    "last_run target_pdf_excel_ready_yield_pct below release threshold: "
                    f"{excel_ready_yield_value:.1f} < {min_target_pdf_auto_yield:.1f}"
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


def _verify_release_exception_record(
    text: str,
    reason: str,
    *,
    mature_year_proof_finished_date: date | None,
    last_run_finished_date: date | None,
    errors: list[str],
) -> date | None:
    record_date_value = _header_field_value(text, "Date")
    record_date: date | None = None
    accepted_approval_date: date | None = None
    if not record_date_value:
        errors.append("release exception record Date is required")
    else:
        record_date = _iso_date_value(record_date_value)
        if record_date is None:
            errors.append("release exception record Date must be YYYY-MM-DD")
        elif record_date > date.today():
            errors.append("release exception record Date must not be in the future")
            record_date = None

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
        elif row_label == "Approver" and _is_signoff_placeholder(value):
            errors.append("release exception record Approver must not be a placeholder")
        elif row_label == "Approval date":
            approval_date = _iso_date_value(value)
            if _is_placeholder(value):
                errors.append("release exception record Approval date is required")
            elif approval_date is None:
                errors.append("release exception record Approval date must be YYYY-MM-DD")
            elif approval_date is not None and approval_date > date.today():
                errors.append("release exception record Approval date must not be in the future")
            elif (
                approval_date is not None
                and mature_year_proof_finished_date is not None
                and approval_date < mature_year_proof_finished_date
            ):
                errors.append(APPROVAL_AFTER_MATURE_YEAR_PROOF_ERROR)
            elif (
                approval_date is not None
                and last_run_finished_date is not None
                and approval_date < last_run_finished_date
            ):
                errors.append(APPROVAL_AFTER_LAST_RUN_ERROR)
            elif approval_date is not None and record_date is not None and approval_date != record_date:
                errors.append(RELEASE_EXCEPTION_DATE_MATCH_ERROR)
            else:
                accepted_approval_date = approval_date
        elif row_label == "Release scope":
            normalized = value.lower()
            if not all(token in normalized for token in ("v1.0", "mature", "proof", "only")):
                errors.append(
                    "release exception record Release scope must limit approval to v1.0 mature-year proof only"
                )
        elif row_label == "FY2026/R8 status acknowledged" and value.lower() != "yes":
            errors.append("release exception record FY2026/R8 status acknowledged must be yes")
        elif row_label == "Required follow-up":
            normalized = value.lower()
            if not all(token in normalized for token in ("fy2026", "r8", "strict-yield")):
                errors.append(
                    "release exception record Required follow-up must require FY2026/R8 strict-yield rerun"
                )
    return accepted_approval_date


def _case_fiscal_year(case: dict[str, Any]) -> int | None:
    fiscal_year = case.get("fiscal_year")
    if isinstance(fiscal_year, int) and not isinstance(fiscal_year, bool):
        return fiscal_year
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


def _case_evidence_source(case: dict[str, Any]) -> str | None:
    evidence_source = case.get("evidence_source")
    if isinstance(evidence_source, str) and evidence_source:
        return evidence_source
    if isinstance(case.get("last_run"), str) and case["last_run"]:
        return "last_run"
    if isinstance(case.get("strict_gap_analysis"), str) and case["strict_gap_analysis"]:
        return "strict_gap_analysis"
    return None


def _case_evidence_path(path_value: str, proof_json_path: Path | None) -> Path | None:
    path = Path(path_value)
    candidates = [path]
    if proof_json_path is not None and not path.is_absolute():
        candidates.insert(0, proof_json_path.parent / path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _append_evidence_mismatch(
    *,
    errors: list[str],
    fiscal_year: int,
    match_error: str,
    field: str,
    proof_value: object,
    evidence_value: object,
    evidence_field: str | None = None,
) -> bool:
    if proof_value == evidence_value:
        return True
    field_label = field if evidence_field is None else f"{field}/{evidence_field}"
    errors.append(
        f"mature-year proof case FY{fiscal_year} {field_label} {match_error}: "
        f"{proof_value!r} != {evidence_value!r}"
    )
    return False


def _verify_last_run_mature_year_evidence(
    *,
    evidence_path: Path,
    fiscal_year: int,
    target_yield: object,
    denominator: object,
    denominator_scope: object,
    operator_reviewable_yield: object,
    ship_gate_status: object,
    school_type: object,
    finished_at: object,
    errors: list[str],
) -> bool:
    evidence_label = f"mature-year proof case FY{fiscal_year} last_run evidence"
    payload = _load_json(evidence_path, errors, evidence_label)
    if payload is None:
        return False

    ok = True
    if payload.get("status") != "success":
        errors.append(f"mature-year proof case FY{fiscal_year} {LAST_RUN_EVIDENCE_STATUS_ERROR}")
        ok = False
    if payload.get("dry_run") is not False:
        errors.append(f"{evidence_label} dry_run must be false")
        ok = False
    if payload.get("current_fy") != fiscal_year:
        errors.append(f"{evidence_label} current_fy must be {fiscal_year}")
        ok = False
    if payload.get("school_type") != V1_RELEASE_SCHOOL_TYPE:
        errors.append(
            f"mature-year proof case FY{fiscal_year} last_run evidence school_type must be "
            f"{V1_RELEASE_SCHOOL_TYPE}"
        )
        ok = False

    evidence_denominator = payload.get("target_pdf_auto_denominator_count")
    if evidence_denominator is None:
        evidence_denominator = payload.get("target_missing_school_count")

    checks = (
        ("finished_at", finished_at, payload.get("finished_at"), None),
        ("school_type", school_type, payload.get("school_type"), None),
        ("target_pdf_auto_denominator_count", denominator, evidence_denominator, None),
        (
            "target_pdf_auto_denominator_scope",
            denominator_scope,
            payload.get("target_pdf_auto_denominator_scope"),
            None,
        ),
        ("target_pdf_auto_yield_pct", target_yield, payload.get("target_pdf_auto_yield_pct"), None),
        (
            "operator_reviewable_yield_pct",
            operator_reviewable_yield,
            payload.get("operator_reviewable_yield_pct"),
            None,
        ),
        ("ship_gate_status", ship_gate_status, payload.get("ship_gate_status"), None),
    )
    for field, proof_value, evidence_value, evidence_field in checks:
        ok = (
            _append_evidence_mismatch(
                errors=errors,
                fiscal_year=fiscal_year,
                match_error=LAST_RUN_EVIDENCE_MATCH_ERROR,
                field=field,
                proof_value=proof_value,
                evidence_value=evidence_value,
                evidence_field=evidence_field,
            )
            and ok
        )
    return ok


def _verify_strict_gap_count_rate(
    *,
    payload: dict[str, Any],
    fiscal_year: int,
    total: int,
    count_field: str,
    rate_field: str,
    errors: list[str],
) -> bool:
    count_value = payload.get(count_field)
    rate_value = payload.get(rate_field)
    if not _is_nonnegative_integer_count(count_value):
        errors.append(
            f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
            f"{count_field} must be a nonnegative integer"
        )
        return False
    if count_value > total:
        errors.append(
            f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
            f"{count_field} must be <= schools_total"
        )
        return False
    if not _is_number(rate_value):
        errors.append(
            f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
            f"{rate_field} must be numeric"
        )
        return False
    expected_rate = _rate_from_counts(count_value, total)
    count_scope = {
        "strict_target_parsed_schools": STRICT_TARGET_RATE_COUNT_SCOPE,
        "excel_ready_schools": EXCEL_READY_RATE_COUNT_SCOPE,
        "operator_reviewable_schools": OPERATOR_REVIEWABLE_RATE_COUNT_SCOPE,
    }.get(count_field, f"{count_field}/schools_total")
    if expected_rate is None or abs(float(rate_value) - expected_rate) > 1e-9:
        errors.append(
            f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence {rate_field} "
            f"must match {count_scope}: {float(rate_value):.1f} != {expected_rate:.1f}"
        )
        return False
    return True


def _verify_strict_gap_mature_year_evidence(
    *,
    evidence_path: Path,
    fiscal_year: int,
    target_yield: object,
    excel_ready_yield: object,
    denominator: object,
    operator_reviewable_yield: object,
    school_type: object,
    finished_at: object,
    errors: list[str],
) -> bool:
    evidence_label = f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence"
    payload = _load_json(evidence_path, errors, evidence_label)
    if payload is None:
        return False

    ok = True
    if payload.get("basis") != "strict_yield_gap_analysis":
        errors.append(f"mature-year proof case FY{fiscal_year} {STRICT_GAP_EVIDENCE_BASIS_ERROR}")
        ok = False
    if payload.get("school_type") != MATURE_YEAR_PROOF_SCHOOL_TYPE:
        errors.append(f"mature-year proof case FY{fiscal_year} {STRICT_GAP_EVIDENCE_SCHOOL_TYPE_ERROR}")
        ok = False
    if payload.get("fiscal_year") != fiscal_year:
        errors.append(f"{evidence_label} fiscal_year must be {fiscal_year}")
        ok = False
    total = payload.get("schools_total")
    if not _is_nonnegative_integer_count(total):
        errors.append(
            f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
            "schools_total must be a nonnegative integer"
        )
        ok = False
        total_for_rate = 0
    elif total <= 0:
        errors.append(f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence schools_total must be > 0")
        ok = False
        total_for_rate = 0
    else:
        total_for_rate = total

    if total_for_rate > 0:
        strict_rate_ok = _verify_strict_gap_count_rate(
            payload=payload,
            fiscal_year=fiscal_year,
            total=total_for_rate,
            count_field="strict_target_parsed_schools",
            rate_field="strict_target_parsed_rate_pct",
            errors=errors,
        )
        excel_ready_rate_ok = _verify_strict_gap_count_rate(
            payload=payload,
            fiscal_year=fiscal_year,
            total=total_for_rate,
            count_field="excel_ready_schools",
            rate_field="excel_ready_rate_pct",
            errors=errors,
        )
        operator_reviewable_rate_ok = _verify_strict_gap_count_rate(
            payload=payload,
            fiscal_year=fiscal_year,
            total=total_for_rate,
            count_field="operator_reviewable_schools",
            rate_field="operator_reviewable_rate_pct",
            errors=errors,
        )
        ok = strict_rate_ok and excel_ready_rate_ok and operator_reviewable_rate_ok and ok
        manual_workload_rate = payload.get("estimated_manual_workload_rate_pct")
        if not _is_number(manual_workload_rate):
            errors.append(
                f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
                "estimated_manual_workload_rate_pct must be numeric"
            )
            ok = False
        else:
            operator_reviewable_count = payload.get("operator_reviewable_schools")
            if _is_nonnegative_integer_count(operator_reviewable_count):
                expected_manual_workload = round(100.0 - (operator_reviewable_count / total_for_rate * 100.0), 1)
                if abs(float(manual_workload_rate) - expected_manual_workload) > 1e-9:
                    errors.append(
                        f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence "
                        f"{MANUAL_WORKLOAD_RATE_COUNT_ERROR}: "
                        f"{float(manual_workload_rate):.1f} != {expected_manual_workload:.1f}"
                    )
                    ok = False
            else:
                ok = False

    evidence_finished_at = payload.get("finished_at") or payload.get("generated_at")
    checks = (
        ("finished_at", finished_at, evidence_finished_at, None),
        ("school_type", school_type, payload.get("school_type"), None),
        ("target_pdf_auto_denominator_count", denominator, payload.get("schools_total"), "schools_total"),
        (
            "target_pdf_auto_yield_pct",
            target_yield,
            payload.get("strict_target_parsed_rate_pct"),
            "strict_target_parsed_rate_pct",
        ),
        (
            "excel_ready_yield_pct",
            excel_ready_yield,
            payload.get("excel_ready_rate_pct"),
            "excel_ready_rate_pct",
        ),
        (
            "operator_reviewable_yield_pct",
            operator_reviewable_yield,
            payload.get("operator_reviewable_rate_pct"),
            "operator_reviewable_rate_pct",
        ),
    )
    for field, proof_value, evidence_value, evidence_field in checks:
        ok = (
            _append_evidence_mismatch(
                errors=errors,
                fiscal_year=fiscal_year,
                match_error=STRICT_GAP_EVIDENCE_MATCH_ERROR,
                field=field,
                proof_value=proof_value,
                evidence_value=evidence_value,
                evidence_field=evidence_field,
            )
            and ok
        )
    return ok


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
    proof_json_path: Path | None,
    target_fy: int | None,
    min_target_pdf_auto_yield: float,
    min_target_pdf_auto_denominator_count: int,
    max_manual_workload: float,
    errors: list[str],
) -> tuple[list[int], date | None]:
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
        return [], None
    passing_years: list[int] = []
    passing_finished_dates: list[date] = []
    for case in cases:
        fiscal_year = _case_fiscal_year(case)
        if fiscal_year is None:
            if _case_ok(case):
                errors.append(
                    "mature-year proof case fiscal_year must be an integer: "
                    f"{case.get('fiscal_year')!r}"
                )
            continue
        if not _case_ok(case):
            continue
        if target_fy is not None and fiscal_year >= target_fy:
            continue

        target_yield = _case_metric(case, "target_pdf_auto_yield_pct")
        excel_ready_yield = _case_metric(case, "excel_ready_yield_pct")
        denominator = _case_denominator(case)
        denominator_scope = _case_metric(case, "target_pdf_auto_denominator_scope")
        operator_reviewable_yield = _case_metric(case, "operator_reviewable_yield_pct")
        school_type = _case_metric(case, "school_type")
        ship_gate_status = _case_metric(case, "ship_gate_status")
        evidence_source = _case_evidence_source(case)
        finished_at = case.get("finished_at")
        finished_date: date | None = None
        case_ok = True
        if evidence_source is None:
            errors.append(f"mature-year proof case FY{fiscal_year} evidence source is required")
            case_ok = False
        elif evidence_source == "last_run":
            last_run_path = case.get("last_run")
            if not isinstance(last_run_path, str) or not last_run_path:
                errors.append(f"mature-year proof case FY{fiscal_year} last_run evidence path is required")
                case_ok = False
            else:
                resolved_last_run_path = _case_evidence_path(last_run_path, proof_json_path)
                if resolved_last_run_path is None:
                    errors.append(
                        f"mature-year proof case FY{fiscal_year} last_run evidence path does not exist: "
                        f"{last_run_path}"
                    )
                    case_ok = False
                elif not _verify_last_run_mature_year_evidence(
                    evidence_path=resolved_last_run_path,
                    fiscal_year=fiscal_year,
                    target_yield=target_yield,
                    denominator=denominator,
                    denominator_scope=denominator_scope,
                    operator_reviewable_yield=operator_reviewable_yield,
                    ship_gate_status=ship_gate_status,
                    school_type=school_type,
                    finished_at=finished_at,
                    errors=errors,
                ):
                    case_ok = False
        elif evidence_source == "strict_gap_analysis":
            strict_gap_analysis_path = case.get("strict_gap_analysis")
            if not isinstance(strict_gap_analysis_path, str) or not strict_gap_analysis_path:
                errors.append(f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence path is required")
                case_ok = False
            else:
                resolved_strict_gap_analysis_path = _case_evidence_path(strict_gap_analysis_path, proof_json_path)
                if resolved_strict_gap_analysis_path is None:
                    errors.append(
                        f"mature-year proof case FY{fiscal_year} strict_gap_analysis evidence path does not exist: "
                        f"{strict_gap_analysis_path}"
                    )
                    case_ok = False
                elif not _verify_strict_gap_mature_year_evidence(
                    evidence_path=resolved_strict_gap_analysis_path,
                    fiscal_year=fiscal_year,
                    target_yield=target_yield,
                    excel_ready_yield=excel_ready_yield,
                    denominator=denominator,
                    operator_reviewable_yield=operator_reviewable_yield,
                    school_type=school_type,
                    finished_at=finished_at,
                    errors=errors,
                ):
                    case_ok = False
        else:
            errors.append(
                f"mature-year proof case FY{fiscal_year} evidence source must be last_run or strict_gap_analysis"
            )
            case_ok = False
        if finished_at in (None, ""):
            errors.append(f"mature-year proof case FY{fiscal_year} finished_at is required")
            case_ok = False
        elif not isinstance(finished_at, str):
            errors.append(f"mature-year proof case FY{fiscal_year} finished_at must be ISO datetime")
            case_ok = False
        else:
            parsed_finished_at = _iso_datetime_value(finished_at)
            if parsed_finished_at is None:
                errors.append(f"mature-year proof case FY{fiscal_year} finished_at must be ISO datetime")
                case_ok = False
            elif _is_future_datetime_value(parsed_finished_at):
                errors.append(f"mature-year proof case FY{fiscal_year} finished_at must not be in the future")
                case_ok = False
            else:
                finished_date = parsed_finished_at.date()
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
        if evidence_source == "last_run" and school_type != V1_RELEASE_SCHOOL_TYPE:
            errors.append(
                f"mature-year proof case FY{fiscal_year} school_type must be "
                f"{V1_RELEASE_SCHOOL_TYPE}: {school_type!r}"
            )
            case_ok = False
        if evidence_source == "strict_gap_analysis":
            if school_type != MATURE_YEAR_PROOF_SCHOOL_TYPE:
                errors.append(
                    f"mature-year proof case FY{fiscal_year} school_type must be "
                    f"{MATURE_YEAR_PROOF_SCHOOL_TYPE}: {school_type!r}"
                )
                case_ok = False
            if not _is_number(excel_ready_yield):
                errors.append(
                    f"mature-year proof case FY{fiscal_year} excel_ready_yield_pct must be numeric"
                )
                case_ok = False
            elif float(excel_ready_yield) < min_target_pdf_auto_yield:
                errors.append(
                    f"mature-year proof case FY{fiscal_year} excel_ready_yield_pct below release threshold: "
                    f"{float(excel_ready_yield):.1f} < {min_target_pdf_auto_yield:.1f}"
                )
                case_ok = False
        if not _is_number(denominator):
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_denominator_count must be numeric"
            )
            case_ok = False
        elif not _is_integer_count(denominator):
            errors.append(
                f"mature-year proof case FY{fiscal_year} target_pdf_auto_denominator_count must be an integer"
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
            if finished_date is not None:
                passing_finished_dates.append(finished_date)
    if not passing_years:
        errors.append("mature-year proof JSON must include at least one passing fiscal year before target_fy")
    mature_year_proof_finished_date = max(passing_finished_dates) if passing_finished_dates else None
    return sorted(set(passing_years), reverse=True), mature_year_proof_finished_date


def _verify_template(
    text: str,
    last_run: dict[str, Any] | None,
    release_exception_reason: str | None,
    release_exception_approval_date: date | None,
    mature_year_proof_json: Path | None,
    mature_year_proof_years: list[int],
    errors: list[str],
    warnings: list[str],
) -> str | None:
    kpi_actual_expectations = _template_kpi_actual_expectations(last_run)
    last_run_finished_date = _last_run_finished_date(last_run)
    for row_label in REQUIRED_KPI_ROWS:
        row = _table_row(text, row_label)
        if row is None or len(row) < 4:
            errors.append(f"E2E template KPI row missing or malformed: {row_label}")
            continue
        actual = row[2]
        verdict = row[3]
        if not actual:
            errors.append(f"E2E template KPI actual is blank: {row_label}")
        else:
            _verify_template_kpi_actual(
                row_label=row_label,
                actual=actual,
                expectations=kpi_actual_expectations,
                errors=errors,
            )
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
            elif row_label == "mature-year proof JSON" and mature_year_proof_json is not None:
                expected_file = mature_year_proof_json.name
                if expected_file not in actual:
                    errors.append(
                        "E2E template mature-year proof JSON must reference verifier proof JSON file: "
                        f"{actual} does not include {expected_file}"
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

    selected_ocr_scope = _verify_template_ocr_scope(text, errors)

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
            elif field == "Name" and _is_signoff_placeholder(value):
                errors.append(f"E2E template {marker} Name must not be a placeholder")
            elif field == "Date":
                signoff_date = _iso_date_value(value)
                if signoff_date is None:
                    errors.append(f"E2E template {marker} Date must be YYYY-MM-DD")
                elif signoff_date > date.today():
                    errors.append(f"E2E template {marker} Date must not be in the future")
                elif last_run_finished_date is not None and signoff_date < last_run_finished_date:
                    errors.append(
                        f"E2E template {marker} Date must be on or after last_run finished_at date"
                    )
                elif release_exception_approval_date is not None and signoff_date < release_exception_approval_date:
                    errors.append(
                        f"E2E template {marker} Date must be on or after release exception Approval date"
                    )
            elif field == "Decision":
                normalized_decision = _release_conclusion_value(value)
                if normalized_decision not in RELEASE_CONCLUSIONS:
                    errors.append(f"E2E template {marker} Decision must be one of READY, RC_ONLY, NOT_READY")
                elif normalized_decision != RELEASE_APPROVAL_CONCLUSION:
                    errors.append(f"E2E template {marker} Decision must be READY for release approval")
    return selected_ocr_scope


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
    publication_lag_decision_brief: Path | None = None,
    ocr_scope_decision_brief: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    active_release_exception_reason: str | None = None
    mature_year_proof_years: list[int] = []
    mature_year_proof_finished_date: date | None = None
    release_exception_approval_date: date | None = None
    selected_ocr_scope: str | None = None
    active_publication_lag_decision_brief = publication_lag_decision_brief
    active_ocr_scope_decision_brief = ocr_scope_decision_brief
    last_run_json = _load_json(last_run, errors, "last_run")
    last_run_finished_date = _last_run_finished_date(last_run_json)

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
                mature_year_proof_years, mature_year_proof_finished_date = _verify_mature_year_proof(
                    proof_json,
                    proof_json_path=mature_year_proof_json,
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
            release_exception_approval_date = _verify_release_exception_record(
                release_exception_record.read_text(encoding="utf-8"),
                active_release_exception_reason,
                mature_year_proof_finished_date=mature_year_proof_finished_date,
                last_run_finished_date=last_run_finished_date,
                errors=errors,
            )
        if active_release_exception_reason == "publication_lag":
            if active_publication_lag_decision_brief is None:
                active_publication_lag_decision_brief = _default_repo_path(PUBLICATION_LAG_DECISION_BRIEF_DEFAULT)
            brief_text = _load_text(
                active_publication_lag_decision_brief,
                errors,
                "publication-lag owner decision brief",
            )
            if brief_text is not None:
                _verify_publication_lag_decision_brief(brief_text, errors)

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
        selected_ocr_scope = _verify_template(
            e2e_template.read_text(encoding="utf-8"),
            last_run_json,
            active_release_exception_reason,
            release_exception_approval_date,
            mature_year_proof_json,
            mature_year_proof_years,
            errors,
            warnings,
        )

    if selected_ocr_scope is not None:
        if active_ocr_scope_decision_brief is None:
            active_ocr_scope_decision_brief = _default_repo_path(OCR_SCOPE_DECISION_BRIEF_DEFAULT)
        brief_text = _load_text(active_ocr_scope_decision_brief, errors, "OCR scope owner decision brief")
        if brief_text is not None:
            _verify_ocr_scope_decision_brief(brief_text, selected_ocr_scope, errors)

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
            "publication_lag_decision_brief": (
                str(active_publication_lag_decision_brief) if active_publication_lag_decision_brief else None
            ),
            "ocr_scope_decision_brief": (
                str(active_ocr_scope_decision_brief) if active_ocr_scope_decision_brief else None
            ),
        },
        "selected_ocr_scope": selected_ocr_scope,
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
    parser.add_argument(
        "--publication-lag-decision-brief",
        help=(
            "Owner decision brief for publication_lag. Defaults to "
            "docs/release/owner-decisions/publication-lag.md when publication_lag is used."
        ),
    )
    parser.add_argument(
        "--ocr-scope-decision-brief",
        help="Owner decision brief for the OCR scope selected in the E2E template.",
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
        publication_lag_decision_brief=(
            Path(args.publication_lag_decision_brief) if args.publication_lag_decision_brief else None
        ),
        ocr_scope_decision_brief=Path(args.ocr_scope_decision_brief) if args.ocr_scope_decision_brief else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
