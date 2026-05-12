from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"
EXPECTED_PREDICTIONS_PATH = GOLD_SET_DIR / "expected-predictions.jsonl"


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
    assert payload["total_gold_entries"] == 28
    assert payload["predicted_entries"] == 1
    assert payload["exact_matches"] == 1
    assert payload["missing_entries"] == 27


def test_eval_discovery_gold_cli_accepts_pdf_evidence_log(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 1721,
                "pdf_url": "https://www.ecole-cpb.com/files/school_support_R8.pdf",
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "extra": {"target_fiscal_year": "2026"},
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
            "--pdf-evidence",
            str(evidence_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["predicted_entries"] == 1
    assert payload["exact_matches"] == 1


def test_eval_discovery_gold_cli_preserves_pdf_evidence_pattern_type(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 760,
                "pdf_url": "https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471",
                "reason": "fiscal_year_mismatch:2024",
                "pdf_type": "target",
                "pattern_type": "wordpress_download_manager",
                "extra": {"target_fiscal_year": "2026"},
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
            "--pdf-evidence",
            str(evidence_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["predicted_entries"] == 1
    assert payload["exact_matches"] == 1


def test_eval_discovery_gold_cli_can_fail_on_incomplete_predictions(tmp_path: Path) -> None:
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
            "--fail-on-regression",
        ],
    )

    assert result.exit_code == 1
    assert "Discovery gold gate failed" in result.output
    assert "missing:     27" in result.output


def test_eval_discovery_gold_cli_full_expected_fixture_passes_fail_on_regression() -> None:
    result = CliRunner().invoke(
        app,
        [
            "eval-discovery-gold",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--predictions",
            str(EXPECTED_PREDICTIONS_PATH),
            "--fail-on-regression",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total_gold_entries"] == 28
    assert payload["predicted_entries"] == 28
    assert payload["exact_matches"] == 28
    assert payload["failed_predictions"] == 0
    assert payload["missing_entries"] == 0
    assert payload["unexpected_predictions"] == 0


def test_discovery_gold_expected_predictions_cli_matches_committed_fixture() -> None:
    result = CliRunner().invoke(
        app,
        [
            "discovery-gold-expected-predictions",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == EXPECTED_PREDICTIONS_PATH.read_text(encoding="utf-8")


def test_eval_discovery_gold_cli_full_fixture_fails_on_mismatch(tmp_path: Path) -> None:
    mutated_path = tmp_path / "mutated-predictions.jsonl"
    lines = EXPECTED_PREDICTIONS_PATH.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["outcome"] = "accepted_target_pdf"
    first["fiscal_year"] = 2026
    first["strict_target_year_success"] = True
    lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
    mutated_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "eval-discovery-gold",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--predictions",
            str(mutated_path),
            "--fail-on-regression",
        ],
    )

    assert result.exit_code == 1
    assert "Discovery gold gate failed" in result.output
    assert "failed:      1" in result.output


def test_eval_discovery_gold_cli_fails_on_pattern_type_mismatch(tmp_path: Path) -> None:
    mutated_path = tmp_path / "mutated-predictions.jsonl"
    lines = EXPECTED_PREDICTIONS_PATH.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        payload = json.loads(line)
        if payload.get("pattern_type"):
            payload["pattern_type"] = "direct"
            lines[index] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            break
    else:  # pragma: no cover - protected by the committed gold-set fixture
        raise AssertionError("expected at least one gold-set prediction with pattern_type")
    mutated_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "eval-discovery-gold",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--predictions",
            str(mutated_path),
            "--fail-on-regression",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["failed_predictions"] == 1
    assert "pattern_type_mismatch" in result.output


def test_eval_discovery_gold_cli_requires_one_input_mode(tmp_path: Path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text("", encoding="utf-8")
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text("", encoding="utf-8")

    missing = CliRunner().invoke(app, ["eval-discovery-gold", "--gold-set-dir", str(GOLD_SET_DIR)])
    both = CliRunner().invoke(
        app,
        [
            "eval-discovery-gold",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--predictions",
            str(predictions_path),
            "--pdf-evidence",
            str(evidence_path),
        ],
    )

    assert missing.exit_code == 2
    assert "Either --predictions or --pdf-evidence is required." in missing.output
    assert both.exit_code == 2
    assert "Use only one of --predictions or --pdf-evidence." in both.output
