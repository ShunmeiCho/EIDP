from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.locking import acquire_lock
from eidp.db.models import (
    Base,
    Department,
    DepartmentChange,
    ManualActionLog,
    School,
    SchoolAlias,
)
from eidp.review.operator_pages import (
    ProposalDecision,
    _active_dept_alias_changes,
    _load_decision_index,
    _read_proposals,
    _record_decision,
    apply_dept_alias_proposal,
    apply_school_alias_proposal,
    void_department_change,
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
        audit = session.query(ManualActionLog).one()
        assert audit.action_type == "dept_alias_approved"
        assert audit.target_table == "department_change"
        assert audit.target_id == dc.id
    finally:
        session.close()


def test_apply_dept_alias_uses_operator_actor_in_audit() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.flush()

        created, reason = apply_dept_alias_proposal(
            session,
            department_id=9,
            old_name="プロミュージシャン学科",
            actor="reviewer-a",
        )

        assert created is True
        assert reason == "inserted"
        audit = session.query(ManualActionLog).one()
        assert audit.actor == "reviewer-a"
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


def test_apply_dept_alias_allows_recreating_voided_alias() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.add(
            DepartmentChange(
                department_id=9,
                change_type="alias",
                fiscal_year=2026,
                old_name="プロミュージシャン学科",
                new_name="プロミュージシャン科",
                verified=False,
                voided=True,
                voided_by="operator",
                void_reason="wrong approval",
            )
        )
        session.flush()

        created, reason = apply_dept_alias_proposal(
            session, department_id=9, old_name="プロミュージシャン学科",
        )
        assert created is True
        assert reason == "inserted"
        rows = (
            session.query(DepartmentChange)
            .filter(
                DepartmentChange.department_id == 9,
                DepartmentChange.old_name == "プロミュージシャン学科",
                DepartmentChange.change_type == "alias",
            )
            .order_by(DepartmentChange.id.asc())
            .all()
        )
        assert len(rows) == 2
        assert rows[0].voided is True
        assert rows[1].voided is False
    finally:
        session.close()


def test_void_department_change_marks_row_and_writes_audit() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        change = DepartmentChange(
            department_id=9,
            change_type="alias",
            fiscal_year=2026,
            old_name="プロミュージシャン学科",
            new_name="プロミュージシャン科",
            verified=False,
        )
        session.add(change)
        session.flush()

        changed, reason = void_department_change(
            session,
            change_id=change.id,
            actor="tester",
            reason="wrong department",
        )
        assert changed is True
        assert reason == "voided"

        session.refresh(change)
        assert change.voided is True
        assert change.voided_by == "tester"
        assert change.void_reason == "wrong department"
        assert change.voided_at is not None

        audit = session.query(ManualActionLog).one()
        assert audit.action_type == "dept_change_void"
        assert audit.target_table == "department_change"
        assert audit.target_id == change.id
    finally:
        session.close()


def test_active_dept_alias_changes_excludes_voided_rows() -> None:
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.add_all([
            DepartmentChange(
                id=1,
                department_id=9,
                change_type="alias",
                fiscal_year=2026,
                old_name="プロミュージシャン学科",
                new_name="プロミュージシャン科",
                verified=False,
            ),
            DepartmentChange(
                id=2,
                department_id=9,
                change_type="alias",
                fiscal_year=2026,
                old_name="誤った別名",
                new_name="プロミュージシャン科",
                verified=False,
                voided=True,
                voided_by="operator",
                void_reason="wrong approval",
            ),
        ])
        session.flush()

        rows = _active_dept_alias_changes(session)

        assert len(rows) == 1
        assert rows[0]["change_id"] == 1
        assert rows[0]["school_name"] == "学校A"
        assert rows[0]["canonical_name"] == "プロミュージシャン科"
        assert rows[0]["old_name"] == "プロミュージシャン学科"
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


def test_apply_dept_alias_returns_lock_busy_without_writing(tmp_path: Path) -> None:
    session = _session()
    lock_path = tmp_path / "data" / ".lock"
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        session.commit()

        with acquire_lock(lock_path, owner="weekly_runner"):
            created, reason = apply_dept_alias_proposal(
                session,
                department_id=9,
                old_name="プロミュージシャン学科",
                lock_path=lock_path,
            )

        assert created is False
        assert reason == "lock_busy"
        assert session.query(DepartmentChange).count() == 0
    finally:
        session.close()


def test_void_department_change_returns_lock_busy_without_writing(tmp_path: Path) -> None:
    session = _session()
    lock_path = tmp_path / "data" / ".lock"
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="学校A"))
        session.add(Department(id=9, school_id=1, canonical_name="プロミュージシャン科"))
        change = DepartmentChange(
            department_id=9,
            change_type="alias",
            fiscal_year=2026,
            old_name="プロミュージシャン学科",
            new_name="プロミュージシャン科",
            verified=False,
        )
        session.add(change)
        session.commit()

        with acquire_lock(lock_path, owner="weekly_runner"):
            changed, reason = void_department_change(
                session,
                change_id=change.id,
                actor="tester",
                reason="wrong department",
                lock_path=lock_path,
            )

        assert changed is False
        assert reason == "lock_busy"
        session.refresh(change)
        assert change.voided is False
        assert session.query(ManualActionLog).count() == 0
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


