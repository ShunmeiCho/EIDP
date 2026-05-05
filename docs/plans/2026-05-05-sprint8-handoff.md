# Sprint 8 Local Handoff

Status: Ready for commit; local commit unblocked, push to `origin/main`
gated on owner approval
Updated: 2026-05-05

This handoff was originally produced by the Codex CLI sandbox, where
`.git/` write returned `Operation not permitted`:

```text
touch .git/codex-write-test
=> Operation not permitted
```

A subsequent Claude Code session re-probed the repository and confirmed
`.git/` is writable from a normal developer shell:

```text
touch .git/eidp-write-probe
=> success
```

So the original "cannot write `.git/`" reading was a Codex sandbox
limitation, not a repository state. Local commit is therefore unblocked;
the recovery patch and bundle below remain available as a fallback for
any future environment that hits the same sandbox restriction.

Remote `push origin main` is still gated on explicit owner approval per
the Sprint 8 release-gate convention. The recommended landing path is to
create a feature branch (e.g. `sprint8-handoff-finalize`), commit
Sprint 8.7 / 8.8 / 8.9 + the simplify pass as separate commits on that
branch, and let the owner review before merging.

## Consolidated Handoff Archive

For transfer, use the tarball below. It contains the commit bundle, recovery
patch, portable `.sha256` sidecars that use relative filenames, and this
handoff document as `README-handoff.md`.

```text
/private/tmp/eidp-sprint8-handoff-20260505.tar.gz
```

After unpacking, verify the contents from inside the extracted directory:

```text
sha256sum -c eidp-sprint8-commits-20260505.bundle.sha256
sha256sum -c eidp-sprint8-local-changes-20260505.patch.sha256
```

The tarball itself also has an external sidecar:

```text
/private/tmp/eidp-sprint8-handoff-20260505.tar.gz.sha256
```

The external sidecar also uses a relative filename. After transferring both
files to another directory, verify from that directory:

```text
sha256sum -c eidp-sprint8-handoff-20260505.tar.gz.sha256
```

## Commit Bundle

The already committed local history from `origin/main` through `e3becc4` is
available as a git bundle:

```text
/private/tmp/eidp-sprint8-commits-20260505.bundle
sha256: 20044d1b32aa41f3be69aa57a491e666b9eb31c57aea7b0e03a77f63e84995e5
contains: e3becc4
requires: ec2ec94
```

The bundle was verified locally:

```text
git bundle verify /private/tmp/eidp-sprint8-commits-20260505.bundle
=> /private/tmp/eidp-sprint8-commits-20260505.bundle is okay
```

Recover committed history in a checkout that has `ec2ec94`:

```text
git fetch /private/tmp/eidp-sprint8-commits-20260505.bundle HEAD:sprint8-local-history
git switch sprint8-local-history
```

Full restore rehearsal was checked from the unpacked handoff archive in
`/private/tmp`:

```text
tar -xzf /private/tmp/eidp-sprint8-handoff-20260505.tar.gz
cd eidp-sprint8-handoff-20260505
sha256sum -c eidp-sprint8-commits-20260505.bundle.sha256
sha256sum -c eidp-sprint8-local-changes-20260505.patch.sha256
git init
git fetch /Users/shunmei/workspace/EIDP ec2ec9405b5d19192fb0e952c525c2a920c280b0
git switch --detach FETCH_HEAD
git fetch eidp-sprint8-commits-20260505.bundle HEAD:sprint8-local-history
git switch sprint8-local-history
git apply --check eidp-sprint8-local-changes-20260505.patch
git apply eidp-sprint8-local-changes-20260505.patch
=> OK simplify-current archive restore: base=e3becc4 status_count=42 tracked_changed=16 untracked=30
```

## Recovery Patch

```text
/private/tmp/eidp-sprint8-local-changes-20260505.patch
```

Base commit:

```text
e3becc4 feat(sprint8.6.d.4): queue depth dashboard in audit log page
```

The patch includes tracked changes and untracked Sprint 8 files after
`e3becc4`. It excludes `_temp/`, which is unrelated local mockup output and
should not be committed.

Apply from a clean checkout at `e3becc4` after fetching the bundle:

