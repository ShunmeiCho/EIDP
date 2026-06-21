# v546 RCA-Summary Windows Canary

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v546.zip`
Package SHA256: `ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`
Package/source commit: `63016054f948b1f4f285c3c822197f76c25b4b7d`
Windows root: `C:\Users\cyo20\EIDP-v546-6301605-env0`

## Release Forecast

`NOT_READY`

## Finding Classification

| Priority | Finding | Evidence | Current action |
| --- | --- | --- | --- |
| P0 release blocker | FY2026/R8 strict Excel-ready yield remains below the v1 release line. | v546 bounded Windows canary strict/Excel-ready `12/50 (24.0%)`; `ship_gate_status=below_gate`. | Keep release blocked; continue RCA and owner decision work. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | v546 is a developer-run side-by-side canary, not owner sign-off. | Do not request `READY`. |
| P0 release blocker | `publication_lag` exception and OCR scope remain owner decisions. | v546 selected status includes `publication_lag=30`, `target_year_unverified=2`, and `image_pending=3`. | Keep `READY` blocked; RC path requires explicit approvals. |
| P1 release hardening | False-reject review RCA summary is now packaged and Windows-canary verified. | Source/package commit `6301605`; setup, bounded weekly canary, and Stage 6 evidence verification all completed. | Keep the hardening; it does not lower strict gates. |
| P2 storage hygiene | Superseded Windows packages and side-by-side directories were pruned. | Cleanup removed `7,836,187,780` bytes while retaining active v527, fallback v545, and current v546. | Continue external-SSD/local artifact pruning for future packages. |
| P3 roadmap/research | University production workflow, cloud, multiuser, and complex frontend remain outside v1. | No v546 evidence changes this boundary. | Leave in roadmap. |

## What Changed

v546 packages commit `6301605`, which adds the false-reject
`review-rca-summary` output for returned owner worksheets. The output helps
frame returned reviews as specific rule defects, incomplete returns, or
unsupported generic model-failure claims.

The change does not alter strict FY acceptance:

- no fiscal year is inferred from download time;
- old-year/R7 target forms remain rejected for FY2026/R8 success;
- non-target PDFs remain rejected;
- school mismatch remains review-only;
- low-confidence or unresolved rows still cannot enter Excel;
- Excel output still depends on the Excel-ready gate.

## Windows Setup Evidence

Windows package SHA check:

```text
SHA256 OK: ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd
```

Setup:

```text
$env:EIDP_REGISTER_WEEKLY_TASK = "0"
.\EIDP-setup.bat
```

Result:

- setup `rc=0`;
- `OK install: C:\Users\cyo20\EIDP-v546-6301605-env0`;
- `build_commit=63016054f948b1f4f285c3c822197f76c25b4b7d`;
- `school_count=2418`;
- `school_fiscal_year_status_count=2418`;
- `sqlite_integrity_check=ok`;
- `wheel_count=84`;
- Task Scheduler registration skipped as intended.

After-setup validation and recovery:

```text
.\scripts\validate_install.bat --after-setup --json
.\scripts\stage6_recovery_check.bat C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

Results:

- after-setup validator `ok=true`;
- recovery check `ok=true`;
- active task still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`;
- v546 was not promoted to the active weekly task.

## Windows Bounded Canary Evidence

Command:

```text
$env:EIDP_WEEKLY_LIMIT = "50"
$env:EIDP_WEEKLY_BATCH_SIZE = "50"
$env:EIDP_WEEKLY_RATE_LIMIT = "0.5"
$env:EIDP_WEEKLY_REQUEST_TIMEOUT = "8"
.\scripts\weekly_run.bat --json
.\scripts\validate_install.bat --after-setup --json
```

Summary path:

```text
C:\Users\cyo20\EIDP-v546-6301605-env0\data\output\target-year-discovery\20260621_042630-summary.json
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

v546 is Windows-canary safe, but the bounded strict/Excel-ready yield remains
unchanged from v545. The release blocker remains strict evidence-gate yield
under FY2026/R8 public availability and candidate quality, not Windows setup,
packaging, or a generic "algorithm/model failure" claim.

## Stage 6 Evidence

Windows:

```text
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Results:

- Windows Stage 6 bundle creation: `ok=true`;
- Windows Stage 6 verification: `ok=true`;
- bundle: `logs/win-v546-6301605-canary/stage6-evidence-20260621-043811.zip`;
- Windows verifier JSON: `logs/win-v546-6301605-canary/stage6-evidence-verify-20260621-133825.json`;
- Mac-side verifier JSON: `logs/win-v546-6301605-canary/stage6-evidence-verify-mac-20260621.json`.

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
errors=[]
warnings=[]
```

## Cleanup Evidence

Windows cleanup:

- report: `logs/win-v546-6301605-canary/win-v546-cleanup-20260621.json`;
- deleted v535/v536/v544 transfer ZIPs and sidecars;
- deleted v532/v533/v535/v536/v537/v538/v539/v544 side-by-side directories;
- deleted bytes: `7,836,187,780`;
- retained active v527, fallback v545, and current v546 directories;
- retained v545 and v546 transfer ZIPs in `C:\EIDP-staging`.