def test_lock_busy_decision_does_not_hide_dept_proposal(tmp_path: Path) -> None:
    audit = tmp_path / "decisions.jsonl"
    _record_decision(
        ProposalDecision(
            decision="lock_busy",
            proposal_kind="dept_alias",
            template_name="プロミュージシャン学科",
            target_id=9,
            operator_name="tester",
            note="lock busy",
            timestamp="2026-04-24T00:00:00+00:00",
        ),
        audit,
    )

    assert ("dept_alias", "プロミュージシャン学科") not in _load_decision_index(audit)


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


def test_apply_school_alias_refuses_cross_school_conflict() -> None:
    """MEDIUM fix: alias already pointing to a different school must not be
    silently created — matcher's ambiguity guard would otherwise flip the
    row to school_name_ambiguous. Refuse up-front with a specific reason."""
    session = _session()
    try:
        session.add(School(id=1, prefecture="東京", corporation_name="A", school_name="学校A"))
        session.add(School(id=2, prefecture="東京", corporation_name="B", school_name="学校B"))
        session.add(SchoolAlias(school_id=1, alias_name="sharedKey", alias_type="x", source="y"))
        session.flush()
        created, reason = apply_school_alias_proposal(
            session, school_id=2, alias_name="sharedKey",
        )
        assert created is False
        assert reason.startswith("conflict_other_school:")
        assert "1" in reason  # id=1 is the existing owner
        # DB state unchanged — no alias pointing to school 2
        rows = session.query(SchoolAlias).filter(SchoolAlias.school_id == 2).all()
        assert rows == []
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


def test_decision_index_dedupes_by_kind_prefix_and_template(tmp_path: Path) -> None:
    """LOW fix: decisions JSONL should roll picker-kind variants
    ('school_alias_ambiguous_candidates') up to the same key prefix
    ('school_alias') used in the UI dedupe check."""
    audit = tmp_path / "decisions.jsonl"
    for kind in (
        "school_alias",
        "school_alias_ambiguous_candidates",
        "school_alias_branch_of_existing",
    ):
        _record_decision(
            ProposalDecision(
                decision="approved",
                proposal_kind=kind,
                template_name="X",
                target_id=1,
                operator_name="t",
                note="",
                timestamp="2026-04-24T00:00:00+00:00",
            ),
            audit,
        )
    _record_decision(
        ProposalDecision(
            decision="deferred",
            proposal_kind="dept_alias",
            template_name="Y",
            target_id=None,
            operator_name="t",
            note="",
            timestamp="2026-04-24T00:00:00+00:00",
        ),
        audit,
    )
    idx = _load_decision_index(audit)
    # school_alias variants collapse to one entry
    assert ("school_alias", "X") in idx
    assert ("dept_alias", "Y") in idx
    # Last write wins for same key
    assert idx[("school_alias", "X")] == "approved"
    assert idx[("dept_alias", "Y")] == "deferred"


def test_decision_index_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert _load_decision_index(tmp_path / "absent.jsonl") == {}


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
