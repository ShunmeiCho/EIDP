"""Build a false-reject audit packet from a Stage 6 evidence ZIP.

The tool is read-only. It helps decide whether a below-gate strict-yield result
is caused by specific over-rejection bugs or by correctly rejected old-year,
non-target, unknown-year, and identity-risk candidates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))

from verify_stage6_evidence import verify_stage6_evidence_bundle

VALID_REVIEW_DECISIONS = ("", "false_reject", "correct_reject", "needs_operator_review")
REVIEW_MUTABLE_COLUMNS = {"decision", "reviewer", "reviewed_at", "notes"}
DECISIONS_REQUIRING_NOTES = {"false_reject", "needs_operator_review"}

OBVIOUS_NON_TARGET_HINTS = (
    "gpa",
    "ＧＰＡ",
    "学校評価",
    "学校関係者評価",
    "学校沿革",
    "実務経験",
    "授業科目",
    "シラバス",
    "syllabus",
    "admission",
    "募集",
    "入学",
)

REQUIRED_LABELS = (
    "build_info",
    "diagnostics",
    "last_run",
    "discovery_evidence",
    "discovery_rca",
)

AUDIT_BUCKETS = (
    {
        "bucket": "fiscal_year_mismatch",
        "reason_prefixes": ("fiscal_year_mismatch",),
        "review_question": "Are these true old-year target forms, or did FY2026/R8 evidence get missed?",
        "false_reject_signal": "PDF/page/anchor contains trusted FY2026/R8 evidence but the row was rejected.",
    },
    {
        "bucket": "pre_filtered_non_target_hint",
        "reason_prefixes": ("pre_filtered_non_target_hint",),
        "review_question": "Did pre-download filtering reject any real target application form?",
        "false_reject_signal": (
            "Anchor/page/PDF title is a target application form, not GPA/syllabus/admission/evaluation material."
        ),
    },
    {
        "bucket": "classified_non_target",
        "reason_prefixes": ("classified_non_target",),
        "review_question": "Did the classifier mark any target application form as non-target?",
        "false_reject_signal": "PDF is a target application form despite the non-target classification.",
    },
    {
        "bucket": "target_fiscal_year_not_detected",
        "reason_prefixes": ("target_fiscal_year_not_detected",),
        "review_question": (
            "Can trusted FY2026/R8 evidence be found in the official page, anchor, filename, or PDF body?"
        ),
        "false_reject_signal": "Trusted FY2026/R8 evidence exists but was not propagated to verification.",
    },
    {
        "bucket": "site_entry_fetch_identity",
        "reason_prefixes": ("no_candidates_found", "discovery_error", "pdf_school_mismatch"),
        "review_question": "Is this a SiteEntry, fetch, or school-identity gap rather than a missing-publication case?",
        "false_reject_signal": "The official source points to a valid FY2026/R8 target document for the same school.",
    },
)


def _entry_by_suffix(names: list[str], suffix: str) -> str:
    matches = sorted(name for name in names if name.replace("\\", "/").endswith(suffix))
    if not matches:
        raise ValueError(f"archive is missing an entry ending with {suffix!r}")
    if len(matches) > 1:
        raise ValueError(f"archive has multiple entries ending with {suffix!r}: {matches}")
    return matches[0]


def _load_json_entry(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    payload = json.loads(zf.read(name).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return payload


def _load_jsonl_entry(zf: zipfile.ZipFile, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(zf.read(name).decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{name}:{line_number} must contain a JSON object")
        rows.append(payload)
    return rows


def _as_int(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _rate(count: int, denominator: int) -> float | None:
    return round(count / denominator * 100.0, 1) if denominator else None


def _row_reason(row: dict[str, Any]) -> str:
    return str(row.get("reason") or "unknown")


def _matches_reason(row: dict[str, Any], prefixes: tuple[str, ...]) -> bool:
    reason = _row_reason(row)
    return any(reason == prefix or reason.startswith(f"{prefix}:") for prefix in prefixes)


def _row_sort_key(row: dict[str, Any]) -> tuple[int, str, str, str]:
    school_id = row.get("school_id")
    return (
        school_id if isinstance(school_id, int) else 10**9,
        _row_reason(row),
        str(row.get("pdf_url") or ""),
        str(row.get("page_url") or ""),
    )


def _row_identity(row: dict[str, Any]) -> tuple[object, ...]:
    return (
        row.get("school_id"),
        _row_reason(row),
        row.get("pdf_url"),
        row.get("page_url"),
        row.get("anchor_text"),
    )


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[object, ...]] = set()
    unique: list[dict[str, Any]] = []
    for row in sorted(rows, key=_row_sort_key):
        key = _row_identity(row)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _sample_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    unique = _dedupe_rows(rows)
    sample: list[dict[str, Any]] = []
    used_keys: set[tuple[object, ...]] = set()
    seen_schools: set[object] = set()

    for row in unique:
        school_id = row.get("school_id")
        if school_id in seen_schools:
            continue
        seen_schools.add(school_id)
        sample.append(row)
        used_keys.add(_row_identity(row))
        if len(sample) >= limit:
            return sample

    for row in unique:
        key = _row_identity(row)
        if key in used_keys:
            continue
        sample.append(row)
        if len(sample) >= limit:
            break
    return sample


def _extra_value(row: dict[str, Any], key: str) -> str:
    extra = row.get("extra")
    if isinstance(extra, dict):
        value = extra.get(key)
        if value is not None:
            return str(value)
    value = row.get(key)
    return "" if value is None else str(value)


def _audit_row_id(bucket: str, row: dict[str, Any]) -> str:
    payload = "\n".join(
        (
            bucket,
            str(row.get("school_id") or ""),
            _row_reason(row),
            str(row.get("page_url") or ""),
            str(row.get("pdf_url") or ""),
            str(row.get("anchor_text") or ""),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _project_row(bucket: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_row_id": _audit_row_id(bucket, row),
        "school_id": row.get("school_id"),
        "reason": _row_reason(row),
        "pdf_type": row.get("pdf_type") or "",
        "detected_fiscal_year": row.get("detected_fiscal_year"),
        "year_evidence": row.get("year_evidence") or _extra_value(row, "year_evidence"),
        "trusted_year_evidence": row.get("trusted_year_evidence") or _extra_value(row, "trusted_year_evidence"),
        "discovery_method": _extra_value(row, "discovery_method"),
        "anchor_text": row.get("anchor_text") or "",
        "page_url": row.get("page_url") or "",
        "pdf_url": row.get("pdf_url") or "",
        "score": row.get("score"),
    }


def _reason_year(reason: str) -> int | None:
    _, _, suffix = reason.partition(":")
    if suffix.isdigit():
        return int(suffix)
    return None


def _suggested_triage_decision(
    *,
    bucket_name: str,
    row: dict[str, Any],
    target_fiscal_year: int | None,
) -> tuple[str, str]:
    """Return non-binding review guidance for the owner/operator worksheet."""

    reason = str(row.get("reason") or "")
    detected_fiscal_year = row.get("detected_fiscal_year")
    if not isinstance(detected_fiscal_year, int):
        detected_fiscal_year = _reason_year(reason)
    target_label = f"FY{target_fiscal_year}" if target_fiscal_year is not None else "target FY"

    if bucket_name == "fiscal_year_mismatch":
        if detected_fiscal_year is not None and detected_fiscal_year != target_fiscal_year:
            return (
                "correct_reject",
                (
                    f"Detected fiscal year {detected_fiscal_year} is not {target_label}; "
                    "confirm no trusted target-year evidence exists."
                ),
            )
        return ("", "Review whether trusted target-year evidence was missed.")

    if bucket_name in {"pre_filtered_non_target_hint", "classified_non_target"}:
        evidence_text = " ".join(
            str(row.get(key) or "") for key in ("anchor_text", "page_url", "pdf_url", "reason", "pdf_type")
        )
        evidence_text_lower = evidence_text.lower()
        if any(hint.lower() in evidence_text_lower or hint in evidence_text for hint in OBVIOUS_NON_TARGET_HINTS):
            return (
                "correct_reject",
                "Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.",
            )
        return ("", "Review whether this non-target classification rejected a real target application form.")

    if bucket_name == "target_fiscal_year_not_detected":
        return (
            "needs_operator_review",
            "Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence.",
        )

    if bucket_name == "site_entry_fetch_identity":
        if reason.startswith(("no_candidates_found", "discovery_error")):
            return (
                "needs_operator_review",
                "No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.",
            )
        if reason.startswith("pdf_school_mismatch"):
            return (
                "needs_operator_review",
                "Target-like document has school-identity risk; confirm it belongs to the same institution.",
            )
        return ("needs_operator_review", "Inspect SiteEntry, fetch, and school-identity evidence before deciding.")

    return ("", "No safe suggestion; review official evidence.")


def build_false_reject_audit_packet(
    archive: Path,
    *,
    sample_size: int = 50,
    required_yield_pct: float = 60.0,
) -> dict[str, Any]:
    """Return a deterministic false-reject audit packet for a Stage 6 evidence ZIP."""

    verification = verify_stage6_evidence_bundle(archive, required_labels=REQUIRED_LABELS)
    errors: list[str] = []
    source_files: dict[str, str] = {}

    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            last_run_name = _entry_by_suffix(names, "data/output/last_run.json")
            rejections_name = _entry_by_suffix(names, "-discovery-rejections.jsonl")
            rca_name = _entry_by_suffix(names, "-discovery-rca-batch-plan.json")
            source_files = {
                "last_run": last_run_name,
                "discovery_evidence": rejections_name,
                "discovery_rca": rca_name,
            }
            last_run = _load_json_entry(zf, last_run_name)
            _load_json_entry(zf, rca_name)
            rejection_rows = _load_jsonl_entry(zf, rejections_name)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return {
            "ok": False,
            "basis": "stage6_false_reject_audit_packet",
            "generated_at": datetime.now(UTC).isoformat(),
            "archive": str(archive),
            "verification": verification,
            "source_files": source_files,
            "errors": errors,
        }

    denominator = _as_int(last_run.get("target_pdf_auto_denominator_count"))
    excel_ready_count = _as_int(last_run.get("target_pdf_excel_ready_acquired_count"))
    excel_ready_yield_pct = _as_float(last_run.get("target_pdf_excel_ready_yield_pct"))
    if excel_ready_yield_pct is None:
        excel_ready_yield_pct = _rate(excel_ready_count, denominator)
    ship_gate_status = str(last_run.get("ship_gate_status") or "")
    ship_gate_met = (
        excel_ready_yield_pct is not None
        and excel_ready_yield_pct >= required_yield_pct
        and ship_gate_status not in {"below_gate", "failed", "fail"}
    )

    reason_counts = Counter(_row_reason(row) for row in rejection_rows)
    audit_buckets: list[dict[str, Any]] = []
    for bucket_def in AUDIT_BUCKETS:
        prefixes = tuple(str(prefix) for prefix in bucket_def["reason_prefixes"])
        bucket_rows = [row for row in rejection_rows if _matches_reason(row, prefixes)]
        sampled = _sample_rows(bucket_rows, sample_size)
        audit_buckets.append(
            {
                "bucket": bucket_def["bucket"],
                "reason_prefixes": list(prefixes),
                "total_rows": len(bucket_rows),
                "unique_candidate_rows": len(_dedupe_rows(bucket_rows)),
                "sample_limit": sample_size,
                "sampled_rows": len(sampled),
                "review_question": bucket_def["review_question"],
                "false_reject_signal": bucket_def["false_reject_signal"],
                "rows": [_project_row(str(bucket_def["bucket"]), row) for row in sampled],
            }
        )

    return {
        "ok": verification.get("ok") is True and not errors,
        "basis": "stage6_false_reject_audit_packet",
        "generated_at": datetime.now(UTC).isoformat(),
        "archive": str(archive),
        "verification": verification,
        "source_files": source_files,
        "strict_yield": {
            "target_fiscal_year": last_run.get("current_fy"),
            "denominator": denominator,
            "excel_ready_acquired_count": excel_ready_count,
            "excel_ready_yield_pct": excel_ready_yield_pct,
            "required_yield_pct": required_yield_pct,
            "ship_gate_status": ship_gate_status,
            "ship_gate_met": ship_gate_met,
            "release_forecast": "READY" if ship_gate_met else "NOT_READY",
        },
        "model_failure_framing": {
            "generic_model_failure_supported": False,
            "reason": (
                "Below-gate strict yield requires bucket-level false-reject audit; "
                "it is not by itself evidence of a generic algorithm/model failure."
            ),
        },
        "rejection_reason_counts": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "audit_buckets": audit_buckets,
        "errors": errors,
    }


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(packet: dict[str, Any]) -> str:
    strict_yield = packet.get("strict_yield", {})
    model_framing = packet.get("model_failure_framing", {})
    lines = [
        "# Stage 6 False-Reject Audit Packet",
        "",
        f"Archive: `{packet.get('archive', '')}`",
        "",
        f"Status: `{'READY_TO_AUDIT' if packet.get('ok') is True else 'INVALID_OR_INCOMPLETE_EVIDENCE'}`",
        f"Release Forecast: `{strict_yield.get('release_forecast', 'NOT_READY')}`",
        (
            "Strict Excel-ready yield: "
            f"`{strict_yield.get('excel_ready_acquired_count')}/{strict_yield.get('denominator')}` "
            f"(`{strict_yield.get('excel_ready_yield_pct')}%`), "
            f"required `{strict_yield.get('required_yield_pct')}%`."
        ),
        "",
        "This packet does not relax FY2026/R8 evidence rules and does not allow rejected rows into Excel.",
        f"Generic algorithm/model failure supported: `{model_framing.get('generic_model_failure_supported')}`.",
        f"Reason: {model_framing.get('reason', '')}",
        "",
        "## Audit Buckets",
        "",
        "| Bucket | Rows | Unique rows | Sampled | Review question |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for bucket in packet.get("audit_buckets", []):
        lines.append(
            "| "
            f"`{_md_cell(bucket.get('bucket', ''))}` | "
            f"{_md_cell(bucket.get('total_rows', 0))} | "
            f"{_md_cell(bucket.get('unique_candidate_rows', 0))} | "
            f"{_md_cell(bucket.get('sampled_rows', 0))} | "
            f"{_md_cell(bucket.get('review_question', ''))} |"
        )

    lines.extend(
        [
            "",
            "## Review Instructions",
            "",
            "- Mark a row `false_reject` only when official evidence proves it should have been accepted "
            "for FY2026/R8.",
            "- Mark a row `correct_reject` when it is old-year, non-target, unknown-year, mismatched, or unsupported.",
            "- Mark a row `needs_operator_review` when evidence exists but requires human confirmation.",
            "- Do not count old-year PDFs, unknown-year PDFs, non-target PDFs, or school mismatches as "
            "FY2026/R8 success.",
            "",
            "## Sample Rows",
        ]
    )
    for bucket in packet.get("audit_buckets", []):
        lines.extend(
            [
                "",
                f"### `{bucket.get('bucket', '')}`",
                "",
                f"False-reject signal: {bucket.get('false_reject_signal', '')}",
                "",
                "| Audit row ID | School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |",
                "| --- | ---: | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in bucket.get("rows", []):
            lines.append(
                "| "
                f"`{_md_cell(row.get('audit_row_id', ''))}` | "
                f"{_md_cell(row.get('school_id', ''))} | "
                f"`{_md_cell(row.get('reason', ''))}` | "
                f"`{_md_cell(row.get('pdf_type', ''))}` | "
                f"{_md_cell(row.get('year_evidence') or row.get('trusted_year_evidence') or '')} | "
                f"{_md_cell(row.get('anchor_text', ''))} | "
                f"`{_md_cell(row.get('page_url', ''))}` | "
                f"`{_md_cell(row.get('pdf_url', ''))}` |"
            )

    if packet.get("errors"):
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{_md_cell(error)}`" for error in packet["errors"])
    return "\n".join(lines) + "\n"


REVIEW_CSV_COLUMNS = (
    "audit_row_id",
    "bucket",
    "decision",
    "reviewer",
    "reviewed_at",
    "school_id",
    "reason",
    "pdf_type",
    "detected_fiscal_year",
    "year_evidence",
    "trusted_year_evidence",
    "discovery_method",
    "anchor_text",
    "page_url",
    "pdf_url",
    "suggested_decision",
    "suggested_decision_basis",
    "review_question",
    "false_reject_signal",
    "notes",
)
REVIEW_CONTEXT_COLUMNS = tuple(column for column in REVIEW_CSV_COLUMNS if column not in REVIEW_MUTABLE_COLUMNS)
OPTIONAL_REVIEW_CONTEXT_COLUMNS = {"suggested_decision", "suggested_decision_basis"}


def _iter_review_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    target_fiscal_year = packet.get("strict_yield", {}).get("target_fiscal_year")
    if not isinstance(target_fiscal_year, int):
        target_fiscal_year = None
    for bucket in packet.get("audit_buckets", []):
        bucket_name = str(bucket.get("bucket") or "")
        review_question = str(bucket.get("review_question") or "")
        false_reject_signal = str(bucket.get("false_reject_signal") or "")
        for row in bucket.get("rows", []):
            suggested_decision, suggested_decision_basis = _suggested_triage_decision(
                bucket_name=bucket_name,
                row=row,
                target_fiscal_year=target_fiscal_year,
            )
            rows.append(
                {
                    "audit_row_id": row.get("audit_row_id") or "",
                    "bucket": bucket_name,
                    "decision": "",
                    "reviewer": "",
                    "reviewed_at": "",
                    "school_id": row.get("school_id") or "",
                    "reason": row.get("reason") or "",
                    "pdf_type": row.get("pdf_type") or "",
                    "detected_fiscal_year": row.get("detected_fiscal_year") or "",
                    "year_evidence": row.get("year_evidence") or "",
                    "trusted_year_evidence": row.get("trusted_year_evidence") or "",
                    "discovery_method": row.get("discovery_method") or "",
                    "anchor_text": row.get("anchor_text") or "",
                    "page_url": row.get("page_url") or "",
                    "pdf_url": row.get("pdf_url") or "",
                    "suggested_decision": suggested_decision,
                    "suggested_decision_basis": suggested_decision_basis,
                    "review_question": review_question,
                    "false_reject_signal": false_reject_signal,
                    "notes": "",
                }
            )
    return rows


def render_review_csv(packet: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REVIEW_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_iter_review_rows(packet))
    return output.getvalue()


def render_review_summary(packet: dict[str, Any]) -> str:
    """Return a read-only owner triage summary for the review worksheet."""

    strict_yield = packet.get("strict_yield", {})
    review_rows = _iter_review_rows(packet)
    decision_counts = Counter(str(row.get("suggested_decision") or "blank") for row in review_rows)
    bucket_counts: dict[str, Counter[str]] = {}
    for row in review_rows:
        bucket = str(row.get("bucket") or "")
        suggested_decision = str(row.get("suggested_decision") or "blank")
        bucket_counts.setdefault(bucket, Counter())[suggested_decision] += 1

    priority_rows = [
        row for row in review_rows if str(row.get("suggested_decision") or "") != "correct_reject"
    ]

    lines = [
        "# False-Reject Review Summary",
        "",
        f"Archive: `{packet.get('archive', '')}`",
        f"Release Forecast: `{strict_yield.get('release_forecast', 'NOT_READY')}`",
        (
            "Strict Excel-ready yield: "
            f"`{strict_yield.get('excel_ready_acquired_count')}/{strict_yield.get('denominator')}` "
            f"(`{strict_yield.get('excel_ready_yield_pct')}%`), "
            f"required `{strict_yield.get('required_yield_pct')}%`."
        ),
        "",
        "This is read-only triage guidance. It does not fill the worksheet, approve rejected rows, "
        "or allow any row into Excel.",
        "",
        "## Suggested Decision Counts",
        "",
        "| Suggested decision | Rows |",
        "| --- | ---: |",
    ]
    for decision, count in sorted(decision_counts.items()):
        lines.append(f"| `{_md_cell(decision)}` | {count} |")

    lines.extend(
        [
            "",
            "## Suggested Decisions By Bucket",
            "",
            "| Bucket | correct_reject | needs_operator_review | false_reject | blank |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for bucket, counter in sorted(bucket_counts.items()):
        lines.append(
            "| "
            f"`{_md_cell(bucket)}` | "
            f"{counter.get('correct_reject', 0)} | "
            f"{counter.get('needs_operator_review', 0)} | "
            f"{counter.get('false_reject', 0)} | "
            f"{counter.get('blank', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Priority Review Rows",
            "",
            "Rows listed here are not suggested as obvious `correct_reject`. They still require owner/operator "
            "decision before they can support any RCA claim.",
            "",
            "| Audit row ID | Bucket | Suggested decision | School ID | Reason | Review focus |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in priority_rows:
        focus = row.get("suggested_decision_basis") or row.get("review_question") or ""
        lines.append(
            "| "
            f"`{_md_cell(row.get('audit_row_id', ''))}` | "
            f"`{_md_cell(row.get('bucket', ''))}` | "
            f"`{_md_cell(row.get('suggested_decision') or 'blank')}` | "
            f"{_md_cell(row.get('school_id', ''))} | "
            f"`{_md_cell(row.get('reason', ''))}` | "
            f"{_md_cell(focus)} |"
        )

    lines.extend(
        [
            "",
            "## Review Rules",
            "",
            "- Fill only `decision`, `reviewer`, `reviewed_at`, and `notes` in the CSV worksheet.",
            "- Mark `false_reject` only with official FY2026/R8 evidence.",
            "- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.",
            "- Release remains blocked until the returned worksheet validates with `review_status=complete` "
            "and `context_mismatch_count=0`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _review_decision_counts_json(counter: Counter[str]) -> dict[str, int]:
    return {key or "blank": count for key, count in sorted(counter.items())}


def _defect_framing(review_status: str, decision_counts: Counter[str]) -> dict[str, Any]:
    false_reject_rows = decision_counts.get("false_reject", 0)
    needs_operator_review_rows = decision_counts.get("needs_operator_review", 0)
    correct_reject_rows = decision_counts.get("correct_reject", 0)

    if review_status != "complete":
        status = "pending_review"
        reason = (
            "Review decisions are incomplete; below-gate yield must not be labeled as an "
            "algorithm/model defect yet."
        )
    elif false_reject_rows:
        status = "specific_false_rejects_found"
        reason = (
            "Completed review found false-reject rows, supporting a specific algorithm or "
            "rule defect for those rows. This still does not prove a generic model failure."
        )
    elif needs_operator_review_rows:
        status = "inconclusive_operator_review"
        reason = (
            "Completed review still has rows requiring operator judgment; treat the defect "
            "claim as unresolved until those rows are adjudicated."
        )
    else:
        status = "not_supported"
        reason = (
            "Completed review found no false-reject rows; below-gate yield remains better "
            "explained by correct strict rejects unless new evidence appears."
        )

    return {
        "generic_model_failure_supported": False,
        "specific_algorithm_or_rule_defect_supported": bool(false_reject_rows),
        "status": status,
        "false_reject_rows": false_reject_rows,
        "needs_operator_review_rows": needs_operator_review_rows,
        "correct_reject_rows": correct_reject_rows,
        "reason": reason,
    }


def _empty_review_validation(
    packet: dict[str, Any],
    expected_rows: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "ok": False,
        "basis": "false_reject_review_decision_validation",
        "release_forecast": packet.get("strict_yield", {}).get("release_forecast", "NOT_READY"),
        "review_status": "invalid",
        "required_decisions": list(VALID_REVIEW_DECISIONS[1:]),
        "expected_rows": len(expected_rows),
        "submitted_rows": 0,
        "completed_decisions": 0,
        "blank_decisions": len(expected_rows),
        "decision_counts": {},
        "bucket_decision_counts": {},
        "defect_framing": _defect_framing("invalid", Counter()),
        "context_mismatch_count": 0,
        "errors": errors,
    }


def _is_review_timestamp(value: str) -> bool:
    if not value or "T" not in value:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def validate_review_csv(
    packet: dict[str, Any],
    csv_text: str,
    *,
    require_decisions: bool = False,
) -> dict[str, Any]:
    expected_rows = _iter_review_rows(packet)
    expected_by_id = {str(row["audit_row_id"]): row for row in expected_rows}
    expected_ids = {str(row["audit_row_id"]) for row in expected_rows}
    errors: list[str] = []
    decision_counts: Counter[str] = Counter()
    bucket_decision_counts: dict[str, Counter[str]] = {}
    seen_ids: set[str] = set()
    context_mismatch_count = 0

    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = set(reader.fieldnames or [])
    required_columns = {"audit_row_id", "decision"}
    missing_columns = sorted(required_columns - fieldnames)
    if missing_columns:
        errors.append(f"review CSV is missing required columns: {', '.join(missing_columns)}")
        return _empty_review_validation(packet, expected_rows, errors)

    for line_number, row in enumerate(reader, start=2):
        audit_row_id = str(row.get("audit_row_id") or "").strip()
        decision = str(row.get("decision") or "").strip()
        reviewer = str(row.get("reviewer") or "").strip()
        reviewed_at = str(row.get("reviewed_at") or "").strip()
        notes = str(row.get("notes") or "").strip()
        if not audit_row_id:
            errors.append(f"line {line_number}: audit_row_id is blank")
            continue
        if audit_row_id in seen_ids:
            errors.append(f"line {line_number}: duplicate audit_row_id {audit_row_id}")
        seen_ids.add(audit_row_id)
        if audit_row_id not in expected_ids:
            errors.append(f"line {line_number}: unknown audit_row_id {audit_row_id}")
            expected_row = None
        else:
            expected_row = expected_by_id[audit_row_id]
            for column in REVIEW_CONTEXT_COLUMNS:
                if column in OPTIONAL_REVIEW_CONTEXT_COLUMNS and column not in fieldnames:
                    continue
                expected_value = str(expected_row.get(column) or "")
                actual_value = str(row.get(column) or "")
                if actual_value != expected_value:
                    context_mismatch_count += 1
                    errors.append(
                        f"line {line_number}: {column} changed for audit_row_id {audit_row_id}; "
                        f"expected {expected_value!r}, got {actual_value!r}"
                    )
        if decision not in VALID_REVIEW_DECISIONS:
            errors.append(
                f"line {line_number}: invalid decision {decision!r}; "
                f"expected one of {', '.join(repr(item) for item in VALID_REVIEW_DECISIONS[1:])}"
            )
        if require_decisions and decision == "":
            errors.append(f"line {line_number}: decision is required")
        if decision:
            if not reviewer:
                errors.append(f"line {line_number}: reviewer is required when decision is set")
            if not _is_review_timestamp(reviewed_at):
                errors.append(f"line {line_number}: reviewed_at must be an ISO timestamp when decision is set")
            if decision in DECISIONS_REQUIRING_NOTES and not notes:
                errors.append(f"line {line_number}: notes are required for decision {decision!r}")
        decision_counts[decision] += 1
        bucket_name = str(expected_row.get("bucket") if expected_row is not None else row.get("bucket") or "")
        bucket_decision_counts.setdefault(bucket_name, Counter())[decision] += 1

    missing_ids = sorted(expected_ids - seen_ids)
    if missing_ids:
        preview = ", ".join(missing_ids[:5])
        suffix = "" if len(missing_ids) <= 5 else f", ... ({len(missing_ids)} total)"
        errors.append(f"review CSV is missing expected audit_row_id values: {preview}{suffix}")

    blank_decisions = decision_counts.get("", 0)
    review_status = "invalid" if errors else ("complete" if blank_decisions == 0 else "incomplete")
    return {
        "ok": not errors,
        "basis": "false_reject_review_decision_validation",
        "release_forecast": packet.get("strict_yield", {}).get("release_forecast", "NOT_READY"),
        "review_status": review_status,
        "required_decisions": list(VALID_REVIEW_DECISIONS[1:]),
        "expected_rows": len(expected_rows),
        "submitted_rows": len(seen_ids),
        "completed_decisions": sum(count for decision, count in decision_counts.items() if decision),
        "blank_decisions": blank_decisions,
        "decision_counts": _review_decision_counts_json(decision_counts),
        "bucket_decision_counts": {
            bucket: _review_decision_counts_json(counter) for bucket, counter in sorted(bucket_decision_counts.items())
        },
        "defect_framing": _defect_framing(review_status, decision_counts),
        "context_mismatch_count": context_mismatch_count,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to logs/stage6-evidence-*.zip.")
    parser.add_argument("--required-yield-pct", type=float, default=60.0)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--format", choices=("markdown", "json", "csv", "review-summary"), default="markdown")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    parser.add_argument("--validate-review-csv", type=Path, help="Validate a completed review CSV for this packet.")
    parser.add_argument("--require-decisions", action="store_true", help="Fail validation when any decision is blank.")
    parser.add_argument("--output", type=Path, help="Write the audit packet to this path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    output_format = "json" if args.json else args.format
    packet = build_false_reject_audit_packet(
        args.archive,
        sample_size=args.sample_size,
        required_yield_pct=args.required_yield_pct,
    )

    if args.validate_review_csv is not None:
        validation = validate_review_csv(
            packet,
            args.validate_review_csv.read_text(encoding="utf-8-sig"),
            require_decisions=args.require_decisions,
        )
        rendered = json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ok = packet.get("ok") is True and validation.get("ok") is True
    elif output_format == "json":
        rendered = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ok = packet.get("ok") is True
    elif output_format == "csv":
        rendered = render_review_csv(packet)
        ok = packet.get("ok") is True
    elif output_format == "review-summary":
        rendered = render_review_summary(packet)
        ok = packet.get("ok") is True
    else:
        rendered = render_markdown(packet)
        ok = packet.get("ok") is True

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
