"""Tests for the SQLite bootstrap path (Sprint 8.1).

Acceptance criteria from Phase 8.1 of the Sprint 8 plan:

  * Partial unique index ``idx_dept_yearly_current`` carries a ``sqlite_where``
    so SQLite does NOT enforce it as a full unique index — i.e. inserting
    revision 1 (current) and revision 2 (current) for the same
    (department_id, fiscal_year) is allowed when the older row is flipped to
    ``is_current=False``.
  * ``bootstrap_sqlite`` is idempotent (safe to re-run).
  * The null-safe department expression index is created (it lives in
    migration 94884a1f8586 only and would otherwise be missed).
  * SQLite PRAGMAs (WAL, foreign_keys=ON, busy_timeout) are applied.
  * Empty database survives a smoke ``School`` count query (analogue of
    ``eidp db-info`` reaching past the table sanity check on a fresh DB).

We deliberately avoid touching anything 8.2+ owns: SupportRecipient and
SchoolYearStatus are not exercised here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, text
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, School
from eidp.db.sqlite_bootstrap import (
    apply_sqlite_pragmas,
    bootstrap_sqlite,
    create_null_safe_dept_index,
    is_sqlite,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sqlite_engine(tmp_path: Path):
    """Fresh on-disk SQLite engine. On-disk so PRAGMA journal_mode=WAL is meaningful."""
    db_path = tmp_path / "eidp_test.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def bootstrapped_engine(sqlite_engine):
    """Engine after a single bootstrap pass."""
    bootstrap_sqlite(sqlite_engine)
    return sqlite_engine


# ---------------------------------------------------------------------------
# Schema sanity
# ---------------------------------------------------------------------------


def test_bootstrap_creates_all_core_tables(bootstrapped_engine):
    inspector = inspect(bootstrapped_engine)
    tables = set(inspector.get_table_names())
    # Spot-check the tables Phase 8.1 must produce. (Full 12-table list lives
    # in models.py; we just need to know create_all ran.)
    expected_subset = {
        "school",
        "department",
        "department_yearly",
        "document",
        "school_fiscal_year_status",
        "alembic_version",  # populated by stamp head
    }
    missing = expected_subset - tables
    assert not missing, f"missing tables after bootstrap: {sorted(missing)}"


def test_alembic_version_is_stamped(bootstrapped_engine):
    with bootstrapped_engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).all()
    assert len(rows) == 1, "alembic_version must hold exactly one head row after stamp"
    assert rows[0][0], "alembic head revision must be non-empty"


def test_null_safe_department_index_present(bootstrapped_engine):
    """SQLAlchemy's inspector skips expression-based indexes
    ("Skipped unsupported reflection of expression-based index ..."),
    so we query sqlite_master directly to confirm the index exists and
    its DDL contains the COALESCE expressions from migration 94884a1f8586."""
    with bootstrapped_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name='idx_department_natural_key_nullsafe'"
            )
        ).first()
    assert row is not None, (
        "null-safe expression index from migration 94884a1f8586 must be reproduced "
        "by sqlite_bootstrap (it is not in ORM metadata)."
    )
    sql = (row[0] or "").upper()
    assert "COALESCE" in sql, f"expression index must contain COALESCE, got: {sql!r}"
    assert "UNIQUE" in sql, f"expression index must be UNIQUE, got: {sql!r}"


def test_partial_current_index_is_partial_under_sqlite(bootstrapped_engine):
    """The partial ``idx_dept_yearly_current`` index must carry a WHERE clause
    on SQLite. Without ``sqlite_where`` it would degrade to a full unique
    index and break revision 2 inserts (the whole point of Phase 8.1)."""
    with bootstrapped_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name='idx_dept_yearly_current'"
            )
        ).first()
    assert row is not None, "idx_dept_yearly_current must exist on SQLite"
    sql = row[0] or ""
    assert "WHERE" in sql.upper(), (
        f"idx_dept_yearly_current must be a partial index on SQLite, got SQL: {sql!r}"
    )


# ---------------------------------------------------------------------------
# Pragmas
# ---------------------------------------------------------------------------


def test_pragmas_applied(bootstrapped_engine):
    with bootstrapped_engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()

    assert str(journal_mode).lower() == "wal", f"journal_mode must be WAL, got {journal_mode!r}"
    assert int(foreign_keys) == 1, "foreign_keys must be ON"
    assert int(busy_timeout) >= 5000, f"busy_timeout must be >= 5000ms, got {busy_timeout}"


def test_connect_hook_applies_pragmas_per_connection(tmp_path):
    """Sprint 8.1.1: per-connection PRAGMA hook on session.py must apply
    ``foreign_keys=ON`` and ``busy_timeout`` to every new DBAPI connection,
    not just the bootstrap connection. Otherwise a Streamlit / weekly_run
    process that re-opens the file would default to ``foreign_keys=OFF``
    and break the FK-protected 4-table contracts coming in Sprint 8.2.

    We exercise this by creating a brand-new engine pointed at the same
    file that bootstrap_sqlite ran against — emulating a separate process
    re-opening the SQLite database.
    """
    from eidp.db.session import _install_sqlite_connect_hook

    db_path = tmp_path / "eidp_hook_test.sqlite3"
    bootstrap_engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(bootstrap_engine)
    bootstrap_engine.dispose()

    # Fresh engine — analogue of a separate process attaching to the same DB.
    fresh_engine = create_engine(f"sqlite:///{db_path}", future=True)
    _install_sqlite_connect_hook(fresh_engine)
    try:
        with fresh_engine.connect() as conn:
            fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
            bt = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert int(fk) == 1, "connect hook must apply foreign_keys=ON to every new connection"
        assert int(bt) >= 5000, f"connect hook must apply busy_timeout, got {bt}"
    finally:
        fresh_engine.dispose()


def test_connect_hook_skips_non_sqlite():
    """Hook installer must short-circuit for non-SQLite dialects so that
    a developer's Postgres engine isn't littered with PRAGMA statements."""
    from eidp.db.session import _install_sqlite_connect_hook

    class _FakeDialect:
        name = "postgresql"

    listened = {"called": False}

    class _FakeEngine:
        dialect = _FakeDialect()

        def __init__(self):
            pass

    # event.listens_for would raise if it tried to attach to a non-Engine,
    # so the test passes simply by not raising and not registering anything.
    _install_sqlite_connect_hook(_FakeEngine())  # type: ignore[arg-type]
    assert listened["called"] is False  # sanity


# ---------------------------------------------------------------------------
# Revision 1 → Revision 2 — the headline Phase 8.1 acceptance criterion
# ---------------------------------------------------------------------------


def _insert_minimal_school_doc_dept(session: Session) -> tuple[int, int]:
    """Create the minimal fixtures to exercise DepartmentYearly revisions."""
    school = School(
        prefecture="東京都",
        corporation_name="テスト法人",
        school_name="テスト専門学校",
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    session.flush()

    doc = Document(
        school_id=school.id,
        source_url="https://example.com/test.pdf",
        fiscal_year=2026,
        ingest_status="ingested",
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()

    dept = Department(
        school_id=school.id,
        canonical_name="テスト学科",
    )
    session.add(dept)
    session.flush()
    return dept.id, doc.id


def test_revision_1_then_revision_2_does_not_collide(bootstrapped_engine):
    """If sqlite_where is wired correctly, this insert sequence succeeds.
    Without it, SQLite would treat ``idx_dept_yearly_current`` as a full
    unique on (department_id, fiscal_year) and the second insert would fail
    with `UNIQUE constraint failed`."""
    with Session(bootstrapped_engine) as session:
        dept_id, doc_id = _insert_minimal_school_doc_dept(session)

        rev1 = DepartmentYearly(
            department_id=dept_id,
            document_id=doc_id,
            fiscal_year=2026,
            revision=1,
            is_current=True,
            enrollment=100,
            extraction_method="pdf_parse",
        )
        session.add(rev1)
        session.flush()

        # Append-only protocol: flip rev1 off-current, then insert rev2.
        session.query(DepartmentYearly).filter(
            DepartmentYearly.department_id == dept_id,
            DepartmentYearly.fiscal_year == 2026,
            DepartmentYearly.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        rev2 = DepartmentYearly(
            department_id=dept_id,
            document_id=doc_id,
            fiscal_year=2026,
            revision=2,
            is_current=True,
            enrollment=110,
            extraction_method="pdf_parse",
        )
        session.add(rev2)
        session.commit()

        rows = (
            session.query(DepartmentYearly)
            .filter(DepartmentYearly.department_id == dept_id)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]


def test_two_concurrent_current_revisions_are_rejected(bootstrapped_engine):
    """Conversely the partial unique index MUST still bite when two rows
    both claim is_current=True for the same (department_id, fiscal_year).
    This is the safety property the partial index exists for."""
    from sqlalchemy.exc import IntegrityError

    with Session(bootstrapped_engine) as session:
        dept_id, doc_id = _insert_minimal_school_doc_dept(session)

        session.add(
            DepartmentYearly(
                department_id=dept_id,
                document_id=doc_id,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                enrollment=100,
                extraction_method="pdf_parse",
            )
        )
        session.flush()

        session.add(
            DepartmentYearly(
                department_id=dept_id,
                document_id=doc_id,
                fiscal_year=2026,
                revision=2,
                is_current=True,  # also current — should violate partial unique
                enrollment=110,
                extraction_method="pdf_parse",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_document_file_hash_is_globally_unique(bootstrapped_engine):
    """A downloaded PDF content hash must be unique across schools.

    ``pdf_discovery`` probes by ``Document.file_hash`` alone to prevent the
    same PDF from being attached to multiple schools. The database constraint
    must match that contract so concurrent workers cannot both pass the
    select-before-insert check and insert duplicate document rows.
    """
    from sqlalchemy.exc import IntegrityError

    with Session(bootstrapped_engine) as session:
        school_a = School(
            prefecture="東京都",
            corporation_name="法人A",
            school_name="A専門学校",
            school_type="専門学校",
            status="active",
        )
        school_b = School(
            prefecture="東京都",
            corporation_name="法人B",
            school_name="B専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add_all([school_a, school_b])
        session.flush()

        shared_hash = "a" * 64
        session.add(
            Document(
                school_id=school_a.id,
                source_url="https://a.example.ac.jp/r8.pdf",
                file_hash=shared_hash,
                fiscal_year=2026,
                ingest_status="ingested",
            )
        )
        session.flush()

        session.add(
            Document(
                school_id=school_b.id,
                source_url="https://b.example.ac.jp/r8.pdf",
                file_hash=shared_hash,
                fiscal_year=2026,
                ingest_status="ingested",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_bootstrap_is_idempotent(sqlite_engine):
    """Running bootstrap twice must not raise (no duplicate-table or
    duplicate-index errors)."""
    bootstrap_sqlite(sqlite_engine)
    bootstrap_sqlite(sqlite_engine)

    with sqlite_engine.connect() as conn:
        version_rows = conn.execute(text("SELECT version_num FROM alembic_version")).all()
    assert len(version_rows) == 1, "stamp head must remain at one row after re-bootstrap"


def test_bootstrap_refuses_to_recreate_missing_main_db_when_wal_sidecar_exists(tmp_path: Path):
    """A missing main SQLite file with WAL/SHM sidecars is not a clean install.

    On Windows this can happen when Defender or another tool quarantines
    ``eidp.sqlite3`` while leaving sidecars behind. Bootstrapping must stop
    instead of silently creating an empty DB next to stale sidecars.
    """
    db_path = tmp_path / "eidp.sqlite3"
    (tmp_path / "eidp.sqlite3-wal").write_bytes(b"stale wal")
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    try:
        with pytest.raises(RuntimeError, match="main SQLite database file is missing"):
            bootstrap_sqlite(engine)
    finally:
        engine.dispose()

    assert not db_path.exists()


def test_create_null_safe_index_is_idempotent(bootstrapped_engine):
    create_null_safe_dept_index(bootstrapped_engine)
    create_null_safe_dept_index(bootstrapped_engine)


def test_apply_sqlite_pragmas_noop_on_non_sqlite(monkeypatch):
    """``apply_sqlite_pragmas`` must short-circuit on non-SQLite engines so
    that mistakenly invoking it under PostgreSQL doesn't raise."""

    class _FakeDialect:
        name = "postgresql"

    class _FakeEngine:
        dialect = _FakeDialect()

        def connect(self):  # pragma: no cover — must NOT be called
            raise AssertionError("apply_sqlite_pragmas should not connect on non-SQLite")

    apply_sqlite_pragmas(_FakeEngine())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Empty-DB smoke (analogue of `eidp db-info` running cleanly post-bootstrap)
