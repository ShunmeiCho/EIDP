from __future__ import annotations

import contextlib
import importlib
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

LINUX_PROC = pytest.mark.skipif(sys.platform != "linux", reason="requires Linux /proc process identity")


def _controller_module() -> ModuleType:
    try:
        return importlib.import_module("eidp.ops.runtime_controller")
    except ModuleNotFoundError as exc:
        pytest.fail(f"runtime controller module is missing: {exc}")


def _process_module() -> ModuleType:
    return importlib.import_module("eidp.ops.runtime_process")


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _linux_start_time(pid: int) -> str:
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return stat[stat.rfind(")") + 2 :].split()[19]


@dataclass
class ControllerEnv:
    app_root: Path
    env: dict[str, str]
    port: int

    @property
    def pid_file(self) -> Path:
        return self.app_root / "run" / "eidp.pid.json"

    @property
    def uv_args_file(self) -> Path:
        return self.app_root / "uv-args.json"

    def run(self, *arguments: str, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "eidp.ops.runtime_controller", *arguments],
            cwd=self.app_root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def write_pid_metadata(
        self,
        *,
        pid: int,
        start_time: str,
        argv_marker: str = "eidp.ops.rotating_runner",
        app_root: Path | None = None,
    ) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(
            json.dumps(
                {
                    "pid": pid,
                    "linux_start_time": start_time,
                    "app_root": str(app_root or self.app_root),
                    "argv_marker": argv_marker,
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture
def controller_env(tmp_path: Path) -> Iterator[ControllerEnv]:
    app_root = tmp_path / "app"
    deploy_dir = app_root / "deploy" / "linux"
    bin_dir = app_root / "test-bin"
    deploy_dir.mkdir(parents=True)
    bin_dir.mkdir()
    (app_root / "data").mkdir()
    port = _unused_port()
    (app_root / ".env").write_text(f"EIDP_WEB_PORT={port}\n", encoding="utf-8")

    fake_web = app_root / "fake_web.py"
    fake_web.write_text(
        "\n".join(
            (
                "import os",
                "from http.server import BaseHTTPRequestHandler, HTTPServer",
                "class Handler(BaseHTTPRequestHandler):",
                "    def do_GET(self):",
                "        if self.path.endswith('/_stcore/health'):",
                "            self.send_response(200)",
                "            self.end_headers()",
                "            self.wfile.write(b'ok')",
                "        else:",
                "            self.send_response(404)",
                "            self.end_headers()",
                "    def log_message(self, _format, *args):",
                "        pass",
                "print('fake web starting', flush=True)",
                "HTTPServer(('127.0.0.1', int(os.environ['STREAMLIT_SERVER_PORT'])), Handler).serve_forever()",
                "",
            )
        ),
        encoding="utf-8",
    )
    run_web = deploy_dir / "run_web.sh"
    run_web.write_text(
        "#!/usr/bin/env bash\nexec \"${EIDP_TEST_PYTHON}\" \"${EIDP_APP_ROOT}/fake_web.py\"\n",
        encoding="utf-8",
    )
    run_web.chmod(0o755)

    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "arguments = sys.argv[1:]\n"
        "Path(os.environ['EIDP_TEST_UV_ARGS']).write_text(json.dumps(arguments), encoding='utf-8')\n"
        "if len(arguments) >= 2 and arguments[-2] == 'import-excel':\n"
        "    Path(os.environ['EIDP_TEST_IMPORTED_BYTES']).write_bytes(Path(arguments[-1]).read_bytes())\n",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "EIDP_APP_ROOT": str(app_root),
            "EIDP_DATA_DIR": str(app_root / "data"),
            "EIDP_DATABASE_URL": f"sqlite:///{app_root}/data/test.sqlite3",
            "EIDP_TEST_PYTHON": sys.executable,
            "EIDP_TEST_UV_ARGS": str(app_root / "uv-args.json"),
            "EIDP_TEST_IMPORTED_BYTES": str(app_root / "imported-bytes.bin"),
            "PATH": os.pathsep.join((str(bin_dir), env.get("PATH", ""))),
        }
    )
    fixture = ControllerEnv(app_root=app_root, env=env, port=port)
    try:
        yield fixture
    finally:
        if fixture.pid_file.exists():
            with contextlib.suppress(subprocess.SubprocessError, OSError):
                fixture.run("stop", "--timeout", "1", timeout=3)
        if fixture.pid_file.exists():
            with contextlib.suppress(ValueError, OSError, json.JSONDecodeError):
                pid = int(json.loads(fixture.pid_file.read_text(encoding="utf-8"))["pid"])
                os.killpg(pid, signal.SIGKILL)


def test_required_controller_modules_and_thin_shell_entrypoint_are_present() -> None:
    assert Path("src/eidp/ops/rotating_runner.py").is_file()
    assert Path("src/eidp/ops/runtime_controller.py").is_file()
    assert Path("deploy/linux/eidpctl.sh").is_file()


def test_controller_reexports_runtime_process_compatibility_interfaces() -> None:
    controller = _controller_module()
    spec = importlib.util.find_spec("eidp.ops.runtime_process")
    assert spec is not None
    process = importlib.import_module("eidp.ops.runtime_process")

    assert controller.ProcessIdentity is process.ProcessIdentity
    assert controller.ProcessIdentityError is process.ProcessIdentityError
    assert controller.read_verified_process is process.read_verified_process


def test_read_verified_process_returns_none_for_dead_pid_and_stale_file(tmp_path: Path) -> None:
    module = _controller_module()
    app_root = tmp_path.resolve()
    pid_file = tmp_path / "run" / "eidp.pid.json"
    pid_file.parent.mkdir()
    pid_file.write_text(
        json.dumps(
            {
                "pid": 2_147_483_647,
                "linux_start_time": "1",
                "app_root": str(app_root),
                "argv_marker": "eidp.ops.rotating_runner",
            }
        ),
        encoding="utf-8",
    )

    assert module.read_verified_process(pid_file, app_root=app_root) is None


def test_status_cleans_stale_pid_metadata(controller_env: ControllerEnv) -> None:
    controller_env.write_pid_metadata(pid=2_147_483_647, start_time="1")

    result = controller_env.run("status", "--json")

    assert result.returncode != 0
    assert json.loads(result.stdout) == {
        "address": "127.0.0.1",
        "port": None,
        "running": False,
    }
    assert not controller_env.pid_file.exists()


def test_start_refuses_an_occupied_loopback_port(controller_env: ControllerEnv) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", controller_env.port))
        listener.listen()

        result = controller_env.run("start", "--health-timeout", "0.2")

    assert result.returncode != 0
    assert "occupied" in result.stderr
    assert not controller_env.pid_file.exists()


@LINUX_PROC
@pytest.mark.parametrize("mismatch", ("start_time", "argv", "app_root"))
def test_stop_refuses_live_pid_with_wrong_signature(
    controller_env: ControllerEnv,
    mismatch: str,
) -> None:
    sleeper = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=controller_env.app_root,
        env=controller_env.env,
        start_new_session=True,
    )
    try:
        start_time = _linux_start_time(sleeper.pid)
        argv_marker = "time.sleep"
        metadata_root = controller_env.app_root
        if mismatch == "start_time":
            start_time = "wrong"
        elif mismatch == "argv":
            argv_marker = "eidp.ops.rotating_runner"
        else:
            metadata_root = controller_env.app_root / "wrong-root"
        controller_env.write_pid_metadata(
            pid=sleeper.pid,
            start_time=start_time,
            argv_marker=argv_marker,
            app_root=metadata_root,
        )

        result = controller_env.run("stop")

        assert result.returncode != 0
        assert "identity mismatch" in result.stderr
        assert sleeper.poll() is None
    finally:
        controller_env.pid_file.unlink(missing_ok=True)
        if sleeper.poll() is None:
            sleeper.terminate()
            sleeper.wait(timeout=5)


