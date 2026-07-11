# Linux/Web v1 Phase 1 Runtime And Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-confined Linux controller, deployment manifest, bounded logging and verified backup package so the application can be operated and recovered without system-wide installation.

**Architecture:** A thin Bash entrypoint sources the existing filesystem boundary and delegates to focused Python `eidp.ops` modules. Process identity is verified before signalling, stdout is supervised through a rotating runner, manifests are written atomically, and backup packages reuse the existing SQLite `VACUUM INTO` snapshot under the global write lock.

**Tech Stack:** Bash, Python 3.12 stdlib, Typer, SQLAlchemy, SQLite, pytest

## Global Constraints

- Execute only after Phase 0 is merged into protected `origin/main`.
- Runtime writes stay below `/home/junming/EIDP`; bind remains exactly `127.0.0.1`.
- Do not source/eval `.env`; accept only `EIDP_WEB_PORT`, `EIDP_WEB_BASE_URL_PATH`, `EIDP_INTERNAL_BASE_URL`, and `EIDP_WEB_MAX_UPLOAD_MB`.
- `logs/web.log` rotates at 10 MiB with at most five retained files.
- Process operations verify PID, Linux start time, app root and argv marker before signalling.
- Backup packaging holds `data/.lock`, reuses `backup_sqlite_database()`, stages and verifies before atomic finalization.
- Same-host backups are not disaster recovery; only an ICT off-host receipt closes the v1 recovery gate.
- Use one short-lived Phase 1 branch for Tasks 1–6; it is review transport, not another product line.

Before Task 1:

```bash
git fetch --prune origin
git switch -c feat/linux-web-v1-phase1-runtime-recovery origin/main
```

---

### Task 1: Safe Runtime Configuration

**Files:**
- Create: `src/eidp/ops/__init__.py`
- Create: `src/eidp/ops/runtime_config.py`
- Create: `tests/unit/test_runtime_config.py`
- Modify: `deploy/linux/env.example`

**Interfaces:**
- Consumes: project-root `.env` as untrusted text
- Produces: `RuntimeLaunchConfig` and `load_runtime_config(path: Path) -> RuntimeLaunchConfig`

- [ ] **Step 1: Write failing allowlist and validation tests**

Add tests for defaults, four accepted keys, duplicate key, malformed assignment, control characters, shell syntax, invalid port, invalid base path, non-HTTP URL and non-positive upload size:

```python
def test_runtime_config_does_not_execute_or_accept_unknown_keys(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"EIDP_WEB_PORT=8502\nEIDP_PROXY_SHARED_SECRET=$(touch {marker})\n",
        encoding="utf-8",
    )
    config = load_runtime_config(env_file)
    assert config.port == 8502
    assert not marker.exists()
    assert "EIDP_PROXY_SHARED_SECRET" not in config.as_streamlit_env()
```

Also test that URL userinfo/query/fragment is rejected, URL path exactly equals normalized base path, root URL requires empty base path, and inherited `EIDP_WEB_PORT`/all `STREAMLIT_SERVER_*`/`STREAMLIT_BROWSER_*` keys cannot override validated values.

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
uv run pytest tests/unit/test_runtime_config.py -v
```

Expected: FAIL because `eidp.ops.runtime_config` does not exist.

- [ ] **Step 3: Implement the strict parser and value object**

Implement these exact public types:

```python
@dataclass(frozen=True)
class RuntimeLaunchConfig:
    port: int = 8502
    base_url_path: str = ""
    internal_base_url: str = ""
    max_upload_mb: int = 200

    def as_streamlit_env(self) -> dict[str, str]:
        values = {
            "STREAMLIT_SERVER_PORT": str(self.port),
            "STREAMLIT_SERVER_MAX_UPLOAD_SIZE": str(self.max_upload_mb),
            "STREAMLIT_SERVER_BASE_URL_PATH": self.base_url_path.lstrip("/"),
        }
        if self.internal_base_url:
            public = urlsplit(self.internal_base_url)
            origin = f"{public.scheme}://{public.netloc}"
            values["STREAMLIT_BROWSER_SERVER_ADDRESS"] = public.hostname or ""
            values["STREAMLIT_BROWSER_SERVER_PORT"] = str(public.port or (443 if public.scheme == "https" else 80))
            values["STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS"] = json.dumps([origin])
        return values


