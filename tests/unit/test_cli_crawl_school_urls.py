from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from eidp.cli import app


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


def test_crawl_school_urls_dry_run_rolls_back(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    fake_session = FakeSession()

    import eidp.db.session as db_session
    import eidp.scraper.school_url_pipeline as pipeline

    def fake_run_school_url_auto_crawl(session, **kwargs):  # noqa: ANN001, ANN003
        calls["session"] = session
        calls["kwargs"] = kwargs
        return {"attempted": 1, "dry_run_auto": 1}

    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(pipeline, "run_school_url_auto_crawl", fake_run_school_url_auto_crawl)

    result = CliRunner().invoke(
        app,
        [
            "crawl-school-urls",
            "--limit",
            "1",
            "--prefecture",
            "東京都",
            "--dry-run",
            "--evidence-log",
            str(tmp_path / "evidence.jsonl"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"dry_run_auto": 1' in result.output
    assert calls["session"] is fake_session
    assert calls["kwargs"]["prefecture"] == "東京都"
    assert calls["kwargs"]["dry_run"] is True
    assert fake_session.commits == 0
    assert fake_session.rollbacks == 1
    assert fake_session.closed is True


def test_crawl_school_urls_rejects_bad_fetch_mode() -> None:
    result = CliRunner().invoke(app, ["crawl-school-urls", "--fetch-mode", "bad"])

    assert result.exit_code == 1
    assert "--fetch-mode must be one of" in result.output


def test_crawl_school_urls_help_explains_dry_run_still_fetches_network() -> None:
    result = CliRunner().invoke(app, ["crawl-school-urls", "--help"])

    assert result.exit_code == 0
    assert "fetches network" in result.output
