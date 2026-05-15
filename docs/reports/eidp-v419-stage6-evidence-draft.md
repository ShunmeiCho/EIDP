# EIDP v419 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: draft / not signed off

This document is the v419 Stage 6 evidence landing page. v419 is
Mac/non-Windows release-gate-clean, but it has not yet been transferred to the
Windows operator PC and has no v419 setup/UI/real-cycle proof.

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v419 package freshness | pass | `logs/release-gate-v419-retroactive.json` reports package/source commit `45b9dffc3c02a844f792f3f0a3a31e98d46d1931`, `source_dirty=false`, and `stale=false`. |
| v419 package integrity | pass | `dist/eidp-windows-v419.zip.sha256` and release gate report SHA256 `f1ce206e169a9f5ab2f1572c0528c47f0c59131af55750ef935aca906093c8e9`. |
| v419 Mac/non-Windows release gate | pass | Full gate returned `ok=true`: unit suite `1545 passed`, validator slice `163 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v419 local CI-equivalent gate | pass | `.github/workflows/ci.yml` now encodes locked uv install, scoped Ruff, `mypy src`, and `pytest --cov=src/eidp --cov-report=term --cov-fail-under=80`; the local equivalent returned `1545 passed` and `Total coverage: 80.03%`. |
| v419 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-135020` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v419 retroactive FY2024/R6 Excel regression | pass | `logs/release-gate-v419-retroactive-fy2024-reference.json` returned `ok=true`; isolated app root `_temp/non-windows-retroactive-fy2024-20260515-135655` exported FY2024 and returned zero missing/extra rows and zero differing fields against the stable FY2024 generated reference. |
| v419 retroactive FY2023/R5 Excel regression | pass | `logs/release-gate-v419-retroactive-fy2023-reference.json` returned `ok=true`; isolated app root `_temp/non-windows-retroactive-fy2023-20260515-135744` exported FY2023 and returned zero missing/extra rows and zero differing fields against the stable FY2023 generated reference. |
| v419 retroactive matrix runner | pass | `scripts/run_retroactive_excel_matrix.py` was added as a thin orchestrator over `run_non_windows_release_gates.py`; a FY2025 smoke wrote `logs/release-gate-v419-retroactive-matrix-smoke.json` and returned `ok=true`. |
| v419 Windows transfer/setup/UI | missing | SSH-Win is disconnected; no v419 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v419.zip` |
| SHA256 | `f1ce206e169a9f5ab2f1572c0528c47f0c59131af55750ef935aca906093c8e9` |
| SHA256 sidecar | `dist/eidp-windows-v419.zip.sha256` |
| Package commit | `45b9dffc3c02a844f792f3f0a3a31e98d46d1931` |
| Full release-gate log | `logs/release-gate-v419-retroactive.json` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v419-45b9dffc` |

## Stage 6 Boundary

| Requirement | Current v419 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | v419 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v419 |
| Retroactive FY2025/R7, FY2024/R6, and FY2023/R5 Excel export parity | v419 isolated Mac exports matched their stable references with zero business-value diffs. | Mac proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v419 operator-cycle audit/outbox delta is not captured. | Missing for v419 real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | No v419 current-FY production yield evidence exists. | Missing / failing |

## Next Windows Steps

When SSH-Win is available again, execute the v419 lane in this order:

1. Transfer `dist/eidp-windows-v419.zip` and `dist/eidp-windows-v419.zip.sha256`
   to `C:\EIDP-staging\`.
2. Verify SHA256 on Windows with `Get-FileHash` or `certutil`.
3. Extract to `C:\Users\cyo20\EIDP-v419-45b9dffc` unless the operator chooses
   a different staging path.
4. Run `first_setup.bat`.
5. Launch Streamlit on `127.0.0.1:8501`.
6. Run the Stage 6 retroactive FY2025 operator dry-run.
7. Build and verify the Stage 6 evidence bundle.
8. Pull the evidence bundle back to Mac and verify it again.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v419
   operator data.

Do not sign this draft until the Windows operator-PC row exists.
