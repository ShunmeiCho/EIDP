# v545 Disclosure-Priority Windows Canary

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v545.zip`
Package SHA256: `ba4d36189d671ce59e01cf8f1bffeb0710d8d2b171376e4cbc0cb4e362f1b8d0`
Package/source commit: `f3eb1663c0333f296856a84f447ef2424ea77ddf`
Windows root: `C:\Users\cyo20\EIDP-v545-f3eb166-env0`

## Release Forecast

`NOT_READY`

## Finding Classification

| Priority | Finding | Evidence | Current action |
| --- | --- | --- | --- |
| P0 release blocker | FY2026/R8 strict Excel-ready yield remains below the v1 release line. | v545 bounded Windows canary strict/Excel-ready `12/50 (24.0%)`; `ship_gate_status=below_gate`. | Keep release blocked; continue RCA and owner decision work. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | v545 is a developer-run side-by-side canary, not owner sign-off. | Do not request READY. |
| P0 release blocker | `publication_lag` exception and OCR scope remain owner decisions. | v545 selected status includes `publication_lag=30`, `target_year_unverified=2`, `image_pending=3`. | Keep `READY` blocked; RC path requires explicit approvals. |
| P1 release hardening | Trusted disclosure `SchoolSite` rows are now prioritized over brand homepages in PDF discovery. | Source commit `f3eb166` and v545 Windows canary completed setup, weekly canary, and Stage 6 evidence verification. | Keep the hardening; it does not lower strict gates. |
| P2 documentation/demo drift | v544 remains the owner handoff lane; v545 is package/canary evidence only. | This report records v545 separately from the staged v544 owner docs. | Refresh current status docs; do not make a new owner handoff unless requested. |
| P3 roadmap/research | University production workflow, cloud, multiuser, and complex frontend remain outside v1. | No v545 evidence changes this boundary. | Leave in roadmap. |

## What Changed

v545 packages commit `f3eb166`, which changes `run_pdf_discovery` site ordering
so trusted `url_type="disclosure"` rows from high-confidence sources are crawled
before ordinary school homepages. This is meant to preserve the official
information-publication entry point when both a brand homepage and a disclosure
URL exist for the same school.

The change does not alter strict FY acceptance:

- no fiscal year is inferred from download time;
- old-year/R7 target forms remain rejected for FY2026/R8 success;
- non-target PDFs remain rejected;
- school mismatch remains review-only;
- low-confidence or unresolved rows still cannot enter Excel;
- Excel output still depends on the Excel-ready gate.

## Local Package Evidence

Commands:

```text
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v545.zip --latest-alias
shasum -a 256 dist/eidp-windows-v545.zip
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v545.zip --json > logs/eidp-windows-v545-distribution-verify-20260621.json
uv run python scripts/prune_release_artifacts.py --base /Volumes/M1nG-ssd/EIDP-artifacts --dist-dir /Volumes/M1nG-ssd/EIDP-artifacts/dist --keep-latest 2 --keep-version 544 --apply --json > logs/eidp-v545-local-prune-20260621.json
```

Results:

- package verifier: `ok=true`;
- `BUILD_INFO.git_commit=f3eb1663c0333f296856a84f447ef2424ea77ddf`;
- `BUILD_INFO.git_dirty=false`;
- `wheel_count=84`;
- `has_runtime=true`;
- local cleanup removed older v535/v536/v542/v543 ZIPs and sidecars;
- local cleanup deleted `843676935` bytes from external-SSD-backed `dist/`;
- external-SSD-backed `dist/` retained v544 fallback and v545 current package.

## Windows Setup Evidence

Windows package SHA check:

```text
SHA256 OK: ba4d36189d671ce59e01cf8f1bffeb0710d8d2b171376e4cbc0cb4e362f1b8d0
```

Setup:

```text
$env:EIDP_REGISTER_WEEKLY_TASK = "0"
.\EIDP-setup.bat
```

Result:

- setup `rc=0`;
- `OK install: C:\Users\cyo20\EIDP-v545-f3eb166-env0`;
- `build_commit=f3eb1663c0333f296856a84f447ef2424ea77ddf`;
- `school_count=2418`;
- `school_fiscal_year_status_count=2418`;
- `sqlite_integrity_check=ok`;
- `wheel_count=84`;
- Task Scheduler registration skipped as intended.

After-setup validation and recovery:

```text
.\scripts\validate_install.bat --after-setup --json > logs\win-v545-f3eb166-validate-after-setup-20260621.json
.\scripts\stage6_recovery_check.bat C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

Results:

