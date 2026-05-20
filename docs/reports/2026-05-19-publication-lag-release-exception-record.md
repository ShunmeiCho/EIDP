# Publication-Lag Release Exception Record

Date: 2026-05-19
Last evidence refresh: 2026-05-20
Status: `NOT_APPROVED`
Package candidate: `dist/eidp-windows-v523.zip`
Package SHA256: `5d47ca9e016aa6aadf3608b5799c773a769af585d158813eada1f80cebe762ce`

This record is the explicit approval artifact required before EIDP v1.0 can
ship under the `publication_lag` exception path. Until the approval fields are
filled and signed, this file is a template only and does not unblock release.

## Approval

| Field | Value |
| --- | --- |
| Exception reason | `publication_lag` |
| Decision | `NOT_APPROVED` |
| Approver |  |
| Approval date |  |
| Release scope | v1.0 may ship on mature FY2025 production-scale proof only |
| FY2026/R8 status acknowledged |  |
| Required follow-up | Re-run FY2026/R8 strict-yield upper-bound proof when R8 target-form publication baseline exists |

Required acknowledgement text:

```text
I acknowledge that FY2026/R8 strict current-year target-PDF yield is below the
60% release gate as of 2026-05-20, and that v1.0 approval under this exception
is scoped to mature FY2025 production-scale evidence. This exception does not
claim FY2026/R8 strict-yield success and does not waive owner real-cycle
evidence or Stage 6 return verification.
```

## Evidence Packet

