"""Operator-facing workflow status taxonomy."""

from enum import StrEnum


class SiteEntryStatus(StrEnum):
    MISSING = "site_entry_missing"
    DISCOVERED_FROM_AUTHORITY_INDEX = "site_entry_from_authority_index"
    DISCOVERED_FROM_OFFICIAL_SITE = "site_entry_from_official_site"
    OPERATOR_PROVIDED = "site_entry_operator_provided"
    UNREACHABLE = "site_entry_unreachable"
    LOW_CONFIDENCE = "site_entry_low_confidence"
    REJECTED = "site_entry_rejected"


class TargetDocumentStatus(StrEnum):
    MISSING = "target_document_missing"
    CANDIDATE_FOUND = "target_document_candidate_found"
    YEAR_UNVERIFIED = "target_document_year_unverified"
    CONFIRMED = "target_document_confirmed"
    PRIOR_YEAR_AVAILABLE = "target_document_prior_year_available"
    NOT_YET_PUBLISHED = "target_document_not_yet_published"
    NON_TARGET_ONLY = "target_document_non_target_only"
    DOWNLOAD_FAILED = "target_document_download_failed"


class ExtractionStatus(StrEnum):
    NOT_STARTED = "extraction_not_started"
    TEXT_EXTRACTED = "extraction_text_extracted"
    OCR_REQUIRED = "extraction_ocr_required"
    OCR_PENDING = "extraction_ocr_pending"
    OCR_FAILED = "extraction_ocr_failed"
    PARSED = "extraction_parsed"
    PARSE_FAILED = "extraction_parse_failed"
    REVIEW_REQUIRED = "extraction_review_required"
    ACCEPTED = "extraction_accepted"


class ProgramReconciliationStatus(StrEnum):
    MATCHED = "program_matched"
    NEW_PROGRAM_DETECTED = "program_new_detected"
    DISCONTINUED_PROGRAM_DETECTED = "program_discontinued_detected"
    RENAME_CANDIDATE = "program_rename_candidate"
    MERGE_CANDIDATE = "program_merge_candidate"
    SPLIT_CANDIDATE = "program_split_candidate"
    OPERATOR_REVIEW_REQUIRED = "program_review_required"
    ACCEPTED = "program_accepted"


class WorkbookReadinessStatus(StrEnum):
    NOT_READY = "workbook_not_ready"
    REVIEW_PENDING = "workbook_review_pending"
    READY = "workbook_ready"
    EXPORTED = "workbook_exported"
    BLOCKED_BY_FILE_LOCK = "workbook_blocked_by_file_lock"


type WorkflowStatus = (
    SiteEntryStatus
    | TargetDocumentStatus
    | ExtractionStatus
    | ProgramReconciliationStatus
    | WorkbookReadinessStatus
)

