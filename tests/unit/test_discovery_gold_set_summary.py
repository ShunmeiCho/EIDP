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

    assert summary.total_entries == 45
    assert summary.target_fiscal_year_counts == {2025: 2, 2026: 43}
    assert summary.outcome_counts == {
        "accepted_target_pdf": 10,
        "needs_operator_review": 15,
        "no_target_candidate_found": 1,
        "publication_lag_latest_public": 18,
        "site_fetch_error": 1,
    }
    assert summary.strict_target_year_successes == 10
    assert summary.operator_review_entries == 15
    assert summary.publication_lag_entries == 18
    assert summary.pattern_source_counts == {
        "direct": 11,
        "embed": 1,
        "wordpress": 6,
        "wordpress_download_manager": 1,
    }
    assert "ascending_historical_support_forms_latest_public" in summary.site_families
    assert "wordpress_current_year_anchor_context" in summary.site_families
    assert "empty_stale_anchor_before_visible_current_year_anchor" in summary.site_families
    assert "multi_year_support_pdf_list_current_year_anchor" in summary.site_families
    assert "news_definition_list_support_year_statement" in summary.site_families
    assert "prefecture_hosted_public_school_publication_lag" in summary.site_families
    assert "school_support_page_with_adjacent_target_year_statement" in summary.site_families
    assert "table_header_confirmation_application" in summary.site_families
    assert "wix_dense_information_page_old_year_target_form" in summary.site_families


def test_render_discovery_gold_summary_outputs_json_safe_payload() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    payload = render_discovery_gold_summary(summarize_discovery_gold_entries(entries))

    decoded = json.loads(payload)

    assert decoded["total_entries"] == 45
    assert decoded["outcome_counts"]["needs_operator_review"] == 15
    assert decoded["outcome_counts"]["no_target_candidate_found"] == 1
    assert decoded["outcome_counts"]["publication_lag_latest_public"] == 18
    assert decoded["outcome_counts"]["site_fetch_error"] == 1
    assert decoded["strict_target_year_successes"] == 10
    assert "dense_information_page" in decoded["site_families"]
    assert "table_header_confirmation_application" in decoded["site_families"]


def test_build_discovery_gold_run_plan_emits_bounded_pdf_discovery_inputs() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)

    plan = build_discovery_gold_run_plan(entries)

    assert len(plan) == 45
    aihok = next(item for item in plan if item.entry_id == "aihok-nursing-support-accepted-2026")
    assert aihok.school_id == 1369
    assert aihok.site_url == "https://www.jaaikosei.or.jp/aihokukansen/news/高等教育の修学支援制度について/"
    assert aihok.target_fiscal_year == 2026
    assert aihok.expected_outcome == "accepted_target_pdf"
    assert (
        aihok.expected_pdf_url
        == "https://www.jaaikosei.or.jp/aihokukansen/7LmQDt/wp-content/uploads/2025/08/youshiki2-r7.pdf"
    )
    iwate_iryo = next(item for item in plan if item.entry_id == "iwate-iryo-dh-publication-lag-2026")
    assert iwate_iryo.school_id == 968
    assert iwate_iryo.site_url == "https://www.iwate-iryo-dh.com/blank-7"
    assert iwate_iryo.target_fiscal_year == 2026
    assert iwate_iryo.expected_outcome == "publication_lag_latest_public"
    assert (
        iwate_iryo.expected_pdf_url
        == "https://www.iwate-iryo-dh.com/_files/ugd/c773fc_c40d31d7e10e4706937b3da7af27d372.pdf"
    )
    hamamatsu_kohka = next(item for item in plan if item.entry_id == "hamamatsu-kohka-support-accepted-2026")
    assert hamamatsu_kohka.school_id == 1317
    assert hamamatsu_kohka.site_url == "https://kohka-h.ac.jp/disclose"
    assert hamamatsu_kohka.target_fiscal_year == 2026
    assert hamamatsu_kohka.expected_outcome == "accepted_target_pdf"
    assert (
        hamamatsu_kohka.expected_pdf_url
        == "https://kohka-h.ac.jp/kohkacms/wp-content/uploads/2025/06/5ad4c281d27a5d882d3124e8c86dbe7e.pdf"
    )
    nagano_public_health = next(item for item in plan if item.entry_id == "nagano-public-health-publication-lag-2026")
    assert nagano_public_health.school_id == 1252
    assert nagano_public_health.site_url == "https://www.pref.nagano.lg.jp/koshueisei/guidance/sinseisyo.html"
    assert nagano_public_health.target_fiscal_year == 2026
    assert nagano_public_health.expected_outcome == "publication_lag_latest_public"
    assert (
        nagano_public_health.expected_pdf_url
        == "https://www.pref.nagano.lg.jp/koshueisei/guidance/documents/2025shinseisho2go.pdf"
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

    assert len(decoded) == 45
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