| Evidence | Artifact | Current status |
| --- | --- | --- |
| FY2026/R8 no-go upper bound | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` | required |
| FY2026/R8 RCA | `logs/win-v485-stage6/fy2026-strict-yield-rca-20260519.json` | required |
| 2026-hint sample probe | `logs/win-v485-stage6/fy2026-current-hint-target-samples-20260519.json` | required |
| Mature FY2025 strict replay | `_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json` | required |
| Verifier-accepted mature-year proof | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` | `ok=true` |
| v523 package/non-Windows release gates | `logs/win-v523-stage6-v523-non-windows-release-gates-20260520.json` | `ok=true`, full unit `1897 passed` |
| v523 owner-request docs-only release gates | `logs/win-v523-stage6-v523-owner-request-docs-only-gates-20260520.json` | `ok=true`, `docs_only_stale=true`, full unit `1897 passed` |
| v523 package/source report | `docs/reports/2026-05-20-v523-current-head-package.md` | current package/source proof |
| v523 Windows side-by-side evidence | `docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md` | latest complete Windows side-by-side proof; FY2026/R8 strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` |
| v523 owner/operator request | `docs/runbooks/eidp-v523-owner-request-20260520.txt` | prepared; not approval |
| v501 Windows side-by-side evidence | `docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md` | historical complete Windows side-by-side proof |
| v502 Windows side-by-side evidence | `docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md` | historical partial proof |
| v503 settings-audit package report | `docs/reports/2026-05-20-v503-settings-audit-package.md` | historical Mac-side package/source proof |
| v504 Excel-preview audit package report | `docs/reports/2026-05-20-v504-excel-preview-audit-package.md` | historical Mac-side package/source proof |
| v505 school-task rebuild audit package report | `docs/reports/2026-05-20-v505-school-task-rebuild-audit-package.md` | historical Mac-side package/source proof |
| v506 operator URL audit package report | `docs/reports/2026-05-20-v506-operator-url-audit-package.md` | historical Mac-side package/source proof |
| v507 prefecture remark audit package report | `docs/reports/2026-05-20-v507-prefecture-remark-audit-package.md` | historical Mac-side package/source proof |
| v508 Excel export audit package report | `docs/reports/2026-05-20-v508-excel-export-audit-package.md` | historical Mac-side package/source proof |
| v509 audit-log filter package report | `docs/reports/2026-05-20-v509-audit-log-filter-package.md` | historical Mac-side package/source proof |
| v510 school alias audit package report | `docs/reports/2026-05-20-v510-school-alias-audit-package.md` | historical Mac-side package/source proof |
| v511 proposal decision audit package report | `docs/reports/2026-05-20-v511-proposal-decision-audit-package.md` | historical Mac-side package/source proof |
| v512 bug-report audit package report | `docs/reports/2026-05-20-v512-bug-report-audit-package.md` | historical Mac-side package/source proof |
| v513 Sanko disclosure probe package report | `docs/reports/2026-05-20-v513-sanko-disclosure-probe-package.md` | historical Mac-side package/source proof |
| v514 weekly selected-site count package report | `docs/reports/2026-05-20-v514-weekly-selected-site-count-package.md` | historical Mac-side package/source proof |
| v514 Mac continuation canary | `docs/reports/2026-05-20-v514-mac-continuation-canary.md` | FY2026/R8 strict `2/50 (4.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate` |
| v515 Sanko child override package report | `docs/reports/2026-05-20-v515-sanko-child-overrides-package.md` | `ok=true` Mac-side package/source proof; FY2026/R8 strict `2/50 (4.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` |
| v516 target-missing selection package report | `docs/reports/2026-05-20-v516-weekly-target-missing-selection-package.md` | `ok=true` Mac-side package/source proof; already confirmed current-FY targets no longer re-enter target-missing queue |
| v517 remaining Sanko child override package report | `docs/reports/2026-05-20-v517-remaining-sanko-child-overrides-package.md` | `ok=true` Mac-side package/source proof; school ID 55 moves from corporation-only non-target evidence to FY2019-FY2025 publication-lag evidence |
| v518 gold-set publication-lag package report | `docs/reports/2026-05-20-v518-gold-set-publication-lag-package.md` | `ok=true` Mac-side package/source proof; school ID 55 publication-lag behavior is now a packaged gold-set regression case |
| v519 vocational-practice basic-info filter package report | `docs/reports/2026-05-20-v519-vocational-practice-basic-info-filter-package.md` | `ok=true` Mac-side package/source proof; current-year-hint vocational-practice basic-info PDFs classify as `non_target` |
| v519 Mac limit-50 continuation canary | `docs/reports/2026-05-20-v519-mac-limit50-continuation-canary.md` | strict FY2026/R8 `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, URL-source overrides loaded, `ship_gate_status=below_gate` |
| v520 Katayanagi URL boundary package report | `docs/reports/2026-05-20-v520-katayanagi-url-boundary-package.md` | `ok=true` Mac-side source proof; exact Katayanagi crawl entries added without counting NEEC no-year PDFs as current-FY strict success; full unit `1895 passed` |
| v521 school-override corporation suppression package report | `docs/reports/2026-05-20-v521-school-override-corporation-suppression-package.md` | `ok=true` Mac-side source proof; exact school-domain overrides now suppress same-school corporation roots in default discovery scope; full unit `1896 passed` |
| v521 Mac limit-50 continuation canary | `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md` | strict FY2026/R8 `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, URL-source overrides loaded, `candidate_school_mismatch=0`, `ship_gate_status=below_gate` |
| v522 stale-yearless RCA bucket source report | `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md` | `ok=true` Mac-side source proof; reclassifies Sanko school ID 44 from no-year RCA to publication-lag RCA; full unit `1897 passed` |
| v522 same-domain FY2026 negative probe | `docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md` | no simple same-domain FY2026/R8 replacement found; 47 expanded candidates returned `404` by HEAD and ranged GET |
| current objective checklist | `docs/reports/eidp-current-objective-evidence-checklist.md` | `NOT COMPLETE`; still blocks on FY2026/owner cycle/approval |
| Owner E2E template | `docs/runbooks/eidp-operator-e2e-template.md` | must be completed after approval |

## Current Negative Verifier Check

The refreshed v523 exception packet was checked against
`scripts/verify_stage6_return.py` while this record remained `NOT_APPROVED`.
The verifier correctly rejected release approval:

- output JSON:
  `logs/win-v523-stage6-v523-verify-stage6-return-not-approved-exception-20260520.json`
- return code:
  `logs/win-v523-stage6-v523-verify-stage6-return-not-approved-exception-20260520.rc`
- observed rc: `1`
- observed `ok`: `false`
- expected blocking errors included:
  `release exception record Status must be APPROVED`,
  `release exception record Decision must be APPROVED`,
  placeholder approver/date/acknowledgement rows, and missing owner/operator
  sign-off fields.

## Return Verification

After owner real-cycle evidence is returned, release approval still requires:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template <filled-owner-e2e-template.md> \
  --last-run <returned-data-output-last_run.json> \
  --evidence-verify-json <returned-stage6-evidence-verify.json> \
  --release-exception-reason publication_lag \
  --mature-year-proof-json logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json \
  --release-exception-record docs/reports/2026-05-19-publication-lag-release-exception-record.md \
  --json
```

The release remains blocked if this command exits non-zero, if owner/operator
sign-off is missing, or if this exception record remains `NOT_APPROVED`.
