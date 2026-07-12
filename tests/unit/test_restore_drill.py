from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import signal
import socket
import sqlite3
import stat
import subprocess
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import pytest

from eidp.db.locking import acquire_lock
from eidp.ops import restore_drill as restore_drill_module
from eidp.ops.backup_package import (
    BackupPackageError,
    build_backup_package,
    verify_backup_package,
)
from eidp.ops.restore_drill import (
    RestoreDrillError,
    RestoreDrillResult,
    RestoreEvidenceExpectation,
    load_restore_evidence_expectation,
    run_restore_drill,
)

BACKUP_ID = "backup-20260712"
SCHEMA_HEAD = "7b8c9d0e1f2a"
EXPORT_ID = "01234567-89ab-4def-8abc-0123456789ab"
ACTION_IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git(app_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=app_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write_restore_database(
    path: Path,
    action_rows: tuple[tuple[str, str | None, str | None], ...] = (),
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES (?)", (SCHEMA_HEAD,))
        connection.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES ('restored-only')")
        connection.execute(
            """
            CREATE TABLE manual_action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL,
                jsonl_exported_at TEXT,
                jsonl_export_error TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO manual_action_log(action_id, jsonl_exported_at, jsonl_export_error)
            VALUES (?, ?, ?)
            """,
            action_rows,
        )


def _tree_bytes(root: Path, *, exclude_report: bool = False) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not (exclude_report and path.name == "restore-report.v1.json")
    }


def _unused_loopback_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _deployment_payload(*, commit: str, uv_lock_sha256: str) -> dict[str, str | int | None]:
    return {
        "deployed_commit": commit,
        "expected_deployment_commit": commit,
        "origin_main_commit": commit,
        "uv_lock_sha256": uv_lock_sha256,
        "schema_head": SCHEMA_HEAD,
        "deployed_at_utc": "2026-07-12T01:02:03Z",
        "operator": "restore-test-operator",
        "internal_base_url": "https://eidp.internal.example/eidp",
        "port": 8502,
        "base_url_path": "/eidp",
        "pre_upgrade_backup_id": None,
        "off_host_receipt_id": None,
    }


def _expectation_payload() -> dict[str, object]:
    return {
        "schema": "eidp.restore-evidence-expectation.v1",
        "export_id": EXPORT_ID,
        "workbook_sha256": "",
        "export_manifest_sha256": "",
        "action_ids": list(ACTION_IDS),
    }


@dataclass
class SyntheticRestore:
    app_root: Path
    package: Path
    target: Path
    deployment_commit: str
    uv_lock_sha256: str
    package_manifest_sha256: str
    live_facts: dict[str, tuple[bytes, int]]
    expectation_path: Path | None = None
    expectation: RestoreEvidenceExpectation | None = None

    def run(self, **overrides: object) -> RestoreDrillResult:
        arguments: dict[str, object] = {
            "app_root": self.app_root,
            "package_path": self.package,
            "target_path": self.target,
            "smoke_port": _unused_loopback_port(),
            "expected_package_manifest_sha256": self.package_manifest_sha256,
            "expected_evidence": self.expectation,
        }
        arguments.update(overrides)
        return run_restore_drill(**arguments)  # type: ignore[arg-type]


def _build_synthetic_restore(tmp_path: Path, *, with_acceptance: bool = False) -> SyntheticRestore:
    app_root = tmp_path / "app"
    app_root.mkdir()
    _git(app_root, "init", "-b", "main")
    _git(app_root, "config", "user.name", "EIDP Restore Test")
    _git(app_root, "config", "user.email", "restore@example.invalid")
    (app_root / ".gitignore").write_text(
        "\n".join(
            (
                "/.env",
                "/backups/",
                "/data/",
                "/evidence/",
                "/logs/",
                "/output/",
                "/restore-drills/",
                "/run/",
                "",
            )
        ),
        encoding="utf-8",
    )
    (app_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    web_app = app_root / "src/eidp/web/app.py"
    web_app.parent.mkdir(parents=True)
    web_app.write_text(
        "import streamlit as st\n"
        "st.set_page_config(page_title='Restore smoke')\n"
        "st.title('Isolated restore smoke')\n",
        encoding="utf-8",
    )
    _git(app_root, "add", ".gitignore", "uv.lock", "src/eidp/web/app.py")
    _git(app_root, "commit", "-m", "synthetic protected checkout")
    deployment_commit = _git(app_root, "rev-parse", "HEAD")
    _git(app_root, "remote", "add", "origin", str(tmp_path / "origin-not-contacted"))
    _git(app_root, "update-ref", "refs/remotes/origin/main", deployment_commit)
    uv_lock_sha256 = _sha256(app_root / "uv.lock")

    action_rows: tuple[tuple[str, str | None, str | None], ...] = ()
    if with_acceptance:
        action_rows = tuple((action_id, "2026-07-12T02:03:04Z", None) for action_id in ACTION_IDS)
    _write_restore_database(app_root / "data/eidp.sqlite3", action_rows)
    (app_root / "data/master.xlsx").write_bytes(b"live-master-must-not-change")
    audit_dir = app_root / "data/audit"
    audit_dir.mkdir()
    if with_acceptance:
        (audit_dir / "manual-actions.jsonl").write_text(
            json.dumps({"action_id": ACTION_IDS[0]}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (audit_dir / "manual-actions-20260712.jsonl").write_text(
            json.dumps({"action_id": ACTION_IDS[1]}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        (audit_dir / "manual-actions.jsonl").write_text(
            json.dumps({"action_id": "live-action"}, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    expectation_path: Path | None = None
    expectation: RestoreEvidenceExpectation | None = None
    if with_acceptance:
        workbook = app_root / "output/exports" / EXPORT_ID / "accepted.xlsx"
        workbook.parent.mkdir(parents=True)
        workbook.write_bytes(b"accepted restored workbook")
        export_manifest = workbook.parent / "export-manifest.v1.json"
        export_manifest.write_text(
            json.dumps(
                {
                    "schema": "eidp.export-manifest.v1",
                    "export_id": EXPORT_ID,
                    "lifecycle": "finalized",
                    "workbook_filename": workbook.name,
                    "workbook_sha256": _sha256(workbook),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        export_manifest_sha256 = _sha256(export_manifest)
        (workbook.parent / "FINALIZED").write_text(export_manifest_sha256 + "\n", encoding="ascii")
        expectation_path = app_root / "evidence/runtime/exports" / f"{EXPORT_ID}.json"
        expectation_path.parent.mkdir(parents=True)
        payload = _expectation_payload()
        payload["workbook_sha256"] = _sha256(workbook)
        payload["export_manifest_sha256"] = export_manifest_sha256
        expectation_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        expectation = RestoreEvidenceExpectation(
            export_id=EXPORT_ID,
            workbook_sha256=_sha256(workbook),
            export_manifest_sha256=export_manifest_sha256,
            action_ids=ACTION_IDS,
        )

    (app_root / "run").mkdir()
    (app_root / "run/deployment-manifest.json").write_text(
        json.dumps(_deployment_payload(commit=deployment_commit, uv_lock_sha256=uv_lock_sha256), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (app_root / "run/eidp.pid.json").write_text('{"pid":999999}\n', encoding="utf-8")
    (app_root / "logs").mkdir()
    (app_root / "logs/web.log").write_text("live log must remain unchanged\n", encoding="utf-8")
    (app_root / ".env").write_text(
        "EIDP_DATA_DIR=/must/not/be/read\nEIDP_PROXY_SHARED_SECRET=live-secret\n",
        encoding="utf-8",
    )
    (app_root / "restore-drills/verified").mkdir(parents=True)
    (app_root / "restore-drills/incoming").mkdir()

    with acquire_lock(app_root / "data/.lock", owner="test_restore_package"):
        built = build_backup_package(
            app_root=app_root,
            database_path=app_root / "data/eidp.sqlite3",
            backup_id=BACKUP_ID,
            deployment_manifest=app_root / "run/deployment-manifest.json",
            actor="restore-test-operator",
        )
    target = app_root / "restore-drills/verified" / BACKUP_ID
    return SyntheticRestore(
        app_root=app_root,
        package=built.finalized_path,
        target=target,
        deployment_commit=deployment_commit,
        uv_lock_sha256=uv_lock_sha256,
        package_manifest_sha256=built.manifest_sha256,
        live_facts=_fact_snapshot(app_root),
        expectation_path=expectation_path,
        expectation=expectation,
    )


@pytest.fixture
def synthetic_restore(tmp_path: Path) -> SyntheticRestore:
    return _build_synthetic_restore(tmp_path)


@pytest.fixture
def acceptance_restore(tmp_path: Path) -> SyntheticRestore:
    return _build_synthetic_restore(tmp_path, with_acceptance=True)


@pytest.fixture
def expectation_file(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    app_root = tmp_path / "app"
    path = app_root / "evidence/runtime/exports" / f"{EXPORT_ID}.json"
    path.parent.mkdir(parents=True)
    payload = _expectation_payload()
    payload["workbook_sha256"] = "a" * 64
    payload["export_manifest_sha256"] = "b" * 64
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return app_root, path, payload


def _reseal_package(package: Path) -> str:
    manifest_path = package / "backup-manifest.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory: list[dict[str, object]] = []
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package)
        if not path.is_file() or relative in {Path("backup-manifest.v1.json"), Path("FINALIZED")}:
            continue
        inventory.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    payload["inventory"] = inventory
    payload["sqlite_snapshot_sha256"] = _sha256(package / "data/eidp.sqlite3")
    payload["deployment_manifest_sha256"] = _sha256(package / "run/deployment-manifest.json")
    manifest_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    digest = _sha256(manifest_path)
    (package / "FINALIZED").write_text(digest + "\n", encoding="ascii")
    return digest


def _install_smoke_stub(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def healthy(*args: object, **kwargs: object) -> bool:
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(restore_drill_module, "_run_streamlit_smoke", healthy, raising=False)
    return calls


def _fact_snapshot(app_root: Path) -> dict[str, tuple[bytes, int]]:
    paths = (
        Path("data/eidp.sqlite3"),
        Path("data/master.xlsx"),
        Path("data/audit/manual-actions.jsonl"),
        Path("run/deployment-manifest.json"),
    )
    return {
        path.as_posix(): ((app_root / path).read_bytes(), (app_root / path).stat().st_mtime_ns)
        for path in paths
    }


@pytest.fixture
def restore_layout(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, tuple[bytes, int]]]:
    app_root = tmp_path / "app"
    package = app_root / "backups/backup-20260712"
    target = app_root / "restore-drills/verified/backup-20260712"
    package.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    (app_root / "restore-drills/incoming").mkdir(parents=True)
    (app_root / "data/audit").mkdir(parents=True)
    (app_root / "run").mkdir()
    (app_root / "data/eidp.sqlite3").write_bytes(b"live-db")
    (app_root / "data/master.xlsx").write_bytes(b"live-master")
    (app_root / "data/audit/manual-actions.jsonl").write_bytes(b'{"action_id":"live"}\n')
    (app_root / "run/deployment-manifest.json").write_bytes(b'{"live":true}\n')
    return app_root, package, target, _fact_snapshot(app_root)


def test_restore_public_results_and_signatures_are_exact() -> None:
    assert [field.name for field in fields(RestoreDrillResult)] == [
        "backup_id",
        "restored_path",
        "deployment_commit",
        "schema_head",
        "sqlite_integrity",
        "health_ok",
        "package_manifest_sha256",
        "off_host_receipt_id",
        "report_path",
    ]
    assert [field.name for field in fields(RestoreEvidenceExpectation)] == [
        "export_id",
        "workbook_sha256",
        "export_manifest_sha256",
        "action_ids",
    ]

    run_parameters = inspect.signature(run_restore_drill).parameters
    assert list(run_parameters) == [
        "app_root",
        "package_path",
        "target_path",
        "smoke_port",
        "expected_package_manifest_sha256",
        "off_host_receipt_id",
        "expected_evidence",
    ]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in run_parameters.values())
    assert run_parameters["smoke_port"].default == 18502
    assert run_parameters["expected_package_manifest_sha256"].default is None
    assert run_parameters["off_host_receipt_id"].default is None
    assert run_parameters["expected_evidence"].default is None

    loader_parameters = inspect.signature(load_restore_evidence_expectation).parameters
    assert list(loader_parameters) == ["app_root", "path"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in loader_parameters.values())


@pytest.mark.parametrize(
    "unsafe",
    (
        "package_outside",
        "package_nested",
        "package_staging",
        "package_traversal",
        "package_symlink",
        "target_outside",
        "target_live_data",
        "target_incoming",
        "target_nested",
        "target_basename_mismatch",
        "target_symlink_parent",
        "package_target_overlap",
    ),
)
def test_restore_rejects_unsafe_package_or_target_layout_before_writes(
    restore_layout: tuple[Path, Path, Path, dict[str, tuple[bytes, int]]],
    tmp_path: Path,
    unsafe: str,
) -> None:
    app_root, package, target, before = restore_layout
    if unsafe == "package_outside":
        package = tmp_path / "outside-package"
        package.mkdir()
    elif unsafe == "package_nested":
        package = app_root / "backups/nested/backup-20260712"
        package.mkdir(parents=True)
    elif unsafe == "package_staging":
        package = app_root / "backups/.staging/backup-20260712"
        package.mkdir(parents=True)
    elif unsafe == "package_traversal":
        package = app_root / "backups/../backups/backup-20260712"
    elif unsafe == "package_symlink":
        outside = tmp_path / "symlinked-package"
        outside.mkdir()
        package.rmdir()
        package.symlink_to(outside, target_is_directory=True)
    elif unsafe == "target_outside":
        target = tmp_path / "outside-target"
    elif unsafe == "target_live_data":
        target = app_root / "data"
    elif unsafe == "target_incoming":
        target = app_root / "restore-drills/incoming/backup-20260712"
    elif unsafe == "target_nested":
        target = app_root / "restore-drills/verified/nested/backup-20260712"
    elif unsafe == "target_basename_mismatch":
        target = app_root / "restore-drills/verified/different-backup"
    elif unsafe == "target_symlink_parent":
        outside = tmp_path / "symlinked-target-parent"
        outside.mkdir()
        verified = app_root / "restore-drills/verified"
        verified.rmdir()
        verified.symlink_to(outside, target_is_directory=True)
    else:
        target = package

    with pytest.raises(RestoreDrillError, match="package|target|layout|path|symlink|isolated|overlap|backup"):
        run_restore_drill(app_root=app_root, package_path=package, target_path=target)

    assert _fact_snapshot(app_root) == before
    if target != app_root / "data" and target != package:
        assert not target.exists()


@pytest.mark.parametrize(
    ("expected_digest", "receipt", "message"),
    (
        (None, "receipt:20260712", "digest|manifest"),
        ("0" * 64, None, "digest|manifest"),
        ("A" * 64, None, "lowercase|digest|SHA"),
        ("0" * 63, None, "digest|SHA|64"),
    ),
)
def test_restore_binds_receipt_to_an_exact_lowercase_package_manifest_digest(
    restore_layout: tuple[Path, Path, Path, dict[str, tuple[bytes, int]]],
    monkeypatch: pytest.MonkeyPatch,
    expected_digest: str | None,
    receipt: str | None,
    message: str,
) -> None:
    app_root, package, target, before = restore_layout
    verify_calls: list[tuple[int, str, str | None, str | None]] = []

    def record_source_verification(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        verify_calls.append(
            (directory_fd, expected_backup_id, expected_manifest_sha256, ignored_file)
        )
        return restore_drill_module._VerifiedPackageEvidence(
            backup_id="backup-20260712",
            manifest_sha256="1" * 64,
        )

    monkeypatch.setattr(restore_drill_module, "_verify_backup_package_fd", record_source_verification)

    with pytest.raises(RestoreDrillError, match=message):
        run_restore_drill(
            app_root=app_root,
            package_path=package,
            target_path=target,
            expected_package_manifest_sha256=expected_digest,
            off_host_receipt_id=receipt,
        )

    assert not target.exists()
    assert _fact_snapshot(app_root) == before
    assert len(verify_calls) == (1 if expected_digest == "0" * 64 and receipt is None else 0)


def test_synthetic_fixture_is_a_real_protected_checkout_and_finalized_task4_package(
    synthetic_restore: SyntheticRestore,
) -> None:
    verified = verify_backup_package(synthetic_restore.package)

    assert verified.backup_id == BACKUP_ID
    assert verified.manifest_sha256 == synthetic_restore.package_manifest_sha256
    assert _git(synthetic_restore.app_root, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert _git(synthetic_restore.app_root, "rev-parse", "HEAD") == synthetic_restore.deployment_commit
    assert (
        _git(synthetic_restore.app_root, "rev-parse", "refs/remotes/origin/main")
        == synthetic_restore.deployment_commit
    )
    assert _sha256(synthetic_restore.app_root / "uv.lock") == synthetic_restore.uv_lock_sha256


def test_happy_restore_rematerializes_the_verified_package_before_publishing_report(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    monkeypatch.setenv("EIDP_PROXY_SHARED_SECRET", "must-never-enter-report")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy-secret.invalid")

    result = synthetic_restore.run()

    report_bytes = result.report_path.read_bytes()
    report = json.loads(report_bytes)
    assert result == RestoreDrillResult(
        backup_id=BACKUP_ID,
        restored_path=synthetic_restore.target,
        deployment_commit=synthetic_restore.deployment_commit,
        schema_head=SCHEMA_HEAD,
        sqlite_integrity="ok",
        health_ok=True,
        package_manifest_sha256=synthetic_restore.package_manifest_sha256,
        off_host_receipt_id=None,
        report_path=synthetic_restore.target / "restore-report.v1.json",
    )
    assert set(report) == {
        "schema",
        "backup_id",
        "restored_path",
        "deployment_commit",
        "schema_head",
        "sqlite_integrity",
        "health_ok",
        "package_manifest_sha256",
        "off_host_receipt_id",
        "verified_at_utc",
        "acceptance_evidence",
    }
    assert report["schema"] == "eidp.restore-report.v1"
    assert report["restored_path"] == f"restore-drills/verified/{BACKUP_ID}"
    assert report["acceptance_evidence"] is None
    assert b"must-never-enter-report" not in report_bytes
    assert b"proxy-secret" not in report_bytes
    assert _tree_bytes(synthetic_restore.target, exclude_report=True) == _tree_bytes(synthetic_restore.package)
    source_master_mode = stat.S_IMODE(os.stat(synthetic_restore.package / "data/master.xlsx").st_mode)
    restored_master_mode = stat.S_IMODE(os.stat(synthetic_restore.target / "data/master.xlsx").st_mode)
    assert source_master_mode == 0o400
    assert restored_master_mode == 0o400
    assert source_master_mode & stat.S_IWUSR == 0
    assert restored_master_mode & stat.S_IWUSR == 0
    assert len(smoke_calls) == 1
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


def test_identical_retry_returns_byte_identical_report_without_second_smoke(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    first = synthetic_restore.run()
    report_before = first.report_path.read_bytes()
    report_mtime_before = first.report_path.stat().st_mtime_ns
    tree_before = _tree_bytes(synthetic_restore.target)

    second = synthetic_restore.run(smoke_port=_unused_loopback_port())

    assert second == first
    assert second.report_path.read_bytes() == report_before
    assert second.report_path.stat().st_mtime_ns == report_mtime_before
    assert _tree_bytes(synthetic_restore.target) == tree_before
    assert len(smoke_calls) == 1
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


@pytest.mark.parametrize(
    "invalid_verified_at",
    (
        "not-a-dateZ",
        "2026-07-13T00:00:00\x00Z",
        "2026-07-13T09:00:00+09:00",
        "2026-07-13T00:00:00+00:00",
    ),
    ids=("not-a-date", "control-character", "non-utc-offset", "utc-offset-not-z"),
)
def test_existing_retry_rejects_invalid_verified_at_without_mutation_or_second_smoke(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    invalid_verified_at: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    first = synthetic_restore.run()
    report_path = first.report_path
    report_path.chmod(0o600)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["verified_at_utc"] = invalid_verified_at
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    target_before_retry = _tree_bytes(synthetic_restore.target)
    report_before_retry = report_path.read_bytes()
    report_mtime_before_retry = report_path.stat().st_mtime_ns
    caught: Exception | None = None
    try:
        synthetic_restore.run(smoke_port=_unused_loopback_port())
    except Exception as exc:  # retain retry mutation evidence for one diagnostic assertion
        caught = exc

    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "invalid_verified_at": repr(invalid_verified_at),
        "smoke_calls": len(smoke_calls),
        "target_unchanged": _tree_bytes(synthetic_restore.target) == target_before_retry,
        "report_unchanged": report_path.read_bytes() == report_before_retry,
        "report_mtime_unchanged": report_path.stat().st_mtime_ns == report_mtime_before_retry,
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and len(smoke_calls) == 1
        and observed["target_unchanged"] is True
        and observed["report_unchanged"] is True
        and observed["report_mtime_unchanged"] is True
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_concurrent_empty_target_created_immediately_before_publish_is_preserved_fail_closed(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_smoke_stub(monkeypatch)
    original_fsync_tree_fd = restore_drill_module._fsync_tree_fd
    concurrent_identity: tuple[int, int] | None = None

    def create_target_after_staging_fsync(staged_fd: int) -> None:
        nonlocal concurrent_identity
        original_fsync_tree_fd(staged_fd)
        if concurrent_identity is None:
            synthetic_restore.target.mkdir(mode=0o700)
            target_stat = os.lstat(synthetic_restore.target)
            concurrent_identity = (target_stat.st_dev, target_stat.st_ino)
            assert list(synthetic_restore.target.iterdir()) == []

    monkeypatch.setattr(restore_drill_module, "_fsync_tree_fd", create_target_after_staging_fsync)
    caught: Exception | None = None
    try:
        synthetic_restore.run()
    except Exception as exc:  # preserve cleanup evidence for the aggregate assertion below
        caught = exc

    target_identity: tuple[int, int] | None = None
    target_entries: tuple[str, ...] | None = None
    if os.path.lexists(synthetic_restore.target):
        target_stat = os.lstat(synthetic_restore.target)
        target_identity = (target_stat.st_dev, target_stat.st_ino)
        target_entries = tuple(sorted(path.name for path in synthetic_restore.target.iterdir()))
    owned_work_residue = tuple(
        sorted(path.name for path in synthetic_restore.target.parent.iterdir() if path.name.startswith(".restore-"))
    )
    live_unchanged = _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "concurrent_identity": concurrent_identity,
        "target_identity": target_identity,
        "target_entries": target_entries,
        "owned_work_residue": owned_work_residue,
        "live_unchanged": live_unchanged,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and concurrent_identity is not None
        and target_identity == concurrent_identity
        and target_entries == ()
        and owned_work_residue == ()
        and live_unchanged
    ), observed


def test_existing_target_replacement_after_pinned_validation_is_preserved_and_retry_fails_closed(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_fsync_tree_fd = restore_drill_module._fsync_tree_fd
    displaced_target = synthetic_restore.target.with_name(f"{BACKUP_ID}.displaced-existing-race")
    replacement_file = synthetic_restore.target / "concurrent-owner.txt"
    replacement_bytes = b"concurrent existing-target owner\n"
    race_armed = False
    swapped = False
    replacement_identity: tuple[int, int] | None = None
    replacement_mtime: int | None = None

    def replace_existing_target_after_validation(directory_fd: int) -> None:
        nonlocal replacement_identity, replacement_mtime, swapped
        original_fsync_tree_fd(directory_fd)
        if not race_armed or swapped:
            return
        descriptor_stat = os.fstat(directory_fd)
        current_target = os.lstat(synthetic_restore.target)
        if (descriptor_stat.st_dev, descriptor_stat.st_ino) != (
            current_target.st_dev,
            current_target.st_ino,
        ):
            return
        os.rename(synthetic_restore.target, displaced_target)
        synthetic_restore.target.mkdir(mode=0o700)
        replacement_file.write_bytes(replacement_bytes)
        replacement_stat = os.lstat(synthetic_restore.target)
        replacement_identity = (replacement_stat.st_dev, replacement_stat.st_ino)
        replacement_mtime = replacement_file.stat().st_mtime_ns
        swapped = True

    monkeypatch.setattr(
        restore_drill_module,
        "_fsync_tree_fd",
        replace_existing_target_after_validation,
    )
    synthetic_restore.run()
    original_target = _tree_bytes(synthetic_restore.target)
    race_armed = True
    caught: Exception | None = None
    retry_result: RestoreDrillResult | None = None
    try:
        retry_result = synthetic_restore.run(smoke_port=_unused_loopback_port())
    except Exception as exc:  # retain replacement ownership evidence for one diagnostic assertion
        caught = exc

    replacement_exists = os.path.lexists(synthetic_restore.target)
    current_replacement_identity: tuple[int, int] | None = None
    replacement_unchanged = False
    if replacement_exists:
        replacement_stat = os.lstat(synthetic_restore.target)
        current_replacement_identity = (replacement_stat.st_dev, replacement_stat.st_ino)
        replacement_unchanged = (
            tuple(sorted(path.name for path in synthetic_restore.target.iterdir()))
            == (replacement_file.name,)
            and replacement_file.read_bytes() == replacement_bytes
            and replacement_mtime is not None
            and replacement_file.stat().st_mtime_ns == replacement_mtime
        )
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "returned_result": retry_result is not None,
        "swapped": swapped,
        "replacement_identity": replacement_identity,
        "current_replacement_identity": current_replacement_identity,
        "replacement_unchanged": replacement_unchanged,
        "displaced_unchanged": (
            displaced_target.is_dir() and _tree_bytes(displaced_target) == original_target
        ),
        "smoke_calls": len(smoke_calls),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and retry_result is None
        and swapped
        and replacement_identity is not None
        and current_replacement_identity == replacement_identity
        and replacement_unchanged
        and observed["displaced_unchanged"] is True
        and len(smoke_calls) == 1
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_published_target_replacement_before_return_is_preserved_and_restore_fails_closed(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_publish = restore_drill_module._publish_restore_noreplace
    displaced_target = synthetic_restore.target.with_name(f"{BACKUP_ID}.displaced-published-race")
    replacement_file = synthetic_restore.target / "concurrent-owner.txt"
    replacement_bytes = b"concurrent post-publish owner\n"
    swapped = False
    published_identity: tuple[int, int] | None = None
    replacement_identity: tuple[int, int] | None = None
    replacement_mtime: int | None = None

    def replace_target_after_publish(
        source: Path,
        target: Path,
        *,
        source_dir_fd: int,
        target_dir_fd: int,
    ) -> None:
        nonlocal published_identity, replacement_identity, replacement_mtime, swapped
        original_publish(
            source,
            target,
            source_dir_fd=source_dir_fd,
            target_dir_fd=target_dir_fd,
        )
        published_stat = os.lstat(target)
        published_identity = (published_stat.st_dev, published_stat.st_ino)
        os.rename(target, displaced_target)
        target.mkdir(mode=0o700)
        replacement_file.write_bytes(replacement_bytes)
        replacement_stat = os.lstat(target)
        replacement_identity = (replacement_stat.st_dev, replacement_stat.st_ino)
        replacement_mtime = replacement_file.stat().st_mtime_ns
        swapped = True

    monkeypatch.setattr(
        restore_drill_module,
        "_publish_restore_noreplace",
        replace_target_after_publish,
    )
    caught: Exception | None = None
    result: RestoreDrillResult | None = None
    try:
        result = synthetic_restore.run()
    except Exception as exc:  # retain replacement and owned-tree evidence for one assertion
        caught = exc

    replacement_exists = os.path.lexists(synthetic_restore.target)
    current_replacement_identity: tuple[int, int] | None = None
    replacement_unchanged = False
    if replacement_exists:
        replacement_stat = os.lstat(synthetic_restore.target)
        current_replacement_identity = (replacement_stat.st_dev, replacement_stat.st_ino)
        replacement_unchanged = (
            tuple(sorted(path.name for path in synthetic_restore.target.iterdir()))
            == (replacement_file.name,)
            and replacement_file.read_bytes() == replacement_bytes
            and replacement_mtime is not None
            and replacement_file.stat().st_mtime_ns == replacement_mtime
        )
    displaced_is_owned_or_cleaned = not os.path.lexists(displaced_target)
    if os.path.lexists(displaced_target) and published_identity is not None:
        displaced_stat = os.lstat(displaced_target)
        displaced_is_owned_or_cleaned = (
            displaced_stat.st_dev,
            displaced_stat.st_ino,
        ) == published_identity
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "returned_result": result is not None,
        "swapped": swapped,
        "published_identity": published_identity,
        "replacement_identity": replacement_identity,
        "current_replacement_identity": current_replacement_identity,
        "replacement_unchanged": replacement_unchanged,
        "displaced_is_owned_or_cleaned": displaced_is_owned_or_cleaned,
        "smoke_calls": len(smoke_calls),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and result is None
        and swapped
        and published_identity is not None
        and replacement_identity is not None
        and current_replacement_identity == replacement_identity
        and replacement_unchanged
        and displaced_is_owned_or_cleaned
        and len(smoke_calls) == 1
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


@pytest.mark.parametrize(
    ("invalid_export_id", "invalid_action_ids"),
    (
        ("/absolute-export", ACTION_IDS),
        ("../traversal-export", ACTION_IDS),
        (EXPORT_ID, ()),
        (EXPORT_ID, tuple(reversed(ACTION_IDS))),
        (EXPORT_ID, (ACTION_IDS[0], ACTION_IDS[0])),
    ),
)
def test_manual_expectation_is_validated_before_verify_copy_or_smoke(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    invalid_export_id: str,
    invalid_action_ids: tuple[str, ...],
) -> None:
    assert acceptance_restore.expectation is not None
    expectation = replace(
        acceptance_restore.expectation,
        export_id=invalid_export_id,
        action_ids=invalid_action_ids,
    )
    operations = {"verify": 0, "copy": 0}
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_verify_fd = restore_drill_module._verify_backup_package_fd
    original_copy = restore_drill_module._copy_package_tree

    def record_verify(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        operations["verify"] += 1
        return original_verify_fd(
            directory_fd,
            expected_backup_id=expected_backup_id,
            expected_manifest_sha256=expected_manifest_sha256,
            ignored_file=ignored_file,
        )

    def record_copy(source: Path, destination: Path, **kwargs: Any) -> None:
        operations["copy"] += 1
        original_copy(source, destination, **kwargs)

    monkeypatch.setattr(restore_drill_module, "_verify_backup_package_fd", record_verify)
    monkeypatch.setattr(restore_drill_module, "_copy_package_tree", record_copy)
    caught: Exception | None = None
    try:
        acceptance_restore.run(expected_evidence=expectation)
    except Exception as exc:  # preserve operation evidence for the aggregate assertion below
        caught = exc

    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "operations": operations,
        "smoke_calls": len(smoke_calls),
        "target_exists": os.path.lexists(acceptance_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in acceptance_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and operations == {"verify": 0, "copy": 0}
        and smoke_calls == []
        and observed["target_exists"] is False
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


@pytest.mark.parametrize("existing_state", ("partial", "missing_report", "conflict", "extra"))
def test_partial_or_conflicting_existing_target_is_read_only_and_never_repaired(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    existing_state: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)

    def target_file_facts() -> dict[str, tuple[bytes, int]]:
        return {
            path.relative_to(synthetic_restore.target).as_posix(): (
                path.read_bytes(),
                stat.S_IMODE(path.stat().st_mode),
            )
            for path in sorted(synthetic_restore.target.rglob("*"))
            if path.is_file()
        }

    if existing_state == "partial":
        synthetic_restore.target.mkdir()
        shutil.copy2(synthetic_restore.package / "FINALIZED", synthetic_restore.target / "FINALIZED")
    else:
        synthetic_restore.run()
        if existing_state == "missing_report":
            (synthetic_restore.target / "restore-report.v1.json").unlink()
        elif existing_state == "conflict":
            conflict_artifact = synthetic_restore.target / "data/master.xlsx"
            conflict_artifact.chmod(0o600)
            conflict_artifact.write_bytes(b"conflicting restored bytes")
        else:
            (synthetic_restore.target / "unexpected.txt").write_text("extra\n", encoding="utf-8")
    target_before = target_file_facts()
    target_mtime_before = synthetic_restore.target.stat().st_mtime_ns
    smoke_count_before = len(smoke_calls)

    with pytest.raises(RestoreDrillError, match="existing|target|report|missing|extra|conflict|package"):
        synthetic_restore.run()

    assert target_file_facts() == target_before
    assert synthetic_restore.target.stat().st_mtime_ns == target_mtime_before
    assert len(smoke_calls) == smoke_count_before
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


@pytest.mark.parametrize("package_failure", ("not_finalized", "tampered", "wrong_digest"))
def test_invalid_package_fails_before_any_restore_write_or_smoke(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    package_failure: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    expected_digest = synthetic_restore.package_manifest_sha256
    if package_failure == "not_finalized":
        (synthetic_restore.package / "FINALIZED").unlink()
    elif package_failure == "tampered":
        (synthetic_restore.package / "data/audit/manual-actions.jsonl").write_text(
            "tampered\n", encoding="utf-8"
        )
    else:
        expected_digest = "0" * 64

    with pytest.raises((RestoreDrillError, BackupPackageError), match="finalized|digest|manifest|artifact|package"):
        synthetic_restore.run(expected_package_manifest_sha256=expected_digest)

    assert not synthetic_restore.target.exists()
    assert list(synthetic_restore.target.parent.iterdir()) == []
    assert smoke_calls == []
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


def test_source_optional_root_presence_mismatch_fails_before_restore_write_or_smoke(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    manifest_path = synthetic_restore.package / "backup-manifest.v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    optional_roots = manifest.get("optional_roots")
    assert isinstance(optional_roots, dict)
    assert optional_roots.get("data/audit") is True
    assert (synthetic_restore.package / "data/audit/manual-actions.jsonl").is_file()
    optional_roots["data/audit"] = False
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    resealed_digest = _reseal_package(synthetic_restore.package)
    caught: Exception | None = None
    try:
        synthetic_restore.run(expected_package_manifest_sha256=resealed_digest)
    except Exception as exc:  # retain write/smoke evidence for one diagnostic assertion
        caught = exc

    error_text = str(caught).lower() if caught is not None else ""
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "error_text": error_text,
        "smoke_calls": len(smoke_calls),
        "target_exists": os.path.lexists(synthetic_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and any(term in error_text for term in ("optional", "root", "package"))
        and smoke_calls == []
        and observed["target_exists"] is False
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


@pytest.mark.parametrize(
    "mutation",
    (
        "valid",
        "artifact_tamper",
        "marker",
        "manifest_field",
        "optional_root_contradiction",
        "schema_mismatch",
        "created_at_minute_precision",
        "deployment_port_zero",
    ),
)
def test_task4_path_and_task5_fd_verifiers_have_static_mutation_parity(
    synthetic_restore: SyntheticRestore,
    mutation: str,
) -> None:
    package = synthetic_restore.package
    manifest_path = package / "backup-manifest.v1.json"
    marker_path = package / "FINALIZED"

    def rewrite_manifest_and_marker(payload: dict[str, object]) -> None:
        manifest_path.chmod(0o600)
        marker_path.chmod(0o600)
        manifest_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        marker_path.write_text(_sha256(manifest_path) + "\n", encoding="ascii")

    if mutation == "artifact_tamper":
        artifact = package / "data/master.xlsx"
        artifact.chmod(0o600)
        artifact.write_bytes(b"static parity artifact tamper\n")
    elif mutation == "marker":
        marker_path.chmod(0o600)
        marker_path.write_text("0" * 64 + "\n", encoding="ascii")
    elif mutation in {"manifest_field", "optional_root_contradiction", "created_at_minute_precision"}:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if mutation == "manifest_field":
            manifest["actor"] = ""
        elif mutation == "optional_root_contradiction":
            optional_roots = manifest.get("optional_roots")
            assert isinstance(optional_roots, dict)
            assert optional_roots.get("data/audit") is True
            optional_roots["data/audit"] = False
        else:
            manifest["created_at_utc"] = "2026-07-13T00:00Z"
        rewrite_manifest_and_marker(manifest)
    elif mutation == "schema_mismatch":
        database = package / "data/eidp.sqlite3"
        database.chmod(0o600)
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE alembic_version SET version_num = ?", ("0" * 12,))
        _reseal_package(package)
    elif mutation == "deployment_port_zero":
        deployment_path = package / "run/deployment-manifest.json"
        deployment_path.chmod(0o600)
        deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
        deployment["port"] = 0
        deployment_path.write_text(json.dumps(deployment, sort_keys=True) + "\n", encoding="utf-8")
        manifest_path.chmod(0o600)
        marker_path.chmod(0o600)
        _reseal_package(package)

    path_error: Exception | None = None
    try:
        verify_backup_package(package)
    except (BackupPackageError, RestoreDrillError) as exc:
        path_error = exc

    fd_error: Exception | None = None
    package_fd = os.open(
        package,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        try:
            restore_drill_module._verify_backup_package_fd(
                package_fd,
                expected_backup_id=BACKUP_ID,
            )
        except (BackupPackageError, RestoreDrillError) as exc:
            fd_error = exc
    finally:
        os.close(package_fd)

    expected_accept = mutation in {"valid", "created_at_minute_precision", "deployment_port_zero"}
    observed = {
        "mutation": mutation,
        "path_accepted": path_error is None,
        "fd_accepted": fd_error is None,
        "path_error_type": type(path_error).__name__ if path_error is not None else None,
        "fd_error_type": type(fd_error).__name__ if fd_error is not None else None,
    }
    assert (
        (path_error is None) == expected_accept
        and (fd_error is None) == expected_accept
        and (path_error is None) == (fd_error is None)
    ), observed


def test_existing_target_retry_rejects_matching_source_and_target_artifact_tamper(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_verify_fd = restore_drill_module._verify_backup_package_fd
    mutation_armed = False
    mutated = False
    target_after_mutation: dict[str, bytes] | None = None
    target_artifact_mtime: int | None = None
    source_artifact = synthetic_restore.package / "data/master.xlsx"
    target_artifact = synthetic_restore.target / "data/master.xlsx"
    tampered = b"matching source and existing-target tamper\n"

    def mutate_after_retry_source_verification(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        nonlocal mutated, target_after_mutation, target_artifact_mtime
        result = original_verify_fd(
            directory_fd,
            expected_backup_id=expected_backup_id,
            expected_manifest_sha256=expected_manifest_sha256,
            ignored_file=ignored_file,
        )
        if mutation_armed and expected_manifest_sha256 is None and not mutated:
            source_artifact.chmod(0o600)
            target_artifact.chmod(0o600)
            source_artifact.write_bytes(tampered)
            target_artifact.write_bytes(tampered)
            target_after_mutation = _tree_bytes(synthetic_restore.target)
            target_artifact_mtime = target_artifact.stat().st_mtime_ns
            mutated = True
        return result

    monkeypatch.setattr(
        restore_drill_module,
        "_verify_backup_package_fd",
        mutate_after_retry_source_verification,
    )
    first = synthetic_restore.run()
    report_before = first.report_path.read_bytes()
    report_mtime_before = first.report_path.stat().st_mtime_ns
    mutation_armed = True
    caught: Exception | None = None
    try:
        synthetic_restore.run(smoke_port=_unused_loopback_port())
    except Exception as exc:  # retain idempotent retry evidence for one diagnostic assertion
        caught = exc

    error_text = str(caught).lower() if caught is not None else ""
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "error_text": error_text,
        "smoke_calls": len(smoke_calls),
        "mutated": mutated,
        "source_unchanged": source_artifact.read_bytes() == tampered,
        "target_unchanged": _tree_bytes(synthetic_restore.target) == target_after_mutation,
        "target_artifact_mtime_unchanged": (
            target_artifact_mtime is not None
            and target_artifact.stat().st_mtime_ns == target_artifact_mtime
        ),
        "report_unchanged": first.report_path.read_bytes() == report_before,
        "report_mtime_unchanged": first.report_path.stat().st_mtime_ns == report_mtime_before,
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and any(term in error_text for term in ("digest", "artifact", "package"))
        and len(smoke_calls) == 1
        and mutated
        and observed["source_unchanged"] is True
        and observed["target_unchanged"] is True
        and observed["target_artifact_mtime_unchanged"] is True
        and observed["report_unchanged"] is True
        and observed["report_mtime_unchanged"] is True
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_source_mutation_after_source_verification_is_caught_before_publish(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_copy = restore_drill_module._copy_package_tree
    copy_calls = 0

    def mutate_before_copy(source: Path, destination: Path, **kwargs: Any) -> None:
        nonlocal copy_calls
        copy_calls += 1
        (synthetic_restore.package / "data/audit/manual-actions.jsonl").write_text(
            "mutated after source verification\n", encoding="utf-8"
        )
        original_copy(source, destination, **kwargs)

    monkeypatch.setattr(restore_drill_module, "_copy_package_tree", mutate_before_copy)

    with pytest.raises((RestoreDrillError, BackupPackageError), match="digest|changed|artifact|package"):
        synthetic_restore.run()

    assert copy_calls == 1
    assert not synthetic_restore.target.exists()
    assert list(synthetic_restore.target.parent.iterdir()) == []
    assert smoke_calls == []
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


def test_pinned_source_parent_swap_never_reads_or_writes_outside_package(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    package_parent = synthetic_restore.package.parent
    displaced_parent = package_parent.with_name(f"{package_parent.name}-displaced")
    replacement = package_parent.with_name(f"{package_parent.name}-outside-replacement")
    parent_stat = os.lstat(package_parent)
    parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
    outside = tmp_path / "outside-source-authority"
    outside_package = outside / BACKUP_ID
    shutil.copytree(synthetic_restore.package, outside_package)
    outside_canary = outside_package / "data/audit/manual-actions.jsonl"
    outside_canary.write_bytes(b'{"source":"outside-authority-canary"}\n')
    _reseal_package(outside_package)
    verify_backup_package(outside_package)
    outside_identities = {
        (candidate.stat().st_dev, candidate.stat().st_ino): candidate.relative_to(outside).as_posix()
        for candidate in outside.rglob("*")
        if candidate.is_file()
    }

    def outside_snapshot() -> tuple[tuple[str, ...], dict[str, tuple[bytes, int]]]:
        return (
            tuple(sorted(candidate.relative_to(outside).as_posix() for candidate in outside.rglob("*"))),
            {
                candidate.relative_to(outside).as_posix(): (candidate.read_bytes(), candidate.stat().st_mtime_ns)
                for candidate in outside.rglob("*")
                if candidate.is_file()
            },
        )

    outside_before = outside_snapshot()
    original_verify_fd = restore_drill_module._verify_backup_package_fd
    original_open = restore_drill_module.os.open
    original_read = restore_drill_module.os.read
    outside_accesses: list[tuple[str, str]] = []
    access_active = False
    swapped = False
    parent_restored = False

    def record_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if access_active:
            descriptor_stat = os.fstat(descriptor)
            relative = outside_identities.get((descriptor_stat.st_dev, descriptor_stat.st_ino))
            if relative is not None:
                outside_accesses.append(("open", relative))
        return descriptor

    def record_read(descriptor: int, length: int) -> bytes:
        if access_active:
            descriptor_stat = os.fstat(descriptor)
            relative = outside_identities.get((descriptor_stat.st_dev, descriptor_stat.st_ino))
            if relative is not None:
                outside_accesses.append(("read", relative))
        return original_read(descriptor, length)

    def swap_parent_during_source_verification(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        nonlocal access_active, parent_restored, swapped
        if expected_manifest_sha256 is not None or swapped:
            return original_verify_fd(
                directory_fd,
                expected_backup_id=expected_backup_id,
                expected_manifest_sha256=expected_manifest_sha256,
                ignored_file=ignored_file,
            )
        replacement.symlink_to(outside, target_is_directory=True)
        os.rename(package_parent, displaced_parent)
        os.rename(replacement, package_parent)
        swapped = True
        access_active = True
        try:
            return original_verify_fd(
                directory_fd,
                expected_backup_id=expected_backup_id,
                expected_manifest_sha256=expected_manifest_sha256,
                ignored_file=ignored_file,
            )
        finally:
            access_active = False
            package_parent.unlink()
            os.rename(displaced_parent, package_parent)
            parent_restored = True

    monkeypatch.setattr(restore_drill_module.os, "open", record_open)
    monkeypatch.setattr(restore_drill_module.os, "read", record_read)
    monkeypatch.setattr(
        restore_drill_module,
        "_verify_backup_package_fd",
        swap_parent_during_source_verification,
    )
    caught: Exception | None = None
    try:
        synthetic_restore.run(expected_package_manifest_sha256="0" * 64)
    except Exception as exc:  # retain all authority-boundary evidence for one diagnostic assertion
        caught = exc

    current_parent_stat = os.lstat(package_parent)
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "swapped": swapped,
        "parent_restored": parent_restored,
        "parent_identity": (current_parent_stat.st_dev, current_parent_stat.st_ino),
        "outside_accesses": tuple(outside_accesses),
        "outside_unchanged": outside_snapshot() == outside_before,
        "target_exists": os.path.lexists(synthetic_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "smoke_calls": tuple(smoke_calls),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, (BackupPackageError, RestoreDrillError))
        and swapped
        and parent_restored
        and observed["parent_identity"] == parent_identity
        and outside_accesses == []
        and observed["outside_unchanged"] is True
        and observed["target_exists"] is False
        and observed["owned_work_residue"] == ()
        and smoke_calls == []
        and observed["live_unchanged"] is True
    ), observed


def test_copy_directory_swap_to_outside_symlink_never_reads_or_writes_outside(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_smoke_stub(monkeypatch)
    outside = tmp_path / "outside-copy-source"
    outside.mkdir()
    outside_file = outside / "manual-actions.jsonl"
    outside_file.write_bytes(b"outside canary must never be read or changed")
    outside_before = (outside_file.read_bytes(), outside_file.stat().st_mtime_ns)
    source_directory = synthetic_restore.package / "data/audit"
    source_data_stat = os.stat(source_directory.parent)
    source_data_identity = (source_data_stat.st_dev, source_data_stat.st_ino)
    outside_stat = os.stat(outside)
    outside_identity = (outside_stat.st_dev, outside_stat.st_ino)
    original_verify_fd = restore_drill_module._verify_backup_package_fd
    original_stat = restore_drill_module.os.stat
    original_open = restore_drill_module.os.open
    copy_phase = False
    swapped = False
    outside_accesses: list[tuple[str, int]] = []

    def arm_copy_race(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        nonlocal copy_phase
        result = original_verify_fd(
            directory_fd,
            expected_backup_id=expected_backup_id,
            expected_manifest_sha256=expected_manifest_sha256,
            ignored_file=ignored_file,
        )
        if expected_manifest_sha256 is None and not copy_phase:
            copy_phase = True
        return result

    def swap_after_data_entry_stat(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        nonlocal swapped
        result = original_stat(path, *args, **kwargs)
        directory_fd = kwargs.get("dir_fd")
        directory_identity: tuple[int, int] | None = None
        if isinstance(directory_fd, int):
            directory_stat = os.fstat(directory_fd)
            directory_identity = (directory_stat.st_dev, directory_stat.st_ino)
        if (
            copy_phase
            and not swapped
            and path == source_directory.name
            and directory_identity == source_data_identity
            and kwargs.get("follow_symlinks") is False
        ):
            swapped = True
            shutil.rmtree(source_directory)
            source_directory.symlink_to(outside, target_is_directory=True)
        return result

    def record_outside_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        accessed_outside = False
        directory_fd = kwargs.get("dir_fd")
        if isinstance(directory_fd, int):
            directory_stat = os.fstat(directory_fd)
            accessed_outside = (directory_stat.st_dev, directory_stat.st_ino) == outside_identity
        if isinstance(path, (str, os.PathLike)):
            candidate = Path(path)
            if candidate.is_absolute() and candidate.resolve(strict=False).is_relative_to(outside):
                accessed_outside = True
        descriptor_stat = os.fstat(descriptor)
        if (descriptor_stat.st_dev, descriptor_stat.st_ino) == outside_identity:
            accessed_outside = True
        if accessed_outside:
            outside_accesses.append((str(path), flags))
        return descriptor

    monkeypatch.setattr(restore_drill_module, "_verify_backup_package_fd", arm_copy_race)
    monkeypatch.setattr(restore_drill_module.os, "stat", swap_after_data_entry_stat)
    monkeypatch.setattr(restore_drill_module.os, "open", record_outside_open)
    caught: Exception | None = None
    try:
        synthetic_restore.run()
    except Exception as exc:  # preserve outside-access evidence for the aggregate assertion below
        caught = exc

    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "swapped": swapped,
        "outside_accesses": outside_accesses,
        "outside_unchanged": (outside_file.read_bytes(), outside_file.stat().st_mtime_ns) == outside_before,
        "target_exists": os.path.lexists(synthetic_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in synthetic_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and swapped
        and outside_accesses == []
        and observed["outside_unchanged"] is True
        and observed["target_exists"] is False
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_verified_target_parent_swap_to_outside_symlink_never_writes_outside(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_smoke_stub(monkeypatch)
    outside = tmp_path / "outside-target-parent"
    outside.mkdir()
    outside_stat = os.lstat(outside)
    outside_identity = (outside_stat.st_dev, outside_stat.st_ino)
    outside_mtime = outside_stat.st_mtime_ns
    verified_parent = synthetic_restore.target.parent
    original_verify_fd = restore_drill_module._verify_backup_package_fd
    swapped = False

    def swap_parent_after_precheck(
        directory_fd: int,
        *,
        expected_backup_id: str,
        expected_manifest_sha256: str | None = None,
        ignored_file: str | None = None,
    ) -> Any:
        nonlocal swapped
        result = original_verify_fd(
            directory_fd,
            expected_backup_id=expected_backup_id,
            expected_manifest_sha256=expected_manifest_sha256,
            ignored_file=ignored_file,
        )
        if expected_manifest_sha256 is None and not swapped:
            verified_parent.rmdir()
            verified_parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        return result

    monkeypatch.setattr(restore_drill_module, "_verify_backup_package_fd", swap_parent_after_precheck)
    caught: Exception | None = None
    try:
        synthetic_restore.run()
    except Exception as exc:  # preserve outside-write evidence for the aggregate assertion below
        caught = exc

    current_outside_stat = os.lstat(outside)
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "swapped": swapped,
        "verified_parent_is_symlink": verified_parent.is_symlink(),
        "outside_identity": (current_outside_stat.st_dev, current_outside_stat.st_ino),
        "outside_mtime_unchanged": current_outside_stat.st_mtime_ns == outside_mtime,
        "outside_entries": tuple(sorted(path.name for path in outside.iterdir())),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and swapped
        and verified_parent.is_symlink()
        and observed["outside_identity"] == outside_identity
        and observed["outside_mtime_unchanged"] is True
        and observed["outside_entries"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_copied_deployment_evidence_parent_swap_never_reads_or_writes_outside(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_smoke_stub(monkeypatch)
    outside = tmp_path / "outside-copied-deployment-evidence"
    outside.mkdir()
    verified_parent = synthetic_restore.target.parent
    displaced_parent = verified_parent.with_name("verified-displaced-after-copy")
    replacement = verified_parent.with_name("verified-outside-replacement")
    original_deployment_evidence_fd = restore_drill_module._deployment_evidence_fd
    original_open = restore_drill_module.os.open
    original_read = restore_drill_module.os.read
    swapped = False
    stage_deployment_calls: list[int] = []
    outside_accesses: list[tuple[str, str]] = []
    outside_canary_identity: tuple[int, int] | None = None
    outside_before: dict[str, tuple[bytes, int]] | None = None
    stage_helper_active = False

    def record_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if stage_helper_active and outside_canary_identity is not None:
            descriptor_stat = os.fstat(descriptor)
            if (descriptor_stat.st_dev, descriptor_stat.st_ino) == outside_canary_identity:
                outside_accesses.append(("open", str(path)))
        return descriptor

    def record_read(descriptor: int, length: int) -> bytes:
        if stage_helper_active and outside_canary_identity is not None:
            descriptor_stat = os.fstat(descriptor)
            if (descriptor_stat.st_dev, descriptor_stat.st_ino) == outside_canary_identity:
                outside_accesses.append(("read", str(descriptor)))
        return original_read(descriptor, length)

    def swap_parent_before_copied_deployment_evidence(directory_fd: int) -> Any:
        nonlocal outside_before, outside_canary_identity, stage_helper_active, swapped
        work_candidates = tuple(
            path
            for path in verified_parent.iterdir()
            if path.name.startswith(".restore-") and path.name.endswith(".work")
        )
        staged = work_candidates[0] / BACKUP_ID if len(work_candidates) == 1 else None
        staged_stat = os.stat(staged) if staged is not None and staged.exists() else None
        directory_stat = os.fstat(directory_fd)
        is_first_copied_stage_deployment = not swapped and staged_stat is not None and (
            directory_stat.st_dev,
            directory_stat.st_ino,
        ) == (staged_stat.st_dev, staged_stat.st_ino)
        if not is_first_copied_stage_deployment:
            return original_deployment_evidence_fd(directory_fd)

        assert staged is not None
        stage_deployment_calls.append(directory_fd)
        outside_manifest = outside / staged.parent.name / staged.name / "run/deployment-manifest.json"
        outside_manifest.parent.mkdir(parents=True)
        canary_payload = json.loads(
            (synthetic_restore.package / "run/deployment-manifest.json").read_text(encoding="utf-8")
        )
        canary_payload["port"] = 31337
        outside_manifest.write_text(json.dumps(canary_payload, sort_keys=True), encoding="utf-8")
        outside_manifest_stat = os.stat(outside_manifest)
        outside_canary_identity = (outside_manifest_stat.st_dev, outside_manifest_stat.st_ino)
        outside_before = {
            candidate.relative_to(outside).as_posix(): (candidate.read_bytes(), candidate.stat().st_mtime_ns)
            for candidate in outside.rglob("*")
            if candidate.is_file()
        }
        replacement.symlink_to(outside, target_is_directory=True)
        os.rename(verified_parent, displaced_parent)
        os.rename(replacement, verified_parent)
        swapped = True
        stage_helper_active = True
        try:
            return original_deployment_evidence_fd(directory_fd)
        finally:
            stage_helper_active = False

    monkeypatch.setattr(restore_drill_module.os, "open", record_open)
    monkeypatch.setattr(restore_drill_module.os, "read", record_read)
    monkeypatch.setattr(
        restore_drill_module,
        "_deployment_evidence_fd",
        swap_parent_before_copied_deployment_evidence,
    )
    caught: Exception | None = None
    try:
        synthetic_restore.run()
    except Exception as exc:  # retain all race evidence for one diagnostic assertion
        caught = exc

    displaced_entries = tuple(sorted(path.name for path in displaced_parent.iterdir()))
    outside_after = {
        candidate.relative_to(outside).as_posix(): (candidate.read_bytes(), candidate.stat().st_mtime_ns)
        for candidate in outside.rglob("*")
        if candidate.is_file()
    }
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "swapped": swapped,
        "stage_deployment_calls": tuple(stage_deployment_calls),
        "outside_accesses": tuple(outside_accesses),
        "outside_unchanged": outside_after == outside_before,
        "displaced_entries": displaced_entries,
        "target_exists": os.path.lexists(synthetic_restore.target),
        "live_unchanged": _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts,
    }
    assert (
        isinstance(caught, (BackupPackageError, RestoreDrillError))
        and swapped
        and len(stage_deployment_calls) == 1
        and outside_accesses == []
        and observed["outside_unchanged"] is True
        and displaced_entries == ()
        and observed["target_exists"] is False
        and observed["live_unchanged"] is True
    ), observed


@pytest.mark.parametrize("fault", ("copy", "smoke", "report", "rename"))
def test_restore_stage_failures_leave_no_target_or_owned_work_and_preserve_live_facts(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    _install_smoke_stub(monkeypatch)

    def injected_failure(*_args: object, **_kwargs: object) -> Any:
        raise OSError(f"injected {fault} failure")

    if fault == "copy":
        monkeypatch.setattr(restore_drill_module, "_copy_package_tree", injected_failure, raising=False)
    elif fault == "smoke":
        monkeypatch.setattr(restore_drill_module, "_run_streamlit_smoke", injected_failure, raising=False)
    elif fault == "report":
        monkeypatch.setattr(restore_drill_module, "_write_restore_report", injected_failure, raising=False)
    else:
        monkeypatch.setattr(
            restore_drill_module,
            "_publish_restore_noreplace",
            injected_failure,
            raising=True,
        )

    with pytest.raises((RestoreDrillError, OSError), match=fault):
        synthetic_restore.run()

    assert not synthetic_restore.target.exists()
    assert list(synthetic_restore.target.parent.iterdir()) == []
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts
    assert (synthetic_restore.app_root / "run/eidp.pid.json").read_bytes() == b'{"pid":999999}\n'
    assert (synthetic_restore.app_root / "logs/web.log").read_bytes() == b"live log must remain unchanged\n"


@pytest.mark.parametrize("mismatch", ("commit", "dirty", "uv_lock", "schema"))
def test_restore_rejects_checkout_or_schema_mismatch_before_publish(
    synthetic_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    if mismatch == "dirty":
        (synthetic_restore.app_root / "src/eidp/web/app.py").write_text("# dirty checkout\n", encoding="utf-8")
    elif mismatch == "schema":
        with sqlite3.connect(synthetic_restore.package / "data/eidp.sqlite3") as connection:
            connection.execute("UPDATE alembic_version SET version_num = 'cccccccccccc'")
        synthetic_restore.package_manifest_sha256 = _reseal_package(synthetic_restore.package)
    else:
        deployment_path = synthetic_restore.package / "run/deployment-manifest.json"
        deployment = json.loads(deployment_path.read_text(encoding="utf-8"))
        if mismatch == "commit":
            deployment["deployed_commit"] = "f" * 40
            deployment["expected_deployment_commit"] = "f" * 40
            deployment["origin_main_commit"] = "f" * 40
            manifest_path = synthetic_restore.package / "backup-manifest.v1.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["deployment_commit"] = "f" * 40
            manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        else:
            deployment["uv_lock_sha256"] = "0" * 64
        deployment_path.write_text(json.dumps(deployment, sort_keys=True) + "\n", encoding="utf-8")
        synthetic_restore.package_manifest_sha256 = _reseal_package(synthetic_restore.package)

    with pytest.raises(
        (RestoreDrillError, BackupPackageError),
        match="commit|clean checkout|uv.lock|schema|deployment|package",
    ):
        synthetic_restore.run()

    assert not synthetic_restore.target.exists()
    assert smoke_calls == []
    assert _fact_snapshot(synthetic_restore.app_root) == synthetic_restore.live_facts


def test_expectation_loader_accepts_only_the_exact_generated_projection(
    expectation_file: tuple[Path, Path, dict[str, object]],
) -> None:
    app_root, path, _payload = expectation_file

    result = load_restore_evidence_expectation(app_root=app_root, path=path)

    assert result == RestoreEvidenceExpectation(
        export_id=EXPORT_ID,
        workbook_sha256="a" * 64,
        export_manifest_sha256="b" * 64,
        action_ids=ACTION_IDS,
    )


@pytest.mark.parametrize(
    "unsafe_path",
    (
        "outside",
        "wrong_root",
        "nested",
        "basename_mismatch",
        "symlink_file",
        "symlink_parent",
        "directory",
        "missing",
        "oversized",
    ),
)
def test_expectation_loader_rejects_unsafe_or_noncanonical_path(
    expectation_file: tuple[Path, Path, dict[str, object]],
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    app_root, path, payload = expectation_file
    candidate = path
    if unsafe_path == "outside":
        candidate = tmp_path / path.name
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif unsafe_path == "wrong_root":
        candidate = app_root / "evidence/runtime/not-exports" / path.name
        candidate.parent.mkdir(parents=True)
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif unsafe_path == "nested":
        candidate = path.parent / "nested" / path.name
        candidate.parent.mkdir()
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif unsafe_path == "basename_mismatch":
        candidate = path.with_name("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa.json")
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif unsafe_path == "symlink_file":
        outside = tmp_path / "outside-expectation.json"
        outside.write_text(json.dumps(payload), encoding="utf-8")
        path.unlink()
        path.symlink_to(outside)
    elif unsafe_path == "symlink_parent":
        outside = tmp_path / "outside-exports"
        outside.mkdir()
        (outside / path.name).write_text(json.dumps(payload), encoding="utf-8")
        shutil.rmtree(path.parent)
        path.parent.symlink_to(outside, target_is_directory=True)
    elif unsafe_path == "directory":
        path.unlink()
        path.mkdir()
    elif unsafe_path == "missing":
        path.unlink()
    else:
        path.write_text("{" + " " * (1024 * 1024), encoding="utf-8")

    with pytest.raises(RestoreDrillError, match="expectation|evidence|path|symlink|regular|size|export"):
        load_restore_evidence_expectation(app_root=app_root, path=candidate)


@pytest.mark.parametrize(
    "invalid_payload",
    (
        "not_object",
        "malformed_json",
        "missing_key",
        "extra_key",
        "schema",
        "export_uuid_version",
        "export_uuid_uppercase",
        "workbook_sha_short",
        "manifest_sha_uppercase",
        "actions_empty",
        "actions_unsorted",
        "actions_duplicate",
        "action_uuid_invalid",
    ),
)
def test_expectation_loader_rejects_invalid_schema_ids_hashes_and_action_order(
    expectation_file: tuple[Path, Path, dict[str, object]],
    invalid_payload: str,
) -> None:
    app_root, path, original = expectation_file
    payload: object = dict(original)
    if invalid_payload == "not_object":
        payload = []
    elif invalid_payload == "malformed_json":
        path.write_text("{not json\n", encoding="utf-8")
    else:
        assert isinstance(payload, dict)
        if invalid_payload == "missing_key":
            payload.pop("schema")
        elif invalid_payload == "extra_key":
            payload["unexpected"] = True
        elif invalid_payload == "schema":
            payload["schema"] = "eidp.restore-evidence-expectation.v2"
        elif invalid_payload == "export_uuid_version":
            payload["export_id"] = "01234567-89ab-1def-8abc-0123456789ab"
        elif invalid_payload == "export_uuid_uppercase":
            payload["export_id"] = EXPORT_ID.upper()
        elif invalid_payload == "workbook_sha_short":
            payload["workbook_sha256"] = "a" * 63
        elif invalid_payload == "manifest_sha_uppercase":
            payload["export_manifest_sha256"] = "B" * 64
        elif invalid_payload == "actions_empty":
            payload["action_ids"] = []
        elif invalid_payload == "actions_unsorted":
            payload["action_ids"] = list(reversed(ACTION_IDS))
        elif invalid_payload == "actions_duplicate":
            payload["action_ids"] = [ACTION_IDS[0], ACTION_IDS[0]]
        else:
            payload["action_ids"] = ["not-a-uuid"]
    if invalid_payload != "malformed_json":
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(RestoreDrillError, match="expectation|schema|UUID|SHA|action|sorted|unique|JSON"):
        load_restore_evidence_expectation(app_root=app_root, path=path)


def test_acceptance_restore_binds_export_and_exactly_once_db_and_jsonl_evidence(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    assert acceptance_restore.expectation_path is not None
    acceptance_restore.expectation = load_restore_evidence_expectation(
        app_root=acceptance_restore.app_root,
        path=acceptance_restore.expectation_path,
    )

    result = acceptance_restore.run()

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["acceptance_evidence"] == {
        "export_id": EXPORT_ID,
        "workbook_sha256": acceptance_restore.expectation.workbook_sha256,
        "export_manifest_sha256": acceptance_restore.expectation.export_manifest_sha256,
        "action_ids": list(ACTION_IDS),
        "db_action_counts": {action_id: 1 for action_id in ACTION_IDS},
        "audit_projection_counts": {action_id: 1 for action_id in ACTION_IDS},
    }
    assert len(smoke_calls) == 1
    assert _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts


@pytest.mark.parametrize(
    "export_failure",
    (
        "marker",
        "manifest_digest",
        "manifest_schema",
        "export_id",
        "lifecycle",
        "manifest_workbook_sha",
        "unsafe_workbook_name",
        "workbook_bytes",
        "extra_file",
    ),
)
def test_acceptance_rejects_tampered_or_nonfinal_export_bundle(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    export_failure: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    assert acceptance_restore.expectation is not None
    export_root = acceptance_restore.package / "output/exports" / EXPORT_ID
    manifest_path = export_root / "export-manifest.v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    update_expected_manifest_digest = False
    if export_failure == "marker":
        (export_root / "FINALIZED").write_text("0" * 64 + "\n", encoding="ascii")
    elif export_failure == "manifest_digest":
        manifest["unexpected_change"] = True
        manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    elif export_failure == "workbook_bytes":
        (export_root / "accepted.xlsx").write_bytes(b"tampered workbook")
    elif export_failure == "extra_file":
        (export_root / "unexpected.txt").write_text("extra\n", encoding="utf-8")
    else:
        update_expected_manifest_digest = True
        if export_failure == "manifest_schema":
            manifest["schema"] = "eidp.export-manifest.v2"
        elif export_failure == "export_id":
            manifest["export_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        elif export_failure == "lifecycle":
            manifest["lifecycle"] = "staged"
        elif export_failure == "manifest_workbook_sha":
            manifest["workbook_sha256"] = "0" * 64
        else:
            manifest["workbook_filename"] = "../escape.xlsx"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    if update_expected_manifest_digest:
        acceptance_restore.expectation = replace(
            acceptance_restore.expectation,
            export_manifest_sha256=_sha256(manifest_path),
        )
    acceptance_restore.package_manifest_sha256 = _reseal_package(acceptance_restore.package)

    with pytest.raises(
        (RestoreDrillError, BackupPackageError),
        match="export|manifest|marker|workbook|FINALIZED|extra|digest|lifecycle|safe",
    ):
        acceptance_restore.run()

    assert not acceptance_restore.target.exists()
    assert smoke_calls == []
    assert _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts


@pytest.mark.parametrize("db_failure", ("missing", "duplicate", "pending", "error"))
def test_acceptance_requires_exactly_one_exported_error_free_db_action(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    db_failure: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    database = acceptance_restore.package / "data/eidp.sqlite3"
    with sqlite3.connect(database) as connection:
        if db_failure == "missing":
            connection.execute("DELETE FROM manual_action_log WHERE action_id = ?", (ACTION_IDS[0],))
        elif db_failure == "duplicate":
            connection.execute(
                """
                INSERT INTO manual_action_log(action_id, jsonl_exported_at, jsonl_export_error)
                VALUES (?, ?, NULL)
                """,
                (ACTION_IDS[0], "2026-07-12T02:03:04Z"),
            )
        elif db_failure == "pending":
            connection.execute(
                "UPDATE manual_action_log SET jsonl_exported_at = NULL WHERE action_id = ?",
                (ACTION_IDS[0],),
            )
        else:
            connection.execute(
                "UPDATE manual_action_log SET jsonl_export_error = 'flush failed' WHERE action_id = ?",
                (ACTION_IDS[0],),
            )
    acceptance_restore.package_manifest_sha256 = _reseal_package(acceptance_restore.package)
    resealed_manifest = json.loads(
        (acceptance_restore.package / "backup-manifest.v1.json").read_text(encoding="utf-8")
    )
    inventory_paths = {entry["path"] for entry in resealed_manifest["inventory"]}
    assert f"output/exports/{EXPORT_ID}/FINALIZED" in inventory_paths

    with pytest.raises(RestoreDrillError, match="action|database|exactly one|exported|pending|error"):
        acceptance_restore.run()

    assert not acceptance_restore.target.exists()
    assert smoke_calls == []
    assert _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts


@pytest.mark.parametrize("jsonl_failure", ("missing", "duplicate", "malformed", "symlink_archive"))
def test_acceptance_requires_one_well_formed_real_jsonl_projection_across_active_and_archives(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    jsonl_failure: str,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    audit_root = acceptance_restore.package / "data/audit"
    active = audit_root / "manual-actions.jsonl"
    archive = audit_root / "manual-actions-20260712.jsonl"
    if jsonl_failure == "missing":
        active.write_text(json.dumps({"action_id": "unrelated"}) + "\n", encoding="utf-8")
    elif jsonl_failure == "duplicate":
        with archive.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"action_id": ACTION_IDS[0]}) + "\n")
    elif jsonl_failure == "malformed":
        with archive.open("a", encoding="utf-8") as stream:
            stream.write("{malformed json\n")
    else:
        outside = tmp_path / "outside-archive.jsonl"
        outside.write_text(archive.read_text(encoding="utf-8"), encoding="utf-8")
        archive.unlink()
        archive.symlink_to(outside)
    acceptance_restore.package_manifest_sha256 = _reseal_package(acceptance_restore.package)

    with pytest.raises(
        (RestoreDrillError, BackupPackageError),
        match="JSONL|audit|action|projection|duplicate|missing|malformed|symlink|package",
    ):
        acceptance_restore.run()

    assert not acceptance_restore.target.exists()
    assert smoke_calls == []
    assert _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts


def test_acceptance_streams_many_small_rows_across_multiple_audit_archives(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    audit_root = acceptance_restore.package / "data/audit"
    for archive_index in range(6):
        archive = audit_root / f"manual-actions-archive-{archive_index:02d}.jsonl"
        archive.write_text(
            "".join(
                json.dumps(
                    {"action_id": f"unrelated-{archive_index:02d}-{row_index:04d}"},
                    sort_keys=True,
                )
                + "\n"
                for row_index in range(1_500)
            ),
            encoding="utf-8",
        )
    acceptance_restore.package_manifest_sha256 = _reseal_package(acceptance_restore.package)

    result = acceptance_restore.run()

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["acceptance_evidence"]["audit_projection_counts"] == {
        action_id: 1 for action_id in ACTION_IDS
    }
    assert len(smoke_calls) == 1
    assert _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts


def test_acceptance_audit_projection_never_uses_unbounded_whole_file_read(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    original_read_regular_at = restore_drill_module._read_regular_at
    unbounded_audit_reads: list[str] = []

    def reject_unbounded_audit_read(
        directory_fd: int,
        relative: str,
        *,
        maximum: int | None,
        label: str,
    ) -> bytes:
        if label == "restored audit JSONL projection" and maximum is None:
            unbounded_audit_reads.append(relative)
            raise AssertionError(f"unbounded whole-file audit read: {relative}")
        return original_read_regular_at(
            directory_fd,
            relative,
            maximum=maximum,
            label=label,
        )

    monkeypatch.setattr(restore_drill_module, "_read_regular_at", reject_unbounded_audit_read)
    caught: Exception | None = None
    result: RestoreDrillResult | None = None
    try:
        result = acceptance_restore.run()
    except Exception as exc:  # retain whole-file read evidence for one diagnostic assertion
        caught = exc

    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "unbounded_audit_reads": tuple(unbounded_audit_reads),
        "returned_result": result is not None,
        "smoke_calls": len(smoke_calls),
        "target_exists": os.path.lexists(acceptance_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in acceptance_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts,
    }
    assert (
        caught is None
        and result is not None
        and unbounded_audit_reads == []
        and len(smoke_calls) == 1
        and observed["target_exists"] is True
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_acceptance_rejects_audit_jsonl_line_larger_than_one_mib(
    acceptance_restore: SyntheticRestore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_calls = _install_smoke_stub(monkeypatch)
    active = acceptance_restore.package / "data/audit/manual-actions.jsonl"
    prefix = b'{"action_id":"' + ACTION_IDS[0].encode("ascii") + b'","padding":"'
    suffix = b'"}'
    maximum_line_bytes = 1024 * 1024
    padding = b"x" * (maximum_line_bytes + 1 - len(prefix) - len(suffix))
    overlong_line = prefix + padding + suffix
    assert len(overlong_line) == maximum_line_bytes + 1
    active.write_bytes(overlong_line + b"\n")
    acceptance_restore.package_manifest_sha256 = _reseal_package(acceptance_restore.package)
    caught: Exception | None = None
    try:
        acceptance_restore.run()
    except Exception as exc:  # retain line-bound and cleanup evidence for one diagnostic assertion
        caught = exc

    error_text = str(caught).lower() if caught is not None else ""
    observed = {
        "error_type": type(caught).__name__ if caught is not None else None,
        "error_text": error_text,
        "line_bytes": len(overlong_line),
        "smoke_calls": len(smoke_calls),
        "target_exists": os.path.lexists(acceptance_restore.target),
        "owned_work_residue": tuple(
            sorted(
                path.name
                for path in acceptance_restore.target.parent.iterdir()
                if path.name.startswith(".restore-")
            )
        ),
        "live_unchanged": _fact_snapshot(acceptance_restore.app_root) == acceptance_restore.live_facts,
    }
    assert (
        isinstance(caught, RestoreDrillError)
        and any(term in error_text for term in ("audit", "jsonl", "line", "limit", "large"))
        and smoke_calls == []
        and observed["target_exists"] is False
        and observed["owned_work_residue"] == ()
        and observed["live_unchanged"] is True
    ), observed


def test_smoke_environment_is_sealed_and_points_only_to_restored_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    restored_root = tmp_path / "restored"
    (restored_root / "data").mkdir(parents=True)
    monkeypatch.setenv("EIDP_PROXY_SHARED_SECRET", "proxy-canary")
    monkeypatch.setenv("EIDP_BRAVE_API_KEY", "api-canary")
    monkeypatch.setenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")

    environment = restore_drill_module._sealed_smoke_environment(restored_root=restored_root)

    assert environment["EIDP_APP_ROOT"] == str(restored_root)
    assert environment["EIDP_DATA_DIR"] == str(restored_root / "data")
    assert environment["EIDP_DATABASE_URL"] == f"sqlite:///{restored_root / 'data/eidp.sqlite3'}"
    assert Path(environment["HOME"]).is_relative_to(restored_root)
    assert Path(environment["TMPDIR"]).is_relative_to(restored_root)
    assert Path(environment["XDG_CACHE_HOME"]).is_relative_to(restored_root)
    allowed_eidp = {"EIDP_APP_ROOT", "EIDP_DATA_DIR", "EIDP_DATABASE_URL", "EIDP_LOG_LEVEL"}
    assert not any(key.startswith("EIDP_") and key not in allowed_eidp for key in environment)
    assert not any(key.startswith("STREAMLIT_") for key in environment)
    assert "HTTPS_PROXY" not in environment
    serialized = json.dumps(environment, sort_keys=True)
    assert "proxy-canary" not in serialized
    assert "api-canary" not in serialized


def test_owned_smoke_cleanup_escalates_term_to_kill_and_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    signals: list[tuple[int, signal.Signals]] = []

    class TermResistantProcess:
        pid = 424242

        def __init__(self) -> None:
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(["streamlit"], timeout)
            return -signal.SIGKILL

    process = TermResistantProcess()
    monkeypatch.setattr(
        restore_drill_module.os,
        "killpg",
        lambda pid, signum: signals.append((pid, signal.Signals(signum))),
    )

    restore_drill_module._terminate_smoke_process(process, timeout=0.01)

    assert signals == [(process.pid, signal.SIGTERM), (process.pid, signal.SIGKILL)]
    assert process.wait_calls == 2


@pytest.mark.parametrize("leader_state", ("already_exited", "exits_after_term"))
def test_smoke_cleanup_kills_surviving_process_group_after_leader_exit(
    monkeypatch: pytest.MonkeyPatch,
    leader_state: str,
) -> None:
    signals: list[signal.Signals] = []
    child_alive = True

    class ExitedLeaderWithLiveChild:
        pid = 434343

        def __init__(self) -> None:
            self.leader_exited = leader_state == "already_exited"
            self.wait_calls = 0

        def poll(self) -> int | None:
            return 0 if self.leader_exited else None

        def wait(self, timeout: float) -> int:
            assert timeout > 0
            self.wait_calls += 1
            self.leader_exited = True
            return 0

    process = ExitedLeaderWithLiveChild()

    def control_group(pid: int, signum: int) -> None:
        nonlocal child_alive
        assert pid == process.pid
        requested = signal.Signals(signum)
        signals.append(requested)
        if requested == signal.SIGTERM:
            process.leader_exited = True
        elif requested == signal.SIGKILL:
            child_alive = False

    monkeypatch.setattr(restore_drill_module.os, "killpg", control_group)

    restore_drill_module._terminate_smoke_process(process, timeout=0.01)

    assert child_alive is False, {
        "leader_state": leader_state,
        "signals": signals,
        "wait_calls": process.wait_calls,
    }
    assert signal.SIGKILL in signals
    assert process.wait_calls >= 1


def test_real_streamlit_smoke_binds_loopback_uses_restored_settings_and_releases_port(tmp_path: Path) -> None:
    app_root = tmp_path / "checkout"
    restored_root = tmp_path / "restored"
    web_app = app_root / "src/eidp/web/app.py"
    web_app.parent.mkdir(parents=True)
    web_app.write_text(
        "import streamlit as st\n"
        "st.set_page_config(page_title='Restore smoke integration')\n"
        "st.title('Restore smoke integration')\n",
        encoding="utf-8",
    )
    _write_restore_database(restored_root / "data/eidp.sqlite3")
    smoke_port = _unused_loopback_port()

    assert restore_drill_module._run_streamlit_smoke(
        app_root=app_root,
        restored_root=restored_root,
        smoke_port=smoke_port,
        live_port=8502,
        timeout=15.0,
    ) is True

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", smoke_port))


def test_real_streamlit_smoke_with_pinned_fd_uses_restored_settings_and_releases_port(tmp_path: Path) -> None:
    app_root = tmp_path / "checkout"
    restored_root = tmp_path / "restored"
    web_app = app_root / "src/eidp/web/app.py"
    web_app.parent.mkdir(parents=True)
    web_app.write_text(
        "import streamlit as st\n"
        "st.set_page_config(page_title='Restore fd smoke integration')\n"
        "st.title('Restore fd smoke integration')\n",
        encoding="utf-8",
    )
    _write_restore_database(restored_root / "data/eidp.sqlite3")
    smoke_port = _unused_loopback_port()
    restored_fd = os.open(
        restored_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        assert restore_drill_module._run_streamlit_smoke(
            app_root=app_root,
            restored_root=restored_root,
            restored_fd=restored_fd,
            smoke_port=smoke_port,
            live_port=8502,
            timeout=15.0,
        ) is True
    finally:
        os.close(restored_fd)

    assert not (restored_root / ".restore-smoke-runtime").exists()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", smoke_port))


def test_real_streamlit_smoke_with_pinned_fd_ignores_rebound_lexical_parent_and_cleans_up(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "checkout"
    restored_parent = tmp_path / "restore-parent"
    restored_root = restored_parent / "restored"
    displaced_parent = tmp_path / "restore-parent-displaced"
    outside = tmp_path / "outside"
    web_app = app_root / "src/eidp/web/app.py"
    web_app.parent.mkdir(parents=True)
    web_app.write_text(
        "import streamlit as st\n"
        "st.set_page_config(page_title='Restore rebound fd smoke integration')\n"
        "st.title('Restore rebound fd smoke integration')\n",
        encoding="utf-8",
    )
    _write_restore_database(restored_root / "data/eidp.sqlite3")
    outside.mkdir()
    outside_stat = os.lstat(outside)
    outside_identity = (outside_stat.st_dev, outside_stat.st_ino)
    outside_mtime = outside_stat.st_mtime_ns
    smoke_port = _unused_loopback_port()
    restored_fd = os.open(
        restored_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    os.rename(restored_parent, displaced_parent)
    restored_parent.symlink_to(outside, target_is_directory=True)
    assert not restored_root.exists()
    try:
        assert restore_drill_module._run_streamlit_smoke(
            app_root=app_root,
            restored_root=restored_root,
            restored_fd=restored_fd,
            smoke_port=smoke_port,
            live_port=8502,
            timeout=15.0,
        ) is True
    finally:
        os.close(restored_fd)

    current_outside_stat = os.lstat(outside)
    assert (current_outside_stat.st_dev, current_outside_stat.st_ino) == outside_identity
    assert current_outside_stat.st_mtime_ns == outside_mtime
    assert tuple(outside.iterdir()) == ()
    assert not (displaced_parent / "restored/.restore-smoke-runtime").exists()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", smoke_port))
