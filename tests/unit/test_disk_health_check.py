from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "disk_health_check.py"
spec = importlib.util.spec_from_file_location("disk_health_check", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _touch(path: Path, size: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_evaluate_target_reports_warn_and_block_thresholds(tmp_path: Path) -> None:
    _touch(tmp_path / "dist" / "eidp-windows-v999.zip", 21)
    target = module.DiskTarget(
        "dist",
        Path("dist"),
        warn_bytes=10,
        block_bytes=20,
        cleanup_hint="prune",
    )

    entry = module.evaluate_target(tmp_path, target)

    assert entry["status"] == "block"
    assert entry["bytes"] == 21
    assert entry["cleanup_hint"] == "prune"


def test_evaluate_profile_marks_protected_data_without_deleting(tmp_path: Path) -> None:
    _touch(tmp_path / "data" / "eidp.sqlite3", 11)
    _touch(tmp_path / "data" / "master.xlsx", 13)

    summary = module.evaluate_profile(tmp_path, "mac-dev")

    data_entry = next(entry for entry in summary["entries"] if entry["name"] == "data")
    assert data_entry["protected"] is True
    assert "never delete" in data_entry["cleanup_hint"]
    assert (tmp_path / "data" / "eidp.sqlite3").exists()
    assert (tmp_path / "data" / "master.xlsx").exists()


def test_operator_profile_covers_pdf_output_logs_and_audit_paths(tmp_path: Path) -> None:
    names = {entry["name"] for entry in module.evaluate_profile(tmp_path, "operator-win")["entries"]}

    assert {
        "app_root_total",
        "data/pdfs",
        "data/output",
        "logs",
        "data/audit/manual-actions.jsonl",
    } <= names


def test_main_can_fail_on_warn(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    _touch(tmp_path / "logs" / "run.log", 6)
    original_targets = module.PROFILES["mac-dev"]

    try:
        module.PROFILES["mac-dev"] = lambda: (
            module.DiskTarget("logs", Path("logs"), warn_bytes=5, block_bytes=10),
        )
        rc = module.main(["--root", str(tmp_path), "--profile", "mac-dev", "--fail-on-warn"])
    finally:
        module.PROFILES["mac-dev"] = original_targets

    assert rc == 1
    assert "warn=1" in capsys.readouterr().out
