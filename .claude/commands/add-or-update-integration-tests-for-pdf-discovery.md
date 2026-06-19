---
name: add-or-update-integration-tests-for-pdf-discovery
description: Workflow command scaffold for add-or-update-integration-tests-for-pdf-discovery in EIDP.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-or-update-integration-tests-for-pdf-discovery

Use this workflow when working on **add-or-update-integration-tests-for-pdf-discovery** in `EIDP`.

## Goal

Add or expand integration tests to cover new or existing fault cases in the PDF discovery pipeline, ensuring batch isolation and robustness.

## Common Files

- `tests/integration/test_fault_injection_pdf_discovery.py`
- `src/eidp/scraper/pdf_discovery.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Modify or add integration test files in tests/integration/ (especially test_fault_injection_pdf_discovery.py)
- If needed, update src/eidp/scraper/pdf_discovery.py to support new testable behaviors
- Document or assert new batch isolation/fault contracts in tests

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.