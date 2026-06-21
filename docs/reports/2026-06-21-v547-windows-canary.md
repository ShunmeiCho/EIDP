# v547 Windows Canary

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v547.zip`
Package SHA256: `f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`
Package/source commit: `86c848f68e1dbde85c9b6422cfc827149940e02a`
Windows root: `C:\Users\cyo20\EIDP-v547-86c848f-env0`

## Release Forecast

`NOT_READY`

## Finding Classification

| Priority | Finding | Evidence | Current action |
| --- | --- | --- | --- |
| P0 release blocker | FY2026/R8 strict Excel-ready yield remains below the v1 release line. | v547 bounded Windows canary strict/Excel-ready `12/50 (24.0%)`; `ship_gate_status=below_gate`. | Keep release blocked; continue owner decision and strict-yield RCA work. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | v547 is a developer-run side-by-side canary, not owner sign-off. | Do not request `READY`. |
| P0 release blocker | `publication_lag` exception and OCR scope remain owner decisions. | v547 selected status includes `publication_lag=30`, `target_year_unverified=2`, and `image_pending=3`. | Keep `READY` blocked; RC path requires explicit approvals. |
| P1 release hardening | False-reject worksheet guidance is now packaged and Windows-canary verified. | v547 packages commit `86c848f`; setup, bounded weekly canary, and Stage 6 evidence verification all completed. | Keep the hardening; it does not lower strict gates. |
| P2 storage hygiene | Superseded Windows transfer/package artifacts and the v545 side-by-side directory were pruned. | Cleanup removed `210,931,692` bytes of v545 transfer ZIPs and `898,464,669` bytes from the v545 side-by-side directory while retaining active v527, fallback v546, and current v547. | Continue external-SSD/local artifact pruning for future packages. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v547 evidence changes this boundary. | Leave in roadmap. |

## What Changed

v547 packages commit `86c848f`, which routes non-obvious
`pre_filtered_non_target_hint` and `classified_non_target` rows to
`needs_operator_review` in the false-reject worksheet guidance instead of
leaving `suggested_decision` blank.

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
SHA256 OK: f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b
```

Setup:

```text
$env:EIDP_REGISTER_WEEKLY_TASK = "0"
.\scripts\first_setup.bat
```

Result:

- setup `rc=0`;
- `OK install: C:\Users\cyo20\EIDP-v547-86c848f-env0`;
- `build_commit=86c848f68e1dbde85c9b6422cfc827149940e02a`;
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
- v547 was not promoted to the active weekly task.

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
C:\Users\cyo20\EIDP-v547-86c848f-env0\data\output\target-year-discovery\20260621_053425-summary.json
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

## 24% Metric Boundary

The `24.0%` value is not a PDF download/acquisition success rate and is not the
overall project completion rate. It is the bounded canary strict
target-document plus Excel-ready rate:

```text
target_pdf_excel_ready_acquired_count / selected target-missing schools
= 12 / 50
= 24.0%
```

The denominator is the `50` selected target-missing specialty schools in this
bounded Windows canary, not all `2,418` specialty schools. The same run found
candidate sets for `50/50` selected schools, downloaded `15` documents,
processed `15` documents, and accepted only `12` schools as strict target PDF
plus Excel-ready. In other words, the system ran and found candidate sets; the
release blocker is that only `12` schools had evidence strong enough to enter
Excel-ready safely.

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

v547 is Windows-canary safe, but the bounded strict/Excel-ready yield remains
unchanged from v546. The release blocker remains strict evidence-gate yield
under FY2026/R8 public availability and candidate quality, plus owner decision
work. It is not Windows setup, packaging, or a generic "algorithm/model
failure" claim.

The next decision path depends on the false-reject worksheet. If owner/operator
review finds many `false_reject` rows, fix the specific discovery/filter rule
and add regression tests. If most rows are `correct_reject`, treat the low
strict yield as publication-lag / old-year / non-target noise and use only an
explicit `RC_ONLY` publication-lag exception if approved. If many rows remain
`needs_operator_review`, strengthen the review queue and evidence display
instead of relaxing Excel-ready gates.

## False-Reject Review Evidence

The v547 worksheet was regenerated from the v547 Stage 6 evidence:

- summary: `docs/reports/2026-06-21-v547-false-reject-review-summary.md`;
- worksheet: `docs/reports/2026-06-21-v547-false-reject-review-sheet.csv`;
- validation JSON: `docs/reports/2026-06-21-v547-false-reject-review-validation.json`;
- validation summary: `docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md`.

Validation result:

- worksheet rows: `53`;
- `suggested_decision` blanks: `0`;
- suggested `correct_reject`: `20`;
- suggested `needs_operator_review`: `33`;
- submitted owner/operator decisions: `0/53`;
- `--require-decisions` fails as expected because every `decision` is blank.

This evidence is read-only guidance. It does not approve rejected rows and does
not allow any unconfirmed row into Excel.

## Stage 6 Evidence

Windows:

```text
.\scripts\collect_stage6_evidence.bat
.\scripts\verify_stage6_evidence.bat
```

Results:

- Windows Stage 6 bundle creation: `ok=true`;
- Windows Stage 6 verification: `ok=true`;
- bundle: `logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`;
- Windows verifier JSON: `logs/win-v547-86c848f-canary/stage6-evidence-verify-20260621-144556.json`;
- Mac-side verifier JSON: `logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json`.

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

- transfer ZIP cleanup report: `logs/win-v547-86c848f-canary/win-v547-cleanup-20260621.json`;
- explicit v545 side-by-side cleanup report: `logs/win-v547-86c848f-canary/win-v547-explicit-dir-cleanup-20260621.json`;
- deleted v545 transfer ZIP and sidecar: `210,931,692` bytes;
- deleted v545 side-by-side directory: `898,464,669` bytes;
- retained active v527, fallback v546, and current v547 directories;
- retained v546 and v547 transfer ZIPs in `C:\EIDP-staging`.
