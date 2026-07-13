"""Persistent external comparison snapshots and append-only human resolutions."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import TypeGuard
from uuid import uuid4

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, SessionTransaction

from eidp.db.audit import log_manual_action
from eidp.db.models import (
    DoubleCheckResolution,
    ExternalComparisonResult,
    ExternalComparisonRun,
    ExtractionReviewDecision,
)
from eidp.identity import ResolvedIdentity
from eidp.pipeline.double_check_compare import (
    DoubleCheckResultRow,
    compare_external_to_reviewed,
    double_check_report_csv,
)
from eidp.pipeline.external_extraction_import import (
    ExternalSourceSystem,
    load_external_extraction_file,
)
from eidp.pipeline.extraction_review import ExtractionReviewRecord
from eidp.pipeline.review_decision import overlay_review_decisions
from eidp.pipeline.review_report import reviewed_rows_from_records

__all__ = [
    "DoubleCheckPersistenceError",
    "DoubleCheckResolutionError",
    "ResolutionOutcome",
    "create_external_comparison_run",
    "latest_double_check_resolutions",
    "load_external_comparison_results",
    "resolve_double_check",
]


class DoubleCheckPersistenceError(ValueError):
    """Raised when immutable comparison evidence cannot be safely persisted."""


class DoubleCheckResolutionError(ValueError):
    """Raised when a human resolution violates the snapshot-bound contract."""


class ResolutionOutcome(StrEnum):
    ACCEPT_EIDP = "accept_eidp"
    ACCEPT_EXTERNAL = "accept_external"
    CORRECT = "correct"
    EXCLUDE = "exclude"


@dataclass(frozen=True)
class _PublishedArtifact:
    root: Path
    relative_path: Path
    device: int
    inode: int


@dataclass
class _ArtifactTransactionState:
    transaction: SessionTransaction
    artifacts: list[_PublishedArtifact]
    committed: bool = False


_PENDING_ARTIFACTS_KEY = "eidp_double_check_pending_artifacts"


@event.listens_for(Session, "after_commit")
def _mark_committed_artifacts(session: Session) -> None:
    if session.in_nested_transaction():
        return
    state = _pending_artifact_state(session)
    if state is None:
        return
    transaction = session.get_transaction()
    if transaction is None or state.transaction is not transaction:
        raise DoubleCheckPersistenceError("invalid pending artifact cleanup state")
    state.committed = True


@event.listens_for(Session, "after_transaction_end")
def _finalize_transaction_artifacts(session: Session, transaction: SessionTransaction) -> None:
    if transaction.parent is not None:
        return
    state = _pending_artifact_state(session)
    if state is None:
        return
    if state.transaction is not transaction:
        raise DoubleCheckPersistenceError("invalid pending artifact cleanup state")
    session.info.pop(_PENDING_ARTIFACTS_KEY, None)
    if not state.committed:
        _remove_artifacts(state.artifacts)


def create_external_comparison_run(
    session: Session,
    *,
    intake_root: Path,
    review_records: Sequence[ExtractionReviewRecord],
    external_file_bytes: bytes,
    original_filename: str,
    source_system: ExternalSourceSystem | str,
    identity: ResolvedIdentity,
) -> ExternalComparisonRun:
    """Create one immutable comparison run and row snapshots without committing."""
    resolved_source = ExternalSourceSystem(source_system)
    external_rows = load_external_extraction_file(
        external_file_bytes,
        filename=original_filename,
        source_system=resolved_source,
    )
    overlaid_records = overlay_review_decisions(session, list(review_records))
    reviewed_rows = reviewed_rows_from_records(overlaid_records)
    comparison_rows = compare_external_to_reviewed(reviewed_rows, external_rows)
    latest_decisions = _latest_review_decisions(session, overlaid_records)
    if not session.in_transaction():
        session.begin()

    file_hash = sha256(external_file_bytes).hexdigest()
    report_bytes = double_check_report_csv(comparison_rows).encode("utf-8")
    report_hash = sha256(report_bytes).hexdigest()
    source_relative_path = Path("external") / file_hash / "source.bin"
    report_relative_path = Path("external") / file_hash / "reports" / f"{report_hash}.csv"
    published: list[_PublishedArtifact] = []
    try:
        for relative_path, payload in (
            (source_relative_path, external_file_bytes),
            (report_relative_path, report_bytes),
        ):
            artifact = _write_immutable_artifact(intake_root, relative_path, payload)
            if artifact is not None:
                published.append(artifact)
                _register_pending_artifact(session, artifact)

        run = ExternalComparisonRun(
            run_id=str(uuid4()),
            source_system=resolved_source.value,
            external_file_sha256=file_hash,
            original_filename=original_filename,
            external_file_path=source_relative_path.as_posix(),
            report_sha256=report_hash,
            report_path=report_relative_path.as_posix(),
            actor=identity.actor,
            identity_source=identity.source.value,
        )
        session.add(run)
        session.flush()

        seen_row_keys: set[str] = set()
        for row in comparison_rows:
            decision = latest_decisions.get(row.review_id) if row.review_id is not None else None
            external_source_row_key = _external_source_row_key(row, file_hash=file_hash)
            row_key = _snapshot_row_key(
                row,
                decision=decision,
                external_source_row_key=external_source_row_key,
            )
            if row_key in seen_row_keys:
                raise DoubleCheckPersistenceError("comparison emitted a duplicate deterministic row key")
            seen_row_keys.add(row_key)
            session.add(
                ExternalComparisonResult(
                    run_id=run.run_id,
                    row_key=row_key,
                    comparison_key=row.key,
                    review_id=row.review_id,
                    review_decision_revision=decision.revision if decision is not None else None,
                    review_audit_action_id=decision.audit_action_id if decision is not None else None,
                    external_source_row_key=external_source_row_key,
                    external_value=row.external_value,
                    external_file_sha256=file_hash,
                    eidp_value=row.eidp_value,
                    comparison_status=row.comparison_status.value,
                    mismatch_reason=row.mismatch_reason,
                )
            )
        session.flush()
        return run
    except Exception:
        _remove_registered_artifacts(session, published)
        raise


def load_external_comparison_results(
    session: Session,
    *,
    run_id: str,
) -> list[ExternalComparisonResult]:
    """Load persisted row snapshots for a run in stable insertion order."""
    return list(
        session.scalars(
            select(ExternalComparisonResult)
            .where(ExternalComparisonResult.run_id == run_id)
            .order_by(ExternalComparisonResult.id)
        ).all()
    )


def latest_double_check_resolutions(
    session: Session,
    *,
    comparison_result_ids: Sequence[int] | None = None,
) -> dict[int, DoubleCheckResolution]:
    """Return each comparison result's highest persisted resolution revision."""
    if comparison_result_ids is not None and not comparison_result_ids:
        return {}
    statement = select(DoubleCheckResolution).order_by(
        DoubleCheckResolution.comparison_result_id,
        DoubleCheckResolution.revision,
    )
    if comparison_result_ids is not None:
        statement = statement.where(
            DoubleCheckResolution.comparison_result_id.in_(set(comparison_result_ids))
        )
    latest: dict[int, DoubleCheckResolution] = {}
    for resolution in session.scalars(statement).all():
        latest[resolution.comparison_result_id] = resolution
    return latest


