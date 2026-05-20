# v526 Target-Yearless RCA Spot Check

Date: 2026-05-20 21:13 JST

## Scope

This is a narrow read-only check of the v526 Windows limit-50 discovery RCA
bucket `target_fiscal_year_not_detected`. It does not change source code,
package contents, Windows runtime state, or release status.

Inputs checked:

- `logs/win-v526-stage6-v526-last-run-after-weekly-canary-limit50-20260520.json`
- Windows runtime evidence:
  `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\data\output\target-year-discovery\20260520_090639-discovery-rejections.jsonl`
- Windows runtime RCA packet:
  `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\data\output\target-year-discovery\20260520_090639-discovery-rca-batch-plan.json`
- Official pages/PDFs opened read-only:
  - `https://www.neec.ac.jp/portal/public/mext-scholarship/`
  - `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf`
  - `https://www.sanko.ac.jp/tachikawa-beauty/disclosure/`

## Findings

The v526 weekly canary recorded:

```json
{
  "rejection_reason_target_fiscal_year_not_detected": 5,
  "rejection_reason_pre_filtered_non_target_hint": 631,
  "rejection_reason_fiscal_year_mismatch": 267,
  "rejection_reason_classified_non_target": 88,
  "rejection_reason_no_candidates_found": 8,
  "rejection_reason_http_error_httpstatuserror": 1
}
```

The five `target_fiscal_year_not_detected` rows are:

| School ID | Candidate | Evidence state | Strict FY2026 verdict |
| --- | --- | --- | --- |
| 1 | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf` | Target-form anchor text, no FY2026/Reiwa 8 evidence | Do not count |
| 1 | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf` | Target-form anchor text, no FY2026/Reiwa 8 evidence | Do not count |
| 2 | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf` | Target-form anchor text, no FY2026/Reiwa 8 evidence | Do not count |
| 2 | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf` | Target-form anchor text, no FY2026/Reiwa 8 evidence | Do not count |
| 44 | `https://www.sanko.ac.jp/tachikawa-beauty/pdf/yoshiki.pdf` | Image-only target-like PDF linked under older/stale context | Do not count |

The NEEC official page contains target-form links for `様式第2号`, but the
checked evidence does not supply a machine-verifiable FY2026/Reiwa 8 year. The
Sanko page exposes historical confirmation-form anchors through FY2025; the
checked v526 candidate for school ID 44 is not FY2026 strict evidence.

## Verdict

No implementation bug was found in the `target_fiscal_year_not_detected` bucket
that can safely raise the v526 strict FY2026/R8 yield. These rows are useful
operator-review evidence, but they must remain excluded from strict current-FY
success until a current-year page/PDF signal or owner-approved exception exists.

This spot check reinforces the existing release boundary:

- strict old-year/no-year fallback exclusion remains correct,
- v526 strict/Excel-ready yield remains `5/50 (10.0%)`,
- `publication_lag` approval and owner Stage 6 return remain required before
  v1.0 release.
