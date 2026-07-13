from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType


@pytest.fixture()
def engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'review-decision.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine):
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture()
def record() -> ExtractionReviewRecord:
    return ExtractionReviewRecord(
        review_id="metric-review-1",
        task_type=ReviewTaskType.EXTRACTED_METRIC,
        intake_record_id="intake-1",
        school_name="東京テスト専門学校",
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        source_pdf="source.pdf",
        department_name="テスト学科",
        field_category="文化教養",
        course_name="専門課程",
        metric="capacity",
        extracted_value=40,
        corrected_value=None,
        confidence=0.9,
        page_no=0,
        table_index=1,
        row_index=2,
        col_index=3,
        raw_label="収容定員",
        raw_value="40",
        canonical_metric="capacity",
        review_status=ReviewStatus.UNREVIEWED,
        review_note=None,
        reviewed_by=None,
        reviewed_at=None,
        next_action=None,
        created_at_utc="2026-07-13T00:00:00+00:00",
        updated_at_utc="2026-07-13T00:00:00+00:00",
    )


def _review_decision_module() -> ModuleType:
    try:
        return importlib.import_module("eidp.pipeline.review_decision")
    except ModuleNotFoundError:
        pytest.fail("eidp.pipeline.review_decision is not implemented", pytrace=False)


def _decision_model():
    model = getattr(importlib.import_module("eidp.db.models"), "ExtractionReviewDecision", None)
    if model is None:
        pytest.fail("ExtractionReviewDecision is not implemented", pytrace=False)
    return model


def test_review_decision_and_audit_commit_together(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()
    result = module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.ACCEPT,
        corrected_value=None,
        note="source checked",
        identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
    )
    session.commit()

    audit = session.scalar(select(ManualActionLog).where(ManualActionLog.action_id == result.audit_action_id))
    assert audit is not None
    UUID(result.decision_id)
    UUID(result.audit_action_id)
    assert result.revision == 1
    assert result.actor == "reviewer-1"
    assert result.identity_source == IdentitySource.TRUSTED_PROXY.value
    assert audit.actor == "reviewer-1"
    assert audit.identity_source == IdentitySource.TRUSTED_PROXY.value
    assert audit.action_type == "extraction_review_decision"
    assert audit.target_table == "extraction_review_decision"
    assert json.loads(audit.new_value or "null")["decision"] == "accept"


def test_service_flushes_without_committing(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()
    module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.ACCEPT,
        corrected_value=None,
        note=None,
        identity=ResolvedIdentity("reviewer-1", IdentitySource.CONFIGURED_FALLBACK),
    )
    session.rollback()

    assert session.scalar(select(_decision_model())) is None
    assert session.scalar(select(ManualActionLog)) is None


