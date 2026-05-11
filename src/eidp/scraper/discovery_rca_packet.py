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
    if evidence_log is not None:
        rows = [
            row
            for row in load_pdf_discovery_evidence(evidence_log)
            if _int_or_none(row.get("school_id")) == school_id
        ]
        school_summary = summarize_pdf_discovery_evidence(rows).school_summaries
        latest_bucket = school_summary[0].bucket if school_summary else "no_evidence"

    return {
        "school_id": int(school.id),
        "school_name": str(school.school_name or ""),
        "prefecture": str(school.prefecture or ""),
        "target_fiscal_year": int(target_fiscal_year),
        "official_index_url": official_index_url,
        "registered_sites": registered_sites,
        "latest_bucket": latest_bucket,
        "latest_evidence_rows_path": str(evidence_log) if evidence_log is not None else "",
        "known_operator_note": known_operator_note,
    }


def render_single_school_rca_packet(packet: dict[str, Any]) -> str:
    """Render a deterministic JSON packet."""
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None
