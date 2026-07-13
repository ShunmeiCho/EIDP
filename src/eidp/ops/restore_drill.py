"""Isolated, fail-closed verification of finalized EIDP backup packages."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import socket
import sqlite3
import stat
import subprocess
import sys
import time
import unicodedata
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPConnection
from pathlib import Path, PurePath
from typing import Protocol
from urllib.parse import quote

from eidp.ops.deployment_manifest import DeploymentManifestError, verify_checkout_matches_deployment
from eidp.ops.receipt_id import require_receipt_id

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_EXPECTATION_KEYS = {
    "schema",
    "export_id",
    "workbook_sha256",
    "export_manifest_sha256",
    "action_ids",
}
_MAX_EXPECTATION_BYTES = 1024 * 1024
_MAX_JSON_BYTES = 1024 * 1024
_MAX_AUDIT_JSONL_LINE_BYTES = 1024 * 1024
_COMMIT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SCHEMA_HEAD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_]{0,127}")
_BACKUP_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}")
_UTC_EVIDENCE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
_DEPLOYMENT_KEYS = {
    "deployed_commit",
    "expected_deployment_commit",
    "origin_main_commit",
    "uv_lock_sha256",
    "schema_head",
    "deployed_at_utc",
    "operator",
    "internal_base_url",
    "port",
    "base_url_path",
    "pre_upgrade_backup_id",
    "off_host_receipt_id",
}
_REPORT_KEYS = {
    "schema",
    "backup_id",
    "restored_path",
    "deployment_commit",
    "schema_head",
    "sqlite_integrity",
    "health_ok",
    "package_manifest_sha256",
    "off_host_receipt_id",
    "verified_at_utc",
    "acceptance_evidence",
}
_EXPORT_MANIFEST_KEYS = {
    "schema",
    "export_id",
    "lifecycle",
    "workbook_filename",
    "workbook_sha256",
}
_BACKUP_MANIFEST_KEYS = {
    "schema",
    "backup_id",
    "deployment_commit",
    "schema_head",
    "source_database_relative_path",
    "actor",
    "created_at_utc",
    "wal_checkpoint_succeeded",
    "wal_checkpoint_succeeded_at_utc",
    "sqlite_snapshot_sha256",
    "deployment_manifest_sha256",
    "optional_roots",
    "inventory",
}
_BACKUP_MANIFEST_NAME = "backup-manifest.v1.json"
_FINALIZED_NAME = "FINALIZED"
_REQUIRED_PACKAGE_ARTIFACTS = {
    "data/eidp.sqlite3",
    "data/master.xlsx",
    "run/deployment-manifest.json",
}
_OPTIONAL_PACKAGE_ROOTS = {
    "data/audit",
    "data/source-pdfs",
    "data/web-intake",
    "output/exports",
}
_MAX_BACKUP_MANIFEST_BYTES = 16 * 1024 * 1024
_AT_FDCWD = -2
_RENAME_NOREPLACE = 1
_RENAME_EXCL = 0x00000004


class RestoreDrillError(RuntimeError):
    """A restore drill could not be proven safe and complete."""


@dataclass(frozen=True)
class RestoreDrillResult:
    backup_id: str
    restored_path: Path
    deployment_commit: str
    schema_head: str
    sqlite_integrity: str
    health_ok: bool
    package_manifest_sha256: str
    off_host_receipt_id: str | None
    report_path: Path


@dataclass(frozen=True)
class RestoreEvidenceExpectation:
    export_id: str
    workbook_sha256: str
    export_manifest_sha256: str
    action_ids: tuple[str, ...]


@dataclass(frozen=True)
class _DeploymentEvidence:
    deployed_commit: str
    uv_lock_sha256: str
    schema_head: str
    live_port: int


@dataclass(frozen=True)
class _VerifiedPackageEvidence:
    backup_id: str
    manifest_sha256: str


class _SmokeProcess(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def wait(self, timeout: float) -> int: ...


def _absolute_root(app_root: Path) -> Path:
    root = Path(os.path.abspath(app_root))
    try:
        root_stat = os.lstat(root)
    except OSError as exc:
        raise RestoreDrillError(f"restore app root is unavailable: {exc}") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise RestoreDrillError("restore app root must be a real directory, not a symlink")
    return root


def _project_relative(raw_path: Path, *, app_root: Path, label: str) -> tuple[Path, Path]:
    if ".." in raw_path.parts:
        raise RestoreDrillError(f"{label} path traversal is not allowed")
    candidate = raw_path if raw_path.is_absolute() else app_root / raw_path
    absolute = Path(os.path.abspath(candidate))
    try:
        relative = absolute.relative_to(app_root)
    except ValueError as exc:
        raise RestoreDrillError(f"{label} path must remain inside the project root") from exc
    return absolute, relative


def _open_directory(app_root: Path, relative: Path) -> int:
    try:
        descriptor = os.open(app_root, _DIRECTORY_FLAGS | _NOFOLLOW)
    except OSError as exc:
        raise RestoreDrillError(f"unsafe restore app root: {exc}") from exc
    try:
        for component in relative.parts:
            next_descriptor = os.open(
                component,
                _DIRECTORY_FLAGS | _NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except OSError as exc:
        os.close(descriptor)
        raise RestoreDrillError(f"unsafe restore path or symlink: {relative}: {exc}") from exc


def _read_project_regular(
    *,
    app_root: Path,
    relative: Path,
    maximum: int,
    label: str,
) -> bytes:
    if not relative.parts:
        raise RestoreDrillError(f"{label} must be a project-local regular file")
    parent = Path(*relative.parts[:-1])
    directory_fd = _open_directory(app_root, parent)
    descriptor = -1
    try:
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise RestoreDrillError(f"{label} must be a real regular file")
        if file_stat.st_size > maximum:
            raise RestoreDrillError(f"{label} exceeds the bounded size limit")
        body = bytearray()
        while chunk := os.read(descriptor, min(64 * 1024, maximum + 1 - len(body))):
            body.extend(chunk)
            if len(body) > maximum:
                raise RestoreDrillError(f"{label} exceeds the bounded size limit")
        return bytes(body)
    except RestoreDrillError:
        raise
    except OSError as exc:
        raise RestoreDrillError(f"unsafe or missing {label}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(directory_fd)


def _canonical_uuid(value: object, *, label: str, require_version_four: bool) -> str:
    if not isinstance(value, str):
        raise RestoreDrillError(f"{label} must be a canonical UUID")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise RestoreDrillError(f"{label} must be a canonical UUID") from exc
    if str(parsed) != value or (require_version_four and parsed.version != 4):
        raise RestoreDrillError(f"{label} must be a canonical lowercase UUID4")
    return value


def load_restore_evidence_expectation(
    *,
    app_root: Path,
    path: Path,
) -> RestoreEvidenceExpectation:
    """Read one exact, project-local acceptance expectation projection."""

    root = _absolute_root(app_root)
    _absolute, relative = _project_relative(path, app_root=root, label="restore expectation")
    if len(relative.parts) != 4 or relative.parts[:3] != ("evidence", "runtime", "exports"):
        raise RestoreDrillError("restore expectation path must be evidence/runtime/exports/{export_id}.json")
    body = _read_project_regular(
        app_root=root,
        relative=relative,
        maximum=_MAX_EXPECTATION_BYTES,
        label="restore expectation",
    )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RestoreDrillError("restore expectation must contain valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _EXPECTATION_KEYS:
        raise RestoreDrillError("restore expectation JSON must have the exact schema keys")
    if payload.get("schema") != "eidp.restore-evidence-expectation.v1":
        raise RestoreDrillError("restore expectation schema is invalid")

    export_id = _canonical_uuid(payload.get("export_id"), label="expectation export ID", require_version_four=True)
    if relative.name != f"{export_id}.json":
        raise RestoreDrillError("restore expectation filename must match its export ID")
    workbook_sha256 = payload.get("workbook_sha256")
    export_manifest_sha256 = payload.get("export_manifest_sha256")
    if not isinstance(workbook_sha256, str) or _SHA256_PATTERN.fullmatch(workbook_sha256) is None:
        raise RestoreDrillError("restore expectation workbook SHA-256 is invalid")
    if not isinstance(export_manifest_sha256, str) or _SHA256_PATTERN.fullmatch(export_manifest_sha256) is None:
        raise RestoreDrillError("restore expectation manifest SHA-256 is invalid")
    raw_action_ids = payload.get("action_ids")
    if not isinstance(raw_action_ids, list) or not raw_action_ids:
        raise RestoreDrillError("restore expectation action IDs must be a non-empty list")
    action_ids = tuple(
        _canonical_uuid(value, label="expectation action ID", require_version_four=False)
        for value in raw_action_ids
    )
    if action_ids != tuple(sorted(action_ids)) or len(action_ids) != len(set(action_ids)):
        raise RestoreDrillError("restore expectation action IDs must be sorted and unique")
    return _validated_expectation(
        RestoreEvidenceExpectation(
            export_id=export_id,
            workbook_sha256=workbook_sha256,
            export_manifest_sha256=export_manifest_sha256,
            action_ids=action_ids,
        )
    )


def _validated_expectation(expectation: RestoreEvidenceExpectation) -> RestoreEvidenceExpectation:
    export_id = _canonical_uuid(
        expectation.export_id,
        label="expectation export ID",
        require_version_four=True,
    )
    if _SHA256_PATTERN.fullmatch(expectation.workbook_sha256) is None:
        raise RestoreDrillError("restore expectation workbook SHA-256 is invalid")
    if _SHA256_PATTERN.fullmatch(expectation.export_manifest_sha256) is None:
        raise RestoreDrillError("restore expectation manifest SHA-256 is invalid")
    if not isinstance(expectation.action_ids, tuple) or not expectation.action_ids:
        raise RestoreDrillError("restore expectation action IDs must be a non-empty tuple")
    action_ids = tuple(
        _canonical_uuid(value, label="expectation action ID", require_version_four=False)
        for value in expectation.action_ids
    )
    if action_ids != tuple(sorted(action_ids)) or len(action_ids) != len(set(action_ids)):
        raise RestoreDrillError("restore expectation action IDs must be sorted and unique")
    return RestoreEvidenceExpectation(
        export_id=export_id,
        workbook_sha256=expectation.workbook_sha256,
        export_manifest_sha256=expectation.export_manifest_sha256,
        action_ids=action_ids,
    )


def _validate_restore_layout(
    *,
    app_root: Path,
    package_path: Path,
    target_path: Path,
) -> tuple[Path, Path]:
    package, package_relative = _project_relative(package_path, app_root=app_root, label="restore package")
    target, target_relative = _project_relative(target_path, app_root=app_root, label="restore target")
    package_parts = package_relative.parts
    if not (
        (len(package_parts) == 2 and package_parts[0] == "backups")
        or (len(package_parts) == 3 and package_parts[:2] == ("restore-drills", "incoming"))
    ):
        raise RestoreDrillError("restore package must use a direct finalized backups or incoming layout")
    if package.name.startswith("."):
        raise RestoreDrillError("restore package staging paths are not allowed")
    package_fd = _open_directory(app_root, package_relative)
    os.close(package_fd)

    if len(target_relative.parts) != 3 or target_relative.parts[:2] != ("restore-drills", "verified"):
        raise RestoreDrillError("restore target must use the exact isolated verified layout")
    if target.name != package.name:
        raise RestoreDrillError("restore target basename must match the backup package")
    target_parent_fd = _open_directory(app_root, Path("restore-drills/verified"))
    os.close(target_parent_fd)
    if target == package or target in package.parents or package in target.parents:
        raise RestoreDrillError("restore package and target must not overlap")
    try:
        target_stat = os.lstat(target)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise RestoreDrillError(f"restore target path is unsafe: {exc}") from exc
    else:
        if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
            raise RestoreDrillError("existing restore target must be a real directory, not a symlink")
    return package, target


def _relative_components(relative: str, *, label: str) -> tuple[str, ...]:
    parsed = PurePath(relative)
    parts = parsed.parts
    if (
        parsed.is_absolute()
        or not parts
        or parsed.as_posix() != relative
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise RestoreDrillError(f"unsafe relative {label}: {relative!r}")
    return parts


def _open_directory_at(directory_fd: int, relative: str, *, label: str) -> int:
    descriptor = os.dup(directory_fd)
    try:
        for component in _relative_components(relative, label=label):
            next_descriptor = os.open(
                component,
                _DIRECTORY_FLAGS | _NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except RestoreDrillError:
        os.close(descriptor)
        raise
    except OSError as exc:
        os.close(descriptor)
        raise RestoreDrillError(f"unsafe or missing {label}: {exc}") from exc


def _open_regular_at(directory_fd: int, relative: str, *, label: str) -> int:
    parts = _relative_components(relative, label=label)
    parent_fd = os.dup(directory_fd)
    descriptor = -1
    try:
        for component in parts[:-1]:
            next_parent = os.open(
                component,
                _DIRECTORY_FLAGS | _NOFOLLOW,
                dir_fd=parent_fd,
            )
            os.close(parent_fd)
            parent_fd = next_parent
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent_fd,
        )
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RestoreDrillError(f"{label} must be a real regular file")
        return descriptor
    except RestoreDrillError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise RestoreDrillError(f"unsafe or missing {label}: {exc}") from exc
    finally:
        os.close(parent_fd)


def _read_open_regular(descriptor: int, *, maximum: int | None, label: str) -> bytes:
    file_stat = os.fstat(descriptor)
    if not stat.S_ISREG(file_stat.st_mode):
        raise RestoreDrillError(f"{label} must be a real regular file")
    if maximum is not None and file_stat.st_size > maximum:
        raise RestoreDrillError(f"{label} exceeds the bounded size limit")
    body = bytearray()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            body.extend(chunk)
            if maximum is not None and len(body) > maximum:
                raise RestoreDrillError(f"{label} exceeds the bounded size limit")
    except OSError as exc:
        raise RestoreDrillError(f"cannot read {label} safely: {exc}") from exc
    return bytes(body)


def _read_regular_at(directory_fd: int, relative: str, *, maximum: int | None, label: str) -> bytes:
    descriptor = _open_regular_at(directory_fd, relative, label=label)
    try:
        return _read_open_regular(descriptor, maximum=maximum, label=label)
    finally:
        os.close(descriptor)


def _sha256_open_regular(descriptor: int, *, label: str) -> str:
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        raise RestoreDrillError(f"{label} must be a real regular file")
    digest = hashlib.sha256()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    except OSError as exc:
        raise RestoreDrillError(f"cannot hash {label} safely: {exc}") from exc
    return digest.hexdigest()


def _sha256_at(directory_fd: int, relative: str, *, label: str) -> str:
    descriptor = _open_regular_at(directory_fd, relative, label=label)
    try:
        return _sha256_open_regular(descriptor, label=label)
    finally:
        os.close(descriptor)


def _json_at(directory_fd: int, relative: str, *, maximum: int, label: str) -> dict[str, object]:
    try:
        payload = json.loads(
            _read_regular_at(directory_fd, relative, maximum=maximum, label=label).decode("utf-8")
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RestoreDrillError(f"{label} must contain valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise RestoreDrillError(f"{label} must contain a JSON object")
    return payload


def _iter_bounded_utf8_lines_at(
    directory_fd: int,
    relative: str,
    *,
    maximum_line_bytes: int,
    label: str,
) -> Iterator[str]:
    if maximum_line_bytes <= 0:
        raise RestoreDrillError(f"{label} line limit must be positive")
    descriptor = _open_regular_at(directory_fd, relative, label=label)
    pending = bytearray()
    try:
        while chunk := os.read(descriptor, 64 * 1024):
            pending.extend(chunk)
            while True:
                newline = pending.find(b"\n")
                if newline < 0:
                    break
                line = bytes(pending[:newline])
                del pending[: newline + 1]
                if len(line) > maximum_line_bytes:
                    raise RestoreDrillError(f"{label} line exceeds the bounded 1 MiB limit")
                try:
                    yield line.decode("utf-8")
                except UnicodeError as exc:
                    raise RestoreDrillError(f"{label} line is not UTF-8") from exc
            if len(pending) > maximum_line_bytes:
                raise RestoreDrillError(f"{label} line exceeds the bounded 1 MiB limit")
        if pending:
            try:
                yield bytes(pending).decode("utf-8")
            except UnicodeError as exc:
                raise RestoreDrillError(f"{label} line is not UTF-8") from exc
    except RestoreDrillError:
        raise
    except OSError as exc:
        raise RestoreDrillError(f"cannot stream {label} safely: {exc}") from exc
    finally:
        os.close(descriptor)


def _tree_snapshot_fd(
    root_fd: int,
    *,
    ignored_file: str | None = None,
) -> dict[str, tuple[str, int, str]]:
    snapshot: dict[str, tuple[str, int, str]] = {}

    def walk(directory_fd: int, prefix: str) -> None:
        try:
            with os.scandir(directory_fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as exc:
            raise RestoreDrillError(f"restore package tree is unavailable: {exc}") from exc
        for name in names:
            relative = f"{prefix}/{name}" if prefix else name
            if ignored_file is not None and relative == ignored_file:
                continue
            try:
                entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise RestoreDrillError(f"restore package entry changed during verification: {exc}") from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                raise RestoreDrillError(f"restore package tree contains a symlink: {relative}")
            if stat.S_ISDIR(entry_stat.st_mode):
                child_fd = -1
                try:
                    child_fd = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=directory_fd)
                    opened_stat = os.fstat(child_fd)
                    if (opened_stat.st_dev, opened_stat.st_ino) != (entry_stat.st_dev, entry_stat.st_ino):
                        raise RestoreDrillError("restore package directory changed while being opened")
                    snapshot[relative] = ("directory", 0, "")
                    walk(child_fd, relative)
                except RestoreDrillError:
                    raise
                except OSError as exc:
                    raise RestoreDrillError(f"cannot open restore package directory safely: {exc}") from exc
                finally:
                    if child_fd >= 0:
                        os.close(child_fd)
                continue
            if not stat.S_ISREG(entry_stat.st_mode):
                raise RestoreDrillError(f"restore package tree contains a non-file entry: {relative}")
            file_fd = -1
            try:
                file_fd = os.open(
                    name,
                    os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
                opened_stat = os.fstat(file_fd)
                if not stat.S_ISREG(opened_stat.st_mode) or (
                    opened_stat.st_dev,
                    opened_stat.st_ino,
                ) != (entry_stat.st_dev, entry_stat.st_ino):
                    raise RestoreDrillError("restore package file changed while being opened")
                snapshot[relative] = (
                    "file",
                    opened_stat.st_size,
                    _sha256_open_regular(file_fd, label=relative),
                )
            except RestoreDrillError:
                raise
            except OSError as exc:
                raise RestoreDrillError(f"cannot open restore package file safely: {exc}") from exc
            finally:
                if file_fd >= 0:
                    os.close(file_fd)

    walk(root_fd, "")
    return snapshot


def _artifact_is_allowlisted(relative: str) -> bool:
    return relative in _REQUIRED_PACKAGE_ARTIFACTS or any(
        relative.startswith(root + "/") for root in _OPTIONAL_PACKAGE_ROOTS
    )


def _expected_package_directories(inventory_paths: set[str], optional_roots: dict[str, bool]) -> set[str]:
    expected: set[str] = set()
    roots = [PurePath(path).parent for path in inventory_paths]
    roots.extend(PurePath(root) for root, present in optional_roots.items() if present)
    for root in roots:
        current = root
        while current != PurePath("."):
            expected.add(current.as_posix())
            current = current.parent
    return expected


def _required_package_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise RestoreDrillError(f"backup manifest field {key!r} must be a string")
    return value


def _validate_utc_evidence(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _UTC_EVIDENCE_PATTERN.fullmatch(value) is None:
        raise RestoreDrillError(f"{label} must be UTC evidence")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RestoreDrillError(f"{label} must be valid UTC evidence") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RestoreDrillError(f"{label} must be UTC evidence")
    return value


def _validate_package_utc_evidence(value: object, *, label: str) -> str:
    """Match the Task 4 public package verifier's UTC acceptance semantics."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise RestoreDrillError(f"{label} must be UTC evidence")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RestoreDrillError(f"{label} must be valid UTC evidence") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RestoreDrillError(f"{label} must be UTC evidence")
    return value


