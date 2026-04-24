from __future__ import annotations

from typer.testing import CliRunner

from eidp.cli import app


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


def test_ingest_pdfs_forwards_document_ids(monkeypatch) -> None:
    session = FakeSession()
    captured: dict[str, object] = {}

    monkeypatch.setattr("eidp.db.session.SessionLocal", lambda: session)

    def fake_run_ingestion(
        fake_session: FakeSession,
        *,
        batch_size: int,
        document_ids: list[int] | None,
    ) -> dict[str, int]:
        captured["session"] = fake_session
        captured["batch_size"] = batch_size
        captured["document_ids"] = document_ids
        return {"processed": 2, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    monkeypatch.setattr("eidp.pipeline.ingest.run_ingestion", fake_run_ingestion)

    result = CliRunner().invoke(
        app,
        ["ingest-pdfs", "--batch-size", "5", "--document-id", "101", "--document-id", "202"],
    )

    assert result.exit_code == 0
    assert captured == {
        "session": session,
        "batch_size": 5,
        "document_ids": [101, 202],
    }
    assert session.committed
    assert session.closed
    assert not session.rolled_back
