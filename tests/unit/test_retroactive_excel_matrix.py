"""Tests for the retroactive Excel matrix runner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_retroactive_excel_matrix.py"
spec = importlib.util.spec_from_file_location("run_retroactive_excel_matrix", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_parse_case_accepts_year_and_reference() -> None:
    case = module.parse_case("2025=_temp/reference.xlsx")

    assert case.fiscal_year == 2025
    assert case.reference_xlsx == Path("_temp/reference.xlsx")


@pytest.mark.parametrize("value", ["2025", "FY2025=ref.xlsx", "1999=ref.xlsx", "2025="])
def test_parse_case_rejects_invalid_values(value: str) -> None:
    with pytest.raises(Exception, match="case"):
        module.parse_case(value)


def test_default_case_output_uses_package_label() -> None:
    output = module.default_case_output(
        package_zip=Path("dist/eidp-windows-v419.zip"),
        fiscal_year=2024,
        output_dir=Path("logs"),
    )

    assert output == Path("logs/release-gate-v419-retroactive-fy2024-reference.json")


def test_build_case_command_forwards_release_gate_flags() -> None:
    command = module.build_case_command(
        package_zip=Path("dist/eidp-windows-v419.zip"),
        case=module.MatrixCase(2025, Path("_temp/ref.xlsx")),
        output_json=Path("logs/out.json"),
        skip_full_unit=True,
        allow_stale_package=False,
        allow_docs_only_stale_package=True,
        retroactive_master=Path("data/master.xlsx"),
        numeric_tolerance=1e-9,
    )

    assert command[:3] == (sys.executable, str(module.RELEASE_GATE_SCRIPT), "dist/eidp-windows-v419.zip")
    assert "--skip-full-unit" in command
    assert "--allow-docs-only-stale-package" in command
    assert "--retroactive-excel-reference" in command
    assert command[command.index("--retroactive-excel-reference") + 1] == "_temp/ref.xlsx"
    assert command[command.index("--retroactive-fiscal-year") + 1] == "2025"
    assert command[command.index("--retroactive-master") + 1] == "data/master.xlsx"
    assert command[command.index("--retroactive-numeric-tolerance") + 1] == "1e-09"
    assert command[-2:] == ("--output", "logs/out.json")


def test_run_matrix_runs_full_unit_only_for_first_case_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(command)
        output_index = command.index("--output") + 1
        Path(command[output_index]).write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    results = module.run_matrix(
        package_zip=Path("dist/eidp-windows-v419.zip"),
        cases=[
            module.MatrixCase(2025, Path("fy2025.xlsx")),
            module.MatrixCase(2024, Path("fy2024.xlsx")),
        ],
        output_dir=tmp_path,
        skip_full_unit=False,
        full_unit_each_case=False,
        allow_stale_package=False,
        allow_docs_only_stale_package=True,
        retroactive_master=Path("data/master.xlsx"),
        numeric_tolerance=0.0,
        keep_going=False,
    )

    assert [result.ok for result in results] == [True, True]
    assert "--skip-full-unit" not in captured[0]
    assert "--skip-full-unit" in captured[1]


def test_run_matrix_stops_after_failure_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output_index = command.index("--output") + 1
        Path(command[output_index]).write_text(json.dumps({"ok": False}) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    results = module.run_matrix(
        package_zip=Path("dist/eidp-windows-v419.zip"),
        cases=[
            module.MatrixCase(2025, Path("fy2025.xlsx")),
            module.MatrixCase(2024, Path("fy2024.xlsx")),
        ],
        output_dir=tmp_path,
        skip_full_unit=True,
        full_unit_each_case=False,
        allow_stale_package=False,
        allow_docs_only_stale_package=True,
        retroactive_master=Path("data/master.xlsx"),
        numeric_tolerance=0.0,
        keep_going=False,
    )

    assert calls == 1
    assert len(results) == 1
    assert results[0].returncode == 1
    assert results[0].ok is False


def test_summarize_requires_every_case_to_pass() -> None:
    passing = module.MatrixCaseResult(
        fiscal_year=2025,
        reference_xlsx="ref.xlsx",
        output_json="out.json",
        command=("python",),
        returncode=0,
        duration_s=0.1,
        ok=True,
        stdout_tail="",
        stderr_tail="",
    )
    failing = module.MatrixCaseResult(
        fiscal_year=2024,
        reference_xlsx="ref.xlsx",
        output_json="out.json",
        command=("python",),
        returncode=0,
        duration_s=0.1,
        ok=False,
        stdout_tail="",
        stderr_tail="",
    )

    assert module.summarize(package_zip=Path("dist/pkg.zip"), results=[passing])["ok"] is True
    assert module.summarize(package_zip=Path("dist/pkg.zip"), results=[passing, failing])["ok"] is False
