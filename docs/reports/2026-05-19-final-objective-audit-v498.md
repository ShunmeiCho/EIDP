# Final Objective Audit - v498 Windows Side-by-Side State

Date: 2026-05-19
Branch: `sprint8-handoff-finalize`
PR: `#2`
Package source commit: `555fe014feba49e13badd66ef6fcbb434f879d26`
Package: `dist/eidp-windows-v498.zip`
Package SHA256: `05f7dee2b6a487a798ae3121ea55ceb5593794126ef82e18afe2925ba7262930`

## Verdict

`NOT COMPLETE`.

v498 is now the current package candidate and has fresh Mac-side package/source
verification plus Windows side-by-side setup, OCR runtime, UI, weekly canary,
Excel export, and Stage 6 evidence-bundle proof. PR #2 mergeability is a live
gate and must be re-checked before merge; this audit intentionally pins the
package source commit, not a moving docs-only PR head.

This still is not v1.0 approval. The controlling business blocker remains the
FY2026/R8 strict current-year yield: the current proof is below the 60% ship
line unless an explicit `publication_lag` release exception is approved. Owner
real-cycle and sign-off evidence are also still missing.

## Objective Restated As Success Criteria

The objective is complete only when all of the following are true:

1. 47 prefecture official-list seeds are packaged and usable.
2. The school universe covers 1,700+ specialty schools.
3. Current rolling FY, now FY2026/Reiwa 8, target PDFs are found in strict mode
   with old-year fallback excluded from success.
4. `pdfplumber` + PyMuPDF + Tesseract OCR extraction exists, and only rows with
   three-factor confidence `>= 0.70` are allowed into Excel-facing output.
5. `DepartmentYearly` / `SupportRecipient` writes are append-only.
6. Excel transfer is verified.
7. All operator changes are auditable through `ManualActionLog`.
8. The Windows ZIP installs by double click and serves the browser UI offline.
9. The ship line is met: strict target-PDF/excel-ready `>= 60%` and manual
   workload `<= 30%` for the current rolling FY.
10. The owner real Windows cycle and sign-off evidence are complete.

## Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds | `logs/win-v498-stage6-v498-verify-windows-distribution-20260519.json`: verifier `ok=true`; package verifier reports `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47` | PASS |
| 1,700+ specialty-school scope | `logs/win-v498-stage6-v498-validate-after-setup-20260519.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v498-stage6-v498-last-run-after-weekly-canary-limit10-20260519.json`: `current_fy=2026`, `dry_run=false` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` and `logs/win-v490-stage6-v490-fy2026-strict-yield-upper-bound-reeval-20260519.json` keep old-year fallback out of strict FY2026 success | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | Upper-bound proof remains `39.3%`; v498 canary denominator 10 produced strict/Excel-ready `50.0%` and `ship_gate_status=below_gate` | FAIL |
| Mature FY2025 strict proof for exception path | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: `ok=true`, FY2025 denominator `1000`, strict `60.0%`, Excel-ready `60.0%`, manual workload `20.2%` | PASS for exception input only |
| PDF extraction stack packaged | v498 package verifier `ok=true`, `has_runtime=true`, `wheel_count=84`, `entry_count=3105` | PASS |
| Tesseract OCR runtime/add-on | `logs/win-v498-stage6-v498-validate-ocr-runtime-20260519.json`: `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present. Core + add-on verifier also `ok=true` in `logs/win-v498-stage6-v498-verify-windows-distribution-with-ocr-addon-20260519.json` | PASS |
| Confidence `>= 0.70` gating | CI and local gates cover confidence propagation and package verifier contracts; v498 OCR runtime proof confirms add-on availability, not full production OCR yield | PASS for code/runtime, PARTIAL for production OCR corpus |
| Append-only business writes | PR checks and unit gates cover write contracts. Owner real-cycle audit evidence is still missing | PASS for code, PARTIAL for real workflow |
| Excel template transfer | `logs/win-v498-stage6-v498-excel-summary-20260519.json`: master workbook exists, competition workbook exists, default competition template exists in `sample/`, competition workbook has 16 sheets | PASS |
| ManualActionLog audit | Tests and UI contracts exist, but owner real-cycle audit counts/outbox proof are not returned yet | PARTIAL |
| ZIP distribution and offline setup | v498 SHA matches sidecar; non-Windows gate package/source check fresh; Windows setup validator `ok=true` | PASS |
| Side-by-side setup can preserve active task | Fresh Windows root `%USERPROFILE%\EIDP-v498-555fe01-env0` was set up with `EIDP_REGISTER_WEEKLY_TASK=0`; `logs/win-v498-stage6-v498-first-setup-env0-20260519.log` shows `skipping Task Scheduler registration because EIDP_REGISTER_WEEKLY_TASK=0`; `logs/win-v498-stage6-v498-env0-validate-after-setup-20260519.json` is `ok=true`; `logs/win-v498-stage6-v498-env0-recovery-expected-v485-20260519.json` is `ok=true` with `action_matches_expected=true` | PASS |
| Browser UI on Windows | `logs/win-v498-stage6-v498-ui-smoke-20260519.json`: `ok=true`, port `8519`, health `200/ok`, root `200`, stopped cleanly | PASS |
| Active scheduled task safety | Initial v498 recovery check caught the task pointing to v498 after setup smoke; task was restored to v485. `logs/win-v498-stage6-v498-recovery-expected-v485-after-restore-20260519.json`: `ok=true`, `action_matches_expected=true` | PASS after restore |
| Stage 6 evidence bundle | `logs/win-v498-stage6-v498-stage6-evidence-20260519-123728.zip`; SHA256 `9d51bfce550dd1d4dc12843b19ecb0a99e5b06cdcbca655cf4aa1088b02d8199` | PASS |
| Stage 6 evidence verifier | `logs/win-v498-stage6-v498-stage6-evidence-verify-20260519-213747.json`: `ok=true`, labels include `build_info`, `diagnostics`, `last_run`, `stage6_recovery`, `weekly_run_logs` | PASS |
| SQLite backup recoverability smoke | `logs/win-v498-stage6-v498-env0-db-backup-summary-20260519.json`: `ok=true`, backup exists, `size_bytes=9383936`, SQLite `integrity_check=ok`, `school_count=2418` | PASS |
| High-severity static security scan | `logs/win-v498-stage6-v498-bandit-high-current-head-20260519.rc`: exit `0` for `uv run --with bandit bandit -q --severity-level high -r src/eidp` plus release scripts | PASS |
| Windows path safety | `logs/win-v498-stage6-v498-windows-path-safety-current-head-20260519.json`: issue count `0`; focused path-safety and CI Bandit contract tests returned `7 passed` | PASS |
| PR mergeability | Live gate checked with `gh pr view 2`; the PR body records the current head and check-run URLs. This audit intentionally avoids pinning docs-only PR heads to prevent freshness churn. | PASS at time of external audit; re-check before merge |
| Package/source freshness | `logs/win-v498-stage6-v498-non-windows-release-gates-20260519.json`: `package_source_check.ok=true`, `source_dirty=false`, `stale=false` | PASS |
| Publication-lag exception record | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| Unapproved exception cannot pass return verifier | `logs/win-v498-stage6-v498-verify-stage6-return-not-approved-exception-20260519.json`: verifier exit code `1`, `ok=false`, and errors include `release exception record Status must be APPROVED` plus `release exception record Decision must be APPROVED` | PASS for negative gate |
| Owner real Windows cycle | v498 has a bounded canary and Stage 6 bundle; owner real-cycle KPI table and sign-off are missing | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete, absent explicit release exception approval | BLOCKED |

## Verifier Coverage Notes

- `verify_windows_distribution.py` proves package structure, wheelhouse,
  build metadata, seed packaging, required files, Streamlit launcher guard,
  competition template packaging, and OCR add-on integrity when passed
  `--ocr-addon`. It does not prove current-FY production yield or owner
  sign-off.
- `run_non_windows_release_gates.py` proves Mac-side validator tests, type/lint
  checks, discovery gold-set checks, package verification, and package/source
  freshness. It does not prove active-lane promotion or production KPI success.
- The v498 Windows side-by-side proof now covers installation, OCR runtime,
  Streamlit health, bounded weekly execution, Excel output, and Stage 6 bundle
  verification. It is still a bounded validation, not owner approval.
- The env0 setup proof confirms that the documented side-by-side validation
  path can run `scripts\first_setup.bat` with `EIDP_REGISTER_WEEKLY_TASK=0`
  without moving the active scheduled task off v485.
- The FY2025 mature-year proof is valid only as release-exception support. It
  must not be counted as strict FY2026/R8 ship proof.
- `verify_stage6_return.py` rejects the current `publication_lag` path while
  the exception record remains `NOT_APPROVED`, even when the mature-year proof
  JSON and Stage 6 evidence verifier JSON are supplied.

## Required Next Actions

1. Keep v1.0 blocked until FY2026/R8 strict proof reaches 60%, or the owner
   explicitly approves the `publication_lag` release exception record.
2. If the exception path is approved, run the owner real Windows cycle on the
   selected lane and return the completed KPI/sign-off template, Stage 6
   evidence ZIP, and verifier JSON.
3. Run `scripts/verify_stage6_return.py` against the returned owner evidence,
   the approved exception record if used, and the mature-year proof JSON.
4. Only after the release blocker is resolved, merge PR #2 and create the
   signed `v1.0` tag.
