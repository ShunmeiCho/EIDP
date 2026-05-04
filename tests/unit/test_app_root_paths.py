"""Sprint 8.5.a — application root resolution.

The fallback chain is the difference between "works on operator PC"
and "Streamlit launches with cwd=C:\\Windows\\System32 because Task
Scheduler". Lock the three paths and verify the last resort never
returns a site-packages directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eidp.config import resolve_app_root


def test_resolve_app_root_uses_env_when_set(tmp_path: Path):
    target = tmp_path / "EIDP"
    target.mkdir()
    resolved = resolve_app_root(env={"EIDP_APP_ROOT": str(target)}, cwd=tmp_path / "elsewhere")
    assert resolved == target.resolve()


def test_resolve_app_root_expands_user_in_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    fake_home_target = tmp_path / "EIDP-home"
    fake_home_target.mkdir()
    resolved = resolve_app_root(
        env={"EIDP_APP_ROOT": "~/EIDP-home"},
        cwd=tmp_path / "irrelevant",
    )
    assert resolved == fake_home_target.resolve()


def test_resolve_app_root_uses_cwd_when_marker_present(tmp_path: Path):
    """If cwd looks like an app root (data/ or .env or pyproject.toml),
    we trust it. This is what happens when launcher.bat does
    ``cd /d "%~dp0\\..\"`` and there's no env override."""
    cwd = tmp_path / "EIDP"
    cwd.mkdir()
    (cwd / "data").mkdir()  # marker
    resolved = resolve_app_root(env={}, cwd=cwd)
    assert resolved == cwd.resolve()


def test_resolve_app_root_uses_cwd_when_dotenv_marker(tmp_path: Path):
    cwd = tmp_path / "EIDP"
    cwd.mkdir()
    (cwd / ".env").write_text("EIDP_APP_ROOT=ignored", encoding="utf-8")
    resolved = resolve_app_root(env={}, cwd=cwd)
    assert resolved == cwd.resolve()


def test_resolve_app_root_falls_back_to_repo_when_cwd_empty(tmp_path: Path):
    """When neither env nor cwd marker exists, last resort is
    ``parents[2]`` of config.py. In a source checkout this is the repo
    root. We assert it points at the repo containing ``pyproject.toml``."""
    blank = tmp_path / "blank"
    blank.mkdir()
    resolved = resolve_app_root(env={}, cwd=blank)
    assert (resolved / "pyproject.toml").is_file(), (
        f"fallback should point at repo root with pyproject.toml; got {resolved}"
    )


def test_resolve_app_root_fallback_is_not_site_packages(tmp_path: Path):
    """The last-resort fallback must never resolve under site-packages,
    because in that case data/eidp.sqlite3 would land beside installed
    code instead of beside the user's data."""
    blank = tmp_path / "blank"
    blank.mkdir()
    resolved = resolve_app_root(env={}, cwd=blank)
    assert "site-packages" not in str(resolved), (
        f"app root must not fall back to site-packages: {resolved}"
    )


def test_resolve_app_root_priority_env_beats_cwd(tmp_path: Path):
    """Env wins over cwd marker."""
    env_root = tmp_path / "from-env"
    env_root.mkdir()
    cwd_root = tmp_path / "from-cwd"
    cwd_root.mkdir()
    (cwd_root / "data").mkdir()
    resolved = resolve_app_root(env={"EIDP_APP_ROOT": str(env_root)}, cwd=cwd_root)
    assert resolved == env_root.resolve()
