from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord
from eidp.pipeline.extraction_queue import process_intake_record
from eidp.pipeline.extraction_review import (
    ReviewStatus,
    ReviewTaskType,
    ReviewValidationError,
    accept_review_record,
    correct_review_record,
    ensure_review_records,
    exclude_review_record,
    is_final_ready,
    mark_review_needs_review,
    review_report_csv,
)
from eidp.pipeline.pdf_intake import PdfKind, store_pdf_upload, validate_intake_metadata

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
TEST_IDENTITY = ResolvedIdentity("operator-a", IdentitySource.CONFIGURED_FALLBACK)


@pytest.fixture()
def db_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'review-decisions.sqlite3'}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


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


def _record() -> TableDepartmentRecord:
    return TableDepartmentRecord(
        field_category="文化教養",
        course_name="専門課程",
        department_name="テスト学科",
        capacity=40,
        enrollment=37,
        intl_students=None,
        evidence=(
            CellEvidence(
                page_no=0,
                table_index=1,
                row_index=3,
                col_index=4,
                raw_label="収容定員",
                raw_value="40",
                canonical_metric="capacity",
            ),
            CellEvidence(
                page_no=0,
                table_index=1,
                row_index=3,
                col_index=5,
                raw_label="在学者数",
                raw_value="37",
                canonical_metric="enrollment",
            ),
        ),
    )


def _extract_and_review_records(tmp_path: Path):
    record = _text_intake(tmp_path)
    process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=lambda _pdf_path: [_record()],
    )
    return ensure_review_records(tmp_path)


def _capacity_review_id(tmp_path: Path) -> str:
    records = _extract_and_review_records(tmp_path)
    return next(record.review_id for record in records if record.metric == "capacity")


def test_review_status_can_be_set_to_all_operator_states(tmp_path: Path, db_session: Session) -> None:
    review_id = _capacity_review_id(tmp_path)

    accepted = accept_review_record(
        db_session,
        intake_root=tmp_path,
        review_id=review_id,
        identity=TEST_IDENTITY,
        review_note="source checked",
    )
    corrected = correct_review_record(
        db_session,
        intake_root=tmp_path,
        review_id=review_id,
        corrected_value=41,
        identity=TEST_IDENTITY,
        review_note="official table uses revised count",
    )
    needs_review = mark_review_needs_review(
        db_session,
        intake_root=tmp_path,
        review_id=review_id,
        identity=TEST_IDENTITY,
        review_note="ask second reviewer",
    )
    excluded = exclude_review_record(
        db_session,
        intake_root=tmp_path,
        review_id=review_id,
        identity=TEST_IDENTITY,
        review_note="not current export scope",
    )

    assert accepted.review_status == ReviewStatus.ACCEPTED
    assert corrected.review_status == ReviewStatus.CORRECTED
    assert needs_review.review_status == ReviewStatus.NEEDS_REVIEW
    assert excluded.review_status == ReviewStatus.EXCLUDED
    assert excluded.reviewed_by == "operator-a"
    assert excluded.reviewed_at is not None


def test_corrected_value_preserves_original_extracted_value_and_json_bytes(
    tmp_path: Path,
    db_session: Session,
) -> None:
    review_id = _capacity_review_id(tmp_path)
    base_path = tmp_path / "extraction" / "reviews" / f"{review_id}.json"
    base_bytes = base_path.read_bytes()

    corrected = correct_review_record(
        db_session,
        intake_root=tmp_path,
        review_id=review_id,
        corrected_value=42,
        identity=TEST_IDENTITY,
    )

    assert corrected.extracted_value == 40
    assert corrected.corrected_value == 42
    assert corrected.review_status == ReviewStatus.CORRECTED
    assert is_final_ready(corrected)
    assert base_path.read_bytes() == base_bytes
    assert ensure_review_records(tmp_path)[0].review_status == ReviewStatus.UNREVIEWED


def test_review_report_includes_immutable_base_evidence_columns(tmp_path: Path) -> None:
    _capacity_review_id(tmp_path)

    report = review_report_csv(tmp_path)
    rows = list(csv.DictReader(io.StringIO(report)))
    capacity = next(row for row in rows if row["metric"] == "capacity")

    assert capacity["school_name"] == "東京テスト専門学校"
    assert capacity["department_name"] == "テスト学科"
    assert capacity["field_category"] == "文化教養"
    assert capacity["course_name"] == "専門課程"
    assert capacity["extracted_value"] == "40"
    assert capacity["corrected_value"] == ""
    assert capacity["review_status"] == "unreviewed"
    assert capacity["source_pdf"]
    assert capacity["page_no"] == "0"
    assert capacity["table_index"] == "1"
    assert capacity["row_index"] == "3"
    assert capacity["col_index"] == "4"
    assert capacity["raw_label"] == "収容定員"
    assert capacity["raw_value"] == "40"
    assert capacity["canonical_metric"] == "capacity"
    assert capacity["review_note"] == ""
    assert capacity["reviewed_by"] == ""
    assert capacity["final_ready"] == "False"
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_exception_manual_ocr_cannot_be_accepted_as_extracted_data(
    tmp_path: Path,
    db_session: Session,
) -> None:
    _image_intake(tmp_path)
    records = ensure_review_records(tmp_path)
    exception = next(record for record in records if record.task_type == ReviewTaskType.EXCEPTION_MANUAL_OCR)

    with pytest.raises(ReviewValidationError):
        accept_review_record(
            db_session,
            intake_root=tmp_path,
            review_id=exception.review_id,
            identity=TEST_IDENTITY,
        )

    loaded = ensure_review_records(tmp_path)
    exception = next(record for record in loaded if record.task_type == ReviewTaskType.EXCEPTION_MANUAL_OCR)
    assert exception.review_status == ReviewStatus.NEEDS_REVIEW
    assert not is_final_ready(exception)
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_low_confidence_unreviewed_row_is_not_final_ready(tmp_path: Path) -> None:
    record = _text_intake(tmp_path)
    process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=lambda _pdf_path: [_record()],
    )

    records = ensure_review_records(tmp_path, default_confidence=0.5)
    capacity = next(record for record in records if record.metric == "capacity")

    assert capacity.confidence == 0.5
    assert capacity.review_status == ReviewStatus.UNREVIEWED
    assert not is_final_ready(capacity)
    assert list(tmp_path.rglob("*.xlsx")) == []
