# EIDP v415 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: **DRAFT / NOT COMPLETE**

This document is the v415 Stage 6 evidence landing page. It is intentionally
not a sign-off: v415 is Mac/non-Windows release-gate-clean, but it has not yet
been transferred to the Windows operator PC and has no v415 setup/UI/real-cycle
evidence.

## Gate Interpretation

| Gate | Current result | Evidence |
| --- | --- | --- |
| v415 package freshness | pass | `logs/release-gate-v415-retroactive.json` reports package/source commit `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`, `source_dirty=false`, and `stale=false`. |
| v415 package integrity | pass | `dist/eidp-windows-v415.zip.sha256` and release gate both report SHA256 `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd`. |
| v415 Mac/non-Windows release gate | pass | Full gate returned `ok=true`: unit suite `1537 passed`, validator slice `161 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v415 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-123749` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v415 Windows transfer/setup/UI | missing | SSH-Win is disconnected; no v415 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |
| Stage 6 operator-PC real cycle | missing | `docs/runbooks/eidp-operator-e2e-template.md` still requires real-cycle fields, owner/operator fields, KPI rows, evidence bundle, and sign-off. |
| FY2026/R8 ship yield | fail / not yet measurable | Current evidence still lacks true current-FY target-form auto-acquisition at 60-70% and manual work <= 30%. Retroactive R7 evidence must not be counted as R8 yield. |

## v415 Package Record

| Item | Record |
| --- | --- |
| Package | `dist/eidp-windows-v415.zip` |
| SHA256 | `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd` |
| SHA256 sidecar | `dist/eidp-windows-v415.zip.sha256` |
| SHA256 sidecar path note | The sidecar records the repo-relative package path. If the ZIP and sidecar are copied flat to `C:\EIDP-staging\`, use the digest value as the source of truth and compare it with `Get-FileHash`; do not rely on `sha256sum -c` unless the same `dist\` relative path is preserved. |
| Package commit | `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c` |
| Full release-gate log | `logs/release-gate-v415-retroactive.json` |
| Representative docs-only stale replay | `logs/release-gate-v415-docs-only-stale-after-sha-sidecar-note.json` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v415-09ad5e6b` |

## Prompt-To-Artifact Checklist

| Requirement | Current v415 evidence | Status |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | Package verifier reports `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, and `prefecture_seed_school_rows_total=2148`. | Packaged / Mac verified |
| Strict target-FY PDF discovery excludes stale fallback from success | Package verifier and discovery-gold gates passed with `discovery_gold_set_entries=44`, `exact_matches=44`, `failed_predictions=0`, and `undemonstrated_pattern_sources=[]`. | Mechanically guarded |
| pdfplumber / PyMuPDF / Tesseract OCR confidence-gated writes | Code and package contracts are present; v384 remains the latest Windows OCR runtime/image-write proof. | v415 Windows OCR proof missing |
| Append-only DepartmentYearly / SupportRecipient writes | Unit and historical Windows copied-DB/sandbox evidence exist; v408 remains the latest Windows browser-write/audit support lane. | v415 real-cycle proof missing |
| Excel template export | v415 isolated FY2025/R7 export matched `_temp/v408-r7-cli-export.xlsx` with `missing_rows=0`, `extra_rows=0`, `differing_fields=0`. | Mac retroactive proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v415 operator-cycle audit/outbox delta is not captured. | Missing for v415 real cycle |
| ZIP distribution -> setup -> browser UI offline operation | v415 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v415 |
| Ship line 60-70% true target PDF / <=30% manual work | No v415 current-FY production yield evidence exists. | Missing / failing |

## Windows Execution To Fill This Draft

When SSH-Win is available again, execute the v415 lane in this order:

1. Transfer `dist/eidp-windows-v415.zip` and `dist/eidp-windows-v415.zip.sha256`
   to `C:\EIDP-staging\` or the approved operator-PC staging path.
2. Verify SHA256 on Windows before extraction. The expected value is
   `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd`:

   ```powershell
   $expected = "25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd"
   $actual = (Get-FileHash C:\EIDP-staging\eidp-windows-v415.zip -Algorithm SHA256).Hash.ToLowerInvariant()
   if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }
   ```
3. Extract to `C:\Users\cyo20\EIDP-v415-09ad5e6b` unless the operator chooses
   a different path.
4. Run `EIDP-setup.bat` / `scripts\first_setup.bat` and save setup logs.
5. Run packaged install validation with `--after-setup --json`.
6. Start `EIDP-start.bat` or `scripts\launch.bat`, open Streamlit at
   `127.0.0.1:8501`, and tunnel from Mac with `18501 -> 8501`.
7. Run the Stage 6 retroactive FY2025 cycle with process-local
   `EIDP_TARGET_FISCAL_YEAR=2025`; do not write it permanently to `.env`.
8. Generate and verify the Stage 6 evidence bundle.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v415
   operator-PC values and KPI rows.

## Known Boundaries

- v408 Windows evidence is supporting evidence only. It does not sign off v415.
- v415 docs-only stale replay is allowed only when the current HEAD differs
  from the package commit by documentation paths. Use the JSON
  `package_source_check.changed_paths` field as the source of truth instead of
  hard-coding a docs-only HEAD in this draft.
- FY2025/R7 retroactive evidence proves rolling-FY mechanics and Excel
  regression, not FY2026/R8 publication yield.
- Do not delete `data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, or
  `data/master.xlsx`.
- Do not patch code on Windows. All fixes must go through Mac TDD, ZIP rebuild,
  SHA verification, and Windows redeploy.
