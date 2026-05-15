"""Tests for the non-Windows release gate helper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
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


def test_build_retroactive_excel_gate_commands_uses_isolated_app_root(tmp_path: Path) -> None:
    app_root = tmp_path / "retroactive"
    master = tmp_path / "master.xlsx"
    reference = tmp_path / "reference.xlsx"

    commands = module.build_retroactive_excel_gate_commands(
        app_root=app_root,
        master_xlsx=master,
        reference_xlsx=reference,
        fiscal_year=2025,
    )

    assert [command.name for command in commands] == [
        "retroactive_excel_prepare",
        "retroactive_excel_db_bootstrap",
        "retroactive_excel_import",
        "retroactive_excel_export",
        "retroactive_excel_diff_reference",
    ]
    env = dict(commands[1].env)
    assert env["EIDP_APP_ROOT"] == str(app_root)
    assert env["EIDP_DATABASE_URL"] == f"sqlite:///{app_root / 'data' / 'eidp.sqlite3'}"
    assert env["EIDP_TARGET_FISCAL_YEAR"] == "2025"
    assert commands[2].command[-1] == str(app_root / "data" / "master.xlsx")
    assert "--business-values" in commands[-1].command
    assert "--fail-on-diff" in commands[-1].command
    assert "--numeric-tolerance" not in commands[-1].command
    assert str(reference) in commands[-1].command


def test_build_retroactive_excel_gate_commands_can_pass_numeric_tolerance(tmp_path: Path) -> None:
    commands = module.build_retroactive_excel_gate_commands(
        app_root=tmp_path / "retroactive",
        master_xlsx=tmp_path / "master.xlsx",
        reference_xlsx=tmp_path / "reference.xlsx",
        fiscal_year=2025,
        numeric_tolerance=1e-9,
    )

    assert "--numeric-tolerance" in commands[-1].command
    tolerance_index = commands[-1].command.index("--numeric-tolerance")
    assert commands[-1].command[tolerance_index + 1] == "1e-09"


def test_retroactive_excel_prepare_command_creates_isolated_root(tmp_path: Path) -> None:
    app_root = tmp_path / "retroactive"
    master = tmp_path / "master.xlsx"
    master.write_bytes(b"PK fake")
    commands = module.build_retroactive_excel_gate_commands(
        app_root=app_root,
        master_xlsx=master,
        reference_xlsx=tmp_path / "reference.xlsx",
        fiscal_year=2025,
    )

    result = module.run_gate(commands[0])

    assert result.returncode == 0
    assert (app_root / "data" / "master.xlsx").read_bytes() == b"PK fake"
    assert (app_root / "output").is_dir()
    assert (app_root / "logs").is_dir()


def test_retroactive_excel_prepare_command_rejects_non_empty_root(tmp_path: Path) -> None:
    app_root = tmp_path / "retroactive"
    app_root.mkdir()
    (app_root / "existing.txt").write_text("occupied", encoding="utf-8")
    master = tmp_path / "master.xlsx"
    master.write_bytes(b"PK fake")
    commands = module.build_retroactive_excel_gate_commands(
        app_root=app_root,
        master_xlsx=master,
        reference_xlsx=tmp_path / "reference.xlsx",
        fiscal_year=2025,
    )

    result = module.run_gate(commands[0])

    assert result.returncode == 1
    assert "retroactive app root is not empty" in result.stderr_tail


def test_run_gate_merges_command_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_env: dict[str, str] = {}

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_env.update(kwargs["env"])
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.run_gate(module.GateCommand("env_gate", ("python", "-V"), (("EIDP_TARGET_FISCAL_YEAR", "2025"),)))

    assert result.returncode == 0
    assert captured_env["EIDP_TARGET_FISCAL_YEAR"] == "2025"


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


def test_verify_package_source_commit_rejects_stale_zip_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)

    result = module.verify_package_source_commit(package)

    assert result["ok"] is False
    assert result["package_commit"] == package_commit
    assert result["source_commit"] == source_commit
    assert "does not match current source HEAD" in result["error"]


def test_verify_package_source_commit_can_allow_stale_zip_for_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)

    result = module.verify_package_source_commit(package, allow_stale_package=True)

    assert result["ok"] is True
    assert result["stale"] is True
    assert result["package_commit"] == package_commit
    assert result["source_commit"] == source_commit


def test_verify_package_source_commit_can_allow_docs_only_stale_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(
        module,
        "_docs_only_stale_check",
        lambda base, head: {
            "ok": True,
            "changed_paths": ["docs/reports/current-release-status.md"],
        },
    )

    result = module.verify_package_source_commit(
        package,
        allow_docs_only_stale_package=True,
    )

    assert result["ok"] is True
    assert result["stale"] is True
    assert result["docs_only_stale"] is True
    assert result["allowed_stale_reason"] == "docs_only"
    assert result["changed_paths"] == ["docs/reports/current-release-status.md"]


def test_verify_package_source_commit_rejects_docs_only_override_for_source_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(
        module,
        "_docs_only_stale_check",
        lambda base, head: {
            "ok": False,
            "changed_paths": ["src/eidp/cli.py"],
            "error": "stale package has non-doc changes: src/eidp/cli.py",
        },
    )

    result = module.verify_package_source_commit(
        package,
        allow_docs_only_stale_package=True,
    )

    assert result["ok"] is False
    assert result["stale"] is True
    assert result["docs_only_stale"] is False
    assert result["changed_paths"] == ["src/eidp/cli.py"]
    assert "non-doc changes" in result["error"]


def test_verify_package_source_commit_allow_stale_still_rejects_dirty_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: True)

    result = module.verify_package_source_commit(package, allow_stale_package=True)

    assert result["ok"] is False
    assert result["stale"] is True
    assert result["source_dirty"] is True
    assert result["error"] == "current source tree has uncommitted tracked changes"


def test_verify_package_source_commit_rejects_dirty_tracked_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "eidp-windows.zip"
    commit = "a" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: True)

    result = module.verify_package_source_commit(package)

    assert result["ok"] is False
    assert result["source_dirty"] is True
    assert result["error"] == "current source tree has uncommitted tracked changes"


def test_verify_package_source_commit_rejects_unknown_package_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ZIP carrying git_commit='unknown' must not bypass commit verification."""
    package = tmp_path / "eidp-windows.zip"
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": "unknown"}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)

    result = module.verify_package_source_commit(package)

    assert result["ok"] is False
    assert result["stale"] is True
    assert result["package_commit"] == "unknown"
    assert result["source_commit"] == source_commit
    assert "unresolved git commit" in result["error"]