@LINUX_PROC
def test_duplicate_start_is_rejected_and_status_reports_verified_endpoint(controller_env: ControllerEnv) -> None:
    try:
        first = controller_env.run("start", "--health-timeout", "3")
        duplicate = controller_env.run("start", "--health-timeout", "1")
        status = controller_env.run("status", "--json")
        health = controller_env.run("health", "--timeout", "1")

        payload = json.loads(status.stdout)
        assert first.returncode == 0, first.stderr
        assert duplicate.returncode != 0
        assert "already running" in duplicate.stderr
        assert status.returncode == 0
        assert payload["running"] is True
        assert payload["pid"] > 1
        assert payload["address"] == "127.0.0.1"
        assert payload["port"] == controller_env.port
        assert health.returncode == 0
    finally:
        controller_env.run("stop", "--timeout", "3")


@LINUX_PROC
def test_start_cleans_up_supervisor_after_health_timeout(controller_env: ControllerEnv) -> None:
    launcher = controller_env.app_root / "deploy" / "linux" / "run_web.sh"
    launcher.write_text("#!/usr/bin/env bash\nexec sleep 60\n", encoding="utf-8")
    launcher.chmod(0o755)

    result = controller_env.run("start", "--health-timeout", "0.2")

    assert result.returncode != 0
    assert "health check timed out" in result.stderr
    assert not controller_env.pid_file.exists()


