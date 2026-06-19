---
name: update-release-documentation
description: Workflow command scaffold for update-release-documentation in EIDP.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-release-documentation

Use this workflow when working on **update-release-documentation** in `EIDP`.

## Goal

Refresh and record release status, checklists, and exception evidence for a new release cycle.

## Common Files

- `docs/reports/eidp-current-objective-evidence-checklist.md`
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `docs/reports/2026-06-19-v530-windows-connectivity-recheck.md`
- `docs/runbooks/eidp-v1-release-admin-checklist.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update or create release exception record in docs/reports/
- Update the current objective evidence checklist in docs/reports/eidp-current-objective-evidence-checklist.md
- Update or refresh the admin checklist in docs/runbooks/eidp-v1-release-admin-checklist.md (if needed)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.