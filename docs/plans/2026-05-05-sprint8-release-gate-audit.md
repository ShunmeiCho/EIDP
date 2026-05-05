# Sprint 8 Release Gate Audit

Status: Local implementation audit complete; external gates remain open
Updated: 2026-05-05

This audit maps the Sprint 8 objective to concrete artifacts and evidence.
It is intentionally stricter than "tests are green": a requirement is closed
only when the artifact and its verification directly cover the operational
constraint.

## Objective Restatement

EIDP Sprint 8 is complete only when a non-technical operator can use a
single Windows PC to run the four business steps without terminal, SSH, or
SQL access:

1. collect PDFs;
2. decide / override R8 fiscal year;
3. extract or manually enter enrollment data;
4. preview and export the weekly Excel output.

Deployment must be a Windows ZIP flow:

1. unzip;
2. double-click `first_setup.bat`;
3. double-click `launch.bat`;
4. weekly processing runs through Task Scheduler / `weekly_run.bat`;
5. optional OCR and Playwright add-ons do not break the core ZIP.

## Prompt-to-Artifact Checklist

| Requirement | Artifact / command | Evidence | Gate |
| --- | --- | --- | --- |
| SQLite bootstrap with schema contract | `src/eidp/db/sqlite_bootstrap.py`, `eidp db-bootstrap --sqlite` | Logged as completed in `docs/plans/2026-05-04-sprint8-win-deployment.md`; unit suite covers SQLite bootstrap | Local closed |
| SQLite PRAGMA per connection | `src/eidp/db/session.py` | Unit suite included in prior Sprint 8.1.1 verification | Local closed |
| 4-table fiscal year override | `src/eidp/pipeline/fiscal_year_override.py` | Prior 8.2 verification; current-read filters logged | Local closed |
| SupportRecipient / SchoolYearStatus append-only | `src/eidp/pipeline/ingest.py`, current helpers | Prior 8.2.x and 8.2.1/8.2.2 tests logged | Local closed |
| DB audit authority + JSONL outbox | `src/eidp/db/audit.py`, `src/eidp/db/audit_outbox.py`, `eidp audit-flush` | Prior 8.2 tests logged; audit page added in 8.4 | Local closed |
| Prefecture aggregator + safe CLI | `src/eidp/scraper/prefecture_aggregator.py`, `eidp prefecture-aggregate --apply` | Prior 8.3/8.3.1 tests logged | Local closed |
| Operator manual-entry contract | `src/eidp/pipeline/manual_entry.py` | Prior 8.4.a/a.1/a.2 tests logged | Local closed |
| Shared lock for UI / weekly | `src/eidp/db/locking.py`, `scripts/run_r8_rediscovery_weekly.py` | `tests/unit/test_r8_rediscovery_weekly.py`; VM still needed for actual `.bat` concurrency | Local closed, Windows open |
| Streamlit 12-page operator UI | `src/eidp/review/app.py`, `src/eidp/review/pages/` | Prior 8.4 UI import smoke logged; VM still needed for browser/manual operation | Local closed, Windows open |
| PDF preview / manual-entry UX | `src/eidp/review/pages/pdf_manual_entry.py` | Prior 8.4 gap fix logged | Local closed |
| Excel preview separate from weekly runner | `src/eidp/review/pages/excel_preview.py`, `scripts/run_r8_rediscovery_weekly.py`, `scripts/verify_windows_distribution.py` | Unit tests and ZIP verifier assert no weekly Excel generation; VM file-lock test remains | Local closed, Windows open |
| Confidence architecture | `src/eidp/extraction_confidence.py` | Prior 8.6.a tests logged | Local closed |
| Confidence gating in ingest | `src/eidp/pipeline/ingest.py` | Prior 8.6.b through 8.6.b.3 tests logged | Local closed |
| Tesseract wrapper + runtime detect | `src/eidp/ocr/tesseract.py`, `src/eidp/ocr/runtime_detect.py` | Prior 8.6.c tests logged; real Windows subprocess remains open | Local closed, Windows open |
| UI confidence breakdown / queue dashboard | `src/eidp/review/pages/` | Prior 8.6.d.1-d.4 tests logged | Local closed |
| Windows app-root and `.bat` contracts | `src/eidp/config.py`, `scripts/*.bat`, `scripts/verify_windows_distribution.py` | Static `.bat` tests and ZIP verifier check app-root anchors, UTF-8 env, exit-code preservation, offline install, locale-safe weekly log naming, and uninstall data protection; actual Windows execution open | Local closed, Windows open |
| Repo Windows path safety | `scripts/check_windows_paths.py` | Current worktree check passes; covers case-insensitive collisions and reserved names | Local closed |
| Windows wheelhouse platform / ABI guard | `scripts/build_windows_zip.py`, `requirements-windows.txt` | `tests/unit/test_windows_packaging_spike.py`; local smoke ZIP with `required_missing: []` | Local closed |
| Windows runtime pinning | `scripts/download_windows_runtime.py` | Prior 8.5.a.2.1 real download evidence logged; current checkout has no `runtime/` directory | Asset build open |
| Core Windows ZIP manifest | `scripts/build_windows_zip.py`, `scripts/verify_windows_distribution.py` | Local smoke ZIP verifies `OK core` with runtime stubs, `scripts/validate_install.bat`, project wheel, required paths, `.bat` contracts, validator flags, and weekly-runner contracts; verifier tests cover runtime/project-wheel/wheel-platform/path-safety/duplicate-entry/stale-bat/stale-entrypoint failures; production ZIP not built in this checkout | Shape closed, asset build open |
| OCR add-on ZIP manifest | `scripts/build_ocr_addon_zip.py`, `scripts/verify_windows_distribution.py` | Smoke ZIP recorded with `manifest_files: 3`; verifier tests cover manifest path, size, sha256, duplicate manifest paths, and unlisted payload failures | Shape closed, asset build open |
| Playwright add-on optional ZIP | `scripts/build_playwright_addon_zip.py`, `scripts/verify_windows_distribution.py` | Smoke ZIP recorded with `manifest_files: 2`; verifier tests cover missing Chrome and manifest integrity failures | Shape closed, asset build open |
| Existing 116 docs migration | `scripts/migrate_pg_to_sqlite.py` | Unit tests cover counts, revision chain, idempotency; real PG corpus migration not run here | Local closed, data-run open |
| Operator runbook | `docs/runbooks/eidp-windows.md` | File present; VM/real-PC findings must still be folded in | Draft closed, validation feedback open |
| Windows VM checklist | `docs/runbooks/eidp-windows-vm-validation.md` | File present with Stage 2-5c steps | Local closed |
| Venus archive | `deploy/legacy-venus/`, archived runbook notice | Legacy systemd files and cron wrapper are byte-identical to HEAD; cron files are archived with only self-reference paths rewritten to `deploy/legacy-venus/...`; Venus crontab removal remains owner manual action | Repo closed, host action open |
| Architecture / roadmap docs | `docs/architecture.md`, future plan docs, `README.md` | Files present | Local closed |
| Git commit / push | Git repository | Codex sandbox could not write `.git/`; the Claude Code session that performed the simplify pass confirmed `.git/` is writable from its environment. Local commit is therefore unblocked; remote `push origin main` still requires owner-level approval. Recovery patch under `/private/tmp` remains available as a fallback. | Local commit unblocked, push open |
| Windows VM offline validation | `docs/runbooks/eidp-windows-vm-validation.md`, `scripts/validate_install.bat`, `scripts/validate_windows_install.py` | Validator exists for post-setup/post-weekly file evidence and can be run from the extracted ZIP; actual VM run not executed in current environment | Open blocker |
| Real operator PC E2E | Operator PC + `docs/runbooks/eidp-operator-e2e-template.md` | Template exists; actual run not executed in current environment | Open blocker |

