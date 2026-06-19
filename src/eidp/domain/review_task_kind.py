"""Controlled operator review task taxonomy."""

from enum import StrEnum


class ReviewTaskKind(StrEnum):
    SITE_ENTRY_REQUIRED = "site_entry_required"
    SITE_ENTRY_CANDIDATE_REVIEW = "site_entry_candidate_review"
    TARGET_DOCUMENT_YEAR_REVIEW = "target_document_year_review"
    TARGET_DOCUMENT_IDENTITY_REVIEW = "target_document_identity_review"
    OCR_OR_MANUAL_ENTRY_REQUIRED = "ocr_or_manual_entry_required"
    PROGRAM_CHANGE_REVIEW = "program_change_review"
    YOY_ANOMALY_REVIEW = "yoy_anomaly_review"
    AUTHORITY_INDEX_REMARK_REVIEW = "authority_index_remark_review"
    WORKBOOK_EXPORT_BLOCKED = "workbook_export_blocked"


REVIEW_TASK_KIND_JA_LABELS: dict[ReviewTaskKind, str] = {
    ReviewTaskKind.SITE_ENTRY_REQUIRED: "情報公開ページの追加が必要",
    ReviewTaskKind.SITE_ENTRY_CANDIDATE_REVIEW: "URL候補の確認が必要",
    ReviewTaskKind.TARGET_DOCUMENT_YEAR_REVIEW: "対象年度の確認が必要",
    ReviewTaskKind.TARGET_DOCUMENT_IDENTITY_REVIEW: "学校名一致の確認が必要",
    ReviewTaskKind.OCR_OR_MANUAL_ENTRY_REQUIRED: "OCRまたは手入力が必要",
    ReviewTaskKind.PROGRAM_CHANGE_REVIEW: "学科変更の確認が必要",
    ReviewTaskKind.YOY_ANOMALY_REVIEW: "前年差分の確認が必要",
    ReviewTaskKind.AUTHORITY_INDEX_REMARK_REVIEW: "公式索引の備考確認が必要",
    ReviewTaskKind.WORKBOOK_EXPORT_BLOCKED: "Excel出力前の確認が必要",
}

REVIEW_TASK_NEXT_ACTIONS: dict[ReviewTaskKind, str] = {
    ReviewTaskKind.SITE_ENTRY_REQUIRED: "公式の情報公開ページを登録してください",
    ReviewTaskKind.SITE_ENTRY_CANDIDATE_REVIEW: "候補URLを採用または却下してください",
    ReviewTaskKind.TARGET_DOCUMENT_YEAR_REVIEW: "PDF本文または公式ページで対象年度を確認してください",
    ReviewTaskKind.TARGET_DOCUMENT_IDENTITY_REVIEW: "PDFの学校名と対象校の一致を確認してください",
    ReviewTaskKind.OCR_OR_MANUAL_ENTRY_REQUIRED: "OCRを実行するか数値を手入力してください",
    ReviewTaskKind.PROGRAM_CHANGE_REVIEW: "学科変更を承認、修正、または却下してください",
    ReviewTaskKind.YOY_ANOMALY_REVIEW: "前年差分が実データか抽出ミスか確認してください",
    ReviewTaskKind.AUTHORITY_INDEX_REMARK_REVIEW: "公式索引の備考を確認してください",
    ReviewTaskKind.WORKBOOK_EXPORT_BLOCKED: "未解決タスクまたはファイルロックを解消してください",
}

LEGACY_BLOCKING_REASON_TO_REVIEW_TASK_KIND: dict[str, ReviewTaskKind] = {
    "no_url": ReviewTaskKind.SITE_ENTRY_REQUIRED,
    "no_target_pdf": ReviewTaskKind.SITE_ENTRY_CANDIDATE_REVIEW,
    "publication_lag_latest_public": ReviewTaskKind.TARGET_DOCUMENT_YEAR_REVIEW,
    "target_year_unverified": ReviewTaskKind.TARGET_DOCUMENT_YEAR_REVIEW,
    "tls_certificate_verify_failed": ReviewTaskKind.SITE_ENTRY_CANDIDATE_REVIEW,
    "stale_pdf_only": ReviewTaskKind.TARGET_DOCUMENT_YEAR_REVIEW,
    "ocr_pending": ReviewTaskKind.OCR_OR_MANUAL_ENTRY_REQUIRED,
    "parse_failed": ReviewTaskKind.OCR_OR_MANUAL_ENTRY_REQUIRED,
    "not_extracted": ReviewTaskKind.OCR_OR_MANUAL_ENTRY_REQUIRED,
    "review_required": ReviewTaskKind.TARGET_DOCUMENT_IDENTITY_REVIEW,
    "dept_change_review": ReviewTaskKind.PROGRAM_CHANGE_REVIEW,
}


def review_task_kind_ja_label(kind: ReviewTaskKind) -> str:
    return REVIEW_TASK_KIND_JA_LABELS[kind]
