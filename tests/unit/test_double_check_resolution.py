from __future__ import annotations

import importlib
import importlib.util
import json
import os
import stat
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.pipeline.external_extraction_import import ExternalSourceSystem
from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType
from eidp.pipeline.review_decision import ReviewDecision, apply_review_decision

EXTERNAL_CSV = """school_name,school_id,field_category,course_name,department_name,fiscal_year,metric,value
東京テスト専門学校,S-001,文化教養,専門課程,テスト学科,2026,capacity,40
""".encode()
TEST_IDENTITY = ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY)
TASK5_IMMUTABILITY_TRIGGERS = {
    f"trg_{table}_immutable_{operation}"
    for table in (
        "external_comparison_run",
        "external_comparison_result",
        "double_check_resolution",
    )
    for operation in ("update", "delete")
}


def _resolution_module() -> ModuleType:
    try:
        return importlib.import_module("eidp.pipeline.double_check_resolution")
    except ModuleNotFoundError:
        pytest.fail("eidp.pipeline.double_check_resolution is not implemented", pytrace=False)


def _task5_models() -> tuple[type[object], type[object], type[object]]:
    models = importlib.import_module("eidp.db.models")
    resolved: list[type[object]] = []
    for model_name in (
        "ExternalComparisonRun",
        "ExternalComparisonResult",
        "DoubleCheckResolution",
    ):
        model = getattr(models, model_name, None)
        if model is None:
            pytest.fail(f"{model_name} is not implemented", pytrace=False)
        resolved.append(model)
    return resolved[0], resolved[1], resolved[2]


def _record() -> ExtractionReviewRecord:
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
        extracted_value=37,
        corrected_value=999,
        confidence=0.9,
        page_no=0,
        table_index=1,
        row_index=2,
        col_index=3,
        raw_label="収容定員",
        raw_value="37",
        canonical_metric="capacity",
        review_status=ReviewStatus.CORRECTED,
        review_note="untrusted base JSON decision",
        reviewed_by="untrusted-json-actor",
        reviewed_at="2026-07-13T00:00:00+00:00",
        next_action=None,
        created_at_utc="2026-07-13T00:00:00+00:00",
        updated_at_utc="2026-07-13T00:00:00+00:00",
    )


