"""Dev-only one-time migration from Postgres to the Sprint 8 SQLite DB.

This script exists for the owner question "keep the existing 116 docs or start
empty?" The operator PC may start with empty documents, but dev can use this
tool to produce a SQLite database carrying the existing documents and revision
chains for validation.

The copy is deliberately boring:

* table order follows ``Base.metadata.sorted_tables`` so FK parents land first;
* rows are copied column-for-column, including primary keys, revisions,
  ``is_current`` flags, audit IDs, and confidence breakdown JSON;
* an existing primary-key row is skipped, making reruns idempotent;
* the target must be SQLite. Source can be Postgres in real use or SQLite in
  tests.

It is not an online sync tool. It does not update existing rows or reconcile
conflicts; if the source changes after the first run, rebuild the target DB or
inspect the report before using the migrated file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Table

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import Base  # noqa: E402
from eidp.db.sqlite_bootstrap import bootstrap_sqlite  # noqa: E402


@dataclass(frozen=True)
class TableMigrationResult:
    table: str
    source_rows: int
    inserted_rows: int
    skipped_rows: int
    target_rows: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "table": self.table,
            "source_rows": self.source_rows,
            "inserted_rows": self.inserted_rows,
            "skipped_rows": self.skipped_rows,
            "target_rows": self.target_rows,
        }


@dataclass(frozen=True)
class MigrationReport:
    tables: tuple[TableMigrationResult, ...]
    dry_run: bool = False

    @property
    def by_table(self) -> dict[str, TableMigrationResult]:
        return {result.table: result for result in self.tables}

    @property
    def total_source_rows(self) -> int:
        return sum(result.source_rows for result in self.tables)

    @property
    def total_inserted(self) -> int:
        return sum(result.inserted_rows for result in self.tables)

    @property
    def total_skipped(self) -> int:
        return sum(result.skipped_rows for result in self.tables)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "total_source_rows": self.total_source_rows,
            "total_inserted": self.total_inserted,
            "total_skipped": self.total_skipped,
            "tables": [result.as_dict() for result in self.tables],
        }


def _count_rows(session: Session, table: Table) -> int:
    return int(session.execute(select(func.count()).select_from(table)).scalar_one())


def _stream_rows(session: Session, table: Table) -> Iterator[dict[str, Any]]:
    """Yield source rows ordered by primary key, streaming to avoid
    materializing the full table in RAM. ``yield_per`` keeps the open
    cursor windowed at 1k rows."""
    pk_columns = list(table.primary_key.columns)
    order_columns = pk_columns or list(table.columns)
    statement = select(table).order_by(*order_columns).execution_options(yield_per=1000)
    for row in session.execute(statement).mappings():
        yield dict(row)


def _existing_pk_set(session: Session, table: Table) -> set[Any]:
    """Return the set of primary keys already present in ``table``.

    For composite primary keys we tuple the values in column order.
    Pre-loading once removes the per-row N+1 SELECT ``_row_exists`` did
    on every source row — material on the 116-doc dev database where
    DepartmentYearly alone has thousands of revisions.
    """
    pk_columns = list(table.primary_key.columns)
    if not pk_columns:
        return set()
    rows = session.execute(select(*pk_columns)).all()
    if len(pk_columns) == 1:
        return {row[0] for row in rows}
    return {tuple(row) for row in rows}


def _row_pk(table: Table, row: dict[str, Any]) -> Any:
    pk_columns = list(table.primary_key.columns)
    if not pk_columns:
        return None
    if len(pk_columns) == 1:
        return row[pk_columns[0].name]
    return tuple(row[column.name] for column in pk_columns)


_INSERT_BATCH_SIZE = 500


def migrate_table(
    source: Session,
    target: Session,
    table: Table,
    *,
    dry_run: bool = False,
) -> TableMigrationResult:
    """Copy a single table from ``source`` to ``target`` idempotently.

    Pre-loads target primary keys once, streams source rows via
    ``yield_per``, and batches inserts via ``executemany`` so the runner
    handles the 116-doc dev DB without flooding memory or doing N+1
    existence checks.
    """
    pk_columns = list(table.primary_key.columns)
    existing_pks = _existing_pk_set(target, table) if pk_columns else set()

    pending: list[dict[str, Any]] = []
    inserted = 0
    skipped = 0
    source_rows = 0

    def _flush() -> None:
        if pending and not dry_run:
            target.execute(table.insert(), pending)
        pending.clear()

    for row in _stream_rows(source, table):
        source_rows += 1
        pk = _row_pk(table, row)
        if pk_columns and pk in existing_pks:
            skipped += 1
            continue
        inserted += 1
        if pk_columns:
            existing_pks.add(pk)
        pending.append(row)
        if len(pending) >= _INSERT_BATCH_SIZE:
            _flush()

    _flush()

    target.flush()
    return TableMigrationResult(
        table=table.name,
        source_rows=source_rows,
        inserted_rows=inserted,
        skipped_rows=skipped,
        target_rows=_count_rows(target, table),
    )


def migrate_sessions(
    source: Session,
    target: Session,
    *,
    dry_run: bool = False,
    tables: list[Table] | None = None,
) -> MigrationReport:
    """Copy ORM-managed tables from ``source`` to ``target``.

    ``tables`` is an injection seam for narrow tests; production uses all
    metadata tables sorted by FK dependency.
    """
    selected_tables = tuple(tables or Base.metadata.sorted_tables)
    results: list[TableMigrationResult] = []
    try:
        for table in selected_tables:
            results.append(migrate_table(source, target, table, dry_run=dry_run))
        if dry_run:
            target.rollback()
        else:
            target.commit()
    except Exception:
        target.rollback()
        raise
    return MigrationReport(tuple(results), dry_run=dry_run)


def _ensure_sqlite_target(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            f"target database must be SQLite, got dialect={engine.dialect.name!r}"
        )


def migrate_database(
    *,
    source_url: str,
    sqlite_url: str,
    bootstrap: bool = True,
    dry_run: bool = False,
) -> MigrationReport:
    source_engine = create_engine(source_url, future=True)
    target_engine = create_engine(sqlite_url, future=True)
    _ensure_sqlite_target(target_engine)

    try:
        if bootstrap:
            # bootstrap_sqlite is idempotent and the partial-index +
            # PRAGMA + alembic-stamp work it does is exactly what
            # dry-run needs to validate the schema. Skipping it on
            # dry-run reintroduces the 8.1 partial-index gotcha
            # (idx_dept_yearly_current sqlite_where missing).
            bootstrap_sqlite(target_engine)

        with Session(source_engine) as source, Session(target_engine) as target:
            return migrate_sessions(source, target, dry_run=dry_run)
    finally:
        source_engine.dispose()
        target_engine.dispose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        default=os.environ.get("EIDP_SOURCE_DATABASE_URL"),
        help="Source database URL. Defaults to EIDP_SOURCE_DATABASE_URL.",
    )
    parser.add_argument(
        "--sqlite-url",
        default=os.environ.get("EIDP_SQLITE_DATABASE_URL"),
        help="Target SQLite URL. Defaults to EIDP_SQLITE_DATABASE_URL.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required for writes. Prevents accidental production-side runs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.source_url:
        raise SystemExit("--source-url or EIDP_SOURCE_DATABASE_URL is required")
    if not args.sqlite_url:
        raise SystemExit("--sqlite-url or EIDP_SQLITE_DATABASE_URL is required")
    if not args.dry_run and not args.yes:
        raise SystemExit("Refusing to write without --yes. Use --dry-run for a read-only report.")

    report = migrate_database(
        source_url=args.source_url,
        sqlite_url=args.sqlite_url,
        bootstrap=not args.skip_bootstrap,
        dry_run=args.dry_run,
    )
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