def resolve_double_check(
    session: Session,
    *,
    comparison_result_id: int,
    outcome: ResolutionOutcome,
    corrected_value: int | None,
    reason: str,
    identity: ResolvedIdentity,
) -> DoubleCheckResolution:
    """Insert one append-only resolution and matching audit row without committing."""
    result = session.get(ExternalComparisonResult, comparison_result_id)
    if result is None:
        raise DoubleCheckResolutionError("comparison result does not exist")

    normalized_outcome = ResolutionOutcome(outcome)
    normalized_reason = _normalize_reason(reason)
    effective_value = _effective_value(
        result=result,
        outcome=normalized_outcome,
        corrected_value=corrected_value,
    )
    max_revision = session.scalar(
        select(func.max(DoubleCheckResolution.revision)).where(
            DoubleCheckResolution.comparison_result_id == comparison_result_id
        )
    )
    revision = int(max_revision or 0) + 1
    resolution_id = str(uuid4())
    audit_payload: dict[str, object] = {
        "comparison_result_id": result.id,
        "corrected_value": corrected_value,
        "effective_value": effective_value,
        "eidp_value": result.eidp_value,
        "external_file_sha256": result.external_file_sha256,
        "external_source_row_key": result.external_source_row_key,
        "external_value": result.external_value,
        "outcome": normalized_outcome.value,
        "reason": normalized_reason,
        "resolution_id": resolution_id,
        "revision": revision,
        "review_audit_action_id": result.review_audit_action_id,
        "review_decision_revision": result.review_decision_revision,
        "review_id": result.review_id,
        "row_key": result.row_key,
        "run_id": result.run_id,
    }
    audit = log_manual_action(
        session,
        action_type="double_check_resolution",
        target_table="double_check_resolution",
        new_value=audit_payload,
        reason=normalized_reason,
        identity=identity,
    )
    resolution = DoubleCheckResolution(
        resolution_id=resolution_id,
        comparison_result_id=result.id,
        revision=revision,
        outcome=normalized_outcome.value,
        corrected_value=corrected_value,
        effective_value=effective_value,
        reason=normalized_reason,
        actor=identity.actor,
        identity_source=identity.source.value,
        audit_action_id=audit.action_id,
    )
    session.add(resolution)
    session.flush()
    return resolution


