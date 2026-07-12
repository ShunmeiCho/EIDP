"""Project-local command boundary for the EIDP Linux Web runtime."""

from __future__ import annotations

import argparse
import os
import secrets
import stat
import subprocess
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn

from eidp.ops.runtime_config import load_runtime_config
from eidp.ops.runtime_process import (
    ControllerError,
    ProcessIdentityError,
    _controller_lock,
    _health,
    _open_relative_directory,
    _start,
    _status,
    _stop,
)
from eidp.ops.runtime_process import (
    ProcessIdentity as ProcessIdentity,
)
from eidp.ops.runtime_process import (
    read_verified_process as read_verified_process,
)

_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _project_relative_path(raw_path: Path, *, app_root: Path) -> Path:
    candidate = raw_path if raw_path.is_absolute() else app_root / raw_path
    try:
        return Path(os.path.abspath(candidate)).relative_to(app_root)
    except ValueError as exc:
        raise ControllerError("import-excel path must remain inside the project root") from exc


def _open_project_regular_file(raw_path: Path, *, app_root: Path) -> int:
    relative = _project_relative_path(raw_path, app_root=app_root)
    if not relative.parts:
        raise ControllerError("import-excel path must be a regular file inside the project root")
    parent = Path(*relative.parts[:-1])
    if parent.parts:
        directory_fd = _open_relative_directory(app_root, parent, create=False)
    else:
        try:
            directory_fd = os.open(app_root, _DIRECTORY_FLAGS | _NOFOLLOW)
        except OSError as exc:
            raise ControllerError(f"unsafe project root: {exc}") from exc
    try:
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        raise ControllerError(
            f"import-excel path is missing, outside the project root, or a symlink: {exc}"
        ) from exc
    finally:
        os.close(directory_fd)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ControllerError("import-excel path must be a regular file inside the project root")
    return descriptor


@contextmanager
def _staged_import_source(source_fd: int, *, app_root: Path) -> Iterator[Path]:
    directory = Path("run/import-staging")
    directory_fd = _open_relative_directory(app_root, directory, create=True)
    name = f"import-{secrets.token_hex(12)}.xlsx"
    destination_fd = -1
    try:
        destination_fd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        os.lseek(source_fd, 0, os.SEEK_SET)
        while chunk := os.read(source_fd, 1024 * 1024):
            written = 0
            while written < len(chunk):
                written += os.write(destination_fd, chunk[written:])
        os.fsync(destination_fd)
        os.close(destination_fd)
        destination_fd = -1
        yield app_root / directory / name
    finally:
        if destination_fd >= 0:
            os.close(destination_fd)
        try:
            os.unlink(name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)


def _delegate(app_root: Path, arguments: Sequence[str]) -> int:
    result = subprocess.run(
        ["uv", "run", "--frozen", "--no-sync", "eidp", *arguments],
        cwd=app_root,
        env=os.environ.copy(),
        check=False,
    )
    return result.returncode


def _import_excel(app_root: Path, raw_path: Path) -> int:
    source_fd = _open_project_regular_file(raw_path, app_root=app_root)
    try:
        with _staged_import_source(source_fd, app_root=app_root) as staged:
            return _delegate(app_root, ["import-excel", str(staged)])
    finally:
        os.close(source_fd)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eidpctl", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("db-bootstrap")
    commands.add_parser("import-excel").add_argument("path", type=Path)
    commands.add_parser("start").add_argument("--health-timeout", type=float, default=30.0)
    commands.add_parser("status").add_argument("--json", action="store_true", dest="as_json")
    commands.add_parser("stop").add_argument("--timeout", type=float, default=10.0)
    restart = commands.add_parser("restart")
    restart.add_argument("--health-timeout", type=float, default=30.0)
    restart.add_argument("--timeout", type=float, default=10.0)
    commands.add_parser("health").add_argument("--timeout", type=float, default=2.0)
    return parser


def _app_root() -> Path:
    configured = os.environ.get("EIDP_APP_ROOT")
    if not configured:
        raise ControllerError("EIDP_APP_ROOT is required")
    try:
        return Path(configured).resolve(strict=True)
    except OSError as exc:
        raise ControllerError(f"EIDP_APP_ROOT is invalid: {exc}") from exc


def _fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run one serialized controller command."""

    parsed = _parser().parse_args(arguments)
    try:
        app_root = _app_root()
        with _controller_lock(app_root):
            if parsed.command == "db-bootstrap":
                return _delegate(app_root, ["db-bootstrap", "--sqlite"])
            if parsed.command == "import-excel":
                return _import_excel(app_root, parsed.path)
            if parsed.command == "start":
                _start(app_root, load_runtime_config(app_root / ".env"), health_timeout=parsed.health_timeout)
                return 0
            if parsed.command == "status":
                return _status(app_root, as_json=parsed.as_json)
            if parsed.command == "stop":
                _stop(app_root, timeout=parsed.timeout)
                return 0
            if parsed.command == "restart":
                if parsed.health_timeout <= 0 or parsed.timeout <= 0:
                    raise ControllerError("restart timeouts must be positive")
                config = load_runtime_config(app_root / ".env")
                _stop(app_root, timeout=parsed.timeout, quiet=True)
                _start(app_root, config, health_timeout=parsed.health_timeout)
                return 0
            if parsed.command == "health":
                _health(app_root, timeout=parsed.timeout)
                return 0
            raise ControllerError(f"unsupported command: {parsed.command}")
    except (ControllerError, ProcessIdentityError, ValueError, OSError, subprocess.SubprocessError) as exc:
        _fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
