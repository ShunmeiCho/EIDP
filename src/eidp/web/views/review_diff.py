"""Review report and master-diff page body for Linux/Web MVP."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from eidp.config import settings
from eidp.identity import ResolvedIdentity
from eidp.pipeline.extraction_review import load_review_records
from eidp.pipeline.review_decision import overlay_review_decisions
from eidp.pipeline.review_master_diff import (
    DiffResultRow,
    diff_report_csv,
    diff_reviewed_against_master,
    diff_summary,
    load_master_expected_subset,
)
from eidp.pipeline.review_report import (
    ReviewedExtractionRow,
    normalized_review_report_csv_from_rows,
    reviewed_rows_from_records,
)


def render_review_diff_page(
    *,
    identity: ResolvedIdentity,
    session_factory: sessionmaker[Session],
    intake_root: Path | None = None,
    master_path: Path | None = None,
) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"
    resolved_master = master_path or Path(settings.app_root) / "data" / "master.xlsx"

    st.title("EIDP Review Diff")
    st.caption("Compare reviewed extraction rows with a read-only master subset. Final Excel output is out of scope.")

    review_records = load_review_records(resolved_root)
    with session_factory() as session:
        review_records = overlay_review_decisions(session, review_records)
    reviewed_rows = reviewed_rows_from_records(review_records)
    comparable_count = sum(1 for row in reviewed_rows if row.final_review_value is not None)
    needs_work_count = sum(1 for row in reviewed_rows if row.metric and row.final_review_value is None)

    col_rows, col_comparable, col_needs_work = st.columns(3)
    col_rows.metric("Review rows", len(reviewed_rows))
    col_comparable.metric("Comparable", comparable_count)
    col_needs_work.metric("Not comparable", needs_work_count)

    st.download_button(
        "Download normalized_review_report.csv",
        data=normalized_review_report_csv_from_rows(reviewed_rows),
        file_name="normalized_review_report.csv",
        mime="text/csv",
    )

    st.subheader("Master subset")
    st.caption("Source: managed read-only master.xlsx")
    school_options = sorted({row.school_name for row in reviewed_rows})
    selected_school = ""
    if school_options:
        selected_school = str(st.selectbox("school_name", school_options))
    corporation_name = st.text_input("corporation_name")
    fiscal_year = int(st.number_input("fiscal_year", value=_default_fiscal_year(reviewed_rows), step=1))

    if not corporation_name.strip() or not selected_school:
        st.info("Enter corporation_name and select school_name to load the master expected subset.")
        return

    try:
        expected_rows = load_master_expected_subset(
            resolved_master,
            corporation_name=corporation_name,
            school_name=selected_school,
            fiscal_year=fiscal_year,
            school_id=_school_id_for(reviewed_rows, selected_school),
        )
    except (FileNotFoundError, KeyError, OSError) as exc:
        st.error(str(exc))
        return

    scoped_reviewed_rows = [
        row for row in reviewed_rows if row.school_name == selected_school and row.fiscal_year == fiscal_year
    ]
    diff_rows = diff_reviewed_against_master(scoped_reviewed_rows, expected_rows)
    summary = diff_summary(diff_rows)
    st.dataframe([summary], hide_index=True, use_container_width=True)
    st.dataframe([_display_row(row) for row in diff_rows], hide_index=True, use_container_width=True)
    st.download_button(
        "Download review_master_diff.csv",
        data=diff_report_csv(diff_rows),
        file_name="review_master_diff.csv",
        mime="text/csv",
    )


def _default_fiscal_year(rows: Sequence[ReviewedExtractionRow]) -> int:
    years = sorted({row.fiscal_year for row in rows})
    return years[-1] if years else int(settings.target_fiscal_year)


def _school_id_for(rows: Sequence[ReviewedExtractionRow], school_name: str) -> str | None:
    for row in rows:
        if row.school_name == school_name:
            return row.school_id
    return None


def _display_row(row: DiffResultRow) -> dict[str, object]:
    return {
        "key": row.key,
        "match_status": row.match_status.value,
        "school_name": row.school_name,
        "department_name": row.department_name,
        "metric": row.metric,
        "extracted_value": row.extracted_value,
        "expected_value": row.expected_value,
        "mismatch_reason": row.mismatch_reason,
        "source_pdf": row.source_pdf or "",
        "page_no": row.page_no if row.page_no is not None else "",
    }
