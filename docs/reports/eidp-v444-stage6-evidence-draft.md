# EIDP v444 Stage 6 Evidence Draft

Updated: 2026-05-16
Status: draft / not signed off

This document records the v444 Windows canary lane. v444 is a targeted
discovery correction after v443 proved that group-root homepage following could
reach a more-specific sibling school. It is not a v1.0 sign-off because the
operator real-cycle row and the FY2026/R8 production yield gate are still
missing.

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v444.zip` |
| SHA256 | `7814b7d1212eb10ef8c9d5b187e24ecc4b7eb72e0f558d6a217c57af1dc53d65` |
| SHA256 sidecar | `dist/eidp-windows-v444.zip.sha256` |
| Package commit | `f14a49fb2036c6ff13869f7d932aea9e52084f87` |
| Windows extract path | `C:\Users\cyo20\EIDP-v444-f14a49f` |
| Windows staging ZIP | `C:\EIDP-staging\eidp-windows-v444.zip` |
| Canary evidence | `logs/win-v444-stage6/20260515_221216-summary.json` |
| RCA evidence | `logs/win-v444-stage6/20260515_221216-discovery-rca-batch-plan.json` |
| Rejection evidence | `logs/win-v444-stage6/20260515_221216-discovery-rejections.jsonl` |

## Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| Mac package freshness | pass | `logs/release-gate-v444.json` reports package/source commit `f14a49fb2036c6ff13869f7d932aea9e52084f87`, SHA sidecar match, `source_dirty=false`, and full package verification. |
| Discovery gold set | pass | v444 gate reports expected predictions `44/44` with no failed, missing, or unexpected entries. |
| Windows transfer + SHA | pass | Win-side `Get-FileHash` matched SHA256 `7814b7d1212eb10ef8c9d5b187e24ecc4b7eb72e0f558d6a217c57af1dc53d65`. |
| Windows setup | pass | `EIDP-setup.bat` completed in `C:\Users\cyo20\EIDP-v444-f14a49f`; `validate_install.bat --after-setup --json` returned `ok=true` with `sqlite_integrity_check=ok`. |
| URL-only bootstrap | pass | `bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed and registered the same 47-prefecture URL baseline shape as v442. |
| Bounded weekly canary | diagnostic pass / yield fail | `scripts\weekly_run.bat` exited `0` under `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`. The summary reported `crawled=5`, `found=3`, `downloaded=0`, `target_pdf_auto_yield_pct=0.0`, and `ship_gate_status=below_gate`. |
| Sibling homepage regression | pass | v444 rejection evidence contains no `nkhs` entries for the base `日本工学院専門学校` sample; v443 had reached `nkhs.ac.jp` through a too-broad base-name match. |
| Disk hygiene | pass | Mac retains v444 current, v442 fallback, and latest alias; `_temp=0B`. Windows `C:\EIDP-staging` and `C:\Users\cyo20` retain only v444 current and v442 fallback. |

## FY2026 Canary RCA

The v444 bounded canary still fails before extraction and Excel export. It
selected the same first 5 target-missing schools, crawled all 5, found
candidates for 3, and downloaded 0 target PDFs.

| RCA field | Result |
| --- | --- |
| Batch plan items | 5 |
| Item buckets | `non_target_candidates_only=3`, `no_pdf_candidates=2` |
| Rejection reasons | `candidate_school_mismatch=23`, `pre_filtered_non_target_hint=9`, `no_candidates_found=2` |
| Affected sample | `日本工学院北海道専門学校`, `日本工学院専門学校`, `日本工学院八王子専門学校`, `東京モード学園`, `大阪モード学園` |
| Primary implication | v444 fixes the sibling-homepage false positive, but the sample still needs better school/site matching and no-PDF candidate discovery before OCR/Excel can contribute. |

## Stage 6 Boundary

v444 proves Mac gate, Windows transfer, setup, URL bootstrap, and bounded
launcher execution for the current code. It does not replace the v442 verified
evidence bundle/browser/R7 Excel proof, and it does not satisfy operator
real-cycle sign-off. The v1.0 ship blocker remains the owner/operator Stage 6
real-cycle row plus a production yield gate showing true FY2026/R8 target-form
auto-acquisition at the required level.

Do not sign this draft until the v444 or later operator-PC real-cycle row
exists.
