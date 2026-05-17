from __future__ import annotations

import json
import multiprocessing
import os
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eidp.bug_signals.bundle import build_bug_report_bundle, scrub_json_value, scrub_text
from eidp.bug_signals.detector import scan_bug_signals, scan_p0_bug_signals


def _worker_hold_lock(lock_path: str, ready_event, release_event) -> None:  # noqa: ANN001
    from eidp.db.locking import acquire_lock

    with acquire_lock(Path(lock_path), owner="weekly_runner"):
        ready_event.set()
        release_event.wait(timeout=10)


def test_scan_bug_signals_detects_weekly_error_and_log_error(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data" / "output").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "data" / "output" / "last_run.json").write_text(
        json.dumps({"status": "error", "error": "weekly failed"}),
        encoding="utf-8",
    )
    (root / "logs" / "run-20260517.log").write_text(
        "start\nTraceback (most recent call last)\nboom\n",
        encoding="utf-8",
    )

    signals = scan_bug_signals(root, now=datetime(2026, 5, 17, 12, 0, tzinfo=UTC), check_sqlite=False)

    assert {signal.kind for signal in signals} == {
        "weekly_run_error",
        "weekly_run_log_error",
    }
    assert all(signal.severity == "P0" for signal in signals)


def test_scan_bug_signals_ignores_unheld_stale_lock_file(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data").mkdir(parents=True)
    lock_path = root / "data" / ".lock"
    lock_path.write_text("", encoding="utf-8")
    now = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)
    stale_timestamp = (now - timedelta(days=6)).timestamp()
    os.utime(lock_path, (stale_timestamp, stale_timestamp))

    signals = scan_bug_signals(root, now=now, check_sqlite=False)

    assert "stale_lock" not in {signal.kind for signal in signals}


def test_scan_bug_signals_detects_held_stale_lock(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data").mkdir(parents=True)
    lock_path = root / "data" / ".lock"
    now = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)

    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    release_event = ctx.Event()
    proc = ctx.Process(target=_worker_hold_lock, args=(str(lock_path), ready_event, release_event))
    proc.start()
    try:
        assert ready_event.wait(timeout=5)
        meta_path = lock_path.with_suffix(lock_path.suffix + ".meta")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["started_at"] = (now - timedelta(hours=3)).isoformat()
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

        signals = scan_bug_signals(root, now=now, check_sqlite=False)
    finally:
        release_event.set()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()

    stale = next(signal for signal in signals if signal.kind == "stale_lock")
    assert stale.title == "Application lock appears held for too long"
    assert stale.evidence_path == meta_path.as_posix()
    assert stale.detail["owner"] == "weekly_runner"
    assert stale.detail["pid"] == str(proc.pid)
    assert stale.detail["age_seconds"] == "10800"


def test_scan_bug_signals_detects_weekly_timeout_without_fresh_last_run(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data" / "output").mkdir(parents=True)
    (root / "logs").mkdir()
    now = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)
    stale_timestamp = (now - timedelta(hours=2)).timestamp()
    run_log = root / "logs" / "run-20260517.log"
    run_log.write_text("[weekly_run] start 2026/05/17 10:00:00\nstill crawling\n", encoding="utf-8")
    os.utime(run_log, (stale_timestamp, stale_timestamp))

    signals = scan_bug_signals(
        root,
        now=now,
        weekly_timeout_after=timedelta(hours=1),
        check_sqlite=False,
    )

    timeout = next(signal for signal in signals if signal.kind == "weekly_run_timeout_no_last_run")
    assert timeout.severity == "P1"
    assert timeout.evidence_path == run_log.as_posix()
    assert timeout.detail["age_seconds"] == "7200"


def test_scan_bug_signals_uses_stable_ids_for_aging_signals(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data").mkdir(parents=True)
    lock_path = root / "data" / ".lock"
    started = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)
    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    release_event = ctx.Event()
    proc = ctx.Process(target=_worker_hold_lock, args=(str(lock_path), ready_event, release_event))
    proc.start()
    try:
        assert ready_event.wait(timeout=5)
        meta_path = lock_path.with_suffix(lock_path.suffix + ".meta")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["started_at"] = (started - timedelta(hours=3)).isoformat()
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

        first = scan_bug_signals(root, now=started, check_sqlite=False)
        second = scan_bug_signals(root, now=started + timedelta(minutes=10), check_sqlite=False)
    finally:
        release_event.set()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()

    first_lock = next(signal for signal in first if signal.kind == "stale_lock")
    second_lock = next(signal for signal in second if signal.kind == "stale_lock")
    assert first_lock.detail["age_seconds"] != second_lock.detail["age_seconds"]
    assert first_lock.signal_id == second_lock.signal_id


