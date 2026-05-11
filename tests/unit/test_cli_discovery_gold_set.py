from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"


def test_discovery_gold_set_cli_outputs_summary_json() -> None:
    result = CliRunner().invoke(
        app,
        ["discovery-gold-set", "--gold-set-dir", str(GOLD_SET_DIR), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total_entries"] == 17
    assert payload["outcome_counts"]["publication_lag_latest_public"] == 4
    assert payload["outcome_counts"]["no_target_candidate_found"] == 1
    assert payload["outcome_counts"]["site_fetch_error"] == 1
    assert payload["operator_review_entries"] == 6


def test_discovery_gold_run_plan_cli_outputs_json_array() -> None:
    result = CliRunner().invoke(
        app,
        ["discovery-gold-run-plan", "--gold-set-dir", str(GOLD_SET_DIR), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload) == 17
    items_by_id = {item["entry_id"]: item for item in payload}
    assert items_by_id["ast-kansai-ika-review-2026"]["site_url"] == "https://www.kmc.ast.ac.jp/jyouhoukokai/"
    assert (
        items_by_id["ageo-central-nursing-review-2026"]["site_url"]
        == "https://ageo.org/admission/support.php"
    )
