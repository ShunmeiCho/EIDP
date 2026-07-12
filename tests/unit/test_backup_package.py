from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import socket
import sqlite3
import stat
from dataclasses import fields
from pathlib import Path

import pytest

from eidp.db.locking import acquire_lock
from eidp.ops import backup_package as backup_package_module
from eidp.ops.backup_package import (
    BackupPackageError,
    BackupPackageResult,
    VerifiedPreUpgradeSnapshot,
    build_backup_package,
    build_pre_upgrade_snapshot,
    verify_backup_package,
)

SCHEMA_HEAD = "7b8c9d0e1f2a"
DEPLOYMENT_COMMIT = "a" * 40


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES (?)", (SCHEMA_HEAD,))
        connection.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES ('preserved')")


def _deployment_payload() -> dict[str, str | int | None]:
    return {
        "deployed_commit": DEPLOYMENT_COMMIT,
        "expected_deployment_commit": DEPLOYMENT_COMMIT,
        "origin_main_commit": DEPLOYMENT_COMMIT,
        "uv_lock_sha256": "b" * 64,
        "schema_head": SCHEMA_HEAD,
        "deployed_at_utc": "2026-07-12T01:02:03Z",
        "operator": "deploy-operator",
        "internal_base_url": "https://eidp.internal.example",
        "port": 8502,
        "base_url_path": "",
        "pre_upgrade_backup_id": None,
        "off_host_receipt_id": None,
    }


