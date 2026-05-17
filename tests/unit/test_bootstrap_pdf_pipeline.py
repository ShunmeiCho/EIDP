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


class _FakeStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


def test_configure_utf8_stdio_sets_strict_utf8_errors() -> None:
    stdout = _FakeStream()
    stderr = _FakeStream()

    module._configure_utf8_stdio(stdout, stderr)

    assert stdout.calls == [{"encoding": "utf-8", "errors": "strict"}]
    assert stderr.calls == [{"encoding": "utf-8", "errors": "strict"}]


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


def test_main_preserves_bootstrap_yield_details_on_success(tmp_path: Path, monkeypatch) -> None:
    progress_file = tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"

    def fake_run_bootstrap(args, **kwargs):  # noqa: ANN001, ARG001
        progress = kwargs["progress"]
        progress.write(
            status="running",
            current_step=2,
            percent=0.45,
            message="都道府県データから学校URLを登録しています。",
            details={
                "official_index_rows_extracted": 12,
                "official_index_rows_matched": 10,
                "official_school_sites_added": 4,
            },
        )
        return 0

    monkeypatch.setattr(module, "run_bootstrap", fake_run_bootstrap)

    rc = module.main(["--no-lock", "--progress-file", str(progress_file)])

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload["status"] == "succeeded"
    assert payload["details"]["official_index_rows_extracted"] == 12
    assert payload["details"]["official_index_rows_matched"] == 10
    assert payload["details"]["official_school_sites_added"] == 4


def test_progress_preserves_discovery_skipped_after_ingest(tmp_path: Path) -> None:
    progress_file = tmp_path / "logs" / "bootstrap-pdfs-20260506-103000.json"
    progress = module.BootstrapProgressWriter(progress_file)

    progress.write(
        status="running",
        current_step=3,
        percent=0.74,
        message="学校サイトから対象年度PDFを探索しています。",
        details=module.discovery_progress_details(
            30,
            {
                "crawled": 30,
                "found": 25,
                "downloaded": 0,
                "failed": 3,
                "skipped": 226,
                "prefiltered": 116,
                "cached_rejections": 24,
            },
        ),
    )
    progress.write(
        status="running",
        current_step=5,
        percent=0.9,
        message="学校別タスクを再計算しています。",
        details=module.ingest_progress_details(
            {
                "processed": 0,
                "departments_created": 0,
                "yearly_upserted": 0,
                "skipped": 0,
            }
        ),
    )
    progress.write(
        status="succeeded",
        current_step=5,
        percent=1.0,
        message="初回URL/PDF取得が完了しました。画面を更新してください。",
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert payload["details"]["skipped"] == 226
    assert payload["details"]["discovery_skipped"] == 226
    assert payload["details"]["ingest_skipped"] == 0


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


def test_aggregate_yield_details_summarizes_official_index_yield() -> None:
    details = module.aggregate_yield_details({
        "tokyo": {
            "extracted": 314,
            "matched": 300,
            "added": 40,
            "upgraded": 5,
            "skipped": 255,
            "artifacts": 1,
        },
        "saitama": {
            "extracted": 50,
            "matched": 49,
            "added": 0,
            "upgraded": 0,
            "skipped": 49,
            "artifacts": 2,
        },
    })

    assert details == {
        "official_prefectures_aggregated": 2,
        "official_artifacts_parsed": 3,
        "official_index_rows_extracted": 364,
        "official_index_rows_matched": 349,
        "official_school_sites_added": 40,
        "official_school_sites_upgraded": 5,
        "official_index_rows_skipped": 304,
        "official_prefectures_without_new_urls": 1,
    }


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


def test_step_download_artifacts_removes_stale_sibling_when_current_artifact_exists(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "\n".join([
            "pref_key,artifact_url,artifact_format,verified_status",
            "shizuoka,https://www.pref.shizuoka.jp/kodomokyoiku/school/1002740/1018809.html,html,url_found",
        ]),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "shizuoka.html").write_text("<html></html>", encoding="utf-8")
    (artifact_dir / "shizuoka.pdf").write_bytes(b"%PDF-stale")
    (artifact_dir / "shizuoka.pdf.url").write_text("https://old.example/shizuoka.pdf\n", encoding="utf-8")

    monkeypatch.setattr(module, "SUPPORTED_PARSERS", frozenset({"shizuoka"}))

    ok, failed = module.step_download_artifacts(
        seed_csv=seed_csv,
        artifact_dir=artifact_dir,
        only=None,
        force=False,
    )

    assert ok == ["shizuoka"]
    assert failed == []
    assert (artifact_dir / "shizuoka.html").is_file()
    assert not (artifact_dir / "shizuoka.pdf").exists()
    assert not (artifact_dir / "shizuoka.pdf.url").exists()


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


def test_step_download_artifacts_downloads_supplemental_prefecture_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_csv = tmp_path / "seed.csv"
    seed_csv.write_text(
        "\n".join([
            "pref_key,artifact_url,artifact_format,verified_status,supplemental_artifact_urls",
            (
                "hyogo,https://pref.example/latest.pdf,pdf,url_found,"
                "https://pref.example/r1.pdf|https://pref.example/r2.pdf"
            ),
        ]),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    downloaded: list[tuple[str, str]] = []

    monkeypatch.setattr(module, "SUPPORTED_PARSERS", frozenset({"hyogo"}))

    def fake_download(url: str, dest: Path) -> None:
        downloaded.append((url, dest.name))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"dummy")
        module.write_source_url_sidecar(dest, url)

    monkeypatch.setattr(module, "download_artifact", fake_download)

    ok, failed = module.step_download_artifacts(
        seed_csv=seed_csv,
        artifact_dir=artifact_dir,
        only=None,
        force=True,
    )

    assert ok == ["hyogo"]
    assert failed == []
    assert downloaded == [
        ("https://pref.example/latest.pdf", "hyogo.pdf"),
        ("https://pref.example/r1.pdf", "hyogo__01.pdf"),
        ("https://pref.example/r2.pdf", "hyogo__02.pdf"),
    ]


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
        "gunma": {"extracted": 3, "matched": 2, "added": 1, "upgraded": 1, "skipped": 1, "artifacts": 1},
        "ehime": {"extracted": 3, "matched": 2, "added": 1, "upgraded": 1, "skipped": 1, "artifacts": 1},
    }
    assert payload["current_step"] == 2
    assert payload["percent"] == 0.45
    assert "2/2件: ehime" in payload["message"]
    assert payload["details"]["prefectures_aggregated"] == 2
    assert payload["details"]["added"] == 1
    assert "commit" in calls


