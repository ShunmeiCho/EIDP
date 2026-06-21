# Publication-lag Owner Decision Brief

Status: decision required
Updated: 2026-06-21

This brief is for deciding whether v1 may use a `publication_lag` release
exception while the current target-year forms are not yet widely published.

It is not approval by itself. Approval still requires the formal exception
record, owner/operator evidence, and release-gate verification.

## What The Owner Chooses

Choose one:

- `APPROVE_RC_ONLY`: allow an internal release-candidate trial using the
  publication-lag exception.
- `DO_NOT_APPROVE`: do not use the exception; wait until the current target-year
  strict Excel-ready gate is met without the exception.
- `DEFER`: no release decision yet.

## Current v548 Evidence Snapshot

Release Forecast: `NOT_READY`

The current owner review baseline is v548:

- package: `dist/eidp-windows-v548.zip`
- package SHA256:
  `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`
- package/source commit:
  `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`
- current Windows canary:
  `docs/reports/2026-06-21-v548-windows-canary.md`
- current owner worksheet:
  `docs/reports/2026-06-21-v548-false-reject-review-sheet.csv`

The v548 bounded Windows canary selected `50` target-missing specialty schools,
found candidate sets for `50/50`, downloaded and processed `15` documents, and
accepted only `12/50 (24.0%)` as strict FY2026/R8 target-document plus
Excel-ready. Operator-reviewable yield was `47/50 (94.0%)`, with
`ship_gate_status=below_gate`.

The selected-school status was:

```text
confirmed_target=12
publication_lag=30
target_year_unverified=2
image_pending=3
review_or_parse=5
excel_ready=12
```

The current false-reject worksheet still has `53` blank owner decisions. The
developer shadow review found `0` likely false rejects, but it is diagnostic
only and is not release evidence.

Owner decision impact from the current v548 evidence:

| Owner choice | Release impact now |
| --- | --- |
| `APPROVE_RC_ONLY` | Can support only an `RC_ONLY` path after the formal exception record, owner real Windows cycle, completed worksheet return, audit log, and Stage 6 return verification all pass. |
| `DO_NOT_APPROVE` | Keeps release `NOT_READY` until the current target-year strict Excel-ready gate is met without the exception. |
| `DEFER` | Keeps release `NOT_READY`; no release-scope decision exists. |

## If Approved

Approval means:

- the release may be considered for `RC_ONLY`, not `READY`
- current target-year strict yield is acknowledged as below the active gate
- mature-year evidence may support a bounded trial decision
- publication-pending schools stay pending or reviewable
- unconfirmed rows must not enter final Excel output
- the owner/operator real Windows cycle is still required
- Stage 6 return verification is still required

Approval does not mean:

- FY2026/R8 strict yield is complete
- old-year PDFs may be counted as current-year success
- year-unknown target forms may enter Excel
- the Windows package is release-ready without current evidence
- v1 expands beyond vocational-school Windows operation

## Required Evidence Before Use

Before this decision can affect a release, the release packet must reference:

- `docs/reports/current-release-status.md`
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- current strict target-year Excel-ready yield
- mature-year proof, if the exception is used
- latest CI result
- latest Windows canary or real-PC evidence
- completed owner/operator return, if requesting release approval
- successful `scripts/verify_stage6_return.py` result for the selected release
  path

## Release Conclusion

- With no approval: `NOT_READY` if strict target-year yield is below gate.
- With approval but incomplete owner/operator evidence: still `NOT_READY`.
- With approval and complete evidence: at most `RC_ONLY`.
- `READY` requires the normal release gates to pass without treating the
  exception as strict target-year success.
