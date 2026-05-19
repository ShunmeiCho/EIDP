# Final Objective Audit - v500 Windows Side-by-Side State

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
Package source commit: `e79ac128cf7063b564f1b0c7c3bb89b6854e51e4`
Package: `dist/eidp-windows-v500.zip`
Package SHA256: `e8d1a736aa725e1a17a4b060daf62f19666ff51ccb0ccb19310d0062de1e42cf`

## Verdict

`NOT COMPLETE`.

v500 is the current package candidate. It has fresh package/source verification,
Windows side-by-side setup proof, OCR runtime proof, UI smoke proof, bounded
weekly canary proof, Excel export proof, Stage 6 evidence-bundle proof, and a
docs-only freshness gate at the current PR head.

This is still not v1.0 approval. The controlling business blocker remains the
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
9. The ship line is met: strict target-PDF/Excel-ready `>= 60%` and manual
   workload `<= 30%` for the current rolling FY.
10. The owner real Windows cycle and sign-off evidence are complete.

## Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds | `logs/win-v500-stage6-v500-non-windows-release-gates-20260520.json`: package verifier `returncode=0`, `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`; discovery gold checks returned `0` | PASS |
| 1,700+ specialty-school scope | `logs/win-v500-stage6-v500-env0-validate-after-setup-20260520.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit10-20260520.json`: `current_fy=2026`, `dry_run=false`, `status=success` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` keeps old-year fallback out of strict FY2026 success; `logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit10-20260520.json` reports `ship_gate_status=below_gate`, not a release pass | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`: after 607/1000 denominator schools, FY2026 documents were `0`; maximum possible strict yield was `39.3%`. v500 bounded canary yielded `50.0%` on 10 schools, but the larger fresh v500 limit-50 re-probe in `logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit50-20260520.json` yielded only `4.0%` strict/Excel-ready and `ship_gate_status=below_gate` | FAIL |
| Mature FY2025 strict proof for exception path | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: `ok=true`, FY2025 denominator `1000`, strict `60.0%`, Excel-ready `60.0%`, manual workload `20.2%` | PASS for exception input only |
| PDF extraction stack packaged | v500 package verifier in `logs/win-v500-stage6-v500-non-windows-release-gates-20260520.json`: `has_runtime=true`, `wheel_count=84`, package verify `returncode=0`; full unit suite returned `1880 passed` | PASS |
| Tesseract OCR runtime/add-on | `logs/win-v500-stage6-v500-validate-ocr-runtime-20260520.json`: `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present; core + add-on verifier `ok=true` in `logs/win-v500-stage6-v500-verify-windows-distribution-with-ocr-addon-20260520.json` | PASS |
| Confidence `>= 0.70` gating | `logs/win-v500-stage6-v500-non-windows-release-gates-20260520.json`: full `tests/unit` suite returned `1880 passed`, including confidence, ingest, review, Excel, OCR, and verifier unit tests. This proves code contract, not production OCR corpus yield | PASS for code/runtime, PARTIAL for production OCR corpus |
| Append-only business writes | Full unit suite returned `1880 passed`; validator confirms required tables include `department_yearly`, `support_recipient`, and `manual_action_log`. Owner real-cycle audit counts are not returned yet | PASS for code, PARTIAL for real workflow |
| Excel template transfer | `logs/win-v500-stage6-v500-excel-summary-20260520.json`: master workbook, competition workbook, and gap report exist; command log generated master rows and competition rows from the v500 Windows root | PASS |
| ManualActionLog audit | Full unit suite returned `1880 passed` and validator confirms `manual_action_log` table exists. Owner real-cycle audit counts/outbox proof are not returned yet | PARTIAL |
| ZIP distribution and offline setup | `logs/win-v500-stage6-v500-preflight-20260520.json`: Windows SHA/BUILD_INFO matched; `logs/win-v500-stage6-v500-first-setup-env0-20260520.log`: `first_setup.bat` completed with scheduler registration skipped; `logs/win-v500-stage6-v500-env0-validate-after-setup-20260520.json`: `ok=true` | PASS |
| Browser UI on Windows | `logs/win-v500-stage6-v500-ui-smoke-20260520.json`: `ok=true`, port `8521`, health `200/ok`, root `200`, stopped cleanly | PASS |
| Active scheduled task safety | `logs/win-v500-stage6-v500-recovery-probe-lock-after-canary-clean-20260520.json`: `ok=true`, active scheduled task still points to `%USERPROFILE%\\EIDP-v485-70e3db4\\scripts\\weekly_run.bat`, lock not held | PASS |
| Bounded Windows canary correctness | `logs/win-v500-stage6-v500-weekly-canary-limit10-run-20260520.log` contains `cli_args --limit 10 --json` and rc `0`; this proves the v499 CLI-argument forwarding bug is fixed | PASS |
| Fresh FY2026 limit-50 re-probe | `logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit50-20260520.json`: `status=success`, denominator `50`, strict/Excel-ready yield `4.0%`, operator-reviewable yield `56.0%`, `ship_gate_status=below_gate`; `docs/reports/2026-05-20-v500-limit50-rca.md`: 17/20 RCA items were `non_target_candidates_only`, 3/20 were `target_form_without_year_evidence`; `logs/win-v500-stage6-v500-recovery-probe-lock-after-limit50-canary-20260520.json`: `ok=true`, lock not held, active task still v485 | FAIL for release gate, PASS for recovery |
| Stage 6 evidence bundle | `logs/win-v500-stage6-v500-stage6-evidence-20260519-161653.zip`; SHA256 `674e2fdcaf6f09611c7ffd00ecff3c714a3913b6727478dac3df1917102e2a3e` | PASS |
| Stage 6 evidence verifier | `logs/win-v500-stage6-v500-stage6-evidence-verify-20260520-011707.json`: `ok=true`, required labels present | PASS |
| Package/source freshness | `logs/win-v500-stage6-v500-non-windows-release-gates-20260520.json`: package/source check fresh at package commit. Later docs-only commits require a `--allow-docs-only-stale-package` gate and should be recorded in the PR body rather than pinned here | PASS |
| PR mergeability | `gh pr view 2` reported `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, and checks `SUCCESS` during this audit. This audit intentionally avoids pinning a moving PR head; re-check before merge | PASS at audit time; re-check before merge |
| Publication-lag exception record | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED`, package candidate v500/SHA pinned | BLOCKED |
| Unapproved exception cannot pass return verifier | `logs/win-v500-stage6-v500-verify-stage6-return-not-approved-exception-20260520.json`: verifier exit code `1`, `ok=false`, and errors include `release exception record Status must be APPROVED` plus `release exception record Decision must be APPROVED` | PASS for negative gate |
| Owner real Windows cycle | v500 has bounded canary and Stage 6 bundle; owner real-cycle KPI table and sign-off are missing | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete, absent explicit release exception approval | BLOCKED |

## Verifier Coverage Notes

- `verify_windows_distribution.py` proves package structure, wheelhouse, build
  metadata, seed packaging, required scripts, Streamlit launcher guard,
  launcher repair hardening tokens, weekly scheduler retry tokens, weekly CLI
  forwarding tokens, competition template packaging, and OCR add-on integrity
  when passed `--ocr-addon`. It does not prove current-FY production yield or
  owner sign-off.
- `run_non_windows_release_gates.py` proves the full unit suite, validator
  tests, type/lint checks, discovery gold-set checks, package verification, and
  package/source freshness. It does not prove active-lane promotion or
  production KPI success.
- The v500 Windows side-by-side proof covers installation, OCR runtime,
  Streamlit health, bounded weekly execution, Excel output, active-task
  preservation, and Stage 6 bundle verification. It is still a bounded
  validation, not owner approval.
- The FY2025 mature-year proof is valid only as release-exception support. It
  must not be counted as strict FY2026/R8 ship proof.
- `verify_stage6_return.py` rejects the current `publication_lag` path while
  the exception record remains `NOT_APPROVED`, even when mature-year proof and
  v500 Stage 6 evidence verifier JSON are supplied.

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
