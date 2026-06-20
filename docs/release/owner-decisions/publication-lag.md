# Publication-lag Owner Decision Brief

Status: decision required

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
