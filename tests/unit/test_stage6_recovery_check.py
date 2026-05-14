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
      <Command>C:\\Users\\cyo20\\EIDP-v380-f6a5e6d\\scripts\\weekly_run.bat</Command>
      <Arguments></Arguments>
    </Exec>
  </Actions>
</Task>
"""

    task = module.parse_task_xml(xml)

    assert task.exists is True
    assert task.execute == r"C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"
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
    expected = r"C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"
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
        execute=r"C:\Users\cyo20\EIDP-v384-75732b0-ocr-sr-sandbox\scripts\weekly_run.bat",
    )

    report = module.build_report(
        expected_weekly_action=r"C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat",
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
        execute=r"C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat",
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


def test_direct_script_disables_wmi_platform_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "_wmi_query", lambda *_args, **_kwargs: [], raising=False)

    _load_module()

    with pytest.raises(OSError, match="WMI disabled"):
        platform._wmi_query("Win32_OperatingSystem", (), ())  # type: ignore[attr-defined]
