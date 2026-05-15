from __future__ import annotations

from typing import Any

from eidp.db import session as db_session


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.committed = False

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.committed = True


def test_get_session_closes_session(monkeypatch: Any) -> None:
    fake = _FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake)

    generator = db_session.get_session()
    assert next(generator) is fake

    try:
        next(generator)
    except StopIteration:
        pass

    assert fake.closed is True


def test_commit_session_commits() -> None:
    fake = _FakeSession()

    db_session.commit_session(fake)  # type: ignore[arg-type]

    assert fake.committed is True
