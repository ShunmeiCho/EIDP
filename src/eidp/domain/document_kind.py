"""Controlled document-kind taxonomy for disclosure PDFs."""

from enum import StrEnum


class DocumentKind(StrEnum):
    """Business-level classification for disclosure documents."""

    TARGET_APPLICATION_FORM = "target_application_form"
    TARGET_APPLICATION_ATTACHMENT = "target_application_attachment"
    SUPPORT_RECIPIENT_ONLY = "support_recipient_only"
    PRIOR_YEAR_TARGET_FORM = "prior_year_target_form"
    NON_TARGET_DISCLOSURE = "non_target_disclosure"
    SCHOOL_EVALUATION = "school_evaluation"
    VOCATIONAL_PRACTICE_FORM = "vocational_practice_form"
    ADMISSION_DOCUMENT = "admission_document"
    UNKNOWN_PDF = "unknown_pdf"


DOCUMENT_KIND_JA_LABELS: dict[DocumentKind, str] = {
    DocumentKind.TARGET_APPLICATION_FORM: "機関要件確認申請書",
    DocumentKind.TARGET_APPLICATION_ATTACHMENT: "別紙・補足資料",
    DocumentKind.SUPPORT_RECIPIENT_ONLY: "対象者数のみ",
    DocumentKind.PRIOR_YEAR_TARGET_FORM: "旧年度の確認申請書",
    DocumentKind.NON_TARGET_DISCLOSURE: "対象外PDF",
    DocumentKind.SCHOOL_EVALUATION: "学校評価",
    DocumentKind.VOCATIONAL_PRACTICE_FORM: "職業実践専門課程資料",
    DocumentKind.ADMISSION_DOCUMENT: "募集・入学関連資料",
    DocumentKind.UNKNOWN_PDF: "未分類PDF",
}

LEGACY_PDF_TYPE_TO_DOCUMENT_KIND: dict[str, DocumentKind] = {
    "target": DocumentKind.TARGET_APPLICATION_FORM,
    "image_only": DocumentKind.TARGET_APPLICATION_FORM,
    "support_only": DocumentKind.SUPPORT_RECIPIENT_ONLY,
    "non_target": DocumentKind.NON_TARGET_DISCLOSURE,
    "unknown": DocumentKind.UNKNOWN_PDF,
}


def document_kind_ja_label(kind: DocumentKind) -> str:
    return DOCUMENT_KIND_JA_LABELS[kind]
