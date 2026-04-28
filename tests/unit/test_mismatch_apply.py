from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, Document, School, SchoolAlias

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mismatch_apply.py"
SPEC = importlib.util.spec_from_file_location("mismatch_apply", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["mismatch_apply"] = MODULE
SPEC.loader.exec_module(MODULE)

classify = MODULE.classify
apply_alias_rows = MODULE.apply_alias_rows


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_wrong_school_collision_beats_similarity_alias() -> None:
    bucket, note = classify(
        "気仙沼リアス調理製菓専門学校",
        "気仙沼リアス調理専門学校",
        twin_already_ingested=False,
        name_collision_other_school="sid=2426 name=気仙沼リアス調理製菓専門学校",
    )

    assert bucket == "wrong_school"
    assert "sid=2426" in note


def test_apply_alias_resets_matching_doc_to_pending() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="愛知", corporation_name="C", school_name="名古屋医専"))
        session.add(
            Document(
                id=492,
                school_id=1,
                source_url="https://example.ac.jp/support.pdf",
                file_path="data/pdfs/1/support.pdf",
                pdf_type="target",
                ingest_status="school_mismatch",
            )
        )
        session.flush()

        stats = apply_alias_rows(
            session,
            [
                {
                    "doc_id": 492,
                    "school_id": 1,
                    "parsed_school_name": "古屋医専",
                    "bucket": "safe_alias",
                }
            ],
            {"safe_alias"},
        )

        alias = session.query(SchoolAlias).filter(SchoolAlias.school_id == 1).one()
        doc = session.get(Document, 492)
        assert stats == {
            "added": 1,
            "skipped_existing": 0,
            "conflicts": 0,
            "reset_pending": 1,
            "missing_doc": 0,
        }
        assert alias.alias_name == "古屋医専"
        assert alias.alias_type == "pdf_school_name"
        assert alias.source == "mismatch_apply"
        assert doc is not None
        assert doc.ingest_status == "pending"
    finally:
        session.close()


def test_apply_alias_conflict_does_not_reset_doc() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="愛知", corporation_name="C", school_name="名古屋医専"))
        session.add(School(id=2, prefecture="愛知", corporation_name="D", school_name="別校"))
        session.add(SchoolAlias(school_id=2, alias_name="古屋医専", alias_type="x", source="test"))
        session.add(
            Document(
                id=492,
                school_id=1,
                source_url="https://example.ac.jp/support.pdf",
                file_path="data/pdfs/1/support.pdf",
                pdf_type="target",
                ingest_status="school_mismatch",
            )
        )
        session.flush()

        stats = apply_alias_rows(
            session,
            [
                {
                    "doc_id": 492,
                    "school_id": 1,
                    "parsed_school_name": "古屋医専",
                    "bucket": "safe_alias",
                }
            ],
            {"safe_alias"},
        )

        doc = session.get(Document, 492)
        assert stats["conflicts"] == 1
        assert stats["reset_pending"] == 0
        assert doc is not None
        assert doc.ingest_status == "school_mismatch"
    finally:
        session.close()
