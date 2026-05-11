"""Build single-school RCA input packets for Codex-assisted discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RCA_OUTCOME_REQUIRED_FIELDS = (
    "school_id",
    "target_fiscal_year",
    "layer",
    "outcome",
    "source_page_url",
    "candidate_pdf_url",
    "anchor_text",
    "fiscal_year_evidence",
    "target_form_evidence",
    "negative_evidence",
    "checked_paths",
    "search_queries_used",
    "operator_action",
    "gold_set_entry_recommended",
    "candidate_rule",
    "anti_pattern",
    "confidence",
)

RCA_OUTCOME_ALLOWED_LAYERS = {
    "layer_0_official_index_handoff",
    "layer_1_pdf_discovery",
    "layer_2_pdf_body_or_ocr",
    "layer_3_operator_or_search_fallback",
    "site_infrastructure_failure",
}

RCA_OUTCOME_ALLOWED_OUTCOMES = {
    "accepted_target_pdf",
    "publication_lag_latest_public",
    "needs_operator_review",
    "no_target_candidate_found",
    "site_fetch_error",
}

RCA_OUTCOME_ALLOWED_OPERATOR_ACTIONS = {
    "none",
    "review_pdf",
    "manual_url_entry",
    "wait_for_publication",
    "site_access_followup",
}

RCA_OUTCOME_STRING_FIELDS = {
    "layer",
    "outcome",
    "source_page_url",
    "candidate_pdf_url",
    "anchor_text",
    "fiscal_year_evidence",
    "target_form_evidence",
    "negative_evidence",
    "operator_action",
    "candidate_rule",
    "anti_pattern",
    "confidence",
}


def build_single_school_rca_packet(
    session: Any,
    *,
    school_id: int,
    target_fiscal_year: int,
    evidence_log: Path | None = None,
    known_operator_note: str = "",
) -> dict[str, Any]:
    """Build the runbook input packet for one school.

    This is read-only. It collects the currently registered school URLs and,
    when an evidence JSONL is supplied, the latest school-level discovery
    bucket. The packet is meant to be pasted into the Codex single-school RCA
    prompt, not to mutate crawler state.
    """
    from eidp.db.models import School, SchoolSite
    from eidp.scraper.discovery_evidence_summary import (
        load_pdf_discovery_evidence,
        summarize_pdf_discovery_evidence,
    )

    school = session.get(School, school_id)
    if school is None:
        raise ValueError(f"school_id={school_id} not found")

    sites = list(
        session.query(SchoolSite)
        .filter(SchoolSite.school_id == school_id)
        .order_by(SchoolSite.id.asc())
        .all()
    )
    sites.sort(key=lambda site: (0 if site.discovery_method == "prefecture_aggregator" else 1, int(site.id or 0)))
    registered_sites = [
        {
            "url": str(site.url or ""),
            "url_type": str(site.url_type or ""),
            "discovery_method": str(site.discovery_method or ""),
            "confidence": float(site.confidence) if site.confidence is not None else None,
            "verified": bool(site.verified),
        }
        for site in sites
    ]

    official_index_url = ""
    for site in sites:
        if site.discovery_method == "prefecture_aggregator":
            official_index_url = str(site.url or "")
            break

    latest_bucket = "unknown"
    latest_evidence_rows: list[dict[str, Any]] = []
    latest_evidence_top_reasons: list[list[Any]] = []
    if evidence_log is not None:
        rows = [
            row
            for row in load_pdf_discovery_evidence(evidence_log)
            if _int_or_none(row.get("school_id")) == school_id
        ]
        school_summary = summarize_pdf_discovery_evidence(rows).school_summaries
        latest_bucket = school_summary[0].bucket if school_summary else "no_evidence"
        latest_evidence_top_reasons = [
            [reason, count]
            for reason, count in (school_summary[0].top_reasons if school_summary else [])
        ]
        latest_evidence_rows = [_compact_evidence_row(row) for row in rows[:10]]

    return {
        "school_id": int(school.id),
        "school_name": str(school.school_name or ""),
        "prefecture": str(school.prefecture or ""),
        "target_fiscal_year": int(target_fiscal_year),
        "official_index_url": official_index_url,
        "registered_sites": registered_sites,
        "latest_bucket": latest_bucket,
        "latest_evidence_rows_path": str(evidence_log) if evidence_log is not None else "",
        "latest_evidence_row_count": len(rows) if evidence_log is not None else 0,
        "latest_evidence_top_reasons": latest_evidence_top_reasons,
        "latest_evidence_rows": latest_evidence_rows,
        "known_operator_note": known_operator_note,
    }


def build_single_school_rca_batch_plan(
    session: Any,
    *,
    evidence_log: Path,
    target_fiscal_year: int,
    prefecture: str = "",
    discovery_method: str = "",
    limit: int = 10,
    known_operator_note: str = "",
    include_prompts: bool = False,
) -> dict[str, Any]:
    """Build a prioritized list of single-school RCA packets."""
    from eidp.scraper.discovery_evidence_summary import (
        load_pdf_discovery_evidence,
        load_pdf_discovery_site_scope,
        summarize_pdf_discovery_evidence,
    )

    site_scope = None
    if prefecture or discovery_method:
        site_scope = load_pdf_discovery_site_scope(
            session,
            prefecture=prefecture,
            discovery_method=discovery_method,
        )
    rows = load_pdf_discovery_evidence(evidence_log)
    summary = summarize_pdf_discovery_evidence(rows, site_scope=site_scope)
    candidate_summaries = [
        school_summary
        for school_summary in summary.school_summaries
        if school_summary.bucket != "accepted_target_pdf"
    ]
    candidate_summaries.sort(
        key=lambda school_summary: (
            _bucket_priority(school_summary.bucket),
            -school_summary.candidate_count,
            school_summary.school_id,
        )
    )

    items: list[dict[str, Any]] = []
    for school_summary in candidate_summaries[:max(limit, 0)]:
        packet = build_single_school_rca_packet(
            session,
            school_id=school_summary.school_id,
            target_fiscal_year=target_fiscal_year,
            evidence_log=evidence_log,
            known_operator_note=known_operator_note,
        )
        item = {
            "priority": _bucket_priority(school_summary.bucket),
            "bucket": school_summary.bucket,
            "candidate_count": school_summary.candidate_count,
            "packet": packet,
        }
        if include_prompts:
            item["prompt"] = render_single_school_rca_prompt(packet)
        items.append(item)

    return {
        "target_fiscal_year": int(target_fiscal_year),
        "evidence_log": str(evidence_log),
        "prefecture": prefecture,
        "discovery_method": discovery_method,
        "total_candidates": len(candidate_summaries),
        "items": items,
    }


def render_single_school_rca_batch_plan(plan: dict[str, Any]) -> str:
    """Render a deterministic JSON batch plan."""
    return json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)


def render_single_school_rca_prompt(packet: dict[str, Any]) -> str:
    """Render a copy-paste Codex prompt for one RCA packet."""
    packet_json = render_single_school_rca_packet(packet)
    return f"""Investigate this EIDP school as a single-school RCA packet. Do not run broad SERP crawling.

