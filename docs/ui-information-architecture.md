# Operator UI Information Architecture

The operator UI should read as a yearly production workbench. It should not
expose implementation modules such as crawler, parser, or agent tooling as the
primary navigation model.

## Target Navigation

| Internal page id | Japanese label | Purpose |
| --- | --- | --- |
| `dashboard` | 年度ダッシュボード | Target fiscal year progress, blocked counts, readiness |
| `institution_queue` | 学校キュー | One row per institution with current blocker and next action |
| `institution_detail` | 学校詳細 | Authority index, site entry, documents, extracted metrics, audit history |
| `document_review` | 申請書PDF確認 | PDF evidence, extracted values, year evidence, identity match |
| `program_reconciliation` | 学科変更レビュー | New, discontinued, renamed, merged, or split programs |
| `authority_index` | 公式索引管理 | MEXT/prefecture index refresh, parse results, matching results |
| `workbook_export` | Excel出力 | Master/competition workbook preview, validation, export |
| `audit_log` | 監査ログ | Operator decisions, corrections, exports |
| `settings` | 設定 | Fiscal year, OCR, proxy, paths, thresholds |

## Current UI Rename Plan

| Current label | Target label |
| --- | --- |
| 学校別タスク | 学校キュー |
| PDF確認・手入力 | 申請書PDF確認 |
| 年度判定・修正 | 対象年度確認 |
| Excel プレビュー | Excel出力 |
| 都道府県公式インデックス | 公式索引管理 |
| URL候補レビュー | 情報公開ページ候補 |

The current implementation can keep existing page ids during the compatibility
phase. The first production-visible step is label cleanup, followed by adapters
that expose `Institution`, `SiteEntry`, `TargetDocument`, `Program`, and
`WorkbookExport` concepts while the old tables remain in place.

## Operator Queue Lanes

| Lane | Source states | Operator decision |
| --- | --- | --- |
| 情報公開ページなし | `site_entry_missing` | Add or approve official disclosure entry |
| PDF候補なし | `target_document_missing` | Wait for publication or investigate official entry |
| PDF候補確認 | `target_document_candidate_found` | Accept target form, reject non-target, or mark old year |
| 年度確認 | `target_document_year_unverified` | Confirm target fiscal year evidence |
| OCR/手入力 | `extraction_ocr_pending`, `extraction_parse_failed` | Run OCR, enter metrics manually, or reject |
| 学科変更確認 | `program_review_required` | Approve new/discontinued/renamed/merged/split programs |
| Excel出力可 | `workbook_ready` | Preview and export workbook |

## Non-Goals For This Phase

- No database table rename.
- No ORM class rename.
- No broad module move from `scraper/`, `pdf/`, `excel/`, or `review/`.
- No Agent-Reach entry point in the operator UI.
