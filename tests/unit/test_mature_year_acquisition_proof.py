from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_mature_year_acquisition_proof.py"
    spec = importlib.util.spec_from_file_location("build_mature_year_acquisition_proof", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_last_run(path: Path, **overrides: object) -> None:
    payload = {
        "status": "success",
        "finished_at": "2026-05-17T01:02:03+00:00",
        "dry_run": False,
        "current_fy": 2025,
        "target_pdf_auto_denominator_count": 1625,
        "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
        "target_missing_school_count": 1625,
        "target_pdf_auto_yield_pct": 67.5,
        "operator_reviewable_yield_pct": 72.0,
        "ship_gate_status": "pass",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_strict_gap_analysis(path: Path, **overrides: object) -> None:
    payload = {
        "basis": "strict_yield_gap_analysis",
        "database": "_temp/fy2025/data/eidp.sqlite3",
        "fiscal_year": 2025,
        "school_type": "専門学校",
        "schools_total": 1000,
        "strict_target_parsed_schools": 600,
        "strict_target_parsed_rate_pct": 60.0,
        "excel_ready_schools": 600,
        "excel_ready_rate_pct": 60.0,
        "operator_reviewable_schools": 798,
        "operator_reviewable_rate_pct": 79.8,
        "estimated_manual_workload_rate_pct": 20.2,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_proof_accepts_mature_year_acquisition_case(tmp_path: Path) -> None:
    module = _load_module()
    last_run = tmp_path / "last_run.json"
    _write_last_run(last_run)

    proof = module.build_proof([(2025, last_run)])

    assert proof["ok"] is True
    assert proof["basis"] == "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition"
    assert proof["min_target_pdf_auto_denominator_count"] == 1000
    assert proof["cases"][0]["ok"] is True
    assert proof["cases"][0]["target_pdf_auto_denominator_count"] == 1625
    assert proof["cases"][0]["target_pdf_auto_yield_pct"] == 67.5
    assert proof["cases"][0]["operator_reviewable_yield_pct"] == 72.0
    assert proof["cases"][0]["estimated_manual_workload_pct"] == 28.0
    assert proof["cases"][0]["threshold_gaps"] == []


def test_build_proof_accepts_strict_gap_analysis_case(tmp_path: Path) -> None:
    module = _load_module()
    strict_gap = tmp_path / "strict-gap-analysis.json"
    _write_strict_gap_analysis(strict_gap)

    proof = module.build_proof([], strict_gap_analysis_cases=[(2025, strict_gap)])

    assert proof["ok"] is True
    assert proof["basis"] == "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition"
    assert proof["cases"][0]["ok"] is True
    assert proof["cases"][0]["evidence_source"] == "strict_gap_analysis"
    assert proof["cases"][0]["strict_gap_analysis"] == str(strict_gap)
    assert proof["cases"][0]["target_pdf_auto_denominator_count"] == 1000
    assert proof["cases"][0]["target_pdf_auto_yield_pct"] == 60.0
    assert proof["cases"][0]["excel_ready_yield_pct"] == 60.0
    assert proof["cases"][0]["operator_reviewable_yield_pct"] == 79.8
    assert proof["cases"][0]["estimated_manual_workload_pct"] == 20.2
    assert proof["cases"][0]["ship_gate_status"] == "pass"


def test_build_proof_rejects_low_target_yield_and_manual_workload(tmp_path: Path) -> None:
    module = _load_module()
    last_run = tmp_path / "last_run.json"
    _write_last_run(
        last_run,
        target_pdf_auto_yield_pct=40.0,
        operator_reviewable_yield_pct=60.0,
    )

    proof = module.build_proof([(2025, last_run)])

    assert proof["ok"] is False
    assert proof["cases"][0]["ok"] is False
    assert "target_pdf_auto_yield_pct below release threshold: 40.0 < 60.0" in proof["cases"][0]["errors"]
    assert "estimated manual workload above release threshold: 40.0 > 30.0" in proof["cases"][0]["errors"]
    assert proof["cases"][0]["threshold_gaps"] == ["strict_auto_yield", "manual_workload"]


def test_build_proof_rejects_strict_gap_analysis_with_low_excel_ready(tmp_path: Path) -> None:
    module = _load_module()
    strict_gap = tmp_path / "strict-gap-analysis.json"
    _write_strict_gap_analysis(strict_gap, excel_ready_rate_pct=59.9)

    proof = module.build_proof([], strict_gap_analysis_cases=[(2025, strict_gap)])

    assert proof["ok"] is False
    assert proof["cases"][0]["ok"] is False
    assert "excel_ready_rate_pct below release threshold: 59.9 < 60.0" in proof["cases"][0]["errors"]


def test_build_proof_rejects_wrong_strict_gap_analysis_basis_and_fiscal_year(tmp_path: Path) -> None:
    module = _load_module()
    strict_gap = tmp_path / "strict-gap-analysis.json"
    _write_strict_gap_analysis(strict_gap, basis="weekly", fiscal_year=2024)

    proof = module.build_proof([], strict_gap_analysis_cases=[(2025, strict_gap)])

    assert proof["ok"] is False
    assert proof["cases"][0]["ok"] is False
    assert "strict_gap_analysis basis must be strict_yield_gap_analysis: 'weekly'" in proof["cases"][0]["errors"]
    assert "strict_gap_analysis fiscal_year must be 2025" in proof["cases"][0]["errors"]


def test_build_proof_rejects_small_mature_year_denominator(tmp_path: Path) -> None:
    module = _load_module()
    last_run = tmp_path / "last_run.json"
    _write_last_run(last_run, target_pdf_auto_denominator_count=5, target_missing_school_count=5)

    proof = module.build_proof([(2025, last_run)])

    assert proof["ok"] is False
    assert proof["cases"][0]["ok"] is False
    assert (
        "target_pdf_auto_denominator_count below production-scale threshold: 5 < 1000"
        in proof["cases"][0]["errors"]
    )


def test_build_proof_rejects_missing_denominator_scope(tmp_path: Path) -> None:
    module = _load_module()
    last_run = tmp_path / "last_run.json"
    _write_last_run(last_run, target_pdf_auto_denominator_scope=None)

    proof = module.build_proof([(2025, last_run)])

    assert proof["ok"] is False
    assert proof["cases"][0]["ok"] is False
    assert (
        "target_pdf_auto_denominator_scope must be target_missing_schools_before_run"
        in proof["cases"][0]["errors"]
    )


def test_build_proof_rejects_dry_run_and_wrong_fiscal_year(tmp_path: Path) -> None:
    module = _load_module()
    last_run = tmp_path / "last_run.json"
    _write_last_run(last_run, dry_run=True, current_fy=2024)

    proof = module.build_proof([(2025, last_run)])

    assert proof["ok"] is False
    assert "last_run dry_run must be false" in proof["cases"][0]["errors"]
    assert "last_run current_fy must be 2025" in proof["cases"][0]["errors"]


def test_cli_writes_json_and_returns_failure_for_missing_case(tmp_path: Path, capsys) -> None:
    module = _load_module()
    output = tmp_path / "proof.json"
    missing = tmp_path / "missing-last-run.json"

    rc = module.main(["--case", f"2025={missing}", "--output", str(output), "--json"])

    assert rc == 1
    stdout_payload = json.loads(capsys.readouterr().out)
    output_payload = json.loads(output.read_text(encoding="utf-8"))
    assert stdout_payload == output_payload
    assert output_payload["ok"] is False
    assert output_payload["basis"] == "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition"
    assert output_payload["cases"][0]["errors"] == [f"last_run does not exist: {missing}"]


def test_cli_accepts_strict_gap_analysis_case(tmp_path: Path, capsys) -> None:
    module = _load_module()
    output = tmp_path / "proof.json"
    strict_gap = tmp_path / "strict-gap-analysis.json"
    _write_strict_gap_analysis(strict_gap)

    rc = module.main(
        [
            "--strict-gap-analysis-case",
            f"2025={strict_gap}",
            "--output",
            str(output),
            "--json",
        ]
    )

    assert rc == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    output_payload = json.loads(output.read_text(encoding="utf-8"))
    assert stdout_payload == output_payload
    assert output_payload["ok"] is True
    assert output_payload["cases"][0]["evidence_source"] == "strict_gap_analysis"