def load_runtime_config(path: Path) -> RuntimeLaunchConfig:
    values = _parse_allowed_assignments(path)
    config = RuntimeLaunchConfig(
        port=_validated_port(values.get("EIDP_WEB_PORT", "8502")),
        base_url_path=_validated_base_path(values.get("EIDP_WEB_BASE_URL_PATH", "")),
        internal_base_url=_validated_http_url(values.get("EIDP_INTERNAL_BASE_URL", "")),
        max_upload_mb=_validated_positive_int(values.get("EIDP_WEB_MAX_UPLOAD_MB", "200")),
    )
    _require_public_url_path_match(config)
    return config


def sanitized_child_env(inherited: Mapping[str, str], config: RuntimeLaunchConfig) -> dict[str, str]:
    blocked_prefixes = ("STREAMLIT_SERVER_", "STREAMLIT_BROWSER_")
    child = {
        key: value for key, value in inherited.items()
        if key != "EIDP_WEB_PORT" and not key.startswith(blocked_prefixes)
    }
    child.update(config.as_streamlit_env())
    return child
```

The parser ignores blank/comment/unknown-key lines, rejects duplicate allowlisted keys, accepts only literal `KEY=value` data, and never calls `source`, `eval`, a shell, or variable expansion.

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
uv run pytest tests/unit/test_runtime_config.py -v
uv run ruff check src/eidp/ops tests/unit/test_runtime_config.py
uv run mypy src/eidp/ops
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/eidp/ops deploy/linux/env.example tests/unit/test_runtime_config.py
git commit -m "feat: validate Linux runtime configuration" -m "Goals: G7, G8, G13"
```

### Task 2: Process Controller And Rotating Supervisor

**Files:**
- Create: `src/eidp/ops/rotating_runner.py`
- Create: `src/eidp/ops/runtime_controller.py`
- Create: `deploy/linux/eidpctl.sh`
- Modify: `deploy/linux/run_web.sh`
- Modify: `.gitignore`
- Create: `tests/unit/test_rotating_runner.py`
- Create: `tests/unit/test_linux_runtime_controller.py`
- Modify: `tests/unit/test_linux_web_release_contract.py`

**Interfaces:**
- Consumes: `RuntimeLaunchConfig`, existing `project_env.sh`, `.venv`, Streamlit health endpoint
- Produces: `eidpctl.sh db-bootstrap|import-excel|start|status|stop|restart|health`, `run/eidp.pid.json`, bounded `logs/web.log`; later tasks add manifest/backup/restore subcommands

- [ ] **Step 1: Write failing process-safety tests**

Cover duplicate start, stale PID cleanup, live PID with wrong start time/argv/app root, occupied port, stop refusing unrelated PID, health timeout, restart, SSH-parent exit survival, log rotation and TERM forwarding. Linux `/proc` assertions use `pytest.mark.skipif(sys.platform != "linux")`.

```python
def test_stop_refuses_live_pid_with_wrong_signature(controller_env: ControllerEnv) -> None:
    controller_env.write_pid_metadata(pid=os.getpid(), start_time="wrong", argv_marker="eidp.ops.rotating_runner")
    result = controller_env.run("stop")
    assert result.returncode != 0
    assert "identity mismatch" in result.stderr
```

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
uv run pytest tests/unit/test_rotating_runner.py tests/unit/test_linux_runtime_controller.py -v
```

Expected: FAIL because the controller/runner do not exist.

- [ ] **Step 3: Implement the supervisor contract**

Expose these interfaces:

```python
@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    linux_start_time: str
    app_root: str
    argv_marker: str