def test_step_aggregate_merges_supplemental_prefecture_artifacts(tmp_path: Path, monkeypatch) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "hyogo__01.pdf").write_bytes(b"%PDF-old")
    (artifact_dir / "hyogo.pdf").write_bytes(b"%PDF-current")
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
        return SimpleNamespace(extracted_total=10 if "__" in artifact.stem else 1, db_matched=8)

    def fake_apply_writer_plan(session, report):  # noqa: ANN001, ARG001
        return {"added": 2, "upgraded": 0, "skipped": 6}

    import eidp.db.session as db_session
    import eidp.scraper.prefecture_aggregator as pa

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(pa, "aggregate", fake_aggregate)
    monkeypatch.setattr(pa, "apply_writer_plan", fake_apply_writer_plan)

    results = module.step_aggregate(
        pref_keys=["hyogo"],
        artifact_dir=artifact_dir,
        output_dir=tmp_path / "out",
    )

    assert results == {
        "hyogo": {"extracted": 11, "matched": 16, "added": 4, "upgraded": 0, "skipped": 12, "artifacts": 2}
    }
    assert calls[:2] == [
        (fake_session, "hyogo", "hyogo__01.pdf"),
        (fake_session, "hyogo", "hyogo.pdf"),
    ]
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
        return {
            "inferred": 4,
            "skipped_has_url": 5,
            "school_override_inferred": 2,
            "school_override_skipped_existing": 3,
            "school_override_skipped_no_school": 1,
        }

    def fake_search_and_discover(  # noqa: ANN001
        session,
        *,
        batch_size,
        evidence_path=None,
        progress_callback=None,
    ):
        _ = progress_callback
        calls.append(("search", session, batch_size, evidence_path))
        return {"searched": 10, "found": 6, "no_result": 3, "errors": 1}

    import eidp.db.session as db_session
    import eidp.scraper.url_discovery as url_discovery

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(url_discovery, "import_seed_urls", fake_import_seed_urls)
    monkeypatch.setattr(url_discovery, "infer_corporation_urls", fake_infer_corporation_urls)
    monkeypatch.setattr(url_discovery, "search_and_discover", fake_search_and_discover)

    stats = module.step_known_url_discovery(seed_url_csv=seed_url_csv)

    assert stats == {
        "seed_imported": 2,
        "seed_skipped_no_school": 1,
        "seed_skipped_existing": 3,
        "school_override_inferred": 2,
        "school_override_skipped_existing": 3,
        "school_override_skipped_no_school": 1,
        "corporation_inferred": 4,
        "corporation_skipped_has_url": 5,
        "search_enabled": 0,
        "search_searched": 0,
        "search_found": 0,
        "search_no_result": 0,
        "search_errors": 0,
    }
    assert calls[0] == ("seed", fake_session, seed_url_csv)
    assert calls[1] == ("corp", fake_session)
    assert "commit" in calls


