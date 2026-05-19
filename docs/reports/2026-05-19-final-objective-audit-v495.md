# Final Objective Audit - v495 Mac-side State

Date: 2026-05-19
Branch: `sprint8-handoff-finalize`
PR: `#2`
PR status source: use live `gh pr view 2`; this audit does not pin the
moving docs-only PR head.
Mac package: `dist/eidp-windows-v495.zip`
Package source commit: `37b5118d3bf9a9a50b281ec0d87bedcf2242d475`

## Verdict

`NOT COMPLETE`.

v495 is the current Mac-side package/source-verified candidate, and PR #2 is
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
| 47 prefecture official-list seeds | `logs/win-v495-stage6-v495-verify-windows-distribution-20260519.json`: `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47` | PASS |
| 1,700+ specialty-school scope | v489 Windows setup validator `logs/win-v489-stage6-v489-validate-after-setup-20260519.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `docs/reports/2026-05-19-fy2026-strict-yield-no-go.md`; no-go proof targets `target_fiscal_year=2026` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`: after `607/1000`, FY2026 discovered documents were `0`; FY2025/R7 PDFs were not counted as FY2026 success | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | Same proof: maximum possible strict yield after the mathematical failure bound is `39.3%` | FAIL |
| Mature FY2025 strict proof | `_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json`: FY2025 denominator `1000`, strict `600/1000 (60.0%)`, excel-ready `600/1000 (60.0%)`, manual workload `20.2%` | PASS for mature-year algorithm evidence only |
| Verifier-accepted mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v495-20260519.json`: `ok=true`, basis `mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition`, FY2025 denominator `1000`, strict `60.0%`, Excel-ready `60.0%`, manual workload `20.2%` | PASS for release-exception proof input |
| PDF extraction stack | v495 package verifier passed; package includes the project wheel and runtime, with `wheel_count=84`, `entry_count=3104`, and `has_runtime=true` | PASS |
| Confidence `>= 0.70` gating | v495 non-Windows gate `logs/win-v495-stage6-v495-non-windows-release-gates-20260519.json` returned `ok=true`; validator/distribution subset passed with package/source freshness | PASS for tested code path |
| Append-only business writes | PR #2 CI passed; local focused checks passed after the fiscal-year override `FOR UPDATE` hardening. This is code/test evidence, not owner-cycle evidence | PASS for code contract, PARTIAL for real workflow |
| Excel template transfer | `logs/release-gate-v485-retroactive-matrix.json`: `ok=true`, `case_count=3`; this is retroactive/mature-year evidence, not FY2026 owner-cycle output | PARTIAL |
| ManualActionLog audit | PR #2 CI passed relevant tests; owner real-cycle audit evidence remains incomplete | PARTIAL |
| ZIP distribution and offline setup | `dist/eidp-windows-v495.zip`, SHA256 `e55c1b2de2b74181f9d29120ba9b074c5d14c82bf4d74ef41c07ff8e84e623c8`; `BUILD_INFO.git_dirty=false`; Mac package verifier `ok=true` | PASS for Mac-side package, PENDING for Windows side-by-side |
| Browser UI on Windows | Latest Windows UI smoke remains v489: `logs/win-v489-stage6-v489-ui-smoke-20260519.json` returned `ok=true`, health `200/ok`, root `200`, stopped cleanly | PASS for v489, PENDING for v495 |
| Active scheduled task safety | v489 recovery check `logs/win-v489-stage6-v489-recovery-expected-v485-20260519.json`: `ok=true`, `action_matches_expected=true`; active task stayed on v485 | PASS |
| v485 `streamlit.main` launcher issue | `docs/runbooks/eidp-windows.md` documents `No module named streamlit.main` and a non-SSH hotfix; `docs/runbooks/eidp-operator-e2e-template.md` checks launcher entrypoint before UI smoke; local ZIP inspection on 2026-05-19 confirmed the current package `scripts/launch.bat` uses `-m streamlit run` and ships the repair helper | PASS for runbook/package, PENDING for Win-side applied repair |
| PR mergeability | Live `gh pr view 2` / PR body are the current source of truth. Before this audit cleanup, PR #2 was `CLEAN` and required checks `Python quality gates` / `Ship gate contract` were `SUCCESS`; any newer commit must rerun those checks before merge | PASS |
| Package/source freshness | v495 package was built from `37b5118d3bf9a9a50b281ec0d87bedcf2242d475`. `logs/win-v495-stage6-v495-non-windows-release-gates-20260519.json`: `package_source_check.ok=true`, `source_dirty=false`, `stale=false`. After v495 evidence docs, `logs/win-v495-stage6-v495-non-windows-release-gates-docs-only-head-20260519.json` returned `ok=true`, `docs_only_stale=true`, `allowed_stale_reason=docs_only` | PASS |
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
  on the operator PC. It does not prove v495 Windows operability.
- The FY2025 strict replay proves mature-year algorithm capability. It must not
  be used as current FY2026 ship proof.
- A publication-lag release exception also requires a verifier-accepted
  mature-year proof JSON. v495 adds an explicit strict-gap-analysis input path
  to `scripts/build_mature_year_acquisition_proof.py`; the generated FY2025
  proof JSON is now available at
  `logs/mature-year-acquisition-proof-fy2025-release-exception-v495-20260519.json`.
- The FY2026 upper-bound proof is the controlling current-FY evidence and is
  below gate.

## Earlier v493 Non-SSH Follow-up Evidence

SSH/Windows access was intentionally avoided after the v493/v494/v495 audit because the
operator PC connection was at risk of dropping. The following Mac-side checks
were re-run against v493 without touching the Windows active lane. v495 package
verification and source-freshness evidence are recorded in the checklist above.

- `unzip -p dist/eidp-windows-v493.zip scripts/launch.bat` confirmed the ZIP
  launcher uses `"%VENV_PY%" -m streamlit run`, not `streamlit.main`.
- `unzip -l dist/eidp-windows-v493.zip` confirmed
  `EIDP-repair-launcher.bat`, `scripts/repair_streamlit_launcher.bat`,
  `scripts/repair_streamlit_launcher.py`, `.streamlit/config.toml`, and
  `scripts/launch.bat` are packaged.
- `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v493.zip --json` returned `ok=true`; rerun output is
  recorded at
  `logs/win-v493-stage6-v493-verify-windows-distribution-rerun-20260519.json`.
- `uv run pytest tests/unit/test_repair_streamlit_launcher.py
  tests/unit/test_windows_install_validator.py::test_validate_after_weekly_warns_on_legacy_ship_gate_basis
  tests/unit/test_stage6_return_verifier.py -q` returned `16 passed`.
- `uv run pytest
  tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_rejects_legacy_streamlit_main_launcher
  -q` returned `1 passed`.
- `uv run pytest tests/unit/test_cli_write_lock_contract.py
  tests/unit/test_audit_outbox.py tests/unit/test_review_audit_log.py -q`
  returned `32 passed`.
- `uv run pytest
  tests/unit/test_review_fiscal_year_override.py::test_override_with_lock_locks_yearly_rows_before_rewrite
  -q` returned `1 passed`.
- `uv run --with bandit bandit -q --severity-level high -r src/eidp`
  returned `0`.

## Required Next Actions

1. Keep v1.0 blocked until FY2026/R8 public target PDFs become available, or
   record an explicit release exception that scopes v1.0 to mature FY2025
   evidence.
2. When SSH/operator PC access is stable, side-by-side validate v495 on Windows
   before any active-lane promotion.
3. If an exception is approved, promote intentionally, run owner E2E with
   evidence collection and sign-off, then consider signed `v1.0` tagging.
4. If no exception is approved, do not promote owner sign-off as release-ready;
   keep v495 as Mac-side package evidence and v489 as Windows side-by-side
   evidence only.