@LINUX_PROC
def test_restart_replaces_the_verified_supervisor(controller_env: ControllerEnv) -> None:
    try:
        started = controller_env.run("start", "--health-timeout", "3")
        first_pid = int(json.loads(controller_env.pid_file.read_text(encoding="utf-8"))["pid"])

        restarted = controller_env.run("restart", "--health-timeout", "3", "--timeout", "3")
        second_pid = int(json.loads(controller_env.pid_file.read_text(encoding="utf-8"))["pid"])

        assert started.returncode == 0, started.stderr
        assert restarted.returncode == 0, restarted.stderr
        assert second_pid != first_pid
        assert controller_env.run("health", "--timeout", "1").returncode == 0
    finally:
        controller_env.run("stop", "--timeout", "3")


@LINUX_PROC
def test_started_supervisor_survives_its_short_lived_parent(controller_env: ControllerEnv) -> None:
    try:
        start = controller_env.run("start", "--health-timeout", "3")
        pid = int(json.loads(controller_env.pid_file.read_text(encoding="utf-8"))["pid"])
        time.sleep(0.1)
        status = controller_env.run("status", "--json")

        assert start.returncode == 0, start.stderr
        assert status.returncode == 0
        assert json.loads(status.stdout)["pid"] == pid
    finally:
        controller_env.run("stop", "--timeout", "3")


def test_db_bootstrap_delegates_to_existing_locked_cli(controller_env: ControllerEnv) -> None:
    result = controller_env.run("db-bootstrap")

    assert result.returncode == 0, result.stderr
    assert json.loads(controller_env.uv_args_file.read_text(encoding="utf-8")) == [
        "run",
        "--frozen",
        "--no-sync",
        "eidp",
        "db-bootstrap",
        "--sqlite",
    ]


def test_backup_package_delegates_to_locked_cli(controller_env: ControllerEnv) -> None:
    result = controller_env.run("backup-package", "--backup-id", "backup-20260712", "--actor", "operator")

    assert result.returncode == 0, result.stderr
    assert json.loads(controller_env.uv_args_file.read_text(encoding="utf-8")) == [
        "run",
        "--frozen",
        "--no-sync",
        "eidp",
        "backup-package",
        "--backup-id",
        "backup-20260712",
        "--actor",
        "operator",
    ]


def test_backup_verify_delegates_only_project_local_package(controller_env: ControllerEnv) -> None:
    package = controller_env.app_root / "backups" / "backup-20260712"
    package.mkdir(parents=True)

    result = controller_env.run("backup-verify", str(package))

    assert result.returncode == 0, result.stderr
    assert json.loads(controller_env.uv_args_file.read_text(encoding="utf-8")) == [
        "run",
        "--frozen",
        "--no-sync",
        "eidp",
        "backup-verify",
        str(package),
    ]


def test_backup_verify_rejects_staging_directory_even_when_project_local(controller_env: ControllerEnv) -> None:
    staged = controller_env.app_root / "backups/.staging/backup-20260712"
    staged.mkdir(parents=True)

    result = controller_env.run("backup-verify", str(staged))

    assert result.returncode != 0
    assert "staging" in result.stderr or "finalized" in result.stderr
    assert not controller_env.uv_args_file.exists()


