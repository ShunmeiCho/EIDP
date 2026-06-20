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

## Strict-Yield Blocker RCA Framing

The primary v1 blocker is:

```text
FY2026/R8 strict target-document to Excel-ready yield below gate
```

It is not simply "the crawler cannot run", "PDFs are missing", or "any PDF was
not found". v541 found many candidates, but most were correctly rejected before
they could become FY2026/R8 Excel-ready evidence. It is also not evidence that
the algorithm/model is broadly broken. Some discovery, classification, and
fiscal-year rules may need improvement, but the current evidence supports a
mixed strict-gate failure profile rather than a single model-failure diagnosis:

- `publication_lag_or_old_target_pdf` / `fiscal_year_mismatch`: old-year or
  latest-public target forms that cannot count as current FY2026/R8 success.
- `pre_filtered_non_target_hint` and `classified_non_target`: public PDFs that
  are not target application forms and must stay out of final Excel.
- `target_fiscal_year_not_detected`: target-form-like PDFs without trusted
  FY2026/R8 evidence.
- `no_candidates_found`, `discovery_error`, and `pdf_school_mismatch`: smaller
  but correctness-critical site-entry, fetch, or identity lanes.

The next RCA pass should follow the largest release-impact buckets in this
order:

1. inspect `rejection_reason_fiscal_year_mismatch=206` to separate true
   publication lag / old target forms from any current-year false rejects;
2. inspect `rejection_reason_pre_filtered_non_target_hint=432` and
   `rejection_reason_classified_non_target=103` for over-rejection risk;
3. inspect `rejection_reason_target_fiscal_year_not_detected=6` for official
   page, index, anchor, filename, or PDF evidence that can support review;
4. inspect `rejection_reason_no_candidates_found=5`,
   `rejection_reason_discovery_error=4`, and
   `rejection_reason_pdf_school_mismatch=2` for site-entry, fetch, and identity
   gaps.

Use a false-reject audit to decide whether the next improvement is algorithmic
or operational:

- sample `fiscal_year_mismatch` candidates and separate true old-year target
  forms from fiscal-year extraction mistakes;
- sample `pre_filtered_non_target_hint` and `classified_non_target` candidates
  to detect target-form over-rejection;
- inspect all `target_fiscal_year_not_detected` candidates for trusted official
  page, anchor, filename, or body evidence;
- inspect all `no_candidates_found`, `discovery_error`, and
  `pdf_school_mismatch` candidates for SiteEntry, fetch, or identity gaps.

If false rejects are high, fix the specific rule or classifier. If false
rejects are low, the blocker is dominated by publication lag, old-year files,
non-target noise, or release-scope decisions, not a generic algorithm failure.
The first reproducible packet for this review is
`docs/reports/2026-06-21-v541-false-reject-audit-packet.md`, generated from the
same Stage 6 evidence ZIP with `scripts/build_false_reject_audit.py`.
The companion review worksheet is
`docs/reports/2026-06-21-v541-false-reject-review-sheet.csv`; the same script
can validate the returned worksheet with `--validate-review-csv` and can require
completed decisions with `--require-decisions`.

None of these buckets permits relaxing the FY2026/R8 evidence rules. A
`publication_lag` decision can support at most the documented `RC_ONLY` route
after owner return evidence and `scripts/verify_stage6_return.py` pass; it does
not make v541 `READY`.

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

1. Run the prepared v541 owner/operator return path from Windows and verify the
   returned evidence with `scripts/verify_stage6_return.py`.
2. Continue strict-yield RCA in bucket order: fiscal-year mismatch /
   publication lag, non-target candidate noise, target-year-unverified, then
   site-entry/fetch/identity lanes.
3. Use `docs/reports/2026-06-21-v541-false-reject-review-sheet.csv` to mark the
   first rejection-bucket sample as `false_reject`, `correct_reject`, or
   `needs_operator_review`, then validate it with `scripts/build_false_reject_audit.py`
   before labeling the blocker as an algorithm/model defect.
4. Keep final release status `NOT_READY` until the strict Excel-ready gate and
   owner evidence are both satisfied.
