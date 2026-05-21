from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path

import pytest


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "stage6_recovery_check.py"
    spec = importlib.util.spec_from_file_location("stage6_recovery_check", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_task_xml_reads_namespaced_exec_action() -> None:
    module = _load_module()
    xml = """<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Actions Context="Author">
    <Exec>
      <Command>C:\\Users\\eidp_operator\\EIDP-v380-f6a5e6d\\scripts\\weekly_run.bat</Command>
      <Arguments></Arguments>
    </Exec>
  </Actions>
</Task>
"""

    task = module.parse_task_xml(xml)

    assert task.exists is True
    assert task.execute == r"C:\Users\eidp_operator\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"
    assert task.arguments is None


def test_decode_process_output_accepts_utf16_xml() -> None:
    module = _load_module()
    xml = "<?xml version=\"1.0\" encoding=\"UTF-16\"?><Task />"

    assert module._decode_process_output(xml.encode("utf-16")) == xml


def test_decode_process_output_accepts_ascii_xml_mislabelled_as_utf16() -> None:
    module = _load_module()
    xml = "<?xml version=\"1.0\" encoding=\"UTF-16\"?>\r\r\n<Task />"

    assert module._decode_process_output(xml.encode("utf-8")) == xml


def test_build_report_passes_when_task_matches_and_no_residuals(tmp_path: Path) -> None:
    module = _load_module()
    expected = r"C:\Users\eidp_operator\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"
    task = module.ScheduledTaskSnapshot(exists=True, execute=expected)

    report = module.build_report(
        expected_weekly_action=expected.replace("\\", "/"),
        check_paths=[str(tmp_path / "missing-sandbox")],
        task=task,
    )

    assert report["ok"] is True
    assert report["task"]["action_matches_expected"] is True
    assert report["residual_paths"] == [{"path": str(tmp_path / "missing-sandbox"), "exists": False}]


def test_build_report_flags_task_mismatch_and_residual_paths(tmp_path: Path) -> None:
    module = _load_module()
    residual = tmp_path / "EIDP-v384-75732b0-ocr-sr-sandbox"
    residual.mkdir()
    task = module.ScheduledTaskSnapshot(
        exists=True,
        execute=r"C:\Users\eidp_operator\EIDP-v384-75732b0-ocr-sr-sandbox\scripts\weekly_run.bat",
    )

    report = module.build_report(
        expected_weekly_action=r"C:\Users\eidp_operator\EIDP-v380-f6a5e6d\scripts\weekly_run.bat",
        check_paths=[str(residual)],
        task=task,
    )

    assert report["ok"] is False
    assert report["task"]["action_matches_expected"] is False
    assert report["residual_paths"] == [{"path": str(residual), "exists": True}]
    assert "Restore EIDP Weekly Run" in " ".join(report["recommendations"])
    assert "interrupted smoke artifacts" in " ".join(report["recommendations"])


def test_build_report_skips_expected_weekly_action_when_not_provided(tmp_path: Path) -> None:
    module = _load_module()
    task = module.ScheduledTaskSnapshot(
        exists=True,
        execute=r"C:\Users\eidp_operator\EIDP-v380-f6a5e6d\scripts\weekly_run.bat",
    )

    report = module.build_report(
        expected_weekly_action=None,
        check_paths=[str(tmp_path / "missing-sandbox")],
        task=task,
    )

    assert report["ok"] is True
    assert report["task"]["expected_action"] is None
    assert report["task"]["action_matches_expected"] is None
    assert "Scheduled task action check skipped" in " ".join(report["recommendations"])


def test_build_report_runs_weekly_dry_run_probe_when_requested(tmp_path: Path) -> None:
    module = _load_module()
    expected = str(tmp_path / "weekly_run.bat")
    Path(expected).write_text("@echo off\n", encoding="utf-8")
    seen: list[tuple[str, float]] = []
    task = module.ScheduledTaskSnapshot(exists=True, execute=expected)

    def fake_weekly_probe(path: str, *, timeout_seconds: float) -> dict[str, object]:
        seen.append((path, timeout_seconds))
        return {
            "enabled": True,
            "ok": True,
            "path": path,
            "returncode": 0,
            "timeout_seconds": timeout_seconds,
        }

    report = module.build_report(
        expected_weekly_action=expected,
        check_paths=[str(tmp_path / "missing-sandbox")],
        task=task,
        probe_weekly_dry_run=True,
        weekly_probe_timeout_seconds=12.5,
        weekly_probe_runner=fake_weekly_probe,
    )

    assert report["ok"] is True
    assert seen == [(expected, 12.5)]
    assert report["weekly_dry_run_probe"]["ok"] is True


def test_build_report_fails_when_weekly_dry_run_probe_fails(tmp_path: Path) -> None:
    module = _load_module()
    expected = str(tmp_path / "weekly_run.bat")
    Path(expected).write_text("@echo off\n", encoding="utf-8")
    task = module.ScheduledTaskSnapshot(exists=True, execute=expected)

    report = module.build_report(
        expected_weekly_action=expected,
        check_paths=[str(tmp_path / "missing-sandbox")],
        task=task,
        probe_weekly_dry_run=True,
        weekly_probe_runner=lambda _path, *, timeout_seconds: {
            "enabled": True,
            "ok": False,
            "path": _path,
            "returncode": 2,
            "timeout_seconds": timeout_seconds,
            "stderr_tail": "venv not found",
        },
    )

    assert report["ok"] is False
    assert report["weekly_dry_run_probe"]["returncode"] == 2
    assert "weekly_run.bat dry-run probe failed" in " ".join(report["recommendations"])


def test_weekly_probe_command_quotes_windows_batch_path(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module.os, "name", "nt")

    assert module._weekly_probe_command(r"C:\Users\operator\EIDP\scripts\weekly_run.bat") == [
        "cmd.exe",
        "/D",
        "/C",
        r'call "C:\Users\operator\EIDP\scripts\weekly_run.bat"',
    ]


def test_weekly_probe_command_rejects_windows_shell_metacharacters(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module.os, "name", "nt")

    with pytest.raises(ValueError, match="unsafe cmd.exe metacharacters"):
        module._weekly_probe_command(r"C:\Users\operator\EIDP\scripts\weekly_run.bat & calc.exe")


def test_build_report_fails_when_lock_probe_reports_held(tmp_path: Path) -> None:
    module = _load_module()
    expected = r"C:\Users\eidp_operator\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"
    task = module.ScheduledTaskSnapshot(exists=True, execute=expected)

    report = module.build_report(
        expected_weekly_action=expected,
        check_paths=[str(tmp_path / "missing-sandbox")],
        task=task,
        probe_lock=True,
        lock_probe_runner=lambda _path: {
            "enabled": True,
            "ok": False,
            "path": _path,
            "held": True,
            "owner": "weekly_runner",
        },
    )

    assert report["ok"] is False
    assert report["lock_probe"]["held"] is True
    assert "Wait for the current EIDP operation" in " ".join(report["recommendations"])


def test_direct_script_disables_wmi_platform_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "_wmi_query", lambda *_args, **_kwargs: [], raising=False)

    _load_module()

    with pytest.raises(OSError, match="WMI disabled"):
        platform._wmi_query("Win32_OperatingSystem", (), ())  # type: ignore[attr-defined]
