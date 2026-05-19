from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.bug_signals.detector import BugSignal
from eidp.db.models import Base, ManualActionLog
from eidp.review._pages import bug_report


class FakeStreamlit:
    def __init__(self, *, button_clicked: bool = False, note: str = "operator note") -> None:
        self.button_clicked = button_clicked
        self.note = note
        self.calls: list[tuple[str, Any]] = []

    def header(self, value: str) -> None:
        self.calls.append(("header", value))

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))

    def error(self, value: str) -> None:
        self.calls.append(("error", value))

    def success(self, value: str) -> None:
        self.calls.append(("success", value))

    def json(self, value: Any) -> None:
        self.calls.append(("json", value))

    def text_area(self, label: str, **kwargs: Any) -> str:
        self.calls.append(("text_area", (label, kwargs)))
        return self.note

    def button(self, label: str, **kwargs: Any) -> bool:
        self.calls.append(("button", (label, kwargs)))
        return self.button_clicked

    def download_button(self, label: str, **kwargs: Any) -> None:
        self.calls.append(("download_button", (label, kwargs)))


def _signal() -> BugSignal:
    return BugSignal(
        signal_id="sig-1",
        severity="P0",
        kind="weekly_run_error",
        title="Weekly run failed",
        evidence_path="/Users/operator/EIDP/data/output/last_run.json",
        detected_at="2026-05-17T00:00:00+00:00",
        detail={"status": "error"},
    )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_bug_report_page_shows_no_p0_state_without_building_bundle(
    monkeypatch, tmp_path: Path
) -> None:
    fake_st = FakeStreamlit(button_clicked=False)
    scan_calls: list[tuple[Path, bool]] = []

    def fake_scan(root: Path, *, check_sqlite: bool = True) -> list[BugSignal]:
        scan_calls.append((root, check_sqlite))
        return []

    def forbidden_build(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        raise AssertionError("bundle should not be built until the operator clicks")

    monkeypatch.setattr(bug_report, "st", fake_st)
    monkeypatch.setattr(bug_report, "scan_bug_signals", fake_scan)
    monkeypatch.setattr(bug_report, "build_bug_report_bundle", forbidden_build)

    bug_report.render(None, app_root=tmp_path)  # type: ignore[arg-type]

    assert scan_calls == [(tmp_path, True)]
    assert ("success", "現在、異常は検出されていません。必要に応じて手動レポートを作成できます。") in fake_st.calls
    assert not any(name == "download_button" for name, _value in fake_st.calls)


def test_bug_report_page_builds_downloadable_zip_when_clicked(monkeypatch, tmp_path: Path) -> None:
    archive = tmp_path / "bug-report.zip"
    archive.write_bytes(b"zip-bytes")
    signal = _signal()
    fake_st = FakeStreamlit(button_clicked=True, note="operator saw traceback")
    build_calls: list[dict[str, Any]] = []
    session = _session()

    def fake_scan(root: Path, *, check_sqlite: bool = True) -> list[BugSignal]:
        return [signal]

    def fake_build(root: Path, *, signals: list[BugSignal], operator_note: str) -> dict[str, str]:
        build_calls.append({"root": root, "signals": signals, "operator_note": operator_note})
        return {"archive": archive.as_posix()}

    monkeypatch.setattr(bug_report, "st", fake_st)
    monkeypatch.setattr(bug_report, "scan_bug_signals", fake_scan)
    monkeypatch.setattr(bug_report, "build_bug_report_bundle", fake_build)

    bug_report.render(session, app_root=tmp_path)

    assert build_calls == [{"root": tmp_path, "signals": [signal], "operator_note": "operator saw traceback"}]
    audit = session.query(ManualActionLog).one()
    assert audit.action_type == "bug_report_generated"
    assert audit.target_table == "bug_report"
    payload = audit.new_value
    assert payload is not None
    assert "bug-report.zip" in payload
    assert "operator saw traceback" not in payload
    assert ("error", "異常を 1 件検出しました。レポートZIPを作成してください。") in fake_st.calls
    assert any(
        name == "json" and "/Users/operator" not in str(value) and "/Users/<REDACTED>" in str(value)
        for name, value in fake_st.calls
    )
    assert ("success", "作成完了: bug-report.zip") in fake_st.calls
    download_calls = [value for name, value in fake_st.calls if name == "download_button"]
    assert download_calls == [
        (
            "レポートZIPを保存",
            {
                "data": b"zip-bytes",
                "file_name": "bug-report.zip",
                "mime": "application/zip",
                "key": "download_bug_report_zip",
            },
        )
    ]


def test_bug_report_page_reports_scan_failure_and_allows_manual_bundle(
    monkeypatch, tmp_path: Path
) -> None:
    archive = tmp_path / "bug-report.zip"
    archive.write_bytes(b"zip-bytes")
    fake_st = FakeStreamlit(button_clicked=True)
    build_calls: list[dict[str, Any]] = []

    def failing_scan(root: Path, *, check_sqlite: bool = True) -> list[BugSignal]:
        raise RuntimeError("sqlite busy")

    def fake_build(root: Path, *, signals: list[BugSignal], operator_note: str) -> dict[str, str]:
        build_calls.append({"root": root, "signals": signals, "operator_note": operator_note})
        return {"archive": archive.as_posix()}

    monkeypatch.setattr(bug_report, "st", fake_st)
    monkeypatch.setattr(bug_report, "scan_bug_signals", failing_scan)
    monkeypatch.setattr(bug_report, "build_bug_report_bundle", fake_build)

    bug_report.render(None, app_root=tmp_path)  # type: ignore[arg-type]

    assert ("error", "異常検出の確認に失敗しました: RuntimeError: sqlite busy") in fake_st.calls
    assert build_calls == [{"root": tmp_path, "signals": [], "operator_note": "operator note"}]
    assert any(name == "download_button" for name, _value in fake_st.calls)


def test_bug_report_page_reports_bundle_failure_without_download(monkeypatch, tmp_path: Path) -> None:
    fake_st = FakeStreamlit(button_clicked=True)

    def fake_scan(root: Path, *, check_sqlite: bool = True) -> list[BugSignal]:
        return [_signal()]

    def failing_build(root: Path, *, signals: list[BugSignal], operator_note: str) -> dict[str, str]:
        raise OSError("disk full")

    monkeypatch.setattr(bug_report, "st", fake_st)
    monkeypatch.setattr(bug_report, "scan_bug_signals", fake_scan)
    monkeypatch.setattr(bug_report, "build_bug_report_bundle", failing_build)

    bug_report.render(None, app_root=tmp_path)  # type: ignore[arg-type]

    assert ("error", "レポート作成に失敗しました: OSError: disk full") in fake_st.calls
    assert not any(name == "download_button" for name, _value in fake_st.calls)
