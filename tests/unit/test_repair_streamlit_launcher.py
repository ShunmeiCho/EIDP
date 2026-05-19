from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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
