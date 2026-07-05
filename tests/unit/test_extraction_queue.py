from __future__ import annotations

from pathlib import Path

from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord
from eidp.pipeline.extraction_queue import (
    ExtractionQueueType,
    ExtractionStatus,
    NextAction,
    ensure_extraction_queue,
    load_extracted_rows,
    process_intake_record,
    process_pending_text_pdf_records,
)
from eidp.pipeline.pdf_intake import PdfKind, store_pdf_upload, validate_intake_metadata

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _metadata(*, school_name: str = "東京テスト専門学校"):
    return validate_intake_metadata(
        school_name=school_name,
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        uploaded_filename="form.pdf",
    )


def _text_intake(tmp_path: Path):
    return store_pdf_upload(
        metadata=_metadata(),
        pdf_bytes=PDF_BYTES,
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.TEXT,
    )


def _image_intake(tmp_path: Path):
    return store_pdf_upload(
        metadata=_metadata(school_name="大阪テスト専門学校"),
        pdf_bytes=PDF_BYTES,
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.IMAGE,
    )


def _record(*, capacity: int | None = 40, enrollment: int | None = 37) -> TableDepartmentRecord:
    evidence: list[CellEvidence] = []
    if capacity is not None:
        evidence.append(
            CellEvidence(
                page_no=0,
                table_index=1,
                row_index=3,
                col_index=4,
                raw_label="収容定員",
                raw_value=str(capacity),
                canonical_metric="capacity",
            )
        )
    if enrollment is not None:
        evidence.append(
            CellEvidence(
                page_no=0,
                table_index=1,
                row_index=3,
                col_index=5,
                raw_label="在学者数",
                raw_value=str(enrollment),
                canonical_metric="enrollment",
            )
        )
    return TableDepartmentRecord(
        field_category="文化教養",
        course_name="専門課程",
        department_name="テスト学科",
        capacity=capacity,
        enrollment=enrollment,
        intl_students=None,
        evidence=tuple(evidence),
    )


def test_text_pdf_main_intake_creates_pending_extraction_job(tmp_path: Path) -> None:
    record = _text_intake(tmp_path)

    items = ensure_extraction_queue(tmp_path)

    assert len(items) == 1
    item = items[0]
    assert item.intake_record_id == record.record_id
    assert item.queue_type == ExtractionQueueType.TEXT_EXTRACTION
    assert item.status == ExtractionStatus.PENDING_EXTRACTION
    assert item.next_action == NextAction.RUN_EXTRACTION
    assert item.school_name == record.school_name
    assert item.school_id == record.school_id
    assert item.fiscal_year == record.fiscal_year
    assert item.source_page_url == record.source_page_url
    assert item.pdf_path == record.stored_path
    assert item.sha256 == record.sha256


def test_queue_runner_calls_table_extractor_and_stores_rows_with_evidence(tmp_path: Path) -> None:
    record = _text_intake(tmp_path)
    called_with: list[Path] = []

    def fake_extractor(pdf_path: Path) -> list[TableDepartmentRecord]:
        called_with.append(pdf_path)
        return [_record()]

    item = process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=fake_extractor,
    )
    rows = load_extracted_rows(tmp_path, record.record_id)

    assert called_with == [tmp_path / (record.stored_path or "")]
    assert item.status == ExtractionStatus.EXTRACTION_COMPLETED
    assert item.next_action == NextAction.REVIEW_EXTRACTED_ROWS
    assert item.rows_written == 2
    assert [row.metric for row in rows] == ["capacity", "enrollment"]
    assert rows[0].page_no == 0
    assert rows[0].table_index == 1
    assert rows[0].row_index == 3
    assert rows[0].col_index == 4
    assert rows[0].raw_label == "収容定員"
    assert rows[0].value == 40
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_image_pdf_exception_creates_manual_ocr_task_and_does_not_call_extractor(tmp_path: Path) -> None:
    record = _image_intake(tmp_path)

    def fail_if_called(_pdf_path: Path) -> list[TableDepartmentRecord]:
        raise AssertionError("image PDFs must not call the extractor")

    item = process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=fail_if_called,
    )

    assert item.queue_type == ExtractionQueueType.MANUAL_OCR_EXCEPTION
    assert item.status == ExtractionStatus.NOT_APPLICABLE
    assert item.next_action == NextAction.UPLOAD_OCR_TEXT_PDF
    assert load_extracted_rows(tmp_path, record.record_id) == []
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_pending_runner_processes_only_text_pdf_main_records(tmp_path: Path) -> None:
    text_record = _text_intake(tmp_path)
    image_record = _image_intake(tmp_path)

    results = process_pending_text_pdf_records(intake_root=tmp_path, extractor_func=lambda _pdf_path: [_record()])

    assert [item.intake_record_id for item in results] == [text_record.record_id]
    queue = {item.intake_record_id: item for item in ensure_extraction_queue(tmp_path)}
    assert queue[text_record.record_id].status == ExtractionStatus.EXTRACTION_COMPLETED
    assert queue[image_record.record_id].queue_type == ExtractionQueueType.MANUAL_OCR_EXCEPTION
    assert queue[image_record.record_id].next_action == NextAction.UPLOAD_OCR_TEXT_PDF


def test_failed_extraction_is_captured_without_crashing_queue(tmp_path: Path) -> None:
    record = _text_intake(tmp_path)

    def failing_extractor(_pdf_path: Path) -> list[TableDepartmentRecord]:
        raise RuntimeError("parser exploded")

    item = process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=failing_extractor,
    )

    assert item.status == ExtractionStatus.EXTRACTION_FAILED
    assert item.next_action == NextAction.RUN_EXTRACTION
    assert item.error_reason == "parser exploded"
    assert load_extracted_rows(tmp_path, record.record_id) == []
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_incomplete_extraction_becomes_needs_review(tmp_path: Path) -> None:
    record = _text_intake(tmp_path)

    item = process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=lambda _pdf_path: [_record(capacity=40, enrollment=None)],
    )

    assert item.status == ExtractionStatus.NEEDS_REVIEW
    assert item.next_action == NextAction.REVIEW_EXTRACTED_ROWS
    assert item.rows_written == 1
    assert list(tmp_path.rglob("*.xlsx")) == []
