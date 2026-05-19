# Publication-Lag Release Exception Record

Date: 2026-05-19
Status: `NOT_APPROVED`
Package candidate: `dist/eidp-windows-v504.zip`
Package SHA256: `9329630e7026c3e568bf78643f4a0e6e0941d4d695030dfdb362e1dc2f20439f`

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
60% release gate as of 2026-05-19, and that v1.0 approval under this exception
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
| v504 package/non-Windows release gates | `logs/win-v504-stage6-v504-non-windows-release-gates-20260520.json` | `ok=true` |
| v501 Windows side-by-side evidence | `docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md` | latest complete Windows side-by-side proof |
| v502 Windows side-by-side evidence | `docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md` | partial proof; full smoke pending SSH recovery |
| v503 settings-audit package report | `docs/reports/2026-05-20-v503-settings-audit-package.md` | `ok=true` Mac-side package/source proof; Windows smoke pending |
| v504 Excel-preview audit package report | `docs/reports/2026-05-20-v504-excel-preview-audit-package.md` | `ok=true` Mac-side package/source proof; Windows smoke pending |
| current objective checklist | `docs/reports/eidp-current-objective-evidence-checklist.md` | `NOT COMPLETE`; still blocks on FY2026/owner cycle/approval |
| Owner E2E template | `docs/runbooks/eidp-operator-e2e-template.md` | must be completed after approval |

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