@pytest.mark.parametrize("unsafe_kind", ("outside", "symlink"))
def test_backup_verify_rejects_outside_or_symlink_package(
    controller_env: ControllerEnv,
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    outside = tmp_path / "outside-package"
    outside.mkdir()
    candidate = outside
    if unsafe_kind == "symlink":
        candidate = controller_env.app_root / "backups" / "linked"
        candidate.parent.mkdir()
        candidate.symlink_to(outside, target_is_directory=True)

    result = controller_env.run("backup-verify", str(candidate))

    assert result.returncode != 0
    assert "project root" in result.stderr or "symlink" in result.stderr
    assert not controller_env.uv_args_file.exists()


def test_import_excel_delegates_project_local_regular_file_to_locked_cli(controller_env: ControllerEnv) -> None:
    workbook = controller_env.app_root / "data" / "incoming.xlsx"
    workbook.write_bytes(b"test workbook boundary")

    result = controller_env.run("import-excel", str(workbook))

    arguments = json.loads(controller_env.uv_args_file.read_text(encoding="utf-8"))
    staged = Path(arguments[-1])
    assert result.returncode == 0, result.stderr
    assert arguments[:-1] == [
        "run",
        "--frozen",
        "--no-sync",
        "eidp",
        "import-excel",
    ]
    assert staged != workbook
    assert staged.parent == controller_env.app_root / "run" / "import-staging"
    assert not staged.exists()
    assert (controller_env.app_root / "imported-bytes.bin").read_bytes() == b"test workbook boundary"
    assert not any(staged.parent.iterdir())


@pytest.mark.parametrize("unsafe_kind", ("outside", "symlink_file", "symlink_parent"))
def test_import_excel_rejects_outside_and_symlink_paths(
    controller_env: ControllerEnv,
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"outside")
    candidate = outside
    if unsafe_kind == "symlink_file":
        candidate = controller_env.app_root / "linked.xlsx"
        candidate.symlink_to(outside)
    elif unsafe_kind == "symlink_parent":
        linked_parent = controller_env.app_root / "linked-parent"
        linked_parent.symlink_to(tmp_path, target_is_directory=True)
        candidate = linked_parent / outside.name

    result = controller_env.run("import-excel", str(candidate))

    assert result.returncode != 0
    assert "project root" in result.stderr or "symlink" in result.stderr
    assert not controller_env.uv_args_file.exists()


def test_process_group_signal_revalidates_identity_immediately_before_kill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    expected = module.ProcessIdentity(101, "before", str(tmp_path), module.RUNNER_ARGV_MARKER)
    changed = module.ProcessIdentity(101, "after", str(tmp_path), module.RUNNER_ARGV_MARKER)
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(module, "_pidfd_open", lambda _pid: 77)
    monkeypatch.setattr(module, "_pidfd_close", lambda _fd: None)
    monkeypatch.setattr(module, "read_verified_process", lambda *_args, **_kwargs: changed)
    monkeypatch.setattr(module.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(module.os, "getsid", lambda pid: pid)
    monkeypatch.setattr(module.os, "killpg", lambda pid, signum: signals.append((pid, signum)))

    with pytest.raises(module.ProcessIdentityError, match="changed"):
        module._signal_verified_process_group(
            tmp_path / "eidp.pid.json",
            app_root=tmp_path,
            expected=expected,
            signum=signal.SIGKILL,
        )

    assert signals == []


def test_pidfd_guard_prevents_signal_after_pid_reuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    expected = module.ProcessIdentity(101, "before", str(tmp_path), module.RUNNER_ARGV_MARKER)
    reused = module.ProcessIdentity(101, "reused", str(tmp_path), module.RUNNER_ARGV_MARKER)
    pidfd_signals: list[tuple[int, signal.Signals]] = []
    closed: list[int] = []
    monkeypatch.setattr(module, "_pidfd_open", lambda pid: 77)
    monkeypatch.setattr(module, "_pidfd_send_signal", lambda fd, signum: pidfd_signals.append((fd, signum)))
    monkeypatch.setattr(module, "_pidfd_close", lambda fd: closed.append(fd))
    monkeypatch.setattr(module, "read_verified_process", lambda *_args, **_kwargs: reused)

    with pytest.raises(module.ProcessIdentityError, match="changed"):
        module._signal_verified_process_group(
            tmp_path / "eidp.pid.json",
            app_root=tmp_path,
            expected=expected,
            signum=signal.SIGTERM,
        )

    assert pidfd_signals == []
    assert closed == [77]


@pytest.mark.parametrize("wrong_boundary", ("process_group", "session"))
def test_process_group_signal_refuses_a_non_supervisor_group(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    wrong_boundary: str,
) -> None:
    module = _process_module()
    expected = module.ProcessIdentity(101, "start", str(tmp_path), module.RUNNER_ARGV_MARKER)
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(module, "_pidfd_open", lambda _pid: 77)
    monkeypatch.setattr(module, "_pidfd_close", lambda _fd: None)
    monkeypatch.setattr(module, "read_verified_process", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(module.os, "getpgid", lambda pid: pid + (wrong_boundary == "process_group"))
    monkeypatch.setattr(module.os, "getsid", lambda pid: pid + (wrong_boundary == "session"))
    monkeypatch.setattr(module.os, "killpg", lambda pid, signum: signals.append((pid, signum)))

    with pytest.raises(module.ProcessIdentityError, match="process group|session"):
        module._signal_verified_process_group(
            tmp_path / "eidp.pid.json",
            app_root=tmp_path,
            expected=expected,
            signum=signal.SIGKILL,
        )

    assert signals == []


def test_process_group_signal_targets_only_the_reverified_supervisor_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    expected = module.ProcessIdentity(101, "start", str(tmp_path), module.RUNNER_ARGV_MARKER)
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(module, "_pidfd_open", lambda _pid: 77)
    monkeypatch.setattr(module, "_pidfd_close", lambda _fd: None)
    monkeypatch.setattr(module, "read_verified_process", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(module.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(module.os, "getsid", lambda pid: pid)
    monkeypatch.setattr(module.os, "killpg", lambda pid, signum: signals.append((pid, signum)))

    result = module._signal_verified_process_group(
        tmp_path / "eidp.pid.json",
        app_root=tmp_path,
        expected=expected,
        signum=signal.SIGKILL,
    )

    assert result == expected
    assert signals == [(expected.pid, signal.SIGKILL)]


def test_failed_start_never_directly_kills_an_unverified_process(tmp_path: Path) -> None:
    module = _process_module()

    class UnverifiedProcess:
        pid = 101
        killed = False

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            return 0

    process = UnverifiedProcess()

    with pytest.raises(module.ControllerError, match="unverified"):
        module._terminate_failed_start(tmp_path, tmp_path / "run" / "eidp.pid.json", process)

    assert process.killed is False


def test_write_record_failure_passes_captured_identity_to_verified_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    launcher = tmp_path / "deploy" / "linux" / "run_web.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    expected = module.ProcessIdentity(101, "start", str(tmp_path), module.RUNNER_ARGV_MARKER)
    cleaned: list[object] = []

    class Process:
        pid = expected.pid

    monkeypatch.setattr(module, "_require_available_port", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(module, "_capture_identity", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(
        module,
        "_write_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("write failed")),
    )
    monkeypatch.setattr(
        module,
        "_terminate_failed_start",
        lambda *_args, captured_identity=None, **_kwargs: cleaned.append(captured_identity),
    )

    with pytest.raises(OSError, match="write failed"):
        module._start(tmp_path, module.RuntimeLaunchConfig(), health_timeout=1)

    assert cleaned == [expected]


def test_failed_start_with_captured_identity_uses_verified_group_escalation_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    expected = module.ProcessIdentity(101, "start", str(tmp_path), module.RUNNER_ARGV_MARKER)
    signals: list[signal.Signals] = []
    waits: list[float] = []

    class Process:
        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            waits.append(timeout)
            if len(waits) == 1:
                raise subprocess.TimeoutExpired("runner", timeout)
            return 0

    monkeypatch.setattr(
        module,
        "_signal_verified_process_group",
        lambda *_args, signum, **_kwargs: signals.append(signum) or expected,
    )

    module._terminate_failed_start(
        tmp_path,
        tmp_path / "run" / "eidp.pid.json",
        Process(),
        captured_identity=expected,
    )

    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert waits == [3.0, 2.0]


def test_stop_rejects_a_non_positive_timeout(controller_env: ControllerEnv) -> None:
    result = controller_env.run("stop", "--timeout", "0")

    assert result.returncode != 0
    assert "positive" in result.stderr


def test_stop_does_not_depend_on_current_runtime_config(controller_env: ControllerEnv) -> None:
    controller_env.write_pid_metadata(pid=2_147_483_647, start_time="1")
    (controller_env.app_root / ".env").write_text("EIDP_WEB_PORT=invalid\n", encoding="utf-8")

    result = controller_env.run("stop")

    assert result.returncode == 0, result.stderr
    assert not controller_env.pid_file.exists()


def test_health_probe_does_not_trust_urlopen_proxy_or_redirect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    identity = module.ProcessIdentity(101, "start", str(tmp_path), module.RUNNER_ARGV_MARKER)
    record = module._RuntimeProcessRecord(identity, "127.0.0.1", _unused_port(), "")

    class FakeProxyResponse:
        status = 200

        def __enter__(self) -> FakeProxyResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: FakeProxyResponse())

    assert module._probe_health(record, timeout=0.1) is False


def test_controller_refuses_a_symlink_run_directory(controller_env: ControllerEnv, tmp_path: Path) -> None:
    outside = tmp_path / "outside-run"
    outside.mkdir()
    (controller_env.app_root / "run").symlink_to(outside, target_is_directory=True)

    result = controller_env.run("status", "--json")

    assert result.returncode != 0
    assert "symlink" in result.stderr or "unsafe" in result.stderr
    assert not (outside / "eidpctl.lock").exists()


def test_controller_refuses_a_symlink_lock_file(controller_env: ControllerEnv, tmp_path: Path) -> None:
    run_dir = controller_env.app_root / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside.lock"
    outside.write_text("must stay unchanged", encoding="utf-8")
    (run_dir / "eidpctl.lock").symlink_to(outside)

    result = controller_env.run("status", "--json")

    assert result.returncode != 0
    assert "symlink" in result.stderr or "unsafe" in result.stderr
    assert outside.read_text(encoding="utf-8") == "must stay unchanged"


def _runtime_record(module: ModuleType, app_root: Path) -> object:
    identity = module.ProcessIdentity(101, "start", str(app_root), module.RUNNER_ARGV_MARKER)
    return module._RuntimeProcessRecord(identity, "127.0.0.1", 8502, "")


def test_pid_record_write_refuses_a_symlink_final_file(tmp_path: Path) -> None:
    module = _process_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("must stay unchanged", encoding="utf-8")
    pid_file = run_dir / "eidp.pid.json"
    pid_file.symlink_to(outside)

    with pytest.raises((module.ProcessIdentityError, module.ControllerError, OSError)):
        module._write_record(pid_file, _runtime_record(module, tmp_path))

    assert outside.read_text(encoding="utf-8") == "must stay unchanged"


def test_pid_record_write_refuses_a_precreated_random_temp_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _process_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside.tmp"
    outside.write_text("must stay unchanged", encoding="utf-8")
    (run_dir / ".eidp.pid.fixed.tmp").symlink_to(outside)
    monkeypatch.setattr(module.secrets, "token_hex", lambda _length: "fixed")

    with pytest.raises((module.ProcessIdentityError, module.ControllerError, OSError)):
        module._write_record(run_dir / "eidp.pid.json", _runtime_record(module, tmp_path))

    assert outside.read_text(encoding="utf-8") == "must stay unchanged"


def test_import_staging_copies_from_pinned_source_fd_after_name_replacement(tmp_path: Path) -> None:
    module = _controller_module()
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    data_dir.mkdir(parents=True)
    workbook = data_dir / "incoming.xlsx"
    workbook.write_bytes(b"pinned original")
    source_fd = module._open_project_regular_file(workbook, app_root=app_root)
    replacement = data_dir / "replacement.xlsx"
    replacement.write_bytes(b"replacement bytes")
    replacement.replace(workbook)

    try:
        with module._staged_import_source(source_fd, app_root=app_root) as staged:
            assert staged.read_bytes() == b"pinned original"
            assert staged.parent == app_root / "run" / "import-staging"
            assert staged.stat().st_mode & 0o777 == 0o600
        assert not staged.exists()
    finally:
        os.close(source_fd)


def test_shutdown_wait_requires_loopback_port_release() -> None:
    module = _process_module()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])
        listener.listen()
        assert module._wait_for_port_release("127.0.0.1", port, timeout=0.05) is False

    assert module._wait_for_port_release("127.0.0.1", port, timeout=0.2) is True


@pytest.mark.parametrize("source_root", ("backups", "restore-drills/incoming"))
def test_restore_drill_delegates_exact_distinct_operator_arguments(
    controller_env: ControllerEnv,
    source_root: str,
) -> None:
    backup_id = "backup-20260712"
    package = controller_env.app_root / source_root / backup_id
    target = controller_env.app_root / "restore-drills/verified" / backup_id
    expectation = (
        controller_env.app_root
        / "evidence/runtime/exports/123e4567-e89b-42d3-a456-426614174000.json"
    )
    package.mkdir(parents=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    expectation.parent.mkdir(parents=True)
    expectation.write_text("{}\n", encoding="utf-8")

    result = controller_env.run(
        "restore-drill",
        str(package),
        "--target",
        str(target),
        "--smoke-port",
        "18502",
        "--expected-manifest-sha",
        "a" * 64,
        "--off-host-receipt-id",
        "receipt:@ICT+20260712",
        "--acceptance-expectations",
        str(expectation),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(controller_env.uv_args_file.read_text(encoding="utf-8")) == [
        "run",
        "--frozen",
        "--no-sync",
        "eidp",
        "restore-drill",
        str(package),
        "--target",
        str(target),
        "--smoke-port",
        "18502",
        "--expected-manifest-sha",
        "a" * 64,
        "--off-host-receipt-id",
        "receipt:@ICT+20260712",
        "--acceptance-expectations",
        str(expectation),
    ]


def test_restore_drill_rejects_pre_upgrade_package_before_uv_delegation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _controller_module()
    app_root = tmp_path / "app"
    package = app_root / "backups/pre-upgrade"
    target = app_root / "restore-drills/verified/pre-upgrade"
    package.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    delegated_calls: list[list[str]] = []

    monkeypatch.setattr(
        module,
        "_delegate",
        lambda _app_root, arguments: delegated_calls.append(list(arguments)) or 0,
    )

    error: str | None = None
    try:
        module._restore_drill(
            app_root,
            package_path=package,
            target_path=target,
            smoke_port=18502,
            expected_manifest_sha=None,
            off_host_receipt_id=None,
            acceptance_expectations=None,
        )
    except module.ControllerError as exc:
        error = str(exc)

    assert delegated_calls == []
    assert error is not None
    assert "pre-upgrade" in error or "finalized" in error


@pytest.mark.parametrize(
    "unsafe",
    (
        "package_outside",
        "package_symlink",
        "package_staging",
        "package_nested",
        "target_outside",
        "target_incoming",
        "target_nested",
        "target_mismatch",
        "target_symlink_parent",
        "expectation_outside",
        "expectation_symlink",
        "expectation_nested",
    ),
)
def test_restore_drill_controller_rejects_unsafe_paths_before_uv_delegation(
    controller_env: ControllerEnv,
    tmp_path: Path,
    unsafe: str,
) -> None:
    backup_id = "backup-20260712"
    package = controller_env.app_root / "backups" / backup_id
    target = controller_env.app_root / "restore-drills/verified" / backup_id
    expectation = controller_env.app_root / "evidence/runtime/exports/123e4567-e89b-42d3-a456-426614174000.json"
    package.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    expectation.parent.mkdir(parents=True)
    expectation.write_text("{}\n", encoding="utf-8")

    if unsafe == "package_outside":
        package = tmp_path / "outside-package"
        package.mkdir()
    elif unsafe == "package_symlink":
        outside = tmp_path / "linked-package"
        outside.mkdir()
        package.rmdir()
        package.symlink_to(outside, target_is_directory=True)
    elif unsafe == "package_staging":
        package = controller_env.app_root / "backups/.staging" / backup_id
        package.mkdir(parents=True)
    elif unsafe == "package_nested":
        package = controller_env.app_root / "backups/nested" / backup_id
        package.mkdir(parents=True)
    elif unsafe == "target_outside":
        target = tmp_path / backup_id
    elif unsafe == "target_incoming":
        target = controller_env.app_root / "restore-drills/incoming" / backup_id
    elif unsafe == "target_nested":
        target = controller_env.app_root / "restore-drills/verified/nested" / backup_id
    elif unsafe == "target_mismatch":
        target = controller_env.app_root / "restore-drills/verified/different-id"
    elif unsafe == "target_symlink_parent":
        outside = tmp_path / "linked-target-parent"
        outside.mkdir()
        target.parent.rmdir()
        target.parent.symlink_to(outside, target_is_directory=True)
    elif unsafe == "expectation_outside":
        expectation = tmp_path / expectation.name
        expectation.write_text("{}\n", encoding="utf-8")
    elif unsafe == "expectation_symlink":
        outside = tmp_path / "linked-expectation.json"
        outside.write_text("{}\n", encoding="utf-8")
        expectation.unlink()
        expectation.symlink_to(outside)
    else:
        expectation = controller_env.app_root / "evidence/runtime/exports/nested" / expectation.name
        expectation.parent.mkdir()
        expectation.write_text("{}\n", encoding="utf-8")

    result = controller_env.run(
        "restore-drill",
        str(package),
        "--target",
        str(target),
        "--acceptance-expectations",
        str(expectation),
    )

    assert result.returncode != 0
    assert not controller_env.uv_args_file.exists()