def test_step_known_url_discovery_runs_search_when_enabled(tmp_path: Path, monkeypatch) -> None:
    calls: list[object] = []
    seed_url_csv = tmp_path / "known.csv"
    seed_url_csv.write_text("school,url\n", encoding="utf-8")
    progress_file = tmp_path / "logs" / "bootstrap.json"
    progress = module.BootstrapProgressWriter(progress_file)

    class FakeSession:
        def commit(self) -> None:
            calls.append("commit")

        def rollback(self) -> None:
            calls.append("rollback")

        def close(self) -> None:
            calls.append("close")

    def fake_import_seed_urls(session, csv_path):  # noqa: ANN001
        calls.append(("seed", session, csv_path))
        return {"imported": 0, "skipped_no_school": 0, "skipped_existing": 0}

    def fake_infer_corporation_urls(session):  # noqa: ANN001
        calls.append(("corp", session))
        return {"inferred": 1, "skipped_has_url": 2, "school_override_inferred": 1}

    def fake_search_and_discover(  # noqa: ANN001
        session,
        *,
        batch_size,
        evidence_path=None,
        progress_callback=None,
    ):
        calls.append(("search", session, batch_size, evidence_path))
        if progress_callback is not None:
            progress_callback({"searched": 10, "found": 4, "no_result": 5, "errors": 1}, 25)
        return {"searched": 25, "found": 9, "no_result": 15, "errors": 1}

    import eidp.db.session as db_session
    import eidp.scraper.url_discovery as url_discovery

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(url_discovery, "import_seed_urls", fake_import_seed_urls)
    monkeypatch.setattr(url_discovery, "infer_corporation_urls", fake_infer_corporation_urls)
    monkeypatch.setattr(url_discovery, "search_and_discover", fake_search_and_discover)

    stats = module.step_known_url_discovery(
        seed_url_csv=seed_url_csv,
        search_missing_urls=True,
        search_batch_size=25,
        url_search_evidence_log=tmp_path / "url-search.jsonl",
        progress=progress,
    )
    payload = json.loads(progress_file.read_text(encoding="utf-8"))

    assert stats["corporation_inferred"] == 1
    assert stats["search_enabled"] == 1
    assert stats["search_searched"] == 25
    assert stats["search_found"] == 9
    assert stats["search_no_result"] == 15
    assert stats["search_errors"] == 1
    assert calls[2] == ("search", fake_session, 25, tmp_path / "url-search.jsonl")
    assert "commit" in calls
    assert payload["current_step"] == 2
    assert 0.45 < payload["percent"] < 0.60
    assert payload["message"].startswith("不足URLをWeb検索で補完しています。")
    assert payload["details"]["search_searched"] == 10
    assert payload["details"]["search_found"] == 4