WORKFLOW_STATUS_JA_LABELS: dict[WorkflowStatus, str] = {
    SiteEntryStatus.MISSING: "情報公開ページなし",
    SiteEntryStatus.DISCOVERED_FROM_AUTHORITY_INDEX: "公式索引由来",
    SiteEntryStatus.DISCOVERED_FROM_OFFICIAL_SITE: "公式サイト由来",
    SiteEntryStatus.OPERATOR_PROVIDED: "担当者登録済",
    SiteEntryStatus.UNREACHABLE: "入口ページ取得不可",
    SiteEntryStatus.LOW_CONFIDENCE: "低信頼候補",
    SiteEntryStatus.REJECTED: "却下済",
    TargetDocumentStatus.MISSING: "申請書PDFなし",
    TargetDocumentStatus.CANDIDATE_FOUND: "PDF候補あり",
    TargetDocumentStatus.YEAR_UNVERIFIED: "対象年度未確認",
    TargetDocumentStatus.CONFIRMED: "申請書PDF確認済",
    TargetDocumentStatus.PRIOR_YEAR_AVAILABLE: "旧年度PDFあり",
    TargetDocumentStatus.NOT_YET_PUBLISHED: "未公表",
    TargetDocumentStatus.NON_TARGET_ONLY: "対象外PDFのみ",
    TargetDocumentStatus.DOWNLOAD_FAILED: "PDF取得失敗",
    ExtractionStatus.NOT_STARTED: "未抽出",
    ExtractionStatus.TEXT_EXTRACTED: "テキスト抽出済",
    ExtractionStatus.OCR_REQUIRED: "OCR必要",
    ExtractionStatus.OCR_PENDING: "OCR待ち",
    ExtractionStatus.OCR_FAILED: "OCR失敗",
    ExtractionStatus.PARSED: "抽出済",
    ExtractionStatus.PARSE_FAILED: "抽出失敗",
    ExtractionStatus.REVIEW_REQUIRED: "抽出レビュー必要",
    ExtractionStatus.ACCEPTED: "抽出承認済",
    ProgramReconciliationStatus.MATCHED: "学科一致",
    ProgramReconciliationStatus.NEW_PROGRAM_DETECTED: "新設学科候補",
    ProgramReconciliationStatus.DISCONTINUED_PROGRAM_DETECTED: "廃止学科候補",
    ProgramReconciliationStatus.RENAME_CANDIDATE: "名称変更候補",
    ProgramReconciliationStatus.MERGE_CANDIDATE: "統合候補",
    ProgramReconciliationStatus.SPLIT_CANDIDATE: "分割候補",
    ProgramReconciliationStatus.OPERATOR_REVIEW_REQUIRED: "学科変更確認",
    ProgramReconciliationStatus.ACCEPTED: "学科変更承認済",
    WorkbookReadinessStatus.NOT_READY: "Excel未準備",
    WorkbookReadinessStatus.REVIEW_PENDING: "Excel確認待ち",
    WorkbookReadinessStatus.READY: "Excel出力可",
    WorkbookReadinessStatus.EXPORTED: "Excel出力済",
    WorkbookReadinessStatus.BLOCKED_BY_FILE_LOCK: "ファイルロック中",
}

WORKFLOW_STATUS_NEXT_ACTIONS: dict[WorkflowStatus, str] = {
    SiteEntryStatus.MISSING: "情報公開ページを追加してください",
    SiteEntryStatus.DISCOVERED_FROM_AUTHORITY_INDEX: "入口ページからPDF候補を確認してください",
    SiteEntryStatus.DISCOVERED_FROM_OFFICIAL_SITE: "入口ページの妥当性を確認してください",
    SiteEntryStatus.OPERATOR_PROVIDED: "登録URLを確認しPDF取得へ進んでください",
    SiteEntryStatus.UNREACHABLE: "URL、証明書、ネットワークを確認してください",
    SiteEntryStatus.LOW_CONFIDENCE: "候補URLを採用または却下してください",
    SiteEntryStatus.REJECTED: "別の公式入口を探してください",
    TargetDocumentStatus.MISSING: "公式入口から対象PDFを探してください",
    TargetDocumentStatus.CANDIDATE_FOUND: "PDF候補を分類してください",
    TargetDocumentStatus.YEAR_UNVERIFIED: "年度根拠を確認してください",
    TargetDocumentStatus.CONFIRMED: "抽出結果を確認してください",
    TargetDocumentStatus.PRIOR_YEAR_AVAILABLE: "公示待ちか旧年度のみか確認してください",
    TargetDocumentStatus.NOT_YET_PUBLISHED: "公示待ちとして記録してください",
    TargetDocumentStatus.NON_TARGET_ONLY: "公式入口または候補を見直してください",
    TargetDocumentStatus.DOWNLOAD_FAILED: "再取得またはURL修正をしてください",
    ExtractionStatus.NOT_STARTED: "抽出を実行してください",
    ExtractionStatus.TEXT_EXTRACTED: "表抽出結果を確認してください",
    ExtractionStatus.OCR_REQUIRED: "OCR add-onを確認してください",
    ExtractionStatus.OCR_PENDING: "OCRまたは手入力を実施してください",
    ExtractionStatus.OCR_FAILED: "手入力または再処理してください",
    ExtractionStatus.PARSED: "年度・学校名・学科を確認してください",
    ExtractionStatus.PARSE_FAILED: "PDF確認または手入力をしてください",
    ExtractionStatus.REVIEW_REQUIRED: "信頼度と差分を確認してください",
    ExtractionStatus.ACCEPTED: "Excel出力対象に進めてください",
    ProgramReconciliationStatus.MATCHED: "次の確認へ進んでください",
    ProgramReconciliationStatus.NEW_PROGRAM_DETECTED: "新設か表記揺れか確認してください",
    ProgramReconciliationStatus.DISCONTINUED_PROGRAM_DETECTED: "廃止か名称変更か確認してください",
    ProgramReconciliationStatus.RENAME_CANDIDATE: "旧学科との対応を確認してください",
    ProgramReconciliationStatus.MERGE_CANDIDATE: "統合元と統合先を確認してください",
    ProgramReconciliationStatus.SPLIT_CANDIDATE: "分割元と分割先を確認してください",
    ProgramReconciliationStatus.OPERATOR_REVIEW_REQUIRED: "変更内容を承認または修正してください",
    ProgramReconciliationStatus.ACCEPTED: "年度データを確定してください",
    WorkbookReadinessStatus.NOT_READY: "未解決タスクを処理してください",
    WorkbookReadinessStatus.REVIEW_PENDING: "出力前チェックを確認してください",
    WorkbookReadinessStatus.READY: "Excelを出力してください",
    WorkbookReadinessStatus.EXPORTED: "出力履歴と監査ログを確認してください",
    WorkbookReadinessStatus.BLOCKED_BY_FILE_LOCK: "Excelを閉じて再実行してください",
}

