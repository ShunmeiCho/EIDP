"""Traceable, secret-free deployment manifest collection and persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import stat
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from eidp.ops.runtime_config import RuntimeLaunchConfig

_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_COMMIT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SCHEMA_HEAD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_]{0,127}")
_OPAQUE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}")


class DeploymentManifestError(RuntimeError):
    """Manifest evidence could not be collected or persisted safely."""


@dataclass(frozen=True)
class DeploymentManifest:
    deployed_commit: str
    expected_deployment_commit: str
    origin_main_commit: str
    uv_lock_sha256: str
    schema_head: str
    deployed_at_utc: str
    operator: str
    internal_base_url: str
    port: int
    base_url_path: str
    pre_upgrade_backup_id: str | None
    off_host_receipt_id: str | None


def _git(
    app_root: Path,
    *arguments: str,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=app_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise DeploymentManifestError("git is unavailable for deployment verification") from exc
    if result.returncode not in allowed_returncodes:
        raise DeploymentManifestError("local Git deployment evidence is unavailable")
    return result


def _canonical_project_root(app_root: Path) -> Path:
    absolute = Path(os.path.abspath(app_root))
    try:
        root_stat = os.lstat(absolute)
    except OSError as exc:
        raise DeploymentManifestError(f"project root is unavailable: {exc}") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise DeploymentManifestError("project root must be a real project-local directory, not a symlink")

    top_level = _git(absolute, "rev-parse", "--show-toplevel").stdout.strip()
    try:
        discovered = Path(top_level).resolve(strict=True)
    except OSError as exc:
        raise DeploymentManifestError("Git project root is unavailable") from exc
    if discovered != absolute.resolve(strict=True):
        raise DeploymentManifestError("app root must equal the project root of the deployment checkout")
    return absolute


def _open_directory(app_root: Path, relative: Path) -> int:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise DeploymentManifestError(f"unsafe project-local directory: {relative}")
    try:
        descriptor = os.open(app_root, _DIRECTORY_FLAGS | _NOFOLLOW)
    except OSError as exc:
        raise DeploymentManifestError(f"unsafe project root: {exc}") from exc
    try:
        for component in relative.parts:
            try:
                next_descriptor = os.open(
                    component,
                    _DIRECTORY_FLAGS | _NOFOLLOW,
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise DeploymentManifestError(
                    f"unsafe project-local directory or symlink: {relative}: {exc}"
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_regular_file(app_root: Path, relative: Path) -> tuple[int, int]:
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise DeploymentManifestError(f"unsafe project-local file: {relative}")
    parent = Path(*relative.parts[:-1])
    directory_fd = _open_directory(app_root, parent) if parent.parts else _open_directory(app_root, Path())
    try:
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        os.close(directory_fd)
        raise DeploymentManifestError(f"unsafe or missing project-local file {relative}: {exc}") from exc
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        os.close(directory_fd)
        raise DeploymentManifestError(f"project-local file must be regular: {relative}")
    return descriptor, directory_fd


def _uv_lock_sha256(app_root: Path) -> str:
    tracked = _git(app_root, "ls-files", "--error-unmatch", "--", "uv.lock", allowed_returncodes=(0, 1))
    if tracked.returncode != 0:
        raise DeploymentManifestError("uv.lock must be tracked by the deployment commit")
    try:
        descriptor, directory_fd = _open_regular_file(app_root, Path("uv.lock"))
    except DeploymentManifestError as exc:
        raise DeploymentManifestError(f"uv.lock is missing or unsafe: {exc}") from exc
    digest = hashlib.sha256()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    except OSError as exc:
        raise DeploymentManifestError(f"uv.lock cannot be read safely: {exc}") from exc
    finally:
        os.close(descriptor)
        os.close(directory_fd)
    return digest.hexdigest()


def _schema_head(app_root: Path) -> str:
    relative = Path("data/eidp.sqlite3")
    try:
        descriptor, directory_fd = _open_regular_file(app_root, relative)
    except DeploymentManifestError as exc:
        raise DeploymentManifestError(f"canonical data/eidp.sqlite3 is missing or unsafe: {exc}") from exc
    pinned_stat = os.fstat(descriptor)
    database_path = app_root / relative
    database_uri = f"file:{quote(str(database_path), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(database_uri, uri=True) as connection:
            rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        current_stat = os.stat(relative.name, dir_fd=directory_fd, follow_symlinks=False)
        if (current_stat.st_dev, current_stat.st_ino) != (pinned_stat.st_dev, pinned_stat.st_ino):
            raise DeploymentManifestError("canonical data/eidp.sqlite3 changed during schema inspection")
    except (OSError, sqlite3.Error) as exc:
        raise DeploymentManifestError(f"canonical SQLite alembic_version is invalid: {exc}") from exc
    finally:
        os.close(descriptor)
        os.close(directory_fd)

    if len(rows) != 1 or not isinstance(rows[0][0], str):
        raise DeploymentManifestError("canonical SQLite alembic_version must contain exactly one schema head")
    head = rows[0][0]
    if _SCHEMA_HEAD_PATTERN.fullmatch(head) is None:
        raise DeploymentManifestError("canonical SQLite schema head is invalid")
    return head


def _validate_operator(actor: str) -> str:
    if (
        not actor
        or len(actor) > 128
        or actor != actor.strip()
        or any(unicodedata.category(character).startswith("C") for character in actor)
    ):
        raise DeploymentManifestError("operator must be a bounded non-control identity")
    return actor


def _validate_optional_identifier(value: str | None, *, label: str) -> str | None:
    if value is not None and _OPAQUE_ID_PATTERN.fullmatch(value) is None:
        raise DeploymentManifestError(f"{label} must be a bounded non-secret identifier")
    return value


def _source_commits(app_root: Path, expected_deployment_commit: str | None) -> tuple[str, str, str]:
    head = _git(app_root, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()
    origin_result = _git(
        app_root,
        "rev-parse",
        "--verify",
        "refs/remotes/origin/main^{commit}",
        allowed_returncodes=(0, 1, 128),
    )
    origin_main = origin_result.stdout.strip()
    if origin_result.returncode != 0 or _COMMIT_PATTERN.fullmatch(origin_main) is None:
        raise DeploymentManifestError("fetched origin/main is missing or invalid")
    if _COMMIT_PATTERN.fullmatch(head) is None:
        raise DeploymentManifestError("HEAD is not a full deployment commit")

    index_entries = _git(app_root, "ls-files", "-v", "-z").stdout.split("\0")
    if any(entry and (entry[0].islower() or entry[0] == "S") for entry in index_entries):
        raise DeploymentManifestError(
            "deployment checkout index must not contain assume-unchanged or skip-worktree entries"
        )

    dirty = _git(app_root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if dirty:
        raise DeploymentManifestError("deployment manifest requires a clean checkout")

    if expected_deployment_commit is None:
        if head != origin_main:
            raise DeploymentManifestError("HEAD must equal fetched origin/main in default deployment mode")
        expected = head
    else:
        if _COMMIT_PATTERN.fullmatch(expected_deployment_commit) is None or expected_deployment_commit != head:
            raise DeploymentManifestError("expected deployment commit must exactly equal HEAD")
        ancestry = _git(
            app_root,
            "merge-base",
            "--is-ancestor",
            head,
            origin_main,
            allowed_returncodes=(0, 1),
        )
        if ancestry.returncode != 0:
            raise DeploymentManifestError("HEAD must remain an ancestor of fetched origin/main")
        expected = expected_deployment_commit
    return head, expected, origin_main


def collect_deployment_manifest(
    *,
    app_root: Path,
    runtime: RuntimeLaunchConfig,
    actor: str,
    expected_deployment_commit: str | None = None,
    pre_upgrade_backup_id: str | None = None,
    off_host_receipt_id: str | None = None,
) -> DeploymentManifest:
    """Fail closed on dirty or unpublished source and return whitelisted fields."""

    root = _canonical_project_root(app_root)
    uv_lock_sha256 = _uv_lock_sha256(root)
    schema_head = _schema_head(root)
    deployed, expected, origin_main = _source_commits(root, expected_deployment_commit)
    operator = _validate_operator(actor)
    backup_id = _validate_optional_identifier(pre_upgrade_backup_id, label="pre-upgrade backup ID")
    receipt_id = _validate_optional_identifier(off_host_receipt_id, label="off-host receipt ID")
    return DeploymentManifest(
        deployed_commit=deployed,
        expected_deployment_commit=expected,
        origin_main_commit=origin_main,
        uv_lock_sha256=uv_lock_sha256,
        schema_head=schema_head,
        deployed_at_utc=datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        operator=operator,
        internal_base_url=runtime.internal_base_url,
        port=runtime.port,
        base_url_path=runtime.base_url_path,
        pre_upgrade_backup_id=backup_id,
        off_host_receipt_id=receipt_id,
    )


def _manifest_payload(manifest: DeploymentManifest) -> dict[str, str | int | None]:
    return {
        "deployed_commit": manifest.deployed_commit,
        "expected_deployment_commit": manifest.expected_deployment_commit,
        "origin_main_commit": manifest.origin_main_commit,
        "uv_lock_sha256": manifest.uv_lock_sha256,
        "schema_head": manifest.schema_head,
        "deployed_at_utc": manifest.deployed_at_utc,
        "operator": manifest.operator,
        "internal_base_url": manifest.internal_base_url,
        "port": manifest.port,
        "base_url_path": manifest.base_url_path,
        "pre_upgrade_backup_id": manifest.pre_upgrade_backup_id,
        "off_host_receipt_id": manifest.off_host_receipt_id,
    }


def write_deployment_manifest_atomic(path: Path, manifest: DeploymentManifest) -> None:
    """Write a whitelisted manifest through a durable same-directory replacement."""

    target = Path(os.path.abspath(path))
    parent = target.parent
    temporary_name = f".{target.name}.{secrets.token_hex(12)}.tmp"
    encoded = (json.dumps(_manifest_payload(manifest), ensure_ascii=False, sort_keys=True) + "\n").encode()
    directory_fd = -1
    descriptor = -1
    temporary_created = False
    try:
        try:
            directory_fd = os.open(parent, _DIRECTORY_FLAGS | _NOFOLLOW)
        except OSError as exc:
            raise DeploymentManifestError(f"unsafe deployment manifest parent directory: {exc}") from exc
        try:
            existing = os.stat(target.name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise DeploymentManifestError("deployment manifest final path is an unsafe symlink or non-file")
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        temporary_created = True
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(
            temporary_name,
            target.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        os.fsync(directory_fd)
    except DeploymentManifestError:
        raise
    except OSError as exc:
        raise DeploymentManifestError(f"cannot write deployment manifest safely: {exc}") from exc
    finally:
        active_error = sys.exception()
        cleanup_error: OSError | None = None
        if descriptor >= 0:
            os.close(descriptor)
        if directory_fd >= 0 and temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            except OSError as exc:
                cleanup_error = exc
        if directory_fd >= 0:
            os.close(directory_fd)
        if cleanup_error is not None:
            error = DeploymentManifestError(f"cannot clean up temporary deployment manifest: {cleanup_error}")
            raise error from (active_error or cleanup_error)


if __name__ == "__main__":
    print("This module is operated through deploy/linux/eidpctl.sh", file=sys.stderr)
    raise SystemExit(2)