def run_rotating(
    command: Sequence[str],
    *,
    log_path: Path,
    max_bytes: int = 10 * 1024 * 1024,
    backups: int = 5,
) -> int:
    """Run one child, rotate its combined output, forward TERM/INT, return its exit code."""


def read_verified_process(pid_file: Path, *, app_root: Path) -> ProcessIdentity | None:
    """Return None for a dead PID; raise ProcessIdentityError for a live mismatch."""
```

Serialize controller operations with `fcntl.flock(run/eidpctl.lock)`. Start the rotating supervisor with `start_new_session=True`; wait for `/_stcore/health` before reporting success. Revalidate PID/start time immediately before every signal.

- [ ] **Step 4: Implement the thin Bash entrypoint**

`deploy/linux/eidpctl.sh` must contain only boundary setup and delegation:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=project_env.sh
source "${SCRIPT_DIR}/project_env.sh"
cd "${APP_ROOT}"
exec uv run --frozen --no-sync python -m eidp.ops.runtime_controller "$@"
```

`run_web.sh` remains loopback-only and receives only the validated Streamlit environment produced by the controller. Add `/run/`, `/backups/`, `/evidence/runtime/`, and `/restore-drills/` to `.gitignore`.
Remove the launcher's direct `${EIDP_WEB_PORT:-8502}` read; the controller-sanitized `STREAMLIT_SERVER_PORT` is the sole port input, while `--server.address 127.0.0.1` remains a fixed CLI argument. `eidpctl.sh status --json` must report verified PID, address and port for later socket evidence.
The `import-excel` controller subcommand delegates only to the existing locked `eidp import-excel PATH` command after resolving PATH inside the project root; it rejects symlinks and outside-root paths.

- [ ] **Step 5: Run focused and contract tests**

Run:

```bash
uv run pytest tests/unit/test_rotating_runner.py tests/unit/test_linux_runtime_controller.py tests/unit/test_linux_web_release_contract.py -v
uv run ruff check src/eidp/ops tests/unit/test_rotating_runner.py tests/unit/test_linux_runtime_controller.py
uv run mypy src/eidp/ops
```

Expected: all pass; static contract still proves loopback bind.

- [ ] **Step 6: Commit**

```bash
git add .gitignore deploy/linux src/eidp/ops tests/unit/test_rotating_runner.py tests/unit/test_linux_runtime_controller.py tests/unit/test_linux_web_release_contract.py
git commit -m "feat: add project-local Linux process control" -m "Goals: G5, G8, G9, G12, G13"
```

### Task 3: Traceable Deployment Manifest

**Files:**
- Create: `src/eidp/ops/deployment_manifest.py`
- Modify: `src/eidp/ops/runtime_controller.py`
- Create: `tests/unit/test_deployment_manifest.py`

**Interfaces:**
- Consumes: clean Git checkout, `origin/main`, `uv.lock`, SQLite `alembic_version`, validated runtime config
- Produces: atomic secret-free `run/deployment-manifest.json`

- [ ] **Step 1: Write failing manifest tests**

```python
def test_manifest_refuses_unpublished_or_dirty_checkout(repo: RepoFixture, tmp_path: Path) -> None:
    repo.write_untracked("dirty.txt")
    with pytest.raises(DeploymentManifestError, match="clean checkout"):
        collect_deployment_manifest(app_root=repo.path, runtime=RuntimeLaunchConfig(), actor="operator")
```

Also assert default collection requires HEAD equal fetched `origin/main`. When an explicit checked `expected_deployment_commit` is supplied, require HEAD equal that commit and prove it is still an ancestor of fetched `origin/main`; a later main advance is recorded but does not silently change the deployment. Assert `uv.lock` SHA-256 and schema head are present, writes use temp+fsync+replace, and environment secrets never appear.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_deployment_manifest.py -v
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement typed collection and atomic write**