LEGACY_URL_STATUS_TO_SITE_ENTRY_STATUS: dict[str, SiteEntryStatus] = {
    "no_url": SiteEntryStatus.MISSING,
    "pref_url": SiteEntryStatus.DISCOVERED_FROM_AUTHORITY_INDEX,
    "operator_url": SiteEntryStatus.OPERATOR_PROVIDED,
    "unknown": SiteEntryStatus.DISCOVERED_FROM_OFFICIAL_SITE,
}

LEGACY_PDF_STATUS_TO_TARGET_DOCUMENT_STATUS: dict[str, TargetDocumentStatus] = {
    "none": TargetDocumentStatus.MISSING,
    "discovered": TargetDocumentStatus.CANDIDATE_FOUND,
    "confirmed_target": TargetDocumentStatus.CONFIRMED,
    "publication_lag": TargetDocumentStatus.NOT_YET_PUBLISHED,
    "target_year_unverified": TargetDocumentStatus.YEAR_UNVERIFIED,
    "site_error": TargetDocumentStatus.DOWNLOAD_FAILED,
    "rejected_stale": TargetDocumentStatus.PRIOR_YEAR_AVAILABLE,
}

LEGACY_EXTRACT_STATUS_TO_EXTRACTION_STATUS: dict[str, ExtractionStatus] = {
    "none": ExtractionStatus.NOT_STARTED,
    "parsed": ExtractionStatus.PARSED,
    "manual_entered": ExtractionStatus.ACCEPTED,
    "ocr_pending": ExtractionStatus.OCR_PENDING,
    "parse_failed": ExtractionStatus.PARSE_FAILED,
}

LEGACY_BLOCKING_REASON_TO_WORKFLOW_STATUS: dict[str, WorkflowStatus] = {
    "no_url": SiteEntryStatus.MISSING,
    "no_target_pdf": TargetDocumentStatus.MISSING,
    "publication_lag_latest_public": TargetDocumentStatus.NOT_YET_PUBLISHED,
    "target_year_unverified": TargetDocumentStatus.YEAR_UNVERIFIED,
    "tls_certificate_verify_failed": SiteEntryStatus.UNREACHABLE,
    "stale_pdf_only": TargetDocumentStatus.PRIOR_YEAR_AVAILABLE,
    "ocr_pending": ExtractionStatus.OCR_PENDING,
    "parse_failed": ExtractionStatus.PARSE_FAILED,
    "not_extracted": ExtractionStatus.NOT_STARTED,
    "review_required": ExtractionStatus.REVIEW_REQUIRED,
    "dept_change_review": ProgramReconciliationStatus.OPERATOR_REVIEW_REQUIRED,
}


def workflow_status_ja_label(status: WorkflowStatus) -> str:
    return WORKFLOW_STATUS_JA_LABELS[status]
