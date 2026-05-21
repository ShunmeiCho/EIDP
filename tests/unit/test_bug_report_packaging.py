from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_build_windows_zip() -> ModuleType:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "build_windows_zip_bug_report_test",
        SCRIPTS_DIR / "build_windows_zip.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_collect_bug_report_bat_runs_packaged_helper() -> None:
    body = (SCRIPTS_DIR / "collect_bug_report.bat").read_text(encoding="utf-8")

    assert "collect_bug_report.py" in body
    assert '--root "%EIDP_APP_ROOT%"' in body
    assert ".venv\\Scripts\\python.exe" in body
    assert "runtime\\python\\python.exe" in body
    assert "[collect_bug_report] ERROR: no Python found" in body
    assert "exit /b %ERRORLEVEL%" in body


def test_windows_zip_members_include_bug_report_scripts(tmp_path: Path) -> None:
    build_windows_zip = _load_build_windows_zip()
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    wheelhouse = tmp_path / "wheelhouse"
    scripts_dir.mkdir(parents=True)
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"wheel")
    (scripts_dir / "collect_bug_report.bat").write_text("@echo off\n", encoding="utf-8")
    (scripts_dir / "collect_bug_report.py").write_text("print('bundle')\n", encoding="utf-8")

    arcs = {
        arcname
        for _source, arcname in build_windows_zip.collect_zip_members(repo_root=repo_root, wheelhouse=wheelhouse)
    }

    assert "scripts/collect_bug_report.bat" in arcs
    assert "scripts/collect_bug_report.py" in arcs
