# v542 False-Reject Verifier Windows Canary

Date: 2026-06-21 JST
Branch: `main`
Package: `dist/eidp-windows-v542.zip`
Package SHA256: `89ace547fcabf43f80b697024f5c13d1398244ad4d4b165160a489c8386f9ecc`
Source commit: `d98ecd7196631a00c27aff1c240ebc7969579ce7`
Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Action |
| --- | --- | --- |
| P0 release blocker | FY2026/R8 strict/Excel-ready yield remains below the v1 release line. | Keep release status `NOT_READY`; do not promote. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | Keep owner approval blocked. |
| P0 release blocker | `publication_lag` exception and OCR scope are not approved as release evidence. | Keep RC/GA path blocked. |
| P1 release hardening | The post-v541 false-reject worksheet return verifier was source-side only on `main`. | Rebuilt and Windows-canary verified as v542. |
| P2 handoff drift | Owner handoff docs remain v541 r3. | Refresh to v542 only if this package becomes the next owner handoff lane. |

## Build

Command:

```text
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-v542.zip --latest-alias --skip-download
```

Result:

```text
OK: wrote dist/eidp-windows-v542.zip (201.2 MB)
OK: wrote checksum sidecar dist/eidp-windows-v542.zip.sha256
OK: refreshed latest alias dist/eidp-windows.zip
```

Package checksum:

```text
dist/eidp-windows-v542.zip: OK
89ace547fcabf43f80b697024f5c13d1398244ad4d4b165160a489c8386f9ecc
```

## Non-Windows Gates

Command:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v542.zip \
  --json \
  --output logs/win-v542-false-reject-verifier-release-gates-20260621.json
```

Result highlights:

```text
ok=true
package_commit=d98ecd7196631a00c27aff1c240ebc7969579ce7
source_commit=d98ecd7196631a00c27aff1c240ebc7969579ce7
source_dirty=false
stale=false
unit_full=2049 passed, 5 warnings
validator_distribution_unit=196 passed
validator_distribution_mypy=0
validator_distribution_ruff=0
package_verify=0
package_verify_demonstrated_patterns=0
```

Package verifier highlights:

```text
BUILD_INFO.git_commit=d98ecd7196631a00c27aff1c240ebc7969579ce7
BUILD_INFO.git_dirty=false
entry_count=3117
has_runtime=true
wheel_count=84
mext_target_total_rows=3132
mext_target_specialty_rows=2067
mext_target_university_rows=769
prefecture_seed_rows=47
prefecture_seed_school_rows_total=2148
discovery_gold_expected_predictions=45
discovery_gold_undemonstrated_pattern_sources=[]
```

GitHub `main` CI was also green before this package rebuild:

```text
CI run 27880148454: completed success for d98ecd7
CI run 27879818860: completed success for b044d02
```

## Windows Evidence

Transfer and checksum:

```text
scp dist/eidp-windows-v542.zip dist/eidp-windows-v542.zip.sha256 win:C:/EIDP-staging/
Get-FileHash -Algorithm SHA256 C:\EIDP-staging\eidp-windows-v542.zip
```

Windows SHA256 matched:

```text
89ace547fcabf43f80b697024f5c13d1398244ad4d4b165160a489c8386f9ecc
```

Side-by-side root:

```text
C:\Users\cyo20\EIDP-v542-d98ecd7-env0
```

Setup and active-task safety:

```text
setup.exit_code=0
EIDP_REGISTER_WEEKLY_TASK=0
validate_after_setup.exit_code=0
recovery.exit_code=0
weekly_task_action_unchanged=true
active weekly task remains C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
sqlite_integrity_check=ok
school_count=2418
school_fiscal_year_status_count=2418
```

Bounded weekly canary:

```text
weekly.exit_code=0
run_id=20260620_185933
last_run.status=success
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
validate_after_weekly.exit_code=0
last_run_status=success
sqlite_target_fy=2026
sqlite_target_fy_target_pdf_school_count=8
sqlite_target_fy_yield_pct=0.3
sqlite_target_fy_operator_reviewable_school_count=40
sqlite_target_fy_operator_reviewable_yield_pct=1.7
discovery_rca_batch_plan_item_count=20
discovery_rca_batch_plan_total_candidates=35
```

Release gate validator:

```text
validate_after_weekly_require_ship_gate.exit_code=1
error: last_run.json ship_gate_status must be pass when --require-ship-gate is used
```

This failure is expected and correct. It proves the validator still rejects
below-gate canary output.

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
rejection_reason_target_fiscal_year_not_detected=6
rejection_reason_fiscal_year_mismatch=206
rejection_reason_classified_non_target=103
rejection_reason_pre_filtered_non_target_hint=432
rejection_reason_no_candidates_found=9
rejection_reason_http_error_httpstatuserror=1
rejection_reason_pdf_school_mismatch=2
```