def test_audit_insert_failure_rolls_back_without_a_decision(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()

    def fail_audit_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected audit insert failure")

    event.listen(ManualActionLog, "before_insert", fail_audit_insert)
    try:
        with pytest.raises(RuntimeError, match="injected audit insert failure"):
            module.apply_review_decision(
                session,
                record=record,
                decision=module.ReviewDecision.ACCEPT,
                corrected_value=None,
                note="source checked",
                identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
            )
        session.rollback()
    finally:
        event.remove(ManualActionLog, "before_insert", fail_audit_insert)

    assert session.scalar(select(_decision_model())) is None
    assert session.scalar(select(ManualActionLog)) is None


@pytest.mark.parametrize(
    ("decision_name", "corrected_value", "expected_status"),
    [
        ("ACCEPT", None, ReviewStatus.ACCEPTED),
        ("CORRECT", 41, ReviewStatus.CORRECTED),
        ("NEEDS_REVIEW", None, ReviewStatus.NEEDS_REVIEW),
        ("EXCLUDE", None, ReviewStatus.EXCLUDED),
    ],
)
def test_all_four_decisions_overlay_the_expected_status(
    session: Session,
    record: ExtractionReviewRecord,
    decision_name: str,
    corrected_value: int | None,
    expected_status: ReviewStatus,
) -> None:
    module = _review_decision_module()
    note = "out of current export scope" if decision_name == "EXCLUDE" else "source checked"
    decision = module.apply_review_decision(
        session,
        record=record,
        decision=getattr(module.ReviewDecision, decision_name),
        corrected_value=corrected_value,
        note=note,
        identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
    )

    [overlaid] = module.overlay_review_decisions(session, [record])

    assert decision.revision == 1
    assert overlaid.review_status == expected_status
    assert overlaid.corrected_value == corrected_value
    assert overlaid.review_note == note
    assert overlaid.reviewed_by == "reviewer-1"
    assert overlaid.reviewed_at == decision.decided_at.isoformat()
    assert record.review_status == ReviewStatus.UNREVIEWED


def test_overlay_uses_highest_revision_and_preserves_input_order(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()
    identity = ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY)
    first = module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.ACCEPT,
        corrected_value=None,
        note="first pass",
        identity=identity,
    )
    second = module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.CORRECT,
        corrected_value=43,
        note="official table corrected",
        identity=identity,
    )
    untouched = ExtractionReviewRecord(**{**record.__dict__, "review_id": "metric-review-2"})

    overlaid = module.overlay_review_decisions(session, [untouched, record])

    assert first.revision == 1
    assert second.revision == 2
    assert [item.review_id for item in overlaid] == ["metric-review-2", "metric-review-1"]
    assert overlaid[0] == untouched
    assert overlaid[1].review_status == ReviewStatus.CORRECTED
    assert overlaid[1].corrected_value == 43
    assert overlaid[1].review_note == "official table corrected"


def test_overlay_ignores_legacy_or_tampered_base_decision_fields_without_database_decision(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()
    legacy = replace(
        record,
        corrected_value=999,
        review_status=ReviewStatus.CORRECTED,
        review_note="legacy JSON decision",
        reviewed_by="untrusted-json-actor",
        reviewed_at="2026-07-13T01:00:00+00:00",
        updated_at_utc="2026-07-13T01:00:00+00:00",
    )

    [overlaid] = module.overlay_review_decisions(session, [legacy])

    assert overlaid.review_id == record.review_id
    assert overlaid.extracted_value == record.extracted_value
    assert overlaid.raw_value == record.raw_value
    assert overlaid.review_status == ReviewStatus.UNREVIEWED
    assert overlaid.corrected_value is None
    assert overlaid.review_note is None
    assert overlaid.reviewed_by is None
    assert overlaid.reviewed_at is None
    assert overlaid.updated_at_utc == record.created_at_utc


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_exclude_rejects_invalid_reason_without_writing(
    session: Session,
    record: ExtractionReviewRecord,
    reason: str,
) -> None:
    module = _review_decision_module()

    with pytest.raises(ValueError, match="reason must be between 1 and 500 characters"):
        module.apply_review_decision(
            session,
            record=record,
            decision=module.ReviewDecision.EXCLUDE,
            corrected_value=None,
            note=reason,
            identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
        )

    session.commit()
    decision_model = getattr(importlib.import_module("eidp.db.models"), "ExtractionReviewDecision")
    assert session.scalar(select(decision_model)) is None
    assert session.scalar(select(ManualActionLog)) is None


def test_exclude_trims_and_audits_the_approved_reason(
    session: Session,
    record: ExtractionReviewRecord,
) -> None:
    module = _review_decision_module()
    result = module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.EXCLUDE,
        corrected_value=None,
        note="  outside the approved export scope  ",
        identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
    )
    session.commit()

    audit = session.scalar(select(ManualActionLog).where(ManualActionLog.action_id == result.audit_action_id))
    assert result.note == "outside the approved export scope"
    assert audit is not None
    assert audit.reason == "outside the approved export scope"
    assert json.loads(audit.new_value or "null")["reason"] == "outside the approved export scope"


