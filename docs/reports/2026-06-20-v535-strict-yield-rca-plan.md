# v535 Strict-Yield RCA Plan

Date: 2026-06-20
Candidate: `v535`
Release conclusion: `NOT_READY`

## Scope

This report decomposes the v535 Windows limit-50 canary blocker into concrete
operator and engineering lanes. It is not a release approval and does not relax
the current FY2026/Reiwa 8 strict evidence rules.

The evidence source is the v535 Stage 6 bundle:

```text
logs/win-v535-stage6/stage6-evidence-20260620-053032.zip
```

The relevant files inside the bundle are:

```text
data/output/last_run.json
data/output/target-year-discovery/20260620_051853-discovery-rejections.jsonl
data/output/target-year-discovery/20260620_051853-discovery-rca-batch-plan.json
```

The same summary is now machine-reproducible with:

```bash
uv run python scripts/summarize_stage6_rca.py logs/win-v535-stage6/stage6-evidence-20260620-053032.zip --json
```

The verifier returns `ok=true`, confirms required evidence labels
`build_info`, `diagnostics`, `last_run`, `discovery_evidence`, and
`discovery_rca`, and keeps the strict-yield conclusion at `BELOW_GATE`.

## Current-State Audit

| Classification | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield is below the release gate. | v535 `last_run.json`: `12/50 (24.0%)`, `ship_gate_status=below_gate` |
| P0 release blocker | Owner real Windows cycle/sign-off is missing. | `docs/reports/current-release-status.md` and owner handoff docs remain request/return templates, not returned sign-off evidence |
| P0 release blocker | `publication_lag` release exception is not approved. | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `NOT_APPROVED` |
| P0 release blocker | v535 OCR scope is unresolved. | v535 has complete non-OCR Windows smoke; latest complete OCR runtime proof is still older than v535 |
| P1 release hardening | v535 owner docs are staged and checked on Windows. | `docs/reports/2026-06-20-v535-owner-docs-windows-staging.md` |
| P2 documentation/demo drift | `.codegraph/` and `.understand-anything/` are local untracked generated directories. | Local `du`: about `17M` and `26M`; not staged |
| P3 roadmap/research | University production workflow remains out of v1 scope. | v1 scope remains `専門学校` priority; MEXT university index package gate is evidence only |

## Canary Result

The v535 Windows canary ran in target-missing mode for `50` schools:

```text
strict_target_pdf_auto_acquired_count=12
target_pdf_excel_ready_acquired_count=12
target_pdf_auto_denominator_count=50
target_pdf_excel_ready_yield_pct=24.0
operator_reviewable_count=47
operator_reviewable_yield_pct=94.0
ship_gate_status=below_gate
```

Discovery/ingest did run successfully:

```text
crawled=59
found=50
downloaded=15
processed=15
departments_created=122
yearly_upserted=129
```

So the P0 problem is not a dead pipeline. It is that most discovered evidence
is not safe to count as current FY2026/R8 Excel-ready data.

## RCA Batch Buckets

The Stage 6 RCA batch contains `20` school packets and `524` candidate rows.
The RCA file header also has `total_candidates=35`; this is not the release
denominator and should not be used as the school-level candidate-row total.

| Bucket | Schools | Candidate rows | Release interpretation |
| --- | ---: | ---: | --- |
| `publication_lag_or_old_target_pdf` | 15 | 454 | Current strict success cannot be raised without an approved publication-lag exception or newly published FY2026/R8 target evidence. |
| `target_form_without_year_evidence` | 2 | 10 | Candidate target forms exist, but year evidence is insufficient. Route to operator year review; do not auto-accept from download time or vague page context. |
| `school_identity_mismatch` | 2 | 48 | Candidate evidence may be from a sibling/corporate site. Fix source mapping or require operator identity confirmation before use. |
| `non_target_candidates_only` | 1 | 12 | Official site was reached but only non-target candidates were found. Needs bounded same-domain disclosure search or manual URL entry. |

Rejection reason totals from the v535 evidence log:

