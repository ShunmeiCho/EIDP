from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.locking import acquire_lock


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_discover_pdfs_cli_uses_strict_target_fiscal_year(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    fake_session = FakeSession()

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.scraper.pdf_discovery as pdf_discovery

    def fake_run_pdf_discovery(session, storage_dir, **kwargs):  # noqa: ANN001, ANN003
        calls["session"] = session
        calls["storage_dir"] = storage_dir
        calls["kwargs"] = kwargs
        return {"downloaded": 0}

    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(pdf_discovery, "run_pdf_discovery", fake_run_pdf_discovery)

    result = CliRunner().invoke(
        app,
        [
            "discover-pdfs",
            "--storage-dir",
            str(tmp_path / "pdfs"),
            "--batch-size",
            "3",
            "--evidence-log",
            str(tmp_path / "evidence.jsonl"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls["session"] is fake_session
    assert calls["kwargs"]["target_fiscal_year"] == 2026
    assert calls["kwargs"]["strict_target_fiscal_year"] is True
    assert fake_session.commits == 1
    assert fake_session.rollbacks == 0
    assert fake_session.closed is True


def test_weekly_update_uses_strict_target_fiscal_year(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    fake_session = FakeSession()

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.excel.exporter as exporter
    import eidp.pipeline.ingest as ingest
    import eidp.scraper.pdf_discovery as pdf_discovery
    import eidp.scraper.url_discovery as url_discovery

    def fake_run_pdf_discovery(session, storage_dir, **kwargs):  # noqa: ANN001, ANN003
        calls["session"] = session
        calls["storage_dir"] = storage_dir
        calls["kwargs"] = kwargs
        return {"downloaded": 0}

    monkeypatch.setattr(config_mod.settings, "target_fiscal_year", 2026)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(url_discovery, "verify_urls_sync", lambda *_args, **_kwargs: {"verified": 0})
    monkeypatch.setattr(
        url_discovery,
        "get_discovery_stats",
        lambda _session: {"verified_disclosure": 0, "coverage_verified": "0%"},
    )
    monkeypatch.setattr(pdf_discovery, "run_pdf_discovery", fake_run_pdf_discovery)
    monkeypatch.setattr(ingest, "run_ingestion", lambda *_args, **_kwargs: {"processed": 0})
    monkeypatch.setattr(exporter, "export_master_workbook", lambda *_args, **_kwargs: {"exported": 0})

    result = CliRunner().invoke(
        app,
        [
            "weekly-update",
            "--storage-dir",
            str(tmp_path / "pdfs"),
            "--export-path",
            str(tmp_path / "weekly.xlsx"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls["session"] is fake_session
    assert calls["kwargs"]["target_fiscal_year"] == 2026
    assert calls["kwargs"]["strict_target_fiscal_year"] is True
    assert fake_session.commits == 3
    assert fake_session.rollbacks == 0
    assert fake_session.closed is True


def test_weekly_update_refuses_when_app_lock_is_held(monkeypatch, tmp_path: Path) -> None:
    fake_session = FakeSession()
    data_dir = tmp_path / "data"
    lock_path = data_dir / ".lock"

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.excel.exporter as exporter
    import eidp.pipeline.ingest as ingest
    import eidp.scraper.pdf_discovery as pdf_discovery
    import eidp.scraper.url_discovery as url_discovery

    monkeypatch.setattr(config_mod.settings, "data_dir", data_dir)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(url_discovery, "verify_urls_sync", lambda *_args, **_kwargs: {"verified": 0})
    monkeypatch.setattr(
        url_discovery,
        "get_discovery_stats",
        lambda _session: {"verified_disclosure": 0, "coverage_verified": "0%"},
    )
    monkeypatch.setattr(pdf_discovery, "run_pdf_discovery", lambda *_args, **_kwargs: {"downloaded": 0})
    monkeypatch.setattr(ingest, "run_ingestion", lambda *_args, **_kwargs: {"processed": 0})
    monkeypatch.setattr(exporter, "export_master_workbook", lambda *_args, **_kwargs: {"exported": 0})

    with acquire_lock(lock_path, owner="ui"):
        result = CliRunner().invoke(
            app,
            [
                "weekly-update",
                "--storage-dir",
                str(tmp_path / "pdfs"),
                "--export-path",
                str(tmp_path / "weekly.xlsx"),
            ],
        )

    assert result.exit_code == 5
    assert "another EIDP process is running" in result.output
    assert fake_session.commits == 0
    assert fake_session.rollbacks == 0
    assert fake_session.closed is False


def test_import_excel_refuses_when_app_lock_is_held(monkeypatch, tmp_path: Path) -> None:
    fake_session = FakeSession()
    data_dir = tmp_path / "data"
    lock_path = data_dir / ".lock"

    import eidp.config as config_mod
    import eidp.db.session as db_session
    import eidp.excel.importer as importer

    monkeypatch.setattr(config_mod.settings, "data_dir", data_dir)
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(importer, "import_all", lambda *_args, **_kwargs: {"sheet": {"rows": 0}})

    with acquire_lock(lock_path, owner="ui"):
        result = CliRunner().invoke(app, ["import-excel", str(tmp_path / "master.xlsx")])

    assert result.exit_code == 5
    assert "another EIDP process is running" in result.output
    assert fake_session.commits == 0
    assert fake_session.rollbacks == 0
    assert fake_session.closed is False
