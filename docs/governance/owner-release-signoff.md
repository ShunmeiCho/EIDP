# Owner Release Sign-off

Owner sign-off is a business risk decision backed by technical evidence. The
owner does not reproduce CI, extraction fixtures, or server checks manually.

## Required Evidence

Before requesting a release decision, the packet must contain:

- release version and source commit;
- conclusion: `READY`, `RC_ONLY`, or `NOT_READY`;
- CI result and served-app smoke result;
- Venus deployment root and virtual-environment verification;
- business-computer intranet reachability evidence;
- correct-PDF intake, review, comparison, audit, and Excel-output evidence;
- SQLite backup/restore result and single-writer verification;
- known limitations and open P0 blockers.

## Separate Decisions

- Operator smoke proves the browser workflow is usable from the intended
  business network. It does not approve release by itself.
- Owner sign-off accepts or rejects the remaining business risk.
- OCR may remain an exception/manual-review path, but OCR output is never an
  automatic trust signal.

## Red Lines

The owner cannot waive these controls:

- unconfirmed data entering final Excel output;
- prior-year PDFs being accepted as target-year evidence;
- school-identity mismatches entering the target institution;
- non-target PDFs entering business metrics;
- writes that bypass the audit log or single-writer lock;
- exposing the Web app without the approved network/authentication boundary.

## Minimal Form

```markdown
# EIDP Release Approval

Release: v___
Commit: ___
Decision: READY / RC_ONLY / NOT_READY

- [ ] I reviewed the Linux/Web release summary and known limitations.
- [ ] I reviewed the served-app and business-network evidence.
- [ ] I approve the selected release decision.

Owner:
Date:
Signature:
```