def test_verify_package_source_commit_rejects_unknown_source_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source tree with no resolvable HEAD must not bypass verification either."""
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr(
            "BUILD_INFO.json",
            json.dumps({"git_commit": package_commit}),
        )
    monkeypatch.setattr(module, "_current_git_commit", lambda: "unknown")
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)

    result = module.verify_package_source_commit(package)

    assert result["ok"] is False
    assert result["stale"] is True
    assert result["package_commit"] == package_commit
    assert result["source_commit"] == "unknown"
    assert "unresolved git commit" in result["error"]


def test_verify_package_source_commit_unknown_still_overridable_for_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """allow_stale_package remains the explicit override even for unknown markers,
    so audited historical replays still work."""
    package = tmp_path / "eidp-windows.zip"
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("BUILD_INFO.json", json.dumps({"git_commit": "unknown"}))
    monkeypatch.setattr(module, "_current_git_commit", lambda: "b" * 40)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)

    result = module.verify_package_source_commit(package, allow_stale_package=True)

    assert result["ok"] is True
    assert result["stale"] is True
    assert result["package_commit"] == "unknown"


def test_current_git_dirty_ignores_untracked_files(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[0] == ("git", "status", "--porcelain", "--untracked-files=no")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._current_git_dirty() is False


def test_main_stops_before_gates_when_package_commit_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("BUILD_INFO.json", json.dumps({"git_commit": package_commit}))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".zip.sha256").write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    output = tmp_path / "summary.json"

    def fail_run_gates(*args: object, **kwargs: object) -> list[object]:
        raise AssertionError("stale packages must fail before running gates")

    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(module, "run_gates", fail_run_gates)

    rc = module.main([str(package), "--skip-full-unit", "--json", "--output", str(output)])

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 1
    assert summary["ok"] is False
    assert summary["package_source_check"]["ok"] is False
    assert summary["package_source_check"]["stale"] is True
    assert summary["results"] == []


def test_main_allows_stale_package_when_explicitly_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("BUILD_INFO.json", json.dumps({"git_commit": package_commit}))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".zip.sha256").write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    output = tmp_path / "summary.json"

    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(module, "run_gates", lambda *args, **kwargs: [])

    rc = module.main(
        [
            str(package),
            "--skip-full-unit",
            "--allow-stale-package",
            "--json",
            "--output",
            str(output),
        ]
    )

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 0
    assert summary["ok"] is True
    assert summary["package_source_check"] == {
        "ok": True,
        "package_commit": package_commit,
        "source_commit": source_commit,
        "source_dirty": False,
        "stale": True,
    }


def test_main_allows_docs_only_stale_package_when_explicitly_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "eidp-windows.zip"
    package_commit = "a" * 40
    source_commit = "b" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("BUILD_INFO.json", json.dumps({"git_commit": package_commit}))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".zip.sha256").write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    output = tmp_path / "summary.json"

    monkeypatch.setattr(module, "_current_git_commit", lambda: source_commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(
        module,
        "_docs_only_stale_check",
        lambda base, head: {
            "ok": True,
            "changed_paths": ["docs/reports/current-release-status.md"],
        },
    )
    monkeypatch.setattr(module, "run_gates", lambda *args, **kwargs: [])

    rc = module.main(
        [
            str(package),
            "--skip-full-unit",
            "--allow-docs-only-stale-package",
            "--json",
            "--output",
            str(output),
        ]
    )

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 0
    assert summary["ok"] is True
    assert summary["package_source_check"]["ok"] is True
    assert summary["package_source_check"]["stale"] is True
    assert summary["package_source_check"]["docs_only_stale"] is True
    assert summary["package_source_check"]["allowed_stale_reason"] == "docs_only"


def test_main_adds_retroactive_excel_gate_when_reference_is_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "eidp-windows.zip"
    commit = "a" * 40
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("BUILD_INFO.json", json.dumps({"git_commit": commit}))
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(".zip.sha256").write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    reference = tmp_path / "reference.xlsx"
    reference.write_bytes(b"PK fake")
    master = tmp_path / "master.xlsx"
    master.write_bytes(b"PK fake")
    app_root = tmp_path / "retroactive-root"
    output = tmp_path / "summary.json"
    captured_commands: list[object] = []

    def fake_run_gates(commands: list[object], **kwargs: object) -> list[object]:
        captured_commands.extend(commands)
        return []

    monkeypatch.setattr(module, "_current_git_commit", lambda: commit)
    monkeypatch.setattr(module, "_current_git_dirty", lambda: False)
    monkeypatch.setattr(module, "run_gates", fake_run_gates)

    rc = module.main(
        [
            str(package),
            "--skip-full-unit",
            "--retroactive-excel-reference",
            str(reference),
            "--retroactive-master",
            str(master),
            "--retroactive-numeric-tolerance",
            "1e-9",
            "--retroactive-app-root",
            str(app_root),
            "--json",
            "--output",
            str(output),
        ]
    )

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 0
    assert summary["retroactive_excel_gate"] == {
        "enabled": True,
        "app_root": str(app_root),
        "fiscal_year": 2025,
        "master_xlsx": str(master),
        "reference_xlsx": str(reference),
        "numeric_tolerance": 1e-9,
    }
    assert [command.name for command in captured_commands][-5:] == [
        "retroactive_excel_prepare",
        "retroactive_excel_db_bootstrap",
        "retroactive_excel_import",
        "retroactive_excel_export",
        "retroactive_excel_diff_reference",
    ]
    diff_command = captured_commands[-1].command
    assert "--numeric-tolerance" in diff_command
    assert diff_command[diff_command.index("--numeric-tolerance") + 1] == "1e-09"


def test_text_summary_prints_package_source_check_error(capsys: pytest.CaptureFixture[str]) -> None:
    module._print_text_summary(
        {
            "package_zip": "dist/eidp-windows.zip",
            "sha256_check": {"ok": True},
            "package_source_check": {
                "ok": False,
                "error": "package BUILD_INFO git_commit abc does not match current source HEAD def",
            },
            "results": [],
        }
    )

    output = capsys.readouterr().out
    assert "package_source_check_ok: False" in output
    assert "package BUILD_INFO git_commit abc does not match current source HEAD def" in output


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