## Current Evidence Snapshot

Latest recorded local verification:

```text
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit -q
=> 593 passed, 5 warnings

git diff --check
=> clean
```

Latest artifact smoke evidence is recorded in
`docs/plans/2026-05-04-sprint8-win-deployment.md`:

- core ZIP smoke: `OK core`, `entry_count=81`, `wheel_count=2`;
- OCR add-on smoke: `OK ocr-addon`, `manifest_files: 3`;
- Playwright add-on smoke: `OK playwright-addon`, `manifest_files: 2`.

Recovery patch for the uncommitted local worktree:

```text
/private/tmp/eidp-sprint8-handoff-20260505.tar.gz
/private/tmp/eidp-sprint8-handoff-20260505.tar.gz.sha256

/private/tmp/eidp-sprint8-commits-20260505.bundle
bundle sha256: 20044d1b32aa41f3be69aa57a491e666b9eb31c57aea7b0e03a77f63e84995e5
bundle contains: e3becc4
bundle requires: ec2ec94

/private/tmp/eidp-sprint8-local-changes-20260505.patch
patch base: e3becc4
```

The handoff archive has a portable external `.sha256` sidecar, and the
unpacked archive's portable checksum sidecars have been validated. From the
unpacked archive only, the combined restore path has also been rehearsed in
`/private/tmp`: fetch base `ec2ec94`, fetch the bundle to
`sprint8-local-history`, switch to `e3becc4`, and apply the patch. The
rehearsal reproduced 16 tracked changes and 30 untracked Sprint 8 files.

