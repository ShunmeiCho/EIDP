# Copilot / NotebookLM Data Policy

- Status: Proposed
- Date: 2026-07-05
- Scope: policy for comparison workflow only

## Policy Summary

Copilot and NotebookLM outputs may be used as operator-provided comparison
inputs only after owner/PI approves the data-handling policy. EIDP must not
automatically upload PDFs or extracted values to external services.

This policy does not implement any upload integration and does not approve
external processing.

## Allowed In The Proposed v1 Flow

Allowed, subject to owner/PI approval:

- operator manually runs Copilot/NotebookLM outside EIDP when permitted;
- operator imports or pastes the resulting extraction output into EIDP;
- EIDP compares external output against local EIDP extraction;
- EIDP highlights mismatches for human reconciliation;
- accepted values are recorded only after human review.

## Not Allowed In This Slice

Not allowed:

- automatic PDF upload to Copilot, NotebookLM, or any external service;
- hidden API calls from EIDP to external extraction tools;
- treating external output as authoritative without human review;
- writing external values into final Excel without acceptance evidence;
- uploading non-public PDFs, personal data, or confidential owner materials
  without explicit policy approval.

## Data Risk

Most EIDP source PDFs are public institutional disclosure documents, but the
workflow can still carry risk:

- users may accidentally include non-public PDFs;
- filenames or notes may include internal context;
- extracted sheets may contain reviewer notes;
- external services may retain prompts, files, or derived data;
- policy terms may differ between tenant, account, and region.

Therefore the default state is "manual import only; no automatic external
upload."

## Required Owner/PI Decisions

Owner/PI must decide:

- whether public disclosure PDFs may be uploaded manually to Copilot/NotebookLM;
- which accounts or tenants are allowed;
- whether operator notes may be included;
- whether outputs can be stored in EIDP;
- retention and deletion expectations;
- whether the comparison workflow is optional or required for v1.

## Minimum Record For Imported Output

If external output is imported, EIDP should record:

- source tool name;
- operator;
- timestamp;
- PDF identity or file hash when available;
- imported text/table payload;
- rows compared;
- mismatch decisions;
- final accepted value provenance.

## Release Boundary

Unresolved Copilot/NotebookLM policy keeps Linux/Web release at `NOT_READY` or
`RC_ONLY`, depending on owner decision. It must not be silently bypassed by
calling the comparison optional while still relying on it for release evidence.

