from __future__ import annotations

import json
from pathlib import Path

from eidp.scraper.discovery_gold_set import (
    build_discovery_gold_run_plan,
    load_discovery_gold_entries,
    render_discovery_gold_run_plan,
    render_discovery_gold_summary,
    summarize_discovery_gold_entries,
)

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"


def test_summarize_discovery_gold_entries_tracks_release_relevant_buckets() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)

    summary = summarize_discovery_gold_entries(entries)

    assert summary.total_entries == 12
    assert summary.target_fiscal_year_counts == {2025: 2, 2026: 10}
    assert summary.outcome_counts == {
        "accepted_target_pdf": 4,
        "needs_operator_review": 5,
        "no_target_candidate_found": 1,
        "publication_lag_latest_public": 2,
    }
    assert summary.strict_target_year_successes == 4
    assert summary.operator_review_entries == 5
    assert summary.publication_lag_entries == 2


def test_render_discovery_gold_summary_outputs_json_safe_payload() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    payload = render_discovery_gold_summary(summarize_discovery_gold_entries(entries))

    decoded = json.loads(payload)

    assert decoded["total_entries"] == 12
    assert decoded["outcome_counts"]["needs_operator_review"] == 5
    assert decoded["outcome_counts"]["no_target_candidate_found"] == 1
    assert decoded["strict_target_year_successes"] == 4
    assert "dense_information_page" in decoded["site_families"]


def test_build_discovery_gold_run_plan_emits_bounded_pdf_discovery_inputs() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)

    plan = build_discovery_gold_run_plan(entries)

    assert len(plan) == 12
    ecole = next(item for item in plan if item.entry_id == "ecole-matsue-nutrition-2026")
    assert ecole.school_id == 1721
    assert ecole.site_url == "https://www.ecole-cpb.com/school-support"
    assert ecole.target_fiscal_year == 2026
    assert ecole.expected_outcome == "accepted_target_pdf"
    assert ecole.expected_pdf_url == "https://www.ecole-cpb.com/files/school_support_R8.pdf"


def test_render_discovery_gold_run_plan_outputs_json_array() -> None:
    payload = render_discovery_gold_run_plan(build_discovery_gold_run_plan(load_discovery_gold_entries(GOLD_SET_DIR)))

    decoded = json.loads(payload)

    assert len(decoded) == 12
    assert decoded[0]["entry_id"] == "ast-kansai-ika-review-2026"
    assert decoded[0]["site_url"] == "https://www.kmc.ast.ac.jp/jyouhoukokai/"