def _latest_review_decisions(
    session: Session,
    records: Sequence[ExtractionReviewRecord],
) -> dict[str, ExtractionReviewDecision]:
    review_ids = {record.review_id for record in records}
    if not review_ids:
        return {}
    latest: dict[str, ExtractionReviewDecision] = {}
    decisions = session.scalars(
        select(ExtractionReviewDecision)
        .where(ExtractionReviewDecision.review_id.in_(review_ids))
        .order_by(ExtractionReviewDecision.review_id, ExtractionReviewDecision.revision)
    ).all()
    for decision in decisions:
        latest[decision.review_id] = decision
    return latest


def _external_source_row_key(row: DoubleCheckResultRow, *, file_hash: str) -> str | None:
    if row.source_row_number is None:
        return None
    return f"{file_hash}:{row.source_row_number}:{row.metric}"


def _snapshot_row_key(
    row: DoubleCheckResultRow,
    *,
    decision: ExtractionReviewDecision | None,
    external_source_row_key: str | None,
) -> str:
    sentinel = "<none>"
    canonical = (
        row.key,
        row.review_id or sentinel,
        str(decision.revision) if decision is not None else sentinel,
        decision.audit_action_id if decision is not None else sentinel,
        external_source_row_key or sentinel,
    )
    encoded = json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalize_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise DoubleCheckResolutionError("reason is required")
    if len(normalized) > 500:
        raise DoubleCheckResolutionError("reason must be at most 500 characters")
    return normalized


def _effective_value(
    *,
    result: ExternalComparisonResult,
    outcome: ResolutionOutcome,
    corrected_value: int | None,
) -> int | None:
    if outcome is ResolutionOutcome.ACCEPT_EIDP:
        if corrected_value is not None:
            raise DoubleCheckResolutionError("corrected_value is not allowed for accept_eidp")
        if not _is_int_value(result.eidp_value):
            raise DoubleCheckResolutionError("EIDP snapshot has no integer value")
        return result.eidp_value
    if outcome is ResolutionOutcome.ACCEPT_EXTERNAL:
        if not _is_int_value(corrected_value):
            raise DoubleCheckResolutionError("corrected_value is required for accept_external")
        if corrected_value != result.external_value:
            raise DoubleCheckResolutionError("corrected_value must equal the snapshot external value")
        return corrected_value
    if outcome is ResolutionOutcome.CORRECT:
        if not _is_int_value(corrected_value):
            raise DoubleCheckResolutionError("corrected_value is required for correct")
        if corrected_value < 0:
            raise DoubleCheckResolutionError("corrected_value must be non-negative")
        return corrected_value
    if corrected_value is not None:
        raise DoubleCheckResolutionError("corrected_value is not allowed for exclude")
    return None