def test_scan_bug_signals_detects_sqlite_integrity_error(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data").mkdir(parents=True)
    (root / "data" / "eidp.sqlite3").write_bytes(b"not sqlite")

    signals = scan_bug_signals(root, check_sqlite=True)

    assert any(signal.kind == "sqlite_integrity_error" for signal in signals)


def test_scan_p0_bug_signals_remains_compatible(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data" / "output").mkdir(parents=True)
    (root / "data" / "output" / "last_run.json").write_text(
        json.dumps({"status": "error", "error": "weekly failed"}),
        encoding="utf-8",
    )

    signals = scan_p0_bug_signals(root, check_sqlite=False)

    assert [signal.kind for signal in signals] == ["weekly_run_error"]


def test_build_bug_report_bundle_sanitizes_and_excludes_sensitive_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "eidp"
    (root / "data" / "output").mkdir(parents=True)
    (root / "data" / "pdfs" / "1").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "BUILD_INFO.json").write_text('{"git_commit":"abc"}\n', encoding="utf-8")
    (root / "data" / "output" / "last_run.json").write_text(
        '{"status":"error","school_name":"東京テスト専門学校","operator_name":"山田"}\n',
        encoding="utf-8",
    )
    (root / "logs" / "run-20260517.log").write_text(
        "C:\\Users\\operator\\EIDP\\secret user@example.com 学校名: 東京テスト専門学校\nERROR: boom\n",
        encoding="utf-8",
    )
    (root / "logs" / "diagnostics-20260517.txt").write_text("diag\n", encoding="utf-8")
    (root / "data" / "eidp.sqlite3").write_bytes(b"sqlite")
    (root / "data" / "pdfs" / "1" / "target.pdf").write_bytes(b"%PDF")
    (root / "data" / "output" / "eidp_master.xlsx").write_bytes(b"PK")

    result = build_bug_report_bundle(
        root,
        operator_note="contact user@example.com /Users/operator/project",
        now=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
    )

    archive = Path(result["archive"])
    assert archive.name == "bug-report-20260517-120000.zip"
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        assert "BUILD_INFO.json" in names
        assert "data/output/last_run.json" in names
        assert "logs/run-latest-tail.txt" in names
        assert "logs/diagnostics-latest-tail.txt" in names
        assert "bug-signals.json" in names
        assert "manifest.json" in names
        assert "data/eidp.sqlite3" not in names
        assert "data/pdfs/1/target.pdf" not in names
        assert "data/output/eidp_master.xlsx" not in names

        run_tail = zf.read("logs/run-latest-tail.txt").decode("utf-8")
        manifest = zf.read("manifest.json").decode("utf-8")
        last_run = zf.read("data/output/last_run.json").decode("utf-8")

    manifest_payload = json.loads(manifest)
    assert "operator" not in run_tail
    assert "user@example.com" not in run_tail
    assert "東京テスト専門学校" not in run_tail
    assert "/Users/operator" not in manifest
    assert manifest_payload["operator_note"] == "contact <EMAIL> /Users/<REDACTED>/project"
    assert "東京テスト専門学校" not in last_run
    assert "/Users/operator" not in json.dumps(result, ensure_ascii=False)


def test_scrub_text_redacts_known_pii_patterns() -> None:
    text = (
        'C:\\Users\\tester\\EIDP C:/Users/forward/EIDP '
        '/Users/operator/x a@example.com "school_name":"A学校" 操作員: 山田'
    )

    scrubbed = scrub_text(text)

    assert "tester" not in scrubbed
    assert "forward" not in scrubbed
    assert "operator" not in scrubbed
    assert "a@example.com" not in scrubbed
    assert "A学校" not in scrubbed
    assert "山田" not in scrubbed


def test_scrub_text_redacts_secret_assignments() -> None:
    text = "OPENAI_API_KEY=sk-proj-testvalue GITHUB_TOKEN:ghp_testvalue password=hunter2 normal=value"

    scrubbed = scrub_text(text)

    assert "sk-proj-testvalue" not in scrubbed
    assert "ghp_testvalue" not in scrubbed
    assert "hunter2" not in scrubbed
    assert "OPENAI_API_KEY=<REDACTED>" in scrubbed
    assert "GITHUB_TOKEN:<REDACTED>" in scrubbed
    assert "password=<REDACTED>" in scrubbed
    assert "normal=value" in scrubbed


def test_scrub_json_value_recursively_redacts_strings() -> None:
    payload = {
        "path": "/Users/operator/EIDP",
        "nested": [{"email": "a@example.com", "school_name": "A学校"}],
        "count": 1,
    }

    scrubbed = scrub_json_value(payload)

    assert scrubbed == {
        "path": "/Users/<REDACTED>/EIDP",
        "nested": [{"email": "<EMAIL>", "school_name": "<REDACTED>"}],
        "count": 1,
    }