Handoff instructions for a git-writable environment:

```text
docs/plans/2026-05-05-sprint8-handoff.md
```

## Open Gates

### Gate 1: Commit / Push

Original blocker (Codex sandbox):

```text
touch .git/codex-write-test
=> Operation not permitted
```

Updated 2026-05-05 by the Claude Code session that ran the simplify pass:

```text
touch .git/eidp-write-probe
=> success
ls .git/eidp-write-probe
=> exists, mode 644
rm .git/eidp-write-probe
=> success
```

So the original "cannot write `.git/`" reading was specific to the Codex
sandbox, not the repository. **Local commit is unblocked** from a normal
developer shell or the Claude Code session; the recovery patch under
`/private/tmp` continues to exist as a fallback.

Remote push to `origin/main` is still gated on explicit owner approval per
the Sprint 8 release-gate convention. The recommended path is:

1. create a feature branch (`sprint8-handoff-finalize`),
2. land 8.7 / 8.8 / 8.9 + simplify as separate commits on that branch,
3. owner reviews and decides when to merge into `main`.

Until step 3 owner-approves the merge, this gate remains "local commit
unblocked, push open".

### Gate 2: Production ZIP Asset Build

This checkout currently has no `runtime/` or `dist/` artifact directory.
Production asset build requires:

```text
uv run python scripts/download_windows_runtime.py
uv run python scripts/build_windows_zip.py
uv run python scripts/build_ocr_addon_zip.py --tesseract-dir <dir> --tessdata-dir <dir>
uv run python scripts/build_playwright_addon_zip.py --wheelhouse <dir> --browsers-dir <dir>
uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip \
  --ocr-addon dist/eidp-ocr-addon-windows.zip \
  --playwright-addon dist/eidp-playwright-addon-windows.zip \
  --json > dist/windows-distribution-verification.json
```

The verifier JSON records `sha256` and `size_bytes` for each ZIP and should be
stored next to the files on the internal file server.

The current sandbox has restricted network access, so runtime / dependency
downloads are not available here.

### Gate 3: Windows VM Offline Validation

Must pass `docs/runbooks/eidp-windows-vm-validation.md` Stage 2 through Stage
5c:

- offline `first_setup.bat`;
- `launch.bat`;
- manual `weekly_run.bat`;
- `scripts\validate_install.bat` after setup and weekly run;
- lock banner;
- `last_run.json`;
- Excel generation and file-lock error;
- OCR add-on execution;
- optional Playwright add-on detection;
- Defender / SmartScreen handling.

### Gate 4: Operator PC E2E

v1.0 requires one real operator PC R8 cycle with owner sign-off and KPI
capture. Record the result in:

```text
docs/runbooks/eidp-operator-e2e-template.md
```

Until this passes, the correct release status is beta.

## Decision

Local implementation may proceed to handoff and external validation, but the
Sprint 8 objective is not complete. Do not mark v1.0 or final delivery until
all open gates above are closed with real evidence.
