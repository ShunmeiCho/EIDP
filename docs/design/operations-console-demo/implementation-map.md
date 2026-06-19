# Implementation Map

This map connects the demo prototype to the current Streamlit implementation.
It is intentionally documentation-only.

## Prototype Page To Streamlit Target

| Prototype page | Streamlit target | Current file | Future file |
| --- | --- | --- | --- |
| `ダッシュボード` | dashboard | `src/eidp/review/app.py` | `src/eidp/review/_pages/dashboard.py` |
| `公式PDF収集` | school queue / official PDF collection | `src/eidp/review/_pages/school_year_tasks.py` | `src/eidp/review/_pages/school_queue.py` |
| `PDF抽出・確認` | PDF review | `src/eidp/review/_pages/pdf_manual_entry.py` | `src/eidp/review/_pages/pdf_review.py` |
| `年度判定・前年差分` | fiscal-year review | `src/eidp/review/_pages/fiscal_year_override.py` | `src/eidp/review/_pages/fiscal_year_review.py` |
| `競合校Excel更新` | workbook export | `src/eidp/review/_pages/excel_preview.py` | `src/eidp/review/_pages/excel_export.py` |
| `設定` | settings | `src/eidp/review/_pages/settings_page.py` | keep / refactor |

## Required Production-Only Pages

The prototype does not cover every production workflow. Streamlit still needs:

- official index management
- school detail and evidence-chain view
- program reconciliation / school-course change review
- audit log and JSONL outbox management
- diagnostics and operator environment checks

## Implementation Rule

Extract layout, page language, and workflow intent from the prototype. Do not
copy generated JavaScript, mock state, or packed runtime code.
