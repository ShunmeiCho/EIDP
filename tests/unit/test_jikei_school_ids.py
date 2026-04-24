from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, School, SchoolAlias

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "list_jikei_school_ids.py"
SPEC = importlib.util.spec_from_file_location("list_jikei_school_ids", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

_corp_group_school_ids = MODULE._corp_group_school_ids
_lookup_school_ids = MODULE._lookup_school_ids


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_lookup_school_ids_uses_alias_name_field() -> None:
    session = _session()
    try:
        school = School(
            id=1,
            prefecture="東京都",
            corporation_name="学校法人東京滋慶学園",
            school_name="東京コミュニケーションアート専門学校",
        )
        session.add(school)
        session.add(
            SchoolAlias(
                school_id=1,
                alias_name="TCA",
                alias_type="competition_report",
                source="test",
            )
        )
        session.flush()

        matches = _lookup_school_ids(session, ["TCA"])

        assert [s.id for s in matches["TCA"]] == [1]
    finally:
        session.close()


def test_corp_group_school_ids_matches_school_corporation_prefix() -> None:
    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人東京滋慶学園",
                school_name="東京デザインテクノロジーセンター専門学校",
            )
        )
        session.add(
            School(
                id=2,
                prefecture="東京都",
                corporation_name="学校法人その他",
                school_name="対象外学校",
            )
        )
        session.flush()

        assert [s.id for s in _corp_group_school_ids(session)] == [1]
    finally:
        session.close()
