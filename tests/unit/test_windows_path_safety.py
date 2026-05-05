"""Windows path safety checks for repo paths and distribution ZIP entries."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_windows_path_safety_accepts_normal_repo_paths() -> None:
    safety = _load("windows_path_safety")

    issues = safety.check_windows_safe_paths(
        [
            "src/eidp/review/app.py",
            "docs/runbooks/eidp-windows.md",
            "scripts/weekly_run.bat",
        ]
    )

    assert issues == []


def test_windows_path_safety_detects_case_collision() -> None:
    safety = _load("windows_path_safety")

    issues = safety.check_windows_safe_paths(["docs/Readme.md", "docs/README.md"])

    assert [issue.kind for issue in issues] == ["case-collision"]
    assert "collides with" in issues[0].detail


def test_windows_path_safety_detects_reserved_names_even_with_extension() -> None:
    safety = _load("windows_path_safety")

    issues = safety.check_windows_safe_paths(["docs/runbooks/CON.txt"])

    assert [issue.kind for issue in issues] == ["reserved-name"]


def test_windows_path_safety_detects_parent_absolute_and_trailing_components() -> None:
    safety = _load("windows_path_safety")

    issues = safety.check_windows_safe_paths(
        [
            "../escape.txt",
            "/absolute/path.txt",
            "docs/bad./file.txt",
            "C:/absolute/windows.txt",
        ]
    )
    kinds = {issue.kind for issue in issues}

    assert {"parent-directory", "absolute-path", "trailing-dot-space"} <= kinds


def test_check_windows_paths_cli_accepts_explicit_paths(capsys) -> None:  # noqa: ANN001
    checker = _load("check_windows_paths")

    rc = checker.main(["docs/runbooks/eidp-windows.md"])

    assert rc == 0
    assert "OK: all paths are Windows-safe" in capsys.readouterr().out


def test_check_windows_paths_cli_json_reports_issues(capsys) -> None:  # noqa: ANN001
    checker = _load("check_windows_paths")

    rc = checker.main(["docs/PRN.md", "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["kind"] == "reserved-name"
