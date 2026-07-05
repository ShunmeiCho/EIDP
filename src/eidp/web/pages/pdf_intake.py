"""PDF intake page for the Linux/Web MVP."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from eidp.config import MAX_SUPPORTED_TARGET_FISCAL_YEAR, MIN_SUPPORTED_TARGET_FISCAL_YEAR, settings
from eidp.pipeline.pdf_intake import (
    PdfIntakeMetadata,
    PdfIntakeValidationError,
    load_intake_queue,
    register_url_csv,
    store_pdf_upload,
    store_zip_upload,
    validate_intake_metadata,
)
from eidp.web.components.intake_table import render_intake_table


def render_pdf_intake_page(*, intake_root: Path | None = None) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"

    st.title("EIDP PDF Intake")
    st.caption("Human-confirmed PDFs only. Image PDFs enter the exception/manual/OCR lane.")

    pdf_tab, zip_tab, url_tab, queue_tab = st.tabs(["PDF", "ZIP", "URL CSV", "Queue"])
    with pdf_tab:
        _render_pdf_upload(resolved_root)
    with zip_tab:
        _render_zip_upload(resolved_root)
    with url_tab:
        _render_url_csv_upload(resolved_root)
    with queue_tab:
        _render_queue(resolved_root)


def _render_pdf_upload(intake_root: Path) -> None:
    with st.form("pdf_intake_single_pdf", clear_on_submit=True):
        school_name, school_id, fiscal_year, source_page_url, pdf_url = _metadata_inputs("pdf")
        uploaded_file = st.file_uploader("PDF file", type=["pdf"], accept_multiple_files=False)
        submitted = st.form_submit_button("Register PDF")
    if not submitted:
        return
    if uploaded_file is None:
        st.error("PDF file is required.")
        return
    try:
        metadata = validate_intake_metadata(
            school_name=school_name,
            school_id=school_id,
            fiscal_year=fiscal_year,
            source_page_url=source_page_url,
            pdf_url=pdf_url,
            uploaded_filename=uploaded_file.name,
        )
        record = store_pdf_upload(metadata=metadata, pdf_bytes=uploaded_file.getvalue(), intake_root=intake_root)
    except PdfIntakeValidationError as exc:
        _render_validation_errors(exc)
        return
    st.success(f"Registered {record.original_filename} as {record.lane.value}.")


def _render_zip_upload(intake_root: Path) -> None:
    with st.form("pdf_intake_zip", clear_on_submit=True):
        school_name, school_id, fiscal_year, source_page_url, _pdf_url = _metadata_inputs("zip")
        uploaded_file = st.file_uploader("ZIP file", type=["zip"], accept_multiple_files=False)
        submitted = st.form_submit_button("Register ZIP PDFs")
    if not submitted:
        return
    if uploaded_file is None:
        st.error("ZIP file is required.")
        return
    try:
        metadata = validate_intake_metadata(
            school_name=school_name,
            school_id=school_id,
            fiscal_year=fiscal_year,
            source_page_url=source_page_url,
            uploaded_filename=uploaded_file.name,
        )
        records = store_zip_upload(metadata=metadata, zip_bytes=uploaded_file.getvalue(), intake_root=intake_root)
    except PdfIntakeValidationError as exc:
        _render_validation_errors(exc)
        return
    st.success(f"Registered {len(records)} PDF(s) from ZIP.")


def _render_url_csv_upload(intake_root: Path) -> None:
    st.download_button(
        "Download CSV template",
        data="school_name,school_id,fiscal_year,source_page_url,pdf_url\n",
        file_name="eidp-url-intake-template.csv",
        mime="text/csv",
    )
    uploaded_file = st.file_uploader("URL CSV file", type=["csv"], accept_multiple_files=False)
    if not st.button("Register URL CSV", type="primary"):
        return
    if uploaded_file is None:
        st.error("URL CSV file is required.")
        return
    try:
        records = register_url_csv(csv_bytes=uploaded_file.getvalue(), intake_root=intake_root)
    except PdfIntakeValidationError as exc:
        _render_validation_errors(exc)
        return
    st.success(f"Registered {len(records)} URL intake row(s).")


def _render_queue(intake_root: Path) -> None:
    records = load_intake_queue(intake_root)
    text_count = sum(1 for record in records if record.lane.value == "text_pdf_main")
    exception_count = sum(1 for record in records if record.lane.value.startswith("exception_"))
    url_count = sum(1 for record in records if record.lane.value == "url_registered")
    col_text, col_exception, col_url = st.columns(3)
    col_text.metric("Text PDF", text_count)
    col_exception.metric("Exception/manual/OCR", exception_count)
    col_url.metric("URL registered", url_count)
    render_intake_table(records)


def _metadata_inputs(prefix: str) -> tuple[str, str, int, str, str]:
    school_name = st.text_input("school_name", key=f"{prefix}_school_name")
    school_id = st.text_input("school_id", key=f"{prefix}_school_id")
    fiscal_year = int(
        st.number_input(
            "fiscal_year",
            min_value=MIN_SUPPORTED_TARGET_FISCAL_YEAR,
            max_value=MAX_SUPPORTED_TARGET_FISCAL_YEAR,
            value=int(settings.target_fiscal_year),
            step=1,
            key=f"{prefix}_fiscal_year",
        )
    )
    source_page_url = st.text_input("source_page_url", key=f"{prefix}_source_page_url")
    pdf_url = st.text_input("pdf_url", key=f"{prefix}_pdf_url")
    return school_name, school_id, fiscal_year, source_page_url, pdf_url


def _render_validation_errors(exc: PdfIntakeValidationError) -> None:
    for error in exc.errors:
        st.error(error)


__all__ = ["PdfIntakeMetadata", "render_pdf_intake_page"]
