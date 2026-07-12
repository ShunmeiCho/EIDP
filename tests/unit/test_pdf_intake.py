from __future__ import annotations

import io
import zipfile

import pytest

from eidp.pipeline.pdf_intake import (
    IntakeLane,
    IntakeSource,
    PdfIntakeValidationError,
    PdfKind,
    compute_sha256,
    load_intake_queue,
    parse_url_csv,
    register_url_csv,
    store_pdf_upload,
    store_zip_upload,
    validate_intake_metadata,
)

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_validate_intake_metadata_requires_human_confirmed_pdf_identity() -> None:
    with pytest.raises(PdfIntakeValidationError) as exc_info:
        validate_intake_metadata(
            school_name=" ",
            fiscal_year="not-a-year",
            source_page_url="not-a-url",
        )

    assert "school_name is required" in exc_info.value.errors
    assert "fiscal_year must be a western-year integer" in exc_info.value.errors
    assert "source_page_url must be an http(s) URL" in exc_info.value.errors
    assert "pdf_url or uploaded filename is required" in exc_info.value.errors


def test_store_pdf_upload_computes_sha_and_writes_local_metadata(tmp_path) -> None:
    metadata = validate_intake_metadata(
        school_name="東京テスト専門学校",
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        uploaded_filename="募集要項.pdf",
    )

    record = store_pdf_upload(
        metadata=metadata,
        pdf_bytes=PDF_BYTES,
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.TEXT,
    )

    assert record.sha256 == compute_sha256(PDF_BYTES)
    assert record.lane == IntakeLane.TEXT_MAIN
    assert record.pdf_kind == PdfKind.TEXT
    assert record.source_type == IntakeSource.PDF_UPLOAD
    assert record.stored_path is not None
    assert (tmp_path / record.stored_path).read_bytes() == PDF_BYTES
    assert len(list((tmp_path / "records").glob("*.json"))) == 1
    assert load_intake_queue(tmp_path) == [record]
    assert list(tmp_path.rglob("*.xlsx")) == []


def test_image_pdf_is_marked_exception_manual_ocr(tmp_path) -> None:
    metadata = validate_intake_metadata(
        school_name="大阪テスト専門学校",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/info/",
        uploaded_filename="scan.pdf",
    )

    record = store_pdf_upload(
        metadata=metadata,
        pdf_bytes=PDF_BYTES,
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.IMAGE,
    )

    assert record.pdf_kind == PdfKind.IMAGE
    assert record.lane == IntakeLane.MANUAL_OCR


def test_zip_upload_registers_pdf_members_only(tmp_path) -> None:
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("nested/a.pdf", PDF_BYTES)
        archive.writestr("notes.txt", "ignore me")
    metadata = validate_intake_metadata(
        school_name="名古屋テスト専門学校",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/downloads/",
        uploaded_filename="bundle.zip",
    )

    records = store_zip_upload(
        metadata=metadata,
        zip_bytes=archive_bytes.getvalue(),
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.TEXT,
    )

    assert len(records) == 1
    assert records[0].source_type == IntakeSource.ZIP_UPLOAD
    assert records[0].original_filename == "nested/a.pdf"
    assert records[0].lane == IntakeLane.TEXT_MAIN


def test_url_csv_registers_metadata_without_downloading_pdf(tmp_path) -> None:
    csv_bytes = (
        "school_name,school_id,fiscal_year,source_page_url,pdf_url\n"
        "京都テスト専門学校,KY-001,2026,https://example.ac.jp/page/,https://example.ac.jp/form.pdf\n"
    ).encode()

    parsed = parse_url_csv(csv_bytes)
    records = register_url_csv(csv_bytes=csv_bytes, intake_root=tmp_path)

    assert parsed[0].school_name == "京都テスト専門学校"
    assert records[0].lane == IntakeLane.URL_REGISTERED
    assert records[0].sha256 is None
    assert records[0].stored_path is None
    assert not (tmp_path / "files").exists()
    assert load_intake_queue(tmp_path) == records


def test_url_csv_reports_row_validation_errors() -> None:
    csv_bytes = (
        b"school_name,school_id,fiscal_year,source_page_url,pdf_url\n"
        b"Broken,,2026,https://example.ac.jp/page/,not-a-url\n"
    )

    with pytest.raises(PdfIntakeValidationError) as exc_info:
        parse_url_csv(csv_bytes)

    assert exc_info.value.errors == ("row 2: pdf_url must be an http(s) URL when provided",)
