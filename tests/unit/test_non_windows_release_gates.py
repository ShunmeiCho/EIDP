"""Tests for the non-Windows release gate helper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_non_windows_release_gates.py"
spec = importlib.util.spec_from_file_location("run_non_windows_release_gates", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_gate_commands_includes_package_verifiers_without_full_unit() -> None:
    package = Path("dist/eidp-windows-v351.zip")

    commands = module.build_gate_commands(package, include_full_unit=False)

    names = [command.name for command in commands]
    assert "unit_full" not in names
    assert names[-2:] == ["package_verify", "package_verify_demonstrated_patterns"]
    validator_unit = next(command for command in commands if command.name == "validator_distribution_unit")
    assert "tests/unit/test_stage6_evidence_bundle.py" in validator_unit.command
    validator_mypy = next(command for command in commands if command.name == "validator_distribution_mypy")
    assert "scripts/verify_stage6_evidence.py" in validator_mypy.command
    validator_ruff = next(command for command in commands if command.name == "validator_distribution_ruff")
    assert "scripts/verify_stage6_evidence.py" in validator_ruff.command
    assert "tests/unit/test_stage6_evidence_bundle.py" in validator_ruff.command
    assert str(package) in commands[-2].command
    assert "--require-demonstrated-discovery-patterns" in commands[-1].command


def test_build_gate_commands_can_include_pdf_evidence_replays() -> None:
    evidence = Path("_temp/evidence.jsonl")

    commands = module.build_gate_commands(
        Path("dist/eidp-windows.zip"),
        include_full_unit=False,
        pdf_evidence_paths=[evidence],
    )

    evidence_commands = [
        command for command in commands if command.name == "discovery_gold_pdf_evidence_1"
    ]
    assert len(evidence_commands) == 1
    assert "--pdf-evidence" in evidence_commands[0].command
    assert str(evidence) in evidence_commands[0].command


def test_build_gate_commands_can_include_full_unit_first() -> None:
    commands = module.build_gate_commands(Path("dist/eidp-windows.zip"), include_full_unit=True)

    assert commands[0].name == "unit_full"
    assert commands[0].command[:3] == (sys.executable, "-m", "pytest")


def test_verify_sha256_sidecar_accepts_matching_file(tmp_path: Path) -> None:
    package = tmp_path / "eidp-windows.zip"
    package.write_bytes(b"package")
    digest = hashlib.sha256(b"package").hexdigest()
    package.with_suffix(".zip.sha256").write_text(f"{digest}  {package}\n", encoding="utf-8")

    result = module.verify_sha256_sidecar(package)

    assert result["ok"] is True
    assert result["actual"] == digest
    assert result["expected"] == digest


def test_verify_sha256_sidecar_rejects_mismatch(tmp_path: Path) -> None:
    package = tmp_path / "eidp-windows.zip"
    package.write_bytes(b"package")
    package.with_suffix(".zip.sha256").write_text(f"{'0' * 64}  {package}\n", encoding="utf-8")

    result = module.verify_sha256_sidecar(package)

    assert result["ok"] is False
    assert result["actual"] == hashlib.sha256(b"package").hexdigest()
    assert result["expected"] == "0" * 64


def test_pdf_evidence_gate_allows_missing_entries() -> None:
    error = module._pdf_evidence_gate_error(
        json.dumps(
            {
                "failed_predictions": 0,
                "unexpected_predictions": 0,
                "missing_entries": 28,
            }
        )
    )

    assert error is None


def test_pdf_evidence_gate_rejects_failed_predictions() -> None:
    error = module._pdf_evidence_gate_error(
        json.dumps(
            {
                "failed_predictions": 1,
                "unexpected_predictions": 0,
                "missing_entries": 28,
            }
        )
    )

    assert error == "pdf-evidence replay had failed_predictions=1, unexpected_predictions=0"


def test_run_gate_fails_pdf_evidence_result_when_json_has_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"failed_predictions": 1, "unexpected_predictions": 0}),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.run_gate(module.GateCommand("discovery_gold_pdf_evidence_1", ("python",)))

    assert result.returncode == 1
    assert result.stderr_tail == "pdf-evidence replay had failed_predictions=1, unexpected_predictions=0"