def test_resolve_url_search_mode_is_key_aware() -> None:
    assert module.resolve_url_search_mode(
        configured_mode="auto",
        provider="duckduckgo",
        batch_size=200,
    ) == (True, 200, "auto_ready")
    assert module.resolve_url_search_mode(
        configured_mode="auto",
        provider="serper",
        batch_size=200,
    ) == (False, 200, "auto_not_ready")
    assert module.resolve_url_search_mode(
        configured_mode="on",
        provider="serper",
        batch_size=200,
    ) == (True, 200, "on")
    assert module.resolve_url_search_mode(
        configured_mode="off",
        provider="duckduckgo",
        batch_size=200,
    ) == (False, 200, "off")


def test_resolve_school_url_crawl_mode_requires_scrapling_and_provider() -> None:
    assert module.resolve_school_url_crawl_mode(
        configured_mode="auto",
        provider="duckduckgo",
        batch_size=25,
        scrapling_installed=True,
    ) == (True, 25, "auto_ready")
    assert module.resolve_school_url_crawl_mode(
        configured_mode="auto",
        provider="duckduckgo",
        batch_size=25,
        scrapling_installed=False,
    ) == (False, 25, "auto_scrapling_not_installed")
    assert module.resolve_school_url_crawl_mode(
        configured_mode="on",
        provider="serper",
        batch_size=25,
        scrapling_installed=True,
    ) == (False, 25, "on_search_provider_not_ready")
    assert module.resolve_school_url_crawl_mode(
        configured_mode="off",
        provider="duckduckgo",
        batch_size=25,
        scrapling_installed=True,
    ) == (False, 25, "off")


