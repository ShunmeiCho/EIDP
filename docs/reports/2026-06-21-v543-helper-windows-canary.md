# v543 Helper Package Windows Canary

Date: 2026-06-21 JST
Branch: `main`
Package: `dist/eidp-windows-v543.zip`
Package SHA256: `c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094`
Source commit: `6aa5735d164101cbe6ec85648bcb8b6f46168c63`
Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Action |
| --- | --- | --- |
| P0 release blocker | FY2026/R8 strict/Excel-ready yield remains below the v1 release line. | Keep release status `NOT_READY`; do not promote. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | Keep owner approval blocked. |
| P0 release blocker | `publication_lag` exception and OCR scope are not approved as release evidence. | Keep RC/GA path blocked. |
| P1 release hardening | v543 packages `scripts/build_false_reject_audit.py` beside `scripts/verify_stage6_return.py`. | Windows setup/canary verified the helper package. |
| P2 RCA wording | The below-gate blocker can be misread as a generic algorithm/model defect. | Keep blocker wording tied to strict evidence yield until false-reject audit proves otherwise. |

## Package Identity

Mac-side package gates are recorded in
`docs/reports/2026-06-21-v543-package-gates.md`.

```text
ZIP=dist/eidp-windows-v543.zip
SHA256=c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094
BUILD_INFO.git_commit=6aa5735d164101cbe6ec85648bcb8b6f46168c63
BUILD_INFO.git_branch=main
BUILD_INFO.git_dirty=false
wheel_count=84
```

The ZIP contains both:

```text
scripts/verify_stage6_return.py
scripts/build_false_reject_audit.py
```

## Windows Setup Evidence

Transfer to Windows was checksum verified at `C:\EIDP-staging`:

```text
SHA256 OK: c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094
```

Side-by-side root:

```text
C:\Users\cyo20\EIDP-v543-6aa5735-env0
```

Setup and install validation:

```text
setup_rc=0
EIDP_REGISTER_WEEKLY_TASK=0
validate_after_setup.ok=true
build_commit=6aa5735d164101cbe6ec85648bcb8b6f46168c63
build_dirty=false
school_count=2418
school_fiscal_year_status_count=2418
sqlite_integrity_check=ok
wheel_count=84
```

Active-task safety:

```text
stage6_recovery.ok=true
action_matches_expected=true
lock_probe.ok=true
lock_probe.held=false
active weekly task remains C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

## Bounded Weekly Canary

The v543 bounded Windows canary ran with `--limit 50`:

```text
weekly_rc=0
run_id=20260620_212327
last_run_status=success
current_fy=2026
school_type=専門学校
selection_mode=target_missing
target_missing_school_count=50
strict_target_pdf_auto_acquired_count=12
strict_target_pdf_auto_yield_pct=24.0
target_pdf_excel_ready_acquired_count=12
target_pdf_excel_ready_yield_pct=24.0
operator_reviewable_count=47
operator_reviewable_yield_pct=94.0
ship_gate_status=below_gate
```

Global after-weekly validator:

```text
validate_after_weekly.ok=true
sqlite_target_fy=2026
sqlite_target_fy_target_pdf_school_count=8
sqlite_target_fy_yield_pct=0.3
sqlite_target_fy_operator_reviewable_school_count=40
sqlite_target_fy_operator_reviewable_yield_pct=1.7
discovery_rca_batch_plan_item_count=20
discovery_rca_batch_plan_total_candidates=35
```

The release gate validator rejected the run, as expected:

```text
validate_after_weekly_require_ship_gate.ok=false
error=last_run.json ship_gate_status must be pass when --require-ship-gate is used
```

This is the correct result. The package runs, but below-gate output is still
blocked from release.

Discovery stats:

```text
crawled=59
found=50
downloaded=15
failed=1
skipped=717
prefiltered=569
candidate_school_mismatch=0
shared_origin_derived_fallback_skipped=0
target_fiscal_year_not_detected=6
fiscal_year_mismatch=206
classified_non_target=103
pre_filtered_non_target_hint=432
no_candidates_found=9
http_error_httpstatuserror=1
pdf_school_mismatch=2
```

## Strict-Yield Blocker Framing

The blocker is not currently proven to be a generic algorithm/model failure.
The confirmed blocker is:

```text
FY2026/R8 strict target-document to Excel-ready yield below gate.
```

The v543 canary found many candidates and then refused to count old-year,
non-target, unknown-year, and identity-mismatch candidates as FY2026/R8
Excel-ready evidence. That is the correct strict-gate behavior unless the
false-reject audit proves material over-rejection or fiscal-year extraction
mistakes.

Next RCA order:

1. `fiscal_year_mismatch=206`: true old-year/publication-lag target forms vs
   fiscal-year extraction mistakes.
2. `pre_filtered_non_target_hint=432` and `classified_non_target=103`: true
   non-target PDF noise vs target-form over-rejection.
3. `target_fiscal_year_not_detected=6`: target-form-like files without trusted
   FY2026/R8 evidence from official page, anchor, filename, or PDF body.
4. `no_candidates_found=9`, `http_error_httpstatuserror=1`, and
   `pdf_school_mismatch=2`: SiteEntry, fetch, and identity gaps.

If false rejects are high, fix the specific discovery, classifier, or
fiscal-year rule. If false rejects are low, the blocker is dominated by
publication lag, old-year documents, non-target PDF noise, and release-scope
decisions. In both cases the FY2026/R8 evidence gate stays strict.

## Evidence Files

Windows evidence copied back to the external-SSD-backed `logs` path:

```text
logs/win-v543-6aa5735-canary/stage6-evidence-20260620-213335.zip
logs/win-v543-6aa5735-canary/stage6-evidence-verify-20260621-063335.json
logs/win-v543-6aa5735-canary/stage6-evidence-verify-mac-20260621.json
logs/win-v543-6aa5735-canary/stage6-recovery-20260621-062226.json
logs/win-v543-6aa5735-canary/win-v543-6aa5735-validate-after-setup-20260621-061945.json
logs/win-v543-6aa5735-canary/win-v543-6aa5735-validate-after-weekly-20260621-062326.json
logs/win-v543-6aa5735-canary/win-v543-6aa5735-validate-after-weekly-require-ship-gate-20260621-062326.json
logs/win-v543-6aa5735-canary/20260620_212327-summary.json
logs/win-v543-6aa5735-canary/20260620_212327-discovery-rca-batch-plan.json
logs/win-v543-6aa5735-canary/run-20260621.log
logs/win-v543-6aa5735-canary/eidp.jsonl
logs/win-v543-6aa5735-canary/diagnostics-20260621-063332.txt
```

Stage 6 evidence verifier:

```text
Windows verifier ok=true
Mac-side verifier ok=true
entry_count=8
missing_required_labels=[]
unsafe_entries=[]
forbidden_entries=[]
present_labels=[
  build_info,
  diagnostics,
  discovery_evidence,
  discovery_rca,
  last_run,
  stage6_recovery,
  weekly_run_logs
]
```

Mac-side AppleDouble `._*` sidecars generated during copy-back were removed
from the evidence directory.

## Verdict

v543 is now the latest packaged bounded Windows canary. It closes the P1 package
helper gap for returned false-reject worksheet validation, but it does not
change the v1.0 release verdict.

Release Forecast: `NOT_READY`