Input:
{packet_json}

Tasks:
1. Classify the failure layer before searching.
2. Check official-index and registered SchoolSite URLs first.
3. Check bounded same-domain disclosure/public-info paths before named-school search.
4. Inspect candidate PDF body/OCR evidence before accepting target FY.
5. Return exactly one Required Output Block JSON object.
6. If this should enter data/discovery-gold-set, draft the entry fields and explain the reusable rule and anti-pattern.
"""


def render_single_school_rca_packet(packet: dict[str, Any]) -> str:
    """Render a deterministic JSON packet."""
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def validate_single_school_rca_outcome(payload: dict[str, Any]) -> list[str]:
    """Validate the Required Output Block from the manual RCA runbook.

    This intentionally checks only shape, allowed labels, and basic types. It
    does not prove the web investigation itself; that evidence must still be
    reviewed before promoting a gold-set entry or crawler rule.
    """
    errors: list[str] = []
    for field in RCA_OUTCOME_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    if "school_id" in payload and not isinstance(payload["school_id"], int):
        errors.append("school_id must be an integer")
    if "target_fiscal_year" in payload and not isinstance(payload["target_fiscal_year"], int):
        errors.append("target_fiscal_year must be an integer")
    if "gold_set_entry_recommended" in payload and not isinstance(payload["gold_set_entry_recommended"], bool):
        errors.append("gold_set_entry_recommended must be a boolean")

    for field in RCA_OUTCOME_STRING_FIELDS:
        if field in payload and not isinstance(payload[field], str):
            errors.append(f"{field} must be a string")

    if "checked_paths" in payload and not _is_string_list(payload["checked_paths"]):
        errors.append("checked_paths must be a list")
    if "search_queries_used" in payload and not _is_string_list(payload["search_queries_used"]):
        errors.append("search_queries_used must be a list")

    layer = payload.get("layer")
    if isinstance(layer, str) and layer not in RCA_OUTCOME_ALLOWED_LAYERS:
        errors.append(f"invalid layer: {layer}")
    outcome = payload.get("outcome")
    if isinstance(outcome, str) and outcome not in RCA_OUTCOME_ALLOWED_OUTCOMES:
        errors.append(f"invalid outcome: {outcome}")
    operator_action = payload.get("operator_action")
    if isinstance(operator_action, str) and operator_action not in RCA_OUTCOME_ALLOWED_OPERATOR_ACTIONS:
        errors.append(f"invalid operator_action: {operator_action}")

    return errors


def validate_rca_outcome_batch_plan_coverage(
    outcomes: list[dict[str, Any]],
    batch_plan: dict[str, Any],
) -> list[str]:
    """Validate that RCA outcomes exactly cover a generated batch plan."""
    items = batch_plan.get("items")
    if not isinstance(items, list):
        return ["batch plan items must be a list"]

    errors: list[str] = []
    expected_counts: dict[tuple[int, int], int] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"batch plan item {index} must be an object")
            continue
        packet = item.get("packet")
        if not isinstance(packet, dict):
            errors.append(f"batch plan item {index} packet must be an object")
            continue
        key = _rca_key(packet)
        if key is None:
            errors.append(f"batch plan item {index} packet must contain integer school_id and target_fiscal_year")
            continue
        expected_counts[key] = expected_counts.get(key, 0) + 1

    actual_counts: dict[tuple[int, int], int] = {}
    for outcome in outcomes:
        key = _rca_key(outcome)
        if key is None:
            continue
        actual_counts[key] = actual_counts.get(key, 0) + 1

    for key, count in sorted(expected_counts.items()):
        actual_count = actual_counts.get(key, 0)
        if actual_count == 0:
            errors.append(_format_batch_coverage_error("missing batch outcome", key))
        elif actual_count > count:
            errors.append(_format_batch_coverage_error("duplicate outcome", key))
    for key in sorted(actual_counts):
        if key not in expected_counts:
            errors.append(_format_batch_coverage_error("unexpected outcome", key))

    return errors


def _bucket_priority(bucket: str) -> int:
    return {
        "target_form_without_year_evidence": 10,
        "non_target_candidates_only": 20,
        "no_pdf_candidates": 30,
        "tls_certificate_verify_failed": 40,
        "site_fetch_error_only": 50,
        "no_evidence": 60,
        "publication_lag_or_old_target_pdf": 90,
    }.get(bucket, 80)


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _compact_evidence_row(row: dict[str, Any]) -> dict[str, Any]:
    extra = row.get("extra")
    return {
        "reason": str(row.get("reason") or ""),
        "pdf_type": str(row.get("pdf_type") or ""),
        "pdf_url": str(row.get("pdf_url") or ""),
        "page_url": str(row.get("page_url") or ""),
        "anchor_text": str(row.get("anchor_text") or ""),
        "pattern_type": str(row.get("pattern_type") or ""),
        "score": _float_or_none(row.get("score")),
        "extra": extra if isinstance(extra, dict) else {},
    }


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _rca_key(payload: dict[str, Any]) -> tuple[int, int] | None:
    school_id = payload.get("school_id")
    target_fiscal_year = payload.get("target_fiscal_year")
    if not isinstance(school_id, int) or not isinstance(target_fiscal_year, int):
        return None
    return (school_id, target_fiscal_year)


def _format_batch_coverage_error(prefix: str, key: tuple[int, int]) -> str:
    school_id, target_fiscal_year = key
    return f"{prefix}: school_id={school_id} target_fiscal_year={target_fiscal_year}"