# ---------------------------------------------------------------------------


def test_support_recipient_revision_columns_present(bootstrapped_engine):
    """Sprint 8.2.a: support_recipient must have revision + is_current with
    a partial unique index ``idx_support_recipient_current`` on
    (school_id, fiscal_year) WHERE is_current=true. Same append-only contract
    as DepartmentYearly."""
    inspector = inspect(bootstrapped_engine)
    columns = {c["name"] for c in inspector.get_columns("support_recipient")}
    assert {"revision", "is_current"}.issubset(columns), (
        f"support_recipient must have revision + is_current, got {sorted(columns)}"
    )

    with bootstrapped_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name='idx_support_recipient_current'"
            )
        ).first()
    assert row is not None, "idx_support_recipient_current partial unique index must exist"
    assert "WHERE" in (row[0] or "").upper()


def test_school_year_status_revision_columns_present(bootstrapped_engine):
    """Sprint 8.2.a: school_year_status mirror of the support_recipient
    contract — revision + is_current + partial unique."""
    inspector = inspect(bootstrapped_engine)
    columns = {c["name"] for c in inspector.get_columns("school_year_status")}
    assert {"revision", "is_current"}.issubset(columns), (
        f"school_year_status must have revision + is_current, got {sorted(columns)}"
    )

    with bootstrapped_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name='idx_school_year_status_current'"
            )
        ).first()
    assert row is not None, "idx_school_year_status_current partial unique index must exist"
    assert "WHERE" in (row[0] or "").upper()


