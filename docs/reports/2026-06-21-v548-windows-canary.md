# v548 Windows Canary

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v548.zip`
Package SHA256: `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`
Package/source commit: `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`
Windows root: `C:\Users\cyo20\EIDP-v548-c1a9690-env0`

## Release Forecast

`NOT_READY`

## Finding Classification

| Priority | Finding | Evidence | Current action |
| --- | --- | --- | --- |
| P0 release blocker | FY2026/R8 strict Excel-ready yield remains below the v1 release line. | v548 bounded Windows canary strict/Excel-ready `12/50 (24.0%)`; `ship_gate_status=below_gate`. | Keep release blocked; continue worksheet-driven RCA and owner decision work. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | v548 is a developer-run side-by-side canary, not owner sign-off. | Do not request `READY`. |
| P0 release blocker | `publication_lag` exception and OCR scope remain owner decisions. | v548 selected status includes `publication_lag=30`, `target_year_unverified=2`, and `image_pending=3`. | Keep `READY` blocked; RC path requires explicit approvals. |
| P1 release hardening | Audit-packet summary hardening is now packaged and Windows-canary verified. | v548 packages commit `c1a9690`; setup, bounded weekly canary, and Stage 6 evidence verification all completed. | Keep the hardening; it does not lower strict gates. |
| P1 release hardening | Latest package/setup proof and latest bounded Windows canary are now aligned on v548. | v548 package gates, Windows setup proof, weekly canary, after-weekly validator, and Stage 6 verification all returned `ok=true` / `rc=0`. | Treat v547 as fallback/historical canary evidence. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v548 evidence changes this boundary. | Leave in roadmap. |

## What Changed

v548 packages commit `c1a9690`, which hardens the owner-return
`false_reject_review_summary` audit-packet validity surface. It exposes compact
completed/blank decision counts, context mismatch count, defect framing,
`owner_return_gate_ok`, audit-packet validity, and blocking packet/CSV/audit-log
error previews in `scripts/verify_stage6_return.py` output.

The change does not alter strict FY acceptance:

- no fiscal year is inferred from download time;
- old-year/R7 target forms remain rejected for FY2026/R8 success;
- non-target PDFs remain rejected;
- school mismatch remains review-only;
- low-confidence or unresolved rows still cannot enter Excel;
- Excel output still depends on the Excel-ready gate.

## Windows Setup Evidence

The v548 side-by-side setup proof was already recorded in
`docs/reports/2026-06-21-v548-package-setup-gates.md`.

Key setup result:

- setup `rc=0`;
- after-setup validator `ok=true`;
- `build_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`;
- `school_count=2418`;
- `school_fiscal_year_status_count=2418`;
- `sqlite_integrity_check=ok`;
- `wheel_count=84`;
- active task restored to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`.

## Windows Bounded Canary Evidence

Command:

```text
$env:EIDP_REGISTER_WEEKLY_TASK = "0"
$env:EIDP_WEEKLY_LIMIT = "50"
$env:EIDP_WEEKLY_BATCH_SIZE = "50"
$env:EIDP_WEEKLY_RATE_LIMIT = "0.5"
$env:EIDP_WEEKLY_REQUEST_TIMEOUT = "8"
.\scripts\weekly_run.bat --json
.\scripts\validate_install.bat --after-setup --json
```

Summary path:

```text
C:\Users\cyo20\EIDP-v548-c1a9690-env0\data\output\target-year-discovery\20260621_105136-summary.json
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

After-weekly validator:

- Windows output: `logs/win-v548-c1a9690-canary/v548-validate-after-weekly-20260621-200251.json`;
- `ok=true`;
- `errors=[]`;
- `warnings=[]`;
- `school_count=2418`;
- `school_fiscal_year_status_count=2418`;
- `sqlite_integrity_check=ok`;
- `build_commit=c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`;
- `build_dirty=false`;
- `wheel_count=84`.

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
plus Excel-ready. The system ran and found candidates; the release blocker is
that only `12` schools had evidence strong enough to enter Excel-ready safely.

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

v548 is Windows-canary safe, but the bounded strict/Excel-ready yield remains
unchanged from v547. The release blocker remains strict evidence-gate yield
under FY2026/R8 public availability and candidate quality, plus owner decision
work. It is not Windows setup, packaging, or a generic algorithm/model failure
claim.

The next decision path still depends on the false-reject worksheet. If
owner/operator review finds many `false_reject` rows, fix the specific
discovery/filter rule and add regression tests. If most rows are
`correct_reject`, treat the low strict yield as publication-lag / old-year /
non-target noise and use only an explicit `RC_ONLY` publication-lag exception
if approved. If many rows remain `needs_operator_review`, strengthen the
review queue and evidence display instead of relaxing Excel-ready gates.

## Stage 6 Evidence

Windows:

```text
.\scripts\collect_stage6_evidence.bat
.\scripts\verify_stage6_evidence.bat
```

Results:

- Windows Stage 6 bundle creation: `ok=true`;
- Windows Stage 6 verification: `ok=true`;
- bundle: `logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip`;
- Windows verifier JSON: `logs/win-v548-c1a9690-canary/stage6-evidence-verify-20260621-200255.json`;
- Mac-side verifier JSON: `logs/win-v548-c1a9690-canary/stage6-evidence-verify-mac-20260621.json`.

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

## Release Boundary

v548 is now both the latest package/setup proof and the latest bounded Windows
weekly canary. It is still `NOT_READY`: the strict/Excel-ready canary yield is
`12/50 (24.0%)`, owner/operator worksheet decisions are still missing, the
`publication_lag` decision is still unsigned, OCR scope is still not approved,
and no owner real Windows cycle/sign-off has been returned.
