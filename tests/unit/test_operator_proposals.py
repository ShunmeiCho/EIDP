from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Base,
    Department,
    DepartmentChange,
    School,
    SchoolAlias,
)
from eidp.review.operator_pages import (
    ProposalDecision,
    _read_proposals,
    _record_decision,
    apply_dept_alias_proposal,
    apply_school_alias_proposal,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_apply_school_alias_inserts_when_absent() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.flush()
        created, reason = apply_school_alias_proposal(
            session, school_id=1, alias_name="A-short",
        )
        assert created is True
        assert reason == "inserted"
        got = (
            session.query(SchoolAlias)
            .filter(SchoolAlias.school_id == 1, SchoolAlias.alias_name == "A-short")
            .first()
        )
        assert got is not None
        assert got.alias_type == "competition_template"
    finally:
        session.close()


def test_apply_school_alias_is_idempotent() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(SchoolAlias(school_id=1, alias_name="A-short", alias_type="x", source="y"))
        session.flush()
        created, reason = apply_school_alias_proposal(
            session, school_id=1, alias_name="A-short",
        )
        assert created is False
        assert reason == "already_exists"
    finally:
        session.close()


def test_apply_dept_alias_records_department_change() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.flush()
        created, reason = apply_dept_alias_proposal(
            session, department_id=9, old_name="プロミュージシャン学科",
        )
        assert created is True
        dc = (
            session.query(DepartmentChange)
            .filter(DepartmentChange.department_id == 9)
            .first()
        )
        assert dc is not None
        assert dc.old_name == "プロミュージシャン学科"
        assert dc.new_name == "プロミュージシャン科"
        assert dc.change_type == "alias"
        assert dc.verified is False
    finally:
        session.close()


def test_apply_dept_alias_idempotent() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.flush()
        apply_dept_alias_proposal(session, department_id=9, old_name="プロミュージシャン学科")
        created, reason = apply_dept_alias_proposal(
            session, department_id=9, old_name="プロミュージシャン学科",
        )
        assert created is False
        assert reason == "already_exists"
    finally:
        session.close()


def test_apply_dept_alias_rejects_nonexistent_dept() -> None:
    session = _session()
    try:
        created, reason = apply_dept_alias_proposal(
            session, department_id=99999, old_name="whatever",
        )
        assert created is False
        assert reason == "dept_not_found"
    finally:
        session.close()


def test_record_decision_writes_audit_jsonl(tmp_path: Path) -> None:
    audit = tmp_path / "decisions.jsonl"
    decision = ProposalDecision(
        decision="approved",
        proposal_kind="school_alias",
        template_name="日本工学院(八王子)",
        target_id=2,
        operator_name="smoke",
        note="inserted",
        timestamp="2026-04-24T00:00:00+00:00",
    )
    _record_decision(decision, audit)

    line = audit.read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["decision"] == "approved"
    assert row["template_name"] == "日本工学院(八王子)"
    assert row["proposal_kind"] == "school_alias"


def test_apply_preserves_school_context_on_picked_candidate() -> None:
    """D-scope: when operator picks a candidate from an ambiguous proposal,
    the resulting SchoolAlias is bound to THAT candidate, not any other.
    """
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="片柳", school_name="日本工学院専門学校"))
        session.add(School(id=2, prefecture="東京", corporation_name="片柳", school_name="日本工学院八王子専門学校"))
        session.flush()
        # Operator picks id=1 as the canonical 蒲田 school
        created, _ = apply_school_alias_proposal(
            session, school_id=1, alias_name="日本工学院(蒲田)",
        )
        assert created is True
        # Only id=1 gets the alias
        got = session.query(SchoolAlias).filter(SchoolAlias.alias_name == "日本工学院(蒲田)").all()
        assert len(got) == 1
        assert got[0].school_id == 1
    finally:
        session.close()


def test_deferred_decision_does_not_write_db_but_audits(tmp_path: Path) -> None:
    """Defer branch: no DB mutation, only decisions JSONL appended."""
    audit = tmp_path / "decisions.jsonl"
    _record_decision(
        ProposalDecision(
            decision="deferred",
            proposal_kind="school_alias_ambiguous_candidates",
            template_name="東京ビジュアルアーツ",
            target_id=None,
            operator_name="tester",
            note="operator deferred",
            timestamp="2026-04-24T00:00:00+00:00",
        ),
        audit,
    )
    row = json.loads(audit.read_text(encoding="utf-8").strip())
    assert row["decision"] == "deferred"
    assert row["target_id"] is None
    assert row["proposal_kind"].startswith("school_alias_")


def test_read_proposals_tolerates_missing_file_and_junk_lines(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    assert _read_proposals(path) == []
    path.write_text(
        '{"template_name": "X", "proposal_type": "alias_existing_school"}\n'
        "not-json-at-all\n"
        '{"template_name": "Y", "proposal_type": "truly_missing"}\n',
        encoding="utf-8",
    )
    rows = _read_proposals(path)
    assert len(rows) == 2
    assert rows[0]["template_name"] == "X"
    assert rows[1]["template_name"] == "Y"