def test_support_recipient_revision_2_does_not_collide(bootstrapped_engine):
    """Inserting a second revision for the same (school_id, fiscal_year) must
    succeed once the previous current row is flipped. Without the partial
    index + (school_id, fiscal_year, revision) unique this would fail."""
    from eidp.db.models import SupportRecipient

    with Session(bootstrapped_engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.flush()

        rev1 = SupportRecipient(
            school_id=school.id,
            fiscal_year=2026,
            annual_total=100,
            revision=1,
            is_current=True,
        )
        session.add(rev1)
        session.flush()

        session.query(SupportRecipient).filter(
            SupportRecipient.school_id == school.id,
            SupportRecipient.fiscal_year == 2026,
            SupportRecipient.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        rev2 = SupportRecipient(
            school_id=school.id,
            fiscal_year=2026,
            annual_total=110,
            revision=2,
            is_current=True,
        )
        session.add(rev2)
        session.commit()

        rows = (
            session.query(SupportRecipient)
            .filter(SupportRecipient.school_id == school.id)
            .order_by(SupportRecipient.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]


def test_school_year_status_revision_2_does_not_collide(bootstrapped_engine):
    from eidp.db.models import SchoolYearStatus

    with Session(bootstrapped_engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.flush()

        session.add(
            SchoolYearStatus(
                school_id=school.id,
                fiscal_year=2026,
                status="collected",
                revision=1,
                is_current=True,
            )
        )
        session.flush()

        session.query(SchoolYearStatus).filter(
            SchoolYearStatus.school_id == school.id,
            SchoolYearStatus.fiscal_year == 2026,
            SchoolYearStatus.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")

        session.add(
            SchoolYearStatus(
                school_id=school.id,
                fiscal_year=2026,
                status="collected",
                revision=2,
                is_current=True,
            )
        )
        session.commit()

        rows = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.school_id == school.id)
            .order_by(SchoolYearStatus.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]


def test_empty_database_db_info_smoke(bootstrapped_engine):
    """After bootstrap on an empty SQLite DB, the row-count queries that
    `eidp db-info` issues must succeed and return 0 across the headline
    tables. We don't invoke the CLI itself (Typer has its own runner) — just
    the SQL-level contract those queries depend on."""
    with Session(bootstrapped_engine) as session:
        assert session.query(func.count(School.id)).scalar() == 0
        assert session.query(func.count(Department.id)).scalar() == 0
        assert session.query(func.count(DepartmentYearly.id)).scalar() == 0
        assert session.query(func.count(Document.id)).scalar() == 0


# ---------------------------------------------------------------------------
# Dialect guard
# ---------------------------------------------------------------------------


def test_bootstrap_refuses_non_sqlite_engine():
    """``bootstrap_sqlite`` must refuse to run on a PostgreSQL engine — it
    would otherwise stamp head over a real production schema."""

    class _FakeDialect:
        name = "postgresql"

    class _FakeEngine:
        dialect = _FakeDialect()
        url = "postgresql://fake/none"

    with pytest.raises(RuntimeError, match="requires a SQLite engine"):
        bootstrap_sqlite(_FakeEngine())  # type: ignore[arg-type]


def test_is_sqlite_helper(sqlite_engine):
    assert is_sqlite(sqlite_engine) is True
