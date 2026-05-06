from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_step_download_artifacts_uses_html_suffix_and_source_sidecar(tmp_path: Path, monkeypatch) -> None:
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "\n".join([
            "pref_key,artifact_url,artifact_format,verified_status",
            "gunma,https://www.pref.gunma.jp/page/12959.html,html,url_found",
        ]),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"

    monkeypatch.setattr(module, "SUPPORTED_PARSERS", frozenset({"gunma"}))

    def fake_download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<html></html>", encoding="utf-8")
        module.write_source_url_sidecar(dest, url)

    monkeypatch.setattr(module, "download_artifact", fake_download)

    ok, failed = module.step_download_artifacts(
        seed_csv=seed_csv,
        artifact_dir=artifact_dir,
        only=None,
        force=False,
    )

    assert ok == ["gunma"]
    assert failed == []
    assert (artifact_dir / "gunma.html").is_file()
    assert (artifact_dir / "gunma.html.url").read_text(encoding="utf-8").strip() == (
        "https://www.pref.gunma.jp/page/12959.html"
    )


def test_step_discover_pdfs_updates_progress_inside_long_step(tmp_path: Path, monkeypatch) -> None:
    progress_file = tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"
    progress = module.BootstrapProgressWriter(progress_file)
    calls: list[object] = []

    class FakeSession:
        def commit(self) -> None:
            calls.append("commit")

        def rollback(self) -> None:
            calls.append("rollback")

        def close(self) -> None:
            calls.append("close")

    def fake_run_pdf_discovery(session, storage_dir, **kwargs):  # noqa: ANN001
        calls.append(session)
        callback = kwargs["progress_callback"]
        callback({"crawled": 5, "found": 3, "downloaded": 1, "failed": 0, "skipped": 4}, 10)
        return {"crawled": 10, "found": 4, "downloaded": 2, "failed": 0, "skipped": 8}

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.scraper.pdf_discovery as pdf_discovery

    monkeypatch.setattr(db_session, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(pdf_discovery, "run_pdf_discovery", fake_run_pdf_discovery)
    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)

    stats = module.step_discover_pdfs(
        storage_dir=tmp_path / "pdfs",
        batch_size=100,
        rate_limit=0,
        evidence_log=None,
        progress=progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert stats["downloaded"] == 2
    assert payload["status"] == "running"
    assert payload["current_step"] == 3
    assert payload["percent"] > 0.45
    assert "5/10件確認済み" in payload["message"]
    assert payload["details"]["downloaded"] == 1
    assert "commit" in calls


def test_step_rebuild_status_includes_all_school_types(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSession:
        def commit(self) -> None:
            calls.append({"commit": True})

        def rollback(self) -> None:
            calls.append({"rollback": True})

        def close(self) -> None:
            calls.append({"close": True})

    def fake_rebuild(session, *, fiscal_year, school_type):  # noqa: ANN001
        calls.append({"session": session, "fiscal_year": fiscal_year, "school_type": school_type})
        return SimpleNamespace(rebuilt=3, excel_ready=1)

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.pipeline.school_fiscal_year_status as status_mod

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(status_mod, "rebuild_school_fiscal_year_status", fake_rebuild)
    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)

    result = module.step_rebuild_status()

    assert result == {"rebuilt": 3, "excel_ready": 1}
    assert calls[0] == {"session": fake_session, "fiscal_year": 2026, "school_type": None}
