from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eidp.ops import deployment_manifest as deployment_manifest_module
from eidp.ops.deployment_manifest import (
    DeploymentManifest,
    DeploymentManifestError,
    collect_deployment_manifest,
    write_deployment_manifest_atomic,
)
from eidp.ops.runtime_config import RuntimeLaunchConfig

SCHEMA_HEAD = "7b8c9d0e1f2a"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$")


@dataclass
class RepoFixture:
    path: Path

    def git(self, *arguments: str, input_text: str | None = None) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.path,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    @property
    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def set_origin_main(self, commit: str) -> None:
        self.git("update-ref", "refs/remotes/origin/main", commit)

    def commit_tree(self, *, parent: str | None) -> str:
        arguments = ["commit-tree", self.git("rev-parse", "HEAD^{tree}")]
        if parent is not None:
            arguments.extend(("-p", parent))
        return self.git(*arguments, input_text="test commit\n")


def _write_schema_database(path: Path, rows: tuple[str, ...] = (SCHEMA_HEAD,)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.executemany("INSERT INTO alembic_version(version_num) VALUES (?)", ((row,) for row in rows))


@pytest.fixture
def repo(tmp_path: Path) -> RepoFixture:
    root = tmp_path / "app"
    root.mkdir()
    fixture = RepoFixture(root)
    fixture.git("init", "-b", "main")
    fixture.git("config", "user.name", "EIDP Test")
    fixture.git("config", "user.email", "eidp@example.invalid")
    (root / ".gitignore").write_text("/.env\n/data/eidp.sqlite3\n/run/\n", encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "tracked.txt").write_text("published\n", encoding="utf-8")
    fixture.git("add", ".gitignore", "uv.lock", "tracked.txt")
    fixture.git("commit", "-m", "published source")
    fixture.git("remote", "add", "origin", str(tmp_path / "remote-does-not-exist"))
    fixture.set_origin_main(fixture.head)
    _write_schema_database(root / "data" / "eidp.sqlite3")
    return fixture


@pytest.fixture
def runtime() -> RuntimeLaunchConfig:
    return RuntimeLaunchConfig(
        port=18502,
        base_url_path="/eidp",
        internal_base_url="https://eidp.internal.example/eidp",
        max_upload_mb=200,
    )


@pytest.fixture
def manifest() -> DeploymentManifest:
    return DeploymentManifest(
        deployed_commit="a" * 40,
        expected_deployment_commit="a" * 40,
        origin_main_commit="b" * 40,
        uv_lock_sha256="c" * 64,
        schema_head=SCHEMA_HEAD,
        deployed_at_utc="2026-07-12T01:02:03Z",
        operator="operator",
        internal_base_url="https://eidp.internal.example/eidp",
        port=18502,
        base_url_path="/eidp",
        pre_upgrade_backup_id="backup-20260712",
        off_host_receipt_id="receipt:20260712",
    )


@pytest.mark.parametrize("dirty_kind", ("untracked", "tracked"))
def test_collection_refuses_dirty_or_untracked_checkout(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    dirty_kind: str,
) -> None:
    if dirty_kind == "untracked":
        (repo.path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    else:
        (repo.path / "tracked.txt").write_text("changed\n", encoding="utf-8")

    with pytest.raises(DeploymentManifestError, match="clean checkout"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")


def test_default_collection_requires_fetched_origin_main_and_exact_head(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
) -> None:
    repo.git("update-ref", "-d", "refs/remotes/origin/main")
    with pytest.raises(DeploymentManifestError, match="origin/main"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    later = repo.commit_tree(parent=repo.head)
    repo.set_origin_main(later)
    with pytest.raises(DeploymentManifestError, match="HEAD.*origin/main|origin/main.*HEAD"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")


def test_expected_commit_mode_records_a_later_main_without_changing_deployment(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
) -> None:
    deployed = repo.head
    later = repo.commit_tree(parent=deployed)
    repo.set_origin_main(later)

    result = collect_deployment_manifest(
        app_root=repo.path,
        runtime=runtime,
        actor="operator",
        expected_deployment_commit=deployed,
    )

    assert result.deployed_commit == deployed
    assert result.expected_deployment_commit == deployed
    assert result.origin_main_commit == later


def test_expected_commit_mode_requires_exact_head_and_origin_main_ancestry(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
) -> None:
    deployed = repo.head
    later = repo.commit_tree(parent=deployed)
    with pytest.raises(DeploymentManifestError, match="expected deployment commit"):
        collect_deployment_manifest(
            app_root=repo.path,
            runtime=runtime,
            actor="operator",
            expected_deployment_commit=later,
        )

    unrelated = repo.commit_tree(parent=None)
    repo.set_origin_main(unrelated)
    with pytest.raises(DeploymentManifestError, match="ancestor.*origin/main|origin/main.*ancestor"):
        collect_deployment_manifest(
            app_root=repo.path,
            runtime=runtime,
            actor="operator",
            expected_deployment_commit=deployed,
        )


def test_expected_commit_mode_ignores_git_replace_refs_that_forge_ancestry(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
) -> None:
    deployed = repo.head
    unrelated = repo.commit_tree(parent=None)
    forged_descendant = repo.commit_tree(parent=deployed)
    repo.git("replace", unrelated, forged_descendant)
    repo.set_origin_main(unrelated)

    with pytest.raises(DeploymentManifestError, match="ancestor.*origin/main|origin/main.*ancestor"):
        collect_deployment_manifest(
            app_root=repo.path,
            runtime=runtime,
            actor="operator",
            expected_deployment_commit=deployed,
        )


@pytest.mark.parametrize(
    ("config_key", "config_value"),
    (("remote.origin.promisor", "true"), ("extensions.partialClone", "origin")),
)
def test_collection_refuses_promisor_or_partial_clone_repositories(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    config_key: str,
    config_value: str,
) -> None:
    repo.git("config", config_key, config_value)

    with pytest.raises(DeploymentManifestError, match="promisor|partial clone"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")


def test_collection_disables_configured_fsmonitor_hooks(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
) -> None:
    run_dir = repo.path / "run"
    run_dir.mkdir()
    marker = run_dir / "fsmonitor-invoked"
    hook = repo.path / ".git" / "hooks" / "fsmonitor-test"
    hook.write_text(f"#!/bin/sh\nprintf invoked > {marker!s}\n", encoding="utf-8")
    hook.chmod(0o755)
    repo.git("config", "core.fsmonitor", str(hook))

    collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    assert not marker.exists()


def test_git_evidence_commands_disable_lazy_fetch_and_have_bounded_timeouts(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_run = deployment_manifest_module.subprocess.run
    evidence_calls: list[tuple[list[str], dict[str, str], object]] = []

    def record_run(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command and command[0] == "git":
            evidence_calls.append((command, kwargs["env"], kwargs.get("timeout")))  # type: ignore[arg-type]
        return original_run(command, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(deployment_manifest_module.subprocess, "run", record_run)

    collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    assert evidence_calls
    assert all(command[1:3] == ["-c", "core.fsmonitor=false"] for command, _env, _timeout in evidence_calls)
    assert all(environment["GIT_NO_LAZY_FETCH"] == "1" for _command, environment, _timeout in evidence_calls)
    assert all(isinstance(timeout, (int, float)) and 0 < timeout <= 30 for _command, _env, timeout in evidence_calls)


def test_git_evidence_timeout_fails_loudly(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_timeouts: list[object] = []

    def time_out(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_timeouts.append(kwargs.get("timeout"))
        raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))

    monkeypatch.setattr(deployment_manifest_module.subprocess, "run", time_out)

    with pytest.raises(DeploymentManifestError, match="timed out"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    assert observed_timeouts
    assert isinstance(observed_timeouts[0], (int, float))


@pytest.mark.parametrize("index_flag", ("--assume-unchanged", "--skip-worktree"))
def test_collection_refuses_index_flags_that_hide_a_modified_tracked_file(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    index_flag: str,
) -> None:
    repo.git("update-index", index_flag, "tracked.txt")
    (repo.path / "tracked.txt").write_text("hidden modification\n", encoding="utf-8")
    assert repo.git("status", "--porcelain=v1", "--untracked-files=all") == ""

    with pytest.raises(DeploymentManifestError, match="index|clean checkout|assume|skip"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")


@pytest.mark.parametrize("unsafe_lock", ("missing", "symlink", "untracked"))
def test_collection_requires_a_safe_tracked_uv_lock(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    tmp_path: Path,
    unsafe_lock: str,
) -> None:
    lock = repo.path / "uv.lock"
    if unsafe_lock == "missing":
        lock.unlink()
    elif unsafe_lock == "symlink":
        outside = tmp_path / "outside.lock"
        outside.write_text("outside\n", encoding="utf-8")
        lock.unlink()
        lock.symlink_to(outside)
    else:
        repo.git("rm", "--cached", "uv.lock")
        (repo.path / ".gitignore").write_text("/data/eidp.sqlite3\n/run/\n/uv.lock\n", encoding="utf-8")
        repo.git("add", ".gitignore")
        repo.git("commit", "-m", "ignore untracked lock")
        repo.set_origin_main(repo.head)

    with pytest.raises(DeploymentManifestError, match="uv.lock|clean checkout"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")


@pytest.mark.parametrize("database_state", ("missing", "missing_table", "no_rows", "multiple_rows", "invalid_head"))
def test_collection_fails_closed_on_missing_or_invalid_canonical_schema(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    database_state: str,
) -> None:
    database = repo.path / "data" / "eidp.sqlite3"
    database.unlink()
    if database_state == "missing_table":
        sqlite3.connect(database).close()
    elif database_state == "no_rows":
        _write_schema_database(database, ())
    elif database_state == "multiple_rows":
        _write_schema_database(database, (SCHEMA_HEAD, "aaaaaaaaaaaa"))
    elif database_state == "invalid_head":
        _write_schema_database(database, ("not a revision",))

    with pytest.raises(DeploymentManifestError, match="eidp.sqlite3|alembic_version|schema"):
        collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    if database_state == "missing":
        assert not database.exists()


@pytest.mark.parametrize("unsafe_source", ("nested_git_root", "database_symlink", "data_symlink"))
def test_collection_rejects_source_paths_outside_the_project_boundary(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    tmp_path: Path,
    unsafe_source: str,
) -> None:
    app_root = repo.path
    if unsafe_source == "nested_git_root":
        app_root = repo.path / "nested"
        app_root.mkdir()
    else:
        outside = tmp_path / "outside-data"
        outside.mkdir()
        outside_database = outside / "eidp.sqlite3"
        _write_schema_database(outside_database)
        database = repo.path / "data" / "eidp.sqlite3"
        database.unlink()
        if unsafe_source == "database_symlink":
            database.symlink_to(outside_database)
        else:
            (repo.path / "data").rmdir()
            (repo.path / "data").symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        DeploymentManifestError,
        match="project root|project-local|symlink|eidp.sqlite3|clean checkout",
    ):
        collect_deployment_manifest(app_root=app_root, runtime=runtime, actor="operator")


def test_collection_records_only_exact_whitelisted_runtime_and_source_fields(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "proxy-secret-must-not-appear"
    monkeypatch.setenv("EIDP_PROXY_SHARED_SECRET", secret)
    before = datetime.now(UTC)

    result = collect_deployment_manifest(
        app_root=repo.path,
        runtime=runtime,
        actor="一貴 PI",
        pre_upgrade_backup_id="backup-20260712",
        off_host_receipt_id="receipt:20260712",
    )
    after = datetime.now(UTC)
    timestamp = datetime.fromisoformat(result.deployed_at_utc.replace("Z", "+00:00"))

    assert result.deployed_commit == repo.head
    assert result.expected_deployment_commit == repo.head
    assert result.origin_main_commit == repo.head
    assert result.uv_lock_sha256 == hashlib.sha256((repo.path / "uv.lock").read_bytes()).hexdigest()
    assert result.schema_head == SCHEMA_HEAD
    assert before <= timestamp <= after
    assert result.operator == "一貴 PI"
    assert result.internal_base_url == runtime.internal_base_url
    assert result.port == runtime.port
    assert result.base_url_path == runtime.base_url_path
    assert result.pre_upgrade_backup_id == "backup-20260712"
    assert result.off_host_receipt_id == "receipt:20260712"
    assert set(asdict(result)) == set(DeploymentManifest.__dataclass_fields__)
    assert secret not in json.dumps(asdict(result), sort_keys=True)


def test_collection_ignores_inherited_git_repository_redirection(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside-repository"
    outside.mkdir()
    outside_repo = RepoFixture(outside)
    outside_repo.git("init", "-b", "main")
    outside_repo.git("config", "user.name", "Outside Test")
    outside_repo.git("config", "user.email", "outside@example.invalid")
    (outside / "outside.txt").write_text("outside\n", encoding="utf-8")
    outside_repo.git("add", "outside.txt")
    outside_repo.git("commit", "-m", "outside source")
    expected_head = repo.head
    monkeypatch.setenv("GIT_DIR", str(outside / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(outside))

    result = collect_deployment_manifest(app_root=repo.path, runtime=runtime, actor="operator")

    assert result.deployed_commit == expected_head


@pytest.mark.parametrize("mutation", ("head_commit", "uv_lock", "explicit_origin_advance"))
def test_collection_rejects_source_changes_between_pre_and_post_snapshots(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    deployed = repo.head
    original_source_commits = deployment_manifest_module._source_commits
    calls = 0

    def mutate_after_pre_snapshot(app_root: Path, expected: str | None) -> tuple[str, str, str]:
        nonlocal calls
        calls += 1
        snapshot = original_source_commits(app_root, expected)
        if calls == 1:
            if mutation == "head_commit":
                (repo.path / "tracked.txt").write_text("new deployed source\n", encoding="utf-8")
                repo.git("add", "tracked.txt")
                repo.git("commit", "-m", "change during manifest collection")
                repo.set_origin_main(repo.head)
            elif mutation == "uv_lock":
                (repo.path / "uv.lock").write_text("version = 2\n", encoding="utf-8")
            else:
                repo.set_origin_main(repo.commit_tree(parent=deployed))
        return snapshot

    monkeypatch.setattr(deployment_manifest_module, "_source_commits", mutate_after_pre_snapshot)
    expected = deployed if mutation == "explicit_origin_advance" else None

    with pytest.raises(DeploymentManifestError, match="changed|stable|clean checkout"):
        collect_deployment_manifest(
            app_root=repo.path,
            runtime=runtime,
            actor="operator",
            expected_deployment_commit=expected,
        )

    assert calls == 2


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("actor", ""),
        ("actor", " operator"),
        ("actor", "x" * 129),
        ("pre_upgrade_backup_id", "bad/value"),
        ("off_host_receipt_id", "bad\nreceipt"),
    ),
)
def test_collection_rejects_unbounded_or_non_identifier_metadata(
    repo: RepoFixture,
    runtime: RuntimeLaunchConfig,
    field: str,
    value: str,
) -> None:
    arguments: dict[str, str | Path | RuntimeLaunchConfig | None] = {
        "app_root": repo.path,
        "runtime": runtime,
        "actor": "operator",
        "pre_upgrade_backup_id": None,
        "off_host_receipt_id": None,
    }
    arguments[field] = value

    with pytest.raises(DeploymentManifestError, match="operator|identifier|backup|receipt"):
        collect_deployment_manifest(**arguments)  # type: ignore[arg-type]

    if field != "actor":
        assert IDENTIFIER_PATTERN.fullmatch(value) is None


def test_atomic_write_fsyncs_file_then_replaces_then_fsyncs_directory_with_mode_0600(
    tmp_path: Path,
    manifest: DeploymentManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    target = run_dir / "deployment-manifest.json"
    events: list[str] = []
    original_fsync = os.fsync
    original_replace = os.replace

    def record_fsync(descriptor: int) -> None:
        mode = os.fstat(descriptor).st_mode
        events.append("file-fsync" if stat.S_ISREG(mode) else "directory-fsync")
        original_fsync(descriptor)

    def record_replace(source: str | bytes | Path, destination: str | bytes | Path, **kwargs: int) -> None:
        if "src_dir_fd" in kwargs or "dst_dir_fd" in kwargs:
            assert kwargs["src_dir_fd"] == kwargs["dst_dir_fd"]
        else:
            assert Path(source).parent == Path(destination).parent
        events.append("replace")
        original_replace(source, destination, **kwargs)

    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(os, "replace", record_replace)

    write_deployment_manifest_atomic(target, manifest)

    assert events.index("file-fsync") < events.index("replace") < events.index("directory-fsync")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert json.loads(target.read_text(encoding="utf-8")) == asdict(manifest)
    assert [path.name for path in run_dir.iterdir()] == [target.name]


def test_atomic_write_replaces_an_existing_manifest_and_cleans_temp_on_failure(
    tmp_path: Path,
    manifest: DeploymentManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    target = run_dir / "deployment-manifest.json"
    write_deployment_manifest_atomic(target, manifest)
    replacement = replace(manifest, operator="second-operator")
    write_deployment_manifest_atomic(target, replacement)
    assert json.loads(target.read_text(encoding="utf-8"))["operator"] == "second-operator"

    original = target.read_bytes()

    def fail_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(DeploymentManifestError, match="replace failed"):
        write_deployment_manifest_atomic(target, replace(manifest, operator="third-operator"))

    assert target.read_bytes() == original
    assert [path.name for path in run_dir.iterdir()] == [target.name]


def test_atomic_write_surfaces_a_temporary_file_cleanup_failure(
    tmp_path: Path,
    manifest: DeploymentManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    target = run_dir / "deployment-manifest.json"
    monkeypatch.setattr(os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("replace failed")))
    monkeypatch.setattr(
        os,
        "unlink",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("cleanup denied")),
    )

    with pytest.raises(DeploymentManifestError, match="clean up temporary deployment manifest"):
        write_deployment_manifest_atomic(target, manifest)


def test_atomic_write_never_unlinks_a_preexisting_random_temp_name(
    tmp_path: Path,
    manifest: DeploymentManifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    target = run_dir / "deployment-manifest.json"
    preexisting = run_dir / ".deployment-manifest.json.fixed.tmp"
    preexisting.write_text("not created by this invocation\n", encoding="utf-8")
    monkeypatch.setattr("eidp.ops.deployment_manifest.secrets.token_hex", lambda _length: "fixed")

    with pytest.raises(DeploymentManifestError):
        write_deployment_manifest_atomic(target, manifest)

    assert preexisting.read_text(encoding="utf-8") == "not created by this invocation\n"


def test_writer_and_controller_use_one_shared_manifest_projection(
    repo: RepoFixture,
    manifest: DeploymentManifest,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from eidp.ops import runtime_controller

    projection = {"projection_contract": "only-this-whitelist"}
    monkeypatch.setattr(
        deployment_manifest_module,
        "deployment_manifest_payload",
        lambda _manifest: projection,
        raising=False,
    )
    monkeypatch.setattr(
        runtime_controller,
        "deployment_manifest_payload",
        lambda _manifest: projection,
        raising=False,
    )

    direct_target = repo.path / "run" / "direct-deployment-manifest.json"
    direct_target.parent.mkdir()
    write_deployment_manifest_atomic(direct_target, manifest)
    assert json.loads(direct_target.read_text(encoding="utf-8")) == projection

    monkeypatch.setenv("EIDP_APP_ROOT", str(repo.path))
    result = runtime_controller.main(("manifest", "--actor", "operator"))
    output = json.loads(capsys.readouterr().out)
    persisted = json.loads((repo.path / "run" / "deployment-manifest.json").read_text(encoding="utf-8"))

    assert result == 0
    assert output == persisted == projection


@pytest.mark.parametrize("unsafe_path", ("final_symlink", "parent_symlink"))
def test_atomic_write_refuses_symlink_final_and_parent_paths(
    tmp_path: Path,
    manifest: DeploymentManifest,
    unsafe_path: str,
) -> None:
    root = tmp_path / "app"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_target = outside / "deployment-manifest.json"
    outside_target.write_text("must remain unchanged\n", encoding="utf-8")
    run_dir = root / "run"
    if unsafe_path == "parent_symlink":
        run_dir.symlink_to(outside, target_is_directory=True)
    else:
        run_dir.mkdir()
        (run_dir / "deployment-manifest.json").symlink_to(outside_target)

    with pytest.raises(DeploymentManifestError, match="unsafe|symlink"):
        write_deployment_manifest_atomic(run_dir / "deployment-manifest.json", manifest)

    assert outside_target.read_text(encoding="utf-8") == "must remain unchanged\n"


def test_controller_manifest_command_loads_runtime_and_writes_only_whitelisted_result(
    repo: RepoFixture,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from eidp.ops import runtime_controller

    secret = "controller-secret-must-not-appear"
    (repo.path / ".env").write_text(
        "\n".join(
            (
                "EIDP_WEB_PORT=18502",
                "EIDP_WEB_BASE_URL_PATH=/eidp",
                "EIDP_INTERNAL_BASE_URL=https://eidp.internal.example/eidp",
                "EIDP_WEB_MAX_UPLOAD_MB=200",
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EIDP_APP_ROOT", str(repo.path))
    monkeypatch.setenv("EIDP_PROXY_SHARED_SECRET", secret)

    result = runtime_controller.main(
        (
            "manifest",
            "--actor",
            "release-operator",
            "--expected-deployment-commit",
            repo.head,
            "--pre-upgrade-backup-id",
            "backup-20260712",
            "--off-host-receipt-id",
            "receipt:20260712",
        )
    )

    output = capsys.readouterr()
    target = repo.path / "run" / "deployment-manifest.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert result == 0
    assert json.loads(output.out) == payload
    assert output.err == ""
    assert payload["operator"] == "release-operator"
    assert payload["port"] == 18502
    assert payload["base_url_path"] == "/eidp"
    assert payload["pre_upgrade_backup_id"] == "backup-20260712"
    assert payload["off_host_receipt_id"] == "receipt:20260712"
    assert set(payload) == set(DeploymentManifest.__dataclass_fields__)
    assert secret not in output.out
    assert secret not in target.read_text(encoding="utf-8")
    assert list((repo.path / "run").glob("*.json")) == [target]


def test_controller_manifest_requires_actor_and_valid_runtime_config(
    repo: RepoFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eidp.ops import runtime_controller

    monkeypatch.setenv("EIDP_APP_ROOT", str(repo.path))
    with pytest.raises(SystemExit) as missing_actor:
        runtime_controller.main(("manifest",))
    assert missing_actor.value.code == 2

    (repo.path / ".env").write_text("EIDP_WEB_PORT=not-a-port\n", encoding="utf-8")
    with pytest.raises(SystemExit) as invalid_runtime:
        runtime_controller.main(("manifest", "--actor", "operator"))
    assert invalid_runtime.value.code == 2
    assert not (repo.path / "run" / "deployment-manifest.json").exists()
