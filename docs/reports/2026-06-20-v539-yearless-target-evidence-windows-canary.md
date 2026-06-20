# v539 Yearless Target Evidence Windows Canary

Date: 2026-06-20
Package: `dist/eidp-windows-v539.zip`
Package SHA256: `2c18d2808d0e6910f056a98b181a057dab95fc229faad93289dde3ed7773a7a3`
Package/source commit: `142dfc71513413412432e4f76d8b7a72f03048cc`
Release conclusion: `NOT_READY`

## Current-State Audit

| Classification | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield remains below gate. | v539 Windows limit-50 canary reports `target_pdf_excel_ready_yield_pct=24.0`, `12/50`, and `ship_gate_status=below_gate`. |
| P0 release blocker | Owner real Windows cycle/sign-off is still missing. | v539 is Codex-operated side-by-side evidence, not returned owner/operator production evidence. |
| P0 release blocker | `publication_lag` release exception is not approved. | Existing release exception state is unchanged by v539. |
| P0 release blocker | OCR scope remains unresolved. | v539 did not restore or validate an OCR add-on/runtime proof. |
| P1 fixed | Target-form-like PDF candidates rejected for missing target fiscal year now retain clearer RCA evidence. | `target_fiscal_year_not_detected` rows for NEEC target-form-like PDFs now record `extra.year_evidence=target_application_no_year` while still rejecting the candidate. |
| P1 verified | Non-target/image-only candidates are not upgraded by the new evidence marker. | Sanko image-only rows rejected for missing target fiscal year keep `extra.year_evidence=none`. |

## CI Evidence

The screenshot showing `Ship gate contract` failure was an older `main` run for
commit `b2ed68f`. Current v539 source CI for `142dfc7` passed:

```text
Run: 27868273926
Commit: 142dfc71513413412432e4f76d8b7a72f03048cc
Python quality gates: success, 7m55s
Ship gate contract: success, 18s
```

Local verification before push:

```text
uv run ruff check src/eidp/scraper/pdf_discovery.py \
  src/eidp/review/_pages/pdf_manual_entry.py \
  tests/unit/test_pdf_discovery.py \
  tests/unit/test_review_pdf_manual_entry.py
All checks passed

uv run mypy src/eidp/scraper/pdf_discovery.py \
  src/eidp/review/_pages/pdf_manual_entry.py
Success: no issues found in 2 source files

uv run pytest tests/unit/test_pdf_discovery.py \
  tests/unit/test_review_pdf_manual_entry.py -q
288 passed, 5 warnings

git diff --check
clean
```

## Package Evidence

Build:

```text
uv run python scripts/build_windows_zip.py \
  --out-zip dist/eidp-windows-v539.zip \
  --latest-alias
```

Result highlights:

```text
OK: wrote dist/eidp-windows-v539.zip
size=210918827 bytes
sha256=2c18d2808d0e6910f056a98b181a057dab95fc229faad93289dde3ed7773a7a3
```

Verification:

```text
shasum -a 256 -c dist/eidp-windows-v539.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v539.zip --json
```

Result highlights:

```text
BUILD_INFO.git_commit=142dfc71513413412432e4f76d8b7a72f03048cc
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

Windows side-by-side root:

```text
C:\Users\cyo20\EIDP-v539-142dfc7-env0
```

Setup and recovery:

```text
setup.exit_code=0
validate.exit_code=0
validate.ok=true
recovery.exit_code=0
recovery.ok=true
sqlite_integrity_check=ok
school_count=2418
school_fiscal_year_status_count=2418
weekly_task_action_unchanged=true
```

Bounded weekly canary:

```text
weekly.exit_code=0
weekly.timed_out=false
validate.exit_code=0
validate.timed_out=false
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
school_alias_proposals.error=null
school_alias_proposals.proposal_stats.proposals=2
school_alias_proposals.write_stats.appended=2
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

Yearless target evidence sample:

```text
reason=target_fiscal_year_not_detected
pdf_type=target
pdf_url=https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf
extra.discovery_method=school_domain_override
extra.target_fiscal_year=2026
extra.detected_fiscal_year=""
extra.year_evidence=target_application_no_year
extra.trusted_year_evidence=""
```

Control sample:

```text
reason=target_fiscal_year_not_detected
pdf_type=image_only
pdf_url=https://www.sanko.ac.jp/sendai-beauty/pdf/yoshiki2021.pdf
extra.year_evidence=none
extra.trusted_year_evidence=""
```

Stage 6 evidence:

```text
archive=C:\Users\cyo20\EIDP-v539-142dfc7-env0\logs\stage6-evidence-20260620-110538.zip
verify_json=C:\Users\cyo20\EIDP-v539-142dfc7-env0\logs\stage6-evidence-verify-20260620-200538.json
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

Pulled-back evidence on the external-SSD-backed `logs` directory:

```text
logs/win-v539-142dfc7-canary/last_run.json
logs/win-v539-142dfc7-canary/20260620_104823-summary.json
logs/win-v539-142dfc7-canary/20260620_104823-discovery-rejections.jsonl
logs/win-v539-142dfc7-canary/20260620_104823-ingest-rejections.jsonl
logs/win-v539-142dfc7-canary/20260620_104823-discovery-rca-batch-plan.json
logs/win-v539-142dfc7-canary/stage6-evidence-20260620-110538.zip
logs/win-v539-142dfc7-canary/stage6-evidence-verify-20260620-200538.json
logs/win-v539-142dfc7-canary/v539-verify-windows-distribution.json
```

## Cleanup

After v539 was built and verified, superseded v538 core artifacts were removed
from the external-SSD-backed `dist` directory:

```text
uv run python scripts/prune_release_artifacts.py \
  --dist-dir dist \
  --keep-latest 1 \
  --keep-version 535 \
  --keep-version 536 \
  --apply \
  --json

deleted_count=2
deleted_bytes=210917697
deleted:
  dist/eidp-windows-v538.zip
  dist/eidp-windows-v538.zip.sha256
```

Retained core package artifacts are v535, v536, and v539. AppleDouble `._*`
metadata sidecars were removed from `dist/`.

## Release Boundary

v539 improves operator/RCA evidence for yearless target-form-like PDF
candidates without accepting them as FY2026/Reiwa 8 target documents. It does
not make v1 release-ready because the v1 release gates remain below required
proof:

- strict FY2026/R8 Excel-ready yield is still below gate;
- owner/operator real Windows cycle and sign-off remain missing;
- `publication_lag` release exception remains unapproved;
- OCR scope remains unresolved.

Therefore the release conclusion remains:

```text
NOT_READY
```
