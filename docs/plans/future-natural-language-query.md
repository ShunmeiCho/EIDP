# Future Natural-Language Query Note

Status: Concept note only
Updated: 2026-05-05

This is not part of Sprint 8 v1.0.

The owner raised a possible future direction: allow nontechnical users to ask
questions about EIDP data in natural language, similar to a NotebookLM-style
assistant over the collected PDFs, extracted tables, audit logs, and Excel
outputs.

## Candidate Use Cases

- "今年 R8 の未採録校はどこですか"
- "東京都で対象比率が前年差で大きく変わった学校はどこですか"
- "この学校の数字は OCR 由来ですか、手入力ですか"
- "監査ログで先週修正された PDF を一覧にしてください"

## Data Sources

- SQLite tables
- `manual_action_log`
- `confidence_breakdown`
- weekly `last_run.json`
- generated Excel files
- stored PDFs and OCR text, if retained

## Guardrails

- SQL and file access must be read-only.
- The assistant must cite source rows, documents, or audit actions.
- It must not perform write operations.
- It must not replace the Excel preview/export approval workflow.

## Deferred Decisions

- local-only model vs internal hosted service;
- Japanese query handling;
- source citation format;
- whether PDFs are indexed as text, images, or both;
- retention policy for OCR text.
