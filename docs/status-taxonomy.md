# EIDP Status Taxonomy

This taxonomy separates object state, next action, and blocking reason. The
current database still stores several legacy strings; new code should route them
through the domain taxonomy in `src/eidp/domain/`.

## Rules

- Object states use `<object>_<state>`.
- Next actions use `<verb>_<object>`.
- Blocking reasons describe why a row cannot progress.
- UI labels are separate from machine values.
- Search-derived and Agent-Reach-derived candidates are review inputs, not
  accepted site entries or target documents.

## Site Entry Status

| Machine value | Japanese label | Operator next action |
| --- | --- | --- |
| `site_entry_missing` | 情報公開ページなし | 情報公開ページを追加してください |
| `site_entry_from_authority_index` | 公式索引由来 | 入口ページからPDF候補を確認してください |
| `site_entry_from_official_site` | 公式サイト由来 | 入口ページの妥当性を確認してください |
| `site_entry_operator_provided` | 担当者登録済 | 登録URLを確認しPDF取得へ進んでください |
| `site_entry_unreachable` | 入口ページ取得不可 | URL、証明書、ネットワークを確認してください |
| `site_entry_low_confidence` | 低信頼候補 | 候補URLを採用または却下してください |
| `site_entry_rejected` | 却下済 | 別の公式入口を探してください |

## Target Document Status

| Machine value | Japanese label | Operator next action |
| --- | --- | --- |
| `target_document_missing` | 申請書PDFなし | 公式入口から対象PDFを探してください |
| `target_document_candidate_found` | PDF候補あり | PDF候補を分類してください |
| `target_document_year_unverified` | 対象年度未確認 | 年度根拠を確認してください |
| `target_document_confirmed` | 申請書PDF確認済 | 抽出結果を確認してください |
| `target_document_prior_year_available` | 旧年度PDFあり | 公示待ちか旧年度のみか確認してください |
| `target_document_not_yet_published` | 未公表 | 公示待ちとして記録してください |
| `target_document_non_target_only` | 対象外PDFのみ | 公式入口または候補を見直してください |
| `target_document_download_failed` | PDF取得失敗 | 再取得またはURL修正をしてください |

## Extraction Status

| Machine value | Japanese label | Operator next action |
| --- | --- | --- |
| `extraction_not_started` | 未抽出 | 抽出を実行してください |
| `extraction_text_extracted` | テキスト抽出済 | 表抽出結果を確認してください |
| `extraction_ocr_required` | OCR必要 | OCR add-onを確認してください |
| `extraction_ocr_pending` | OCR待ち | OCRまたは手入力を実施してください |
| `extraction_ocr_failed` | OCR失敗 | 手入力または再処理してください |
| `extraction_parsed` | 抽出済 | 年度・学校名・学科を確認してください |
| `extraction_parse_failed` | 抽出失敗 | PDF確認または手入力をしてください |
| `extraction_review_required` | 抽出レビュー必要 | 信頼度と差分を確認してください |
| `extraction_accepted` | 抽出承認済 | Excel出力対象に進めてください |

## Program Reconciliation Status

| Machine value | Japanese label | Operator next action |
| --- | --- | --- |
| `program_matched` | 学科一致 | 次の確認へ進んでください |
| `program_new_detected` | 新設学科候補 | 新設か表記揺れか確認してください |
| `program_discontinued_detected` | 廃止学科候補 | 廃止か名称変更か確認してください |
| `program_rename_candidate` | 名称変更候補 | 旧学科との対応を確認してください |
| `program_merge_candidate` | 統合候補 | 統合元と統合先を確認してください |
| `program_split_candidate` | 分割候補 | 分割元と分割先を確認してください |
| `program_review_required` | 学科変更確認 | 変更内容を承認または修正してください |
| `program_accepted` | 学科変更承認済 | 年度データを確定してください |

## Workbook Readiness Status

| Machine value | Japanese label | Operator next action |
| --- | --- | --- |
| `workbook_not_ready` | Excel未準備 | 未解決タスクを処理してください |
| `workbook_review_pending` | Excel確認待ち | 出力前チェックを確認してください |
| `workbook_ready` | Excel出力可 | Excelを出力してください |
| `workbook_exported` | Excel出力済 | 出力履歴と監査ログを確認してください |
| `workbook_blocked_by_file_lock` | ファイルロック中 | Excelを閉じて再実行してください |

## Legacy Mapping

| Legacy field/value | Domain mapping |
| --- | --- |
| `url_status=no_url` | `site_entry_missing` |
| `url_status=pref_url` | `site_entry_from_authority_index` |
| `url_status=operator_url` | `site_entry_operator_provided` |
| `pdf_status=none` | `target_document_missing` |
| `pdf_status=discovered` | `target_document_candidate_found` |
| `pdf_status=confirmed_target` | `target_document_confirmed` |
| `pdf_status=publication_lag` | `target_document_not_yet_published` |
| `pdf_status=target_year_unverified` | `target_document_year_unverified` |
| `pdf_status=rejected_stale` | `target_document_prior_year_available` |
| `pdf_status=image_pending` | `extraction_ocr_pending` |
| `extract_status=parse_failed` | `extraction_parse_failed` |
| `blocking_reason=dept_change_review` | `program_change_review` |
