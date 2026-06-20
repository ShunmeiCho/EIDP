# v538 PDF Mismatch Alias Windows Canary

Date: 2026-06-20
Package: `dist/eidp-windows-v538.zip`
Package SHA256: `5d32c3c21fef227a8da13a6dab2c7b6d29e6d304363d90340af757ed0a7b7e1a`
Package/source commit: `27e1bcd067212f4f362a31309122ee2492373b72`
Release conclusion: `NOT_READY`

## Current-State Audit

| Classification | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield remains below gate. | v538 Windows limit-50 canary reports `target_pdf_excel_ready_yield_pct=24.0`, `12/50`, and `ship_gate_status=below_gate`. |
| P0 release blocker | Owner real Windows cycle/sign-off is still missing. | v538 is Codex-operated side-by-side evidence, not returned owner/operator production evidence. |
| P0 release blocker | `publication_lag` release exception is not approved. | Existing release exception record remains `NOT_APPROVED`; v538 does not change the approval state. |
| P0 release blocker | OCR scope remains unresolved. | v538 did not restore or validate an OCR add-on/runtime proof. |
| P1 fixed | v537 Windows weekly canary failed because alias proposal logic was imported by sibling script module name. | v537 `last_run.json` recorded `ModuleNotFoundError: No module named 'pdf_school_mismatch_alias_proposals'`. |
| P1 fixed | Alias proposal logic is now packaged under `eidp.review.pdf_school_mismatch_alias_proposals`. | Commit `27e1bcd` moves the reusable logic into `src/eidp/review/`, keeps the script as a wrapper, and adds a regression test that blocks dependency on the old script module name. |
| P1 verified | v538 Windows weekly canary now completes and writes alias proposals. | v538 `last_run.json` has `status=success`; `school_alias_proposals.error=null`; `proposal_stats.proposals=2`; `write_stats.appended=2`. |

## CI Evidence

The screenshot showing `Ship gate contract` failure was CI run `#789`
(`b2ed68fb8c9a797efc96987058a3997491de65b2`) and is stale. Its failure was
valid at the time: the smoke proof JSON missed `school_type=専門学校`. It was
fixed by the later `#790` run and current `main` is green.

Latest v538 source CI:

```text
Run: #803 / 27866916777
Commit: 27e1bcd067212f4f362a31309122ee2492373b72
Python quality gates: success, 7m57s
Ship gate contract: success, 16s
```

Local verification before push:

```text
uv run pytest tests/unit/test_pdf_school_mismatch_alias_proposals.py \
  tests/unit/test_run_weekly_target_year_discovery.py -q
40 passed

uv run ruff check scripts/run_weekly_target_year_discovery.py \
  scripts/pdf_school_mismatch_alias_proposals.py \
  src/eidp/review/pdf_school_mismatch_alias_proposals.py \
  tests/unit/test_run_weekly_target_year_discovery.py \
  tests/unit/test_pdf_school_mismatch_alias_proposals.py
All checks passed

uv run mypy src scripts/run_weekly_target_year_discovery.py \
  scripts/pdf_school_mismatch_alias_proposals.py
Success: no issues found in 99 source files
```

## Package Evidence

Build:

```text
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-v538.zip --latest-alias
```

Result:

```text
OK: wheelhouse contains 84 accepted wheels
OK: wrote dist/eidp-windows-v538.zip (201.1 MB)
OK: wrote checksum sidecar dist/eidp-windows-v538.zip.sha256
OK: refreshed latest alias dist/eidp-windows.zip
```

Verification:

```text
shasum -a 256 -c dist/eidp-windows-v538.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v538.zip --json
```

Result highlights:

```text
sha256=5d32c3c21fef227a8da13a6dab2c7b6d29e6d304363d90340af757ed0a7b7e1a
BUILD_INFO.git_commit=27e1bcd067212f4f362a31309122ee2492373b72
BUILD_INFO.git_dirty=false
entry_count=3117
has_runtime=true
wheel_count=84
project_wheel_count=1
mext_target_total_rows=3132
mext_target_specialty_rows=2067
discovery_gold_set_entries=45
discovery_gold_expected_predictions=45
discovery_gold_undemonstrated_pattern_sources=[]
```

## Windows Evidence

Windows side-by-side root:

```text
C:\Users\cyo20\EIDP-v538-27e1bcd-env0
```

Transfer/extract:

```text
sha256=5d32c3c21fef227a8da13a6dab2c7b6d29e6d304363d90340af757ed0a7b7e1a
setup_bat=true
build_info=true
```

Setup and recovery:

```text
setup_rc=0
validate_rc=0
validate_ok=true
recovery_rc=0
recovery_ok=true
weekly_action_before="C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
weekly_action_after="C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
weekly_action_unchanged=true
```

Bounded weekly canary:

```text
weekly.exit_code=0
weekly.timed_out=false
validate.exit_code=0
validate_ok=true
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
school_alias_proposals.proposal_stats.input_rows=774
school_alias_proposals.proposal_stats.pdf_school_mismatch_rows=2
school_alias_proposals.proposal_stats.proposals=2
school_alias_proposals.write_stats.appended=2
school_alias_proposals.error=null
```

Stage 6 evidence:

```text
archive=C:\Users\cyo20\EIDP-v538-27e1bcd-env0\logs\stage6-evidence-20260620-094934.zip
verify_json=C:\Users\cyo20\EIDP-v538-27e1bcd-env0\logs\stage6-evidence-verify-20260620-184948.json
verify.ok=true
verify.errors=[]
present_labels=[
  build_info,
  diagnostics,
  discovery_evidence,
  discovery_rca,
  last_run,
  weekly_run_logs
]
required_labels=[build_info, diagnostics, last_run]
```

Pulled-back evidence:

```text
logs/win-v538-stage6/stage6-evidence-20260620-094934.zip
logs/win-v538-stage6/stage6-evidence-verify-20260620-184948.json
logs/win-v538-stage6/last_run.json
logs/win-v538-stage6/school_missing_proposals.jsonl
logs/win-v538-stage6/BUILD_INFO.json
logs/win-v538-stage6/win-20260620-v538-validate-after-weekly.json
```

## Cleanup

After v538 was built and Windows-validated, superseded v537 core artifacts were
removed from the external-SSD-backed `dist` directory:

```text
uv run python scripts/prune_release_artifacts.py \
  --dist-dir dist \
  --keep-latest 1 \
  --keep-version 535 \
  --keep-version 536 \
  --apply \
  --json

deleted_count=2
deleted_bytes=210912547
deleted:
  dist/eidp-windows-v537.zip
  dist/eidp-windows-v537.zip.sha256
```

Retained core package artifacts are v535, v536, and v538. AppleDouble `._*`
metadata sidecars were removed from `dist/`.

## Release Boundary

v538 fixes the v537 Windows canary failure and is now the latest bounded
Windows canary package. It does not make v1 release-ready because the v1 release
gates remain below required proof:

- strict FY2026/R8 Excel-ready yield is still below gate;
- owner/operator real Windows cycle and sign-off remain missing;
- `publication_lag` release exception remains unapproved;
- OCR scope remains unresolved.

Therefore the release conclusion remains:

```text
NOT_READY
```
