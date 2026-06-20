# v540 Owner-Brief Gate Windows Canary

Date: 2026-06-20
Branch: `main`
Package: `dist/eidp-windows-v540.zip`
Package SHA256: `6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6`
Package/source commit: `fbdd0bddbeca3e6ceaa7b9e576bc9c5b0b88025a`
Windows side-by-side root: `C:\Users\cyo20\EIDP-v540-fbdd0bd-env0`

## Classification

| Class | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield remains below gate. | v540 Windows limit-50 canary reports `target_pdf_excel_ready_yield_pct=24.0`, `12/50`, and `ship_gate_status=below_gate`. |
| P0 release blocker | Owner real Windows cycle/sign-off is still missing. | v540 is Codex-operated side-by-side evidence, not returned owner/operator production evidence. |
| P0 release blocker | `publication_lag` release exception is not approved. | v540 wires the owner-decision brief gate, but does not approve the exception. |
| P0 release blocker | OCR scope remains unresolved. | v540 did not restore or validate an OCR add-on/runtime proof. |
| P1 release hardening | Post-v539 source-hardening now has Windows package/canary evidence. | v540 packages commit `fbdd0bd` and completed setup, bounded weekly canary, after-weekly validation, and Stage 6 evidence verification on Windows. |

## Owner Sign-off Boundary

Owner sign-off should stay short, but the evidence it points to must not be
shortened. The owner/operator should not be asked to manually reproduce CI,
wheelhouse, package-entry, or JSONL checklist details. The release packet must
provide those details through CI, package verification, Windows canary evidence,
Stage 6 evidence verification, `current-release-status.md`, and known
limitations.

The owner decision should confirm only:

- the selected release ID, ZIP, SHA256, and source commit are understood;
- the release conclusion is one of `READY`, `RC_ONLY`, or `NOT_READY`;
- v1 scope is the vocational-school Windows single-operator workflow, not the
  university production workflow;
- known limitations and release exceptions are understood;
- the owner accepts or rejects the selected release decision.

For v540, the only supported release conclusion is still `NOT_READY`.
`publication_lag` approval could support at most `RC_ONLY` after the rest of
the required evidence is complete; it must not convert old-year, year-unknown,
school-mismatch, low-confidence, or unresolved program-change rows into
Excel-ready data.

## Package Evidence

Build:

```text
uv run python scripts/build_windows_zip.py \
  --out-zip dist/eidp-windows-v540.zip \
  --latest-alias \
  --skip-download
```

Result highlights:

```text
OK: wrote dist/eidp-windows-v540.zip (201.1 MB)
sha256=6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6
```

Verification:

```text
shasum -a 256 -c dist/eidp-windows-v540.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v540.zip --json
```

Result highlights:

```text
BUILD_INFO.git_commit=fbdd0bddbeca3e6ceaa7b9e576bc9c5b0b88025a
BUILD_INFO.git_dirty=false
entry_count=3117
has_runtime=true
wheel_count=84
mext_target_total_rows=3132
mext_target_specialty_rows=2067
discovery_gold_expected_predictions=45
discovery_gold_undemonstrated_pattern_sources=[]
```

Local package verifier JSON:

```text
logs/win-v540-stage6-v540-verify-windows-distribution-20260620.json
```

## Windows Evidence

Transfer and checksum:

```text
scp dist/eidp-windows-v540.zip dist/eidp-windows-v540.zip.sha256 win:C:/EIDP-staging/
certutil -hashfile C:\EIDP-staging\eidp-windows-v540.zip SHA256
```

Windows SHA256 matched:

```text
6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6
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
weekly.end_marker=rc=0
last_run.status=success
last_run.selection_mode=target_missing
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
last_run_status=success
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
failed=1
skipped=717
prefiltered=569
rejection_reason_target_fiscal_year_not_detected=6
rejection_reason_fiscal_year_mismatch=206
rejection_reason_classified_non_target=103
rejection_reason_pre_filtered_non_target_hint=432
rejection_reason_no_candidates_found=9
rejection_reason_pdf_school_mismatch=2
```

Stage 6 evidence:

```text
archive=C:\Users\cyo20\EIDP-v540-fbdd0bd-env0\logs\stage6-evidence-20260620-133325.zip
verify_json=C:\Users\cyo20\EIDP-v540-fbdd0bd-env0\logs\stage6-evidence-verify-20260620-223357.json
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

Local copied evidence:

```text
logs/win-v540-fbdd0bd-canary/last_run.json
logs/win-v540-fbdd0bd-canary/20260620_131759-summary.json
logs/win-v540-fbdd0bd-canary/20260620_131759-discovery-rejections.jsonl
logs/win-v540-fbdd0bd-canary/20260620_131759-ingest-rejections.jsonl
logs/win-v540-fbdd0bd-canary/20260620_131759-discovery-rca-batch-plan.json
logs/win-v540-fbdd0bd-canary/stage6-evidence-20260620-133325.zip
logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-20260620-223357.json
logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-mac-20260620.json
logs/win-v540-fbdd0bd-canary/stage6-rca-summary-20260620.json
logs/win-v540-fbdd0bd-canary/stage6-recovery-20260620-221715.json
logs/win-v540-fbdd0bd-canary/win-20260620-v540-validate-after-setup.json
logs/win-v540-fbdd0bd-canary/win-20260620-v540-validate-after-weekly.json
logs/win-v540-fbdd0bd-canary/run-20260620.log
```

## RCA Summary

Local RCA summary:

```text
uv run python scripts/summarize_stage6_rca.py \
  logs/win-v540-fbdd0bd-canary/stage6-evidence-20260620-133325.zip \
  --json
```

RCA result:

```text
ok=true
item_count=20
candidate_rows=524
publication_lag_or_old_target_pdf=15 schools / 454 actionable candidate rows
target_form_without_year_evidence=2 schools / 10 actionable candidate rows
school_identity_mismatch=2 schools / 48 actionable candidate rows
non_target_candidates_only=1 school / 12 actionable candidate rows
```

## Storage Hygiene

The build used the external-SSD-backed symlinks:

```text
dist -> /Volumes/M1nG-ssd/EIDP-artifacts/dist
logs -> /Volumes/M1nG-ssd/EIDP-artifacts/logs
```

After v540 verification, generated AppleDouble `._*` sidecars were removed
from `dist/` and `logs/win-v540-fbdd0bd-canary/`. The superseded v539 core ZIP
and sidecar were pruned from `dist/`. Retained local core package artifacts are
v535, v536, and v540, plus the `dist/eidp-windows.zip` latest alias.

## Conclusion

v540 closes the post-v539 source-to-Windows evidence gap for the owner-decision
brief release-gate hardening. It does not make v1.0 ready. Release remains
blocked by the current-year strict yield gate, missing owner/operator real-cycle
approval, missing `publication_lag` approval, and unresolved OCR scope.
