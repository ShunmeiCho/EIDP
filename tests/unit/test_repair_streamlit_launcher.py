from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "repair_streamlit_launcher.py"
    spec = importlib.util.spec_from_file_location("repair_streamlit_launcher", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_launcher(root: Path, body: str) -> Path:
    launch_bat = root / "scripts" / "launch.bat"
    launch_bat.parent.mkdir(parents=True)
    launch_bat.write_text(body, encoding="utf-8")
    return launch_bat


def test_repair_streamlit_launcher_dry_run_does_not_write(tmp_path: Path) -> None:
    module = _load_module()
    launch_bat = _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit.main run ^\n')

    result = module.repair_launcher(tmp_path, apply=False)

    assert result["ok"] is True
    assert result["would_update"] is True
    assert result["applied"] is False
    assert "-m streamlit.main run" in launch_bat.read_text(encoding="utf-8")


def test_repair_streamlit_launcher_apply_rewrites_and_keeps_backup(tmp_path: Path) -> None:
    module = _load_module()
    launch_bat = _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit.main run ^\n')

    result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is True
    assert result["applied"] is True
    assert result["backup"] is not None
    assert Path(result["backup"]).is_file()
    body = launch_bat.read_text(encoding="utf-8")
    assert "-m streamlit run" in body
    assert "streamlit.main" not in body


def test_repair_streamlit_launcher_accepts_current_launcher(tmp_path: Path) -> None:
    module = _load_module()
    _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit run ^\n')

    result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is True
    assert result["would_update"] is False
    assert result["applied"] is False


def test_repair_streamlit_launcher_cli_emits_json(tmp_path: Path, capsys) -> None:
    module = _load_module()
    _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit.main run ^\n')

    rc = module.main([str(tmp_path), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["would_update"] is True
    assert payload["applied"] is False


def test_repair_streamlit_launcher_rejects_symlink_escape(tmp_path: Path) -> None:
    module = _load_module()
    outside = tmp_path.parent / f"{tmp_path.name}-outside-launch.bat"
    outside.write_text('"outside" -m streamlit.main run ^\n', encoding="utf-8")
    launch_bat = tmp_path / "scripts" / "launch.bat"
    launch_bat.parent.mkdir(parents=True)
    try:
        launch_bat.symlink_to(outside)
    except OSError as exc:  # pragma: no cover - platform/filesystem dependent
        pytest.skip(f"symlink unavailable: {exc}")

    result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is False
    assert result["applied"] is False
    assert any("must not be a symlink" in error for error in result["errors"])
    assert "streamlit.main" in outside.read_text(encoding="utf-8")


def test_repair_streamlit_launcher_refuses_backup_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    launch_bat = _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit.main run ^\n')
    backup = tmp_path / "scripts" / "launch.bat.collision.bak"
    backup.write_text("existing backup", encoding="utf-8")
    monkeypatch.setattr(module, "_unique_backup_path", lambda _path: backup)

    result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is False
    assert result["applied"] is False
    assert any("backup already exists" in error for error in result["errors"])
    assert "streamlit.main" in launch_bat.read_text(encoding="utf-8")


def test_repair_streamlit_launcher_respects_app_lock(tmp_path: Path) -> None:
    module = _load_module()
    launch_bat = _write_launcher(tmp_path, '"%VENV_PY%" -m streamlit.main run ^\n')

    from eidp.db.locking import acquire_lock

    with acquire_lock(tmp_path / "data" / ".lock", owner="weekly_runner"):
        result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is False
    assert result["applied"] is False
    assert any("could not acquire EIDP app lock" in error for error in result["errors"])
    assert "streamlit.main" in launch_bat.read_text(encoding="utf-8")


def test_repair_streamlit_launcher_revalidates_write_and_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    original = '"%VENV_PY%" -m streamlit.main run ^\n'
    launch_bat = _write_launcher(tmp_path, original)
    real_write = module._write_text_atomic
    corrupted_once = False

    def corrupt_first_launcher_write(path: Path, text: str) -> None:
        nonlocal corrupted_once
        if path == launch_bat.resolve(strict=True) and not corrupted_once:
            corrupted_once = True
            real_write(path, "corrupted launcher body\n")
            return
        real_write(path, text)

    monkeypatch.setattr(module, "_write_text_atomic", corrupt_first_launcher_write)

    result = module.repair_launcher(tmp_path, apply=True)

    assert result["ok"] is False
    assert result["applied"] is False
    assert result["backup"] is not None
    assert any("post-repair validation failed" in error for error in result["errors"])
    assert launch_bat.read_text(encoding="utf-8") == original
