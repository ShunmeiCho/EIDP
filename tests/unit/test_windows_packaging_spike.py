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
    """Read all four launcher scripts once."""
    out: dict[str, str] = {}
    for name in ("first_setup.bat", "launch.bat", "weekly_run.bat", "uninstall.bat"):
        path = SCRIPTS_DIR / name
        out[name] = path.read_text(encoding="utf-8")
    return out


def test_bat_skeletons_all_present(bat_files: dict[str, str]):
    assert set(bat_files.keys()) == {
        "first_setup.bat", "launch.bat", "weekly_run.bat", "uninstall.bat"
    }


@pytest.mark.parametrize("name", ["first_setup.bat", "launch.bat", "weekly_run.bat"])
def test_bat_anchors_cwd_to_app_root(bat_files: dict[str, str], name: str):
    """All write-capable launchers MUST cd to the script parent so
    EIDP_APP_ROOT is anchored regardless of who invoked them
    (Explorer, Task Scheduler, terminal). Owner ruled this in v6
    Constraint #1."""
    body = bat_files[name]
    assert 'cd /d "%~dp0\\.."' in body, f"{name} must anchor cwd via cd /d %~dp0\\.."
    assert 'set "EIDP_APP_ROOT=%CD%"' in body, f"{name} must export EIDP_APP_ROOT"


@pytest.mark.parametrize("name", ["launch.bat", "weekly_run.bat"])
def test_long_running_bat_forces_utf8(bat_files: dict[str, str], name: str):
    """Streamlit logs and run_r8_rediscovery_weekly print Japanese.
    Default Windows console is cp932 in JP, which corrupts text and
    breaks downstream log scrapers. v6 Constraint #6 mandates UTF-8."""
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
