# EIDP v420 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: draft / not signed off

This document is the v420 Stage 6 evidence landing page. v420 is
Mac/non-Windows release-gate-clean, but it has not yet been transferred to the
Windows operator PC and has no v420 setup/UI/real-cycle proof.

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v420 package freshness | pass | `logs/release-gate-v420-retroactive.json` reports package/source commit `99efba8a798d76611896be22e36abbb125a5eb71`, `source_dirty=false`, and `stale=false`. |
| v420 package integrity | pass | `dist/eidp-windows-v420.zip.sha256` and release gate report SHA256 `5585d303b97de1f29af3737a7c1fcd614eb5c23b51307fb2af57988612740de8`. |
| v420 Mac/non-Windows release gate | pass | Full gate returned `ok=true`: unit suite `1555 passed`, validator slice `163 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v420 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-140811` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v419 retroactive FY2024/R6 and FY2023/R5 support | pass | `logs/release-gate-v419-retroactive-fy2024-reference.json` and `logs/release-gate-v419-retroactive-fy2023-reference.json` remain the current multi-year support evidence; both returned `ok=true` and zero business-value diffs against stable generated references. |
| v420 Windows transfer/setup/UI | missing | SSH-Win is disconnected; no v420 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v420.zip` |
| SHA256 | `5585d303b97de1f29af3737a7c1fcd614eb5c23b51307fb2af57988612740de8` |
| SHA256 sidecar | `dist/eidp-windows-v420.zip.sha256` |
| Package commit | `99efba8a798d76611896be22e36abbb125a5eb71` |
| Full release-gate log | `logs/release-gate-v420-retroactive.json` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v420-99efba8a` |

## Stage 6 Boundary

| Requirement | Current v420 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | v420 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v420 |
| Retroactive FY2025/R7 Excel export parity | v420 isolated Mac export matched the stable v408 R7 CLI reference with zero business-value diffs. | Mac proof only |
| Retroactive FY2024/R6 and FY2023/R5 Excel export parity | v419 isolated Mac exports matched their stable references with zero business-value diffs. | Mac support evidence |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v420 operator-cycle audit/outbox delta is not captured. | Missing for v420 real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | No v420 current-FY production yield evidence exists. | Missing / failing |

## Next Windows Steps

When SSH-Win is available again, execute the v420 lane in this order:

1. Transfer `dist/eidp-windows-v420.zip` and `dist/eidp-windows-v420.zip.sha256`
   to `C:\EIDP-staging\`.
2. Verify SHA256 on Windows with `Get-FileHash` or `certutil`.
3. Extract to `C:\Users\cyo20\EIDP-v420-99efba8a` unless the operator chooses
   a different staging path.
4. Run `first_setup.bat`.
5. Launch Streamlit on `127.0.0.1:8501`.
6. Run the Stage 6 retroactive FY2025 operator dry-run.
7. Build and verify the Stage 6 evidence bundle.
8. Pull the evidence bundle back to Mac and verify it again.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v420
   operator data.

Do not sign this draft until the Windows operator-PC row exists.