```text
git apply /private/tmp/eidp-sprint8-local-changes-20260505.patch
git status --short
```

Patch application was checked against a clean `git archive` of `e3becc4`:

```text
git apply --check /private/tmp/eidp-sprint8-local-changes-20260505.patch
=> OK
```

Expected status after applying:

- modified `.env.example`
- Venus cron/systemd files removed from their old paths
- Venus files added under `deploy/legacy-venus/`
- Windows runbooks, architecture docs, and plan docs added
- Windows packaging / add-on / verifier scripts added
- weekly runner and `.bat` hardening applied
- unit tests for packaging, migration, weekly runner, and verifier added

Do not stage `_temp/`.

## Verification Before Commit

Run:

```text
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit -q
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run ruff check \
  scripts/_packaging_lib.py \
  scripts/check_windows_paths.py \
  scripts/build_ocr_addon_zip.py \
  scripts/build_playwright_addon_zip.py \
  scripts/migrate_pg_to_sqlite.py \
  scripts/validate_windows_install.py \
  scripts/verify_windows_distribution.py \
  tests/unit/test_ocr_addon_packaging.py \
  tests/unit/test_pg_to_sqlite_migration.py \
  tests/unit/test_playwright_addon_packaging.py \
  tests/unit/test_windows_install_validator.py \
  tests/unit/test_windows_path_safety.py \
  tests/unit/test_windows_distribution_verifier.py
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run python scripts/check_windows_paths.py
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run mypy scripts/verify_windows_distribution.py
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run mypy scripts/validate_windows_install.py
git diff --check
```

Latest local evidence:

```text
tests/unit: 593 passed, 5 warnings
check_windows_paths.py: OK, 247 paths checked
verify_windows_distribution.py mypy: success
validate_windows_install.py mypy: success
validate_install.bat: included in the core ZIP and used by the VM checklist
verify_windows_distribution.py smoke: OK core for /private/tmp/eidp-zip-wrapper-smoke/eidp-windows.zip
verify_windows_distribution.py add-on integrity smoke: OK ocr-addon + OK playwright-addon
verify_windows_distribution.py .bat contract tests: rejects stale launch, locale-dependent weekly scripts, and data-deleting uninstall scripts
verify_windows_distribution.py Python entrypoint tests: rejects stale validator and weekly Excel export regressions
git diff --check: clean
```

## Suggested Commit Split

The split below keeps review manageable while preserving the Sprint 8
decision trail. Use the repository's Lore commit protocol.

### Commit 1 — Weekly runner Windows hardening

Stage:

```text
git add scripts/run_r8_rediscovery_weekly.py scripts/weekly_run.bat \
  tests/unit/test_r8_rediscovery_weekly.py \
  tests/unit/test_windows_packaging_spike.py
```

Message:

```text
Make weekly R8 runs observable and lock-safe on Windows

The operator PC flow needs weekly_run.bat to behave like a Task Scheduler
entrypoint rather than a Venus cron wrapper. The runner now resolves paths
from app root, acquires the shared UI lock, writes last_run.json, preserves
failure status, and prunes logs to a 12-week ringbuffer.

Constraint: Sprint 8 v6 requires Windows-PC operation with no terminal access
Constraint: Weekly runner must not generate Excel; Excel remains UI-driven
Rejected: Keep relying on cron-oriented defaults | cwd and logging are not stable under Task Scheduler
Confidence: high
Scope-risk: moderate
Directive: Do not reintroduce locale-dependent %DATE% parsing in weekly_run.bat
Tested: UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit/test_r8_rediscovery_weekly.py tests/unit/test_windows_packaging_spike.py -q
Not-tested: Actual Windows Task Scheduler execution; covered by VM gate
```

### Commit 2 — Migration and Windows distribution tooling

Stage:

