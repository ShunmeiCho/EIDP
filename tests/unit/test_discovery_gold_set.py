from __future__ import annotations

import json
from pathlib import Path

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"
ENTRY_DIR = GOLD_SET_DIR / "entries"
MANUAL_RCA_RUNBOOK = Path(__file__).resolve().parents[2] / "docs" / "runbooks" / "discovery-codex-manual-rca.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_discovery_gold_set_schema_and_prototypes_exist() -> None:
    assert (GOLD_SET_DIR / "schema.json").is_file()
    assert (GOLD_SET_DIR / "README.md").is_file()

    entries = sorted(ENTRY_DIR.glob("*.json"))
    assert len(entries) >= 10


def test_discovery_gold_set_entries_capture_manual_demonstrations() -> None:
    entries = [_load_json(path) for path in sorted(ENTRY_DIR.glob("*.json"))]
    entries_by_id = {entry["entry_id"]: entry for entry in entries}

    accepted = [entry for entry in entries if entry["outcome"] == "accepted_target_pdf"]
    assert accepted, "prototype set needs at least one successful discovery path"
    assert any(entry["target_fiscal_year"] == 2026 for entry in accepted)
    assert any(entry["evidence"]["source_kind"] == "manual_web" for entry in entries)
    assert any(entry["outcome"] == "needs_operator_review" for entry in entries)
    assert any(entry["outcome"] == "publication_lag_latest_public" for entry in entries)
    assert any(entry["outcome"] == "no_target_candidate_found" for entry in entries)
    assert any(entry["evidence"]["source_kind"] == "saitama_rca_jsonl" for entry in entries)
    assert len({entry["entry_id"] for entry in entries}) == len(entries)
    assert entries_by_id["saitama-it-web-accepted-2026"]["outcome"] == "accepted_target_pdf"
    assert entries_by_id["saitama-it-web-accepted-2026"]["expected_result"]["strict_target_year_success"] is True
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
        }
        assert entry["manual_demonstration"]["operator_goal"]
        assert entry["manual_demonstration"]["steps"]
        assert entry["automation_pattern"]["reusable_rules"]
        assert entry["evidence"]["source_kind"] in {
            "windows_v136_jsonl",
            "manual_web",
            "operator_review",
            "saitama_rca_jsonl",
        }

        if entry["outcome"] == "accepted_target_pdf":
            assert entry["expected_result"]["pdf_url"].endswith(".pdf")
            assert entry["expected_result"]["pdf_type"] == "target"
            assert entry["expected_result"]["fiscal_year"] == entry["target_fiscal_year"]


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
    assert "details.discovery_rca_batch_plan_path" in text
