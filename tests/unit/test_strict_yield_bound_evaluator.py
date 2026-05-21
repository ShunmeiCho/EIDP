from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_strict_yield_bound.py"
    spec = importlib.util.spec_from_file_location("evaluate_strict_yield_bound", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_strict_yield_bound_marks_no_go_when_remaining_cannot_reach_gate() -> None:
    module = _load_module()

    result = module.evaluate_bound(
        denominator=1000,
        processed=607,
        strict_successes=0,
        required_strict_yield_pct=60.0,
        target_fiscal_year=2026,
        discovered_target_year_documents=0,
    )

    assert result["ok"] is False
    assert result["status"] == "no_go_upper_bound_below_required"
    assert result["required_strict_count"] == 600
    assert result["remaining_schools"] == 393
    assert result["max_possible_strict_count_if_all_remaining_pass"] == 393
    assert result["max_possible_strict_yield_pct_if_all_remaining_pass"] == 39.3
    assert result["target_fiscal_year"] == 2026
    assert result["discovered_target_year_documents"] == 0


def test_strict_yield_bound_keeps_still_possible_separate_from_pass() -> None:
    module = _load_module()

    result = module.evaluate_bound(
        denominator=1000,
        processed=590,
        strict_successes=200,
        required_strict_yield_pct=60.0,
    )

    assert result["ok"] is False
    assert result["status"] == "still_possible_below_gate"
    assert result["required_strict_count"] == 600
    assert result["max_possible_strict_count_if_all_remaining_pass"] == 610


def test_strict_yield_bound_passes_when_required_count_is_already_met() -> None:
    module = _load_module()

    result = module.evaluate_bound(
        denominator=1000,
        processed=1000,
        strict_successes=600,
        required_strict_yield_pct=60.0,
    )

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["current_strict_yield_pct"] == 60.0


def test_strict_yield_bound_cli_reads_gap_json(tmp_path: Path, capsys) -> None:
    module = _load_module()
    gap_json = tmp_path / "strict-gap.json"
    gap_json.write_text(
        json.dumps(
            {
                "fiscal_year": 2025,
                "schools_total": 1000,
                "strict_target_parsed_schools": 600,
            }
        ),
        encoding="utf-8",
    )

    rc = module.main(["--strict-gap-json", str(gap_json), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["target_fiscal_year"] == 2025
    assert payload["processed_position"] == 1000
