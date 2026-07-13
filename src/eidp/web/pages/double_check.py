"""External double-check page for Linux/Web MVP."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import streamlit as st

from eidp.config import settings
from eidp.identity import ResolvedIdentity
from eidp.pipeline.double_check_compare import (
    DoubleCheckResultRow,
    compare_external_to_reviewed,
    double_check_report_csv,
    double_check_summary,
)
from eidp.pipeline.external_extraction_import import (
    ExternalExtractionImportError,
    ExternalExtractionRow,
    ExternalSourceSystem,
    load_external_extraction_file,
)
from eidp.pipeline.extraction_review import load_review_records
from eidp.pipeline.review_report import reviewed_rows_from_records


def render_double_check_page(*, identity: ResolvedIdentity, intake_root: Path | None = None) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"

    st.title("EIDP Double Check")
    st.caption("Import Copilot/NotebookLM CSV/XLSX outputs and compare them with reviewed EIDP rows.")

    reviewed_rows = reviewed_rows_from_records(load_review_records(resolved_root))
    st.metric("Reviewed rows", len(reviewed_rows))

    source_system = ExternalSourceSystem(
        str(
            st.selectbox(
                "source_system",
                [system.value for system in ExternalSourceSystem],
                index=0,
            )
        )
    )
    uploaded_file = st.file_uploader("External extraction CSV/XLSX", type=["csv", "xlsx", "xlsm"])
    if uploaded_file is None:
        st.info("Upload a Copilot, NotebookLM, or manual external extraction file to run the comparison.")
        return

    try:
        external_rows = load_external_extraction_file(
            uploaded_file.getvalue(),
            filename=uploaded_file.name,
            source_system=source_system,
        )
    except ExternalExtractionImportError as exc:
        st.error(str(exc))
        return

    _render_external_summary(external_rows)
    comparison_rows = compare_external_to_reviewed(reviewed_rows, external_rows)
    st.dataframe([double_check_summary(comparison_rows)], hide_index=True, use_container_width=True)
    st.dataframe([_display_row(row) for row in comparison_rows], hide_index=True, use_container_width=True)
    st.download_button(
        "Download double_check_report.csv",
        data=double_check_report_csv(comparison_rows),
        file_name="double_check_report.csv",
        mime="text/csv",
    )


def _render_external_summary(rows: Sequence[ExternalExtractionRow]) -> None:
    by_source: dict[str, int] = {}
    for row in rows:
        by_source[row.source_system.value] = by_source.get(row.source_system.value, 0) + 1
    st.metric("External metric rows", len(rows))
    st.dataframe([by_source], hide_index=True, use_container_width=True)


def _display_row(row: DoubleCheckResultRow) -> dict[str, object]:
    return {
        "key": row.key,
        "comparison_result": row.comparison_result,
        "comparison_status": row.comparison_status.value,
        "school_name": row.school_name,
        "department_name": row.department_name,
        "metric": row.metric,
        "eidp_value": row.eidp_value if row.eidp_value is not None else "",
        "external_value": row.external_value if row.external_value is not None else "",
        "mismatch_reason": row.mismatch_reason,
        "source_system": row.source_system.value if row.source_system is not None else "",
        "source_file": row.source_file or "",
        "source_pdf": row.source_pdf or "",
    }
