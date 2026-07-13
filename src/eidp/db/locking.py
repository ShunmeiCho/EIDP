"""POSIX cross-process advisory lock for the Linux/Web deployment.

The lock coordinates background jobs, CLI writes, and Streamlit writes that
share the SQLite-backed application data directory.

Design contract owner pinned in v6:

  * v1 = strict whole-job exclusion. Weekly runner holds the lock from
    start to finish; UI write paths refuse with a banner ("週次処理中、
    編集は一時停止") if they cannot acquire it. UI read paths run
    unimpeded.
  * Linux/macOS use ``fcntl.flock``; Windows is no longer a supported target.
  * Stale-lock recovery — the lock file persists across crashes, but
    OS-level file locks release on process death, so re-acquisition
    "just works". The lock file also records pid+started_at metadata
    for diagnostics; that metadata is best-effort, never used for
    correctness.

API
---
``acquire_lock(lock_path, *, owner='weekly_runner')``
    Context manager. Tries to obtain the lock; raises
    ``LockBusyError`` immediately if another process holds it. Use
    inside the weekly runner.

``acquire_lock_or_block(lock_path, *, owner, timeout=None)``
    Blocking variant. Used very rarely — prefer the non-blocking
    variant + UI feedback.

``probe_lock(lock_path) -> LockStatus``
    Non-mutating check used by the UI to render the status banner.
    Returns whether the lock is currently held and any owner metadata
    written by the holder.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import structlog

log = structlog.get_logger(__name__)


class LockBusyError(RuntimeError):
    """Raised when a non-blocking lock acquisition fails because another
    process is already holding the lock."""


@dataclass(frozen=True)
class LockStatus:
    """Read-only snapshot of the lock state for UI display."""

    held: bool
    owner: str | None = None
    pid: int | None = None
    started_at: str | None = None  # ISO-8601 string for easy display


@dataclass(frozen=True)
class _HeldLock:
    path: Path
    pid: int
    thread_id: int
    fd: int
    device: int
    inode: int


_held_locks: dict[tuple[Path, int], list[_HeldLock]] = {}
_held_locks_guard = threading.RLock()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _try_lock(fd: int) -> bool:
    """Non-blocking exclusive lock attempt. Returns True on success."""
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False


def _block_lock(fd: int) -> None:
    fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError as exc:
        log.warning("lock_release_failed", platform="posix", error=str(exc))


def _write_owner_metadata(path: Path, owner: str) -> None:
    """Record best-effort holder metadata (pid + start time) so the UI
    can surface a useful banner. Failures here never fail the lock —
    the metadata is decorative."""
    try:
        meta = {
            "owner": owner,
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        log.exception(
            "lock_owner_metadata_write_failed",
            meta_path=str(path),
            owner=owner,
            error_type=type(exc).__name__,
        )


def _read_owner_metadata(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cast(dict[str, Any], payload) if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _canonical_lock_path(lock_path: Path) -> Path:
    absolute = Path(os.path.abspath(lock_path))
    return absolute.parent.resolve(strict=True) / absolute.name


def _register_held_lock(path: Path, fd: int) -> _HeldLock:
    descriptor_stat = os.fstat(fd)
    path_stat = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(path_stat.st_mode)
        or (descriptor_stat.st_dev, descriptor_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino)
    ):
        raise RuntimeError(f"lock path identity changed before proof registration: {path}")
    proof = _HeldLock(
        path=path,
        pid=os.getpid(),
        thread_id=threading.get_ident(),
        fd=fd,
        device=descriptor_stat.st_dev,
        inode=descriptor_stat.st_ino,
    )
    key = (path, proof.thread_id)
    with _held_locks_guard:
        _held_locks.setdefault(key, []).append(proof)
    return proof


def _unregister_held_lock(proof: _HeldLock) -> None:
    key = (proof.path, proof.thread_id)
    with _held_locks_guard:
        registered = _held_locks.get(key)
        if registered is None:
            return
        try:
            registered.remove(proof)
        except ValueError:
            return
        if not registered:
            del _held_locks[key]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def acquire_lock(
    lock_path: Path,
    *,
    owner: str = "weekly_runner",
    blocking: bool = False,
    timeout: float | None = None,
) -> Iterator[None]:
    """Acquire the EIDP advisory lock.

    Parameters
    ----------
    lock_path :
        Path to the lock file. Created (and parent dirs) if missing.
        Convention: ``<APP_ROOT>/data/.lock``.
    owner :
        Short label written into the lock file's metadata sidecar so
        the UI can surface "weekly_runner is busy" or similar.
    blocking :
        If True, wait for the lock instead of raising. Defaults False.
    timeout :
        Optional upper bound for blocking acquisitions, in seconds.
        Implemented with a 200ms polling interval.

    Raises
    ------
    LockBusyError
        Non-blocking acquisition failed because another process holds
        the lock.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path = _canonical_lock_path(lock_path)
    meta_path = canonical_path.with_suffix(canonical_path.suffix + ".meta")

    fd = os.open(
        canonical_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    acquired = False
    proof: _HeldLock | None = None
    try:
        if blocking:
            if timeout is None:
                _block_lock(fd)
                acquired = True
            else:
                # Implement timed blocking via a polling loop so we don't
                # rely on platform-specific timed-lock semantics.
                import time
                deadline = time.monotonic() + timeout
                while True:
                    if _try_lock(fd):
                        acquired = True
                        break
                    if time.monotonic() >= deadline:
                        raise LockBusyError(
                            f"could not acquire {lock_path} within {timeout}s"
                        )
                    time.sleep(0.2)
        else:
            if not _try_lock(fd):
                meta = _read_owner_metadata(meta_path) or {}
                raise LockBusyError(
                    f"{canonical_path} held by {meta.get('owner', 'unknown')} "
                    f"pid={meta.get('pid')} since {meta.get('started_at')}"
                )
            acquired = True

        proof = _register_held_lock(canonical_path, fd)
        _write_owner_metadata(meta_path, owner)
        try:
            yield
        finally:
            # Clear metadata first; the lock release will let any
            # waiter wake up and find a clean meta file.
            try:
                meta_path.unlink(missing_ok=True)
            except OSError as exc:
                log.exception(
                    "lock_owner_metadata_unlink_failed",
                    meta_path=str(meta_path),
                    owner=owner,
                    error_type=type(exc).__name__,
                )
    finally:
        if proof is not None:
            _unregister_held_lock(proof)
        if acquired:
            _unlock(fd)
        os.close(fd)


def require_lock_held(lock_path: Path) -> None:
    """Require a live lock proof owned by this process and current thread."""

    try:
        canonical_path = _canonical_lock_path(lock_path)
    except OSError as exc:
        raise RuntimeError(f"lock is not held; path is unavailable: {lock_path}") from exc
    thread_id = threading.get_ident()
    with _held_locks_guard:
        registered = tuple(_held_locks.get((canonical_path, thread_id), ()))
    if not registered:
        raise RuntimeError(f"lock is not held by the current thread: {canonical_path}")

    proof = registered[-1]
    if proof.pid != os.getpid() or proof.thread_id != thread_id:
        raise RuntimeError(f"lock proof process or thread identity mismatch: {canonical_path}")
    try:
        descriptor_stat = os.fstat(proof.fd)
    except OSError as exc:
        raise RuntimeError(f"lock proof descriptor is no longer live: {canonical_path}") from exc
    try:
        path_stat = os.stat(canonical_path, follow_symlinks=False)
    except OSError as exc:
        raise RuntimeError(f"lock path is unavailable for identity proof: {canonical_path}") from exc
    if (
        not stat.S_ISREG(path_stat.st_mode)
        or (descriptor_stat.st_dev, descriptor_stat.st_ino) != (proof.device, proof.inode)
        or (path_stat.st_dev, path_stat.st_ino) != (proof.device, proof.inode)
    ):
        raise RuntimeError(f"lock path or descriptor identity mismatch: {canonical_path}")


def probe_lock(lock_path: Path) -> LockStatus:
    """Non-mutating check used by the Streamlit UI.

    Returns ``LockStatus(held=True, owner=...)`` if the lock is
    currently held, ``LockStatus(held=False)`` otherwise. Never
    raises — the UI must always be able to display *something*.
    """
    if not lock_path.exists():
        return LockStatus(held=False)

    fd = os.open(str(lock_path), os.O_RDWR)
    try:
        # Try the lock non-blocking — if we get it, nothing was holding
        # it. We must release it immediately so the legitimate holder
        # can re-acquire on its next attempt.
        acquired = _try_lock(fd)
        if acquired:
            _unlock(fd)
            return LockStatus(held=False)
    finally:
        os.close(fd)

    meta_path = lock_path.with_suffix(lock_path.suffix + ".meta")
    meta = _read_owner_metadata(meta_path) or {}
    return LockStatus(
        held=True,
        owner=meta.get("owner"),
        pid=meta.get("pid"),
        started_at=meta.get("started_at"),
    )