@pytest.fixture()
def engine(tmp_path: Path):
    _resolution_module()
    _task5_models()
    database_engine = create_engine(f"sqlite:///{tmp_path / 'double-check.sqlite3'}", future=True)

    @event.listens_for(database_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # noqa: ANN001, ANN202
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(database_engine)
    yield database_engine
    database_engine.dispose()


@pytest.fixture()
def session(engine):  # noqa: ANN001
    with Session(engine) as db_session:
        yield db_session


def _create_mismatch(
    session: Session,
    *,
    intake_root: Path,
    record: ExtractionReviewRecord | None = None,
):  # noqa: ANN202
    module = _resolution_module()
    base_record = record or _record()
    decision = apply_review_decision(
        session,
        record=base_record,
        decision=ReviewDecision.CORRECT,
        corrected_value=41,
        note="official table checked",
        identity=TEST_IDENTITY,
    )
    run = module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[base_record],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()
    _run_model, result_model, _resolution_model = _task5_models()
    result = session.scalar(select(result_model).where(result_model.run_id == run.run_id))
    assert result is not None
    return run, result, decision


def test_external_comparison_run_requires_persistent_models_and_service(tmp_path: Path) -> None:
    module = _resolution_module()
    models = importlib.import_module("eidp.db.models")
    for model_name in (
        "ExternalComparisonRun",
        "ExternalComparisonResult",
        "DoubleCheckResolution",
    ):
        assert getattr(models, model_name, None) is not None, f"{model_name} is not implemented"

    engine = create_engine(f"sqlite:///{tmp_path / 'double-check.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            run = module.create_external_comparison_run(
                session,
                intake_root=tmp_path / "intake",
                review_records=[_record()],
                external_file_bytes=EXTERNAL_CSV,
                original_filename="../../copilot.csv",
                source_system=ExternalSourceSystem.COPILOT,
                identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
            )
            session.commit()

            assert run.external_file_sha256
            assert len(run.external_file_sha256) == 64
            assert run.original_filename == "../../copilot.csv"
            assert run.actor == "reviewer-1"
            assert run.identity_source == IdentitySource.TRUSTED_PROXY.value
            assert not (tmp_path / "copilot.csv").exists()
    finally:
        engine.dispose()


def test_run_snapshots_db_overlay_and_immutable_artifacts(
    session: Session,
    tmp_path: Path,
) -> None:
    run, result, decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    source_path = tmp_path / "intake" / run.external_file_path
    report_path = tmp_path / "intake" / run.report_path

    assert UUID(run.run_id)
    assert run.external_file_sha256 == sha256(EXTERNAL_CSV).hexdigest()
    assert source_path.read_bytes() == EXTERNAL_CSV
    assert sha256(report_path.read_bytes()).hexdigest() == run.report_sha256
    assert source_path == tmp_path / "intake" / "external" / run.external_file_sha256 / "source.bin"
    assert report_path.parent == source_path.parent / "reports"
    assert result.comparison_key
    assert len(result.row_key) == 64
    assert result.review_id == "metric-review-1"
    assert result.review_decision_revision == 1
    assert result.review_audit_action_id == decision.audit_action_id
    assert result.external_source_row_key == f"{run.external_file_sha256}:2:capacity"
    assert result.external_file_sha256 == run.external_file_sha256
    assert result.eidp_value == 41
    assert result.external_value == 40
    assert result.comparison_status == "value_mismatch"
    assert result.mismatch_reason == "EIDP value differs from external value"
    assert b",41,40," in report_path.read_bytes()


def test_path_traversal_filename_is_metadata_only(session: Session, tmp_path: Path) -> None:
    module = _resolution_module()
    run = module.create_external_comparison_run(
        session,
        intake_root=tmp_path / "intake",
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="../../outside.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()

    assert run.original_filename == "../../outside.csv"
    assert not (tmp_path / "outside.csv").exists()
    assert (tmp_path / "intake" / run.external_file_path).is_file()


def test_preexisting_corrupt_content_addressed_source_is_refused(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    file_hash = sha256(EXTERNAL_CSV).hexdigest()
    source_path = tmp_path / "intake" / "external" / file_hash / "source.bin"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"different bytes")

    with pytest.raises(module.DoubleCheckPersistenceError, match="immutable artifact"):
        module.create_external_comparison_run(
            session,
            intake_root=tmp_path / "intake",
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )

    session.rollback()
    run_model, result_model, _resolution_model = _task5_models()
    assert session.scalar(select(func.count()).select_from(run_model)) == 0
    assert session.scalar(select(func.count()).select_from(result_model)) == 0


def _artifact_files(intake_root: Path) -> list[Path]:
    external_root = intake_root / "external"
    return sorted(path for path in external_root.rglob("*") if path.is_file()) if external_root.exists() else []


def test_explicit_rollback_removes_newly_published_artifacts(session: Session, tmp_path: Path) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    assert len(_artifact_files(intake_root)) == 2

    session.rollback()

    assert _artifact_files(intake_root) == []


def test_session_close_rolls_back_run_and_removes_newly_published_artifacts(
    engine,  # noqa: ANN001
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    run_model, result_model, _resolution_model = _task5_models()
    intake_root = tmp_path / "intake"

    with Session(engine) as uncommitted_session:
        run = module.create_external_comparison_run(
            uncommitted_session,
            intake_root=intake_root,
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )
        run_id = run.run_id
        assert len(_artifact_files(intake_root)) == 2
        assert module._PENDING_ARTIFACTS_KEY in uncommitted_session.info

    assert _artifact_files(intake_root) == []
    assert module._PENDING_ARTIFACTS_KEY not in uncommitted_session.info
    with Session(engine) as verification_session:
        assert verification_session.scalar(select(func.count()).select_from(run_model)) == 0
        assert verification_session.scalar(select(func.count()).select_from(result_model)) == 0
        assert verification_session.get(run_model, run_id) is None


def test_session_close_surfaces_cleanup_failure_after_attempting_every_artifact(
    engine,  # noqa: ANN001
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    attempted: list[Path] = []

    def _fail_unlink(artifact):  # noqa: ANN001, ANN202
        attempted.append(artifact.relative_path)
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(module, "_unlink_published_artifact", _fail_unlink)
    with pytest.raises(
        module.DoubleCheckPersistenceError,
        match=r"^immutable artifact cleanup failed$",
    ):
        with Session(engine) as uncommitted_session:
            module.create_external_comparison_run(
                uncommitted_session,
                intake_root=intake_root,
                review_records=[_record()],
                external_file_bytes=EXTERNAL_CSV,
                original_filename="copilot.csv",
                source_system=ExternalSourceSystem.COPILOT,
                identity=TEST_IDENTITY,
            )

    assert len(attempted) == 2
    assert module._PENDING_ARTIFACTS_KEY not in uncommitted_session.info


def test_session_close_never_removes_preexisting_deduplicated_artifacts(
    engine,  # noqa: ANN001
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    run_model, result_model, _resolution_model = _task5_models()
    intake_root = tmp_path / "intake"

    with Session(engine) as committed_session:
        first = module.create_external_comparison_run(
            committed_session,
            intake_root=intake_root,
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )
        committed_session.commit()
        first_external_file_path = first.external_file_path
        first_report_path = first.report_path

    existing_paths = _artifact_files(intake_root)
    existing_bytes = {path: path.read_bytes() for path in existing_paths}
    with Session(engine) as uncommitted_session:
        second = module.create_external_comparison_run(
            uncommitted_session,
            intake_root=intake_root,
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )
        assert second.external_file_path == first_external_file_path
        assert second.report_path == first_report_path

    assert _artifact_files(intake_root) == existing_paths
    assert {path: path.read_bytes() for path in existing_paths} == existing_bytes
    with Session(engine) as verification_session:
        assert verification_session.scalar(select(func.count()).select_from(run_model)) == 1
        assert verification_session.scalar(select(func.count()).select_from(result_model)) == 1


def test_nested_commit_keeps_artifacts_registered_for_outer_rollback(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )

    with session.begin_nested():
        pass
    session.rollback()

    assert _artifact_files(intake_root) == []


def test_nested_rollback_does_not_remove_outer_transaction_artifacts(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    expected_artifacts = _artifact_files(intake_root)

    nested = session.begin_nested()
    nested.rollback()

    assert _artifact_files(intake_root) == expected_artifacts
    session.rollback()
    assert _artifact_files(intake_root) == []


def test_failure_after_source_publication_removes_only_new_source(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    original_publish = module._write_immutable_artifact
    publish_count = 0

    def _fail_report(root: Path, relative_path: Path, payload: bytes):  # noqa: ANN202
        nonlocal publish_count
        publish_count += 1
        if publish_count == 2:
            raise module.DoubleCheckPersistenceError("injected report publication failure")
        return original_publish(root, relative_path, payload)

    monkeypatch.setattr(module, "_write_immutable_artifact", _fail_report)
    with pytest.raises(module.DoubleCheckPersistenceError, match="injected report"):
        module.create_external_comparison_run(
            session,
            intake_root=intake_root,
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )
    session.rollback()

    assert _artifact_files(intake_root) == []


def test_failure_after_report_publication_removes_new_artifacts(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    run_model, _result_model, _resolution_model = _task5_models()
    intake_root = tmp_path / "intake"
    original_add = session.add

    def _reject_run(instance: object) -> None:
        if isinstance(instance, run_model):
            raise RuntimeError("injected post-report failure")
        original_add(instance)

    monkeypatch.setattr(session, "add", _reject_run)
    with pytest.raises(RuntimeError, match="post-report"):
        module.create_external_comparison_run(
            session,
            intake_root=intake_root,
            review_records=[_record()],
            external_file_bytes=EXTERNAL_CSV,
            original_filename="copilot.csv",
            source_system=ExternalSourceSystem.COPILOT,
            identity=TEST_IDENTITY,
        )
    session.rollback()

    assert _artifact_files(intake_root) == []


def test_db_flush_failure_removes_new_artifacts(session: Session, tmp_path: Path) -> None:
    module = _resolution_module()
    run_model, _result_model, _resolution_model = _task5_models()
    intake_root = tmp_path / "intake"

    def _fail_flush(_mapper, _connection, _target):  # noqa: ANN001, ANN202
        raise RuntimeError("injected run flush failure")

    event.listen(run_model, "before_insert", _fail_flush)
    try:
        with pytest.raises(RuntimeError, match="run flush"):
            module.create_external_comparison_run(
                session,
                intake_root=intake_root,
                review_records=[_record()],
                external_file_bytes=EXTERNAL_CSV,
                original_filename="copilot.csv",
                source_system=ExternalSourceSystem.COPILOT,
                identity=TEST_IDENTITY,
            )
        session.rollback()
    finally:
        event.remove(run_model, "before_insert", _fail_flush)

    assert _artifact_files(intake_root) == []


def test_failed_commit_then_rollback_removes_new_artifacts(session: Session, tmp_path: Path) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )

    def _fail_commit(_session: Session) -> None:
        raise RuntimeError("injected commit failure")

    event.listen(session, "before_commit", _fail_commit)
    try:
        with pytest.raises(RuntimeError, match="commit failure"):
            session.commit()
    finally:
        event.remove(session, "before_commit", _fail_commit)
    session.rollback()

    assert _artifact_files(intake_root) == []


def test_rollback_never_removes_preexisting_deduplicated_artifacts(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    first = module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()
    existing_paths = _artifact_files(intake_root)
    existing_bytes = {path: path.read_bytes() for path in existing_paths}

    second = module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    assert second.external_file_path == first.external_file_path
    assert second.report_path == first.report_path
    session.rollback()

    assert _artifact_files(intake_root) == existing_paths
    assert {path: path.read_bytes() for path in existing_paths} == existing_bytes


def test_rollback_surfaces_cleanup_failure_after_attempting_every_artifact(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root = tmp_path / "intake"
    module.create_external_comparison_run(
        session,
        intake_root=intake_root,
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    expected_attempts = len(_artifact_files(intake_root))
    original_unlink = module._unlink_published_artifact
    attempted: list[Path] = []

    def _record_unlink(artifact):  # noqa: ANN001, ANN202
        attempted.append(artifact.relative_path)
        original_unlink(artifact)

    monkeypatch.setattr(module, "_unlink_published_artifact", _record_unlink)
    external_root = intake_root / "external"
    external_root.rename(intake_root / "sensitive-replaced-external")
    sensitive_bytes = b"sensitive replacement bytes"
    external_root.write_bytes(sensitive_bytes)

    with pytest.raises(
        module.DoubleCheckPersistenceError,
        match=r"^immutable artifact cleanup failed$",
    ) as exc_info:
        session.rollback()

    assert len(attempted) == expected_attempts
    assert "sensitive-replaced-external" not in str(exc_info.value)
    assert sensitive_bytes.decode() not in str(exc_info.value)
    assert external_root.read_bytes() == sensitive_bytes


def _artifact_target(tmp_path: Path) -> tuple[Path, Path, bytes]:
    intake_root = tmp_path / "intake"
    relative_path = Path("external") / ("a" * 64) / "source.bin"
    return intake_root, relative_path, b"immutable evidence\n"


def test_immutable_publication_rejects_existing_symlink(tmp_path: Path) -> None:
    module = _resolution_module()
    intake_root, relative_path, payload = _artifact_target(tmp_path)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(payload)
    target = intake_root / relative_path
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)

    with pytest.raises(module.DoubleCheckPersistenceError, match="immutable artifact"):
        module._write_immutable_artifact(intake_root, relative_path, payload)

    assert outside.read_bytes() == payload


def test_immutable_publication_rejects_existing_hardlink(tmp_path: Path) -> None:
    module = _resolution_module()
    intake_root, relative_path, payload = _artifact_target(tmp_path)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(payload)
    target = intake_root / relative_path
    target.parent.mkdir(parents=True)
    os.link(outside, target)

    with pytest.raises(module.DoubleCheckPersistenceError, match="immutable artifact"):
        module._write_immutable_artifact(intake_root, relative_path, payload)

    assert outside.read_bytes() == payload
    assert os.stat(outside).st_nlink == 2


def test_immutable_publication_detects_destination_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root, relative_path, payload = _artifact_target(tmp_path)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(payload)
    original_link = os.link

    def _swap_after_link(src, dst, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        result = original_link(src, dst, *args, **kwargs)
        destination_dir_fd = kwargs.get("dst_dir_fd")
        os.unlink(dst, dir_fd=destination_dir_fd)
        os.symlink(outside, dst, dir_fd=destination_dir_fd)
        return result

    monkeypatch.setattr(module.os, "link", _swap_after_link)

    with pytest.raises(module.DoubleCheckPersistenceError, match="immutable artifact"):
        module._write_immutable_artifact(intake_root, relative_path, payload)

    assert outside.read_bytes() == payload


def test_immutable_publication_detects_parent_swap_and_leaves_no_outside_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root, relative_path, payload = _artifact_target(tmp_path)
    target_parent = (intake_root / relative_path).parent
    outside_parent = tmp_path / "swapped-parent"
    original_link = os.link
    swapped = False

    def _swap_parent_before_link(src, dst, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        nonlocal swapped
        if not swapped:
            target_parent.rename(outside_parent)
            target_parent.mkdir(parents=True)
            swapped = True
        return original_link(src, dst, *args, **kwargs)

    monkeypatch.setattr(module.os, "link", _swap_parent_before_link)

    with pytest.raises(module.DoubleCheckPersistenceError, match="immutable artifact"):
        module._write_immutable_artifact(intake_root, relative_path, payload)

    assert not any(path.is_file() for path in outside_parent.rglob("*"))
    assert not (intake_root / relative_path).exists()


def test_immutable_publication_fsyncs_file_and_containing_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _resolution_module()
    intake_root, relative_path, payload = _artifact_target(tmp_path)
    original_fsync = os.fsync
    fsynced_modes: list[int] = []

    def _record_fsync(descriptor: int) -> None:
        fsynced_modes.append(os.fstat(descriptor).st_mode)
        original_fsync(descriptor)

    monkeypatch.setattr(module.os, "fsync", _record_fsync)

    module._write_immutable_artifact(intake_root, relative_path, payload)

    assert any(stat.S_ISREG(mode) for mode in fsynced_modes)
    assert any(stat.S_ISDIR(mode) for mode in fsynced_modes)


def test_review_change_creates_new_snapshot_without_mutating_old_run(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    run_1, result_1, _decision_1 = _create_mismatch(session, intake_root=tmp_path / "intake")
    old_row_key = result_1.row_key
    old_report = (tmp_path / "intake" / run_1.report_path).read_bytes()
    decision_2 = apply_review_decision(
        session,
        record=_record(),
        decision=ReviewDecision.CORRECT,
        corrected_value=42,
        note="second official correction",
        identity=TEST_IDENTITY,
    )
    run_2 = module.create_external_comparison_run(
        session,
        intake_root=tmp_path / "intake",
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()
    _run_model, result_model, _resolution_model = _task5_models()
    result_2 = session.scalar(select(result_model).where(result_model.run_id == run_2.run_id))

    assert result_2 is not None
    assert run_2.run_id != run_1.run_id
    assert run_2.external_file_path == run_1.external_file_path
    assert run_2.report_path != run_1.report_path
    assert result_2.review_decision_revision == 2
    assert result_2.review_audit_action_id == decision_2.audit_action_id
    assert result_2.eidp_value == 42
    assert result_2.row_key != old_row_key
    assert result_1.eidp_value == 41
    assert (tmp_path / "intake" / run_1.report_path).read_bytes() == old_report


@pytest.mark.parametrize(
    ("outcome_name", "corrected_value", "expected_effective"),
    [
        ("ACCEPT_EIDP", None, 41),
        ("ACCEPT_EXTERNAL", 40, 40),
        ("CORRECT", 39, 39),
        ("EXCLUDE", None, None),
    ],
)
def test_all_resolution_outcomes_append_and_audit_complete_payload(
    session: Session,
    tmp_path: Path,
    outcome_name: str,
    corrected_value: int | None,
    expected_effective: int | None,
) -> None:
    module = _resolution_module()
    run, result, _decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    resolution = module.resolve_double_check(
        session,
        comparison_result_id=result.id,
        outcome=getattr(module.ResolutionOutcome, outcome_name),
        corrected_value=corrected_value,
        reason="  independently checked  ",
        identity=TEST_IDENTITY,
    )
    session.commit()
    audit = session.scalar(
        select(ManualActionLog).where(ManualActionLog.action_id == resolution.audit_action_id)
    )

    assert audit is not None
    assert UUID(resolution.resolution_id)
    assert UUID(resolution.audit_action_id)
    assert resolution.revision == 1
    assert resolution.corrected_value == corrected_value
    assert resolution.effective_value == expected_effective
    assert resolution.reason == "independently checked"
    assert resolution.actor == TEST_IDENTITY.actor
    assert resolution.identity_source == TEST_IDENTITY.source.value
    assert audit.target_id is None
    assert audit.action_type == "double_check_resolution"
    assert audit.target_table == "double_check_resolution"
    assert audit.reason == "independently checked"
    payload = json.loads(audit.new_value or "null")
    assert payload == {
        "comparison_result_id": result.id,
        "corrected_value": corrected_value,
        "effective_value": expected_effective,
        "eidp_value": 41,
        "external_file_sha256": run.external_file_sha256,
        "external_source_row_key": result.external_source_row_key,
        "external_value": 40,
        "outcome": getattr(module.ResolutionOutcome, outcome_name).value,
        "reason": "independently checked",
        "resolution_id": resolution.resolution_id,
        "revision": 1,
        "review_audit_action_id": result.review_audit_action_id,
        "review_decision_revision": 1,
        "review_id": result.review_id,
        "row_key": result.row_key,
        "run_id": run.run_id,
    }


@pytest.mark.parametrize(
    ("outcome_name", "corrected_value", "reason", "message"),
    [
        ("ACCEPT_EIDP", 41, "checked", "not allowed"),
        ("ACCEPT_EXTERNAL", None, "checked", "required"),
        ("ACCEPT_EXTERNAL", 39, "checked", "must equal"),
        ("CORRECT", None, "checked", "required"),
        ("CORRECT", -1, "checked", "non-negative"),
        ("EXCLUDE", 40, "checked", "not allowed"),
        ("ACCEPT_EIDP", None, "", "reason is required"),
        ("ACCEPT_EIDP", None, "   ", "reason is required"),
        ("ACCEPT_EIDP", None, "x" * 501, "at most 500"),
    ],
)
def test_invalid_resolution_writes_neither_resolution_nor_audit(
    session: Session,
    tmp_path: Path,
    outcome_name: str,
    corrected_value: int | None,
    reason: str,
    message: str,
) -> None:
    module = _resolution_module()
    _run, result, _decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    _run_model, _result_model, resolution_model = _task5_models()
    audit_count = session.scalar(select(func.count()).select_from(ManualActionLog))

    with pytest.raises(module.DoubleCheckResolutionError, match=message):
        module.resolve_double_check(
            session,
            comparison_result_id=result.id,
            outcome=getattr(module.ResolutionOutcome, outcome_name),
            corrected_value=corrected_value,
            reason=reason,
            identity=TEST_IDENTITY,
        )
    session.commit()

    assert session.scalar(select(func.count()).select_from(resolution_model)) == 0
    assert session.scalar(select(func.count()).select_from(ManualActionLog)) == audit_count


def test_audit_failure_leaves_no_resolution_or_audit(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    _run, result, _decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    _run_model, _result_model, resolution_model = _task5_models()
    audit_count = session.scalar(select(func.count()).select_from(ManualActionLog))

    def _fail_resolution_audit(_mapper, _connection, target):  # noqa: ANN001, ANN202
        if target.action_type == "double_check_resolution":
            raise RuntimeError("injected resolution audit failure")

    event.listen(ManualActionLog, "before_insert", _fail_resolution_audit)
    try:
        with pytest.raises(RuntimeError, match="injected resolution audit failure"):
            module.resolve_double_check(
                session,
                comparison_result_id=result.id,
                outcome=module.ResolutionOutcome.ACCEPT_EIDP,
                corrected_value=None,
                reason="checked",
                identity=TEST_IDENTITY,
            )
        session.rollback()
    finally:
        event.remove(ManualActionLog, "before_insert", _fail_resolution_audit)

    assert session.scalar(select(func.count()).select_from(resolution_model)) == 0
    assert session.scalar(select(func.count()).select_from(ManualActionLog)) == audit_count


def test_resolution_service_flushes_without_committing(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    _run, result, _decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    _run_model, _result_model, resolution_model = _task5_models()
    audit_count = session.scalar(select(func.count()).select_from(ManualActionLog))
    module.resolve_double_check(
        session,
        comparison_result_id=result.id,
        outcome=module.ResolutionOutcome.ACCEPT_EIDP,
        corrected_value=None,
        reason="checked",
        identity=TEST_IDENTITY,
    )
    session.rollback()

    assert session.scalar(select(func.count()).select_from(resolution_model)) == 0
    assert session.scalar(select(func.count()).select_from(ManualActionLog)) == audit_count


def test_latest_resolution_overlay_survives_restart(
    engine,  # noqa: ANN001
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    _run_model, _result_model, resolution_model = _task5_models()
    with Session(engine) as first_session:
        run, result, _decision = _create_mismatch(first_session, intake_root=tmp_path / "intake")
        first = module.resolve_double_check(
            first_session,
            comparison_result_id=result.id,
            outcome=module.ResolutionOutcome.ACCEPT_EIDP,
            corrected_value=None,
            reason="first pass",
            identity=TEST_IDENTITY,
        )
        first_session.commit()
        first_resolution_id = first.resolution_id
        second = module.resolve_double_check(
            first_session,
            comparison_result_id=result.id,
            outcome=module.ResolutionOutcome.CORRECT,
            corrected_value=39,
            reason="latest official value",
            identity=TEST_IDENTITY,
        )
        first_session.commit()
        second_resolution_id = second.resolution_id
        result_id = result.id
        run_id = run.run_id

    with Session(engine) as restarted_session:
        persisted_results = module.load_external_comparison_results(restarted_session, run_id=run_id)
        latest = module.latest_double_check_resolutions(
            restarted_session,
            comparison_result_ids=[result_id],
        )
        all_resolutions = restarted_session.scalars(
            select(resolution_model)
            .where(resolution_model.comparison_result_id == result_id)
            .order_by(resolution_model.revision)
        ).all()

        assert [item.id for item in persisted_results] == [result_id]
        assert [item.revision for item in all_resolutions] == [1, 2]
        assert [item.resolution_id for item in all_resolutions] == [
            first_resolution_id,
            second_resolution_id,
        ]
        assert latest[result_id].revision == 2
        assert latest[result_id].effective_value == 39
        assert latest[result_id].reason == "latest official value"


def test_external_only_snapshot_has_nullable_review_provenance(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    run = module.create_external_comparison_run(
        session,
        intake_root=tmp_path / "intake",
        review_records=[],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()
    _run_model, result_model, _resolution_model = _task5_models()
    result = session.scalar(select(result_model).where(result_model.run_id == run.run_id))

    assert result is not None
    assert result.review_id is None
    assert result.review_decision_revision is None
    assert result.review_audit_action_id is None
    assert result.eidp_value is None
    assert result.external_value == 40
    assert result.external_source_row_key == f"{run.external_file_sha256}:2:capacity"
    assert result.comparison_status == "missing_in_eidp"


def test_model_enforces_append_only_unique_foreign_key_and_checks() -> None:
    run_model, result_model, resolution_model = _task5_models()

    def _unique_columns(model: type[object]) -> set[tuple[str, ...]]:
        return {
            tuple(constraint.columns.keys())
            for constraint in model.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }

    assert ("run_id",) in _unique_columns(run_model)
    assert ("run_id", "row_key") in _unique_columns(result_model)
    assert ("resolution_id",) in _unique_columns(resolution_model)
    assert ("audit_action_id",) in _unique_columns(resolution_model)
    assert ("comparison_result_id", "revision") in _unique_columns(resolution_model)

    result_checks = " ".join(
        str(constraint.sqltext).lower()
        for constraint in result_model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    )
    resolution_checks = " ".join(
        str(constraint.sqltext).lower()
        for constraint in resolution_model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    )
    assert "review_decision_revision" in result_checks and "review_audit_action_id" in result_checks
    assert "length(external_file_sha256) = 64" in result_checks
    assert "revision >= 1" in resolution_checks
    assert "accept_eidp" in resolution_checks
    assert "accept_external" in resolution_checks
    assert "correct" in resolution_checks
    assert "exclude" in resolution_checks
    assert "trim" in resolution_checks and "500" in resolution_checks
    assert "effective_value" in resolution_checks and "corrected_value" in resolution_checks


def test_base_metadata_creates_task5_sqlite_immutability_triggers(engine) -> None:  # noqa: ANN001
    with engine.connect() as connection:
        names = set(
            connection.scalars(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            ).all()
        )

    assert TASK5_IMMUTABILITY_TRIGGERS <= names


@pytest.mark.parametrize(
    ("table_name", "column_name"),
    [
        ("external_comparison_run", "original_filename"),
        ("external_comparison_result", "mismatch_reason"),
        ("double_check_resolution", "reason"),
    ],
)
@pytest.mark.parametrize("operation", ["update", "delete"])
def test_sqlite_rejects_raw_mutation_of_task5_history(
    session: Session,
    tmp_path: Path,
    table_name: str,
    column_name: str,
    operation: str,
) -> None:
    module = _resolution_module()
    run, result, _decision = _create_mismatch(session, intake_root=tmp_path / "intake")
    resolution = module.resolve_double_check(
        session,
        comparison_result_id=result.id,
        outcome=module.ResolutionOutcome.ACCEPT_EIDP,
        corrected_value=None,
        reason="checked",
        identity=TEST_IDENTITY,
    )
    target_ids = {
        "external_comparison_run": run.id,
        "external_comparison_result": result.id,
        "double_check_resolution": resolution.id,
    }
    session.commit()
    statement = (
        f"UPDATE {table_name} SET {column_name} = {column_name} WHERE id = :target_id"
        if operation == "update"
        else f"DELETE FROM {table_name} WHERE id = :target_id"
    )

    with session.get_bind().connect() as connection:
        with pytest.raises(IntegrityError, match="immutable|append-only"):
            connection.execute(text(statement), {"target_id": target_ids[table_name]})
        connection.rollback()


def test_database_rejects_orphan_result_foreign_key(session: Session) -> None:
    _run_model, result_model, _resolution_model = _task5_models()
    session.add(
        result_model(
            run_id=str(uuid4()),
            row_key="a" * 64,
            comparison_key="missing-run",
            review_id=None,
            review_decision_revision=None,
            review_audit_action_id=None,
            external_source_row_key="b" * 64,
            external_value=1,
            external_file_sha256="c" * 64,
            eidp_value=None,
            comparison_status="missing_in_eidp",
            mismatch_reason="missing",
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_database_rejects_result_hash_from_a_different_parent_run(
    session: Session,
    tmp_path: Path,
) -> None:
    module = _resolution_module()
    run = module.create_external_comparison_run(
        session,
        intake_root=tmp_path / "intake",
        review_records=[_record()],
        external_file_bytes=EXTERNAL_CSV,
        original_filename="copilot.csv",
        source_system=ExternalSourceSystem.COPILOT,
        identity=TEST_IDENTITY,
    )
    session.commit()
    different_hash = "f" * 64
    assert different_hash != run.external_file_sha256

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                """
                INSERT INTO external_comparison_result (
                    run_id,
                    row_key,
                    comparison_key,
                    external_file_sha256,
                    comparison_status,
                    mismatch_reason
                ) VALUES (
                    :run_id,
                    :row_key,
                    :comparison_key,
                    :external_file_sha256,
                    :comparison_status,
                    :mismatch_reason
                )
                """
            ),
            {
                "run_id": run.run_id,
                "row_key": "d" * 64,
                "comparison_key": "mixed-parent-hash",
                "external_file_sha256": different_hash,
                "comparison_status": "missing_in_external",
                "mismatch_reason": "adversarial parent hash",
            },
        )
    session.rollback()


@pytest.mark.parametrize("mismatch", ["review_id", "revision", "missing_review_id"])
def test_database_rejects_mixed_review_provenance(
    session: Session,
    tmp_path: Path,
    mismatch: str,
) -> None:
    run, _result, decision_a1 = _create_mismatch(session, intake_root=tmp_path / "intake")
    decision_a2 = apply_review_decision(
        session,
        record=_record(),
        decision=ReviewDecision.CORRECT,
        corrected_value=42,
        note="second decision",
        identity=TEST_IDENTITY,
    )
    record_b = replace(_record(), review_id="metric-review-2", intake_record_id="intake-2")
    decision_b1 = apply_review_decision(
        session,
        record=record_b,
        decision=ReviewDecision.CORRECT,
        corrected_value=43,
        note="different record",
        identity=TEST_IDENTITY,
    )
    session.commit()
    run_id = run.run_id
    file_hash = run.external_file_sha256

    if mismatch == "review_id":
        review_id, revision, action_id = _record().review_id, decision_a1.revision, decision_b1.audit_action_id
    elif mismatch == "revision":
        review_id, revision, action_id = _record().review_id, decision_a2.revision, decision_a1.audit_action_id
    else:
        review_id, revision, action_id = None, decision_a1.revision, decision_a1.audit_action_id

    _run_model, result_model, _resolution_model = _task5_models()
    session.add(
        result_model(
            run_id=run_id,
            row_key=sha256(f"mixed-{mismatch}".encode()).hexdigest(),
            comparison_key=f"mixed-{mismatch}",
            review_id=review_id,
            review_decision_revision=revision,
            review_audit_action_id=action_id,
            external_source_row_key=None,
            external_value=None,
            external_file_sha256=file_hash,
            eidp_value=1,
            comparison_status="missing_in_external",
            mismatch_reason="adversarial provenance",
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_migration_contract() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/ae1f2a3b4c5d_add_double_check_resolutions.py"
    )
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("task5_double_check_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "ae1f2a3b4c5d"
    assert migration.down_revision == "9d0e1f2a3b4c"


def test_migration_schema_matches_task5_models(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    database_url = f"sqlite:///{tmp_path / 'migrated.sqlite3'}"
    migrated_engine = create_engine(database_url, future=True)
    try:
        ManualActionLog.__table__.create(migrated_engine)
        importlib.import_module("eidp.db.models").ExtractionReviewDecision.__table__.create(
            migrated_engine
        )
        migration_path = (
            repository_root
            / "migrations/versions/ae1f2a3b4c5d_add_double_check_resolutions.py"
        )
        spec = importlib.util.spec_from_file_location("task5_schema_equivalence_migration", migration_path)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with migrated_engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()

        schema = inspect(migrated_engine)
        for model in _task5_models():
            table = model.__table__
            reflected_columns = {column["name"]: column for column in schema.get_columns(table.name)}
            assert set(reflected_columns) == set(table.columns.keys())
            assert {
                name: bool(column["nullable"])
                for name, column in reflected_columns.items()
            } == {column.name: column.nullable for column in table.columns}

            reflected_uniques = {
                constraint["name"] for constraint in schema.get_unique_constraints(table.name)
            }
            model_uniques = {
                constraint.name
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
            }
            assert reflected_uniques == model_uniques

            reflected_checks = {
                constraint["name"] for constraint in schema.get_check_constraints(table.name)
            }
            model_checks = {
                constraint.name
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            }
            assert reflected_checks == model_checks

            reflected_foreign_keys = {
                (
                    tuple(constraint["constrained_columns"]),
                    constraint["referred_table"],
                    tuple(constraint["referred_columns"]),
                )
                for constraint in schema.get_foreign_keys(table.name)
            }
            model_foreign_keys = {
                (
                    tuple(element.parent.name for element in constraint.elements),
                    constraint.referred_table.name,
                    tuple(element.column.name for element in constraint.elements),
                )
                for constraint in table.foreign_key_constraints
            }
            assert reflected_foreign_keys == model_foreign_keys

        provenance_indexes = {
            index["name"]: index for index in schema.get_indexes("extraction_review_decision")
        }
        assert provenance_indexes["uq_extraction_review_decision_provenance"]["unique"]

        with migrated_engine.connect() as connection:
            trigger_names = set(
                connection.scalars(
                    text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
                ).all()
            )
        assert TASK5_IMMUTABILITY_TRIGGERS <= trigger_names
    finally:
        migrated_engine.dispose()
