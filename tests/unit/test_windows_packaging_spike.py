"""Sprint 8.5.a — Mac-side packaging guards.

These tests prove the wheelhouse rejection logic works and that the
``.bat`` skeletons obey the contract owners care about (cwd anchoring
via ``cd /d "%~dp0\\.."``, ``EIDP_APP_ROOT`` exported, UTF-8 forced
for the launcher and weekly runner).

We deliberately do NOT try to execute any ``.bat`` from Mac — that is
Sprint 8.5.b (Windows VM offline validation). Mac side proves the
asset is well-formed; Windows side proves it actually runs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_build_script():
    spec = importlib.util.spec_from_file_location(
        "build_windows_zip", SCRIPTS_DIR / "build_windows_zip.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Wheelhouse verification
# ---------------------------------------------------------------------------


def _make_empty_wheel(path: Path) -> None:
    path.write_bytes(b"")


def test_verify_wheelhouse_accepts_cp312_win_amd64(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp312-cp312-win_amd64.whl")
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")

    accepted = bw.verify_wheelhouse(wh)
    assert {p.name for p in accepted} == {
        "pymupdf-1.25.0-cp312-cp312-win_amd64.whl",
        "structlog-25.0.0-py3-none-any.whl",
    }


def test_verify_wheelhouse_accepts_abi3_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "cryptography-44.0.0-cp312-abi3-win_amd64.whl")
    accepted = bw.verify_wheelhouse(wh)
    assert len(accepted) == 1


def test_verify_wheelhouse_rejects_macosx_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp312-cp312-macosx_11_0_arm64.whl")
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")

    with pytest.raises(bw.WheelhouseError, match="cp312/win_amd64"):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_cp311_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp311-cp311-win_amd64.whl")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_linux_manylinux(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "psycopg2_binary-2.9-cp312-cp312-manylinux_2_17_x86_64.whl")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_unexpected_files(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")
    (wh / "stray.txt").write_text("oops", encoding="utf-8")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_empty_directory(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    with pytest.raises(bw.WheelhouseError, match="empty"):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_missing_directory(tmp_path: Path):
    bw = _load_build_script()
    with pytest.raises(bw.WheelhouseError, match="does not exist"):
        bw.verify_wheelhouse(tmp_path / "nope")


def test_accepted_wheel_suffixes_includes_pure_python(tmp_path: Path):
    """py3-none-any and py2.py3-none-any must both be accepted because
    requirements-windows.txt includes pure-Python deps like structlog
    and tenacity."""
    bw = _load_build_script()
    assert "-py3-none-any.whl" in bw.ACCEPTED_WHEEL_SUFFIXES
    assert "-py2.py3-none-any.whl" in bw.ACCEPTED_WHEEL_SUFFIXES


# ---------------------------------------------------------------------------
# .bat skeleton static review
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bat_files() -> dict[str, str]:
    """Read all Windows launcher / utility scripts once."""
    out: dict[str, str] = {}
    for name in ("first_setup.bat", "launch.bat", "weekly_run.bat", "uninstall.bat", "validate_install.bat"):
        path = SCRIPTS_DIR / name
        out[name] = path.read_text(encoding="utf-8")
    return out


def test_bat_skeletons_all_present(bat_files: dict[str, str]):
    assert set(bat_files.keys()) == {
        "first_setup.bat", "launch.bat", "weekly_run.bat", "uninstall.bat", "validate_install.bat",
    }


@pytest.mark.parametrize("name", ["first_setup.bat", "launch.bat", "weekly_run.bat", "validate_install.bat"])
def test_bat_anchors_cwd_to_app_root(bat_files: dict[str, str], name: str):
    """All write-capable launchers MUST cd to the script parent so
    EIDP_APP_ROOT is anchored regardless of who invoked them
    (Explorer, Task Scheduler, terminal). Owner ruled this in v6
    Constraint #1."""
    body = bat_files[name]
    assert 'cd /d "%~dp0\\.."' in body, f"{name} must anchor cwd via cd /d %~dp0\\.."
    assert 'set "EIDP_APP_ROOT=%CD%"' in body, f"{name} must export EIDP_APP_ROOT"