```python
@dataclass(frozen=True)
class DeploymentManifest:
    deployed_commit: str
    expected_deployment_commit: str
    origin_main_commit: str
    uv_lock_sha256: str
    schema_head: str
    deployed_at_utc: str
    operator: str
    internal_base_url: str
    port: int
    base_url_path: str
    pre_upgrade_backup_id: str | None
    off_host_receipt_id: str | None


def collect_deployment_manifest(
    *, app_root: Path, runtime: RuntimeLaunchConfig, actor: str,
    expected_deployment_commit: str | None = None,
    pre_upgrade_backup_id: str | None = None,
    off_host_receipt_id: str | None = None,
) -> DeploymentManifest:
    """Fail closed on dirty/unpublished/unexpected source and return whitelisted fields."""


def write_deployment_manifest_atomic(path: Path, manifest: DeploymentManifest) -> None:
    """Write JSON to a same-directory temp file, fsync it, replace, then fsync the directory."""
```

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_deployment_manifest.py -v
uv run ruff check src/eidp/ops/deployment_manifest.py tests/unit/test_deployment_manifest.py
uv run mypy src/eidp/ops/deployment_manifest.py
git add src/eidp/ops/runtime_controller.py src/eidp/ops/deployment_manifest.py tests/unit/test_deployment_manifest.py
git commit -m "feat: record traceable Linux deployments" -m "Goals: G5, G9, G14"
```

### Task 4: Finalized Backup Packages

**Files:**
- Create: `src/eidp/ops/backup_package.py`
- Modify: `src/eidp/cli.py`
- Create: `tests/unit/test_backup_package.py`
- Modify: `tests/unit/test_cli_write_lock_contract.py`

**Interfaces:**
- Consumes: existing `backup_sqlite_database()`, deployment manifest, project-root data/audit/source/export files
- Produces: verified `backups/{backup_id}` with `backup-manifest.v1.json` and `FINALIZED`

- [ ] **Step 1: Write failing package and lock tests**

Test complete inventory/hashes, `.env`/logs/cache/PID/backups exclusion, symlink/outside-root refusal, interrupted staging, tamper detection, finalized no-overwrite, same-ID idempotent recovery and CLI acquisition of `data/.lock`. The allowlist includes the SQLite snapshot, `data/master.xlsx`, `data/audit/**`, `data/web-intake/**`, `data/source-pdfs/**`, and `output/exports/**`; absent optional trees are recorded as absent, not errors. Create a synthetic full-SHA CAS blob and prove its exact relative path/digest enters the manifest. Test the pre-upgrade variant's code/schema/source-path binding, integrity verification and refusal without a caller-held data lock. Verification opens packaged SQLite with a read-only URI (`mode=ro`, `immutable=1` when supported) and proves every package file hash is identical before/after verification.

```python
def test_ict_can_pull_only_verified_finalized_package(package_fixture: PackageFixture) -> None:
    staged = package_fixture.build(interrupt_before_finalize=True)
    assert not (staged / "FINALIZED").exists()
    with pytest.raises(BackupPackageError, match="not finalized"):
        verify_backup_package(staged)
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_backup_package.py tests/unit/test_cli_write_lock_contract.py -v
```

Expected: FAIL because package builder/CLI command are absent.

- [ ] **Step 3: Implement the package lifecycle**

```python
@dataclass(frozen=True)
class BackupPackageResult:
    backup_id: str
    finalized_path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class VerifiedPreUpgradeSnapshot:
    snapshot_path: Path
    manifest_path: Path
    snapshot_sha256: str
    source_database_relative_path: str
    deployment_commit: str
    schema_head: str


def build_backup_package(
    *, app_root: Path, database_path: Path, backup_id: str,
    deployment_manifest: Path, actor: str,
) -> BackupPackageResult:
    """Build in .staging, reuse backup_sqlite_database, hash inventory, atomically finalize."""


def verify_backup_package(path: Path) -> BackupPackageResult:
    """Require FINALIZED, verify manifest/hash inventory and SQLite integrity."""


def build_pre_upgrade_snapshot(
    *, app_root: Path, database_path: Path,
    upgrade_id: str, deployment_commit: str,
) -> VerifiedPreUpgradeSnapshot:
    """Create and verify a code-paired SQLite snapshot while caller holds the data lock."""
```

Manifest fields bind `deployment_commit`, Alembic/schema head, source database relative path, successful WAL checkpoint time/status, SQLite snapshot SHA-256, and every allowlisted artifact digest. Do **not** claim the `VACUUM INTO` snapshot bytes equal the live SQLite file bytes. Safety comes from holding the global lock across checkpoint, snapshot, inventory and finalization, then verifying the snapshot's integrity and manifest. `build_pre_upgrade_snapshot()` is a DB-only code-paired variant used by later schema rebuilds; it does not acquire a second lock and refuses to run unless its caller proves the global data lock is held.

The `eidp backup-package` CLI wraps the entire build in `_require_app_lock("cli_backup_package")`; `eidp backup-verify PATH` is read-only. Expose both through `eidpctl.sh` so project-root environment/cache redirection always applies. Add `build_backup_package` to the AST write-lock contract. ICT receipt IDs are recorded later; the builder never fabricates one.

- [ ] **Step 4: Run focused and full quality checks**

```bash
uv run pytest tests/unit/test_backup_package.py tests/unit/test_sqlite_backup.py tests/unit/test_cli_write_lock_contract.py -v
uv run ruff check src/eidp/ops/backup_package.py src/eidp/cli.py tests/unit/test_backup_package.py
uv run mypy src/eidp/ops/backup_package.py src/eidp/cli.py
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/eidp/ops/backup_package.py src/eidp/cli.py tests/unit/test_backup_package.py tests/unit/test_cli_write_lock_contract.py
git commit -m "feat: build finalized recovery packages" -m "Goals: G2, G9, G10, G13"
```

### Task 5: Isolated Restore Drill

**Files:**
- Create: `src/eidp/ops/restore_drill.py`
- Create: `src/eidp/ops/receipt_id.py`
- Modify: `src/eidp/cli.py`
- Create: `tests/unit/test_restore_drill.py`

**Interfaces:**
- Consumes: a verified finalized backup package and matching protected checkout
- Produces: an isolated restored tree plus secret-free `restore-report.v1.json`; live data is untouched

- [ ] **Step 1: Write failing traversal, isolation and smoke tests**

Test refusal of non-finalized/tampered packages, wrong expected package-manifest digest, symlink/path escape, target outside `restore-drills`, live DB path reuse, schema/commit mismatch, and conflicting existing target. Prove an identical completed target returns the same verified report idempotently. Prove restored SQLite integrity and a temporary loopback Streamlit health smoke use restored data and stop cleanly. With acceptance expectations, require a non-symlink file below `evidence/runtime/`, validate schema `eidp.restore-evidence-expectation.v1`, then verify restored export ID/workbook/manifest hashes, required manual action IDs and exactly one audit projection per action.

```python
def test_restore_drill_never_uses_live_data_dir(restore_fixture: RestoreFixture) -> None:
    with pytest.raises(RestoreDrillError, match="isolated restore-drills path"):
        run_restore_drill(
            app_root=restore_fixture.app_root,
            package_path=restore_fixture.package,
            target_path=restore_fixture.app_root / "data",
            smoke_port=18502,
        )
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_restore_drill.py -v
```

Expected: FAIL because restore orchestration is absent.

- [ ] **Step 3: Implement verified isolated restoration**

```python
@dataclass(frozen=True)
class RestoreDrillResult:
    backup_id: str
    restored_path: Path
    deployment_commit: str
    schema_head: str
    sqlite_integrity: str
    health_ok: bool
    package_manifest_sha256: str
    off_host_receipt_id: str | None
    report_path: Path


@dataclass(frozen=True)
class RestoreEvidenceExpectation:
    export_id: str
    workbook_sha256: str
    export_manifest_sha256: str
    action_ids: tuple[str, ...]


def run_restore_drill(
    *, app_root: Path, package_path: Path,
    target_path: Path, smoke_port: int = 18502,
    expected_package_manifest_sha256: str | None = None,
    off_host_receipt_id: str | None = None,
    expected_evidence: RestoreEvidenceExpectation | None = None,
) -> RestoreDrillResult:
    """Verify package, copy below restore-drills, check DB, run/stop temporary loopback smoke."""
```

The smoke process receives restored `EIDP_DATA_DIR`/database URL, fixed `127.0.0.1`, a non-production port, and no proxy secret. It must be terminated in `finally`. `receipt_id.py` defines the shared allowlist validator `^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$`. Expose the command through `eidpctl.sh restore-drill` with `--expected-manifest-sha`, `--off-host-receipt-id`, and optional `--acceptance-expectations`. When a validated receipt is supplied the expected digest is mandatory; the report persists both and the verified evidence results, never credentials. It does not update the live deployment manifest.

- [ ] **Step 4: Add CLI, run tests and commit**

```bash
uv run pytest tests/unit/test_restore_drill.py tests/unit/test_backup_package.py -v
uv run ruff check src/eidp/ops/restore_drill.py src/eidp/ops/receipt_id.py src/eidp/cli.py tests/unit/test_restore_drill.py
uv run mypy src/eidp/ops/restore_drill.py src/eidp/ops/receipt_id.py src/eidp/cli.py
git add src/eidp/ops/restore_drill.py src/eidp/ops/receipt_id.py src/eidp/cli.py tests/unit/test_restore_drill.py
git commit -m "feat: verify isolated backup restoration" -m "Goals: G3, G9, G13, G14"
```

### Task 6: Phase 1 Integration Gate

**Files:**
- Modify if contract coverage requires it: `tests/unit/test_linux_web_release_contract.py`
- Modify: `docs/runbooks/venus-init-and-acceptance.md`

**Interfaces:**
- Consumes: Tasks 1–5
- Produces: one reviewable Phase 1 PR with local runtime/recovery evidence; no Venus deployment

- [ ] **Step 1: Run complete gates**

```bash
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
```

Expected: all pass.

- [ ] **Step 2: Update truth labels only for proven behavior**

Change controller/manifest/package lines from PENDING only when their tests pass. Keep off-host restore, ICT proxy and Venus gates PENDING.

- [ ] **Step 3: Commit the evidence update**

```bash
git add docs/runbooks/venus-init-and-acceptance.md tests/unit/test_linux_web_release_contract.py
git commit -m "docs: record local runtime recovery evidence" -m "Goals: G5, G9, G14"
```

- [ ] **Step 4: Publish, observe checks, and merge only with authorization**

After explicit external-write authorization:

```bash
git push -u origin feat/linux-web-v1-phase1-runtime-recovery
gh pr create --base main --head feat/linux-web-v1-phase1-runtime-recovery --title "feat: harden Linux Web runtime recovery" --body $'Summary:\n- add project-confined runtime control and deployment manifest\n- add finalized backup packages and isolated restore drills\n\nVerification:\n- full local quality gates passed\n\nGoals: G5, G8, G9, G12, G13, G14'
gh pr checks feat/linux-web-v1-phase1-runtime-recovery --watch --interval 10
```

Require both named checks green. Obtain explicit owner merge authorization, then:

```bash
gh pr merge feat/linux-web-v1-phase1-runtime-recovery --merge --delete-branch
git fetch --prune origin
git switch main
git merge --ff-only origin/main
test "$(git rev-list --left-right --count origin/main...main | tr '\t' ' ')" = "0 0"
git status --short --branch
```

Expected: clean synchronized `main`. Phase 2 branches only from this merged result.
