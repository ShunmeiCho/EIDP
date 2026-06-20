# v541 Owner Sign-off Verifier Windows Canary

Date: 2026-06-21 JST
Branch: `main`
Package: `dist/eidp-windows-v541.zip`
Package SHA256: `2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f`
Source commit: `e62d074081e60428957a2f405c3a917bbceb31a0`
Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Action |
| --- | --- | --- |
| P0 release blocker | FY2026 strict/Excel-ready yield remains below the v1 release line. | Keep release status `NOT_READY`; do not promote. |
| P0 release blocker | Owner real Windows cycle and release sign-off are still missing. | Keep owner approval blocked. |
| P0 release blocker | `publication_lag` exception and OCR scope are not approved as release evidence. | Keep RC/GA path blocked. |
| P1 release hardening | Current `main` owner-return verifier hardening was not packaged in v540. | Rebuilt and Windows-canary verified as v541. |
| P2 documentation drift | Owner handoff docs are still v540 r2 while the latest package/canary is v541. | Refresh v541 owner handoff before any owner real cycle. |

## Build

Command:

```text
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-v541.zip --latest-alias --skip-download
```

Result:

```text
OK: wrote dist/eidp-windows-v541.zip (201.2 MB)
OK: wrote checksum sidecar dist/eidp-windows-v541.zip.sha256
OK: refreshed latest alias /Users/shunmei/workspace/EIDP/dist/eidp-windows.zip
```

Package checksum:

```text
dist/eidp-windows-v541.zip: OK
2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f
```

## Non-Windows Gates

Command:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v541.zip \
  --json \
  --output logs/win-v541-owner-signoff-release-path-gates-20260621.json
```

Result highlights:

```text
ok=true
package_commit=e62d074081e60428957a2f405c3a917bbceb31a0
source_commit=e62d074081e60428957a2f405c3a917bbceb31a0
source_dirty=false
unit_full=2043 passed
validator_distribution_unit=196 passed
package_verify=0
package_verify_demonstrated_patterns=0
```

Package verifier highlights:

```text
BUILD_INFO.git_commit=e62d074081e60428957a2f405c3a917bbceb31a0
BUILD_INFO.git_dirty=false
entry_count=3117
has_runtime=true
wheel_count=84
mext_target_total_rows=3132
mext_target_specialty_rows=2067
discovery_gold_expected_predictions=45
discovery_gold_undemonstrated_pattern_sources=[]
```

## Windows Evidence

Transfer and checksum:

```text
scp dist/eidp-windows-v541.zip dist/eidp-windows-v541.zip.sha256 win:C:/EIDP-staging/
Get-FileHash -Algorithm SHA256 C:\EIDP-staging\eidp-windows-v541.zip
```

Windows SHA256 matched:

```text
2FFB25884E15B9E2937F43BAB7A8F5866D9434BC9F29F8067DBC1760397FA46F
```

Side-by-side root:

```text
C:\Users\cyo20\EIDP-v541-e62d074-env0
```

Setup and active-task safety:

```text
setup.exit_code=0
EIDP_REGISTER_WEEKLY_TASK=0
validate_after_setup.ok=true
recovery.ok=true
weekly_task_action_unchanged=true
active weekly task remains C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
sqlite_integrity_check=ok
school_count=2418
school_fiscal_year_status_count=2418
```

Bounded weekly canary:

```text
weekly.exit_code=0
run_id=20260620_152248
last_run.status=success
current_fy=2026
school_type=専門学校
selection_mode=target_missing
target_missing_school_count=50
target_pdf_auto_acquired_count=12
target_pdf_auto_denominator_count=50
target_pdf_auto_yield_pct=24.0
strict_target_pdf_auto_acquired_count=12
strict_target_pdf_auto_yield_pct=24.0
target_pdf_excel_ready_acquired_count=12
target_pdf_excel_ready_yield_pct=24.0
operator_reviewable_count=47
operator_reviewable_yield_pct=94.0
ship_gate_status=below_gate
new_document_count=15
```

Global after-weekly validator:

```text
ok=true
last_run_status=success
sqlite_target_fy=2026
sqlite_target_fy_target_pdf_school_count=8
sqlite_target_fy_yield_pct=0.3
sqlite_target_fy_operator_reviewable_school_count=40
sqlite_target_fy_operator_reviewable_yield_pct=1.7
discovery_rca_batch_plan_item_count=20
discovery_rca_batch_plan_total_candidates=35
```

Discovery stats:

```text
crawled=59
found=50
downloaded=15
failed=5
skipped=713
prefiltered=569
candidate_school_mismatch=0
shared_origin_derived_fallback_skipped=0
rejection_reason_target_fiscal_year_not_detected=6
rejection_reason_fiscal_year_mismatch=206
rejection_reason_classified_non_target=103
rejection_reason_pre_filtered_non_target_hint=432
rejection_reason_no_candidates_found=5
rejection_reason_discovery_error=4
rejection_reason_pdf_school_mismatch=2
```

Stage 6 evidence:

```text
archive=C:\Users\cyo20\EIDP-v541-e62d074-env0\logs\stage6-evidence-20260620-153655.zip
verify_json=C:\Users\cyo20\EIDP-v541-e62d074-env0\logs\stage6-evidence-verify-20260621-003707.json
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
logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip
logs/win-v541-e62d074-canary/stage6-evidence-verify-20260621-003707.json
logs/win-v541-e62d074-canary/stage6-recovery-20260621-002217.json
logs/win-v541-e62d074-canary/20260620_152248-summary.json
```

Mac-side evidence verifier:

```text
uv run python scripts/verify_stage6_evidence.py \
  logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip \
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

The external-SSD-backed `dist/` directory was cleaned after v541 packaging:

- removed AppleDouble sidecars generated during packaging,
- removed superseded `eidp-v532-operator-docs-20260620.zip` and sidecar,
- retained v535, v536, v540, v541 core ZIPs and the v540 r2 owner-docs ZIP.

Current `dist/` size after cleanup: about `1.3G` on `/Volumes/M1nG-ssd`.

## Conclusion

v541 closes the P1 package/canary gap for the owner-return verifier hardening
introduced after v540. It does not change the v1 release verdict. The bounded
Windows canary remains strict/Excel-ready `12/50 (24.0%)`, and the owner real
cycle/sign-off is still missing.

Next required actions:

1. Refresh and stage v541 owner handoff docs before any owner real cycle.
2. Continue strict-yield RCA against the `publication_lag_or_old_target_pdf`,
   target-year-unverified, OCR/image-pending, and mismatch lanes.
3. Keep final release status `NOT_READY` until the strict Excel-ready gate and
   owner evidence are both satisfied.