```text
git add scripts/windows_path_safety.py scripts/check_windows_paths.py \
  scripts/_packaging_lib.py \
  scripts/build_windows_zip.py scripts/build_ocr_addon_zip.py \
  scripts/build_playwright_addon_zip.py scripts/migrate_pg_to_sqlite.py \
  scripts/first_setup.bat scripts/launch.bat \
  scripts/validate_install.bat scripts/validate_windows_install.py scripts/verify_windows_distribution.py .env.example \
  tests/unit/test_config.py tests/unit/test_ocr_addon_packaging.py \
  tests/unit/test_pg_to_sqlite_migration.py \
  tests/unit/test_playwright_addon_packaging.py \
  tests/unit/test_windows_install_validator.py \
  tests/unit/test_windows_path_safety.py \
  tests/unit/test_windows_distribution_verifier.py
```

Message:

```text
Close Mac-side distribution checks before the Windows VM gate

The Windows ZIP still needs real runtime and VM validation, but Mac-side
builds can now prove package shape before handoff: wheel ABI/platform,
runtime paths, project wheel presence, add-on layout, Windows path safety,
checksum JSON, and the dev-only PostgreSQL-to-SQLite corpus migration path.

Constraint: Network and Windows execution are external gates in this environment
Constraint: Operator ZIP must be verifiable before transfer to the VM
Rejected: Rely on manual ZIP inspection | misses project wheel/runtime/checksum regressions
Confidence: high
Scope-risk: moderate
Directive: Keep verify_windows_distribution.py stricter than build_windows_zip.py; it is a release gate, not a convenience helper
Tested: UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit/test_windows_distribution_verifier.py tests/unit/test_ocr_addon_packaging.py tests/unit/test_playwright_addon_packaging.py tests/unit/test_pg_to_sqlite_migration.py tests/unit/test_config.py -q
Not-tested: Production ZIP generation with live downloads; blocked until runtime/wheelhouse artifacts are available
```

### Commit 3 — Windows runbooks and Venus archive

Stage:

```text
git add README.md docs/architecture.md docs/runbooks/eidp-windows.md \
  docs/runbooks/eidp-windows-vm-validation.md \
  docs/runbooks/eidp-operator-e2e-template.md \
  docs/runbooks/eidp-r8-rediscovery.md \
  docs/plans/2026-04-11-eidp-design.md \
  docs/plans/2026-05-04-sprint8-win-deployment.md \
  docs/plans/2026-05-05-sprint8-release-gate-audit.md \
  docs/plans/2026-05-05-sprint8-handoff.md \
  docs/plans/future-natural-language-query.md \
  docs/plans/future-v2-roadmap.md \
  deploy/legacy-venus \
  deploy/cron/eidp-r8-rediscovery.cron deploy/cron/install.sh \
  deploy/systemd/eidp-r8-rediscovery.service \
  deploy/systemd/eidp-r8-rediscovery.timer \
  scripts/run_r8_rediscovery_cron.sh
```

Message:

```text
Document the Windows handoff and archive Venus operations

Sprint 8 changes the operational owner from a Linux server to one Windows
operator PC. The docs now separate operator instructions, VM validation,
architecture, release gates, future roadmap, and legacy Venus paths.

Constraint: Venus crontab is no longer in production scope
Constraint: Non-technical operator must not need terminal, SSH, or SQL
Rejected: Leave Venus runbook as primary | conflicts with Windows-PC final target
Confidence: high
Scope-risk: narrow
Directive: Treat Windows VM Stage 2-5c and real operator PC E2E as mandatory gates before v1.0
Tested: git diff --check; docs are linked from README and runbooks
Not-tested: Operator trial reading and screenshots; fold in after VM/real-PC validation
```

## Post-Commit Commands

After committing:

```text
git log --oneline -3
git status --short
```

Push only after confirming the branch target:

```text
git push origin main
```

If direct main push is not allowed, create a branch instead:

```text
git switch -c sprint8-windows-handoff
git push -u origin sprint8-windows-handoff
```

## Remaining External Gates

Do not mark Sprint 8 complete until these are closed with evidence:

1. production `dist/eidp-windows.zip` built with real `runtime/` and wheelhouse;
2. `dist/windows-distribution-verification.json` generated and stored with the ZIPs;
3. Windows VM offline validation Stage 2-5c passed;
4. VM findings folded back into code / runbook;
5. one real operator PC R8 cycle passed with KPI and owner sign-off.
   Record the cycle in `docs/runbooks/eidp-operator-e2e-template.md`.
