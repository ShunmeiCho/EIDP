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

    assert summary.total_entries == 37
    assert summary.target_fiscal_year_counts == {2025: 2, 2026: 35}
    assert summary.outcome_counts == {
        "accepted_target_pdf": 9,
        "needs_operator_review": 15,
        "no_target_candidate_found": 1,
        "publication_lag_latest_public": 11,
        "site_fetch_error": 1,
    }
    assert summary.strict_target_year_successes == 9
    assert summary.operator_review_entries == 15
    assert summary.publication_lag_entries == 11
    assert summary.pattern_source_counts == {
        "direct": 5,
        "embed": 1,
        "wordpress": 5,
        "wordpress_download_manager": 1,
    }
    assert "empty_stale_anchor_before_visible_current_year_anchor" in summary.site_families
    assert "multi_year_support_pdf_list_current_year_anchor" in summary.site_families
    assert "news_definition_list_support_year_statement" in summary.site_families
    assert "school_support_page_with_adjacent_target_year_statement" in summary.site_families
    assert "table_header_confirmation_application" in summary.site_families


def test_render_discovery_gold_summary_outputs_json_safe_payload() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    payload = render_discovery_gold_summary(summarize_discovery_gold_entries(entries))

    decoded = json.loads(payload)

    assert decoded["total_entries"] == 37
    assert decoded["outcome_counts"]["needs_operator_review"] == 15
    assert decoded["outcome_counts"]["no_target_candidate_found"] == 1
    assert decoded["outcome_counts"]["publication_lag_latest_public"] == 11
    assert decoded["outcome_counts"]["site_fetch_error"] == 1
    assert decoded["strict_target_year_successes"] == 9
    assert "dense_information_page" in decoded["site_families"]
    assert "table_header_confirmation_application" in decoded["site_families"]


def test_build_discovery_gold_run_plan_emits_bounded_pdf_discovery_inputs() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)

    plan = build_discovery_gold_run_plan(entries)

    assert len(plan) == 37
    aihok = next(item for item in plan if item.entry_id == "aihok-nursing-support-accepted-2026")
    assert aihok.school_id == 1369
    assert aihok.site_url == "https://www.jaaikosei.or.jp/aihokukansen/news/高等教育の修学支援制度について/"
    assert aihok.target_fiscal_year == 2026
    assert aihok.expected_outcome == "accepted_target_pdf"
    assert (
        aihok.expected_pdf_url
        == "https://www.jaaikosei.or.jp/aihokukansen/7LmQDt/wp-content/uploads/2025/08/youshiki2-r7.pdf"
    )
    ecole = next(item for item in plan if item.entry_id == "ecole-matsue-nutrition-2026")
    assert ecole.school_id == 1721
    assert ecole.site_url == "https://www.ecole-cpb.com/school-support"
    assert ecole.target_fiscal_year == 2026
    assert ecole.expected_outcome == "accepted_target_pdf"
    assert ecole.expected_pdf_url == "https://www.ecole-cpb.com/files/school_support_R8.pdf"


def test_render_discovery_gold_run_plan_outputs_json_array() -> None:
    payload = render_discovery_gold_run_plan(build_discovery_gold_run_plan(load_discovery_gold_entries(GOLD_SET_DIR)))

    decoded = json.loads(payload)

    assert len(decoded) == 37
    items_by_id = {item["entry_id"]: item for item in decoded}
    assert items_by_id["ast-kansai-ika-review-2026"]["site_url"] == "https://www.kmc.ast.ac.jp/jyouhoukokai/"
    assert (
        items_by_id["saitama-it-web-accepted-2026"]["site_url"]
        == "https://www.siw.ac.jp/information"
    )
    assert (
        items_by_id["hal-tokyo-embed-publication-lag-2026"]["site_url"]
        == "https://www.nkz.ac.jp/clginfo/thinfo.html"
    )
