from __future__ import annotations

import json
from pathlib import Path

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"
ENTRY_DIR = GOLD_SET_DIR / "entries"
MANUAL_RCA_RUNBOOK = Path(__file__).resolve().parents[2] / "docs" / "runbooks" / "discovery-codex-manual-rca.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_discovery_gold_set_schema_allows_image_only_review_entries() -> None:
    schema = _load_json(GOLD_SET_DIR / "schema.json")
    pdf_type_enum = schema["properties"]["expected_result"]["properties"]["pdf_type"]["enum"]

    assert "image_only" in pdf_type_enum


def test_discovery_gold_set_schema_and_prototypes_exist() -> None:
    assert (GOLD_SET_DIR / "schema.json").is_file()
    assert (GOLD_SET_DIR / "README.md").is_file()

    entries = sorted(ENTRY_DIR.glob("*.json"))
    assert len(entries) >= 10


def test_discovery_gold_set_entries_capture_manual_demonstrations() -> None:
    from eidp.scraper.discovery_gold_set import load_discovery_gold_entries, validate_discovery_gold_entries

    entries = [_load_json(path) for path in sorted(ENTRY_DIR.glob("*.json"))]
    entries_by_id = {entry["entry_id"]: entry for entry in entries}

    assert validate_discovery_gold_entries(load_discovery_gold_entries(GOLD_SET_DIR)) == []

    accepted = [entry for entry in entries if entry["outcome"] == "accepted_target_pdf"]
    assert accepted, "prototype set needs at least one successful discovery path"
    assert any(entry["target_fiscal_year"] == 2026 for entry in accepted)
    assert any(entry["evidence"]["source_kind"] == "manual_web" for entry in entries)
    assert any(entry["outcome"] == "needs_operator_review" for entry in entries)
    assert any(entry["outcome"] == "publication_lag_latest_public" for entry in entries)
    assert any(entry["outcome"] == "no_target_candidate_found" for entry in entries)
    assert any(entry["outcome"] == "site_fetch_error" for entry in entries)
    assert any(entry["evidence"]["source_kind"] == "saitama_rca_jsonl" for entry in entries)
    assert len({entry["entry_id"] for entry in entries}) == len(entries)
    assert entries_by_id["saitama-it-web-accepted-2026"]["outcome"] == "publication_lag_latest_public"
    assert entries_by_id["saitama-it-web-accepted-2026"]["expected_result"]["strict_target_year_success"] is False
    assert entries_by_id["ageo-central-nursing-review-2026"]["outcome"] == "accepted_target_pdf"
    assert entries_by_id["ageo-central-nursing-review-2026"]["expected_result"]["fiscal_year"] == 2026

    for entry in entries:
        assert entry["schema_version"] == "discovery-gold-set/v0.1"
        assert entry["school"]["school_id"] > 0
        assert entry["target_fiscal_year"] >= 2025
        assert entry["outcome"] in {
            "accepted_target_pdf",
            "publication_lag_latest_public",
            "no_target_candidate_found",
            "needs_operator_review",
            "site_fetch_error",
        }
        assert entry["manual_demonstration"]["operator_goal"]
        assert entry["manual_demonstration"]["steps"]
        assert entry["automation_pattern"]["reusable_rules"]
        assert entry["evidence"]["source_kind"] in {
            "windows_v136_jsonl",
            "manual_web",
            "operator_review",
            "saitama_rca_jsonl",
            "current_code_jsonl",
        }

        if entry["outcome"] == "accepted_target_pdf":
            assert entry["expected_result"]["pdf_url"].endswith(".pdf")
            assert entry["expected_result"]["pdf_type"] == "target"
            assert entry["expected_result"]["fiscal_year"] == entry["target_fiscal_year"]


def test_discovery_gold_set_semantic_validator_rejects_inconsistent_outcomes() -> None:
    from eidp.scraper.discovery_gold_set import DiscoveryGoldEntry, validate_discovery_gold_entries

    errors = validate_discovery_gold_entries([
        DiscoveryGoldEntry(
            entry_id="bad-accepted",
            school_id=1,
            school_name="学校",
            prefecture="東京都",
            corporation_name="",
            target_fiscal_year=2026,
            outcome="accepted_target_pdf",
            school_url="https://example.test/",
            disclosure_url="https://example.test/disclosure/",
            pdf_url="https://example.test/r7.pdf",
            pdf_type="target",
            fiscal_year=2025,
            strict_target_year_success=False,
            site_family="test",
        )
    ])

    assert "bad-accepted: accepted_target_pdf fiscal_year must equal target_fiscal_year" in errors
    assert "bad-accepted: accepted_target_pdf requires strict_target_year_success=true" in errors


def test_manual_rca_runbook_contains_single_school_packet_contract() -> None:
    text = MANUAL_RCA_RUNBOOK.read_text(encoding="utf-8")

    assert "## Single-School RCA Packet" in text
    assert '"latest_evidence_rows_path"' in text
    assert '"checked_paths"' in text
    assert '"search_queries_used"' in text
    assert "Allowed `layer` values" in text
    assert "layer_0_official_index_handoff" in text
    assert "layer_1_pdf_discovery" in text
    assert "site_infrastructure_failure" in text
    assert "at most three query variants" in text
    assert "third-party directories are hints for a domain, never truth sources" in text
    assert "bootstrap-{timestamp}-discovery-rca-batch-plan.json" in text
    assert "uv run eidp discovery-rca-outcome-validate" in text
    assert '`accepted_target_pdf` must include a PDF URL' in text
    assert '`operator_action="wait_for_publication"`' in text
    assert "Every output must also include at least one `checked_paths` entry" in text
    assert '"checked_paths": ["https://example.ac.jp/disclosure"]' in text
    assert "path/to/rca-outcomes/" in text
    assert "--batch-plan path/to/discovery-rca-batch-plan.json" in text
    assert "details.discovery_rca_batch_plan_path" in text
