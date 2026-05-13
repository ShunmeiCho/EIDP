"""Tests for the non-Windows release gate helper."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

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
    assert str(package) in commands[-2].command
    assert "--require-demonstrated-discovery-patterns" in commands[-1].command


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
