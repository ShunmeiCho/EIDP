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


def test_step_download_artifacts_updates_progress_per_prefecture(tmp_path: Path, monkeypatch) -> None:
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "\n".join([
            "pref_key,artifact_url,artifact_format,verified_status",
            "gunma,https://www.pref.gunma.jp/page/12959.html,html,url_found",
            "ehime,https://www.pref.ehime.jp/list.xlsx,xlsx,url_found",
        ]),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    progress_file = tmp_path / "logs" / "bootstrap.json"
    progress = module.BootstrapProgressWriter(progress_file)

    monkeypatch.setattr(module, "SUPPORTED_PARSERS", frozenset({"gunma", "ehime"}))

    def fake_download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"dummy")
        module.write_source_url_sidecar(dest, url)

    monkeypatch.setattr(module, "download_artifact", fake_download)

    ok, failed = module.step_download_artifacts(
        seed_csv=seed_csv,
        artifact_dir=artifact_dir,
        only=None,
        force=True,
        progress=progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert ok == ["gunma", "ehime"]
    assert failed == []
    assert payload["current_step"] == 1
    assert payload["percent"] == 0.25
    assert "2/2件: ehime" in payload["message"]
    assert payload["details"]["prefectures_done"] == 2
    assert payload["details"]["prefectures_ok"] == 2


def test_step_aggregate_updates_progress_per_prefecture(tmp_path: Path, monkeypatch) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "gunma.html").write_text("<html></html>", encoding="utf-8")
    (artifact_dir / "ehime.xlsx").write_bytes(b"dummy")
    progress_file = tmp_path / "logs" / "bootstrap.json"
    progress = module.BootstrapProgressWriter(progress_file)
    calls: list[object] = []

    class FakeSession:
        def commit(self) -> None:
            calls.append("commit")

        def rollback(self) -> None:
            calls.append("rollback")

        def close(self) -> None:
            calls.append("close")

    def fake_aggregate(session, pref, artifact):  # noqa: ANN001
        calls.append((session, pref, artifact.name))
        return SimpleNamespace(extracted_total=3, db_matched=2)

    def fake_apply_writer_plan(session, report):  # noqa: ANN001, ARG001
        return {"added": 1, "upgraded": 1, "skipped": 1}

    import eidp.db.session as db_session
    import eidp.scraper.prefecture_aggregator as pa

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(pa, "aggregate", fake_aggregate)
    monkeypatch.setattr(pa, "apply_writer_plan", fake_apply_writer_plan)

    results = module.step_aggregate(
        pref_keys=["gunma", "ehime"],
        artifact_dir=artifact_dir,
        output_dir=tmp_path / "out",
        progress=progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert results == {
        "gunma": {"extracted": 3, "matched": 2, "added": 1, "upgraded": 1, "skipped": 1},
        "ehime": {"extracted": 3, "matched": 2, "added": 1, "upgraded": 1, "skipped": 1},
    }
    assert payload["current_step"] == 2
    assert payload["percent"] == 0.45
    assert "2/2件: ehime" in payload["message"]
    assert payload["details"]["prefectures_aggregated"] == 2
    assert payload["details"]["added"] == 1
    assert "commit" in calls


def test_step_known_url_discovery_imports_seed_and_corporation_fallbacks(tmp_path: Path, monkeypatch) -> None:
    calls: list[object] = []
    seed_url_csv = tmp_path / "known.csv"
    seed_url_csv.write_text("school,url\n", encoding="utf-8")

    class FakeSession:
        def commit(self) -> None:
            calls.append("commit")

        def rollback(self) -> None:
            calls.append("rollback")

        def close(self) -> None:
            calls.append("close")

    def fake_import_seed_urls(session, csv_path):  # noqa: ANN001
        calls.append(("seed", session, csv_path))
        return {"imported": 2, "skipped_no_school": 1, "skipped_existing": 3}

    def fake_infer_corporation_urls(session):  # noqa: ANN001
        calls.append(("corp", session))
        return {"inferred": 4, "skipped_has_url": 5}

    import eidp.db.session as db_session
    import eidp.scraper.url_discovery as url_discovery

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(url_discovery, "import_seed_urls", fake_import_seed_urls)
    monkeypatch.setattr(url_discovery, "infer_corporation_urls", fake_infer_corporation_urls)

    stats = module.step_known_url_discovery(seed_url_csv=seed_url_csv)

    assert stats == {
        "seed_imported": 2,
        "seed_skipped_no_school": 1,
        "seed_skipped_existing": 3,
        "corporation_inferred": 4,
        "corporation_skipped_has_url": 5,
    }
    assert calls[0] == ("seed", fake_session, seed_url_csv)
    assert calls[1] == ("corp", fake_session)
    assert "commit" in calls


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
        discovery_methods=["prefecture_aggregator", "seed_csv", "corporation_pattern"],
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