def test_step_school_url_auto_crawl_writes_progress_when_disabled(tmp_path: Path) -> None:
    progress_file = tmp_path / "logs" / "bootstrap.json"
    progress = module.BootstrapProgressWriter(progress_file)

    stats = module.step_school_url_auto_crawl(
        enabled=False,
        batch_size=25,
        progress=progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert stats["school_url_crawl_enabled"] == 0
    assert payload["status"] == "running"
    assert payload["percent"] == module.SCHOOL_URL_CRAWL_PERCENT_END
    assert "スキップ" in payload["message"]
    assert payload["details"]["school_url_crawl_enabled"] == 0


def test_run_bootstrap_adds_web_search_sites_to_pdf_discovery(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    def fake_step_download_artifacts(**kwargs):  # noqa: ANN003
        calls["download"] = kwargs
        return ["tokyo"], []

    def fake_step_aggregate(**kwargs):  # noqa: ANN003
        calls["aggregate"] = kwargs
        return {"tokyo": {"added": 1}}

    def fake_step_known_url_discovery(**kwargs):  # noqa: ANN003
        calls["known"] = kwargs
        return {
            "seed_imported": 0,
            "seed_skipped_no_school": 0,
            "seed_skipped_existing": 0,
            "corporation_inferred": 0,
            "corporation_skipped_has_url": 0,
            "search_enabled": 1,
            "search_searched": 25,
            "search_found": 2,
            "search_no_result": 23,
            "search_errors": 0,
        }

    def fake_step_discover_pdfs(**kwargs):  # noqa: ANN003
        calls["discover"] = kwargs
        return {"downloaded": 0}

    def fake_step_school_url_auto_crawl(**kwargs):  # noqa: ANN003
        calls["school_url_crawl"] = kwargs
        return {
            "school_url_crawl_enabled": 1,
            "school_url_crawl_attempted": 3,
            "school_url_crawl_auto_registered": 1,
            "school_url_crawl_auto_existing": 0,
            "school_url_crawl_review_enqueued": 1,
            "school_url_crawl_review_existing": 0,
            "school_url_crawl_dry_run_auto": 0,
            "school_url_crawl_dry_run_review": 0,
            "school_url_crawl_dry_run_manual_required": 0,
            "school_url_crawl_manual_required_enqueued": 1,
            "school_url_crawl_manual_required_existing": 0,
            "school_url_crawl_rejected": 0,
            "school_url_crawl_no_candidates": 0,
            "school_url_crawl_circuit_open": 0,
            "school_url_crawl_errors": 0,
            "school_url_crawl_unavailable": 0,
        }

    import eidp.config as config_mod
    import eidp.scraper.scrapling_fetcher as scrapling_fetcher

    monkeypatch.setattr(module, "step_download_artifacts", fake_step_download_artifacts)
    monkeypatch.setattr(module, "step_aggregate", fake_step_aggregate)
    monkeypatch.setattr(module, "step_known_url_discovery", fake_step_known_url_discovery)
    monkeypatch.setattr(module, "step_school_url_auto_crawl", fake_step_school_url_auto_crawl)
    monkeypatch.setattr(module, "step_discover_pdfs", fake_step_discover_pdfs)
    monkeypatch.setattr(scrapling_fetcher, "scrapling_available", lambda: True)
    monkeypatch.setattr(config_mod.settings, "url_search_auto_enable", "auto")
    monkeypatch.setattr(config_mod.settings, "url_search_batch_size", 25)
    monkeypatch.setattr(config_mod.settings, "school_url_crawl_auto_enable", "auto")
    monkeypatch.setattr(config_mod.settings, "school_url_crawl_batch_size", 25)
    monkeypatch.setattr(config_mod.settings, "school_url_crawl_fetch_mode", "static")
    monkeypatch.setattr(config_mod.settings, "search_provider", "duckduckgo")
    monkeypatch.setattr(config_mod.settings, "serper_api_key", "")
    monkeypatch.setattr(config_mod.settings, "brave_api_key", "")
    monkeypatch.setattr(config_mod.settings, "google_api_key", "")
    monkeypatch.setattr(config_mod.settings, "google_cx", "")

    rc = module.run_bootstrap(
        SimpleNamespace(
            pref="",
            seed_csv=tmp_path / "seed.csv",
            artifact_dir=tmp_path / "artifacts",
            force_redownload=False,
            aggregate_output=tmp_path / "out",
            skip_known_url_discovery=False,
            url_search="settings",
            url_search_batch_size=None,
            seed_url_csv=tmp_path / "known.csv",
            skip_discover=False,
            discovery_methods="prefecture_aggregator,seed_csv,corporation_pattern",
            storage_dir=tmp_path / "pdfs",
            batch_size=100,
            rate_limit=0.0,
            request_timeout=12.0,
            evidence_log=None,
            url_search_evidence_log=tmp_path / "url_search_evidence.jsonl",
            school_url_crawl="settings",
            school_url_crawl_batch_size=None,
            school_url_crawl_fetch_mode="settings",
            school_url_crawl_evidence_log=tmp_path / "school_url_crawl_evidence.jsonl",
            allow_stale_fallback=False,
            target_fiscal_year=2025,
            skip_ingest=True,
        )
    )

    assert rc == 0
    assert calls["known"]["search_missing_urls"] is True
    assert calls["known"]["search_batch_size"] == 25
    assert calls["discover"]["discovery_methods"] == [
        "prefecture_aggregator",
        "seed_csv",
        "corporation_pattern",
        "school_domain_override",
        "web_search",
        "scrapling_stealth",
    ]
    assert calls["school_url_crawl"]["enabled"] is True
    assert calls["school_url_crawl"]["batch_size"] == 25
    assert calls["discover"]["request_timeout"] == 12.0
    assert calls["discover"]["target_fiscal_year"] == 2025


def test_skip_discover_progress_preserves_known_url_yield(monkeypatch, tmp_path: Path) -> None:
    def fake_step_download_artifacts(**kwargs):  # noqa: ANN003
        return ["tokyo"], []

    def fake_step_aggregate(**kwargs):  # noqa: ANN003
        return {
            "tokyo": {
                "extracted": 12,
                "matched": 10,
                "added": 4,
                "upgraded": 1,
                "skipped": 6,
                "artifacts": 1,
            }
        }

    def fake_step_known_url_discovery(**kwargs):  # noqa: ANN003
        return {
            "seed_imported": 3,
            "seed_skipped_no_school": 0,
            "seed_skipped_existing": 1,
            "corporation_inferred": 5,
            "corporation_skipped_has_url": 2,
            "search_enabled": 0,
            "search_searched": 0,
            "search_found": 0,
            "search_no_result": 0,
            "search_errors": 0,
        }

    import eidp.config as config_mod

    monkeypatch.setattr(module, "step_download_artifacts", fake_step_download_artifacts)
    monkeypatch.setattr(module, "step_aggregate", fake_step_aggregate)
    monkeypatch.setattr(module, "step_known_url_discovery", fake_step_known_url_discovery)
    monkeypatch.setattr(config_mod.settings, "url_search_auto_enable", "off")
    monkeypatch.setattr(config_mod.settings, "url_search_batch_size", 0)
    monkeypatch.setattr(config_mod.settings, "search_provider", "duckduckgo")
    monkeypatch.setattr(config_mod.settings, "serper_api_key", "")
    monkeypatch.setattr(config_mod.settings, "brave_api_key", "")
    monkeypatch.setattr(config_mod.settings, "google_api_key", "")
    monkeypatch.setattr(config_mod.settings, "google_cx", "")

    progress_file = tmp_path / "logs" / "bootstrap.json"
    progress = module.BootstrapProgressWriter(progress_file)

    rc = module.run_bootstrap_with_progress(
        SimpleNamespace(
            pref="",
            seed_csv=tmp_path / "seed.csv",
            artifact_dir=tmp_path / "artifacts",
            force_redownload=False,
            aggregate_output=tmp_path / "out",
            skip_known_url_discovery=False,
            url_search="settings",
            url_search_batch_size=None,
            seed_url_csv=tmp_path / "known.csv",
            skip_discover=True,
            discovery_methods="prefecture_aggregator,seed_csv,corporation_pattern",
            storage_dir=tmp_path / "pdfs",
            batch_size=100,
            rate_limit=0.0,
            request_timeout=12.0,
            evidence_log=None,
            url_search_evidence_log=tmp_path / "url_search_evidence.jsonl",
            allow_stale_fallback=False,
            skip_ingest=True,
        ),
        progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload["status"] == "succeeded"
    assert payload["details"]["official_index_rows_extracted"] == 12
    assert payload["details"]["official_school_sites_added"] == 4
    assert payload["details"]["seed_imported"] == 3
    assert payload["details"]["corporation_inferred"] == 5


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
        calls.append({
            "request_timeout": kwargs["request_timeout"],
            "target_fiscal_year": kwargs["target_fiscal_year"],
        })
        callback({"crawled": 5, "found": 3, "downloaded": 1, "failed": 0, "skipped": 4}, 10)
        callback(
            {
                "crawled": 5,
                "found": 3,
                "downloaded": 1,
                "failed": 0,
                "skipped": 4,
                "active_index": 6,
                "active_school_id": 123,
            },
            10,
        )
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
        request_timeout=12,
        evidence_log=None,
        discovery_methods=["prefecture_aggregator", "seed_csv", "corporation_pattern"],
        progress=progress,
    )

    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert stats["downloaded"] == 2
    assert payload["status"] == "running"
    assert payload["current_step"] == 3
    assert payload["percent"] > 0.60
    assert "5/10件確認済み" in payload["message"]
    assert "6件目を確認中" in payload["message"]
    assert payload["details"]["downloaded"] == 1
    assert payload["details"]["active_school_id"] == 123
    assert "commit" in calls
    assert {"request_timeout": 12, "target_fiscal_year": 2026} in calls


def test_step_discover_pdfs_explicit_target_year_overrides_settings(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSession:
        def commit(self) -> None:
            calls.append({"commit": True})

        def rollback(self) -> None:
            calls.append({"rollback": True})

        def close(self) -> None:
            calls.append({"close": True})

    def fake_run_pdf_discovery(session, storage_dir, **kwargs):  # noqa: ANN001, ARG001, ANN003
        calls.append({"target_fiscal_year": kwargs["target_fiscal_year"]})
        return {"crawled": 1, "found": 0, "downloaded": 0, "failed": 0, "skipped": 1}

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.scraper.pdf_discovery as pdf_discovery

    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(pdf_discovery, "run_pdf_discovery", fake_run_pdf_discovery)

    module.step_discover_pdfs(
        storage_dir=tmp_path / "pdfs",
        batch_size=10,
        rate_limit=0.0,
        request_timeout=12.0,
        evidence_log=None,
        discovery_methods=["prefecture_aggregator"],
        target_fiscal_year=2025,
    )

    assert {"target_fiscal_year": 2025} in calls


def test_step_ingest_explicit_target_year_overrides_settings(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSession:
        def commit(self) -> None:
            calls.append({"commit": True})

        def rollback(self) -> None:
            calls.append({"rollback": True})

        def close(self) -> None:
            calls.append({"close": True})

    def fake_run_ingestion(session, **kwargs):  # noqa: ANN001, ANN003
        calls.append({"session": session, **kwargs})
        return {"processed": 1, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.pipeline.ingest as ingest_mod

    fake_session = FakeSession()
    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(ingest_mod, "run_ingestion", fake_run_ingestion)

    module.step_ingest(batch_size=10, evidence_log=None, target_fiscal_year=2025)

    assert calls[0]["session"] is fake_session
    assert calls[0]["target_fiscal_year"] == 2025
    assert {"commit": True} in calls


def test_bootstrap_target_pdf_yield_metrics_marks_gate_status() -> None:
    assert module.bootstrap_target_pdf_yield_metrics(
        schools_total=10,
        schools_with_target_pdf_current_fy=6,
    ) == {
        "target_pdf_auto_acquired_count": 6,
        "target_pdf_auto_denominator_count": 10,
        "target_pdf_auto_denominator_scope": "active_specialty_schools",
        "target_pdf_auto_yield_pct": 60.0,
        "operator_reviewable_count": 6,
        "operator_reviewable_yield_pct": 60.0,
        "ship_gate_auto_yield_pct": 60.0,
        "ship_gate_operator_coverage_pct": 60.0,
        "ship_gate_metric_basis": "post_bootstrap_operator_reviewable_coverage",
        "ship_gate_status": "pass",
    }

    assert module.bootstrap_target_pdf_yield_metrics(
        schools_total=10,
        schools_with_target_pdf_current_fy=3,
        operator_reviewable_count=4,
    ) == {
        "target_pdf_auto_acquired_count": 3,
        "target_pdf_auto_denominator_count": 10,
        "target_pdf_auto_denominator_scope": "active_specialty_schools",
        "target_pdf_auto_yield_pct": 30.0,
        "operator_reviewable_count": 7,
        "operator_reviewable_yield_pct": 70.0,
        "ship_gate_auto_yield_pct": 60.0,
        "ship_gate_operator_coverage_pct": 60.0,
        "ship_gate_metric_basis": "post_bootstrap_operator_reviewable_coverage",
        "ship_gate_status": "pass",
    }

    assert module.bootstrap_target_pdf_yield_metrics(
        schools_total=0,
        schools_with_target_pdf_current_fy=0,
    ) == {
        "target_pdf_auto_acquired_count": 0,
        "target_pdf_auto_denominator_count": 0,
        "target_pdf_auto_denominator_scope": "active_specialty_schools",
        "target_pdf_auto_yield_pct": None,
        "operator_reviewable_count": 0,
        "operator_reviewable_yield_pct": None,
        "ship_gate_auto_yield_pct": 60.0,
        "ship_gate_operator_coverage_pct": 60.0,
        "ship_gate_metric_basis": "post_bootstrap_operator_reviewable_coverage",
        "ship_gate_status": "not_measured",
    }


def test_write_bootstrap_discovery_rca_batch_plan_writes_copy_paste_queue(tmp_path: Path, monkeypatch) -> None:
    evidence_log = tmp_path / "discovery_rejections.jsonl"
    evidence_log.write_text('{"school_id": 1}\n', encoding="utf-8")
    output_dir = tmp_path / "data" / "output" / "target-year-discovery"
    calls: list[dict[str, object]] = []

    def fake_build(session, **kwargs):  # noqa: ANN001, ANN003
        calls.append({"session": session, **kwargs})
        return {"total_candidates": 2, "items": [{"packet": {"school_id": 1}}]}

    def fake_render(plan):  # noqa: ANN001
        return json.dumps(plan, ensure_ascii=False, sort_keys=True)

    import eidp.scraper.discovery_rca_packet as rca_mod

    monkeypatch.setattr(rca_mod, "build_single_school_rca_batch_plan", fake_build)
    monkeypatch.setattr(rca_mod, "render_single_school_rca_batch_plan", fake_render)

    session = object()
    result = module.write_bootstrap_discovery_rca_batch_plan(
        session,
        evidence_log=evidence_log,
        output_dir=output_dir,
        target_fiscal_year=2026,
    )

    plan_path = Path(result["discovery_rca_batch_plan_path"])
    assert plan_path.name.endswith("-discovery-rca-batch-plan.json")
    assert plan_path.parent == output_dir
    assert result["discovery_rca_batch_plan_item_count"] == 1
    assert result["discovery_rca_batch_plan_total_candidates"] == 2
    assert json.loads(plan_path.read_text(encoding="utf-8"))["total_candidates"] == 2
    assert calls == [
        {
            "session": session,
            "evidence_log": evidence_log,
            "target_fiscal_year": 2026,
            "limit": module.DEFAULT_RCA_BATCH_LIMIT,
            "include_prompts": True,
        }
    ]


def test_write_bootstrap_discovery_rca_batch_plan_skips_missing_evidence(tmp_path: Path) -> None:
    result = module.write_bootstrap_discovery_rca_batch_plan(
        object(),
        evidence_log=tmp_path / "missing.jsonl",
        output_dir=tmp_path / "out",
        target_fiscal_year=2026,
    )

    assert result == {
        "discovery_rca_batch_plan_path": None,
        "discovery_rca_batch_plan_item_count": 0,
        "discovery_rca_batch_plan_total_candidates": 0,
        "discovery_rca_error": None,
    }


def test_step_rebuild_status_uses_specialty_school_denominator_for_ship_gate(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []
    evidence_log = tmp_path / "discovery.jsonl"

    class FakeSession:
        def commit(self) -> None:
            calls.append({"commit": True})

        def rollback(self) -> None:
            calls.append({"rollback": True})

        def close(self) -> None:
            calls.append({"close": True})

    def fake_rebuild(session, *, fiscal_year, school_type, discovery_evidence_path):  # noqa: ANN001
        calls.append(
            {
                "session": session,
                "fiscal_year": fiscal_year,
                "school_type": school_type,
                "discovery_evidence_path": discovery_evidence_path,
            }
        )
        return SimpleNamespace(rebuilt=3, excel_ready=1)

    def fake_compute_coverage(session, *, school_type, fiscal_year):  # noqa: ANN001
        calls.append({"coverage_session": session, "school_type": school_type, "fiscal_year": fiscal_year})
        return SimpleNamespace(
            totals=SimpleNamespace(
                schools_total=10,
                schools_with_target_pdf_current_fy=6,
            )
        )

    def fake_status_counts(session, *, fiscal_year, school_type):  # noqa: ANN001
        calls.append({"status_session": session, "school_type": school_type, "fiscal_year": fiscal_year})
        return {"publication_lag": 2, "target_year_unverified": 1}

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.pipeline.school_fiscal_year_status as status_mod
    import eidp.reports.coverage as coverage_mod

    fake_session = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(status_mod, "rebuild_school_fiscal_year_status", fake_rebuild)
    monkeypatch.setattr(status_mod, "school_fiscal_year_status_counts", fake_status_counts)
    monkeypatch.setattr(coverage_mod, "compute_coverage", fake_compute_coverage)
    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)

    result = module.step_rebuild_status(evidence_log=evidence_log, target_fiscal_year=2025)

    assert result == {
        "rebuilt": 3,
        "excel_ready": 1,
        "current_fy": 2025,
        "target_pdf_auto_acquired_count": 6,
        "target_pdf_auto_denominator_count": 10,
        "target_pdf_auto_denominator_scope": "active_specialty_schools",
        "target_pdf_auto_yield_pct": 60.0,
        "operator_reviewable_count": 9,
        "operator_reviewable_yield_pct": 90.0,
        "ship_gate_auto_yield_pct": 60.0,
        "ship_gate_operator_coverage_pct": 60.0,
        "ship_gate_metric_basis": "post_bootstrap_operator_reviewable_coverage",
        "ship_gate_status": "pass",
    }
    assert calls[0] == {
        "session": fake_session,
        "fiscal_year": 2025,
        "school_type": None,
        "discovery_evidence_path": evidence_log,
    }
    assert calls[1] == {"coverage_session": fake_session, "school_type": "専門学校", "fiscal_year": 2025}
    assert calls[2] == {"status_session": fake_session, "school_type": "専門学校", "fiscal_year": 2025}
