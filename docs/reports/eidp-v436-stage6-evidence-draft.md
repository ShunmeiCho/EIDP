# EIDP v436 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: draft / not signed off

This document is the v436 Stage 6 evidence landing page. v436 is
Mac/non-Windows release-gate-clean, but it has not yet been transferred to the
Windows operator PC and has no v436 setup/UI/real-cycle proof.

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v436 package freshness | pass | `logs/release-gate-v436-full.json` reports package/source commit `f56b2e4b6bcd1bc26b94c2f9e38baab8438dde05`, `source_dirty=false`, and `stale=false`. |
| v436 package integrity | pass | `dist/eidp-windows-v436.zip.sha256` and release gate report SHA256 `d94ec5f4c735b7730d83299fc484fbcd71e5c0544a0f484ae5d900b4c46e218e`. |
| v436 Mac/non-Windows release gate | pass | Standard full gate exited `0`: unit suite `1592 passed`, validator slice `164 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v436 ZIP launcher/script consistency | pass | `unzip -l dist/eidp-windows-v436.zip` contains `EIDP-setup.bat`, `EIDP-start.bat`, `EIDP-diagnose.bat`, `EIDP-stage6-evidence.bat`, `EIDP-stage6-verify-evidence.bat`, `scripts/first_setup.bat`, `scripts/launch.bat`, `scripts/weekly_run.bat`, `scripts/validate_install.bat`, `scripts/collect_stage6_evidence.bat`, and `scripts/verify_stage6_evidence.bat`. The root Stage 6 evidence launchers call the packaged `scripts\collect_stage6_evidence.bat` and `scripts\verify_stage6_evidence.bat` wrappers. |
| v436 operator hardening | pass | v425 binds Streamlit launchers to `127.0.0.1`, adds app-lock acquisition around school-code and URL-candidate review writes, and filters PDF annotation URIs to absolute `http(s)` links. v436 adds per-call Excel threshold reads, lock-required proposal-review helpers, protected-file refusal in Stage 6 residual cleanup, pipeline-level fiscal-year range rejection, collateral-demotion audit rows for fiscal-year overrides, expanded CLI write-lock AST coverage across all `cli_*.py` command modules plus attribute-form write helper calls, `invalid_fiscal_year` stats/evidence for future or otherwise out-of-cap ingest annotations, app-root/data-dir install-path guards, SQLite performance indexes, manual-entry `SchoolYearStatus` plus `SupportRecipient` writes, locked school URL crawl-evidence JSONL appends, non-persistent `EIDP_TARGET_FISCAL_YEAR` operator settings, provider-specific OCR extraction methods, and `Numeric(4,3)` confidence precision. The full gate includes regression coverage for these contracts. |
| v436 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-181906` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v436 retroactive FY2025/R7, FY2024/R6, and FY2023/R5 matrix | pass | `logs/release-gate-v436-retroactive-matrix.json` returned `ok=true` for all three cases. `logs/release-gate-v436-retroactive-fy2025-reference.json`, `logs/release-gate-v436-retroactive-fy2024-reference.json`, and `logs/release-gate-v436-retroactive-fy2023-reference.json` each returned `ok=true` and zero business-value diffs against stable references. |
| v436 Windows transfer/setup/UI | missing | SSH-Win is disconnected; `docs/runbooks/eidp-v436-windows-transfer-checklist.md` now includes a no-SSH manual transfer path, but no v436 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v436.zip` |
| SHA256 | `d94ec5f4c735b7730d83299fc484fbcd71e5c0544a0f484ae5d900b4c46e218e` |
| SHA256 sidecar | `dist/eidp-windows-v436.zip.sha256` |
| Package commit | `f56b2e4b6bcd1bc26b94c2f9e38baab8438dde05` |
| FY2025 retroactive release-gate log | `logs/release-gate-v436-retroactive-fy2025-reference.json` |
| Superseded package note | v421 was rejected by the package verifier because the packaged E2E template still contained hard-coded v420 package/SHA fields. Do not transfer v421. |
| Windows transfer checklist | `docs/runbooks/eidp-v436-windows-transfer-checklist.md` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v436-f56b2e4b` |

Note: the v436 ZIP contains the reusable operator E2E template, while this
version-specific transfer checklist and evidence draft are companion documents
outside the ZIP. Carry the current repo copies of
`docs/runbooks/eidp-v436-windows-transfer-checklist.md` and this draft alongside
the ZIP and SHA sidecar during manual transfer or operator-PC execution. Fill
`docs/runbooks/eidp-operator-e2e-template.md` after execution; do not prefill the
packaged reusable template before building a ZIP.

## Stage 6 Boundary

| Requirement | Current v436 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | v436 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v436 |
| Retroactive FY2025/R7 Excel export parity | v436 isolated Mac export matched the stable v408 R7 CLI reference with zero business-value diffs. | Mac proof only |
| Retroactive FY2024/R6 and FY2023/R5 Excel export parity | v436 isolated Mac exports matched their stable references with zero business-value diffs. | Mac proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v436 operator-cycle audit/outbox delta is not captured. | Missing for v436 real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | No v436 current-FY production yield evidence exists. | Missing / failing |

## Next Windows Steps

When SSH-Win is available again, or when the operator can manually move the ZIP
through a USB drive or trusted internal file share, execute the v436 lane in
this order:

1. Transfer `dist/eidp-windows-v436.zip` and `dist/eidp-windows-v436.zip.sha256`
   to `C:\EIDP-staging\` using either SSH/SCP or the no-SSH manual path in
   `docs/runbooks/eidp-v436-windows-transfer-checklist.md`.
2. Verify SHA256 on Windows with `Get-FileHash` or `certutil`.
3. Extract to `C:\Users\cyo20\EIDP-v436-f56b2e4b` unless the operator chooses
   a different staging path.
4. Run `first_setup.bat`.
5. Launch Streamlit on `127.0.0.1:8501`.
6. Run the Stage 6 retroactive FY2025 operator dry-run.
7. Build and verify the Stage 6 evidence bundle.
8. Pull or manually copy the evidence bundle back to Mac and verify it again.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v436
   operator data.

Do not sign this draft until the Windows operator-PC row exists.
