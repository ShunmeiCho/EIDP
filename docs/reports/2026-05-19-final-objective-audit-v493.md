# Final Objective Audit - v493 Mac-side State

Date: 2026-05-19
Branch: `sprint8-handoff-finalize`
PR: `#2`
PR head checked: `5967d8e5d23be55c9546503fc226fdd47d7db107`
Mac package: `dist/eidp-windows-v493.zip`
Package source commit: `a3fbf4a728917defb5ef9bff7568322deb7f99dd`

## Verdict

`NOT COMPLETE`.

v493 is the current Mac-side package/source-verified candidate, and PR #2 is
clean with the required checks passing. That is not sufficient for the final
rolling-FY objective. The controlling business blocker remains the FY2026/R8
production-scale strict-yield proof: currently available public PDFs cannot
reach the 60% strict current-FY target-PDF/excel-ready gate. Owner real Windows
cycle evidence is also still missing.

Do not tag `v1.0`, merge to `main`, or request owner sign-off under the strict
FY2026 contract unless an explicit release exception is approved.

## Objective Restated As Success Criteria

The objective is complete only when all of the following are true:

1. 47 prefecture official-list seeds are packaged and usable.
2. The school universe covers 1,700+ specialty schools.
3. Current rolling FY, now FY2026/Reiwa 8, target PDFs are found in strict mode
   with old-year fallback excluded from success.
4. `pdfplumber` + PyMuPDF + Tesseract OCR extraction exists, and only rows with
   three-factor confidence `>= 0.70` are allowed into Excel-facing business
   output.
5. `DepartmentYearly` / `SupportRecipient` writes are append-only.
6. Excel transfer is verified.
7. All operator changes are auditable through `ManualActionLog`.
8. The Windows ZIP installs by double click and serves the browser UI offline.
9. The ship line is met: strict target-PDF/excel-ready `>= 60%` and manual
   workload `<= 30%` for the current rolling FY.
10. The owner real Windows cycle and sign-off evidence are complete.

## Prompt-to-artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds | `logs/win-v493-stage6-v493-verify-windows-distribution-20260519.json`: `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47` | PASS |
| 1,700+ specialty-school scope | v489 Windows setup validator `logs/win-v489-stage6-v489-validate-after-setup-20260519.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `docs/reports/2026-05-19-fy2026-strict-yield-no-go.md`; no-go proof targets `target_fiscal_year=2026` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`: after `607/1000`, FY2026 discovered documents were `0`; FY2025/R7 PDFs were not counted as FY2026 success | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | Same proof: maximum possible strict yield after the mathematical failure bound is `39.3%` | FAIL |
| Mature FY2025 strict proof | `_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json`: FY2025 denominator `1000`, strict `600/1000 (60.0%)`, excel-ready `600/1000 (60.0%)`, manual workload `20.2%` | PASS for mature-year algorithm evidence only |
| PDF extraction stack | v493 package verifier passed; package includes the project wheel and runtime, with `wheel_count=84`, `entry_count=3104`, and `has_runtime=true` | PASS |
| Confidence `>= 0.70` gating | v493 non-Windows gate `logs/win-v493-stage6-v493-non-windows-release-gates-20260519.json` returned `ok=true`; full unit count `1865 passed` | PASS for tested code path |
| Append-only business writes | PR #2 CI passed; local focused checks passed after the fiscal-year override `FOR UPDATE` hardening. This is code/test evidence, not owner-cycle evidence | PASS for code contract, PARTIAL for real workflow |
| Excel template transfer | `logs/release-gate-v485-retroactive-matrix.json`: `ok=true`, `case_count=3`; this is retroactive/mature-year evidence, not FY2026 owner-cycle output | PARTIAL |
| ManualActionLog audit | PR #2 CI passed relevant tests; owner real-cycle audit evidence remains incomplete | PARTIAL |
| ZIP distribution and offline setup | `dist/eidp-windows-v493.zip`, SHA256 `77d98222d9e5474b5db173e6a4ec252b0c06295d1f1c6fce63a2fc1732d34e9b`; `BUILD_INFO.git_dirty=false`; Mac package verifier `ok=true` | PASS for Mac-side package, PENDING for Windows side-by-side |
| Browser UI on Windows | Latest Windows UI smoke remains v489: `logs/win-v489-stage6-v489-ui-smoke-20260519.json` returned `ok=true`, health `200/ok`, root `200`, stopped cleanly | PASS for v489, PENDING for v493 |
| Active scheduled task safety | v489 recovery check `logs/win-v489-stage6-v489-recovery-expected-v485-20260519.json`: `ok=true`, `action_matches_expected=true`; active task stayed on v485 | PASS |
| v485 `streamlit.main` launcher issue | `docs/runbooks/eidp-windows.md` documents `No module named streamlit.main` and a non-SSH hotfix; `docs/runbooks/eidp-operator-e2e-template.md` now checks launcher entrypoint before UI smoke | PASS for runbook, PENDING for Win-side applied repair |
| PR mergeability | `gh pr view 2`: head `5967d8e5d23be55c9546503fc226fdd47d7db107`, `mergeStateStatus=CLEAN`; `Python quality gates` and `Ship gate contract` both `SUCCESS` | PASS |
| Package/source freshness | v493 package was built from `a3fbf4a728917defb5ef9bff7568322deb7f99dd`; current PR head `5967d8e...` is docs-only ahead. `logs/win-v493-stage6-v493-docs-only-stale-check-20260519.json`: `ok=true`, `docs_only_stale=true`, `allowed_stale_reason=docs_only` | PASS |
| Owner real Windows cycle | Latest owner evidence remains incomplete; active v485 DB previously had `school_site_count=0` and `document_count=0`; owner must run initial bootstrap before weekly cycle | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete, absent an explicit release exception | BLOCKED |

## Verifier Coverage Notes

- `verify_windows_distribution.py` proves package structure, wheelhouse,
  build metadata, seed packaging, required files, Streamlit launcher guard, and
  packaging contracts. It does not prove FY2026 strict target-PDF yield or owner
  workflow completion.
- `run_non_windows_release_gates.py` proves Mac-side unit tests, validator
  tests, type/lint checks, discovery gold-set checks, package verification, and
  package/source freshness. It does not prove Windows active-lane promotion or
  real operator E2E.
- v489 Windows setup/UI smoke proves a previous side-by-side package can start
  on the operator PC. It does not prove v493 Windows operability.
- The FY2025 strict replay proves mature-year algorithm capability. It must not
  be used as current FY2026 ship proof.
- The FY2026 upper-bound proof is the controlling current-FY evidence and is
  below gate.

## Required Next Actions

1. Keep v1.0 blocked until FY2026/R8 public target PDFs become available, or
   record an explicit release exception that scopes v1.0 to mature FY2025
   evidence.
2. When SSH/operator PC access is stable, side-by-side validate v493 on Windows
   before any active-lane promotion.
3. If an exception is approved, promote intentionally, run owner E2E with
   evidence collection and sign-off, then consider signed `v1.0` tagging.
4. If no exception is approved, do not promote owner sign-off as release-ready;
   keep v493 as Mac-side package evidence and v489 as Windows side-by-side
   evidence only.
