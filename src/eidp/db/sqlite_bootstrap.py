"""SQLite bootstrap — owner-mandated path that bypasses PG-only alembic migrations.

Phase 8.1 (Sprint 8): the existing alembic chain (cbb204a26301 et al.) uses
PostgreSQL-only constructs (`postgresql_using`, raw `UPDATE ... FROM`, etc.) that
fail on SQLite. For Windows business-user deployment we therefore:

1. Create all tables from ORM metadata (`Base.metadata.create_all`).
2. Re-create the null-safe expression unique index that lives in migration
   ``94884a1f8586_add_null_safe_department_natural_key_`` but is NOT expressed
   in ORM metadata. SQLite supports expression indexes with ``COALESCE`` so we
   reproduce it via raw SQL with ``IF NOT EXISTS`` for idempotency.
3. Apply runtime PRAGMAs (WAL, foreign_keys, busy_timeout) for safer
   single-file SQLite operation under the UI + weekly_run sharing pattern.
4. Stamp alembic ``head`` so the schema appears already-migrated and future
   migrations only run for additive changes.

This module deliberately does NOT touch SupportRecipient/SchoolYearStatus
revision rework, audit tables, or confidence_breakdown — those land in
Phase 8.2.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, text

from eidp.db.models import Base

_NULL_SAFE_DEPT_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_department_natural_key_nullsafe
ON department (
    school_id,
    canonical_name,
    COALESCE(course_type, ''),
    COALESCE(course_name, ''),
    COALESCE(duration_years, 0)
)
"""

_SQLITE_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
)


def _resolve_alembic_ini() -> Path:
    """Locate ``alembic.ini`` in deployment-aware order.

    Priority:
      1. ``settings.app_root / "alembic.ini"`` — the operator install
         layout where the ZIP includes ``alembic.ini`` next to ``data``.
      2. ``Path(__file__).resolve().parents[3] / "alembic.ini"`` — repo
         source checkout, ``src/eidp/db/sqlite_bootstrap.py`` →
         repo root via ``parents[3]``. Last resort.

    Returns the first existing path; if none exist returns the
    settings.app_root candidate so the caller surfaces a clear "no such
    file" error pointing at the operator-visible location.
    """
    try:
        from eidp.config import settings
        primary = Path(settings.app_root) / "alembic.ini"
    except Exception:
        primary = None

    fallback = Path(__file__).resolve().parents[3] / "alembic.ini"

    if primary is not None and primary.is_file():
        return primary
    if fallback.is_file():
        return fallback
    return primary if primary is not None else fallback


def is_sqlite(engine: Engine) -> bool:
    """Return True if engine is bound to a SQLite database."""
    return engine.dialect.name == "sqlite"


def _sqlite_main_file(engine: Engine) -> Path | None:
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    return Path(database).expanduser()


def _refuse_orphaned_sqlite_sidecars(engine: Engine) -> None:
    db_path = _sqlite_main_file(engine)
    if db_path is None or db_path.exists():
        return
    sidecars = [Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]
    existing = [path for path in sidecars if path.exists()]
    if existing:
        rels = ", ".join(str(path) for path in existing)
        raise RuntimeError(
            "main SQLite database file is missing but SQLite sidecar files exist; "
            f"refusing to create an empty replacement database at {db_path}. "
            f"Move or restore the sidecar files first: {rels}"
        )


def apply_sqlite_pragmas(engine: Engine) -> None:
    """Apply WAL / FK / busy_timeout PRAGMAs on a SQLite engine.

    No-op for non-SQLite dialects.
    """
    if not is_sqlite(engine):
        return
    with engine.connect() as conn:
        for stmt in _SQLITE_PRAGMAS:
            conn.execute(text(stmt))
        conn.commit()


def create_null_safe_dept_index(engine: Engine) -> None:
    """Create the null-safe expression unique index on department.

    This index lives in migration 94884a1f8586 as raw SQL and is NOT in ORM
    metadata, so ``create_all`` would skip it. We reproduce it idempotently
    via ``CREATE UNIQUE INDEX IF NOT EXISTS``.
    """
    with engine.connect() as conn:
        conn.execute(text(_NULL_SAFE_DEPT_INDEX_DDL))
        conn.commit()


def stamp_alembic_head(engine: Engine, alembic_ini: Path | None = None) -> None:
    """Mark the database as being at alembic ``head`` revision.

    We never run ``alembic upgrade head`` on SQLite because the existing
    migration chain (cbb204a26301) uses PG-only constructs. Stamping marks
    the schema as already-migrated so future additive migrations apply
    cleanly.

    Parameters
    ----------
    engine : Engine
        Target SQLite engine (the URL is passed to alembic via the engine).
    alembic_ini : Path | None
        Path to alembic.ini. If None, falls back to repo-root ``alembic.ini``.
    """
    from alembic import command
    from alembic.config import Config

    if alembic_ini is None:
        alembic_ini = _resolve_alembic_ini()

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    # Tell migrations/env.py to respect the URL we just set instead of
    # overriding it back to settings.database_url (which is typically the dev
    # Postgres URL).
    cfg.attributes["preserve_url_override"] = True
    command.stamp(cfg, "head")


def bootstrap_sqlite(engine: Engine, *, alembic_ini: Path | None = None) -> None:
    """Idempotent bootstrap for a fresh SQLite database.

    Order matters:
      1. ``create_all`` — builds all 12 tables + ORM-expressed indexes
         (including ``idx_dept_yearly_current`` partial index, which now
         carries both ``postgresql_where`` and ``sqlite_where`` predicates).
      2. ``create_null_safe_dept_index`` — adds the migration-only expression
         index that ORM cannot express.
      3. ``apply_sqlite_pragmas`` — WAL, FK, busy_timeout.
      4. ``stamp_alembic_head`` — mark schema as up-to-date.

    Re-runnable: every step is idempotent (``checkfirst=True`` for tables,
    ``IF NOT EXISTS`` for the expression index, PRAGMAs are no-ops if already
    set, ``stamp head`` is no-op when already at head).
    """
    if not is_sqlite(engine):
        raise RuntimeError(
            f"bootstrap_sqlite requires a SQLite engine, got dialect={engine.dialect.name!r}"
        )

    _refuse_orphaned_sqlite_sidecars(engine)
    Base.metadata.create_all(engine, checkfirst=True)
    create_null_safe_dept_index(engine)
    apply_sqlite_pragmas(engine)
    stamp_alembic_head(engine, alembic_ini=alembic_ini)
