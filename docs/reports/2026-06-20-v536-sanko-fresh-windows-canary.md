# v536 Sanko Fresh Windows Canary

Date: 2026-06-20
Package: `dist/eidp-windows-v536.zip`
Package SHA256: `381ec169b8380cfe666a89e02a8b786d3a8cdc79dca4b420276517bbbdb0349a`
Package/source commit: `f81a9cf8f785457e844cb77857426a02c91f60c7`
Windows root: `C:\Users\cyo20\EIDP-v536-f81a9cf-env0`
Release conclusion: `NOT_READY`

## Current-State Audit

| Classification | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield remains below gate. | v536 Windows canary: `12/50 (24.0%)`, `ship_gate_status=below_gate` |
| P0 release blocker | Owner real Windows cycle/sign-off is still missing. | v536 is a bounded side-by-side canary, not returned owner sign-off evidence |
| P0 release blocker | `publication_lag` release exception is not approved. | Current release exception record remains `NOT_APPROVED` |
| P0 release blocker | OCR scope remains unresolved. | v536 did not add a fresh validated OCR runtime proof |
| P1 release hardening | Sanko shared-origin disclosure probe fix is now Windows-canary exercised. | v536 BUILD_INFO commit is `f81a9cf...`; `shared_origin_derived_fallback_skipped=0` |

## Purpose

v536 rebuilds the Windows package after the Sanko shared-origin disclosure
probe fix. The purpose of this canary is to verify whether keeping both
Sanko school-slug disclosure shapes under shared-origin throttling changes the
remaining v535 `non_target_candidates_only` RCA packet for:

```text
school_id=41
大宮ビューティ＆ブライダル専門学校
registered_source=https://www.sanko.ac.jp/omiya-beauty/
```

## Mac-Side Package Evidence

Build:

```text
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-v536.zip --latest-alias
```

Result:

```text
OK: wheelhouse contains 84 accepted wheels
OK: wrote dist/eidp-windows-v536.zip (201.1 MB)
OK: wrote checksum sidecar dist/eidp-windows-v536.zip.sha256
OK: refreshed latest alias dist/eidp-windows.zip
```

Package verification:

```text
shasum -a 256 -c dist/eidp-windows-v536.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v536.zip --json
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v536.zip \
  --json \
  --output logs/win-v536-stage6-v536-non-windows-release-gates-20260620.json
```

Result highlights:

```text
sha256=381ec169b8380cfe666a89e02a8b786d3a8cdc79dca4b420276517bbbdb0349a
package_source_check.ok=true
package_source_check.stale=false
package_source_check.source_dirty=false
unit_full=2019 passed
validator_distribution_unit=196 passed
validator_distribution_mypy=success
validator_distribution_ruff=success
package_verify=ok
```

## Windows Evidence

Transfer and SHA verification:

```text
scp dist/eidp-windows-v536.zip dist/eidp-windows-v536.zip.sha256 win:C:/EIDP-staging/
Windows Get-FileHash SHA256 -> 381ec169b8380cfe666a89e02a8b786d3a8cdc79dca4b420276517bbbdb0349a
```

Side-by-side setup:

```text
C:\Users\cyo20\EIDP-v536-f81a9cf-env0
EIDP_REGISTER_WEEKLY_TASK=0
EIDP-setup.bat rc=0
validate_windows_install.py . --after-setup --json -> ok=true
```

Active-task safety:

```text
stage6_recovery_check.py --expected-weekly-action C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat --probe-lock --json
ok=true
lock_probe.ok=true
lock_probe.held=false
```

Bounded weekly canary:

```text
scripts\weekly_run.bat --limit 50 --json
rc=0
status=success
current_fy=2026
school_type=専門学校
selection_mode=target_missing
target_pdf_auto_acquired_count=12
target_pdf_auto_denominator_count=50
strict_target_pdf_auto_yield_pct=24.0
target_pdf_excel_ready_yield_pct=24.0
operator_reviewable_count=47
operator_reviewable_yield_pct=94.0
ship_gate_status=below_gate
```

The canary produced:

```text
discovery_stats.crawled=59
discovery_stats.found=50
discovery_stats.downloaded=15
discovery_stats.failed=2
discovery_stats.shared_origin_derived_fallback_skipped=0
ingest_stats.processed=15
ingest_stats.departments_created=122
ingest_stats.yearly_upserted=129
```

`validate_windows_install.py . --after-weekly --json` passed with `ok=true`.
The stricter `--require-ship-gate` variant intentionally failed because the
canary is still below the release gate:

```text
last_run.json ship_gate_status must be pass when --require-ship-gate is used
```

Stage 6 evidence:

```text
logs/win-v536-stage6/stage6-evidence-20260620-074649.zip
logs/win-v536-stage6/stage6-evidence-verify-20260620-164649.json
```

Windows and Mac verification both returned:

```text
ok=true
entry_count=7
present_labels=build_info, diagnostics, discovery_evidence, discovery_rca, last_run, weekly_run_logs
missing_required_labels=[]
unsafe_entries=[]
forbidden_entries=[]
```

## RCA Result

Mac-side RCA summary:

```text
uv run python scripts/summarize_stage6_rca.py \
  logs/win-v536-stage6/stage6-evidence-20260620-074649.zip \
  --json
```

Result:

```text
strict_yield.conclusion=BELOW_GATE
strict_yield.excel_ready_acquired_count=12
strict_yield.denominator=50
strict_yield.operator_reviewable_count=47
rca_batch.item_count=20
rca_batch.candidate_rows=524
```

The bucket summary remains:

```text
publication_lag_or_old_target_pdf: 15 schools / 454 candidate rows
target_form_without_year_evidence: 2 schools / 10 candidate rows
school_identity_mismatch: 2 schools / 48 candidate rows
non_target_candidates_only: 1 school / 12 candidate rows
```

School `41` remains `non_target_candidates_only`, but the reason changed from
"possibly missed same-origin disclosure page" to "official disclosure page was
reached and only non-target candidates were found". The evidence includes
Sanko same-host disclosure candidates such as:

```text
https://www.sanko.ac.jp/omiya-beauty/disclosure/2026/docs/schoolinfo.pdf
https://www.sanko.ac.jp/omiya-beauty/disclosure/beauty_01.pdf
https://www.sanko.ac.jp/omiya-beauty/disclosure/hairmake_01.pdf
```

These are not accepted as target documents, and they must not enter Excel.

## Release Boundary

v536 is useful P1 Windows evidence for the Sanko probe fix. It is not a full
release replacement for v535 because this run did not repeat the full UI and
Excel smoke matrix. More importantly, it does not change the P0 release result:

```text
Release conclusion: NOT_READY
```

The remaining blockers are:

- strict FY2026/R8 Excel-ready yield is still `12/50 (24.0%)`;
- owner/operator real Windows cycle and sign-off are missing;
- `publication_lag` release exception remains unapproved;
- OCR release scope still lacks a fresh v536 runtime proof or written scope
  decision.
