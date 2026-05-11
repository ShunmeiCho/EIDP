"""Build single-school RCA input packets for Codex-assisted discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
