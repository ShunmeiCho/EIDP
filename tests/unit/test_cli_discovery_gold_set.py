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
    assert payload["total_entries"] == 10
    assert payload["outcome_counts"]["publication_lag_latest_public"] == 2
    assert payload["operator_review_entries"] == 4