- after-setup validator `ok=true`;
- recovery check `ok=true`;
- active task still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`;
- v545 was not promoted to the active weekly task.

## Windows Bounded Canary Evidence

Command:

```text
$env:EIDP_WEEKLY_LIMIT = "50"
$env:EIDP_WEEKLY_BATCH_SIZE = "50"
$env:EIDP_WEEKLY_RATE_LIMIT = "0.5"
$env:EIDP_WEEKLY_REQUEST_TIMEOUT = "8"
.\scripts\weekly_run.bat --json
.\scripts\validate_install.bat --after-setup --json > logs\win-v545-f3eb166-validate-after-weekly-canary-20260621.json
```

Summary path:

```text
C:\Users\cyo20\EIDP-v545-f3eb166-env0\data\output\target-year-discovery\20260621_003033-summary.json
```

Key result:

| Metric | Value |
| --- | --- |
| Selected schools | `50` |
| Crawled site rows | `59` |
| Candidate sets found | `50` |
| Downloaded documents | `15` |
| Processed documents | `15` |
| Department rows upserted | `129` |
| Strict target PDFs | `12/50 (24.0%)` |
| Excel-ready | `12/50 (24.0%)` |
| Operator-reviewable | `47/50 (94.0%)` |
| Ship gate | `below_gate` |

Selected school status:

```text
confirmed_target=12
confirmed_target_parsed=12
confirmed_target_excel_ready=12
publication_lag=30
target_year_unverified=2
image_pending=3
stale_or_old=30
review_or_parse=5
excel_ready=12
```

Discovery rejection counters:

```text
pre_filtered_non_target_hint=432
fiscal_year_mismatch=206
classified_non_target=103
target_fiscal_year_not_detected=6
no_candidates_found=9
http_error_httpstatuserror=1
pdf_school_mismatch=2
```

Interpretation:

The disclosure-priority hardening is Windows-safe, but it did not move the
bounded strict/Excel-ready yield above v544. The release blocker remains the
strict evidence gate under FY2026/R8 public availability and candidate quality,
not Windows setup, packaging, or a generic "algorithm/model failure" claim.

## Stage 6 Evidence

Windows:

```text
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Results:

- Windows Stage 6 bundle creation: `ok=true`;
- Windows Stage 6 verification: `ok=true`;
- bundle: `logs/win-v545-f3eb166-canary/stage6-evidence-20260621-004156.zip`;
- Windows verifier JSON: `logs/win-v545-f3eb166-canary/stage6-evidence-verify-20260621-094157.json`;
- Mac-side verifier JSON: `logs/win-v545-f3eb166-canary/stage6-evidence-verify-mac-20260621.json`.

Mac-side verifier result:

```text
ok=true
present_labels=[
  build_info,
  diagnostics,
  discovery_evidence,
  discovery_rca,
  last_run,
  stage6_recovery,
  weekly_run_logs
]
required_labels=[build_info, diagnostics, last_run]
errors=[]
warnings=[]
```

## Cleanup Evidence

Local external-SSD cleanup:

- report: `logs/eidp-v545-local-prune-20260621.json`;
- deleted v535/v536/v542/v543 package ZIPs and sidecars;
- deleted bytes: `843676935`;
- retained v544 fallback and v545 current package.

Windows cleanup:

- report: `logs/win-v545-f3eb166-canary/win-v545-cleanup-20260621.json`;
- deleted `C:\EIDP-staging\eidp-windows-v542.zip`;
- deleted `C:\EIDP-staging\eidp-windows-v542.zip.sha256`;
- deleted `C:\EIDP-staging\eidp-windows-v543.zip`;
- deleted `C:\EIDP-staging\eidp-windows-v543.zip.sha256`;
- deleted `C:\Users\cyo20\EIDP-v540-fbdd0bd-env0`;
- deleted `C:\Users\cyo20\EIDP-v541-e62d074-env0`;
- deleted `C:\Users\cyo20\EIDP-v542-d98ecd7-env0`;
- deleted `C:\Users\cyo20\EIDP-v543-6aa5735-env0`;
- Windows deleted bytes: `4015573603`;
- retained active v527, fallback v544, and current v545.

Post-cleanup Windows staging contains only:

```text
C:\EIDP-staging\eidp-windows-v544.zip
C:\EIDP-staging\eidp-windows-v544.zip.sha256
C:\EIDP-staging\eidp-windows-v545.zip
C:\EIDP-staging\eidp-windows-v545.zip.sha256
```

Post-cleanup Windows side-by-side v54x directories contain only:

```text
C:\Users\cyo20\EIDP-v544-74325bc-env0
C:\Users\cyo20\EIDP-v545-f3eb166-env0
```

## Remaining Risk

- P0: strict/Excel-ready FY2026/R8 yield is still `24.0%`, below the `60.0%`
  ship line.
- P0: owner real Windows cycle and sign-off remain missing.
- P0: publication-lag exception is not approved.
- P0: OCR scope decision is not approved.
- P1: next RCA should focus on `publication_lag=30`, `fiscal_year_mismatch=206`,
  and the remaining `no_candidates_found=9` rows, using the v545 evidence bundle.

Release conclusion remains `NOT_READY`.
