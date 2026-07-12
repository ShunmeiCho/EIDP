"""Finalized, checksummed recovery packages for the project-local runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.parse import quote

from eidp.db.locking import require_lock_held
from eidp.db.sqlite_backup import backup_sqlite_database

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _NOFOLLOW | _CLOEXEC
_READ_FLAGS = os.O_RDONLY | _NOFOLLOW | _CLOEXEC
_WRITE_EXCLUSIVE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC
_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_COMMIT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SCHEMA_HEAD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_]{0,127}")
_MANIFEST_NAME = "backup-manifest.v1.json"
_FINALIZED_NAME = "FINALIZED"
_DATABASE_RELATIVE = "data/eidp.sqlite3"
_DEPLOYMENT_RELATIVE = "run/deployment-manifest.json"
_MASTER_RELATIVE = "data/master.xlsx"
_OPTIONAL_ROOTS = (
    "data/audit",
    "data/source-pdfs",
    "data/web-intake",
    "output/exports",
)
_REQUIRED_ARTIFACTS = frozenset({_DATABASE_RELATIVE, _DEPLOYMENT_RELATIVE, _MASTER_RELATIVE})
_DEPLOYMENT_KEYS = frozenset(
    {
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
)
_BACKUP_MANIFEST_KEYS = frozenset(
    {
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
)
_PRE_UPGRADE_KEYS = frozenset(
    {
        "schema",
        "upgrade_id",
        "deployment_commit",
        "schema_head",
        "source_database_relative_path",
        "snapshot_sha256",
    }
)


class BackupPackageError(RuntimeError):
    """A backup could not be built or verified without weakening evidence."""


@dataclass(frozen=True)
class BackupPackageResult:
    backup_id: str
    finalized_path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class VerifiedPreUpgradeSnapshot:
    snapshot_path: Path
    manifest_path: Path
    snapshot_sha256: str
    source_database_relative_path: str
    deployment_commit: str
    schema_head: str


@dataclass(frozen=True)
class _InventoryEntry:
    path: str
    size: int
    sha256: str


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _validate_identifier(value: str, *, label: str) -> str:
    if _IDENTIFIER_PATTERN.fullmatch(value) is None or value in {".staging", "pre-upgrade"}:
        raise BackupPackageError(f"unsafe {label}: {value!r}")
    return value


def _validate_commit(value: str, *, label: str = "deployment commit") -> str:
    if _COMMIT_PATTERN.fullmatch(value) is None:
        raise BackupPackageError(f"invalid {label}")
    return value


def _validate_actor(actor: str) -> str:
    if (
        not actor
        or len(actor) > 128
        or actor != actor.strip()
        or any(unicodedata.category(character).startswith("C") for character in actor)
    ):
        raise BackupPackageError("actor must be a bounded non-control identity")
    return actor


def _validate_utc(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BackupPackageError(f"{label} must be UTC evidence")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BackupPackageError(f"{label} must be valid UTC evidence") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise BackupPackageError(f"{label} must be UTC evidence")
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _require_real_directory(path: Path, *, label: str) -> None:
    try:
        current = Path(path.anchor)
        for component in path.parts[1:]:
            current /= component
            current_stat = os.lstat(current)
            if stat.S_ISLNK(current_stat.st_mode):
                raise BackupPackageError(f"unsafe symlink in {label}: {current}")
        final_stat = os.lstat(path)
    except FileNotFoundError as exc:
        raise BackupPackageError(f"{label} does not exist: {path}") from exc
    except OSError as exc:
        raise BackupPackageError(f"cannot inspect {label}: {path}: {exc}") from exc
    if not stat.S_ISDIR(final_stat.st_mode):
        raise BackupPackageError(f"{label} must be a real directory: {path}")


def _ensure_real_directory(path: Path, *, label: str) -> None:
    if not _lexists(path):
        try:
            path.mkdir(mode=0o700)
        except OSError as exc:
            raise BackupPackageError(f"cannot create {label}: {path}: {exc}") from exc
    _require_real_directory(path, label=label)


def _canonical_app_root(app_root: Path) -> Path:
    if ".." in app_root.parts:
        raise BackupPackageError("unsafe project root traversal")
    root = _absolute(app_root)
    _require_real_directory(root, label="project root")
    return root


def _require_exact_project_file(path: Path, *, root: Path, relative: str, label: str) -> Path:
    if ".." in path.parts:
        raise BackupPackageError(f"unsafe traversal in {label}")
    candidate = _absolute(path)
    expected = root / PurePosixPath(relative)
    if candidate != expected:
        raise BackupPackageError(f"{label} must be the project-local {relative}")
    _require_real_regular_file(candidate, root=root, label=label)
    return candidate


def _require_real_regular_file(path: Path, *, root: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise BackupPackageError(f"{label} must remain inside the project root") from exc
    try:
        relative = path.relative_to(root)
        current = root
        for component in relative.parts[:-1]:
            current /= component
            current_stat = os.lstat(current)
            if stat.S_ISLNK(current_stat.st_mode) or not stat.S_ISDIR(current_stat.st_mode):
                raise BackupPackageError(f"unsafe symlink or non-directory in {label}: {current}")
        final_stat = os.lstat(path)
    except FileNotFoundError as exc:
        raise BackupPackageError(f"required {label} is missing: {path}") from exc
    except OSError as exc:
        raise BackupPackageError(f"cannot inspect {label}: {path}: {exc}") from exc
    if stat.S_ISLNK(final_stat.st_mode) or not stat.S_ISREG(final_stat.st_mode):
        raise BackupPackageError(f"unsafe symlink or non-regular {label}: {path}")


def _open_regular_read(path: Path) -> int:
    try:
        descriptor = os.open(path, _READ_FLAGS)
    except OSError as exc:
        raise BackupPackageError(f"unsafe or unreadable regular file: {path}: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise BackupPackageError(f"path is not a real regular file: {path}")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_regular_bytes(path: Path, *, maximum: int) -> bytes:
    descriptor = _open_regular_read(path)
    body = bytearray()
    try:
        while chunk := os.read(descriptor, min(1024 * 1024, maximum + 1 - len(body))):
            body.extend(chunk)
            if len(body) > maximum:
                raise BackupPackageError(f"bounded file limit exceeded: {path}")
    except OSError as exc:
        raise BackupPackageError(f"cannot read regular file: {path}: {exc}") from exc
    finally:
        os.close(descriptor)
    return bytes(body)


def _sha256_file(path: Path) -> str:
    descriptor = _open_regular_read(path)
    digest = hashlib.sha256()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    except OSError as exc:
        raise BackupPackageError(f"cannot hash regular file: {path}: {exc}") from exc
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _write_exclusive(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, _WRITE_EXCLUSIVE_FLAGS, mode)
        written = 0
        while written < len(content):
            written += os.write(descriptor, content[written:])
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    except OSError as exc:
        raise BackupPackageError(f"cannot write package evidence safely: {path}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _copy_regular_file(source: Path, target: Path, *, root: Path, mode: int = 0o600) -> None:
    _require_real_regular_file(source, root=root, label="allowlisted source file")
    target.parent.mkdir(parents=True, exist_ok=True)
    source_fd = _open_regular_read(source)
    target_fd = -1
    created = False
    try:
        target_fd = os.open(target, _WRITE_EXCLUSIVE_FLAGS, mode)
        created = True
        while chunk := os.read(source_fd, 1024 * 1024):
            written = 0
            while written < len(chunk):
                written += os.write(target_fd, chunk[written:])
        os.fchmod(target_fd, mode)
        os.fsync(target_fd)
    except OSError as exc:
        if created:
            try:
                os.unlink(target)
            except OSError:
                pass
        raise BackupPackageError(f"cannot copy allowlisted source safely: {source}: {exc}") from exc
    finally:
        if target_fd >= 0:
            os.close(target_fd)
        os.close(source_fd)


def _copy_optional_directory(source: Path, target: Path, *, root: Path) -> None:
    _require_real_directory(source, label="optional allowlisted root")
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise BackupPackageError("optional source root must remain inside the project root") from exc
    target.mkdir(parents=True, exist_ok=False)

    def visit(current_source: Path, current_target: Path) -> None:
        try:
            entries = sorted(os.scandir(current_source), key=lambda entry: entry.name)
        except OSError as exc:
            raise BackupPackageError(f"cannot enumerate optional allowlisted root: {current_source}: {exc}") from exc
        for entry in entries:
            entry_path = Path(entry.path)
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise BackupPackageError(f"cannot inspect optional allowlisted entry: {entry_path}: {exc}") from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                raise BackupPackageError(f"unsafe symlink in optional allowlisted root: {entry_path}")
            destination = current_target / entry.name
            if stat.S_ISDIR(entry_stat.st_mode):
                destination.mkdir(mode=0o700)
                visit(entry_path, destination)
            elif stat.S_ISREG(entry_stat.st_mode):
                _copy_regular_file(entry_path, destination, root=root)
            else:
                raise BackupPackageError(f"unsafe non-regular entry in optional allowlisted root: {entry_path}")

    visit(source, target)


def _tree_entries(root: Path) -> tuple[list[Path], set[str]]:
    _require_real_directory(root, label="package directory")
    files: list[Path] = []
    directories: set[str] = set()

    def visit(current: Path) -> None:
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name)
        except OSError as exc:
            raise BackupPackageError(f"cannot enumerate package directory: {current}: {exc}") from exc
        for entry in entries:
            entry_path = Path(entry.path)
            relative = entry_path.relative_to(root).as_posix()
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise BackupPackageError(f"cannot inspect package entry: {relative}: {exc}") from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                raise BackupPackageError(f"unsafe symlink in package: {relative}")
            if stat.S_ISDIR(entry_stat.st_mode):
                directories.add(relative)
                visit(entry_path)
            elif stat.S_ISREG(entry_stat.st_mode):
                files.append(entry_path)
            else:
                raise BackupPackageError(f"unsafe non-regular entry in package: {relative}")

    visit(root)
    return files, directories


def _fsync_file(path: Path) -> None:
    descriptor = _open_regular_read(path)
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise BackupPackageError(f"cannot fsync package file: {path}: {exc}") from exc
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise BackupPackageError(f"cannot open package directory for fsync: {path}: {exc}") from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise BackupPackageError(f"cannot fsync package directory: {path}: {exc}") from exc
    finally:
        os.close(descriptor)


def _fsync_tree_directories(root: Path) -> None:
    _, relative_directories = _tree_entries(root)
    for relative in sorted(relative_directories, key=lambda value: len(PurePosixPath(value).parts), reverse=True):
        _fsync_directory(root / PurePosixPath(relative))
    _fsync_directory(root)


def _json_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        payload = json.loads(_read_regular_bytes(path, maximum=16 * 1024 * 1024).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BackupPackageError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BackupPackageError(f"{label} must be a JSON object")
    return cast(dict[str, object], payload)


def _require_exact_keys(payload: dict[str, object], expected: frozenset[str], *, label: str) -> None:
    if set(payload) != expected:
        raise BackupPackageError(f"{label} has unexpected or missing fields")


def _required_string(payload: dict[str, object], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise BackupPackageError(f"{label} field {key!r} must be a string")
    return value


def _parse_deployment_manifest(path: Path) -> tuple[str, str]:
    payload = _json_object(path, label="deployment manifest")
    _require_exact_keys(payload, _DEPLOYMENT_KEYS, label="deployment manifest")
    deployed_commit = _validate_commit(_required_string(payload, "deployed_commit", label="deployment manifest"))
    _validate_commit(
        _required_string(payload, "expected_deployment_commit", label="deployment manifest"),
        label="expected deployment commit",
    )
    _validate_commit(
        _required_string(payload, "origin_main_commit", label="deployment manifest"),
        label="origin/main commit",
    )
    if _SHA256_PATTERN.fullmatch(_required_string(payload, "uv_lock_sha256", label="deployment manifest")) is None:
        raise BackupPackageError("deployment manifest uv.lock digest is invalid")
    schema_head = _required_string(payload, "schema_head", label="deployment manifest")
    if _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise BackupPackageError("deployment manifest schema head is invalid")
    _validate_utc(payload.get("deployed_at_utc"), label="deployment manifest deployed_at_utc")
    _validate_actor(_required_string(payload, "operator", label="deployment manifest"))
    for key in ("internal_base_url", "base_url_path"):
        _required_string(payload, key, label="deployment manifest")
    if type(payload.get("port")) is not int:
        raise BackupPackageError("deployment manifest port must be an integer")
    for key in ("pre_upgrade_backup_id", "off_host_receipt_id"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise BackupPackageError(f"deployment manifest field {key!r} must be a string or null")
    return deployed_commit, schema_head


def _sqlite_schema_head(path: Path) -> str:
    uri = f"file:{quote(str(path), safe='/')}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            heads = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    except sqlite3.Error as exc:
        raise BackupPackageError(f"packaged SQLite verification failed: {exc}") from exc
    if integrity != [("ok",)]:
        raise BackupPackageError(f"packaged SQLite integrity_check failed: {integrity}")
    if len(heads) != 1 or not isinstance(heads[0][0], str):
        raise BackupPackageError("packaged SQLite must contain exactly one Alembic schema head")
    schema_head = heads[0][0]
    if _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise BackupPackageError("packaged SQLite schema head is invalid")
    return schema_head


def _artifact_is_allowlisted(relative: str) -> bool:
    if relative in _REQUIRED_ARTIFACTS:
        return True
    return any(relative.startswith(root + "/") for root in _OPTIONAL_ROOTS)


def _inventory_for(root: Path) -> list[_InventoryEntry]:
    files, _ = _tree_entries(root)
    entries: list[_InventoryEntry] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        if not _artifact_is_allowlisted(relative):
            raise BackupPackageError(f"package contains a non-allowlisted artifact: {relative}")
        entries.append(_InventoryEntry(relative, path.stat().st_size, _sha256_file(path)))
    return sorted(entries, key=lambda entry: entry.path)


def _inventory_payload(entries: list[_InventoryEntry]) -> list[dict[str, object]]:
    return [{"path": entry.path, "size": entry.size, "sha256": entry.sha256} for entry in entries]


def _parse_inventory(value: object) -> list[_InventoryEntry]:
    if not isinstance(value, list):
        raise BackupPackageError("backup manifest inventory must be a list")
    entries: list[_InventoryEntry] = []
    for raw_entry in value:
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"path", "size", "sha256"}:
            raise BackupPackageError("backup manifest inventory entry is invalid")
        relative = raw_entry.get("path")
        size = raw_entry.get("size")
        digest = raw_entry.get("sha256")
        if not isinstance(relative, str) or not relative:
            raise BackupPackageError("backup manifest inventory path is invalid")
        parsed = PurePosixPath(relative)
        if parsed.is_absolute() or str(parsed) != relative or any(part in {"", ".", ".."} for part in parsed.parts):
            raise BackupPackageError(f"unsafe backup inventory path: {relative}")
        if not _artifact_is_allowlisted(relative):
            raise BackupPackageError(f"non-allowlisted backup inventory path: {relative}")
        if type(size) is not int or size < 0:
            raise BackupPackageError(f"backup inventory size is invalid: {relative}")
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise BackupPackageError(f"backup inventory digest is invalid: {relative}")
        entries.append(_InventoryEntry(relative, size, digest))
    paths = [entry.path for entry in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise BackupPackageError("backup inventory must be sorted and unique")
    if not _REQUIRED_ARTIFACTS.issubset(paths):
        raise BackupPackageError("backup inventory is missing a required artifact")
    return entries


def _parse_optional_roots(value: object) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != set(_OPTIONAL_ROOTS):
        raise BackupPackageError("backup optional-root evidence is invalid")
    result: dict[str, bool] = {}
    for root in _OPTIONAL_ROOTS:
        present = value.get(root)
        if type(present) is not bool:
            raise BackupPackageError("backup optional-root presence must be boolean")
        result[root] = present
    return result


def _expected_directories(entries: list[_InventoryEntry], optional_roots: dict[str, bool]) -> set[str]:
    expected: set[str] = set()
    paths = [PurePosixPath(entry.path) for entry in entries]
    paths.extend(PurePosixPath(root) for root, present in optional_roots.items() if present)
    for path in paths:
        parent = path if path.as_posix() in _OPTIONAL_ROOTS else path.parent
        while parent != PurePosixPath("."):
            expected.add(parent.as_posix())
            parent = parent.parent
    return expected


def _hash_tree(root: Path) -> dict[str, str]:
    files, _ = _tree_entries(root)
    return {path.relative_to(root).as_posix(): _sha256_file(path) for path in files}


def _verify_package(
    path: Path,
    *,
    require_finalized: bool,
    expected_backup_id: str | None = None,
    enforce_directory_name: bool,
) -> BackupPackageResult:
    package = _absolute(path)
    _require_real_directory(package, label="backup package")
    manifest_path = package / _MANIFEST_NAME
    marker_path = package / _FINALIZED_NAME
    marker_exists = _lexists(marker_path)
    if require_finalized and not marker_exists:
        raise BackupPackageError(f"backup package is not finalized: {package}")
    if not require_finalized and marker_exists:
        raise BackupPackageError("unfinalized verification received an unexpected marker")

    manifest_digest = _sha256_file(manifest_path)
    if marker_exists:
        marker = _read_regular_bytes(marker_path, maximum=65)
        expected_marker = (manifest_digest + "\n").encode("ascii")
        if marker != expected_marker:
            raise BackupPackageError("backup FINALIZED marker does not match the manifest")

    payload = _json_object(manifest_path, label="backup manifest")
    _require_exact_keys(payload, _BACKUP_MANIFEST_KEYS, label="backup manifest")
    if payload.get("schema") != "eidp.backup-manifest.v1":
        raise BackupPackageError("backup manifest schema is invalid")
    backup_id = _validate_identifier(_required_string(payload, "backup_id", label="backup manifest"), label="backup ID")
    if expected_backup_id is not None and backup_id != expected_backup_id:
        raise BackupPackageError("backup manifest ID does not match the requested backup ID")
    if enforce_directory_name and package.name != backup_id:
        raise BackupPackageError("backup manifest ID does not match the package path")
    deployment_commit = _validate_commit(_required_string(payload, "deployment_commit", label="backup manifest"))
    schema_head = _required_string(payload, "schema_head", label="backup manifest")
    if _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise BackupPackageError("backup manifest schema head is invalid")
    if payload.get("source_database_relative_path") != _DATABASE_RELATIVE:
        raise BackupPackageError("backup manifest source database path is unsafe")
    _validate_actor(_required_string(payload, "actor", label="backup manifest"))
    _validate_utc(payload.get("created_at_utc"), label="backup creation time")
    _validate_utc(payload.get("wal_checkpoint_succeeded_at_utc"), label="backup checkpoint time")
    if payload.get("wal_checkpoint_succeeded") is not True:
        raise BackupPackageError("backup manifest does not prove a successful WAL checkpoint")
    snapshot_digest = _required_string(payload, "sqlite_snapshot_sha256", label="backup manifest")
    deployment_digest = _required_string(payload, "deployment_manifest_sha256", label="backup manifest")
    if _SHA256_PATTERN.fullmatch(snapshot_digest) is None or _SHA256_PATTERN.fullmatch(deployment_digest) is None:
        raise BackupPackageError("backup manifest digest field is invalid")
    optional_roots = _parse_optional_roots(payload.get("optional_roots"))
    inventory = _parse_inventory(payload.get("inventory"))

    files, directories = _tree_entries(package)
    actual_files = {file.relative_to(package).as_posix() for file in files}
    expected_files = {entry.path for entry in inventory} | {_MANIFEST_NAME}
    if marker_exists:
        expected_files.add(_FINALIZED_NAME)
    if actual_files != expected_files:
        raise BackupPackageError("backup package has missing or extra files")
    actual_optional_roots = {root: root in directories for root in _OPTIONAL_ROOTS}
    if actual_optional_roots != optional_roots:
        raise BackupPackageError("backup optional-root presence does not match the package tree")
    if directories != _expected_directories(inventory, optional_roots):
        raise BackupPackageError("backup package has missing or extra directories")

    for entry in inventory:
        artifact = package / PurePosixPath(entry.path)
        artifact_stat = os.lstat(artifact)
        if artifact_stat.st_size != entry.size or _sha256_file(artifact) != entry.sha256:
            raise BackupPackageError(f"backup artifact digest or size mismatch: {entry.path}")

    inventory_by_path = {entry.path: entry for entry in inventory}
    if inventory_by_path[_DATABASE_RELATIVE].sha256 != snapshot_digest:
        raise BackupPackageError("backup SQLite snapshot digest binding is invalid")
    if inventory_by_path[_DEPLOYMENT_RELATIVE].sha256 != deployment_digest:
        raise BackupPackageError("backup deployment manifest digest binding is invalid")
    deployed, deployed_schema = _parse_deployment_manifest(package / _DEPLOYMENT_RELATIVE)
    if deployed != deployment_commit or deployed_schema != schema_head:
        raise BackupPackageError("backup deployment manifest binding is invalid")

    before = _hash_tree(package)
    if _sqlite_schema_head(package / _DATABASE_RELATIVE) != schema_head:
        raise BackupPackageError("backup SQLite schema does not match deployment evidence")
    if _hash_tree(package) != before:
        raise BackupPackageError("backup package changed during read-only verification")
    return BackupPackageResult(backup_id=backup_id, finalized_path=package, manifest_sha256=manifest_digest)


def verify_backup_package(path: Path) -> BackupPackageResult:
    """Read-only verification of a finalized package and its SQLite snapshot."""

    package = _absolute(path)
    if ".staging" in package.parts:
        raise BackupPackageError("backup staging directories are never finalized evidence")
    return _verify_package(package, require_finalized=True, enforce_directory_name=True)


def _remove_owned_staging(path: Path, *, device: int, inode: int) -> None:
    try:
        current = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError:
        return
    if stat.S_ISDIR(current.st_mode) and not stat.S_ISLNK(current.st_mode) and (current.st_dev, current.st_ino) == (
        device,
        inode,
    ):
        shutil.rmtree(path)


def _create_staging(parent: Path, *, prefix: str) -> tuple[Path, int, int]:
    for _ in range(32):
        candidate = parent / f"{prefix}-{secrets.token_hex(12)}"
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            continue
        except OSError as exc:
            raise BackupPackageError(f"cannot create unique backup staging directory: {exc}") from exc
        created = os.lstat(candidate)
        return candidate, created.st_dev, created.st_ino
    raise BackupPackageError("cannot allocate a unique backup staging directory")


def _write_finalized_marker(package: Path, manifest_sha256: str) -> None:
    if _SHA256_PATTERN.fullmatch(manifest_sha256) is None:
        raise BackupPackageError("cannot finalize an invalid manifest digest")
    _write_exclusive(package / _FINALIZED_NAME, (manifest_sha256 + "\n").encode("ascii"))
    _fsync_directory(package)
    _fsync_directory(package.parent)


def _fsync_finalized_publication(package: Path) -> None:
    _fsync_directory(package)
    _fsync_directory(package.parent)


def _existing_backup(final_path: Path, *, backup_id: str) -> BackupPackageResult | None:
    if not _lexists(final_path):
        return None
    marker = final_path / _FINALIZED_NAME
    if _lexists(marker):
        result = verify_backup_package(final_path)
    else:
        verified = _verify_package(
            final_path,
            require_finalized=False,
            expected_backup_id=backup_id,
            enforce_directory_name=True,
        )
        _write_finalized_marker(final_path, verified.manifest_sha256)
        result = verify_backup_package(final_path)
    _fsync_finalized_publication(final_path)
    return result


def build_backup_package(
    *,
    app_root: Path,
    database_path: Path,
    backup_id: str,
    deployment_manifest: Path,
    actor: str,
) -> BackupPackageResult:
    """Build, verify, atomically publish and finalize one allowlisted package."""

    root = _canonical_app_root(app_root)
    identifier = _validate_identifier(backup_id, label="backup ID")
    source_database = _require_exact_project_file(
        database_path,
        root=root,
        relative=_DATABASE_RELATIVE,
        label="SQLite database",
    )
    source_deployment = _require_exact_project_file(
        deployment_manifest,
        root=root,
        relative=_DEPLOYMENT_RELATIVE,
        label="deployment manifest",
    )
    source_master = _require_exact_project_file(
        root / _MASTER_RELATIVE,
        root=root,
        relative=_MASTER_RELATIVE,
        label="master workbook",
    )
    validated_actor = _validate_actor(actor)
    try:
        require_lock_held(root / "data/.lock")
    except RuntimeError as exc:
        raise BackupPackageError("required data lock is not held by the current thread") from exc

    backups = root / "backups"
    _ensure_real_directory(backups, label="backups directory")
    staging_root = backups / ".staging"
    _ensure_real_directory(staging_root, label="backup staging root")
    final_path = backups / identifier
    existing = _existing_backup(final_path, backup_id=identifier)
    if existing is not None:
        return existing

    staging, staging_device, staging_inode = _create_staging(staging_root, prefix=identifier)
    published = False
    try:
        backup_sqlite_database(source_database, staging / _DATABASE_RELATIVE)
        checkpoint_succeeded_at = _utc_now()
        _fsync_file(staging / _DATABASE_RELATIVE)
        _copy_regular_file(source_deployment, staging / _DEPLOYMENT_RELATIVE, root=root)
        _copy_regular_file(source_master, staging / _MASTER_RELATIVE, root=root, mode=0o400)

        optional_presence: dict[str, bool] = {}
        for relative in _OPTIONAL_ROOTS:
            source_root = root / PurePosixPath(relative)
            present = _lexists(source_root)
            optional_presence[relative] = present
            if present:
                _copy_optional_directory(source_root, staging / PurePosixPath(relative), root=root)

        deployment_commit, deployment_schema = _parse_deployment_manifest(staging / _DEPLOYMENT_RELATIVE)
        snapshot_schema = _sqlite_schema_head(staging / _DATABASE_RELATIVE)
        if deployment_schema != snapshot_schema:
            raise BackupPackageError("deployment manifest schema does not match the SQLite snapshot")
        inventory = _inventory_for(staging)
        inventory_by_path = {entry.path: entry for entry in inventory}
        manifest: dict[str, object] = {
            "schema": "eidp.backup-manifest.v1",
            "backup_id": identifier,
            "deployment_commit": deployment_commit,
            "schema_head": snapshot_schema,
            "source_database_relative_path": _DATABASE_RELATIVE,
            "actor": validated_actor,
            "created_at_utc": _utc_now(),
            "wal_checkpoint_succeeded": True,
            "wal_checkpoint_succeeded_at_utc": checkpoint_succeeded_at,
            "sqlite_snapshot_sha256": inventory_by_path[_DATABASE_RELATIVE].sha256,
            "deployment_manifest_sha256": inventory_by_path[_DEPLOYMENT_RELATIVE].sha256,
            "optional_roots": optional_presence,
            "inventory": _inventory_payload(inventory),
        }
        encoded_manifest = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        _write_exclusive(staging / _MANIFEST_NAME, encoded_manifest)
        _fsync_tree_directories(staging)
        staged = _verify_package(
            staging,
            require_finalized=False,
            expected_backup_id=identifier,
            enforce_directory_name=False,
        )

        if _lexists(final_path):
            raise BackupPackageError(f"backup final path already exists and will not be overwritten: {final_path}")
        os.rename(staging, final_path)
        published = True
        _fsync_directory(backups)
        _write_finalized_marker(final_path, staged.manifest_sha256)
        return verify_backup_package(final_path)
    except BackupPackageError:
        raise
    except Exception as exc:
        raise BackupPackageError(f"backup package build failed: {exc}") from exc
    finally:
        if not published:
            _remove_owned_staging(staging, device=staging_device, inode=staging_inode)


def _verify_pre_upgrade_directory(
    directory: Path,
    *,
    expected_upgrade_id: str,
    expected_deployment_commit: str,
) -> VerifiedPreUpgradeSnapshot:
    root = _absolute(directory)
    _require_real_directory(root, label="pre-upgrade snapshot directory")
    files, directories = _tree_entries(root)
    if directories or {path.relative_to(root).as_posix() for path in files} != {
        "eidp.sqlite3",
        "pre-upgrade-manifest.v1.json",
    }:
        raise BackupPackageError("pre-upgrade snapshot has missing or extra entries")
    snapshot_path = root / "eidp.sqlite3"
    manifest_path = root / "pre-upgrade-manifest.v1.json"
    payload = _json_object(manifest_path, label="pre-upgrade manifest")
    _require_exact_keys(payload, _PRE_UPGRADE_KEYS, label="pre-upgrade manifest")
    if payload.get("schema") != "eidp.pre-upgrade-snapshot.v1":
        raise BackupPackageError("pre-upgrade manifest schema is invalid")
    if payload.get("upgrade_id") != expected_upgrade_id:
        raise BackupPackageError("pre-upgrade manifest ID does not match")
    if payload.get("deployment_commit") != expected_deployment_commit:
        raise BackupPackageError("pre-upgrade deployment commit does not match")
    if payload.get("source_database_relative_path") != _DATABASE_RELATIVE:
        raise BackupPackageError("pre-upgrade source database path is unsafe")
    schema_head = _required_string(payload, "schema_head", label="pre-upgrade manifest")
    if _SCHEMA_HEAD_PATTERN.fullmatch(schema_head) is None:
        raise BackupPackageError("pre-upgrade schema head is invalid")
    snapshot_sha256 = _required_string(payload, "snapshot_sha256", label="pre-upgrade manifest")
    if _SHA256_PATTERN.fullmatch(snapshot_sha256) is None or _sha256_file(snapshot_path) != snapshot_sha256:
        raise BackupPackageError("pre-upgrade snapshot digest does not match")
    before = _hash_tree(root)
    if _sqlite_schema_head(snapshot_path) != schema_head:
        raise BackupPackageError("pre-upgrade SQLite schema does not match its manifest")
    if _hash_tree(root) != before:
        raise BackupPackageError("pre-upgrade evidence changed during read-only verification")
    return VerifiedPreUpgradeSnapshot(
        snapshot_path=snapshot_path,
        manifest_path=manifest_path,
        snapshot_sha256=snapshot_sha256,
        source_database_relative_path=_DATABASE_RELATIVE,
        deployment_commit=expected_deployment_commit,
        schema_head=schema_head,
    )


def build_pre_upgrade_snapshot(
    *,
    app_root: Path,
    database_path: Path,
    upgrade_id: str,
    deployment_commit: str,
) -> VerifiedPreUpgradeSnapshot:
    """Create and verify a DB-only code/schema-paired snapshot under the caller's lock."""

    root = _canonical_app_root(app_root)
    identifier = _validate_identifier(upgrade_id, label="upgrade ID")
    commit = _validate_commit(deployment_commit)
    source_database = _require_exact_project_file(
        database_path,
        root=root,
        relative=_DATABASE_RELATIVE,
        label="SQLite database",
    )
    try:
        require_lock_held(root / "data/.lock")
    except RuntimeError as exc:
        raise BackupPackageError("required data lock is not held by the current thread") from exc

    backups = root / "backups"
    _ensure_real_directory(backups, label="backups directory")
    pre_upgrade_root = backups / "pre-upgrade"
    _ensure_real_directory(pre_upgrade_root, label="pre-upgrade root")
    staging_root = pre_upgrade_root / ".staging"
    _ensure_real_directory(staging_root, label="pre-upgrade staging root")
    final_path = pre_upgrade_root / identifier
    if _lexists(final_path):
        result = _verify_pre_upgrade_directory(
            final_path,
            expected_upgrade_id=identifier,
            expected_deployment_commit=commit,
        )
        _fsync_directory(final_path)
        _fsync_directory(pre_upgrade_root)
        _fsync_directory(backups)
        return result

    staging, staging_device, staging_inode = _create_staging(staging_root, prefix=identifier)
    published = False
    try:
        snapshot_path = staging / "eidp.sqlite3"
        backup_sqlite_database(source_database, snapshot_path)
        _fsync_file(snapshot_path)
        snapshot_sha256 = _sha256_file(snapshot_path)
        schema_head = _sqlite_schema_head(snapshot_path)
        payload: dict[str, object] = {
            "deployment_commit": commit,
            "schema": "eidp.pre-upgrade-snapshot.v1",
            "schema_head": schema_head,
            "snapshot_sha256": snapshot_sha256,
            "source_database_relative_path": _DATABASE_RELATIVE,
            "upgrade_id": identifier,
        }
        manifest_path = staging / "pre-upgrade-manifest.v1.json"
        _write_exclusive(
            manifest_path,
            (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"),
        )
        _fsync_tree_directories(staging)
        _verify_pre_upgrade_directory(
            staging,
            expected_upgrade_id=identifier,
            expected_deployment_commit=commit,
        )
        if _lexists(final_path):
            raise BackupPackageError(f"pre-upgrade final path already exists and will not be overwritten: {final_path}")
        os.rename(staging, final_path)
        published = True
        _fsync_directory(pre_upgrade_root)
        _fsync_directory(backups)
        return _verify_pre_upgrade_directory(
            final_path,
            expected_upgrade_id=identifier,
            expected_deployment_commit=commit,
        )
    except BackupPackageError:
        raise
    except Exception as exc:
        raise BackupPackageError(f"pre-upgrade snapshot build failed: {exc}") from exc
    finally:
        if not published:
            _remove_owned_staging(staging, device=staging_device, inode=staging_inode)
