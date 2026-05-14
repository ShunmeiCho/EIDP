"""Database session management."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from eidp.config import settings


def _install_sqlite_connect_hook(target_engine: Engine) -> None:
    """Apply per-connection SQLite PRAGMAs (FK, busy_timeout, WAL).

    ``sqlite_bootstrap.bootstrap_sqlite`` only sets PRAGMAs on the connection
    used during bootstrap. Every subsequent process / engine that opens the
    same SQLite file would otherwise default to ``foreign_keys=OFF`` and
    ``busy_timeout=0``, which would silently break the 4-table append-only
    contracts coming in Sprint 8.2 (audit, fiscal-year override) and risk
    lock-contention freezes between Streamlit UI and weekly_run.

    Registering a ``connect`` listener guarantees every new DBAPI connection
    runs the PRAGMAs, regardless of who created the engine.
    """
    if target_engine.dialect.name != "sqlite":
        return

    @event.listens_for(target_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            # journal_mode=WAL persists in the database file metadata once set
            # by bootstrap, so this is a belt-and-suspenders no-op on already-
            # WAL files but a useful safety net for fresh databases.
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


engine = create_engine(settings.database_url, echo=False)
_install_sqlite_connect_hook(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def commit_session(session: Session) -> None:
    """Explicitly commit. Call after all operations succeed."""
    session.commit()
