from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest


def _runner_module() -> ModuleType:
    try:
        return importlib.import_module("eidp.ops.rotating_runner")
    except ModuleNotFoundError as exc:
        pytest.fail(f"rotating runner module is missing: {exc}")


def _wait_for_path(path: Path, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    pytest.fail(f"timed out waiting for {path}")


def _open_fd_count() -> int:
    fd_root = Path("/proc/self/fd") if Path("/proc/self/fd").is_dir() else Path("/dev/fd")
    return len(tuple(fd_root.iterdir()))


def test_run_rotating_exposes_bounded_production_defaults() -> None:
    signature = inspect.signature(_runner_module().run_rotating)

    assert signature.parameters["max_bytes"].default == 10 * 1024 * 1024
    assert signature.parameters["backups"].default == 5


def test_run_rotating_combines_output_and_returns_child_exit_code(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "web.log"
    child = (
        "import sys; "
        "print('from-stdout', flush=True); "
        "print('from-stderr', file=sys.stderr, flush=True); "
        "raise SystemExit(7)"
    )

    result = _runner_module().run_rotating(
        [sys.executable, "-c", child],
        log_path=log_path,
    )

    assert result == 7
    assert log_path.read_text(encoding="utf-8").splitlines() == ["from-stdout", "from-stderr"]


def test_run_rotating_bounds_current_log_and_retained_backups(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "web.log"
    child = "for index in range(40): print(f'line-{index:02d}-' + 'x' * 32, flush=True)"

    result = _runner_module().run_rotating(
        [sys.executable, "-c", child],
        log_path=log_path,
        max_bytes=96,
        backups=2,
    )

    retained = [log_path, log_path.with_name("web.log.1"), log_path.with_name("web.log.2")]
    assert result == 0
    assert all(path.exists() for path in retained)
    assert all(0 < path.stat().st_size <= 96 for path in retained)
    assert not log_path.with_name("web.log.3").exists()
    assert "line-39" in "".join(path.read_text(encoding="utf-8") for path in retained)


def test_run_rotating_refuses_a_symlink_log_file(tmp_path: Path) -> None:
    outside = tmp_path / "outside.log"
    outside.write_text("must stay unchanged\n", encoding="utf-8")
    log_path = tmp_path / "web.log"
    log_path.symlink_to(outside)

    before = _open_fd_count()
    with pytest.raises(OSError):
        _runner_module().run_rotating(
            [sys.executable, "-c", "print('must not escape')"],
            log_path=log_path,
        )

    assert outside.read_text(encoding="utf-8") == "must stay unchanged\n"
    assert _open_fd_count() == before


def test_run_rotating_refuses_a_symlink_log_parent(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    logs = tmp_path / "logs"
    logs.symlink_to(outside, target_is_directory=True)

    with pytest.raises(OSError):
        _runner_module().run_rotating(
            [sys.executable, "-c", "print('must not escape')"],
            log_path=logs / "web.log",
        )

    assert not (outside / "web.log").exists()


def test_run_rotating_closes_log_dirfd_when_child_spawn_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _runner_module()

    def fail_spawn(*_args: object, **_kwargs: object) -> None:
        raise OSError("controlled spawn failure")

    monkeypatch.setattr(runner.subprocess, "Popen", fail_spawn)
    before = _open_fd_count()

    with pytest.raises(OSError, match="controlled spawn failure"):
        runner.run_rotating([sys.executable, "-c", "pass"], log_path=tmp_path / "web.log")

    assert _open_fd_count() == before


@pytest.mark.parametrize("forwarded_signal", (signal.SIGTERM, signal.SIGINT))
def test_run_rotating_forwards_term_and_int_to_child(
    tmp_path: Path,
    forwarded_signal: signal.Signals,
) -> None:
    runner = _runner_module()
    child_pid_path = tmp_path / "child.pid"
    forwarded_path = tmp_path / "forwarded.txt"
    log_path = tmp_path / "web.log"
    child_code = "\n".join(
        (
            "import os",
            "import signal",
            "from pathlib import Path",
            "pid_path = Path(os.environ['CHILD_PID_PATH'])",
            "forwarded_path = Path(os.environ['FORWARDED_PATH'])",
            "def handle(signum, _frame):",
            "    forwarded_path.write_text(str(signum), encoding='utf-8')",
            "    raise SystemExit(128 + signum)",
            "signal.signal(signal.SIGTERM, handle)",
            "signal.signal(signal.SIGINT, handle)",
            "pid_path.write_text(str(os.getpid()), encoding='utf-8')",
            "signal.pause()",
        )
    )
    supervisor_code = "\n".join(
        (
            "import sys",
            "from pathlib import Path",
            "from eidp.ops.rotating_runner import run_rotating",
            "raise SystemExit(run_rotating(sys.argv[2:], log_path=Path(sys.argv[1])))",
        )
    )
    env = os.environ.copy()
    env.update(
        {
            "CHILD_PID_PATH": str(child_pid_path),
            "FORWARDED_PATH": str(forwarded_path),
        }
    )
    supervisor = subprocess.Popen(
        [sys.executable, "-c", supervisor_code, str(log_path), sys.executable, "-c", child_code],
        env=env,
        start_new_session=True,
    )

    try:
        _wait_for_path(child_pid_path)
        os.kill(supervisor.pid, forwarded_signal)
        returncode = supervisor.wait(timeout=5)
        _wait_for_path(forwarded_path)

        assert returncode == 128 + forwarded_signal
        assert forwarded_path.read_text(encoding="utf-8") == str(forwarded_signal)
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=5)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(supervisor.pid, signal.SIGKILL)
        if child_pid_path.exists():
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
            with contextlib.suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)

    assert runner.run_rotating is not None
