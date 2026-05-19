# FY2026 Strict-Yield No-Go Evidence

Date: 2026-05-19  
Branch: `sprint8-handoff-finalize`  
Source package lane: `v485` active on the Windows operator PC

## Verdict

Do not proceed to v1.0 merge, tag, or owner sign-off under the strict current-FY
FY2026/R8 contract.

The current 60% strict target-PDF / Excel-ready ship line is mathematically
unreachable in the latest sandbox replay. After `607/1000` denominator schools,
the replay had discovered `0` FY2026 target documents. Even if every remaining
school passed, the maximum possible strict yield would be `39.3%`.

## Evidence

Local source artifacts:

- `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`
- `logs/win-v485-stage6/fy2026-strict-yield-rca-20260519.json`
- `logs/win-v485-stage6/fy2026-current-hint-target-samples-20260519.json`
- `logs/win-v485-stage6/final-objective-audit-current.json`

The replay used a sandbox copy of the URL-rich DB and did not modify the active
Windows operator DB.

Key metrics:

| Metric | Value |
| --- | ---: |
| Denominator | `1000` |
| Processed before mathematical failure bound | `607` |
| Latest school ID observed | `661` |
| FY2026 documents discovered | `0` |
| Remaining schools | `393` |
| Best-case final strict yield | `39.3%` |
| Required strict yield | `60.0%` |

Top rejection buckets:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | `8589` |
| `classified_non_target` | `1537` |
| `candidate_school_mismatch` | `958` |
| `fiscal_year_mismatch:2025` | `758` |
| `candidate_budget_dropped` | `645` |
| `fiscal_year_mismatch:2024` | `465` |
| `target_fiscal_year_not_detected` | `237` |
| `fiscal_year_mismatch:2023` | `131` |

For candidates with a `2026` / R8 hint in the URL or anchor text, the top buckets
were still non-target materials and old-year target forms:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | `2073` |
| `candidate_school_mismatch` | `243` |
| `candidate_budget_dropped` | `242` |
| `classified_non_target` | `61` |
| `fiscal_year_mismatch:2025` | `61` |
| `fiscal_year_mismatch:2024` | `54` |
| `target_fiscal_year_not_detected` | `8` |

## 2026-Hint Sample Probe

Four `2026`-path target-looking PDFs from the Kawahara group were downloaded
for a direct text probe. All four extracted only `令和6年度`, not FY2026/R8.
This confirms that URL upload path or timestamp is not safe fiscal-year
evidence.

| School ID | Probe result |
| ---: | --- |
| `389` | `令和6年度` |
| `389` | `令和6年度` |
| `389` | `令和6年度` |
| `391` | `令和6年度` |

## RCA

The observed failure is not a v485 packaging, Windows deployment, or CI problem.
The pipeline is finding many target-form PDFs, but they are overwhelmingly
FY2025/R7 or earlier. Many FY2026/R8-hinted PDFs are governance disclosures,
school information, syllabi, brochures, or other non-target materials.

Secondary algorithm work remains valuable, especially around
`target_fiscal_year_not_detected`, image-only/OCR handling, and dense-page
candidate ranking. Based on this replay, those secondary buckets are not large
enough to close the current FY2026 gap to 60% by themselves.

## Required Decision

Choose one path before requesting owner E2E or tagging v1.0:

1. Keep v1.0 blocked under the rolling FY2026/R8 contract until enough public
   current-year target PDFs exist.
2. Record an explicit release exception that scopes v1.0 to mature-year FY2025
   proof, then run owner E2E under that exception.

Without one of those decisions, the final objective audit remains `ok=false`.

## Publication-Lag Exception Approval Packet

Default decision: no exception. Under the strict rolling-FY contract, v1.0 stays
blocked until FY2026/R8 public target-form PDFs become available at enough
schools to meet the 60% strict Excel-ready gate.

The only supported exception reason is `publication_lag`. It is a release-scope
decision, not an algorithm pass. If approved, it means:

- v1.0 release evidence is scoped to mature-year FY2025 production-scale proof.
- FY2026/R8 strict yield remains explicitly below gate and must not be described
  as passed.
- FY2026/R8 current-year public-PDF availability remains a v1.1 follow-up gate.
- Owner E2E still has to run and produce measured KPI rows; the exception does
  not allow blank KPI values, `not_measured`, or missing evidence.

Minimum approval record:

| Field | Required value |
| --- | --- |
| Exception reason | `publication_lag` |
| Approver | named owner / release decision maker |
| Approval date | calendar date |
| Scope | v1.0 may ship on mature FY2025 proof only |
| FY2026 status | explicit acknowledgement: current FY2026 strict yield is below gate |
| Follow-up | FY2026/R8 strict-yield re-probe when public forms are seasonally available |

Required evidence before owner E2E under the exception:

| Evidence | Current artifact |
| --- | --- |
| FY2026 no-go proof | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` |
| FY2026 RCA | `logs/win-v485-stage6/fy2026-strict-yield-rca-20260519.json` |
| 2026-hint direct PDF probe | `logs/win-v485-stage6/fy2026-current-hint-target-samples-20260519.json` |
| Mature-year strict replay evidence | `_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json` |
| Verifier-accepted mature-year proof JSON | not yet archived; must be generated before exception approval |
| Owner E2E template | `docs/runbooks/eidp-operator-e2e-template.md` |

The FY2025 strict replay evidence above proves the `600/1000 (60.0%)`
algorithm result, but it is a `strict_yield_gap_analysis` artifact. It is not
the mature-year proof schema consumed by `scripts/verify_stage6_return.py`.
Before an exception can approve release, a separate mature-year proof JSON with
`basis=mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition`
and `ok=true` must be generated and archived.

Mature-year proof generation command:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=<mature-year-weekly-last_run.json> \
  --output logs/mature-year-acquisition-proof-fy2025-release-exception.json \
  --json
```

Owner E2E template rows that must be filled when the exception is used:

| Row | Expected actual |
| --- | --- |
| `release exception reason` | `publication_lag` |
| `mature-year proof JSON` | path to the FY2025 mature-year proof JSON |
| `mature-year proof years` | at least one fiscal year before FY2026 |
| strict target PDF 自動取得率 | measured value, or `watch` under the approved exception |
| Excel ready 率 | measured value, or `watch` under the approved exception |
| 推定手作業率 | measured value, or `watch` under the approved exception |

Return verification command after owner E2E evidence is collected:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template <filled-owner-e2e-template.md> \
  --last-run <returned-data-output-last_run.json> \
  --evidence-verify-json <returned-stage6-evidence-verify.json> \
  --release-exception-reason publication_lag \
  --mature-year-proof-json logs/mature-year-acquisition-proof-fy2025-release-exception.json \
  --json
```

The release remains blocked if this verifier exits non-zero, if owner sign-off
is missing, or if the exception approval record is absent. A signed `v1.0` tag
is only allowed after the return verifier passes and the owner evidence bundle
is archived.
