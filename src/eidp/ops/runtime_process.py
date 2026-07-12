"""Secure process lifecycle primitives for the EIDP Linux Web runtime."""

from __future__ import annotations

import fcntl
import http.client
import json
import os
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from eidp.ops.runtime_config import RuntimeLaunchConfig, sanitized_child_env

RUNNER_ARGV_MARKER = "eidp.ops.rotating_runner"
LOOPBACK_ADDRESS = "127.0.0.1"
PID_FILE_RELATIVE = Path("run/eidp.pid.json")
LOCK_FILE_RELATIVE = Path("run/eidpctl.lock")
WEB_LOG_RELATIVE = Path("logs/web.log")
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class ProcessIdentityError(RuntimeError):
    """A live PID does not match the project-local supervisor identity."""


class ControllerError(RuntimeError):
    """An operator-facing controller operation failed safely."""


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    linux_start_time: str
    app_root: str
    argv_marker: str


@dataclass(frozen=True)
class _RuntimeProcessRecord:
    identity: ProcessIdentity
    address: str
    port: int
    base_url_path: str


def _identity_error(message: str) -> ProcessIdentityError:
    return ProcessIdentityError(f"identity mismatch: {message}")


def _open_relative_directory(app_root: Path, relative: Path, *, create: bool) -> int:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ControllerError(f"unsafe project-local directory: {relative}")
    try:
        descriptor = os.open(app_root, _DIRECTORY_FLAGS | _NOFOLLOW)
    except OSError as exc:
        raise ControllerError(f"unsafe project root: {app_root}: {exc}") from exc
    try:
        for component in relative.parts:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            try:
                next_descriptor = os.open(
                    component,
                    _DIRECTORY_FLAGS | _NOFOLLOW,
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise ControllerError(
                    f"unsafe project-local directory or symlink: {relative}: {exc}"
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
            if create:
                os.fchmod(descriptor, 0o700)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _pid_location(pid_file: Path) -> tuple[Path, str]:
    absolute = Path(os.path.abspath(pid_file))
    if absolute.parent.name != "run":
        raise _identity_error("PID metadata must live directly below run/")
    return absolute.parent.parent, absolute.name


def _read_pid_payload(pid_file: Path) -> dict[str, object] | None:
    app_root, name = _pid_location(pid_file)
    directory_fd = _open_relative_directory(app_root, Path("run"), create=True)
    descriptor = -1
    try:
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_fd,
            )
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise _identity_error(f"PID metadata is an unsafe symlink: {exc}") from exc
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise _identity_error("PID metadata must be a regular file")
        with os.fdopen(descriptor, encoding="utf-8") as stream:
            descriptor = -1
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _identity_error(f"cannot read PID metadata: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(directory_fd)
    if not isinstance(payload, dict):
        raise _identity_error("PID metadata must be a JSON object")
    return payload


def _identity_from_payload(payload: dict[str, object]) -> ProcessIdentity:
    pid = payload.get("pid")
    linux_start_time = payload.get("linux_start_time")
    app_root = payload.get("app_root")
    argv_marker = payload.get("argv_marker")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1:
        raise _identity_error("PID metadata has an invalid pid")
    if not isinstance(linux_start_time, str) or not linux_start_time:
        raise _identity_error("PID metadata has an invalid Linux start time")
    if not isinstance(app_root, str) or not app_root:
        raise _identity_error("PID metadata has an invalid app root")
    if not isinstance(argv_marker, str) or not argv_marker:
        raise _identity_error("PID metadata has an invalid argv marker")
    return ProcessIdentity(
        pid=pid,
        linux_start_time=linux_start_time,
        app_root=app_root,
        argv_marker=argv_marker,
    )


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError as exc:
        raise _identity_error(f"permission denied probing pid {pid}") from exc
    return True


def _linux_process_snapshot(pid: int) -> tuple[str, tuple[str, ...], Path] | None:
    if sys.platform != "linux":
        raise _identity_error("Linux /proc is required for live process verification")
    proc_root = Path("/proc") / str(pid)
    try:
        stat_body = (proc_root / "stat").read_text(encoding="utf-8")
        command_bytes = (proc_root / "cmdline").read_bytes()
        cwd = (proc_root / "cwd").resolve(strict=True)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise _identity_error(f"cannot inspect /proc/{pid}: {exc}") from exc

    closing_parenthesis = stat_body.rfind(")")
    fields = stat_body[closing_parenthesis + 2 :].split() if closing_parenthesis >= 0 else []
    if len(fields) <= 19:
        raise _identity_error(f"/proc/{pid}/stat is malformed")
    if fields[0] == "Z":
        return None
    try:
        argv = tuple(part.decode("utf-8") for part in command_bytes.split(b"\0") if part)
    except UnicodeDecodeError as exc:
        raise _identity_error(f"/proc/{pid}/cmdline is not UTF-8") from exc
    return fields[19], argv, cwd


def _verify_live_identity(identity: ProcessIdentity, *, app_root: Path) -> ProcessIdentity | None:
    expected_root = app_root.resolve(strict=True)
    try:
        recorded_root = Path(identity.app_root).resolve(strict=True)
    except OSError as exc:
        raise _identity_error(f"recorded app root is invalid: {exc}") from exc
    if recorded_root != expected_root:
        raise _identity_error("recorded app root differs from the requested app root")
    if identity.argv_marker != RUNNER_ARGV_MARKER:
        raise _identity_error("recorded argv marker is not the EIDP supervisor marker")
    if not _process_exists(identity.pid):
        return None

    snapshot = _linux_process_snapshot(identity.pid)
    if snapshot is None:
        return None
    live_start_time, argv, live_cwd = snapshot
    if live_start_time != identity.linux_start_time:
        raise _identity_error("Linux process start time changed")
    if live_cwd != expected_root:
        raise _identity_error("live process app root changed")
    if identity.argv_marker not in argv:
        raise _identity_error("live process argv marker changed")
    return identity


def read_verified_process(pid_file: Path, *, app_root: Path) -> ProcessIdentity | None:
    """Return None for a dead PID; raise ProcessIdentityError for a live mismatch."""

    payload = _read_pid_payload(pid_file)
    return None if payload is None else _verify_live_identity(_identity_from_payload(payload), app_root=app_root)


def _record_from_payload(payload: dict[str, object], identity: ProcessIdentity) -> _RuntimeProcessRecord:
    address = payload.get("address")
    port = payload.get("port")
    base_url_path = payload.get("base_url_path")
    if address != LOOPBACK_ADDRESS:
        raise _identity_error("PID metadata has an invalid loopback address")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise _identity_error("PID metadata has an invalid port")
    if not isinstance(base_url_path, str):
        raise _identity_error("PID metadata has an invalid base URL path")
    return _RuntimeProcessRecord(
        identity=identity,
        address=address,
        port=port,
        base_url_path=base_url_path,
    )


def _read_verified_record(pid_file: Path, *, app_root: Path) -> _RuntimeProcessRecord | None:
    identity = read_verified_process(pid_file, app_root=app_root)
    if identity is None:
        return None
    payload = _read_pid_payload(pid_file)
    if payload is None:
        return None
    refreshed_identity = _identity_from_payload(payload)
    if refreshed_identity != identity:
        raise _identity_error("PID metadata changed during verification")
    return _record_from_payload(payload, identity)


def _write_record(pid_file: Path, record: _RuntimeProcessRecord) -> None:
    app_root, name = _pid_location(pid_file)
    directory_fd = _open_relative_directory(app_root, Path("run"), create=True)
    temporary_name = f".eidp.pid.{secrets.token_hex(8)}.tmp"
    payload = {
        "pid": record.identity.pid,
        "linux_start_time": record.identity.linux_start_time,
        "app_root": record.identity.app_root,
        "argv_marker": record.identity.argv_marker,
        "address": record.address,
        "port": record.port,
        "base_url_path": record.base_url_path,
    }
    encoded = (json.dumps(payload, sort_keys=True) + "\n").encode()
    descriptor = -1
    try:
        try:
            existing = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise _identity_error("PID metadata final path is an unsafe symlink")
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        written = 0
        while written < len(encoded):
            written += os.write(descriptor, encoded[written:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(
            temporary_name,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)


def _remove_stale_pid_file(pid_file: Path) -> None:
    app_root, name = _pid_location(pid_file)
    directory_fd = _open_relative_directory(app_root, Path("run"), create=True)
    try:
        try:
            existing = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(existing.st_mode):
            raise _identity_error("PID metadata must not be a symlink")
        os.unlink(name, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


@contextmanager
def _controller_lock(app_root: Path) -> Iterator[None]:
    directory_fd = _open_relative_directory(app_root, LOCK_FILE_RELATIVE.parent, create=True)
    try:
        descriptor = os.open(
            LOCK_FILE_RELATIVE.name,
            os.O_RDWR | os.O_CREAT | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
    except OSError as exc:
        os.close(directory_fd)
        raise ControllerError(f"unsafe controller lock file or symlink: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ControllerError("unsafe controller lock file")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        os.close(directory_fd)


def _require_available_port(address: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((address, port))
        except OSError as exc:
            raise ControllerError(f"loopback port {port} is occupied or unavailable: {exc}") from exc


def _capture_identity(pid: int, app_root: Path, *, timeout: float = 2.0) -> ProcessIdentity:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            raise ControllerError("rotating supervisor exited before its identity could be recorded")
        snapshot = _linux_process_snapshot(pid)
        if snapshot is not None:
            linux_start_time, argv, cwd = snapshot
            if RUNNER_ARGV_MARKER in argv and cwd == app_root:
                return ProcessIdentity(
                    pid=pid,
                    linux_start_time=linux_start_time,
                    app_root=str(app_root),
                    argv_marker=RUNNER_ARGV_MARKER,
                )
        time.sleep(0.02)
    raise ControllerError("rotating supervisor identity did not become verifiable")


def _health_url(record: _RuntimeProcessRecord) -> str:
    base_path = record.base_url_path.rstrip("/")
    return f"http://{record.address}:{record.port}{base_path}/_stcore/health"


def _probe_health(record: _RuntimeProcessRecord, *, timeout: float) -> bool:
    connection = http.client.HTTPConnection(record.address, record.port, timeout=timeout)
    try:
        base_path = record.base_url_path.rstrip("/")
        connection.request("GET", f"{base_path}/_stcore/health")
        return connection.getresponse().status == 200
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def _wait_for_health(
    pid_file: Path,
    *,
    app_root: Path,
    record: _RuntimeProcessRecord,
    timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        verified = _read_verified_record(pid_file, app_root=app_root)
        if verified is None:
            raise ControllerError("rotating supervisor exited before Web health became ready")
        remaining = deadline - time.monotonic()
        if _probe_health(record, timeout=max(0.01, min(0.2, remaining))):
            return
        time.sleep(min(0.05, max(0.0, remaining)))
    raise ControllerError(f"health check timed out after {timeout:g}s")


def _pidfd_open(pid: int) -> int | None:
    if sys.platform != "linux":
        return None
    opener = getattr(os, "pidfd_open", None)
    if opener is None:
        raise ControllerError("Linux pidfd_open is required for safe process control")
    try:
        return int(opener(pid, 0))
    except ProcessLookupError:
        return None


def _pidfd_send_signal(pidfd: int, signum: signal.Signals) -> None:
    sender = getattr(signal, "pidfd_send_signal", None)
    if sender is None:
        raise ControllerError("Linux pidfd_send_signal is required for safe process control")
    sender(pidfd, int(signum), None, 0)


def _pidfd_close(pidfd: int) -> None:
    os.close(pidfd)


def _signal_verified_process_group(
    pid_file: Path | None,
    *,
    app_root: Path,
    expected: ProcessIdentity,
    signum: signal.Signals,
) -> ProcessIdentity | None:
    pidfd = _pidfd_open(expected.pid)
    if sys.platform == "linux" and pidfd is None:
        return None
    try:
        identity = (
            read_verified_process(pid_file, app_root=app_root)
            if pid_file is not None
            else _verify_live_identity(expected, app_root=app_root)
        )
        if identity is None:
            return None
        if identity != expected:
            raise _identity_error("supervisor identity changed before signal")
        try:
            process_group = os.getpgid(identity.pid)
            session = os.getsid(identity.pid)
        except ProcessLookupError:
            return None
        if process_group != identity.pid:
            raise _identity_error("supervisor process group changed before signal")
        if session != identity.pid:
            raise _identity_error("supervisor session changed before signal")

        if signum in {signal.SIGTERM, signal.SIGINT} and pidfd is not None:
            _pidfd_send_signal(pidfd, signum)
        else:
            os.killpg(identity.pid, signum)
        return identity
    except ProcessLookupError:
        return None
    finally:
        if pidfd is not None:
            _pidfd_close(pidfd)


def _wait_until_dead(pid_file: Path, *, app_root: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if read_verified_process(pid_file, app_root=app_root) is None:
            return True
        time.sleep(0.05)
    return read_verified_process(pid_file, app_root=app_root) is None


def _wait_for_port_release(address: str, port: int, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((address, port))
            except OSError:
                available = False
            else:
                available = True
        if available:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def _stop(app_root: Path, *, timeout: float, quiet: bool = False) -> None:
    if timeout <= 0:
        raise ControllerError("stop timeout must be positive")
    pid_file = app_root / PID_FILE_RELATIVE
    record = _read_verified_record(pid_file, app_root=app_root)
    if record is None:
        _remove_stale_pid_file(pid_file)
        if not quiet:
            print("EIDP Web is not running")
        return

    identity = record.identity
    _signal_verified_process_group(
        pid_file,
        app_root=app_root,
        expected=identity,
        signum=signal.SIGTERM,
    )
    if not _wait_until_dead(pid_file, app_root=app_root, timeout=timeout):
        _signal_verified_process_group(
            pid_file,
            app_root=app_root,
            expected=identity,
            signum=signal.SIGKILL,
        )
        if not _wait_until_dead(pid_file, app_root=app_root, timeout=2.0):
            raise ControllerError(f"supervisor pid {identity.pid} did not stop")
    if not _wait_for_port_release(record.address, record.port, timeout=2.0):
        raise ControllerError(f"loopback port {record.port} remained occupied after stop")
    _remove_stale_pid_file(pid_file)
    if not quiet:
        print(f"EIDP Web stopped (pid {identity.pid})")


def _terminate_failed_start(
    app_root: Path,
    pid_file: Path,
    process: subprocess.Popen[bytes],
    *,
    captured_identity: ProcessIdentity | None = None,
) -> None:
    if _read_pid_payload(pid_file) is not None:
        _stop(app_root, timeout=3.0, quiet=True)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise ControllerError("verified failed-start supervisor did not become reapable") from exc
        return
    if captured_identity is not None:
        _signal_verified_process_group(
            None,
            app_root=app_root,
            expected=captured_identity,
            signum=signal.SIGTERM,
        )
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            _signal_verified_process_group(
                None,
                app_root=app_root,
                expected=captured_identity,
                signum=signal.SIGKILL,
            )
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired as exc:
                raise ControllerError("captured failed-start supervisor did not stop") from exc
        return
    if process.poll() is None:
        raise ControllerError("unverified failed-start supervisor remains live; refusing direct kill")


def _start(app_root: Path, config: RuntimeLaunchConfig, *, health_timeout: float) -> None:
    if health_timeout <= 0:
        raise ControllerError("health timeout must be positive")
    pid_file = app_root / PID_FILE_RELATIVE
    existing = read_verified_process(pid_file, app_root=app_root)
    if existing is not None:
        raise ControllerError(f"EIDP Web is already running (pid {existing.pid})")
    _remove_stale_pid_file(pid_file)
    _require_available_port(LOOPBACK_ADDRESS, config.port)

    launcher = app_root / "deploy" / "linux" / "run_web.sh"
    if not launcher.is_file() or launcher.is_symlink():
        raise ControllerError(f"Web launcher is missing or unsafe: {launcher}")

    child_env = sanitized_child_env(os.environ, config)
    child_env["EIDP_APP_ROOT"] = str(app_root)
    command = [
        sys.executable,
        "-m",
        RUNNER_ARGV_MARKER,
        "--log-path",
        str(app_root / WEB_LOG_RELATIVE),
        "--",
        str(launcher),
    ]
    process = subprocess.Popen(
        command,
        cwd=app_root,
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    captured_identity: ProcessIdentity | None = None
    try:
        captured_identity = _capture_identity(process.pid, app_root)
        record = _RuntimeProcessRecord(
            identity=captured_identity,
            address=LOOPBACK_ADDRESS,
            port=config.port,
            base_url_path=config.base_url_path,
        )
        _write_record(pid_file, record)
        _wait_for_health(
            pid_file,
            app_root=app_root,
            record=record,
            timeout=health_timeout,
        )
    except Exception:
        _terminate_failed_start(
            app_root,
            pid_file,
            process,
            captured_identity=captured_identity,
        )
        raise
    print(f"EIDP Web started (pid {process.pid}, {LOOPBACK_ADDRESS}:{config.port})")


def _status(app_root: Path, *, as_json: bool) -> int:
    pid_file = app_root / PID_FILE_RELATIVE
    record = _read_verified_record(pid_file, app_root=app_root)
    if record is None:
        _remove_stale_pid_file(pid_file)
        payload = {"running": False, "address": LOOPBACK_ADDRESS, "port": None}
        if as_json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"EIDP Web is not running ({LOOPBACK_ADDRESS}, port unknown)")
        return 3

    payload = {
        "running": True,
        "pid": record.identity.pid,
        "address": record.address,
        "port": record.port,
    }
    if as_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"EIDP Web is running (pid {record.identity.pid}, {record.address}:{record.port})")
    return 0


def _health(app_root: Path, *, timeout: float) -> None:
    if timeout <= 0:
        raise ControllerError("health timeout must be positive")
    record = _read_verified_record(app_root / PID_FILE_RELATIVE, app_root=app_root)
    if record is None:
        raise ControllerError("EIDP Web is not running")
    if not _probe_health(record, timeout=timeout):
        raise ControllerError(f"EIDP Web health check failed: {_health_url(record)}")
    print(f"healthy: {_health_url(record)}")
