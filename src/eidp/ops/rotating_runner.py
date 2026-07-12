"""Small rotating-output supervisor for the Linux Web process."""

from __future__ import annotations

import argparse
import contextlib
import errno
import os
import signal
import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _open_secure_directory(directory: Path) -> int:
    absolute = Path(os.path.abspath(directory))
    descriptor = os.open(absolute.anchor, _DIRECTORY_FLAGS)
    try:
        for component in absolute.parts[1:]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            next_descriptor = os.open(component, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _require_regular_or_missing(directory_fd: int, name: str) -> None:
    try:
        file_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(file_stat.st_mode):
        raise OSError(errno.ELOOP, f"refusing unsafe log path: {name}")


def _rotate(directory_fd: int, log_name: str, backups: int) -> None:
    _require_regular_or_missing(directory_fd, log_name)
    if backups == 0:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(log_name, dir_fd=directory_fd)
        return

    oldest = f"{log_name}.{backups}"
    _require_regular_or_missing(directory_fd, oldest)
    with contextlib.suppress(FileNotFoundError):
        os.unlink(oldest, dir_fd=directory_fd)
    for number in range(backups - 1, 0, -1):
        source = f"{log_name}.{number}"
        destination = f"{log_name}.{number + 1}"
        _require_regular_or_missing(directory_fd, source)
        _require_regular_or_missing(directory_fd, destination)
        try:
            os.replace(source, destination, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        except FileNotFoundError:
            pass
    try:
        os.replace(log_name, f"{log_name}.1", src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
    except FileNotFoundError:
        pass


def _append_bounded(
    directory_fd: int,
    log_name: str,
    chunk: bytes,
    *,
    max_bytes: int,
    backups: int,
) -> None:
    remaining = memoryview(chunk)
    while remaining:
        _require_regular_or_missing(directory_fd, log_name)
        descriptor = os.open(
            log_name,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        try:
            current_size = os.fstat(descriptor).st_size
            if current_size >= max_bytes:
                os.close(descriptor)
                descriptor = -1
                _rotate(directory_fd, log_name, backups)
                continue
            write_size = min(len(remaining), max_bytes - current_size)
            written = 0
            while written < write_size:
                written += os.write(descriptor, remaining[written:write_size])
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        remaining = remaining[write_size:]


def run_rotating(
    command: Sequence[str],
    *,
    log_path: Path,
    max_bytes: int = 10 * 1024 * 1024,
    backups: int = 5,
) -> int:
    """Run one child, rotate its combined output, forward TERM/INT, return its exit code."""

    if not command:
        raise ValueError("command must not be empty")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if backups < 0:
        raise ValueError("backups must not be negative")

    log_directory_fd = _open_secure_directory(log_path.parent)
    log_name = log_path.name
    try:
        _require_regular_or_missing(log_directory_fd, log_name)
        child = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
    except Exception:
        os.close(log_directory_fd)
        raise
    def forward(signum: int, _frame: FrameType | None) -> None:
        if child.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                child.send_signal(signum)

    forwarded_signals = (signal.SIGTERM, signal.SIGINT)
    previous_handlers = {
        forwarded_signal: signal.getsignal(forwarded_signal) for forwarded_signal in forwarded_signals
    }
    try:
        for forwarded_signal in forwarded_signals:
            signal.signal(forwarded_signal, forward)

        if child.stdout is None:  # pragma: no cover - guaranteed by Popen arguments
            raise RuntimeError("child output pipe was not created")
        while chunk := child.stdout.read(64 * 1024):
            _append_bounded(
                log_directory_fd,
                log_name,
                chunk,
                max_bytes=max_bytes,
                backups=backups,
            )
        return child.wait()
    finally:
        for forwarded_signal, previous_handler in previous_handlers.items():
            signal.signal(forwarded_signal, previous_handler)
        if child.stdout is not None:
            child.stdout.close()
        if child.poll() is None:
            child.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(timeout=5)
            if child.poll() is None:
                child.kill()
                child.wait()
        os.close(log_directory_fd)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024)
    parser.add_argument("--backups", type=int, default=5)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the command-line supervisor."""

    parsed = _parser().parse_args(arguments)
    command: list[str] = parsed.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        _parser().error("a child command is required after --")
    return run_rotating(
        command,
        log_path=parsed.log_path,
        max_bytes=parsed.max_bytes,
        backups=parsed.backups,
    )


if __name__ == "__main__":
    raise SystemExit(main())
