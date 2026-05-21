"""Sprint 8.4.b — cross-process advisory lock regression.

Owner-pinned contract:

  * Non-blocking acquire fails fast with LockBusyError when another
    holder is alive (weekly runner busy → UI must see ``held=True``).
  * Holder writes meta sidecar (owner / pid / started_at) so the UI
    can render a useful banner.
  * Lock release on context-exit and on process crash (the OS-level
    file lock is dropped when the fd is closed).
  * probe_lock() is non-mutating: calling it does not steal the lock
    from the legitimate holder.

We test the POSIX side directly. Windows side compiles via the same
import path (msvcrt) but the test infrastructure here runs on macOS
CI; the Windows regression lives in 8.5 packaging spike where a real
Win VM is in scope.
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from pathlib import Path

import pytest

from eidp.db.locking import LockBusyError, acquire_lock, probe_lock

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-side regression; Windows path validated in 8.5 VM spike",
)


def test_acquire_lock_basic_round_trip(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with acquire_lock(lock_path, owner="weekly_runner"):
        # While held the lock file exists.
        assert lock_path.exists()
        meta = lock_path.with_suffix(lock_path.suffix + ".meta")
        assert meta.exists()
        # And probe sees it as held by us.
        status = probe_lock(lock_path)
        assert status.held is True
        assert status.owner == "weekly_runner"
        assert status.pid == os.getpid()
    # After release, probe sees it free.
    status = probe_lock(lock_path)
    assert status.held is False


def _worker_acquire(lock_path: str, ready_event, release_event) -> None:
    """Hold the lock until release_event is set."""
    from eidp.db.locking import acquire_lock as _acq
    with _acq(Path(lock_path), owner="other_proc"):
        ready_event.set()
        # Wait until the test signals us to release.
        release_event.wait(timeout=10)


def test_acquire_lock_fails_when_another_process_holds_it(tmp_path: Path):
    """The headline contract: non-blocking acquire raises LockBusyError
    while another process holds the lock, and probe sees it as held."""
    lock_path = tmp_path / ".lock"

    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    release_event = ctx.Event()
    proc = ctx.Process(
        target=_worker_acquire,
        args=(str(lock_path), ready_event, release_event),
    )
    proc.start()
    try:
        # Wait until worker has acquired the lock.
        assert ready_event.wait(timeout=5), "worker process never acquired lock"

        # UI-side probe must see it.
        status = probe_lock(lock_path)
        assert status.held is True, status
        assert status.owner == "other_proc"
        assert status.pid == proc.pid

        # Non-blocking acquire from this process must fail fast.
        with pytest.raises(LockBusyError, match="other_proc"):
            with acquire_lock(lock_path, owner="ui"):  # pragma: no cover - body must not run
                pass

    finally:
        release_event.set()
        proc.join(timeout=5)
        if proc.is_alive():  # pragma: no cover
            proc.terminate()


def test_lock_releases_on_context_exit(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with acquire_lock(lock_path, owner="A"):
        pass
    # We can re-acquire immediately.
    with acquire_lock(lock_path, owner="B"):
        status = probe_lock(lock_path)
        assert status.owner == "B"


def test_probe_returns_unheld_when_no_lock_file(tmp_path: Path):
    lock_path = tmp_path / "nope.lock"
    status = probe_lock(lock_path)
    assert status.held is False
    assert status.owner is None


def test_lock_releases_when_holder_process_dies(tmp_path: Path):
    """If the holder crashes, the OS drops the fcntl lock and a
    subsequent acquire from a different process succeeds. This is the
    "stale lock recovery" property — we don't need to manually delete
    the file."""
    lock_path = tmp_path / ".lock"

    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    # Set release_event from the start so the worker exits immediately
    # after acquiring — emulating a fast crash.
    release_event = ctx.Event()
    release_event.set()
    proc = ctx.Process(
        target=_worker_acquire,
        args=(str(lock_path), ready_event, release_event),
    )
    proc.start()
    proc.join(timeout=5)
    assert proc.exitcode == 0

    # The file may still exist, but the OS-level lock is gone.
    # We can grab it ourselves.
    with acquire_lock(lock_path, owner="recovery"):
        status = probe_lock(lock_path)
        assert status.owner == "recovery"


def test_blocking_with_timeout_raises_on_deadline(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    release_event = ctx.Event()
    proc = ctx.Process(
        target=_worker_acquire,
        args=(str(lock_path), ready_event, release_event),
    )
    proc.start()
    try:
        assert ready_event.wait(timeout=5)
        start = time.monotonic()
        with pytest.raises(LockBusyError, match="within"):
            with acquire_lock(lock_path, owner="ui", blocking=True, timeout=0.5):
                pass
        elapsed = time.monotonic() - start
        # Sanity: we waited roughly the timeout, not 0s and not forever.
        assert 0.4 <= elapsed <= 5.0, elapsed
    finally:
        release_event.set()
        proc.join(timeout=5)


def test_probe_does_not_steal_lock_from_holder(tmp_path: Path):
    """Calling probe_lock while another process holds the lock must
    NOT release that process's lock. Regression for the temptation to
    skip the immediate re-unlock inside probe_lock()."""
    lock_path = tmp_path / ".lock"
    ctx = multiprocessing.get_context("spawn")
    ready_event = ctx.Event()
    release_event = ctx.Event()
    proc = ctx.Process(
        target=_worker_acquire,
        args=(str(lock_path), ready_event, release_event),
    )
    proc.start()
    try:
        assert ready_event.wait(timeout=5)
        # Probe many times — must stay held throughout.
        for _ in range(5):
            status = probe_lock(lock_path)
            assert status.held is True, "probe accidentally released the held lock"
        # And we still cannot acquire.
        with pytest.raises(LockBusyError):
            with acquire_lock(lock_path):
                pass
    finally:
        release_event.set()
        proc.join(timeout=5)


def test_unlock_logs_release_failures(monkeypatch):
    """Unlock errors are diagnostic evidence and must not disappear silently."""
    from eidp.db import locking

    calls: list[tuple[str, dict[str, str]]] = []

    class FakeLog:
        def warning(self, event: str, **kwargs: str) -> None:
            calls.append((event, kwargs))

    def fail_unlock(fd: int, flags: int) -> None:
        assert fd == 123
        assert flags == locking.fcntl.LOCK_UN
        raise OSError("unlock failed")

    monkeypatch.setattr(locking, "log", FakeLog())
    monkeypatch.setattr(locking.fcntl, "flock", fail_unlock)

    locking._unlock(123)

    assert calls == [
        (
            "lock_release_failed",
            {"platform": "posix", "error": "unlock failed"},
        ),
    ]


def test_owner_metadata_write_failure_is_logged(tmp_path: Path, monkeypatch):
    """Metadata is best-effort, but failure must leave diagnostic evidence."""
    from eidp.db import locking

    calls: list[tuple[str, dict[str, str]]] = []
    meta_path = tmp_path / ".lock.meta"

    class FakeLog:
        def exception(self, event: str, **kwargs: str) -> None:
            calls.append((event, kwargs))

    def fail_write_text(path: Path, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        assert path == meta_path
        raise OSError("metadata write failed")

    monkeypatch.setattr(locking, "log", FakeLog())
    monkeypatch.setattr(Path, "write_text", fail_write_text)

    locking._write_owner_metadata(meta_path, "weekly_runner")

    assert calls == [
        (
            "lock_owner_metadata_write_failed",
            {
                "meta_path": str(meta_path),
                "owner": "weekly_runner",
                "error_type": "OSError",
            },
        )
    ]


def test_owner_metadata_unlink_failure_is_logged(tmp_path: Path, monkeypatch):
    """Stale sidecar cleanup failures must not disappear silently."""
    from eidp.db import locking

    calls: list[tuple[str, dict[str, str]]] = []
    lock_path = tmp_path / ".lock"
    meta_path = lock_path.with_suffix(lock_path.suffix + ".meta")

    class FakeLog:
        def exception(self, event: str, **kwargs: str) -> None:
            calls.append((event, kwargs))

    original_unlink = Path.unlink

    def fail_meta_unlink(path: Path, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        if path == meta_path:
            raise OSError("metadata unlink failed")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(locking, "log", FakeLog())
    monkeypatch.setattr(Path, "unlink", fail_meta_unlink)

    with acquire_lock(lock_path, owner="weekly_runner"):
        assert meta_path.exists()

    assert calls == [
        (
            "lock_owner_metadata_unlink_failed",
            {
                "meta_path": str(meta_path),
                "owner": "weekly_runner",
                "error_type": "OSError",
            },
        )
    ]