def _validate_actor_evidence(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or value != value.strip()
        or any(unicodedata.category(character).startswith("C") for character in value)
    ):
        raise RestoreDrillError(f"{label} must be a bounded non-control identity")
    return value


def _verify_backup_package_fd(
    directory_fd: int,
    *,
    expected_backup_id: str,
    expected_manifest_sha256: str | None = None,
    ignored_file: str | None = None,
) -> _VerifiedPackageEvidence:
    if _BACKUP_ID_PATTERN.fullmatch(expected_backup_id) is None or expected_backup_id in {
        ".staging",
        "pre-upgrade",
    }:
        raise RestoreDrillError("expected backup ID is invalid")
    if expected_manifest_sha256 is not None and _SHA256_PATTERN.fullmatch(expected_manifest_sha256) is None:
        raise RestoreDrillError("expected backup manifest SHA-256 is invalid")
    if ignored_file not in {None, "restore-report.v1.json"}:
        raise RestoreDrillError("unsupported ignored backup verification file")
    manifest_bytes = _read_regular_at(
        directory_fd,
        _BACKUP_MANIFEST_NAME,
        maximum=_MAX_BACKUP_MANIFEST_BYTES,
        label="backup manifest",
    )
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_manifest_sha256 is not None and not hmac.compare_digest(
        manifest_sha256,
        expected_manifest_sha256,
    ):
        raise RestoreDrillError("restore package manifest changed during materialization")
    marker = _read_regular_at(
        directory_fd,
        _FINALIZED_NAME,
        maximum=65,
        label="backup finalized package marker",
    )
    if marker != (manifest_sha256 + "\n").encode("ascii"):
        raise RestoreDrillError("restore package FINALIZED marker does not match its manifest")
    try:
        payload = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RestoreDrillError("backup manifest must contain valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _BACKUP_MANIFEST_KEYS:
        raise RestoreDrillError("backup manifest has missing or extra fields")
    if payload.get("schema") != "eidp.backup-manifest.v1":
        raise RestoreDrillError("backup manifest schema is invalid")
    backup_id = _required_package_string(payload, "backup_id")
    if (
        _BACKUP_ID_PATTERN.fullmatch(backup_id) is None
        or backup_id in {".staging", "pre-upgrade"}
        or backup_id != expected_backup_id
    ):
        raise RestoreDrillError("backup manifest identity does not match the package")
    deployment_commit = _required_package_string(payload, "deployment_commit")
    if _COMMIT_PATTERN.fullmatch(deployment_commit) is None:
        raise RestoreDrillError("backup manifest deployment commit is invalid")
    schema_head = _required_package_string(payload, "schema_head")
    if _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise RestoreDrillError("backup manifest schema head is invalid")
    if payload.get("source_database_relative_path") != "data/eidp.sqlite3":
        raise RestoreDrillError("backup manifest source database path is unsafe")
    _validate_actor_evidence(payload.get("actor"), label="backup actor")
    _validate_package_utc_evidence(payload.get("created_at_utc"), label="backup creation time")
    if payload.get("wal_checkpoint_succeeded") is not True:
        raise RestoreDrillError("backup manifest does not prove a successful WAL checkpoint")
    _validate_package_utc_evidence(
        payload.get("wal_checkpoint_succeeded_at_utc"),
        label="backup checkpoint time",
    )
    snapshot_digest = _required_package_string(payload, "sqlite_snapshot_sha256")
    deployment_digest = _required_package_string(payload, "deployment_manifest_sha256")
    if _SHA256_PATTERN.fullmatch(snapshot_digest) is None or _SHA256_PATTERN.fullmatch(deployment_digest) is None:
        raise RestoreDrillError("backup manifest digest field is invalid")

    raw_inventory = payload.get("inventory")
    if not isinstance(raw_inventory, list):
        raise RestoreDrillError("backup manifest inventory is invalid")
    inventory: dict[str, tuple[int, str]] = {}
    ordered_paths: list[str] = []
    for raw_entry in raw_inventory:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"path", "size", "sha256"}:
            raise RestoreDrillError("backup manifest inventory entry is invalid")
        relative = raw_entry.get("path")
        size = raw_entry.get("size")
        digest = raw_entry.get("sha256")
        if not isinstance(relative, str) or not _artifact_is_allowlisted(relative):
            raise RestoreDrillError("backup manifest inventory path is invalid")
        _relative_components(relative, label="backup inventory path")
        if type(size) is not int or size < 0:
            raise RestoreDrillError("backup manifest inventory size is invalid")
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise RestoreDrillError("backup manifest inventory digest is invalid")
        ordered_paths.append(relative)
        inventory[relative] = (size, digest)
    if ordered_paths != sorted(ordered_paths) or len(ordered_paths) != len(inventory):
        raise RestoreDrillError("backup manifest inventory must be sorted and unique")
    if not _REQUIRED_PACKAGE_ARTIFACTS.issubset(inventory):
        raise RestoreDrillError("backup manifest inventory is missing a required artifact")
    if inventory["data/eidp.sqlite3"][1] != snapshot_digest:
        raise RestoreDrillError("backup SQLite snapshot digest binding is invalid")
    if inventory["run/deployment-manifest.json"][1] != deployment_digest:
        raise RestoreDrillError("backup deployment manifest digest binding is invalid")

    raw_optional = payload.get("optional_roots")
    if not isinstance(raw_optional, dict) or set(raw_optional) != _OPTIONAL_PACKAGE_ROOTS:
        raise RestoreDrillError("backup optional-root evidence is invalid")
    optional_roots: dict[str, bool] = {}
    for root in sorted(_OPTIONAL_PACKAGE_ROOTS):
        present = raw_optional.get(root)
        if type(present) is not bool:
            raise RestoreDrillError("backup optional-root evidence must be boolean")
        optional_roots[root] = present

    snapshot = _tree_snapshot_fd(directory_fd, ignored_file=ignored_file)
    actual_files = {
        relative: (size, digest)
        for relative, (kind, size, digest) in snapshot.items()
        if kind == "file"
    }
    actual_directories = {relative for relative, (kind, _size, _digest) in snapshot.items() if kind == "directory"}
    expected_files = set(inventory) | {_BACKUP_MANIFEST_NAME, _FINALIZED_NAME}
    if set(actual_files) != expected_files:
        raise RestoreDrillError("restore package has missing or extra files")
    expected_control_files = {
        _BACKUP_MANIFEST_NAME: (len(manifest_bytes), manifest_sha256),
        _FINALIZED_NAME: (len(marker), hashlib.sha256(marker).hexdigest()),
    }
    for relative, expected in expected_control_files.items():
        if actual_files[relative] != expected:
            raise RestoreDrillError(f"restore package control file changed during verification: {relative}")
    actual_optional_roots = {root: root in actual_directories for root in _OPTIONAL_PACKAGE_ROOTS}
    if actual_optional_roots != optional_roots:
        raise RestoreDrillError("backup optional-root presence does not match the package tree")
    if actual_directories != _expected_package_directories(set(inventory), optional_roots):
        raise RestoreDrillError("restore package has missing or extra directories")
    for relative, expected in inventory.items():
        if actual_files[relative] != expected:
            raise RestoreDrillError(f"restore package artifact digest or size mismatch: {relative}")

    deployment = _deployment_evidence_fd(directory_fd)
    if deployment.deployed_commit != deployment_commit or deployment.schema_head != schema_head:
        raise RestoreDrillError("backup deployment manifest binding is invalid")
    _integrity, sqlite_schema_head = _sqlite_evidence_fd(directory_fd, expected_schema_head=schema_head)
    if sqlite_schema_head != schema_head:
        raise RestoreDrillError("backup SQLite schema does not match deployment evidence")
    if _tree_snapshot_fd(directory_fd, ignored_file=ignored_file) != snapshot:
        raise RestoreDrillError("backup package changed during read-only verification")
    return _VerifiedPackageEvidence(backup_id=backup_id, manifest_sha256=manifest_sha256)


