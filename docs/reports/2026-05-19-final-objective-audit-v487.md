# Final Objective Audit - v487 Side-by-side State

Date: 2026-05-19
Branch: `sprint8-handoff-finalize`
PR: `#2`
PR head at audit time: `fb04db6d23ad39c2ccee016b4103da16cb074049`

## Verdict

`NOT COMPLETE`.

v487 is a valid Windows side-by-side package candidate, but it is not proof that
the final rolling-FY objective is complete. The current blocking issue remains
the FY2026/R8 production-scale strict-yield gate: available public PDFs do not
yet support a 60% strict current-FY target-PDF/excel-ready claim.

Do not tag `v1.0`, merge to `main`, or request owner sign-off under the strict
FY2026 contract unless an explicit release exception is approved.

## Success Criteria

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

| Requirement | Evidence | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds | `data/prefecture-aggregators/seed.csv`: 47 rows, all with `artifact_url`; v487 verifier `logs/win-v487-stage6-v487-verify-windows-distribution-20260519.json` returned `ok=true` | PASS |
| 1,700+ specialty-school scope | v487 Windows setup validator `logs/win-v487-stage6-v487-validate-after-setup-20260519.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `docs/reports/2026-05-19-fy2026-strict-yield-no-go.md`; no-go proof targets `target_fiscal_year=2026` | PASS |
| Strict current-FY PDF success excludes old-year fallback | No-go proof found `discovered_fy2026_documents=0` after 607/1000 schools; FY2025 docs were not counted as FY2026 success | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`: max possible strict yield after mathematical failure bound is `39.3%` | FAIL |
| Mature FY2025 strict proof | `_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json`: FY2025 denominator 1000, strict `60.0%`, excel-ready `60.0%`, manual workload `20.2%` | PASS for mature-year algorithm evidence only |
| PDF extraction stack | v487 package verifier passed; source package includes `src/eidp/pdf/extractor.py`, OCR paths, and confidence modules | PASS |
| Confidence `>= 0.70` gating | CI and local release gate passed tests for confidence routing; `scripts/run_non_windows_release_gates.py` output `ok=true` in `logs/win-v487-stage6-v487-non-windows-release-gates-20260519.json` | PASS for tested code path |
| Append-only business writes | Existing unit coverage and CI passed; not re-proven by v487 owner cycle because owner cycle is incomplete | PARTIAL |
| Excel template transfer | `logs/release-gate-v485-retroactive-matrix.json`: `ok=true`, `case_count=3`; this is retroactive/mature-year evidence, not FY2026 owner-cycle output | PARTIAL |
| ManualActionLog audit | CI passed relevant tests; owner real-cycle audit evidence remains incomplete | PARTIAL |
| ZIP distribution and offline setup | v487 ZIP SHA256 `552ae87354b0e0f11d9a2dcb6a47f85bd43334cdac613b78a7860bf44af7d514`; `BUILD_INFO.git_commit=5893393`, `git_dirty=false`; Windows setup `rc=0`; validator `ok=true` | PASS |
| Browser UI on Windows | v487 has setup validation only; earlier v485 UI smoke exists, but v487 browser UI was not smoked after side-by-side setup in this audit | PARTIAL |
| Active scheduled task safety | v487 setup was run with `EIDP_REGISTER_WEEKLY_TASK=0`; recovery check `logs/win-v487-stage6-v487-recovery-expected-v485-20260519.json` returned `ok=true`, `action_matches_expected=true`; active task stayed on v485 | PASS |
| PR mergeability | PR #2 head `fb04db6`; GitHub `Python quality gates` and `Ship gate contract` both success; `mergeStateStatus=CLEAN` | PASS |
| Owner real Windows cycle | Latest owner evidence remains incomplete; active v485 DB previously had `school_site_count=0` and `document_count=0`; owner must run initial bootstrap before weekly cycle | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete | BLOCKED |

## Verifier Coverage Notes

- `verify_windows_distribution.py` proves package structure, wheelhouse,
  build metadata, and required packaged files. It does not prove FY2026 strict
  target-PDF yield or owner workflow completion.
- `run_non_windows_release_gates.py` proves Mac-side tests, type/lint/security
  gates, discovery gold-set checks, and package verification. It does not prove
  Windows active-lane promotion or real operator E2E.
- Windows `validate_install.bat --after-setup --json` proves extracted install
  health, SQLite integrity, school count, and wheel count. It does not prove
  PDF discovery, extraction, Excel output, or owner sign-off.
- The FY2025 strict replay proves mature-year algorithm capability. It must not
  be used as current FY2026 ship proof.
- The FY2026 upper-bound proof is the controlling current-FY evidence and is
  below gate.

## Required Next Actions

1. Decide whether v1.0 is blocked until FY2026 public PDFs become available, or
   record an explicit release exception that scopes v1.0 to mature FY2025
   evidence.
2. If an exception is approved, promote a current package intentionally and run
   owner E2E with evidence collection and sign-off.
3. If no exception is approved, do not promote owner sign-off as release-ready;
   keep v487 as side-by-side validated package evidence only.

