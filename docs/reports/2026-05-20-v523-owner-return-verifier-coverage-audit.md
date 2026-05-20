# v523 Owner Return Verifier Coverage Audit

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Scope: `scripts/verify_stage6_return.py`, `tests/unit/test_stage6_return_verifier.py`,
`docs/runbooks/eidp-operator-e2e-template.md`, and
`docs/runbooks/eidp-v523-owner-request-20260520.txt`

## Purpose

Check whether a future green `scripts/verify_stage6_return.py` result would, by
itself, cover every owner/operator return item required for v1.0 approval.

## Coverage

| Return requirement | Current machine coverage | Verdict |
| --- | --- | --- |
| `last_run.json` status, `finished_at`, `dry_run=false`, `current_fy` | Enforced by `_verify_last_run()` | covered |
| `target_pdf_auto_yield_pct`, `operator_reviewable_yield_pct`, and `ship_gate_status` consistency | Enforced by `_verify_last_run()` and `ship_gate_status_from_weekly_metrics()` | covered |
| Stage 6 evidence verifier `ok=true` and required labels | Enforced by `_verify_evidence_verify_json()` for `build_info`, `diagnostics`, `last_run`, `stage6_recovery`, and `weekly_run_logs` | covered |
| E2E KPI rows | Enforced for `ship_readiness_rc`, `strict target PDF 自動取得率`, and `推定手作業率` | covered for these rows only |
| Owner/operator release rows and sign-off blocks | Enforced for `業務員 PC 1 サイクル完了=yes`, `KPI owner 承認=yes`, `残 P0/P1 bug=none`, conclusion `go`, owner sign-off, and operator sign-off | covered |
| `publication_lag` exception record | Enforced only when `--release-exception-reason publication_lag` is used; requires `Status: APPROVED`, `Decision: APPROVED`, approver, approval date, and FY2026/R8 acknowledgement | covered |
| Mature-year proof for exception path | Enforced for `ok=true`, expected metric basis, production-scale denominator, strict yield, manual workload, denominator scope, and fiscal year before target FY | covered |
| Excel proof: workbook path, redacted workbook metadata, and Excel-ready consistency with DB/run metrics | Required by `eidp-v523-owner-request-20260520.txt`, but not parsed by `verify_stage6_return.py` | not machine-enforced |
| ManualActionLog proof: audit page status, `manual_action_log` count, pending JSONL outbox count before/after flush, and `action_id` consistency | Required by `eidp-v523-owner-request-20260520.txt`, and template section 7 records these fields, but `verify_stage6_return.py` does not parse or enforce them | not machine-enforced |
| `DepartmentYearly` / `SupportRecipient` append-only evidence from the owner cycle | Present indirectly through `last_run` and evidence bundle, but not independently checked by the return verifier | partially covered |
| OCR scope decision and OCR add-on/runtime proof in the returned owner packet | v523 Windows smoke already has OCR runtime proof; the return verifier only checks generic evidence labels and does not parse an OCR-specific owner-cycle row | partially covered |

## Verdict

`verify_stage6_return.py` is strong enough to block KPI-threshold mistakes,
unapproved `publication_lag` release exceptions, missing owner/operator
sign-off, and incomplete Stage 6 evidence labels.

It is not sufficient by itself to accept a real owner cycle. Until the verifier
is extended, Excel proof and ManualActionLog / JSONL audit proof must still be
reviewed manually against the returned files listed in
`docs/runbooks/eidp-v523-owner-request-20260520.txt`.

Current release status remains **NOT COMPLETE**.