def test_model_enforces_unique_keys_and_cross_dialect_exclude_check() -> None:
    table = _decision_model().__table__
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    checks = [
        str(constraint.sqltext).lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]

    assert ("decision_id",) in unique_columns
    assert ("audit_action_id",) in unique_columns
    assert ("review_id", "revision") in unique_columns
    assert any("exclude" in check and "trim" in check and "500" in check for check in checks)


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_database_check_rejects_invalid_exclude_reason(
    session: Session,
    reason: str,
) -> None:
    action_id = str(uuid4())
    session.add(
        ManualActionLog(
            action_id=action_id,
            actor="reviewer-1",
            identity_source=IdentitySource.TRUSTED_PROXY.value,
            action_type="extraction_review_decision",
            target_table="extraction_review_decision",
        )
    )
    session.flush()
    session.add(
        _decision_model()(
            decision_id=str(uuid4()),
            review_id="metric-review-1",
            revision=1,
            decision="exclude",
            corrected_value=None,
            note=reason,
            actor="reviewer-1",
            identity_source=IdentitySource.TRUSTED_PROXY.value,
            audit_action_id=action_id,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    assert session.scalar(select(_decision_model())) is None
    assert session.scalar(select(ManualActionLog)) is None


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_base_metadata_sqlite_rejects_raw_review_decision_mutation(
    engine,  # noqa: ANN001
    session: Session,
    record: ExtractionReviewRecord,
    operation: str,
) -> None:
    module = _review_decision_module()
    decision = module.apply_review_decision(
        session,
        record=record,
        decision=module.ReviewDecision.ACCEPT,
        corrected_value=None,
        note="source checked",
        identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
    )
    session.commit()
    statement = (
        "UPDATE extraction_review_decision SET note = note WHERE id = :decision_id"
        if operation == "update"
        else "DELETE FROM extraction_review_decision WHERE id = :decision_id"
    )

    with engine.connect() as connection:
        with pytest.raises(IntegrityError, match="immutable|append-only"):
            connection.execute(text(statement), {"decision_id": decision.id})
        connection.rollback()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_alembic_upgraded_sqlite_rejects_raw_review_decision_mutation(
    tmp_path: Path,
    operation: str,
) -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/9d0e1f2a3b4c_add_extraction_review_decisions.py"
    )
    spec = importlib.util.spec_from_file_location(
        "task4_review_decision_immutability_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    migrated_engine = create_engine(
        f"sqlite:///{tmp_path / 'migrated-review-decision.sqlite3'}",
        future=True,
    )
    try:
        ManualActionLog.__table__.create(migrated_engine)
        with migrated_engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            connection.execute(
                text(
                    """
                    INSERT INTO manual_action_log (
                        action_id, actor, identity_source, action_type, target_table
                    ) VALUES (
                        :action_id, 'reviewer-1', 'trusted_proxy',
                        'extraction_review_decision', 'extraction_review_decision'
                    )
                    """
                ),
                {"action_id": "00000000-0000-4000-8000-000000000001"},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO extraction_review_decision (
                        decision_id, review_id, revision, decision, actor,
                        identity_source, audit_action_id
                    ) VALUES (
                        '00000000-0000-4000-8000-000000000002',
                        'metric-review-1', 1, 'accept', 'reviewer-1',
                        'trusted_proxy', '00000000-0000-4000-8000-000000000001'
                    )
                    """
                )
            )

        statement = (
            "UPDATE extraction_review_decision SET note = note WHERE id = 1"
            if operation == "update"
            else "DELETE FROM extraction_review_decision WHERE id = 1"
        )
        with migrated_engine.connect() as connection:
            with pytest.raises(IntegrityError, match="immutable|append-only"):
                connection.execute(text(statement))
            connection.rollback()

        with migrated_engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.downgrade()
        assert "extraction_review_decision" not in inspect(migrated_engine).get_table_names()
    finally:
        migrated_engine.dispose()


def test_migration_contract() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/9d0e1f2a3b4c_add_extraction_review_decisions.py"
    )
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("task4_review_decision_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "9d0e1f2a3b4c"
    assert migration.down_revision == "8c9d0e1f2a3b"
