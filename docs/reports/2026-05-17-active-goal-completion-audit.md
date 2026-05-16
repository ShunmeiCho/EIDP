# Active Goal Completion Audit - EIDP Rolling Automation

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Verdict: **NOT COMPLETE**

This audit checks the active long-term objective against current artifacts. It
does not approve release, tag, merge, or mark the goal complete.

## Objective Restated

EIDP must let one Windows operator process 1,700+ Japanese vocational schools
each rolling fiscal year by:

1. Seeding school URLs from all 47 prefecture official lists.
2. Finding and downloading true target-FY institution-requirement confirmation
   PDFs in strict mode, excluding stale-year fallback from success.
3. Extracting rows with pdfplumber, PyMuPDF, and Tesseract OCR, writing only
   confidence >= 0.70 records into append-only `DepartmentYearly` and
   `SupportRecipient` paths.
4. Exporting the Excel template.
5. Auditing all operator actions in `ManualActionLog` and JSONL outbox.
6. Running from a Windows ZIP via double-click setup and browser UI.

The stated shipping line is strict target-form auto-acquisition of 60-70% and
operator manual workload of 30% or lower. Full automation is not required.

## Prompt-To-Artifact Checklist

| Requirement | Current strongest evidence | Audit result |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | `docs/reports/current-release-status.md` records all 47 seed artifacts in prior bounded/proof lanes; v459 URL-only bootstrap imported `48` seed URLs, inferred `296` corporation URLs, and later v460 bootstrap reached `school_site_count=1838`, `schools_with_url=1805`, `schools_with_verified_url=1312` | Partially proven. Packaged/proof evidence exists, but v460 owner-cycle KPI still unmeasured |
| Strict target-FY PDF discovery excludes stale fallback from success | Unit/gold-set coverage plus v463/v464 package lane; v459 bounded R7 weekly downloaded `2` target PDFs from `5` target-missing schools; v460 FY2026 Plan A selected no crawlable schools and second URL-rich FY2026 probe stopped without `last_run`; fresh source check `uv run pytest tests/unit/test_pdf_discovery.py -k "repeated_http_gets or cached_rejection"` returned `1 passed`, covering run-scoped shared-corporation HTTP GET caching | Mechanically guarded, but current FY2026/R8 production yield not proven |
| Extract confidence >= 0.70 rows only | OCR/package verifier contracts, confidence tests, v384 OCR copied-DB write proof, and historical v408/v384 append-only write proofs | Mechanically and sandbox-proven. No current strict R8 workload extraction proof |
| Append-only `DepartmentYearly` / `SupportRecipient` writes | Unit coverage plus v384/v407/v408 copied-DB manual-entry and fiscal-year override browser proofs | Sandbox-proven. No real v460 operator write cycle yet |
| Excel template export | v464 side-by-side FY2025/R7 browser Excel proof: `output/playwright/v464-r7-excel-smoke/summary.json ok=true`, workbook SHA256 `aff3dea57af4c6d96d8859e52748f8cecefb4e593f5da74b4f68646175937685`, sheet data rows `2418/10022/9719/9719`; v463 Mac retroactive matrix passed FY2025/FY2024/FY2023 | R7 historical/browser export and multi-year algorithm regression proven. FY2026/R8 production workbook still pending |
| ManualActionLog audits every operator action | v459 URL-candidate reject plus outbox flush sandbox, v408/v384 broader manual-entry/fiscal-year override/audit outbox browser proofs | Sandbox-proven. Real v460 operator-cycle audit delta still missing |
| ZIP distribution, double-click setup, offline browser UI | Active v460 root `C:\Users\cyo20\EIDP-v460-01e4427`; v460 setup, validation, recovery, read-only UI nav, docs staging, and Plan A evidence bundle all recorded. v464 side-by-side setup/UI/R7 Excel/evidence guard/return verifier/disk health also recorded. Scheduled task still points to v460 | Windows setup and support lanes proven. Real operator one-cycle still missing |
| Stage 6 evidence bundle verifier | v460 diagnostic bundle correctly rejected without `last_run`; v460 Plan A bundle verified `ok=true` after CLI weekly wrote `last_run`; v464 evidence guard correctly rejected setup/UI-only bundle; v464 return verifier rejected unfilled Plan A return | Verifier behavior proven. Final real-cycle return still missing |
| Strict target-form auto-acquisition 60-70% | v459 bounded R7 canary recorded `target_pdf_auto_yield_pct=40.0`; v460 Plan A recorded `target_pdf_auto_yield_pct=null`; second v460 URL-rich probe did not complete | **Failing / unproven** |
| Operator workload <=30% | v459 bounded R7 canary recorded `operator_reviewable_yield_pct=100.0`; v460 Plan A diagnostics reported `estimated_manual_workload_rate=1.0`; no owner timing/sign-off | **Failing / unproven** |
| Owner/operator sign-off | `docs/runbooks/eidp-v460-real-cycle-card.md` and `docs/runbooks/eidp-operator-e2e-template.md` define the return path | Missing |

## Current Lane Boundaries

- Active owner-cycle lane remains v460:
  `C:\Users\cyo20\EIDP-v460-01e4427`.
- `EIDP Weekly Run` still executes
  `C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat`.
- Latest support package is v464:
  `dist/eidp-windows-v464.zip`, package commit
  `9a94226b243fba691936db46c1fc11ef7c9debbd`, SHA256
  `6b95d9f3e06d70a0018119b2665070cf3af735e01b61920f6492234e174bd378`.
- Latest operator companion docs ZIP is
  `dist/eidp-v460-operator-docs-20260517.zip`; verify the generated artifact
  with its sidecar. It is expanded on Windows under
  `C:\EIDP-staging\v460-operator-docs-20260517`.
- No tag, no main merge, and no release approval has been made from these
  support proofs.

## Missing Gates

The goal is not achieved because the following remain missing:

- Owner/operator v460 real-cycle click-through.
- Final `data\output\last_run.json` from the real cycle.
- Verifier-accepted final Stage 6 evidence ZIP from the real cycle.
- Filled `docs/runbooks/eidp-operator-e2e-template.md` return rows.
- Measured `target_pdf_auto_yield_pct`.
- Measured `operator_reviewable_yield_pct` and workload <=30% evidence.
- Audit/outbox delta from the real operator cycle.
- Owner and operator sign-off.

## Next Concrete Gate

The next release-relevant action is still the owner/operator v460 real-cycle
and return-artifact verification. Local side-by-side support work can continue,
but it must not be counted as completion unless it produces the missing
real-cycle KPI, evidence ZIP, and sign-off artifacts above.
