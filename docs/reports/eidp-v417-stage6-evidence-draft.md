# EIDP v417 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: **DRAFT / NOT COMPLETE**

This document is the v417 Stage 6 evidence landing page. It is intentionally
not a sign-off: v417 is Mac/non-Windows release-gate-clean, but it has not yet
been transferred to the Windows operator PC and has no v417 setup/UI/real-cycle
evidence.

## Gate Interpretation

| Gate | Current result | Evidence |
| --- | --- | --- |
| v417 package freshness | pass | `logs/release-gate-v417-retroactive.json` reports package/source commit `32b1dee32ad20804e624080e284c1dd8c2227c42`, `source_dirty=false`, and `stale=false`. |
| v417 package integrity | pass | `dist/eidp-windows-v417.zip.sha256` and release gate both report SHA256 `01eae4467ab3a66b1e04a1d6c4ba78b50ed46d8b789c2718462c7c8b685f4dce`. |
| v417 Mac/non-Windows release gate | pass | Full gate returned `ok=true`: unit suite `1539 passed`, validator slice `163 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v417 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-131707` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v417 Windows transfer/setup/UI | missing | SSH-Win is disconnected; no v417 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |
| Stage 6 operator-PC real cycle | missing | `docs/runbooks/eidp-operator-e2e-template.md` still requires real-cycle fields, owner/operator fields, KPI rows, evidence bundle, and sign-off. |
| FY2026/R8 ship yield | fail / not yet measurable | Current evidence still lacks true current-FY target-form auto-acquisition at 60-70% and manual work <= 30%. Retroactive R7 evidence must not be counted as R8 yield. |

## v417 Package Record

| Item | Record |
| --- | --- |
| Package | `dist/eidp-windows-v417.zip` |
| SHA256 | `01eae4467ab3a66b1e04a1d6c4ba78b50ed46d8b789c2718462c7c8b685f4dce` |
| SHA256 sidecar | `dist/eidp-windows-v417.zip.sha256` |
| SHA256 sidecar path note | The sidecar records the repo-relative package path. If the ZIP and sidecar are copied flat to `C:\EIDP-staging\`, use the digest value as the source of truth and compare it with `Get-FileHash`; do not rely on `sha256sum -c` unless the same `dist\` relative path is preserved. |
| Package commit | `32b1dee32ad20804e624080e284c1dd8c2227c42` |
| Full release-gate log | `logs/release-gate-v417-retroactive.json` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v417-32b1dee3` |

## Prompt-To-Artifact Checklist

| Requirement | Current v417 evidence | Status |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | Package verifier reports `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, and `prefecture_seed_school_rows_total=2148`. | Packaged / Mac verified |
| Strict target-FY PDF discovery excludes stale fallback from success | Package verifier and discovery-gold gates passed with `discovery_gold_set_entries=44`, `exact_matches=44`, `failed_predictions=0`, and `undemonstrated_pattern_sources=[]`. | Mechanically guarded |
| pdfplumber / PyMuPDF / Tesseract OCR confidence-gated writes | Code and package contracts are present; v384 remains the latest Windows OCR runtime/image-write proof. | v417 Windows OCR proof missing |
| Append-only DepartmentYearly / SupportRecipient writes | Unit and historical Windows copied-DB/sandbox evidence exist; v408 remains the latest Windows browser-write/audit support lane. | v417 real-cycle proof missing |
| Excel template export | v417 isolated FY2025/R7 export matched `_temp/v408-r7-cli-export.xlsx` with `missing_rows=0`, `extra_rows=0`, `differing_fields=0`. | Mac retroactive proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v417 operator-cycle audit/outbox delta is not captured. | Missing for v417 real cycle |
| ZIP distribution -> setup -> browser UI offline operation | v417 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v417 |
| Ship line 60-70% true target PDF / <=30% manual work | No v417 current-FY production yield evidence exists. | Missing / failing |

## Windows Execution To Fill This Draft

When SSH-Win is available again, execute the v417 lane in this order:

1. Transfer `dist/eidp-windows-v417.zip` and `dist/eidp-windows-v417.zip.sha256`
   to `C:\EIDP-staging\` or the approved operator-PC staging path.
2. Verify SHA256 on Windows before extraction. The expected value is
   `01eae4467ab3a66b1e04a1d6c4ba78b50ed46d8b789c2718462c7c8b685f4dce`:

   ```powershell
   $expected = "01eae4467ab3a66b1e04a1d6c4ba78b50ed46d8b789c2718462c7c8b685f4dce"
   $actual = (Get-FileHash C:\EIDP-staging\eidp-windows-v417.zip -Algorithm SHA256).Hash.ToLowerInvariant()
   if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }
   ```
3. Extract to `C:\Users\cyo20\EIDP-v417-32b1dee3` unless the operator chooses
   a different path.
4. Run `EIDP-setup.bat` / `scripts\first_setup.bat` and save setup logs.
5. Run packaged install validation with `--after-setup --json`.
6. Start `EIDP-start.bat` or `scripts\launch.bat`, open Streamlit at
   `127.0.0.1:8501`, and tunnel from Mac with `18501 -> 8501`.
7. Run the Stage 6 retroactive FY2025 cycle with process-local
   `EIDP_TARGET_FISCAL_YEAR=2025`; do not write it permanently to `.env`.
8. Generate and verify the Stage 6 evidence bundle.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v417
   operator-PC values and KPI rows.

## Known Boundaries

- v408 Windows evidence is supporting evidence only. It does not sign off v417.
- FY2025/R7 retroactive evidence proves rolling-FY mechanics and Excel
  regression, not FY2026/R8 publication yield.
- Do not delete `data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, or
  `data/master.xlsx`.
- Do not patch code on Windows. All fixes must go through Mac TDD, ZIP rebuild,
  SHA verification, and Windows redeploy.
