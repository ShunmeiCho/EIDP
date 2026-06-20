# Owner Release Sign-off

Owner sign-off is intentionally short. The owner should not manually reproduce
CI logs, parser fixtures, ZIP inventory, Windows canary stdout, or release-gate
checklists. Those belong in the release evidence bundle prepared by the agent,
CI, Windows validation, and release engineering process.

The rule is:

```text
The sign-off form may be simple; the sign-off basis may not be simple.
```

## Required Inputs

Before owner sign-off is requested, the release packet must already contain:

- release summary
- release conclusion: `READY`, `RC_ONLY`, or `NOT_READY`
- package path and SHA256
- source commit and packaged commit
- latest CI result
- latest Windows canary or real-PC validation result
- current strict target-year Excel-ready yield
- known limitations
- release exceptions requiring owner approval
- current P0 blockers

The owner reads the release summary and signs only the business decision.
Short owner decision briefs live under `docs/release/owner-decisions/`; they
help choose a path, but they are not approval artifacts by themselves.

## Owner Sign-off Scope

The owner confirms only:

- which version, package, and commit are being decided
- whether the release conclusion is `READY`, `RC_ONLY`, or `NOT_READY`
- that v1 scope is vocational-school-first, one-operator Windows operation
- that university production workflow is outside v1
- that HTML demos, PPTX exports, and UI prototypes are not the production system
- which known limitations or release exceptions are accepted
- whether the package may be used for GA, RC trial, or not at all

The owner does not personally verify every technical checklist item.

## Operator Smoke Sign-off

Operator smoke sign-off is separate from owner release approval.

It proves only that the package is usable on the actual Windows environment:

1. unzip the package
2. run setup or start scripts
3. open the UI
4. inspect the school queue, PDF review, and Excel output pages
5. generate a preview or open an existing workbook output

Operator smoke sign-off does not approve GA by itself.

## Owner Release Sign-off

Owner release sign-off approves or rejects release risk. It covers:

- v1 scope
- known limitations
- strict target-year Excel-ready yield
- publication-lag handling
- OCR scope
- `RC_ONLY` or `READY` acceptance

`READY` requires all release gates and evidence to pass. `RC_ONLY` may be used
for limited trial when the owner accepts documented limitations. `NOT_READY`
means at least one P0 blocker remains.

## Publication-lag Exception

A publication-lag exception may be approved separately, but it is limited:

- it can support `RC_ONLY`
- it does not make the release `READY`
- publication-pending schools must remain reviewable or pending
- unconfirmed rows must not enter final Excel output

## OCR Scope Decision

OCR scope may be approved separately:

- v1 may release the text-PDF workflow without requiring full automatic OCR
  success
- image PDFs may enter OCR or manual review queues
- OCR output is not an automatic trust signal
- an OCR add-on, if advertised, still requires separate validation evidence

This turns OCR into an explicit known limitation instead of a vague release
blocker.

The short decision brief is
`docs/release/owner-decisions/ocr-scope.md`.

## Red Lines

The owner must not be asked to approve these as exceptions:

- unconfirmed data entering final Excel output
- prior-year PDFs being accepted as target-year evidence
- school-identity mismatches entering the target institution
- non-target PDFs entering business metrics
- university production workflow being silently included in v1

## Minimal Sign-off Form

For RC, patch, or internal trial decisions, this minimal form is sufficient:

```markdown
# EIDP Release Approval

Release: v___
Package SHA256: ___
Decision: READY / RC_ONLY / NOT_READY

- [ ] I have read the Release Summary and confirm the v1 vocational-school
      Windows operation scope.
- [ ] I understand the current known limitations and release exceptions.
- [ ] I approve the selected release decision.

Owner:
Date:
Signature:
```

GA may use the same evidence packet, but should retain the full release summary
and owner release sign-off together.