@pytest.mark.parametrize("name", ["first_setup.bat", "launch.bat", "weekly_run.bat", "validate_install.bat"])
def test_python_bat_forces_utf8(bat_files: dict[str, str], name: str):
    """Streamlit logs and run_r8_rediscovery_weekly print Japanese.
    Default Windows console is cp932 in JP, which corrupts text and
    breaks downstream log scrapers. first_setup also runs Python CLI
    commands that may read/write Japanese data. v6 Constraint #6
    mandates UTF-8."""
    body = bat_files[name]
    assert 'PYTHONIOENCODING=utf-8' in body
    assert 'PYTHONUTF8=1' in body


def test_first_setup_bootstraps_db(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert "db-bootstrap --sqlite" in body, (
        "first_setup must call eidp db-bootstrap --sqlite to create "
        "data/eidp.sqlite3 from a clean install"
    )


def test_first_setup_uses_offline_install(bat_files: dict[str, str]):
    """No-network install is the entire reason we ship a wheelhouse."""
    body = bat_files["first_setup.bat"]
    assert "--no-index" in body
    assert "wheelhouse" in body


def test_first_setup_registers_weekly_task(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert "schtasks" in body
    assert "EIDP Weekly Run" in body


def test_uninstall_does_not_delete_data(bat_files: dict[str, str]):
    """Owner data is precious. uninstall.bat must NEVER rmdir data\\."""
    body = bat_files["uninstall.bat"]
    assert "rmdir" not in body.lower()
    assert "del " not in body.lower() or "data" not in body.lower()


# ---------------------------------------------------------------------------
# Sprint 8.5.a.1 — venv + actual CLI command tokens
# ---------------------------------------------------------------------------


def test_first_setup_creates_isolated_venv(bat_files: dict[str, str]):
    """Owner finding 8.5.a P0: install must target an isolated env, not
    rely on the runtime's site-packages."""
    body = bat_files["first_setup.bat"]
    assert "uv.exe" in body, "first_setup must drive uv.exe explicitly"
    assert "venv" in body and ".venv" in body, "first_setup must create .venv"
    assert ".venv\\Scripts\\python.exe" in body, (
        "subsequent commands must run via .venv python so they see the "
        "wheelhouse-installed packages"
    )
    assert "--python" in body, "uv pip install must target the venv via --python"


def test_first_setup_uses_existing_cli_command_for_master(bat_files: dict[str, str]):
    """Owner finding 8.5.a P0: there is no `import-master`. The CLI
    only exposes `import-excel`."""
    body = bat_files["first_setup.bat"]
    assert "import-master" not in body, "import-master is not a real CLI command"
    assert "import-excel" in body, "use eidp import-excel for master.xlsx"


@pytest.mark.parametrize("name", ["launch.bat", "weekly_run.bat"])
def test_runtime_bats_use_venv_python(bat_files: dict[str, str], name: str):
    body = bat_files[name]
    assert ".venv\\Scripts\\python.exe" in body, (
        f"{name} must use the venv python created by first_setup.bat"
    )


def test_weekly_run_uses_locale_safe_datestamp(bat_files: dict[str, str]):
    """Windows %DATE% is locale-dependent (JP console can include
    separators/day text). The log filename must come from a stable date
    formatter, not substring slicing."""
    body = bat_files["weekly_run.bat"]
    assert "Get-Date -Format yyyyMMdd" in body
    assert "%DATE:~" not in body


def test_weekly_run_preserves_python_exit_code_after_endlocal(bat_files: dict[str, str]):
    body = bat_files["weekly_run.bat"]
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_launch_preserves_streamlit_exit_code_after_endlocal(bat_files: dict[str, str]):
    """Delayed expansion is not enabled in launch.bat. Capture the
    Streamlit return code before `endlocal` so Task Scheduler / manual
    runs observe the real failure status instead of a stale expansion."""
    body = bat_files["launch.bat"]
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_validate_install_bat_runs_packaged_validator(bat_files: dict[str, str]):
    """The VM checklist must be runnable from the extracted ZIP without
    a dev checkout or `uv run`. The wrapper chooses .venv after setup,
    falls back to the bundled runtime before setup, forwards all flags,
    and preserves the validator exit code."""
    body = bat_files["validate_install.bat"]
    assert "validate_windows_install.py" in body
    assert ".venv\\Scripts\\python.exe" in body
    assert "runtime\\python\\python.exe" in body
    assert '"%EIDP_APP_ROOT%" %*' in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_first_setup_calls_db_bootstrap_via_python_module(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    # `python -m eidp.cli db-bootstrap --sqlite` is the actual command
    # that exists, not a bare `eidp` invocation that may not be on PATH.
    assert "-m eidp.cli db-bootstrap --sqlite" in body


# ---------------------------------------------------------------------------
# pip download command surface
# ---------------------------------------------------------------------------


def test_download_uses_pip_not_uv(monkeypatch: pytest.MonkeyPatch):
    """Owner finding 8.5.a P0: ``uv pip download`` does not exist.
    download_windows_wheels must shell out to ``python -m pip
    download``."""
    bw = _load_build_script()
    captured: dict[str, list[str]] = {}

    def _stub_run(cmd, check):  # noqa: ANN001
        captured["cmd"] = list(cmd)

        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(bw.subprocess, "run", _stub_run)
    bw.download_windows_wheels(
        requirements=Path("requirements-windows.txt"),
        dest=Path("/tmp/wh-test-stub"),
        python_executable="/usr/bin/fake-python",
    )

    cmd = captured["cmd"]
    # Tokens must include "-m pip download" — owner explicitly required
    # this and it is the smoke test that ran red on 8.5.a.
    assert "-m" in cmd and "pip" in cmd and "download" in cmd
    assert "uv" not in cmd[0:1], "uv is not the entrypoint here"
    # Platform / abi tokens must be carried through.
    assert "--platform" in cmd
    assert "win_amd64" in cmd
    assert "--abi" in cmd
    assert "cp312" in cmd


# ---------------------------------------------------------------------------
# ZIP manifest must include alembic + weekly runner
# ---------------------------------------------------------------------------


def test_collect_zip_members_includes_alembic_and_weekly_runner(tmp_path: Path):
    """Owner finding 8.5.a P0/P1: the ZIP manifest was missing
    alembic.ini, migrations/, and run_r8_rediscovery_weekly.py.
    Recreate a faux repo and assert the new collector picks them up."""
    bw = _load_build_script()

    fake_repo = tmp_path / "repo"
    (fake_repo / "src" / "eidp").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")
    (fake_repo / "scripts").mkdir()
    (fake_repo / "scripts" / "first_setup.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "run_r8_rediscovery_weekly.py").write_text(
        "print('weekly')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "validate_windows_install.py").write_text(
        "print('validate')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "validate_install.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    migrations = fake_repo / "migrations"
    (migrations / "versions").mkdir(parents=True)
    (migrations / "env.py").write_text("# env", encoding="utf-8")
    (migrations / "versions" / "abcd_initial.py").write_text("# rev", encoding="utf-8")
    (fake_repo / "docs" / "runbooks").mkdir(parents=True)
    (fake_repo / "docs" / "runbooks" / "eidp-windows.md").write_text("# runbook", encoding="utf-8")
    (fake_repo / "README.md").write_text("# EIDP", encoding="utf-8")
    (fake_repo / "requirements-windows.txt").write_text("structlog\n", encoding="utf-8")
    (fake_repo / "pyproject.toml").write_text("[project]\nname='eidp'\n", encoding="utf-8")

    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")

    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}

    assert "alembic.ini" in arcs, "alembic.ini must be in the Windows ZIP"
    assert "migrations/env.py" in arcs
    assert "migrations/versions/abcd_initial.py" in arcs
    assert "scripts/run_r8_rediscovery_weekly.py" in arcs, (
        "weekly_run.bat depends on this Python entrypoint"
    )
    assert "scripts/validate_windows_install.py" in arcs, (
        "Windows VM checklist depends on this validation entrypoint"
    )
    assert "scripts/validate_install.bat" in arcs, (
        "Windows VM checklist must run the validator from the extracted ZIP"
    )
    assert "scripts/first_setup.bat" in arcs
    assert "wheelhouse/structlog-25.0.0-py3-none-any.whl" in arcs
    assert "docs/runbooks/eidp-windows.md" in arcs
    assert "README.md" in arcs
    assert "requirements-windows.txt" in arcs


def test_collect_zip_members_skips_pycache(tmp_path: Path):
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    (fake_repo / "src" / "eidp" / "__pycache__").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__pycache__" / "junk.pyc").write_bytes(b"")
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")
    (fake_repo / "migrations" / "__pycache__").mkdir(parents=True)
    (fake_repo / "migrations" / "__pycache__" / "stale.pyc").write_bytes(b"")
    (fake_repo / "migrations" / "env.py").write_text("# env", encoding="utf-8")

    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")

    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}
    assert all("__pycache__" not in a for a in arcs)


# ---------------------------------------------------------------------------
# CLI command existence sanity
# ---------------------------------------------------------------------------


def test_resolve_alembic_ini_prefers_app_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sprint 8.5.a.1 — db-bootstrap must read alembic.ini from
    settings.app_root first so the operator ZIP layout works."""
    from eidp.db import sqlite_bootstrap

    fake_root = tmp_path / "EIDP"
    fake_root.mkdir()
    (fake_root / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")

    class _FakeSettings:
        app_root = fake_root

    import eidp.config as cfg

    monkeypatch.setattr(cfg, "settings", _FakeSettings(), raising=True)
    resolved = sqlite_bootstrap._resolve_alembic_ini()
    assert resolved == fake_root / "alembic.ini"


def test_resolve_alembic_ini_falls_back_to_repo(monkeypatch: pytest.MonkeyPatch):
    """If app_root has no alembic.ini, fallback to the repo source
    layout (parents[3] of sqlite_bootstrap.py)."""
    from eidp.db import sqlite_bootstrap

    class _NoFile:
        app_root = Path("/path/that/does/not/exist")

    import eidp.config as cfg

    monkeypatch.setattr(cfg, "settings", _NoFile(), raising=True)
    resolved = sqlite_bootstrap._resolve_alembic_ini()
    # Must point to a real alembic.ini somewhere in the repo.
    assert resolved.is_file(), f"fallback resolution did not land on a real file: {resolved}"
    assert resolved.name == "alembic.ini"


def test_first_setup_only_uses_existing_cli_subcommands():
    """Static parse first_setup.bat for ``-m eidp.cli <name>`` tokens
    and assert each name is exposed by the actual CLI. Prevents future
    drift — if someone removes a CLI subcommand the .bat will fail
    here before it fails on a Windows VM."""
    body = (SCRIPTS_DIR / "first_setup.bat").read_text(encoding="utf-8")
    import re

    used = set(re.findall(r"-m eidp\.cli\s+([a-z][a-z0-9-]+)", body))
    assert used, "first_setup.bat must invoke at least one eidp.cli subcommand"

    from eidp.cli import app

    # typer derives the CLI command name from the callback function
    # name, mapping underscores to hyphens. Use the same transform here.
    registered: set[str] = set()
    for cmd in app.registered_commands:
        if cmd.name:
            registered.add(cmd.name)
        elif cmd.callback is not None:
            registered.add(cmd.callback.__name__.replace("_", "-"))
    missing = used - registered
    assert not missing, f"first_setup.bat references unknown CLI commands: {missing}"
