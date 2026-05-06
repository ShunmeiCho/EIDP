from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from eidp.db.locking import acquire_lock, probe_lock

script = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap_pdf_pipeline.py"
spec = importlib.util.spec_from_file_location("bootstrap_pdf_pipeline", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["bootstrap_pdf_pipeline"] = module
spec.loader.exec_module(module)


def test_main_holds_app_lock_around_bootstrap(tmp_path: Path, monkeypatch) -> None:
    calls: list[Path] = []
    lock_path = tmp_path / "data" / ".lock"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001
        assert probe_lock(lock_path).held is True
        calls.append(args.lock_path)
        return 0

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    rc = module.main(["--lock-path", str(lock_path)])

    assert rc == 0
    assert calls == [lock_path]
    assert probe_lock(lock_path).held is False


def test_main_returns_busy_when_app_lock_is_held(tmp_path: Path, monkeypatch) -> None:
    called = False
    lock_path = tmp_path / "data" / ".lock"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    with acquire_lock(lock_path, owner="weekly_runner"):
        rc = module.main(["--lock-path", str(lock_path)])

    assert rc == 5
    assert called is False


def test_main_can_skip_lock_for_developer_recovery(tmp_path: Path, monkeypatch) -> None:
    calls: list[Path] = []
    lock_path = tmp_path / "data" / ".lock"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001
        calls.append(args.lock_path)
        return 0

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    rc = module.main(["--no-lock", "--lock-path", str(lock_path)])

    assert rc == 0
    assert calls == [lock_path]


def test_main_writes_progress_file(tmp_path: Path, monkeypatch) -> None:
    lock_path = tmp_path / "data" / ".lock"
    progress_file = tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001
        progress = kwargs["progress"]
        progress.write(
            status="running",
            current_step=3,
            percent=0.45,
            message="学校サイトから対象年度PDFを探索しています。",
        )
        return 0

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    rc = module.main(["--lock-path", str(lock_path), "--progress-file", str(progress_file)])

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload["status"] == "succeeded"
    assert payload["current_step"] == 5
    assert payload["percent"] == 1.0
    assert payload["log_path"] == str(progress_file.with_suffix(".log"))


def test_main_marks_progress_failed_for_nonzero_exit(tmp_path: Path, monkeypatch) -> None:
    progress_file = tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001, ARG001
        return 2

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    rc = module.main(["--no-lock", "--progress-file", str(progress_file)])

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert rc == 2
    assert payload["status"] == "failed"
    assert payload["error"] == "exit_code=2"
