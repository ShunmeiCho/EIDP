"""Cross-process advisory lock for the EIDP single-user Windows deploy.

Sprint 8.4.b. Provides a single advisory lock that the weekly runner
takes for the duration of its job, and that the Streamlit UI checks
before performing manual writes (manual_entry, fiscal_year_override,
Excel preview-and-export).

Design contract owner pinned in v6:

  * v1 = strict whole-job exclusion. Weekly runner holds the lock from
    start to finish; UI write paths refuse with a banner ("週次処理中、
    編集は一時停止") if they cannot acquire it. UI read paths run
    unimpeded.
  * Cross-platform — Windows is the production target (msvcrt.locking)
    but development is on macOS / Linux (fcntl.flock).
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
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# Cross-platform file-lock primitives.
if sys.platform == "win32":  # pragma: no cover — exercised in Windows VM tests
    import msvcrt
else:
    import fcntl


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


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _try_lock(fd: int) -> bool:
    """Non-blocking exclusive lock attempt. Returns True on success."""
    if sys.platform == "win32":  # pragma: no cover
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    else:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (BlockingIOError, OSError):
            return False


def _block_lock(fd: int) -> None:
    if sys.platform == "win32":  # pragma: no cover
        # msvcrt has no native blocking lock with retry; emulate via
        # short sleep loop. This path is rarely used (callers prefer
        # the non-blocking variant).
        import time
        while True:
            if _try_lock(fd):
                return
            time.sleep(0.2)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock(fd: int) -> None:
    if sys.platform == "win32":  # pragma: no cover
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


def _write_owner_metadata(path: Path, owner: str) -> None:
    """Record best-effort holder metadata (pid + start time) so the UI
    can surface a useful banner. Failures here never fail the lock —
    the metadata is decorative."""
    try:
        meta = {
            "owner": owner,
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _read_owner_metadata(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


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
        Currently advisory only on POSIX (fcntl) and ignored on
        Windows; the loop wakeup is 200ms.

    Raises
    ------
    LockBusyError
        Non-blocking acquisition failed because another process holds
        the lock.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = lock_path.with_suffix(lock_path.suffix + ".meta")

    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if blocking:
            if timeout is None:
                _block_lock(fd)
            else:
                # Implement timed blocking via a polling loop so we don't
                # rely on platform-specific timed-lock semantics.
                import time
                deadline = time.monotonic() + timeout
                while True:
                    if _try_lock(fd):
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
                    f"{lock_path} held by {meta.get('owner', 'unknown')} "
                    f"pid={meta.get('pid')} since {meta.get('started_at')}"
                )

        _write_owner_metadata(meta_path, owner)
        try:
            yield
        finally:
            # Clear metadata first; the lock release will let any
            # waiter wake up and find a clean meta file.
            try:
                meta_path.unlink(missing_ok=True)
            except OSError:
                pass
    finally:
        _unlock(fd)
        os.close(fd)


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