def _is_int_value(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _register_pending_artifact(session: Session, artifact: _PublishedArtifact) -> None:
    transaction = session.get_transaction()
    if transaction is None:
        raise DoubleCheckPersistenceError("invalid pending artifact cleanup state")
    state = _pending_artifact_state(session)
    if state is None:
        state = _ArtifactTransactionState(transaction=transaction, artifacts=[])
        session.info[_PENDING_ARTIFACTS_KEY] = state
    elif state.transaction is not transaction:
        raise DoubleCheckPersistenceError("invalid pending artifact cleanup state")
    state.artifacts.append(artifact)


def _remove_registered_artifacts(session: Session, artifacts: Sequence[_PublishedArtifact]) -> None:
    state = session.info.get(_PENDING_ARTIFACTS_KEY)
    if isinstance(state, _ArtifactTransactionState):
        for artifact in artifacts:
            if artifact in state.artifacts:
                state.artifacts.remove(artifact)
        if not state.artifacts:
            session.info.pop(_PENDING_ARTIFACTS_KEY, None)
    _remove_artifacts(artifacts)


def _pending_artifact_state(session: Session) -> _ArtifactTransactionState | None:
    state = session.info.get(_PENDING_ARTIFACTS_KEY)
    if state is None:
        return None
    if not isinstance(state, _ArtifactTransactionState):
        raise DoubleCheckPersistenceError("invalid pending artifact cleanup state")
    return state


def _remove_artifacts(artifacts: Sequence[_PublishedArtifact]) -> None:
    cleanup_failures: list[Exception] = []
    for artifact in reversed(artifacts):
        try:
            _unlink_published_artifact(artifact)
        except Exception as exc:
            cleanup_failures.append(exc)
    if cleanup_failures:
        raise DoubleCheckPersistenceError("immutable artifact cleanup failed") from None


def _write_immutable_artifact(
    intake_root: Path,
    relative_path: Path,
    payload: bytes,
) -> _PublishedArtifact | None:
    root, components = _validated_artifact_path(intake_root, relative_path)
    root.mkdir(parents=True, exist_ok=True)
    directory_fds: list[int] = []
    directory_chain: list[tuple[int, str, int]] = []
    try:
        root_fd = _open_directory(root)
        directory_fds.append(root_fd)
        parent_fd = root_fd
        for component in components[:-1]:
            child_fd = _open_or_create_child_directory(parent_fd, component)
            directory_chain.append((parent_fd, component, child_fd))
            directory_fds.append(child_fd)
            parent_fd = child_fd

        target_name = components[-1]
        tmp_name = f".{target_name}.{uuid4().hex}.tmp"
        tmp_fd = -1
        tmp_exists = False
        created_target = False
        expected_identity: tuple[int, int] | None = None
        try:
            try:
                tmp_fd = os.open(
                    tmp_name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=parent_fd,
                )
                tmp_exists = True
                _write_all(tmp_fd, payload)
                os.fsync(tmp_fd)
                temporary_stat = os.fstat(tmp_fd)
                expected_identity = (temporary_stat.st_dev, temporary_stat.st_ino)

                try:
                    os.link(
                        tmp_name,
                        target_name,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                        follow_symlinks=False,
                    )
                    created_target = True
                except FileExistsError:
                    _validate_opened_artifact(parent_fd, target_name, payload)
                else:
                    os.unlink(tmp_name, dir_fd=parent_fd)
                    tmp_exists = False
                    os.fsync(parent_fd)
                    published_stat = _validate_opened_artifact(parent_fd, target_name, payload)
                    if (published_stat.st_dev, published_stat.st_ino) != expected_identity:
                        raise DoubleCheckPersistenceError("immutable artifact destination was swapped")

                _validate_directory_chain(directory_chain)
                os.fsync(parent_fd)
            except DoubleCheckPersistenceError:
                if created_target and expected_identity is not None:
                    _unlink_if_identity_matches(parent_fd, target_name, expected_identity)
                raise
            except OSError as exc:
                if created_target and expected_identity is not None:
                    _unlink_if_identity_matches(parent_fd, target_name, expected_identity)
                raise DoubleCheckPersistenceError("immutable artifact publication failed") from exc
        finally:
            if tmp_fd >= 0:
                os.close(tmp_fd)
            if tmp_exists:
                try:
                    os.unlink(tmp_name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
                except FileNotFoundError:
                    pass

        if not created_target:
            return None
        if expected_identity is None:
            raise DoubleCheckPersistenceError("immutable artifact identity is unavailable")
        return _PublishedArtifact(
            root=root,
            relative_path=Path(*components),
            device=expected_identity[0],
            inode=expected_identity[1],
        )
    except DoubleCheckPersistenceError:
        raise
    except OSError as exc:
        raise DoubleCheckPersistenceError("immutable artifact path is unsafe") from exc
    finally:
        for descriptor in reversed(directory_fds):
            os.close(descriptor)


def _validated_artifact_path(intake_root: Path, relative_path: Path) -> tuple[Path, tuple[str, ...]]:
    candidate = Path(relative_path)
    components = candidate.parts
    if (
        candidate.is_absolute()
        or len(components) < 2
        or components[0] != "external"
        or any(component in {"", ".", ".."} for component in components)
    ):
        raise DoubleCheckPersistenceError("immutable artifact path must stay beneath intake_root/external")
    return Path(os.path.abspath(intake_root)), components


def _open_directory(path: Path) -> int:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise DoubleCheckPersistenceError("immutable artifact directory is not regular")
    return descriptor


def _open_or_create_child_directory(parent_fd: int, name: str) -> int:
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
    except FileExistsError:
        pass
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=parent_fd,
    )
    child_stat = os.fstat(descriptor)
    if not stat.S_ISDIR(child_stat.st_mode):
        os.close(descriptor)
        raise DoubleCheckPersistenceError("immutable artifact parent is not a directory")
    if created:
        os.fsync(parent_fd)
    return descriptor


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short immutable artifact write")
        remaining = remaining[written:]


def _validate_opened_artifact(parent_fd: int, name: str, payload: bytes) -> os.stat_result:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise DoubleCheckPersistenceError("existing immutable artifact is unsafe") from exc
    try:
        artifact_stat = os.fstat(descriptor)
        if not stat.S_ISREG(artifact_stat.st_mode) or artifact_stat.st_nlink != 1:
            raise DoubleCheckPersistenceError("existing immutable artifact must be a single-link regular file")
        if artifact_stat.st_size != len(payload) or not _descriptor_matches(descriptor, payload):
            raise DoubleCheckPersistenceError("existing immutable artifact content differs")
        os.fsync(descriptor)
        return artifact_stat
    finally:
        os.close(descriptor)


def _descriptor_matches(descriptor: int, payload: bytes) -> bool:
    os.lseek(descriptor, 0, os.SEEK_SET)
    offset = 0
    while offset < len(payload):
        chunk = os.read(descriptor, min(1024 * 1024, len(payload) - offset))
        if not chunk or chunk != payload[offset : offset + len(chunk)]:
            return False
        offset += len(chunk)
    return os.read(descriptor, 1) == b""


def _validate_directory_chain(chain: Sequence[tuple[int, str, int]]) -> None:
    for parent_fd, name, child_fd in chain:
        opened = os.fstat(child_fd)
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(named.st_mode)
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise DoubleCheckPersistenceError("immutable artifact parent directory was swapped")


def _unlink_if_identity_matches(
    parent_fd: int,
    name: str,
    expected_identity: tuple[int, int],
) -> bool:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if (
        not stat.S_ISREG(current.st_mode)
        or (current.st_dev, current.st_ino) != expected_identity
    ):
        return False
    os.unlink(name, dir_fd=parent_fd)
    os.fsync(parent_fd)
    return True


def _unlink_published_artifact(artifact: _PublishedArtifact) -> None:
    root, components = _validated_artifact_path(artifact.root, artifact.relative_path)
    directory_fds: list[int] = []
    try:
        root_fd = _open_directory(root)
        directory_fds.append(root_fd)
        parent_fd = root_fd
        for component in components[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            directory_fds.append(child_fd)
            parent_fd = child_fd
        _unlink_if_identity_matches(
            parent_fd,
            components[-1],
            (artifact.device, artifact.inode),
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DoubleCheckPersistenceError("immutable artifact cleanup path is unsafe") from exc
    finally:
        for descriptor in reversed(directory_fds):
            os.close(descriptor)
