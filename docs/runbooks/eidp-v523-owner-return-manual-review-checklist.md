# EIDP v523 Owner Return Manual Review Checklist

Status: required manual review companion for v523 owner-return evidence
Date: 2026-05-20

Use this checklist after `scripts/verify_stage6_return.py` returns `ok=true`.
The verifier is necessary, but it does not yet machine-enforce every returned
owner/operator artifact. Until a new package lane hardens the verifier, this
manual checklist covers the remaining release evidence.

## Inputs

Collect the returned files listed in
`docs/runbooks/eidp-v523-owner-request-20260520.txt`:

- completed `eidp-operator-e2e-template.md`
- `data\output\last_run.json`
- latest `logs\run-*.log`
- latest `logs\diagnostics-*.txt`
- latest `logs\stage6-evidence-*.zip`
- latest `logs\stage6-evidence-verify-*.json`
- ManualActionLog / JSONL audit proof
- Excel proof

Do not approve v1.0 if any returned file is missing, redacted beyond review, or
inconsistent with `last_run.json`.

## 1. Excel Proof

| Check | Pass condition |
| --- | --- |
| Output workbook path | Returned path exists in the evidence packet or redacted metadata identifies the workbook unambiguously |
| Workbook generation time | Timestamp is after the owner real-cycle run start |
| Fiscal year | Workbook evidence corresponds to the target FY in `last_run.json` |
| Excel-ready coverage | Workbook/excel summary matches the `target_pdf_excel_ready_*` or strict target-PDF metrics used in the owner template |
| Consistency | No mismatch between owner template KPI actuals, `last_run.json`, and workbook metadata |
| Redaction | No student PII is copied into PR text or public release notes |

Result:

```text
pass / fail
```

Reviewer notes:

```text

```

## 2. ManualActionLog / JSONL Audit Proof

| Check | Pass condition |
| --- | --- |
| Audit page status | Returned screenshot/metadata shows audit page can load or the API/query result is available |
| `manual_action_log` count | Count is present and non-negative; if operator actions were performed, count reflects them |
| JSONL outbox before flush | Before-flush count is recorded when outbox sync is exercised |
| JSONL outbox after flush | After-flush count is `0`, or a documented local/offline reason is recorded |
| `action_id` consistency | DB action IDs match JSONL action IDs; duplicates are `none` |
| Sensitive text | Raw operator free-text notes, API keys, and credentials are not exposed in public artifacts |

Result:

```text
pass / fail
```

Reviewer notes:

```text

```

## 3. Append-Only Data Evidence

| Check | Pass condition |
| --- | --- |
| `DepartmentYearly` rows | Row count/delta is returned or inferable from diagnostics/run log |
| `SupportRecipient` rows | Row count/delta is returned or inferable from diagnostics/run log |
| Append-only behavior | No evidence of destructive rewrite, table reset, or unexpected deletion |
| Source linkage | Created/updated rows can be traced to processed target PDFs or operator-confirmed review actions |

Result:

```text
pass / fail
```

Reviewer notes:

```text

```

## 4. OCR Scope

If OCR is in the release scope for the returned cycle:

| Check | Pass condition |
| --- | --- |
| Tesseract runtime | Evidence shows Tesseract is available |
| Japanese language data | Evidence shows `jpn` and `jpn_vert` are available |
| OCR usage boundary | OCR failures are reflected as review/failure evidence, not silent success |

If OCR is explicitly out of scope for the returned cycle, record the reason in
the owner template and do not count OCR-only cases as proven.

Result:

```text
pass / fail / n/a
```

Reviewer notes:

```text

```

## Final Manual Review Decision

Only mark this checklist as pass when every applicable section above is pass.
This checklist does not override the current FY2026/R8 strict-yield blocker or
the need for an approved `publication_lag` exception if that lane is used.

```text
pass / fail
```