| Reason | Count | Interpretation |
| --- | ---: | --- |
| `pre_filtered_non_target_hint` | 432 | Mostly non-target PDFs and disclosure attachments correctly excluded before download. |
| `classified_non_target` | 103 | Downloaded/classified non-target documents correctly excluded. |
| `fiscal_year_mismatch:2025` | 32 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2024` | 30 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2023` | 29 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2022` | 30 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2021` | 28 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2020` | 30 | Old-year target forms; cannot be counted as R8. |
| `fiscal_year_mismatch:2019` | 27 | Old-year target forms; cannot be counted as R8. |
| `accepted_downloaded` | 15 | Downloaded candidates; 12 became Excel-ready. |
| `no_candidates_found` | 9 | No usable candidate path found. |
| `target_fiscal_year_not_detected` | 6 | Target-form-like PDF without machine-verifiable target-year evidence. |
| `pdf_school_mismatch` | 2 | Candidate document identity does not match the school. |
| `http_error:HTTPStatusError` | 1 | Site or document fetch failure. |

## School-Level Action Queue

| School ID | School | Bucket | Candidate rows | Registered source |
| ---: | --- | --- | ---: | --- |
| 1 | 日本工学院専門学校 | `target_form_without_year_evidence` | 5 | `https://www.neec.ac.jp/portal/public/mext-scholarship/` |
| 2 | 日本工学院八王子専門学校 | `target_form_without_year_evidence` | 5 | `https://www.neec.ac.jp/portal/public/mext-scholarship/` |
| 41 | 大宮ビューティ＆ブライダル専門学校 | `non_target_candidates_only` | 12 | `https://www.sanko.ac.jp/omiya-beauty/` |
| 25 | 福岡医療秘書福祉専門学校 | `school_identity_mismatch` | 25 | `https://www.sanko.ac.jp/fukuoka-med/` |
| 20 | 横浜医療秘書専門学校 | `school_identity_mismatch` | 23 | `https://www.sanko.ac.jp/yokohama-med/` |
| 43 | 東京ビューティアート専門学校 | `publication_lag_or_old_target_pdf` | 42 | `https://www.sanko.ac.jp/tokyo-beauty/` |
| 42 | 千葉ビューティ＆ブライダル専門学校 | `publication_lag_or_old_target_pdf` | 40 | `https://www.sanko.ac.jp/chiba-beauty/` |
| 47 | 大阪ビューティアート専門学校 | `publication_lag_or_old_target_pdf` | 34 | `https://www.sanko.ac.jp/osaka-beauty/` |
| 3 | 日本工学院北海道専門学校 | `publication_lag_or_old_target_pdf` | 33 | `https://www.nkhs.ac.jp/about/publicindex/` |
| 14 | 仙台医療秘書福祉＆IT専門学校 | `publication_lag_or_old_target_pdf` | 31 | `https://www.sanko.ac.jp/sendai-med/` |
| 21 | 名古屋医療秘書福祉&IT専門学校 | `publication_lag_or_old_target_pdf` | 31 | `https://www.sanko.ac.jp/nagoya-med/` |
| 22 | 大阪医療秘書福祉&IT専門学校 | `publication_lag_or_old_target_pdf` | 29 | `https://www.sanko.ac.jp/osaka-med/` |
| 44 | 東京ビューティ＆ブライダル専門学校 | `publication_lag_or_old_target_pdf` | 29 | `https://www.sanko.ac.jp/tachikawa-beauty/` |
| 13 | 札幌医療秘書福祉＆IT専門学校 | `publication_lag_or_old_target_pdf` | 28 | `https://www.sanko.ac.jp/sapporo-med/` |
| 32 | 東京リゾート＆スポーツ専門学校 | `publication_lag_or_old_target_pdf` | 28 | `https://www.sanko.ac.jp/tokyo-sports/` |
| 18 | 東京医療秘書歯科衛生＆IT専門学校 | `publication_lag_or_old_target_pdf` | 27 | `https://www.sanko.ac.jp/tokyo-med/` |
| 16 | 千葉医療秘書&IT専門学校 | `publication_lag_or_old_target_pdf` | 26 | `https://www.sanko.ac.jp/chiba-med/` |
| 17 | 東京未来大学福祉保育専門学校 | `publication_lag_or_old_target_pdf` | 26 | `https://www.sanko.ac.jp/tokyo-fukushi/` |
| 35 | 大阪リゾート＆スポーツ専門学校 | `publication_lag_or_old_target_pdf` | 26 | `https://www.sanko.ac.jp/osaka-sports/` |
| 30 | 仙台リゾート＆スポーツ専門学校 | `publication_lag_or_old_target_pdf` | 24 | `https://www.sanko.ac.jp/sendai-sports/` |

## Guardrails

- Do not count R7/FY2025 or older PDFs as FY2026/R8 strict successes.
- Do not infer fiscal year from download time, fetch time, or file mtime.
- Do not count target-form-like PDFs when target-year evidence is missing from
  the accepted evidence chain.
- Do not accept sibling-school or corporate-site PDFs until the school identity
  check passes or an operator confirms the exact school mapping.
- Do not use broad `school name + PDF` search as the acquisition path. RCA may
  use bounded same-domain and official-index sources first.

## Next Actions

P0 actions:

1. Owner decision: either approve the documented `publication_lag` exception
   path or keep v1.0 `NOT_READY` until FY2026/R8 target forms are actually
   published for enough schools.
2. Operator review: inspect the two NEEC `target_form_without_year_evidence`
   packets and decide whether page-level official evidence is strong enough
   for a structured year override. If not, keep them out of Excel.
3. Source correction: review the two Sanko `school_identity_mismatch` packets
   and fix exact official URL mapping only if the evidence proves the school
   identity. Otherwise keep them in review.

P1 actions:

1. Done in source: `scripts/summarize_stage6_rca.py` summarizes RCA batch
   buckets from a Stage 6 evidence ZIP so future owner handoffs show the same
   action lanes automatically.
2. Source hardening added after this v535 evidence:
   `docs/reports/2026-06-20-sanko-shared-origin-disclosure-probe.md` keeps both
   Sanko school-slug disclosure shapes under shared-origin throttling for the
   one `non_target_candidates_only` site. It needs a rebuilt Windows canary
   before it can be counted as release evidence.

P2 actions:

1. Clean or ignore local generated analysis directories only after confirming
   they are not needed by the user: `.codegraph/` and `.understand-anything/`.

P3 actions:

1. Keep university target-document discovery, extraction, and Excel mapping in
   v2 scope. The v535 MEXT workbook package gate is useful source-index
   evidence, not a v1 production university workflow.
