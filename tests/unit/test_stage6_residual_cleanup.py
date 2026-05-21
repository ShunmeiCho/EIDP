from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_module() -> Any:
    script = Path(__file__).resolve().parents[2] / "scripts" / "stage6_residual_cleanup.py"
    script_dir = str(script.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("stage6_residual_cleanup", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cleanup_residuals_dry_run_reports_existing_without_moving(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    residual = tmp_path / "eidp-windows-v384.zip"
    residual.write_text("zip", encoding="utf-8")

    report = module.cleanup_residuals(
        app_root=tmp_path / "app",
        check_paths=[r"%USERPROFILE%\eidp-windows-v384.zip"],
        archive_dir=tmp_path / "archive",
        apply=False,
    )

    assert report["ok"] is False
    assert report["mode"] == "dry_run"
    assert report["existing_count"] == 1
    assert report["moved_count"] == 0
    assert residual.exists()
    assert report["actions"][0]["destination"] == str(tmp_path / "archive" / "eidp-windows-v384.zip")


def test_cleanup_residuals_apply_moves_file_and_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    residual_file = tmp_path / "eidp-windows-v384.zip"
    residual_file.write_text("zip", encoding="utf-8")
    residual_dir = tmp_path / "EIDP-v384-75732b0-ocr-sr-sandbox"
    residual_dir.mkdir()
    (residual_dir / "marker.txt").write_text("marker", encoding="utf-8")

    report = module.cleanup_residuals(
        app_root=tmp_path / "app",
        check_paths=[
            r"%USERPROFILE%\eidp-windows-v384.zip",
            r"%USERPROFILE%\EIDP-v384-75732b0-ocr-sr-sandbox",
        ],
        archive_dir=tmp_path / "archive",
        apply=True,
    )

    assert report["ok"] is True
    assert report["mode"] == "apply"
    assert report["existing_count"] == 0
    assert report["moved_count"] == 2
    assert not residual_file.exists()
    assert not residual_dir.exists()
    assert (tmp_path / "archive" / "eidp-windows-v384.zip").read_text(encoding="utf-8") == "zip"
    assert (tmp_path / "archive" / "EIDP-v384-75732b0-ocr-sr-sandbox" / "marker.txt").exists()


def test_cleanup_residuals_refuses_outside_userprofile_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    user_profile = tmp_path / "user"
    user_profile.mkdir()
    monkeypatch.setenv("USERPROFILE", str(user_profile))
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")

    report = module.cleanup_residuals(
        app_root=tmp_path / "app",
        check_paths=[str(outside)],
        archive_dir=tmp_path / "archive",
        apply=True,
    )

    assert report["ok"] is False
    assert report["existing_count"] == 1
    assert report["actions"][0]["error"] == "refusing to move path outside USERPROFILE"
    assert outside.exists()


def test_cleanup_residuals_refuses_symlink_without_following_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    target = tmp_path / "Documents"
    target.mkdir()
    (target / "private.txt").write_text("keep", encoding="utf-8")
    residual_link = tmp_path / "EIDP-v384-75732b0-ocr-sr-sandbox"
    residual_link.symlink_to(target, target_is_directory=True)

    report = module.cleanup_residuals(
        app_root=tmp_path / "app",
        check_paths=[str(residual_link)],
        archive_dir=tmp_path / "archive",
        apply=True,
    )

    assert report["ok"] is False
    assert report["existing_count"] == 1
    assert report["moved_count"] == 0
    assert report["actions"][0]["error"] == "refusing to move symlink or junction"
    assert residual_link.is_symlink()
    assert (target / "private.txt").read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / "archive" / "EIDP-v384-75732b0-ocr-sr-sandbox").exists()


@pytest.mark.parametrize("filename", ["eidp.sqlite3", "manual-actions.jsonl", "master.xlsx"])
def test_cleanup_residuals_refuses_protected_runtime_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    module = _load_module()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    protected = tmp_path / filename
    protected.write_text("keep", encoding="utf-8")

    report = module.cleanup_residuals(
        app_root=tmp_path / "app",
        check_paths=[str(protected)],
        archive_dir=tmp_path / "archive",
        apply=True,
    )

    assert report["ok"] is False
    assert report["existing_count"] == 1
    assert report["moved_count"] == 0
    assert report["actions"][0]["error"] == "refusing to move protected runtime file"
    assert protected.read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / "archive" / filename).exists()


def test_write_cleanup_log_records_json(tmp_path: Path) -> None:
    module = _load_module()
    report = {"ok": True, "actions": []}

    log_path = module.write_cleanup_log(tmp_path, report)

    assert log_path.name.startswith("stage6-residual-cleanup-")
    assert '"ok": true' in log_path.read_text(encoding="utf-8")
