# EIDP v456 Real-Cycle Execution Card

Updated: 2026-05-16

This card is the short operator/owner checklist for the next Stage 6 real-cycle
run on the current v456 lane. It does not replace
`docs/runbooks/eidp-operator-e2e-template.md`; use that template for the final
record.

## Current Lane

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v456.zip` |
| SHA256 | `73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2` |
| Package snapshot | `f33ffc0e6fd801782f3e49fad3315adc64081f6f` |
| Windows root | `C:\Users\cyo20\EIDP-v456-f33ffc0` |
| Evidence draft | `docs/reports/eidp-v456-stage6-evidence-draft.md` |
| Full template | `docs/runbooks/eidp-operator-e2e-template.md` |

## Do Not Touch

- Do not delete `data\eidp.sqlite3`.
- Do not delete `data\audit\manual-actions.jsonl`.
- Do not delete `data\master.xlsx`.
- Do not run `uninstall.bat`.
- Do not persist `EIDP_TARGET_FISCAL_YEAR` into `.env`.
- Do not overwrite an existing operator data directory without a backup.

## Preflight

Run from PowerShell on the operator PC:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v456-f33ffc0"
$zip = "C:\EIDP-staging\eidp-windows-v456.zip"
$expected = "73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2"
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

.\scripts\validate_install.bat --after-setup
.\scripts\stage6_recovery_check.bat "C:\Users\cyo20\EIDP-v456-f33ffc0\scripts\weekly_run.bat"
.\scripts\diagnose.bat
```

Expected before continuing:

| Check | Expected |
| --- | --- |
| SHA256 | matches the value above |
| setup validator | exit code `0` |
| recovery check | `ok=true`, `action_matches_expected=true` |
| diagnostics | writes `logs\diagnostics-*.txt` |

## Real-Cycle Run

1. Double-click `EIDP-start.bat`.
2. Confirm the browser opens `http://127.0.0.1:8501`.
3. Confirm the UI shows `2026年度（令和8年度）`.
4. Run the normal weekly collection cycle only with owner/operator present.
5. Use the browser UI to resolve the real work queue:
   - `① 学校別タスク`
   - `② PDF確認・手入力`
   - `③ 年度判定・修正`
   - `④ Excel プレビュー`
   - `詳細 operator` -> `URL候補レビュー`
   - `詳細 operator` -> `監査ログ`
6. In `監査ログ`, run `Outbox を flush` after write actions.
7. Record the actual KPI values in `docs/runbooks/eidp-operator-e2e-template.md`.

Do not treat the existing v456 bounded canary, browser navigation, UI sandbox,
or R7 browser Excel proof as the real-cycle sign-off.

## Evidence Bundle

After the real-cycle run:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v456-f33ffc0"
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Copy these files back to Mac:

- `logs\stage6-evidence-*.zip`
- `logs\stage6-evidence-verify-*.json`
- `logs\diagnostics-*.txt`
- `logs\run-*.log`
- `data\output\last_run.json`
- `data\output\target-year-discovery\*-discovery-rca-batch-plan.json`

Do not put Excel exports or live SQLite files into the shared evidence ZIP.

## Sign-Off Gate

The v1.0 line is still blocked until the owner/operator record contains:

| Gate | Required result |
| --- | --- |
| Operator PC one-cycle | completed |
| `ship_readiness_rc` | `0` or approved release exception |
| strict target PDF auto-yield | production R8 evidence, target 60-70% |
| estimated manual workload | 30% or lower |
| audit/outbox | no pending JSONL rows after flush |
| evidence verification | `ok=true` |
| owner sign-off | present |
| operator sign-off | present |