def _parse_deployment_evidence(payload: dict[str, object]) -> _DeploymentEvidence:
    if set(payload) != _DEPLOYMENT_KEYS:
        raise RestoreDrillError("packaged deployment manifest has missing or extra fields")
    deployed_commit = payload.get("deployed_commit")
    uv_lock_sha256 = payload.get("uv_lock_sha256")
    schema_head = payload.get("schema_head")
    live_port = payload.get("port")
    if not isinstance(deployed_commit, str) or _COMMIT_PATTERN.fullmatch(deployed_commit) is None:
        raise RestoreDrillError("packaged deployment commit is invalid")
    for key in ("expected_deployment_commit", "origin_main_commit"):
        commit = payload.get(key)
        if not isinstance(commit, str) or _COMMIT_PATTERN.fullmatch(commit) is None:
            raise RestoreDrillError(f"packaged deployment field {key!r} is invalid")
    if not isinstance(uv_lock_sha256, str) or _SHA256_PATTERN.fullmatch(uv_lock_sha256) is None:
        raise RestoreDrillError("packaged deployment uv.lock SHA-256 is invalid")
    if not isinstance(schema_head, str) or _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise RestoreDrillError("packaged deployment schema head is invalid")
    if type(live_port) is not int:
        raise RestoreDrillError("packaged deployment live port is invalid")
    _validate_package_utc_evidence(payload.get("deployed_at_utc"), label="deployment time")
    _validate_actor_evidence(payload.get("operator"), label="deployment operator")
    for key in ("internal_base_url", "base_url_path"):
        if not isinstance(payload.get(key), str):
            raise RestoreDrillError(f"packaged deployment field {key!r} must be a string")
    for key in ("pre_upgrade_backup_id", "off_host_receipt_id"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise RestoreDrillError(f"packaged deployment field {key!r} must be a string or null")
    return _DeploymentEvidence(deployed_commit, uv_lock_sha256, schema_head, live_port)


def _deployment_evidence_fd(directory_fd: int) -> _DeploymentEvidence:
    return _parse_deployment_evidence(
        _json_at(
            directory_fd,
            "run/deployment-manifest.json",
            maximum=_MAX_JSON_BYTES,
            label="packaged deployment manifest",
        )
    )


def _verify_checkout(*, app_root: Path, deployment: _DeploymentEvidence) -> None:
    try:
        verify_checkout_matches_deployment(
            app_root=app_root,
            deployed_commit=deployment.deployed_commit,
            uv_lock_sha256=deployment.uv_lock_sha256,
        )
    except DeploymentManifestError as exc:
        raise RestoreDrillError(f"restore checkout does not match deployment evidence: {exc}") from exc


def _copy_package_tree(
    source: Path,
    destination: Path,
    *,
    pinned_source_fd: int | None = None,
    pinned_destination_parent_fd: int | None = None,
) -> None:
    source_root_fd = -1
    destination_parent_fd = -1
    destination_root_fd = -1
    try:
        source_root_fd = (
            os.dup(pinned_source_fd)
            if pinned_source_fd is not None
            else os.open(source, _DIRECTORY_FLAGS | _NOFOLLOW)
        )
        destination_parent_fd = (
            os.dup(pinned_destination_parent_fd)
            if pinned_destination_parent_fd is not None
            else os.open(destination.parent, _DIRECTORY_FLAGS | _NOFOLLOW)
        )
        os.mkdir(destination.name, mode=0o700, dir_fd=destination_parent_fd)
        destination_root_fd = os.open(
            destination.name,
            _DIRECTORY_FLAGS | _NOFOLLOW,
            dir_fd=destination_parent_fd,
        )
    except OSError as exc:
        if destination_root_fd >= 0:
            os.close(destination_root_fd)
        if destination_parent_fd >= 0:
            os.close(destination_parent_fd)
        if source_root_fd >= 0:
            os.close(source_root_fd)
        raise RestoreDrillError(f"cannot create exclusive restore package staging root: {exc}") from exc

    def copy_directory(source_directory_fd: int, destination_directory_fd: int, relative_prefix: str) -> None:
        try:
            with os.scandir(source_directory_fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as exc:
            raise RestoreDrillError(f"cannot enumerate restore package during copy: {exc}") from exc
        for name in names:
            relative = f"{relative_prefix}/{name}" if relative_prefix else name
            try:
                entry_stat = os.stat(name, dir_fd=source_directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise RestoreDrillError(f"restore package entry changed during copy: {exc}") from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                raise RestoreDrillError(f"restore package changed to a symlink during copy: {name}")
            if stat.S_ISDIR(entry_stat.st_mode):
                source_child_fd = -1
                destination_child_fd = -1
                try:
                    source_child_fd = os.open(
                        name,
                        _DIRECTORY_FLAGS | _NOFOLLOW,
                        dir_fd=source_directory_fd,
                    )
                    pinned_stat = os.fstat(source_child_fd)
                    if (pinned_stat.st_dev, pinned_stat.st_ino) != (entry_stat.st_dev, entry_stat.st_ino):
                        raise RestoreDrillError("restore package directory changed while being pinned for copy")
                    os.mkdir(name, mode=0o700, dir_fd=destination_directory_fd)
                    destination_child_fd = os.open(
                        name,
                        _DIRECTORY_FLAGS | _NOFOLLOW,
                        dir_fd=destination_directory_fd,
                    )
                    copy_directory(source_child_fd, destination_child_fd, relative)
                except RestoreDrillError:
                    raise
                except OSError as exc:
                    raise RestoreDrillError(f"cannot create exclusive restore directory: {exc}") from exc
                finally:
                    if destination_child_fd >= 0:
                        os.close(destination_child_fd)
                    if source_child_fd >= 0:
                        os.close(source_child_fd)
                continue
            if not stat.S_ISREG(entry_stat.st_mode):
                raise RestoreDrillError("restore package contains a non-regular copy source")
            source_fd = -1
            destination_fd = -1
            try:
                source_fd = os.open(
                    name,
                    os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=source_directory_fd,
                )
                pinned_stat = os.fstat(source_fd)
                if not stat.S_ISREG(pinned_stat.st_mode):
                    raise RestoreDrillError("restore package copy source is not a real regular file")
                if (pinned_stat.st_dev, pinned_stat.st_ino) != (entry_stat.st_dev, entry_stat.st_ino):
                    raise RestoreDrillError("restore package file changed while being pinned for copy")
                destination_mode = 0o400 if relative == "data/master.xlsx" else 0o600
                destination_fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    destination_mode,
                    dir_fd=destination_directory_fd,
                )
                while chunk := os.read(source_fd, 1024 * 1024):
                    offset = 0
                    while offset < len(chunk):
                        offset += os.write(destination_fd, chunk[offset:])
                os.fchmod(destination_fd, destination_mode)
                os.fsync(destination_fd)
            except RestoreDrillError:
                raise
            except OSError as exc:
                raise RestoreDrillError(f"restore package exclusive copy failed: {exc}") from exc
            finally:
                if destination_fd >= 0:
                    os.close(destination_fd)
                if source_fd >= 0:
                    os.close(source_fd)

    try:
        copy_directory(source_root_fd, destination_root_fd, "")
    finally:
        if destination_root_fd >= 0:
            os.close(destination_root_fd)
        if destination_parent_fd >= 0:
            os.close(destination_parent_fd)
        if source_root_fd >= 0:
            os.close(source_root_fd)


def _sqlite_uri_for_descriptor(descriptor: int) -> str:
    if sys.platform == "darwin":
        descriptor_path = f"/dev/fd/{descriptor}"
    elif sys.platform == "linux":
        descriptor_path = f"/proc/self/fd/{descriptor}"
    else:
        raise RestoreDrillError("descriptor-backed SQLite verification is unsupported on this platform")
    return f"file:{quote(descriptor_path, safe='/')}?mode=ro&immutable=1"


def _sqlite_evidence_fd(directory_fd: int, *, expected_schema_head: str) -> tuple[str, str]:
    database_fd = _open_regular_at(directory_fd, "data/eidp.sqlite3", label="restored SQLite database")
    try:
        try:
            with sqlite3.connect(_sqlite_uri_for_descriptor(database_fd), uri=True) as connection:
                connection.execute("PRAGMA query_only=ON")
                integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
                schema_rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        except sqlite3.Error as exc:
            raise RestoreDrillError(f"restored SQLite verification failed: {exc}") from exc
    finally:
        os.close(database_fd)
    if integrity_rows != [("ok",)]:
        raise RestoreDrillError("restored SQLite integrity_check did not return exactly ok")
    if len(schema_rows) != 1 or not isinstance(schema_rows[0][0], str):
        raise RestoreDrillError("restored SQLite must contain exactly one Alembic schema head")
    schema_head = schema_rows[0][0]
    if schema_head != expected_schema_head:
        raise RestoreDrillError("restored SQLite schema does not match packaged deployment evidence")
    return "ok", schema_head


def _safe_workbook_name(value: object) -> str:
    if not isinstance(value, str) or not value or PurePath(value).name != value or value in {".", ".."}:
        raise RestoreDrillError("restored export workbook filename is not a safe leaf")
    return value


def _verify_acceptance_fd(
    restored_fd: int,
    expectation: RestoreEvidenceExpectation,
) -> dict[str, object]:
    export_fd = _open_directory_at(
        restored_fd,
        f"output/exports/{expectation.export_id}",
        label="restored export bundle",
    )
    try:
        manifest_digest = _sha256_at(export_fd, "export-manifest.v1.json", label="restored export manifest")
        if not hmac.compare_digest(manifest_digest, expectation.export_manifest_sha256):
            raise RestoreDrillError("restored export manifest digest does not match the expectation")
        marker = _read_regular_at(
            export_fd,
            "FINALIZED",
            maximum=65,
            label="restored export FINALIZED marker",
        )
        if marker != (expectation.export_manifest_sha256 + "\n").encode("ascii"):
            raise RestoreDrillError("restored export FINALIZED marker does not match its manifest")
        manifest = _json_at(
            export_fd,
            "export-manifest.v1.json",
            maximum=_MAX_JSON_BYTES,
            label="restored export manifest",
        )
        if set(manifest) != _EXPORT_MANIFEST_KEYS or manifest.get("schema") != "eidp.export-manifest.v1":
            raise RestoreDrillError("restored export manifest schema or fields are invalid")
        if manifest.get("export_id") != expectation.export_id:
            raise RestoreDrillError("restored export manifest ID does not match the expectation")
        if manifest.get("lifecycle") != "finalized":
            raise RestoreDrillError("restored export lifecycle is not finalized")
        workbook_name = _safe_workbook_name(manifest.get("workbook_filename"))
        if manifest.get("workbook_sha256") != expectation.workbook_sha256:
            raise RestoreDrillError("restored export manifest workbook SHA-256 does not match")
        try:
            with os.scandir(export_fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as exc:
            raise RestoreDrillError(f"restored export bundle is unavailable: {exc}") from exc
        expected_names = sorted((workbook_name, "export-manifest.v1.json", "FINALIZED"))
        if names != expected_names:
            raise RestoreDrillError("restored export bundle has missing or extra files")
        for name in names:
            try:
                entry_stat = os.stat(name, dir_fd=export_fd, follow_symlinks=False)
            except OSError as exc:
                raise RestoreDrillError(f"restored export bundle changed during verification: {exc}") from exc
            if not stat.S_ISREG(entry_stat.st_mode):
                raise RestoreDrillError("restored export bundle contains a symlink or non-file entry")
        workbook_digest = _sha256_at(export_fd, workbook_name, label="restored export workbook")
        if not hmac.compare_digest(workbook_digest, expectation.workbook_sha256):
            raise RestoreDrillError("restored export workbook bytes do not match the expectation")
    finally:
        os.close(export_fd)

    database_fd = _open_regular_at(restored_fd, "data/eidp.sqlite3", label="restored action database")
    db_counts: dict[str, int] = {}
    try:
        try:
            with sqlite3.connect(_sqlite_uri_for_descriptor(database_fd), uri=True) as connection:
                connection.execute("PRAGMA query_only=ON")
                for action_id in expectation.action_ids:
                    rows = connection.execute(
                        """
                        SELECT jsonl_exported_at, jsonl_export_error
                        FROM manual_action_log
                        WHERE action_id = ?
                        """,
                        (action_id,),
                    ).fetchall()
                    db_counts[action_id] = len(rows)
                    if len(rows) != 1:
                        raise RestoreDrillError("each expected database action must occur exactly one time")
                    exported_at, export_error = rows[0]
                    if not isinstance(exported_at, str) or not exported_at or export_error is not None:
                        raise RestoreDrillError("expected database action is pending or has an export error")
        except RestoreDrillError:
            raise
        except sqlite3.Error as exc:
            raise RestoreDrillError(f"restored action database evidence is invalid: {exc}") from exc
    finally:
        os.close(database_fd)

    audit_fd = _open_directory_at(restored_fd, "data/audit", label="restored audit projection directory")
    projection_counts = {action_id: 0 for action_id in expectation.action_ids}
    try:
        try:
            with os.scandir(audit_fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as exc:
            raise RestoreDrillError(f"restored audit projection directory is unavailable: {exc}") from exc
        matched_names = [
            name for name in names if name.startswith("manual-actions") and name.endswith(".jsonl")
        ]
        if not matched_names:
            raise RestoreDrillError("restored audit JSONL projection is missing")
        for name in matched_names:
            for line in _iter_bounded_utf8_lines_at(
                audit_fd,
                name,
                maximum_line_bytes=_MAX_AUDIT_JSONL_LINE_BYTES,
                label="restored audit JSONL projection",
            ):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RestoreDrillError("restored audit JSONL projection is malformed") from exc
                if not isinstance(record, dict):
                    raise RestoreDrillError("restored audit JSONL projection rows must be JSON objects")
                projected_action_id = record.get("action_id")
                if isinstance(projected_action_id, str) and projected_action_id in projection_counts:
                    projection_counts[projected_action_id] += 1
    finally:
        os.close(audit_fd)
    if any(count != 1 for count in projection_counts.values()):
        raise RestoreDrillError("each expected action needs exactly one restored audit JSONL projection")
    return {
        "export_id": expectation.export_id,
        "workbook_sha256": expectation.workbook_sha256,
        "export_manifest_sha256": expectation.export_manifest_sha256,
        "action_ids": list(expectation.action_ids),
        "db_action_counts": db_counts,
        "audit_projection_counts": projection_counts,
    }


def _write_restore_report(
    path: Path,
    payload: dict[str, object],
    *,
    directory_fd: int | None = None,
) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    descriptor = -1
    try:
        descriptor = os.open(
            path.name if directory_fd is not None else path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    except OSError as exc:
        raise RestoreDrillError(f"cannot write restore report safely: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _fsync_tree_fd(root_fd: int) -> None:
    def fsync_directory(directory_fd: int) -> None:
        try:
            with os.scandir(directory_fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as exc:
            raise RestoreDrillError(f"cannot enumerate restore tree for fsync: {exc}") from exc
        for name in names:
            try:
                entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise RestoreDrillError(f"restore tree changed before fsync: {exc}") from exc
            descriptor = -1
            try:
                if stat.S_ISDIR(entry_stat.st_mode):
                    descriptor = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=directory_fd)
                    opened_stat = os.fstat(descriptor)
                    if (opened_stat.st_dev, opened_stat.st_ino) != (entry_stat.st_dev, entry_stat.st_ino):
                        raise RestoreDrillError("restore directory changed while being opened for fsync")
                    fsync_directory(descriptor)
                elif stat.S_ISREG(entry_stat.st_mode):
                    descriptor = os.open(
                        name,
                        os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=directory_fd,
                    )
                    opened_stat = os.fstat(descriptor)
                    if not stat.S_ISREG(opened_stat.st_mode) or (
                        opened_stat.st_dev,
                        opened_stat.st_ino,
                    ) != (entry_stat.st_dev, entry_stat.st_ino):
                        raise RestoreDrillError("restore file changed while being opened for fsync")
                    os.fsync(descriptor)
                else:
                    raise RestoreDrillError("restore tree contains a symlink or non-file entry before fsync")
            except RestoreDrillError:
                raise
            except OSError as exc:
                raise RestoreDrillError(f"cannot fsync restore tree safely: {exc}") from exc
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        try:
            os.fsync(directory_fd)
        except OSError as exc:
            raise RestoreDrillError(f"cannot fsync restore directory safely: {exc}") from exc

    fsync_directory(root_fd)


def _remove_owned_tree(path: Path, *, device: int, inode: int) -> None:
    parent_fd = -1
    try:
        parent_fd = os.open(path.parent, _DIRECTORY_FLAGS | _NOFOLLOW)
        _remove_owned_tree_at(parent_fd, path.name, device=device, inode=inode)
    except RestoreDrillError:
        raise
    except OSError as exc:
        raise RestoreDrillError(f"cannot clean up owned restore work safely: {exc}") from exc
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)


def _remove_owned_tree_at(parent_fd: int, name: str, *, device: int, inode: int) -> None:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(current.st_mode) or not stat.S_ISDIR(current.st_mode):
        raise RestoreDrillError("owned restore work path changed identity before cleanup")
    if (current.st_dev, current.st_ino) != (device, inode):
        raise RestoreDrillError("owned restore work path was replaced before cleanup")
    try:
        shutil.rmtree(name, dir_fd=parent_fd)
    except OSError as exc:
        raise RestoreDrillError(f"cannot clean up owned restore work safely: {exc}") from exc


def _require_pinned_directory(path: Path, pinned_stat: os.stat_result, *, label: str) -> None:
    try:
        current = os.lstat(path)
    except OSError as exc:
        raise RestoreDrillError(f"{label} path changed after it was pinned: {exc}") from exc
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != (pinned_stat.st_dev, pinned_stat.st_ino)
    ):
        raise RestoreDrillError(f"{label} path was replaced after it was pinned")


def _require_directory_entry_identity(
    parent_fd: int,
    name: str,
    *,
    expected_identity: tuple[int, int],
    label: str,
) -> None:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise RestoreDrillError(f"{label} changed before verified return: {exc}") from exc
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != expected_identity
    ):
        raise RestoreDrillError(f"{label} was replaced before verified return")


def _publish_restore_noreplace(
    source: Path,
    target: Path,
    *,
    source_dir_fd: int | None = None,
    target_dir_fd: int | None = None,
) -> None:
    """Atomically publish a directory without ever replacing an existing target."""

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source.name if source_dir_fd is not None else source)
    target_bytes = os.fsencode(target.name if target_dir_fd is not None else target)
    source_base_fd = source_dir_fd if source_dir_fd is not None else _AT_FDCWD
    target_base_fd = target_dir_fd if target_dir_fd is not None else _AT_FDCWD
    if sys.platform == "linux":
        try:
            rename = libc.renameat2
        except AttributeError as exc:
            raise RestoreDrillError("atomic no-replace restore publication is unavailable") from exc
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(source_base_fd, source_bytes, target_base_fd, target_bytes, _RENAME_NOREPLACE)
    elif sys.platform == "darwin":
        try:
            rename = libc.renameatx_np
        except AttributeError as exc:
            raise RestoreDrillError("atomic exclusive restore publication is unavailable") from exc
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(source_base_fd, source_bytes, target_base_fd, target_bytes, _RENAME_EXCL)
    else:
        raise RestoreDrillError("atomic no-replace restore publication is unsupported on this platform")
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise RestoreDrillError("restore target appeared concurrently and was preserved unchanged")
    raise RestoreDrillError(f"atomic no-replace restore publication failed: {os.strerror(error_number)}")


def _result_from_report(
    *,
    target: Path,
    report_path: Path,
    report: dict[str, object],
) -> RestoreDrillResult:
    return RestoreDrillResult(
        backup_id=str(report["backup_id"]),
        restored_path=target,
        deployment_commit=str(report["deployment_commit"]),
        schema_head=str(report["schema_head"]),
        sqlite_integrity=str(report["sqlite_integrity"]),
        health_ok=report["health_ok"] is True,
        package_manifest_sha256=str(report["package_manifest_sha256"]),
        off_host_receipt_id=report["off_host_receipt_id"] if isinstance(report["off_host_receipt_id"], str) else None,
        report_path=report_path,
    )


def _validate_existing_target(
    *,
    app_root: Path,
    package_fd: int,
    target: Path,
    target_fd: int,
    verified_parent_fd: int,
    backup_id: str,
    package_manifest_sha256: str,
    deployment: _DeploymentEvidence,
    off_host_receipt_id: str | None,
    expected_evidence: RestoreEvidenceExpectation | None,
) -> RestoreDrillResult:
    _verify_backup_package_fd(
        target_fd,
        expected_backup_id=backup_id,
        expected_manifest_sha256=package_manifest_sha256,
        ignored_file="restore-report.v1.json",
    )
    source_snapshot = _tree_snapshot_fd(package_fd)
    target_snapshot = _tree_snapshot_fd(target_fd, ignored_file="restore-report.v1.json")
    if source_snapshot != target_snapshot:
        raise RestoreDrillError("existing restore target conflicts with the verified package or has extra content")
    report_path = target / "restore-report.v1.json"
    report = _json_at(
        target_fd,
        "restore-report.v1.json",
        maximum=_MAX_JSON_BYTES,
        label="existing restore report",
    )
    if set(report) != _REPORT_KEYS:
        raise RestoreDrillError("existing restore report has missing or extra fields")
    acceptance = _verify_acceptance_fd(target_fd, expected_evidence) if expected_evidence is not None else None
    integrity, schema_head = _sqlite_evidence_fd(target_fd, expected_schema_head=deployment.schema_head)
    restored_deployment = _deployment_evidence_fd(target_fd)
    expected_values: dict[str, object] = {
        "schema": "eidp.restore-report.v1",
        "backup_id": backup_id,
        "restored_path": target.relative_to(app_root).as_posix(),
        "deployment_commit": deployment.deployed_commit,
        "schema_head": schema_head,
        "sqlite_integrity": integrity,
        "health_ok": True,
        "package_manifest_sha256": package_manifest_sha256,
        "off_host_receipt_id": off_host_receipt_id,
        "acceptance_evidence": acceptance,
    }
    if restored_deployment != deployment or any(report.get(key) != value for key, value in expected_values.items()):
        raise RestoreDrillError("existing restore report conflicts with current verified evidence")
    _validate_utc_evidence(
        report.get("verified_at_utc"),
        label="existing restore report verification time",
    )
    _verify_checkout(app_root=app_root, deployment=deployment)
    _fsync_tree_fd(target_fd)
    os.fsync(verified_parent_fd)
    return _result_from_report(target=target, report_path=report_path, report=report)


def _sealed_smoke_environment(*, restored_root: Path) -> dict[str, str]:
    runtime_root = restored_root / ".restore-smoke-runtime"
    created = False
    try:
        runtime_root.mkdir(mode=0o700)
        created = True
        home = runtime_root / "home"
        temporary = runtime_root / "tmp"
        cache = runtime_root / "cache"
        for directory in (home, temporary, cache):
            directory.mkdir(mode=0o700)
    except OSError as exc:
        if created:
            shutil.rmtree(runtime_root, ignore_errors=True)
        raise RestoreDrillError(f"cannot create sealed restore smoke environment: {exc}") from exc
    return {
        "HOME": str(home),
        "TMPDIR": str(temporary),
        "XDG_CACHE_HOME": str(cache),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
        "EIDP_APP_ROOT": str(restored_root),
        "EIDP_DATA_DIR": str(restored_root / "data"),
        "EIDP_DATABASE_URL": f"sqlite:///{restored_root / 'data/eidp.sqlite3'}",
        "EIDP_LOG_LEVEL": "INFO",
    }


def _sealed_smoke_environment_fd(restored_fd: int) -> tuple[dict[str, str], os.stat_result]:
    runtime_name = ".restore-smoke-runtime"
    runtime_fd = -1
    created = False
    runtime_stat: os.stat_result | None = None
    try:
        os.mkdir(runtime_name, mode=0o700, dir_fd=restored_fd)
        created = True
        runtime_stat = os.stat(runtime_name, dir_fd=restored_fd, follow_symlinks=False)
        runtime_fd = os.open(runtime_name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=restored_fd)
        opened_runtime = os.fstat(runtime_fd)
        if (opened_runtime.st_dev, opened_runtime.st_ino) != (runtime_stat.st_dev, runtime_stat.st_ino):
            raise RestoreDrillError("sealed restore smoke environment changed while being opened")
        for name in ("home", "tmp", "cache"):
            os.mkdir(name, mode=0o700, dir_fd=runtime_fd)
    except (OSError, RestoreDrillError) as exc:
        if runtime_fd >= 0:
            os.close(runtime_fd)
            runtime_fd = -1
        if created and runtime_stat is not None:
            _remove_owned_tree_at(
                restored_fd,
                runtime_name,
                device=runtime_stat.st_dev,
                inode=runtime_stat.st_ino,
            )
        if isinstance(exc, RestoreDrillError):
            raise
        raise RestoreDrillError(f"cannot create sealed restore smoke environment: {exc}") from exc
    finally:
        if runtime_fd >= 0:
            os.close(runtime_fd)
    if runtime_stat is None:
        raise RestoreDrillError("sealed restore smoke environment has no pinned identity")
    return (
        {
            "HOME": ".restore-smoke-runtime/home",
            "TMPDIR": ".restore-smoke-runtime/tmp",
            "XDG_CACHE_HOME": ".restore-smoke-runtime/cache",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "EIDP_APP_ROOT": ".",
            "EIDP_DATA_DIR": "data",
            "EIDP_DATABASE_URL": "sqlite:///data/eidp.sqlite3",
            "EIDP_LOG_LEVEL": "INFO",
        },
        runtime_stat,
    )


def _terminate_smoke_process(process: _SmokeProcess, *, timeout: float) -> None:
    if timeout <= 0:
        raise RestoreDrillError("restore smoke cleanup timeout must be positive")
    leader_running = process.poll() is None
    if not leader_running:
        process.wait(timeout=timeout)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        if leader_running:
            process.wait(timeout=timeout)
        return
    except OSError as exc:
        raise RestoreDrillError(f"cannot TERM the owned restore smoke process group: {exc}") from exc
    leader_needs_reap = False
    if leader_running:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            leader_needs_reap = True
    if not leader_needs_reap:
        time.sleep(min(timeout, 0.05))
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as exc:
        raise RestoreDrillError(f"cannot KILL the owned restore smoke process group: {exc}") from exc
    if leader_needs_reap:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RestoreDrillError("owned restore smoke process group could not be reaped") from exc


def _port_is_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def _wait_for_port_release(port: int, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_is_available(port):
            return True
        time.sleep(0.05)
    return _port_is_available(port)


def _probe_streamlit_health(port: int, *, timeout: float) -> bool:
    connection = HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET", "/_stcore/health", headers={"Host": f"127.0.0.1:{port}"})
        response = connection.getresponse()
        response.read(4096)
        return response.status == 200
    except OSError:
        return False
    finally:
        connection.close()


def _probe_restored_settings(
    *,
    restored_root: Path,
    environment: dict[str, str],
    timeout: float,
    restored_fd: int | None = None,
) -> None:
    if restored_fd is None:
        probe_code = (
            "import json; from eidp.config import settings; "
            "print(json.dumps({'app_root': str(settings.app_root), "
            "'data_dir': str(settings.data_dir), 'database_url': settings.database_url}, sort_keys=True))"
        )
        command = [sys.executable, "-c", probe_code]
        cwd: Path | None = restored_root
        pass_fds: tuple[int, ...] = ()
        expected: dict[str, object] = {
            "app_root": str(restored_root),
            "data_dir": str(restored_root / "data"),
            "database_url": f"sqlite:///{restored_root / 'data/eidp.sqlite3'}",
        }
    else:
        probe_code = (
            "import json, os, sys; os.fchdir(int(sys.argv[1])); "
            "from eidp.config import settings; "
            "print(json.dumps({'app_root': str(settings.app_root), "
            "'data_dir': str(settings.data_dir), 'database_url': settings.database_url}, sort_keys=True))"
        )
        command = [sys.executable, "-c", probe_code, str(restored_fd)]
        cwd = None
        pass_fds = (restored_fd,)
        expected = {
            "app_root": ".",
            "data_dir": "data",
            "database_url": "sqlite:///data/eidp.sqlite3",
        }
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            pass_fds=pass_fds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RestoreDrillError(f"restored settings probe could not run: {exc}") from exc
    if result.returncode != 0:
        raise RestoreDrillError("restored settings probe exited unsuccessfully")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RestoreDrillError("restored settings probe returned invalid JSON") from exc
    if payload != expected:
        raise RestoreDrillError("restored settings probe did not resolve only the restored paths")


def _run_streamlit_smoke(
    *,
    app_root: Path,
    restored_root: Path,
    smoke_port: int,
    live_port: int,
    timeout: float = 15.0,
    restored_fd: int | None = None,
) -> bool:
    if restored_fd is None:
        restored_root = Path(os.path.abspath(restored_root))
    elif not stat.S_ISDIR(os.fstat(restored_fd).st_mode):
        raise RestoreDrillError("pinned restore smoke root must be a real directory")
    if type(smoke_port) is not int or not 1 <= smoke_port <= 65535 or smoke_port == live_port:
        raise RestoreDrillError("restore smoke port must be valid and different from the live runtime port")
    if timeout <= 0:
        raise RestoreDrillError("restore smoke timeout must be positive")
    if not _port_is_available(smoke_port):
        raise RestoreDrillError("restore smoke loopback port is already occupied")
    web_app = app_root / "src/eidp/web/app.py"
    try:
        app_stat = os.lstat(web_app)
    except OSError as exc:
        raise RestoreDrillError(f"restore smoke Streamlit app is unavailable: {exc}") from exc
    if stat.S_ISLNK(app_stat.st_mode) or not stat.S_ISREG(app_stat.st_mode):
        raise RestoreDrillError("restore smoke Streamlit app must be a real regular file")

    runtime_root: Path | None
    if restored_fd is None:
        environment = _sealed_smoke_environment(restored_root=restored_root)
        runtime_root = Path(environment["HOME"]).parent
        runtime_stat = os.lstat(runtime_root)
    else:
        environment, runtime_stat = _sealed_smoke_environment_fd(restored_fd)
        runtime_root = None
    process: subprocess.Popen[bytes] | None = None
    cleanup_error: RestoreDrillError | None = None
    try:
        _probe_restored_settings(
            restored_root=restored_root,
            environment=environment,
            timeout=min(timeout, 10.0),
            restored_fd=restored_fd,
        )
        streamlit_arguments = [
            "-m",
            "streamlit",
            "run",
            str(web_app),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(smoke_port),
            "--server.baseUrlPath",
            "",
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
        ]
        if restored_fd is None:
            command = [sys.executable, *streamlit_arguments]
            cwd: Path | None = restored_root
            pass_fds: tuple[int, ...] = ()
        else:
            wrapper = (
                "import os, sys; os.fchdir(int(sys.argv[1])); "
                "os.execv(sys.executable, [sys.executable, *sys.argv[2:]])"
            )
            command = [sys.executable, "-c", wrapper, str(restored_fd), *streamlit_arguments]
            cwd = None
            pass_fds = (restored_fd,)
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                pass_fds=pass_fds,
            )
        except OSError as exc:
            raise RestoreDrillError(f"cannot launch isolated restore Streamlit smoke: {exc}") from exc
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            returncode = process.poll()
            if returncode is not None:
                raise RestoreDrillError(f"isolated restore Streamlit smoke exited early with code {returncode}")
            if _probe_streamlit_health(smoke_port, timeout=min(0.25, max(0.05, deadline - time.monotonic()))):
                return True
            time.sleep(0.05)
        raise RestoreDrillError("isolated restore Streamlit health check timed out")
    finally:
        if process is not None:
            try:
                _terminate_smoke_process(process, timeout=min(5.0, max(0.1, timeout)))
            except (OSError, subprocess.SubprocessError, RestoreDrillError) as exc:
                cleanup_error = RestoreDrillError(f"restore smoke process cleanup failed: {exc}")
            if not _wait_for_port_release(smoke_port, timeout=min(5.0, max(0.1, timeout))):
                cleanup_error = RestoreDrillError("restore smoke loopback port was not released")
        try:
            if restored_fd is None:
                if runtime_root is None:
                    raise RestoreDrillError("restore smoke runtime path was not retained for cleanup")
                _remove_owned_tree(runtime_root, device=runtime_stat.st_dev, inode=runtime_stat.st_ino)
            else:
                _remove_owned_tree_at(
                    restored_fd,
                    ".restore-smoke-runtime",
                    device=runtime_stat.st_dev,
                    inode=runtime_stat.st_ino,
                )
        except (OSError, RestoreDrillError) as exc:
            cleanup_error = RestoreDrillError(f"restore smoke environment cleanup failed: {exc}")
        if cleanup_error is not None:
            raise cleanup_error


def _run_restore_with_pinned_parent(
    *,
    root: Path,
    package: Path,
    package_fd: int,
    target: Path,
    verified_parent_fd: int,
    verified_parent_stat: os.stat_result,
    smoke_port: int,
    expected_package_manifest_sha256: str | None,
    off_host_receipt_id: str | None,
    expected_evidence: RestoreEvidenceExpectation | None,
) -> RestoreDrillResult:
    verified = _verify_backup_package_fd(package_fd, expected_backup_id=package.name)
    _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
    if verified.backup_id != package.name or target.name != verified.backup_id:
        raise RestoreDrillError("restore package, target, and backup ID must match")
    if expected_package_manifest_sha256 is not None and not hmac.compare_digest(
        verified.manifest_sha256,
        expected_package_manifest_sha256,
    ):
        raise RestoreDrillError("backup package manifest digest does not match the expected digest")
    deployment = _deployment_evidence_fd(package_fd)
    _verify_checkout(app_root=root, deployment=deployment)

    try:
        existing_stat = os.stat(target.name, dir_fd=verified_parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        existing_stat = None
    if existing_stat is not None:
        if stat.S_ISLNK(existing_stat.st_mode) or not stat.S_ISDIR(existing_stat.st_mode):
            raise RestoreDrillError("existing restore target must be a real directory")
        target_fd = -1
        try:
            target_fd = os.open(target.name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=verified_parent_fd)
            opened_target = os.fstat(target_fd)
            if (opened_target.st_dev, opened_target.st_ino) != (existing_stat.st_dev, existing_stat.st_ino):
                raise RestoreDrillError("existing restore target changed while being opened")
            result = _validate_existing_target(
                app_root=root,
                package_fd=package_fd,
                target=target,
                target_fd=target_fd,
                verified_parent_fd=verified_parent_fd,
                backup_id=verified.backup_id,
                package_manifest_sha256=verified.manifest_sha256,
                deployment=deployment,
                off_host_receipt_id=off_host_receipt_id,
                expected_evidence=expected_evidence,
            )
            _require_directory_entry_identity(
                verified_parent_fd,
                target.name,
                expected_identity=(opened_target.st_dev, opened_target.st_ino),
                label="existing restore target",
            )
        except RestoreDrillError:
            raise
        except OSError as exc:
            raise RestoreDrillError(f"cannot open existing restore target safely: {exc}") from exc
        finally:
            if target_fd >= 0:
                os.close(target_fd)
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        return result

    work_name = f".restore-{secrets.token_hex(12)}.work"
    work_created = False
    work_fd = -1
    try:
        os.mkdir(work_name, mode=0o700, dir_fd=verified_parent_fd)
        work_created = True
        work_fd = os.open(work_name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=verified_parent_fd)
    except OSError as exc:
        if work_created:
            try:
                abandoned_stat = os.stat(work_name, dir_fd=verified_parent_fd, follow_symlinks=False)
                _remove_owned_tree_at(
                    verified_parent_fd,
                    work_name,
                    device=abandoned_stat.st_dev,
                    inode=abandoned_stat.st_ino,
                )
            except (OSError, RestoreDrillError) as cleanup_exc:
                raise RestoreDrillError(
                    f"cannot clean up failed restore work creation: {cleanup_exc}"
                ) from cleanup_exc
        raise RestoreDrillError(f"cannot create exclusive restore work container: {exc}") from exc
    work_stat = os.fstat(work_fd)
    work = target.parent / work_name
    staged = work / verified.backup_id
    staged_fd = -1
    staged_identity: tuple[int, int] | None = None
    published = False
    complete = False
    try:
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        _copy_package_tree(
            package,
            staged,
            pinned_source_fd=package_fd,
            pinned_destination_parent_fd=work_fd,
        )
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        staged_fd = os.open(
            verified.backup_id,
            _DIRECTORY_FLAGS | _NOFOLLOW,
            dir_fd=work_fd,
        )
        staged_stat = os.fstat(staged_fd)
        staged_identity = (staged_stat.st_dev, staged_stat.st_ino)
        _verify_backup_package_fd(
            staged_fd,
            expected_backup_id=verified.backup_id,
            expected_manifest_sha256=verified.manifest_sha256,
        )
        restored_deployment = _deployment_evidence_fd(staged_fd)
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        if restored_deployment != deployment:
            raise RestoreDrillError("copied restore deployment evidence changed during materialization")
        integrity, schema_head = _sqlite_evidence_fd(staged_fd, expected_schema_head=deployment.schema_head)
        acceptance = _verify_acceptance_fd(staged_fd, expected_evidence) if expected_evidence is not None else None
        health_ok = _run_streamlit_smoke(
            app_root=root,
            restored_root=staged,
            smoke_port=smoke_port,
            live_port=deployment.live_port,
            restored_fd=staged_fd,
        )
        if health_ok is not True:
            raise RestoreDrillError("isolated restored Streamlit health smoke did not pass")
        _verify_checkout(app_root=root, deployment=deployment)
        _verify_backup_package_fd(
            staged_fd,
            expected_backup_id=verified.backup_id,
            expected_manifest_sha256=verified.manifest_sha256,
        )

        report_path = staged / "restore-report.v1.json"
        report: dict[str, object] = {
            "schema": "eidp.restore-report.v1",
            "backup_id": verified.backup_id,
            "restored_path": target.relative_to(root).as_posix(),
            "deployment_commit": deployment.deployed_commit,
            "schema_head": schema_head,
            "sqlite_integrity": integrity,
            "health_ok": True,
            "package_manifest_sha256": verified.manifest_sha256,
            "off_host_receipt_id": off_host_receipt_id,
            "verified_at_utc": datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "acceptance_evidence": acceptance,
        }
        _write_restore_report(report_path, report, directory_fd=staged_fd)
        _verify_backup_package_fd(
            staged_fd,
            expected_backup_id=verified.backup_id,
            expected_manifest_sha256=verified.manifest_sha256,
            ignored_file="restore-report.v1.json",
        )
        _fsync_tree_fd(staged_fd)
        result = _result_from_report(
            target=target,
            report_path=target / "restore-report.v1.json",
            report=report,
        )
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        _publish_restore_noreplace(
            staged,
            target,
            source_dir_fd=work_fd,
            target_dir_fd=verified_parent_fd,
        )
        published = True
        _require_pinned_directory(target.parent, verified_parent_stat, label="verified restore parent")
        os.close(staged_fd)
        staged_fd = -1
        os.close(work_fd)
        work_fd = -1
        os.rmdir(work_name, dir_fd=verified_parent_fd)
        os.fsync(verified_parent_fd)
        if staged_identity is None:
            raise RestoreDrillError("published restore target has no pinned identity")
        _require_directory_entry_identity(
            verified_parent_fd,
            target.name,
            expected_identity=staged_identity,
            label="published restore target",
        )
        complete = True
        return result
    finally:
        if published and not complete and staged_identity is not None:
            _remove_owned_tree_at(
                verified_parent_fd,
                target.name,
                device=staged_identity[0],
                inode=staged_identity[1],
            )
        if staged_fd >= 0:
            os.close(staged_fd)
        if work_fd >= 0:
            os.close(work_fd)
        _remove_owned_tree_at(
            verified_parent_fd,
            work_name,
            device=work_stat.st_dev,
            inode=work_stat.st_ino,
        )


def run_restore_drill(
    *,
    app_root: Path,
    package_path: Path,
    target_path: Path,
    smoke_port: int = 18502,
    expected_package_manifest_sha256: str | None = None,
    off_host_receipt_id: str | None = None,
    expected_evidence: RestoreEvidenceExpectation | None = None,
) -> RestoreDrillResult:
    """Verify, rematerialize, smoke, and atomically publish an isolated restore."""

    if expected_evidence is not None:
        expected_evidence = _validated_expectation(expected_evidence)
    root = _absolute_root(app_root)
    package, target = _validate_restore_layout(
        app_root=root,
        package_path=package_path,
        target_path=target_path,
    )
    if expected_package_manifest_sha256 is not None and (
        _SHA256_PATTERN.fullmatch(expected_package_manifest_sha256) is None
    ):
        raise RestoreDrillError("expected package manifest SHA-256 must be exactly 64 lowercase hex characters")
    if off_host_receipt_id is not None:
        try:
            require_receipt_id(off_host_receipt_id)
        except ValueError as exc:
            raise RestoreDrillError(str(exc)) from exc
        if expected_package_manifest_sha256 is None:
            raise RestoreDrillError("off-host receipt requires an expected package manifest digest")

    package_fd = _open_directory(root, package.relative_to(root))
    try:
        verified_parent_fd = _open_directory(root, Path("restore-drills/verified"))
        verified_parent_stat = os.fstat(verified_parent_fd)
        try:
            return _run_restore_with_pinned_parent(
                root=root,
                package=package,
                package_fd=package_fd,
                target=target,
                verified_parent_fd=verified_parent_fd,
                verified_parent_stat=verified_parent_stat,
                smoke_port=smoke_port,
                expected_package_manifest_sha256=expected_package_manifest_sha256,
                off_host_receipt_id=off_host_receipt_id,
                expected_evidence=expected_evidence,
            )
        finally:
            os.close(verified_parent_fd)
    finally:
        os.close(package_fd)
