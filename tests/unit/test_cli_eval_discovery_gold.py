from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"


def test_eval_discovery_gold_cli_outputs_json_report(tmp_path: Path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        json.dumps(
            {
                "entry_id": "ecole-matsue-nutrition-2026",
                "outcome": "accepted_target_pdf",
                "pdf_url": "https://www.ecole-cpb.com/files/school_support_R8.pdf",
                "fiscal_year": 2026,
                "strict_target_year_success": True,
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "eval-discovery-gold",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--predictions",
            str(predictions_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total_gold_entries"] == 10
    assert payload["predicted_entries"] == 1
    assert payload["exact_matches"] == 1
    assert payload["missing_entries"] == 9