@pytest.fixture
def package_root(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    (root / "run").mkdir(parents=True)
    (root / "data" / "audit").mkdir(parents=True)
    (root / "data" / "source-pdfs").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "cache").mkdir()
    _write_database(root / "data" / "eidp.sqlite3")
    (root / "data" / "master.xlsx").write_bytes(b"read-only master")
    os.chmod(root / "data" / "master.xlsx", 0o444)
    (root / "data" / "audit" / "manual-actions.jsonl").write_text(
        '{"action_id":"act-1"}\n', encoding="utf-8"
    )
    pdf = b"synthetic source pdf"
    cas = hashlib.sha256(pdf).hexdigest()
    cas_path = root / "data" / "source-pdfs" / cas[:2] / f"{cas}.pdf"
    cas_path.parent.mkdir()
    cas_path.write_bytes(pdf)
    (root / "run" / "deployment-manifest.json").write_text(
        json.dumps(_deployment_payload(), sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / ".env").write_text("EIDP_PROXY_SHARED_SECRET=never-copy\n", encoding="utf-8")
    (root / "logs" / "web.log").write_text("never copy\n", encoding="utf-8")
    (root / "cache" / "secret.bin").write_bytes(b"never copy")
    (root / "run" / "eidp.pid.json").write_text("{}\n", encoding="utf-8")
    return root


def _build(root: Path, backup_id: str = "backup-20260712") -> BackupPackageResult:
    with acquire_lock(root / "data" / ".lock", owner="test_backup_package"):
        return build_backup_package(
            app_root=root,
            database_path=root / "data" / "eidp.sqlite3",
            backup_id=backup_id,
            deployment_manifest=root / "run" / "deployment-manifest.json",
            actor="operator",
        )


def _manifest(package: Path) -> dict[str, object]:
    return json.loads((package / "backup-manifest.v1.json").read_text(encoding="utf-8"))


def _tree_bytes(package: Path) -> dict[str, bytes]:
    return {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }


def _reseal_manifest(package: Path, mutate: object) -> None:
    manifest_path = package / "backup-manifest.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert callable(mutate)
    mutate(payload)
    manifest_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    (package / "FINALIZED").write_text(_sha256(manifest_path) + "\n", encoding="ascii")


def test_public_results_and_signatures_are_stable() -> None:
    assert [field.name for field in fields(BackupPackageResult)] == [
        "backup_id",
        "finalized_path",
        "manifest_sha256",
    ]
    assert [field.name for field in fields(VerifiedPreUpgradeSnapshot)] == [
        "snapshot_path",
        "manifest_path",
        "snapshot_sha256",
        "source_database_relative_path",
        "deployment_commit",
        "schema_head",
    ]
    build_parameters = inspect.signature(build_backup_package).parameters
    assert list(build_parameters) == ["app_root", "database_path", "backup_id", "deployment_manifest", "actor"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in build_parameters.values())
    verify_parameters = inspect.signature(verify_backup_package).parameters
    assert list(verify_parameters) == ["path"]
    assert verify_parameters["path"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    upgrade_parameters = inspect.signature(build_pre_upgrade_snapshot).parameters
    assert list(upgrade_parameters) == ["app_root", "database_path", "upgrade_id", "deployment_commit"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in upgrade_parameters.values())


def test_build_requires_the_exact_current_thread_data_lock(package_root: Path) -> None:
    arguments = {
        "app_root": package_root,
        "database_path": package_root / "data/eidp.sqlite3",
        "backup_id": "backup-exact-lock",
        "deployment_manifest": package_root / "run/deployment-manifest.json",
        "actor": "operator",
    }
    with pytest.raises(BackupPackageError, match="lock.*held|held.*lock"):
        build_backup_package(**arguments)

    with acquire_lock(package_root / "data/other.lock", owner="wrong_lock"):
        with pytest.raises(BackupPackageError, match="lock.*held|held.*lock"):
            build_backup_package(**arguments)


def test_build_creates_only_allowlisted_inventory_and_finalizes_last(package_root: Path) -> None:
    result = _build(package_root)
    package = package_root / "backups" / "backup-20260712"

    assert result == BackupPackageResult(
        backup_id="backup-20260712",
        finalized_path=package,
        manifest_sha256=_sha256(package / "backup-manifest.v1.json"),
    )
    manifest = _manifest(package)
    inventory = manifest["inventory"]
    assert isinstance(inventory, list)
    inventory_paths = [entry["path"] for entry in inventory]
    cas_paths = [path for path in inventory_paths if path.startswith("data/source-pdfs/")]
    expected_paths = {
        "data/eidp.sqlite3",
        "data/master.xlsx",
        "data/audit/manual-actions.jsonl",
        "run/deployment-manifest.json",
        *cas_paths,
    }
    assert set(inventory_paths) == expected_paths
    assert inventory_paths == sorted(inventory_paths)
    assert len(cas_paths) == 1
    cas_name = Path(cas_paths[0]).stem
    assert len(cas_name) == 64
    assert cas_name == _sha256(package / cas_paths[0])
    assert manifest["schema"] == "eidp.backup-manifest.v1"
    assert manifest["backup_id"] == "backup-20260712"
    assert manifest["deployment_commit"] == DEPLOYMENT_COMMIT
    assert manifest["schema_head"] == SCHEMA_HEAD
    assert manifest["source_database_relative_path"] == "data/eidp.sqlite3"
    assert manifest["sqlite_snapshot_sha256"] == _sha256(package / "data/eidp.sqlite3")
    assert manifest["wal_checkpoint_succeeded"] is True
    assert manifest["actor"] == "operator"
    assert manifest["optional_roots"] == {
        "data/audit": True,
        "data/source-pdfs": True,
        "data/web-intake": False,
        "output/exports": False,
    }
    assert "off_host_receipt_id" not in manifest
    assert (package / "FINALIZED").read_text(encoding="ascii") == result.manifest_sha256 + "\n"
    assert stat.S_IMODE((package / "data/master.xlsx").stat().st_mode) & stat.S_IWUSR == 0
    assert not (package / ".env").exists()
    assert not (package / "logs").exists()
    assert not (package / "cache").exists()
    assert not (package / "run/eidp.pid.json").exists()
    assert not (package / "backups").exists()


def test_present_optional_roots_are_inventoried_while_arbitrary_trees_and_sqlite_sidecars_are_excluded(
    package_root: Path,
) -> None:
    (package_root / "data/web-intake").mkdir()
    (package_root / "data/web-intake/queue.json").write_text("{}\n", encoding="utf-8")
    (package_root / "output/exports").mkdir(parents=True)
    (package_root / "output/exports/export.xlsx").write_bytes(b"export")
    (package_root / "data/unrelated").mkdir()
    (package_root / "data/unrelated/secret.txt").write_text("exclude\n", encoding="utf-8")
    (package_root / "output/unrelated").mkdir(parents=True)
    (package_root / "output/unrelated/secret.txt").write_text("exclude\n", encoding="utf-8")
    (package_root / "data/eidp.sqlite3-wal").write_bytes(b"exclude wal")
    (package_root / "data/eidp.sqlite3-shm").write_bytes(b"exclude shm")
    (package_root / "backups/older").mkdir(parents=True)
    (package_root / "backups/older/secret.txt").write_text("exclude\n", encoding="utf-8")

    built = _build(package_root, "backup-allowlist")
    manifest = _manifest(built.finalized_path)
    inventory_paths = {entry["path"] for entry in manifest["inventory"]}

    assert manifest["optional_roots"] == {
        "data/audit": True,
        "data/source-pdfs": True,
        "data/web-intake": True,
        "output/exports": True,
    }
    assert "data/web-intake/queue.json" in inventory_paths
    assert "output/exports/export.xlsx" in inventory_paths
    assert not any("unrelated" in path for path in inventory_paths)
    assert "data/eidp.sqlite3-wal" not in inventory_paths
    assert "data/eidp.sqlite3-shm" not in inventory_paths
    assert not any(path.startswith("backups/") for path in inventory_paths)


def test_verify_is_read_only_and_checks_packaged_sqlite(package_root: Path) -> None:
    built = _build(package_root)
    before = _tree_bytes(built.finalized_path)
    with sqlite3.connect(built.finalized_path / "data/eidp.sqlite3") as connection:
        assert connection.execute("SELECT value FROM evidence").fetchone() == ("preserved",)
    os.chmod(built.finalized_path / "data/eidp.sqlite3", 0o444)

    verified = verify_backup_package(built.finalized_path)

    assert verified == built
    assert _tree_bytes(built.finalized_path) == before


@pytest.mark.parametrize("tamper", ("content", "extra", "marker", "manifest"))
def test_verify_rejects_tamper_without_repairing(package_root: Path, tamper: str) -> None:
    built = _build(package_root)
    package = built.finalized_path
    if tamper == "content":
        target = package / "data/audit/manual-actions.jsonl"
        target.write_text("tampered\n", encoding="utf-8")
    elif tamper == "extra":
        target = package / "unexpected.txt"
        target.write_text("extra\n", encoding="utf-8")
    elif tamper == "marker":
        target = package / "FINALIZED"
        target.write_text("0" * 64 + "\n", encoding="ascii")
    else:
        target = package / "backup-manifest.v1.json"
        target.write_text("{}\n", encoding="utf-8")
    before = target.read_bytes()

    with pytest.raises(BackupPackageError):
        verify_backup_package(package)

    assert target.read_bytes() == before


def test_verify_never_accepts_or_repairs_unfinalized_evidence(package_root: Path) -> None:
    built = _build(package_root)
    marker = built.finalized_path / "FINALIZED"
    marker.unlink()

    with pytest.raises(BackupPackageError, match="not finalized"):
        verify_backup_package(built.finalized_path)

    assert not marker.exists()


def test_verify_rejects_self_consistent_finalized_content_below_staging(package_root: Path) -> None:
    built = _build(package_root)
    staged = package_root / "backups/.staging" / built.backup_id
    shutil.copytree(built.finalized_path, staged)

    with pytest.raises(BackupPackageError, match="staging|finalized.*layout|layout.*finalized"):
        verify_backup_package(staged)


def test_public_verify_accepts_a_finalized_off_host_copy_outside_local_backups(package_root: Path) -> None:
    built = _build(package_root)
    incoming = package_root / "restore-drills/incoming" / built.backup_id
    incoming.parent.mkdir(parents=True)
    shutil.copytree(built.finalized_path, incoming)

    verified = verify_backup_package(incoming)

    assert verified.backup_id == built.backup_id
    assert verified.finalized_path == incoming
    assert verified.manifest_sha256 == built.manifest_sha256


@pytest.mark.parametrize(
    ("root_name", "declared_present"),
    (("data/audit", False), ("data/web-intake", True)),
)
def test_verify_requires_optional_root_presence_to_match_the_actual_tree(
    package_root: Path,
    root_name: str,
    declared_present: bool,
) -> None:
    built = _build(package_root)

    def contradict(payload: dict[str, object]) -> None:
        optional = payload["optional_roots"]
        assert isinstance(optional, dict)
        optional[root_name] = declared_present

    _reseal_manifest(built.finalized_path, contradict)

    with pytest.raises(BackupPackageError, match="optional.*root|root.*presence|missing or extra directories"):
        verify_backup_package(built.finalized_path)


def test_same_id_is_idempotent_and_build_completes_only_valid_missing_marker(package_root: Path) -> None:
    first = _build(package_root)
    before = _tree_bytes(first.finalized_path)

    assert _build(package_root) == first
    assert _tree_bytes(first.finalized_path) == before

    (first.finalized_path / "FINALIZED").unlink()
    recovered = _build(package_root)
    assert recovered == first
    assert (first.finalized_path / "FINALIZED").read_text(encoding="ascii") == first.manifest_sha256 + "\n"


def test_same_id_never_overwrites_conflicting_final(package_root: Path) -> None:
    built = _build(package_root)
    target = built.finalized_path / "data/audit/manual-actions.jsonl"
    target.write_text("conflict\n", encoding="utf-8")
    before = _tree_bytes(built.finalized_path)

    with pytest.raises(BackupPackageError):
        _build(package_root)

    assert _tree_bytes(built.finalized_path) == before


def test_retry_after_final_marker_fsync_failure_reestablishes_durability(
    package_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_id = "backup-fsync-retry"
    original_fsync = backup_package_module._fsync_directory
    failed = False

    def fail_after_marker(path: Path) -> None:
        nonlocal failed
        if path.name == backup_id and (path / "FINALIZED").exists() and not failed:
            failed = True
            raise BackupPackageError("injected finalized directory fsync failure")
        original_fsync(path)

    monkeypatch.setattr(backup_package_module, "_fsync_directory", fail_after_marker)
    with pytest.raises(BackupPackageError, match="fsync failure"):
        _build(package_root, backup_id)
    final = package_root / "backups" / backup_id
    assert (final / "FINALIZED").is_file()

    observed: list[Path] = []

    def record_fsync(path: Path) -> None:
        observed.append(path)
        original_fsync(path)

    monkeypatch.setattr(backup_package_module, "_fsync_directory", record_fsync)
    retried = _build(package_root, backup_id)

    assert retried.finalized_path == final
    assert final in observed
    assert package_root / "backups" in observed


@pytest.mark.parametrize("unsafe", ("backup_id", "database", "manifest", "optional_file", "optional_root"))
def test_build_refuses_traversal_outside_sources_and_symlinks(
    package_root: Path,
    tmp_path: Path,
    unsafe: str,
) -> None:
    database = package_root / "data/eidp.sqlite3"
    deployment = package_root / "run/deployment-manifest.json"
    backup_id = "backup-safe"
    outside = tmp_path / "outside"
    outside.mkdir()
    if unsafe == "backup_id":
        backup_id = "../escape"
    elif unsafe == "database":
        database = outside / "database.sqlite3"
        _write_database(database)
    elif unsafe == "manifest":
        deployment = outside / "deployment.json"
        deployment.write_text(json.dumps(_deployment_payload()), encoding="utf-8")
    elif unsafe == "optional_file":
        secret = outside / "secret"
        secret.write_text("outside\n", encoding="utf-8")
        (package_root / "data/audit/linked.jsonl").symlink_to(secret)
    else:
        (package_root / "data/audit/manual-actions.jsonl").unlink()
        (package_root / "data/audit").rmdir()
        (package_root / "data/audit").symlink_to(outside, target_is_directory=True)

    with acquire_lock(package_root / "data/.lock", owner="test_unsafe"):
        with pytest.raises(BackupPackageError, match="unsafe|inside|symlink|backup ID|project"):
            build_backup_package(
                app_root=package_root,
                database_path=database,
                backup_id=backup_id,
                deployment_manifest=deployment,
                actor="operator",
            )

    assert not (tmp_path / "escape").exists()


def test_build_interruption_never_creates_finalized_evidence(
    package_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def interrupt(_source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"partial")
        raise RuntimeError("interrupted")

    monkeypatch.setattr(backup_package_module, "backup_sqlite_database", interrupt)
    with acquire_lock(package_root / "data/.lock", owner="test_interrupt"):
        with pytest.raises(BackupPackageError, match="interrupted"):
            build_backup_package(
                app_root=package_root,
                database_path=package_root / "data/eidp.sqlite3",
                backup_id="backup-interrupted",
                deployment_manifest=package_root / "run/deployment-manifest.json",
                actor="operator",
            )

    assert not (package_root / "backups/backup-interrupted").exists()
    for staging in (package_root / "backups/.staging").glob("*"):
        assert not (staging / "FINALIZED").exists()


@pytest.mark.parametrize("non_regular", ("fifo", "socket"))
def test_build_rejects_non_regular_optional_entries(
    package_root: Path,
    non_regular: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsafe = package_root / "data/audit" / non_regular
    listener: socket.socket | None = None
    if non_regular == "fifo":
        os.mkfifo(unsafe)
    else:
        listener = socket.socket(socket.AF_UNIX)
        monkeypatch.chdir(unsafe.parent)
        listener.bind(unsafe.name)
    try:
        with pytest.raises(BackupPackageError, match="non-regular|unsafe"):
            _build(package_root, f"backup-{non_regular}")
    finally:
        if listener is not None:
            listener.close()


@pytest.mark.parametrize("binding", ("deployment_commit", "deployment_schema", "sqlite_multi_head"))
def test_verify_rejects_rebound_but_semantically_conflicting_evidence(package_root: Path, binding: str) -> None:
    built = _build(package_root)
    package = built.finalized_path
    artifact_relative = "run/deployment-manifest.json"
    if binding == "sqlite_multi_head":
        artifact_relative = "data/eidp.sqlite3"
        with sqlite3.connect(package / artifact_relative) as connection:
            connection.execute("INSERT INTO alembic_version VALUES ('bbbbbbbbbbbb')")
    else:
        deployment_path = package / artifact_relative
        deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
        if binding == "deployment_commit":
            deployment["deployed_commit"] = "c" * 40
        else:
            deployment["schema_head"] = "bbbbbbbbbbbb"
        deployment_path.write_text(json.dumps(deployment, sort_keys=True) + "\n", encoding="utf-8")

    def rebind(payload: dict[str, object]) -> None:
        inventory = payload["inventory"]
        assert isinstance(inventory, list)
        artifact = package / artifact_relative
        for entry in inventory:
            assert isinstance(entry, dict)
            if entry["path"] == artifact_relative:
                entry["size"] = artifact.stat().st_size
                entry["sha256"] = _sha256(artifact)
        digest_key = "sqlite_snapshot_sha256" if binding == "sqlite_multi_head" else "deployment_manifest_sha256"
        payload[digest_key] = _sha256(artifact)

    _reseal_manifest(package, rebind)

    with pytest.raises(BackupPackageError, match="schema|commit|Alembic|binding"):
        verify_backup_package(package)


def test_pre_upgrade_snapshot_requires_current_data_lock_and_binds_evidence(package_root: Path) -> None:
    database = package_root / "data/eidp.sqlite3"
    with pytest.raises(BackupPackageError, match="lock.*held|held.*lock"):
        build_pre_upgrade_snapshot(
            app_root=package_root,
            database_path=database,
            upgrade_id="upgrade-20260712",
            deployment_commit=DEPLOYMENT_COMMIT,
        )

    with acquire_lock(package_root / "data/.lock", owner="test_pre_upgrade"):
        result = build_pre_upgrade_snapshot(
            app_root=package_root,
            database_path=database,
            upgrade_id="upgrade-20260712",
            deployment_commit=DEPLOYMENT_COMMIT,
        )

    assert isinstance(result, VerifiedPreUpgradeSnapshot)
    assert result.snapshot_path == package_root / "backups/pre-upgrade/upgrade-20260712/eidp.sqlite3"
    assert result.manifest_path == package_root / "backups/pre-upgrade/upgrade-20260712/pre-upgrade-manifest.v1.json"
    assert result.snapshot_sha256 == _sha256(result.snapshot_path)
    assert result.source_database_relative_path == "data/eidp.sqlite3"
    assert result.deployment_commit == DEPLOYMENT_COMMIT
    assert result.schema_head == SCHEMA_HEAD
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest == {
        "deployment_commit": DEPLOYMENT_COMMIT,
        "schema": "eidp.pre-upgrade-snapshot.v1",
        "schema_head": SCHEMA_HEAD,
        "snapshot_sha256": result.snapshot_sha256,
        "source_database_relative_path": "data/eidp.sqlite3",
        "upgrade_id": "upgrade-20260712",
    }
    with sqlite3.connect(f"file:{result.snapshot_path}?mode=ro&immutable=1", uri=True) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]


def test_pre_upgrade_retry_after_publication_fsync_failure_reestablishes_durability(
    package_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upgrade_id = "upgrade-fsync-retry"
    database = package_root / "data/eidp.sqlite3"
    pre_upgrade_root = package_root / "backups/pre-upgrade"
    final = pre_upgrade_root / upgrade_id
    original_fsync = backup_package_module._fsync_directory
    failed = False

    def fail_after_publish(path: Path) -> None:
        nonlocal failed
        if path == pre_upgrade_root and final.exists() and not failed:
            failed = True
            raise BackupPackageError("injected pre-upgrade parent fsync failure")
        original_fsync(path)

    monkeypatch.setattr(backup_package_module, "_fsync_directory", fail_after_publish)
    with acquire_lock(package_root / "data/.lock", owner="test_pre_upgrade_fsync"):
        with pytest.raises(BackupPackageError, match="fsync failure"):
            build_pre_upgrade_snapshot(
                app_root=package_root,
                database_path=database,
                upgrade_id=upgrade_id,
                deployment_commit=DEPLOYMENT_COMMIT,
            )
    assert final.is_dir()

    observed: list[Path] = []

    def record_fsync(path: Path) -> None:
        observed.append(path)
        original_fsync(path)

    monkeypatch.setattr(backup_package_module, "_fsync_directory", record_fsync)
    with acquire_lock(package_root / "data/.lock", owner="test_pre_upgrade_retry"):
        retried = build_pre_upgrade_snapshot(
            app_root=package_root,
            database_path=database,
            upgrade_id=upgrade_id,
            deployment_commit=DEPLOYMENT_COMMIT,
        )

    assert retried.snapshot_path == final / "eidp.sqlite3"
    assert final in observed
    assert pre_upgrade_root in observed
    assert package_root / "backups" in observed