## Strict-Yield Blocker RCA Framing

The current blocker is not simply "the algorithm/model is broken". The v542
canary found many candidates, then correctly refused to count old-year,
non-target, unknown-year, and identity-mismatch candidates as FY2026/R8
Excel-ready evidence.

The release blocker remains:

```text
FY2026/R8 strict target-document to Excel-ready yield below gate
```

The next RCA pass must separate false rejects from correct rejects by bucket:

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
decisions. None of these buckets permits relaxing the FY2026/R8 evidence gate.

## Evidence Files

Windows-side evidence:

```text
archive=C:\Users\cyo20\EIDP-v542-d98ecd7-env0\logs\stage6-evidence-20260620-190958.zip
verify_json=C:\Users\cyo20\EIDP-v542-d98ecd7-env0\logs\stage6-evidence-verify-20260621-040959.json
verify.ok=true
verify.errors=[]
verify.warnings=[]
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

Mac-side evidence retrieval:

```text
logs/win-v542-d98ecd7-canary/stage6-evidence-20260620-190958.zip
logs/win-v542-d98ecd7-canary/stage6-evidence-verify-20260621-040959.json
logs/win-v542-d98ecd7-canary/stage6-recovery-20260621-035740.json
logs/win-v542-d98ecd7-canary/20260620_185933-summary.json
logs/win-v542-d98ecd7-canary/20260620_185933-discovery-rca-batch-plan.json
logs/win-v542-d98ecd7-canary/last_run.json
logs/win-v542-d98ecd7-canary/run-20260621.log
logs/win-v542-d98ecd7-canary/diagnostics-20260621-040954.txt
```

Mac-side evidence verifier:

```text
uv run python scripts/verify_stage6_evidence.py \
  logs/win-v542-d98ecd7-canary/stage6-evidence-20260620-190958.zip \
  --json
```

Result:

```text
ok=true
errors=[]
warnings=[]
present_labels=[build_info, diagnostics, discovery_evidence, discovery_rca, last_run, stage6_recovery, weekly_run_logs]
```

## Cleanup

After v542 verification, superseded core ZIPs were pruned to control storage
growth.

Mac external-SSD-backed `dist/` cleanup:

```text
deleted dist/eidp-windows-v540.zip
deleted dist/eidp-windows-v540.zip.sha256
deleted dist/eidp-windows-v541.zip
deleted dist/eidp-windows-v541.zip.sha256
retained core ZIPs: v535, v536, v542, latest alias
```

Windows staging cleanup:

```text
deleted v527, v532, v533, v537, v538, v540, v541 core ZIPs and sidecars
removed temporary v542 setup/canary/logtail scripts
remaining core ZIPs: v535, v536, v542
```

Storage check after cleanup:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist  1.1G
/Volumes/M1nG-ssd/EIDP-artifacts/logs  1.3G
/System/Volumes/Data                   91Gi available, 79% used
/Volumes/M1nG-ssd                      1.8Ti available, 1% used
```

## Conclusion

v542 closes the P1 source/package gap for the false-reject owner-return
verifier integration on current `main`. It does not change the v1 release
verdict. The bounded Windows canary remains strict/Excel-ready
`12/50 (24.0%)`, and the owner real cycle/sign-off is still missing.

Next required actions:

1. Use v542 as the current packaged verification head for false-reject return
   verifier claims.
2. Continue the strict-yield RCA with the rejection-bucket false-reject audit.
3. Keep final release status `NOT_READY` until the strict Excel-ready gate and
   owner evidence are both satisfied.
