"""Sprint 8.7.b — dev-only PostgreSQL -> SQLite data migration.

The real source database is Postgres, but the migration logic is table/row
copying through SQLAlchemy Core. These tests use two SQLite databases to pin
the contracts that matter before running against the 116-doc dev database:

* source/target row counts match for migrated tables;
* append-only revision chains keep revision + is_current exactly;
* rerunning the script is idempotent and does not duplicate rows.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Base,
    Department,
    DepartmentYearly,
    Document,
    School,
    SchoolSite,
    SchoolYearStatus,
    SupportRecipient,
)

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "migrate_pg_to_sqlite.py"
spec = importlib.util.spec_from_file_location("migrate_pg_to_sqlite", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

migrate_sessions = module.migrate_sessions


def _engine(tmp_path: Path, name: str) -> Engine:
    engine = create_engine(f"sqlite:///{tmp_path / name}", future=True)
    Base.metadata.create_all(engine)
    return engine


def _count(session: Session, model: type[Base]) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


def _seed_source(session: Session) -> None:
    school = School(
        id=1,
        school_code="S001",
        prefecture="東京都",
        corporation_name="移行法人",
        school_name="移行専門学校",
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    session.add(
        SchoolSite(
            id=1,
            school_id=1,
            url="https://example.ac.jp/disclosure",
            url_type="disclosure",
            discovery_method="prefecture_aggregator",
            verified=True,
            http_status=200,
        )
    )
    doc = Document(
        id=1,
        school_id=1,
        source_url="https://example.ac.jp/r8.pdf",
        file_path="data/pdfs/1/r8.pdf",
        file_hash="a" * 64,
        fiscal_year=2026,
        fiscal_year_override=2026,
        pdf_type="target",
        ingest_status="ingested",
        confidence=0.95,
    )
    session.add(doc)
    dept = Department(
        id=1,
        school_id=1,
        course_name="専門課程",
        canonical_name="情報学科",
        course_type="昼",
        duration_years=2,
        status="active",
    )
    session.add(dept)
    session.flush()

    session.add_all(
        [
            DepartmentYearly(
                id=1,
                department_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=False,
                capacity=40,
                enrollment=38,
                graduates=12,
                extraction_confidence=0.90,
                extraction_method="pdf_parse",
            ),
            DepartmentYearly(
                id=2,
                department_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=2,
                is_current=True,
                capacity=40,
                enrollment=41,
                graduates=13,
                extraction_confidence=0.94,
                extraction_method="pdf_parse",
                confidence_breakdown='{"method":"pdf_parse"}',
            ),
            SupportRecipient(
                id=1,
                school_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=False,
                annual_total=100,
                grand_total=100,
            ),
            SupportRecipient(
                id=2,
                school_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=2,
                is_current=True,
                annual_total=111,
                grand_total=111,
                confidence_breakdown='{"method":"pdf_parse"}',
            ),
            SchoolYearStatus(
                id=1,
                school_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=False,
                status="partial",
            ),
            SchoolYearStatus(
                id=2,
                school_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=2,
                is_current=True,
                status="collected",
            ),
        ]
    )
    session.commit()


def test_migration_count_match(tmp_path: Path) -> None:
    source_engine = _engine(tmp_path, "source.sqlite3")
    target_engine = _engine(tmp_path, "target.sqlite3")
    with Session(source_engine) as source:
        _seed_source(source)

    with Session(source_engine) as source, Session(target_engine) as target:
        report = migrate_sessions(source, target)

    assert report.total_inserted == 10
    assert report.by_table["document"].source_rows == 1
    assert report.by_table["department_yearly"].source_rows == 2
    assert report.by_table["support_recipient"].source_rows == 2
    assert report.by_table["school_year_status"].source_rows == 2

    with Session(target_engine) as target:
        assert _count(target, School) == 1
        assert _count(target, SchoolSite) == 1
        assert _count(target, Document) == 1
        assert _count(target, Department) == 1
        assert _count(target, DepartmentYearly) == 2
        assert _count(target, SupportRecipient) == 2
        assert _count(target, SchoolYearStatus) == 2


def test_migration_preserves_revision_chain(tmp_path: Path) -> None:
    source_engine = _engine(tmp_path, "source.sqlite3")
    target_engine = _engine(tmp_path, "target.sqlite3")
    with Session(source_engine) as source:
        _seed_source(source)

    with Session(source_engine) as source, Session(target_engine) as target:
        migrate_sessions(source, target)

    with Session(target_engine) as target:
        yearly = target.query(DepartmentYearly).order_by(DepartmentYearly.revision).all()
        sr = target.query(SupportRecipient).order_by(SupportRecipient.revision).all()
        sys_rows = target.query(SchoolYearStatus).order_by(SchoolYearStatus.revision).all()

        assert [row.revision for row in yearly] == [1, 2]
        assert [row.is_current for row in yearly] == [False, True]
        assert [row.enrollment for row in yearly] == [38, 41]

        assert [row.revision for row in sr] == [1, 2]
        assert [row.is_current for row in sr] == [False, True]
        assert [row.grand_total for row in sr] == [100, 111]

        assert [row.revision for row in sys_rows] == [1, 2]
        assert [row.is_current for row in sys_rows] == [False, True]
        assert [row.status for row in sys_rows] == ["partial", "collected"]


def test_migration_idempotent_on_rerun(tmp_path: Path) -> None:
    source_engine = _engine(tmp_path, "source.sqlite3")
    target_engine = _engine(tmp_path, "target.sqlite3")
    with Session(source_engine) as source:
        _seed_source(source)

    with Session(source_engine) as source, Session(target_engine) as target:
        first = migrate_sessions(source, target)
    with Session(source_engine) as source, Session(target_engine) as target:
        second = migrate_sessions(source, target)

    assert first.total_inserted == 10
    assert second.total_inserted == 0
    assert second.total_skipped == 10

    with Session(target_engine) as target:
        assert _count(target, Document) == 1
        assert _count(target, DepartmentYearly) == 2
        assert _count(target, SupportRecipient) == 2
        assert _count(target, SchoolYearStatus) == 2
