# EIDP v548 Owner Return Fill Sheet

Date: 2026-06-21
Scope: v548 owner/operator return evidence only

This sheet is a fill aid for `docs/runbooks/eidp-operator-e2e-template.md`.
It is not release approval and does not replace the signed template,
`publication_lag` exception record, OCR scope decision, or
`scripts/verify_stage6_return.py`.

## Use This Only After The Owner Chooses Route A

Route A means:

1. the owner explicitly approves the `publication_lag` exception;
2. the owner explicitly selects OCR scope; and
3. the operator runs one real Stage 6 cycle on the v548 side-by-side lane; and
4. the completed template, logs, Excel proof, audit proof, and sign-offs are
   returned for verification.

If the owner chooses Route B, do not run the owner sign-off cycle yet. Keep
v1.0 on hold until enough FY2026/R8 target-form PDFs are public.

## Fixed Values To Copy Into The E2E Template

| E2E field | Value |
| --- | --- |
| EIDP package commit | `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be` |
| core ZIP ファイル名 | `eidp-windows-v548.zip` |
| core ZIP sha256 | `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c` |
| transferred ZIP | `C:\EIDP-staging\eidp-windows-v548.zip` |
| Windows extract path | `%USERPROFILE%\EIDP-v548-c1a9690-env0` |
| current active root to preserve | `%USERPROFILE%\EIDP-v527-69fe81f-env0` |
| non-Windows release gate | `logs/eidp-windows-v548-release-gates-20260621.json` -> `ok=true` |
| GitHub main CI | packaged source commit c1a9690: CI `27900695351` -> success; latest docs/worksheet commit 900168c: CI `27902936247` -> success; docs-only handoff commits do not change packaged runtime; re-check current main CI before release approval |
| Windows validation evidence | `docs/reports/2026-06-21-v548-windows-canary.md` |
| OCR runtime evidence | v548 OCR runtime validation is not complete; required if OCR remains in v1.0 scope |
| setup validation evidence | `docs/reports/2026-06-21-v548-windows-canary.md` records after-setup validator `ok=true` |
| after-weekly validation evidence | `docs/reports/2026-06-21-v548-windows-canary.md` records after-weekly validator `ok=true` |
| bounded canary evidence | strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate` |
| Stage 6 evidence verify | `logs/win-v548-c1a9690-canary/stage6-evidence-verify-20260621-200255.json` -> `ok=true` |
| release exception reason | `publication_lag` if Route A is chosen |
| mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` |
| mature-year proof years | `2025` |

The v548 bounded canary is side-by-side smoke evidence only. It is not owner
real-cycle sign-off evidence.

The v548 false-reject worksheet is also not approval evidence yet. Its current
validation summary reports `completed_decisions=0`, `blank_decisions=53`, and
`context_mismatch_count=0`.

## Short Owner Decision Form

Use `docs/runbooks/eidp-v548-release-summary.md` as the owner-facing one-page
summary and `docs/runbooks/eidp-v548-owner-signoff.md` as the short owner
decision form. Do not ask the owner to manually fill or reproduce the
engineering checklist.

For v548, current evidence supports `NOT_READY` only. `publication_lag`
approval can support at most `RC_ONLY` after all required return evidence is
complete. It must not allow unconfirmed rows into final Excel output.

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
| OCR scope 決定 | `core_non_ocr_only` or `ocr_addon_verified` |
| Owner sign-off | name, date, decision |
| 業務員 sign-off | name, date, decision |

## Files To Return

