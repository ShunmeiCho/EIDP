# EIDP v445 Stage 6 Evidence Draft

Updated: 2026-05-16
Status: draft / not signed off

This document records the v445 Windows canary lane. v445 is a targeted master
import correction after v444 proved the `日本工学院北海道専門学校` sample reached the
wrong site set because the school prefecture stayed as `東京都` from earlier
master sheets. It is not a v1.0 sign-off because the operator real-cycle row and
the FY2026/R8 production yield gate are still missing.

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v445.zip` |
| SHA256 | `3cd36e11e281a4cd9646bcb865a006f5e99c9f15fae1f7700f65714aa56ba04b` |
| SHA256 sidecar | `dist/eidp-windows-v445.zip.sha256` |
| Package commit | `19ceb0dee69fe7b90e32a9a90591018d9c5e773f` |
| Windows extract path | `C:\Users\cyo20\EIDP-v445-19ceb0d` |
| Windows staging ZIP | `C:\EIDP-staging\eidp-windows-v445.zip` |
| Canary evidence | `logs/win-v445-stage6/20260515_223402-summary.json` |
| RCA evidence | `logs/win-v445-stage6/20260515_223402-discovery-rca-batch-plan.json` |
| Rejection evidence | `logs/win-v445-stage6/20260515_223402-discovery-rejections.jsonl` |

## Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| Mac tests | pass | `uv run pytest` returned `1618 passed`; `uv run mypy src` returned 0 errors; Ruff passed for `src/eidp/excel/importer.py` and `tests/unit/test_importer_idempotency.py`. |
| Real master import regression | pass | A temporary Mac SQLite import of `data/master.xlsx` ended with school id 3 as `(3, '北海道', '日本工学院北海道専門学校')`. |
| Mac package freshness | pass | `logs/release-gate-v445.json` reports package/source commit `19ceb0dee69fe7b90e32a9a90591018d9c5e773f`, SHA sidecar match, `source_dirty=false`, and full package verification. |
| Discovery gold set | pass | v445 gate reports expected predictions `44/44` with no failed, missing, or unexpected entries. |
| Windows transfer + SHA | pass | Win-side `Get-FileHash` matched SHA256 `3cd36e11e281a4cd9646bcb865a006f5e99c9f15fae1f7700f65714aa56ba04b`. |
| Windows setup | pass | `EIDP-setup.bat` completed in `C:\Users\cyo20\EIDP-v445-19ceb0d`; `validate_install.bat --after-setup --json` returned `ok=true` with `sqlite_integrity_check=ok`. |
| Master prefecture reconciliation | pass | Windows setup logs recorded `school_prefecture_reconciled` for `日本工学院北海道専門学校`, changing `old_prefecture=東京都` to `new_prefecture=北海道`. |
| URL-only bootstrap | pass | `bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed; school id 3 now has `https://www.nkhs.ac.jp/about/publicindex/` as `url_type=disclosure`, `discovery_method=prefecture_aggregator`, confidence `0.95`. |
| Bounded weekly canary | diagnostic pass / yield fail | `scripts\weekly_run.bat` exited `0` under `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`. The summary reported `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, and `ship_gate_status=below_gate`. |
| Disk hygiene | pass | Mac and Windows retain only v445 current and v442 fallback package/deploy artifacts; v444 package and deploy artifacts were removed. `_temp=0B` and `.claude/worktrees=0B` on Mac. |

## FY2026 Canary RCA

The v445 bounded canary improves the v444 failure shape but still cannot
auto-acquire FY2026/R8 target PDFs. The Hokkaido school now reaches the correct
official disclosure page and produces an actionable review packet, but all
target-form candidates are 2025 or older.

| RCA field | Result |
| --- | --- |
| Batch plan items | 5 |
| Item buckets | `target_form_without_year_evidence=1`, `non_target_candidates_only=2`, `no_pdf_candidates=2` |
| Rejection reasons | `pre_filtered_non_target_hint=22`, `target_fiscal_year_not_detected=5`, `fiscal_year_mismatch=2`, `classified_non_target=3`, `no_candidates_found=2` |
| Candidate-school mismatch | `0` |
| Affected improved sample | `日本工学院北海道専門学校` |
| Hokkaido official URL | `https://www.nkhs.ac.jp/about/publicindex/` |
| Primary implication | v445 fixes the master-data/site-linkage defect. Remaining yield failure is expected until FY2026/R8 target-form PDFs are published or the operator accepts an older-year candidate manually. |

## Stage 6 Boundary

v445 proves Mac gate, Windows transfer, setup, URL bootstrap, bounded launcher
execution, and the targeted Hokkaido school-site correction for the current
code. It does not replace the v442 verified evidence bundle/browser/R7 Excel
proof, and it does not satisfy operator real-cycle sign-off. The v1.0 ship
blocker remains the owner/operator Stage 6 real-cycle row plus a production
yield gate showing true FY2026/R8 target-form auto-acquisition at the required
level.

Do not sign this draft until the v445 or later operator-PC real-cycle row
exists.
