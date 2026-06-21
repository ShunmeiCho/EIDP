# v548 Audit-Packet Summary Package and Windows Setup Gates

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v548.zip`
Package SHA256: `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`
Source commit: `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`

Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Evidence | Action |
| --- | --- | --- | --- |
| P0 release blocker | v548 is not a release-ready package by itself. | v548 has package gates and Windows setup proof, but no bounded weekly canary, no owner real-cycle sign-off, no OCR scope approval, and no publication-lag decision. | Keep release blocked. |
| P0 release blocker | FY2026/R8 strict Excel-ready yield remains below the v1 line. | Latest bounded Windows canary is still v547 at `12/50 (24.0%)`; v548 did not rerun the weekly canary. | Continue worksheet-driven RCA and owner decision work. |
| P1 release hardening | The `false_reject_review_summary` audit-packet gate is now packaged and setup-verified on Windows. | v548 packages `c1a9690`; package verifier, non-Windows release gates, Windows SHA, clean setup, after-setup validator, and active-task recovery check passed. | Use v548 for future owner-return verifier/package evidence; do not lower strict gates. |
| P1 release hardening | Side-by-side setup command hygiene matters. | An early setup attempt used an unsafe `cmd` env assignment and the active weekly task briefly pointed at v548; it was restored to v527 and recovery check returned `ok=true`. | Use PowerShell `$env:EIDP_REGISTER_WEEKLY_TASK="0"` or `cmd` `set "EIDP_REGISTER_WEEKLY_TASK=0"` for side-by-side setup. |
| P2 storage hygiene | Superseded v546 artifacts were pruned after v548 proof. | Local prune removed `210,934,325` bytes; Windows cleanup removed v546 transfer ZIPs and side-by-side directory, retaining active v527, fallback v547, and current v548. | Continue retaining one fallback plus current package. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v548 evidence changes the v1 scope boundary. | Leave in roadmap. |

## Package Evidence

Commands:

```text
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v548.zip --latest-alias
shasum -a 256 dist/eidp-windows-v548.zip
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v548.zip --json > logs/eidp-windows-v548-distribution-verify-20260621.json
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v548.zip --json --require-demonstrated-discovery-patterns > logs/eidp-windows-v548-distribution-verify-patterns-20260621.json
```

Results:

- package verifier: `ok=true`;
- `BUILD_INFO.git_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`;
- `BUILD_INFO.git_dirty=false`;
- package SHA `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`;
- `has_runtime=true`;
- `wheel_count=84`;
- `entry_count=3118`;
- discovery gold entries `45`;
- discovery gold expected predictions `45`;
- no undemonstrated discovery pattern sources.

## Non-Windows Release Gates

Command:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v548.zip \
  --output logs/eidp-windows-v548-release-gates-20260621.json
```

Result: `ok=true`.

Key gate results:

- SHA sidecar check: `ok=true`;
- package/source check: `package_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`, `source_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`, `source_dirty=false`, `stale=false`;
- full unit suite: `2059 passed`;
- validator/distribution unit slice: `196 passed`;
- validator/distribution mypy: success;
- validator/distribution Ruff: success;
- discovery gold expected prediction replay: `45` exact matches, `0` failed predictions;
- package verifier: `returncode=0`;
- package verifier with demonstrated patterns required: `returncode=0`.

## Windows Setup Evidence

Windows transfer and SHA check:

```text
scp dist/eidp-windows-v548.zip dist/eidp-windows-v548.zip.sha256 win:C:/EIDP-staging/
```

Result:

- transferred ZIP: `C:\EIDP-staging\eidp-windows-v548.zip`;
- transferred sidecar: `C:\EIDP-staging\eidp-windows-v548.zip.sha256`;
- Windows SHA match: `true`;
- Windows SHA: `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`.

Clean side-by-side setup root:

```text
C:\Users\cyo20\EIDP-v548-c1a9690-env0
```

Clean setup:

```text
set "EIDP_REGISTER_WEEKLY_TASK=0"
scripts\first_setup.bat
scripts\validate_install.bat --after-setup --json
```

Results:

- clean setup `rc=0`;
- after-setup validator `ok=true`;
- `build_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`;
- `build_dirty=false`;
- `school_count=2418`;
- `school_fiscal_year_status_count=2418`;
- `sqlite_integrity_check=ok`;
- `wheel_count=84`.

Evidence:

- `logs/win-v548-c1a9690-validate-after-setup-20260621.json`;
- Windows staging log: `C:\EIDP-staging\v548-first-setup-clean-20260621.log`.

## Active-Task Safety

During one early setup attempt, the command used an unsafe `cmd` assignment:

```text
set EIDP_REGISTER_WEEKLY_TASK=0 && scripts\first_setup.bat
```

In `cmd`, this can leave a trailing space in the variable value and fail the
`EIDP_REGISTER_WEEKLY_TASK=0` comparison. The active `EIDP Weekly Run` task was
therefore observed pointing at the v548 side-by-side root. It was immediately
restored with `Set-ScheduledTask` to the production v527 weekly action:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

Final recovery check:

- `scripts\stage6_recovery_check.bat C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`
- result `ok=true`;
- `action_matches_expected=true`;
- residual OCR smoke paths absent;
- evidence copied to `logs/win-v548-c1a9690-stage6-recovery-20260621.out.txt`.

## Cleanup Evidence

Local cleanup:

```text
uv run python scripts/prune_release_artifacts.py \
  --dist-dir dist \
  --keep-latest 2 \
  --apply \
  --json > logs/eidp-v548-local-prune-20260621.json
dot_clean -m dist
```

Result:

- `ok=true`;
- removed local `dist/eidp-windows-v546.zip` and sidecar;
- `deleted_count=2`;
- `deleted_bytes=210934325`;
- external-SSD-backed `dist/` now retains v547 fallback, v548 current package, and latest alias;
- AppleDouble `._*` files are absent from `dist/` after cleanup.

Windows cleanup:

- removed `C:\EIDP-staging\eidp-windows-v546.zip`;
- removed `C:\EIDP-staging\eidp-windows-v546.zip.sha256`;
- removed `C:\Users\cyo20\EIDP-v546-6301605-env0`;
- deleted bytes: `1,109,412,996`;
- retained active v527, fallback v547, current v548;
- evidence copied to `logs/win-v548-cleanup-20260621.json`.

## Release Boundary

v548 is package/setup proof for the current `main` audit-packet summary
hardening. It is not the latest bounded Windows weekly canary. The latest
bounded Windows canary remains v547, with strict/Excel-ready `12/50 (24.0%)`.

v548 remains `NOT_READY` until at least:

1. a v548 bounded weekly canary is run, if v548 becomes the candidate for
   strict-yield evidence;
2. the strict/Excel-ready line is resolved or the owner approves an explicit
   `publication_lag` RC-only exception;
3. the false-reject worksheet is returned and validated with audit log evidence;
4. OCR scope and owner real-cycle sign-off are complete;
5. `scripts/verify_stage6_return.py` passes against the returned owner evidence.
