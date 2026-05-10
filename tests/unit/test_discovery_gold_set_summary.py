from __future__ import annotations

import json
from pathlib import Path

from eidp.scraper.discovery_gold_set import (
    load_discovery_gold_entries,
    render_discovery_gold_summary,
    summarize_discovery_gold_entries,
)

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"


def test_summarize_discovery_gold_entries_tracks_release_relevant_buckets() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)

    summary = summarize_discovery_gold_entries(entries)

    assert summary.total_entries == 10
    assert summary.target_fiscal_year_counts == {2025: 2, 2026: 8}
    assert summary.outcome_counts == {
        "accepted_target_pdf": 4,
        "needs_operator_review": 4,
        "publication_lag_latest_public": 2,
    }
    assert summary.strict_target_year_successes == 4
    assert summary.operator_review_entries == 4
    assert summary.publication_lag_entries == 2


def test_render_discovery_gold_summary_outputs_json_safe_payload() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    payload = render_discovery_gold_summary(summarize_discovery_gold_entries(entries))

    decoded = json.loads(payload)

    assert decoded["total_entries"] == 10
    assert decoded["outcome_counts"]["needs_operator_review"] == 4
    assert decoded["strict_target_year_successes"] == 4
    assert "dense_information_page" in decoded["site_families"]
