# EIDP v526 Owner Return Fill Sheet

Date: 2026-05-20
Scope: v526 owner/operator return evidence only

This sheet is a fill aid for `docs/runbooks/eidp-operator-e2e-template.md`.
It is not release approval and does not replace the signed template,
`publication_lag` exception record, or `scripts/verify_stage6_return.py`.

## Use This Only After The Owner Chooses Route A

Route A means:

1. the owner explicitly approves the `publication_lag` exception;
2. the operator runs one real Stage 6 cycle on the v526 side-by-side lane; and
3. the completed template, logs, Excel proof, audit proof, and sign-offs are
   returned for verification.

If the owner chooses Route B, do not run the owner sign-off cycle yet. Keep
v1.0 on hold until enough FY2026/R8 target-form PDFs are public.

## Fixed Values To Copy Into The E2E Template

| E2E field | Value |
| --- | --- |
| EIDP commit / tag | `5b30eb78edc331f992c1a99fdc7611174791ab87` for the v526 package; PR docs head `3e42340c6798d2e7a134b6b605060e1cd7f45a7b` |
| core ZIP ファイル名 | `eidp-windows-v526.zip` |
| core ZIP sha256 | `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca` |
| transferred ZIP | `C:\EIDP-staging\eidp-windows-v526.zip` |
| Windows extract path | `%USERPROFILE%\EIDP-v526-5b30eb7-env0` |
| current active root to preserve | `%USERPROFILE%\EIDP-v485-70e3db4` |
| non-Windows release gate | `logs/win-v526-stage6-v526-non-windows-release-gates-20260520.json` -> `ok=true` |
| Windows validation evidence | `logs\win-v526-stage6-v526-env0-validate-after-setup-20260520.json` |
| OCR runtime evidence | `logs\win-v526-stage6-v526-env0-validate-ocr-runtime-20260520.json` |
| UI smoke evidence | `logs\win-v526-stage6-v526-ui-smoke-20260520.json` |
| Excel smoke evidence | `logs\win-v526-stage6-v526-excel-summary-20260520.json` |
| bounded canary evidence | `logs\win-v526-stage6-v526-last-run-after-weekly-canary-limit50-20260520.json` |
| Stage 6 evidence verify | `logs\stage6-evidence-verify-local-v526-20260520.json` |
| release exception reason | `publication_lag` |
| mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` |
| mature-year proof years | `2025` |

The existing v526 bounded canary is reference evidence only. It is not owner
sign-off evidence:

| Metric | Existing v526 canary |
| --- | --- |
| strict FY2026/R8 target-PDF / Excel-ready yield | `5/50 (10.0%)` |
| operator-reviewable yield | `50/50 (100.0%)` |
| ship gate status | `below_gate` |

## Fields The Owner/Operator Must Fill From The Real Cycle

Do not copy the bounded canary into these fields. Fill them from the owner real
cycle and returned diagnostics.

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