- completed `eidp-operator-e2e-template.md`
- approved `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- selected OCR scope decision
- `data\output\last_run.json`
- latest `logs\run-*.log`
- latest `logs\diagnostics-*.txt`
- latest `logs\stage6-evidence-*.zip`
- latest `logs\stage6-evidence-verify-*.json`
- v548 setup validation evidence
- v548 active-task recovery JSON
- Excel output proof or redacted workbook metadata
- ManualActionLog / JSONL outbox proof
- completed false-reject review worksheet if claiming a discovery/classifier/year
  evidence false reject:
  `docs/reports/2026-06-21-v548-false-reject-review-sheet.csv`
- generated false-reject review audit JSONL if submitting that worksheet:
  `docs/reports/2026-06-21-v548-false-reject-review-audit-log.jsonl`
- optional read-only triage guide for that worksheet:
  `docs/reports/2026-06-21-v548-false-reject-review-summary.md`

## False-Reject RCA Worksheet

Use this only to support or reject the claim that the below-gate FY2026/R8
yield is caused by material discovery/classifier/year-evidence false rejects.
It does not relax the Excel-ready gate and does not allow rejected rows into the
final Excel output.

Worksheet to fill:

```text
docs/reports/2026-06-21-v548-false-reject-review-sheet.csv
```

Read-only triage guide:

```text
docs/reports/2026-06-21-v548-false-reject-review-summary.md
```

The summary groups non-binding suggested decisions and priority rows.
This is read-only triage guidance. It does not fill the worksheet, approve
rejected rows, or allow any row into Excel.

Fill only these columns:

| Column | Required value |
| --- | --- |
| `decision` | `false_reject`, `correct_reject`, or `needs_operator_review` |
| `reviewer` | owner/operator reviewer name or stable reviewer ID |
| `reviewed_at` | ISO timestamp, for example `2026-06-21T09:30:00+09:00` |
| `notes` | required for `false_reject` and `needs_operator_review`; recommended for any difficult row |

Do not edit `audit_row_id`, `bucket`, school/document fields, URLs, anchor
text, review questions, or false-reject signals. Those columns are immutable
row context; if they change, developer validation must reject the worksheet.

Decision meanings:

- `false_reject`: official FY2026/R8 evidence proves the row should have been
  accepted or routed differently.
- `correct_reject`: the row is old-year, non-target, unknown-year, mismatched,
  unsupported, or otherwise correctly blocked.
- `needs_operator_review`: there is plausible official evidence, but it needs a
  human decision before it can affect any workflow or Excel output.

Developer validation is run from current `main` after the returned CSV is
copied back to the repo. The staged v548 package proves the verifier and helper
were packaged for the v548 canary, while current `main` carries the regenerated
v548 worksheet, worklist, validation summary, and RCA summary. Validate this
v548 worksheet from current `main` unless a later package supersedes v548.
Current `main` also emits a compact `false_reject_review_summary` in the JSON
result for easier owner/developer handoff; this is a convenience field only and
does not change `ok`, `errors`, `review_status=complete`, or
`context_mismatch_count=0` release gates.
Current `main` can also render completed false-reject worksheet decisions as a
JSONL audit log. This is an audit handoff artifact only; it does not write to
business tables, approve rejected rows, or relax Excel-ready gates.

For row-by-row review, use
`docs/reports/2026-06-21-v548-false-reject-review-worklist.md`. It is a
read-only worklist generated with the same `--sample-size 12` as the v548 CSV,
so its `53` rows correspond to the worksheet. The worklist is not a return
artifact; only the completed CSV worksheet is validated.

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
  --publication-lag-decision-brief docs/release/owner-decisions/publication-lag.md \
  --ocr-scope-decision-brief docs/release/owner-decisions/ocr-scope.md \
  --owner-signoff docs/runbooks/eidp-v548-owner-signoff.md \
  --expected-package-sha256 488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c \
  --expected-source-commit c1a96903ed10f1cc9c48d1a6912061ba0aaf86be \
  --false-reject-evidence-zip logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --false-reject-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --false-reject-review-audit-log docs/reports/2026-06-21-v548-false-reject-review-audit-log.jsonl \
  --false-reject-sample-size 12 \
  --json
```

Release remains blocked unless this command returns `ok=true` and the approval
record, OCR scope, E2E sign-off fields, and short owner sign-off are complete.

If a completed false-reject review worksheet is returned outside the owner
return verifier, the same check can be run directly for debugging:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --sample-size 12 \
  --validate-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --require-decisions
```

This command must return `ok=true`, `review_status=complete`, and
`context_mismatch_count=0` before the worksheet can be used as RCA evidence.
For an owner-readable failure summary while the worksheet is still incomplete,
rerun the same command with:

```bash
  --format review-validation-summary
```

After the worksheet validates, generate the RCA framing summary with:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --sample-size 12 \
  --validate-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --require-decisions \
  --format review-rca-summary
```

That summary distinguishes `SPECIFIC_RULE_DEFECTS_FOUND` from
`GENERIC_MODEL_FAILURE_NOT_SUPPORTED`. It is still read-only RCA evidence: it
does not relax strict FY2026/R8 evidence rules, does not approve rejected rows,
and does not replace the full owner return gate.

After the returned CSV is complete, the developer can validate it and generate
the per-row audit JSONL in one current-main command:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --sample-size 12 \
  --validate-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --require-decisions \
  --write-review-audit-log docs/reports/2026-06-21-v548-false-reject-review-audit-log.jsonl \
  --json
```

Each JSONL row records the immutable worksheet context hash, reviewer,
`reviewed_at`, decision, notes, source archive, and strict-gate forecast. Blank
worksheet decisions do not generate audit events. The audit log remains RCA
handoff evidence only; it still does not make any rejected row Excel-ready.
The `--write-review-audit-log` convenience option is a current-main developer
validation step after owner return; it must not be treated as v548 runtime
release approval.

If the audit JSONL must be rendered separately, use:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --sample-size 12 \
  --validate-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --require-decisions \
  --format review-audit-log \
  --output docs/reports/2026-06-21-v548-false-reject-review-audit-log.jsonl
```

To regenerate the row-by-row owner worklist from the v548 Stage 6 evidence:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v548-c1a9690-canary/stage6-evidence-20260621-110254.zip \
  --sample-size 12 \
  --format review-worklist \
  --output docs/reports/2026-06-21-v548-false-reject-review-worklist.md
```
