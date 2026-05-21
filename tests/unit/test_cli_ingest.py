from __future__ import annotations

from typer.testing import CliRunner

from eidp.cli import _configure_utf8_stdio, app


class FakeStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_configure_utf8_stdio_sets_strict_utf8_errors() -> None:
    stdout = FakeStream()
    stderr = FakeStream()

    _configure_utf8_stdio(stdout, stderr)

    assert stdout.calls == [{"encoding": "utf-8", "errors": "strict"}]
    assert stderr.calls == [{"encoding": "utf-8", "errors": "strict"}]


def test_ingest_pdfs_forwards_document_ids(monkeypatch) -> None:
    session = FakeSession()
    captured: dict[str, object] = {}

    monkeypatch.setattr("eidp.db.session.SessionLocal", lambda: session)

    def fake_run_ingestion(
        fake_session: FakeSession,
        *,
        batch_size: int,
        document_ids: list[int] | None,
        target_fiscal_year: int | None,
        evidence_path=None,
    ) -> dict[str, int]:
        captured["session"] = fake_session
        captured["batch_size"] = batch_size
        captured["document_ids"] = document_ids
        captured["target_fiscal_year"] = target_fiscal_year
        captured["evidence_path"] = evidence_path
        return {"processed": 2, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    monkeypatch.setattr("eidp.pipeline.ingest.run_ingestion", fake_run_ingestion)

    result = CliRunner().invoke(
        app,
        ["ingest-pdfs", "--batch-size", "5", "--document-id", "101", "--document-id", "202"],
    )

    assert result.exit_code == 0
    assert captured["session"] is session
    assert captured["batch_size"] == 5
    assert captured["document_ids"] == [101, 202]
    assert captured["target_fiscal_year"] is None
    # default evidence path is forwarded (non-None Path), regardless of file existence
    assert captured["evidence_path"] is not None
    assert session.committed
    assert session.closed
    assert not session.rolled_back


def test_ingest_pdfs_forwards_target_fiscal_year(monkeypatch) -> None:
    session = FakeSession()
    captured: dict[str, object] = {}

    monkeypatch.setattr("eidp.db.session.SessionLocal", lambda: session)

    def fake_run_ingestion(
        fake_session: FakeSession,
        *,
        batch_size: int,
        document_ids: list[int] | None,
        target_fiscal_year: int | None,
        evidence_path=None,
    ) -> dict[str, int]:
        captured["session"] = fake_session
        captured["batch_size"] = batch_size
        captured["document_ids"] = document_ids
        captured["target_fiscal_year"] = target_fiscal_year
        captured["evidence_path"] = evidence_path
        return {"processed": 0, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    monkeypatch.setattr("eidp.pipeline.ingest.run_ingestion", fake_run_ingestion)

    result = CliRunner().invoke(
        app,
        ["ingest-pdfs", "--target-fiscal-year", "2025"],
    )

    assert result.exit_code == 0
    assert captured["session"] is session
    assert captured["batch_size"] == 50
    assert captured["document_ids"] is None
    assert captured["target_fiscal_year"] == 2025
    assert captured["evidence_path"] is not None
    assert session.committed
    assert session.closed
    assert not session.rolled_back
