# EIDP v532 Owner Return Fill Sheet

Date: 2026-06-20
Scope: v532 owner/operator return evidence only

This sheet is a fill aid for `docs/runbooks/eidp-operator-e2e-template.md`.
It is not release approval and does not replace the signed template,
`publication_lag` exception record, or `scripts/verify_stage6_return.py`.

## Use This Only After The Owner Chooses Route A

Route A means:

1. the owner explicitly approves the `publication_lag` exception;
2. the operator runs one real Stage 6 cycle on the v532 side-by-side lane; and
3. the completed template, logs, Excel proof, audit proof, and sign-offs are
   returned for verification.

If the owner chooses Route B, do not run the owner sign-off cycle yet. Keep
v1.0 on hold until enough FY2026/R8 target-form PDFs are public.

## Fixed Values To Copy Into The E2E Template

| E2E field | Value |
| --- | --- |
| EIDP package commit | `723a5072f63e8a874bef85cc52d869f5e6daff15` |
| core ZIP ファイル名 | `eidp-windows-v532.zip` |
| core ZIP sha256 | `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7` |
| transferred ZIP | `C:\EIDP-staging\eidp-windows-v532.zip` |
| Windows extract path | `%USERPROFILE%\EIDP-v532-723a507-env0` |
| current active root to preserve | `%USERPROFILE%\EIDP-v485-70e3db4` |
| non-Windows release gate | `logs/win-v532-main-post-merge-release-gates-20260619.json` -> `ok=true` |
| GitHub main CI | run `27834912983` for `92ad3ef` -> `success` |
| Windows validation evidence | to be returned from v532 side-by-side run |
| OCR runtime evidence | required if OCR remains in v1.0 scope |
| UI smoke evidence | to be returned from v532 side-by-side run |
| Excel smoke evidence | to be returned from v532 side-by-side run |
| bounded canary evidence | to be returned from v532 side-by-side run |
| Stage 6 evidence verify | to be returned from v532 side-by-side run |
| release exception reason | `publication_lag` if Route A is chosen |
| mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` |
| mature-year proof years | `2025` |

The existing v526 bounded canary is reference evidence only. It is not v532
owner sign-off evidence.

## Fields The Owner/Operator Must Fill From The Real Cycle

Do not copy bounded-canary values into these fields. Fill them from the owner
real cycle and returned diagnostics.

| Required E2E row | Fill from |
| --- | --- |
| `ship_readiness_rc` | latest owner-cycle `diagnostics-*.txt` / `last_run.json` |
| `strict target PDF 自動取得率` | owner-cycle diagnostics / `last_run.json` |
| `推定手作業率` | owner-cycle diagnostics / `last_run.json` |
| `Excel ready 率` | owner-cycle diagnostics and Excel proof |
| `Excel 整合性` | output workbook metadata or redacted workbook proof |
| `監査ログページ表示` | operator UI audit page proof |
| `manual_action_log 件数` | DB / diagnostics / audit page count |
| `JSONL outbox 未送信件数` | before/after flush proof |
| `audit-flush 実行` | `pass` or `not needed`, with reason |
| `JSONL action_id 重複` | `none` |
| `業務員 PC 1 サイクル完了` | `pass`, with returned log paths |
| `KPI owner 承認` | `pass`, with owner name/date |
| `残 P0/P1 bug` | `none`, or list blocker IDs |
| Owner sign-off | name, date, decision |
| 業務員 sign-off | name, date, decision |

## Files To Return

- completed `eidp-operator-e2e-template.md`
- approved `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `data\output\last_run.json`
- latest `logs\run-*.log`
- latest `logs\diagnostics-*.txt`
- latest `logs\stage6-evidence-*.zip`
- latest `logs\stage6-evidence-verify-*.json`
- v532 setup validation JSON
- v532 active-task recovery JSON
- v532 UI smoke evidence
- Excel output proof or redacted workbook metadata
- ManualActionLog / JSONL outbox proof

## Developer Verification After Return

After copying the owner return files back to the repo, run:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template <filled-owner-e2e-template.md> \
  --last-run <returned-data-output-last_run.json> \
  --evidence-verify-json <returned-stage6-evidence-verify.json> \
  --release-exception-reason publication_lag \
  --mature-year-proof-json logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json \
  --release-exception-record docs/reports/2026-05-19-publication-lag-release-exception-record.md \
  --json
```

Release remains blocked unless this command returns `ok=true` and the approval
record plus sign-off fields are complete.
