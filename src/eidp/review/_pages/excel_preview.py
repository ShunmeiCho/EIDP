"""Streamlit page: Excel プレビュー (Sprint 8.4.c.3).

Operator-facing dry-run before the master workbook is downloaded /
distributed. Generates the same 4-sheet workbook ``export_master_workbook``
produces, but in memory (BytesIO) so nothing hits disk until the operator
clicks the download button.

Architecture
------------
Same shape as 8.4.c.1 / 8.4.c.2. Pure helpers under unit test:

  * ``build_preview_workbook(session)`` — in-memory openpyxl workbook
    builder that mirrors ``export_master_workbook`` but returns
    BytesIO + a counts dict. No filesystem writes.
  * ``format_sheet_preview(workbook, sheet_name, max_rows)`` — slices
    the first N rows of a sheet into a list-of-rows for the UI table.
  * ``count_unmatched_and_gap(session)`` — surfaces 採録状況 unmatched
    and 学科別 gap counts so the operator sees what's missing before
    downloading.

Lock contract: this page is read-only — Excel is generated from
already-committed data. No lock needed. The page surfaces a probe
banner for visibility only.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.locking import probe_lock
from eidp.db.models import Department, DepartmentYearly, School, SchoolYearStatus
from eidp.excel.exporter import (
    _write_gakka,
    _write_sairoku,
    _write_taisho_hiritu,
    _write_zaiseki,
)
from eidp.fiscal_year import format_fiscal_year_label
from eidp.review.target_year_status import target_year_overview

# Sheets the master workbook carries, in display order.
SHEET_ORDER: tuple[str, ...] = ("採録状況", "対象比率", "学科別", "在籍のみ抜粋")


@dataclass
class PreviewWorkbook:
    """In-memory workbook + per-sheet row counts."""

    workbook: openpyxl.Workbook
    counts: dict[str, int] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        """Serialize to bytes for st.download_button. Calling this does
        NOT close the workbook — caller controls lifecycle."""
        buf = io.BytesIO()
        self.workbook.save(buf)
        return buf.getvalue()


@dataclass
class CoverageGapCounts:
    schools_total: int
    schools_with_any_data: int
    schools_unmatched: int          # in current code: schools without any DepartmentYearly
    students_missing_year: int      # SchoolYearStatus rows where status != 'collected'


# ---------------------------------------------------------------------------
# In-memory workbook builder
# ---------------------------------------------------------------------------


def build_preview_workbook(session: Session) -> PreviewWorkbook:
    """Build the 4-sheet master workbook in memory.

    Mirrors ``eidp.excel.exporter.export_master_workbook`` but returns a
    PreviewWorkbook with counts attached. No filesystem writes — caller
    decides whether to materialize via ``to_bytes()``.
    """
    wb = openpyxl.Workbook()

    ws_sairoku = wb.active
    ws_sairoku.title = "採録状況"
    sairoku_count = _write_sairoku(ws_sairoku, session)

    ws_taisho = wb.create_sheet("対象比率")
    taisho_count = _write_taisho_hiritu(ws_taisho, session)

    ws_gakka = wb.create_sheet("学科別")
    gakka_count = _write_gakka(ws_gakka, session)

    ws_zaiseki = wb.create_sheet("在籍のみ抜粋")
    zaiseki_count = _write_zaiseki(ws_zaiseki, session)

    return PreviewWorkbook(
        workbook=wb,
        counts={
            "採録状況": sairoku_count,
            "対象比率": taisho_count,
            "学科別": gakka_count,
            "在籍のみ抜粋": zaiseki_count,
        },
    )


# ---------------------------------------------------------------------------
# Sheet preview slicing
# ---------------------------------------------------------------------------


def format_sheet_preview(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    *,
    max_rows: int = 30,
) -> list[list[Any]]:
    """Return the first N rows of ``sheet_name`` as a list-of-rows."""
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"sheet {sheet_name!r} not in workbook ({workbook.sheetnames})")
    ws = workbook[sheet_name]
    out: list[list[Any]] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= max_rows:
            break
        out.append(list(row))
    return out


# ---------------------------------------------------------------------------
# Coverage / gap counts
# ---------------------------------------------------------------------------


def count_unmatched_and_gap(session: Session) -> CoverageGapCounts:
    """Aggregate counts the operator wants to see before downloading.

    * ``schools_total`` — every active school.
    * ``schools_with_any_data`` — schools with ≥ 1 current DepartmentYearly.
    * ``schools_unmatched`` — schools_total − schools_with_any_data.
    * ``students_missing_year`` — SchoolYearStatus current-revision rows
      whose status is NOT ``collected`` (partial / support_only / etc.),
      i.e. years where the picture is incomplete.

    Sprint 8.2.1 read-path filters apply transitively via the
    is_current=True scope.
    """
    schools_total = session.query(func.count(School.id)).filter(School.status == "active").scalar() or 0

    schools_with_data = (
        session.query(func.count(func.distinct(Department.school_id)))
        .join(DepartmentYearly, DepartmentYearly.department_id == Department.id)
        .filter(DepartmentYearly.is_current.is_(True))
        .scalar()
        or 0
    )

    students_missing_year = (
        session.query(func.count(SchoolYearStatus.id))
        .filter(SchoolYearStatus.is_current.is_(True))
        .filter(SchoolYearStatus.status != "collected")
        .scalar()
        or 0
    )

    return CoverageGapCounts(
        schools_total=schools_total,
        schools_with_any_data=schools_with_data,
        schools_unmatched=max(0, schools_total - schools_with_data),
        students_missing_year=students_missing_year,
    )


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin streamlit shell
    """Top-level Streamlit render for the Excel プレビュー page."""
    import streamlit as st

    st.subheader("Excel プレビュー")
    status = probe_lock(lock_path)
    if status.held:
        st.info(
            f"週次処理中 (owner={status.owner})。"
            " このページは読み取り専用です。"
        )

    target_label = format_fiscal_year_label(settings.target_fiscal_year)
    target = target_year_overview(
        session,
        target_fiscal_year=settings.target_fiscal_year,
        school_type="専門学校",
    )
    st.caption(f"対象年度: {target_label}")
    target_cols = st.columns(4)
    target_cols[0].metric("対象年度PDFあり", target.current_target_schools)
    target_cols[1].metric("旧年度fallback", target.stale_target_documents)
    target_cols[2].metric("未採録校", target.missing_current_target_schools)
    target_cols[3].metric("要確認キュー", target.review_queue_documents)
    if target.current_target_documents == 0 and target.stale_target_documents > 0:
        st.warning(
            f"{target_label} のPDFが未採録です。旧年度fallbackはExcel成果として扱わず、"
            "先に週次再取得またはURL追加を行ってください。"
        )

    counts = count_unmatched_and_gap(session)
    cols = st.columns(4)
    cols[0].metric("学校 総数", counts.schools_total)
    cols[1].metric("データあり", counts.schools_with_any_data)
    cols[2].metric("データなし", counts.schools_unmatched)
    cols[3].metric("年度不足", counts.students_missing_year)

    if st.button("プレビュー workbook を生成", type="primary"):
        with st.spinner("生成中..."):
            preview = build_preview_workbook(session)
            st.session_state["excel_preview_bytes"] = preview.to_bytes()
            st.session_state["excel_preview_counts"] = preview.counts
            st.session_state["excel_preview_workbook"] = preview.workbook
        st.rerun()

    if "excel_preview_workbook" in st.session_state:
        wb = st.session_state["excel_preview_workbook"]
        counts_map = st.session_state["excel_preview_counts"]
        st.caption(
            "シート行数: " + " / ".join(
                f"{name}={counts_map.get(name, 0)}" for name in SHEET_ORDER
            )
        )
        sheet_name = st.selectbox("シート選択", options=list(SHEET_ORDER))
        rows = format_sheet_preview(wb, sheet_name, max_rows=30)
        if rows:
            st.table(rows)
        else:
            st.caption("(空)")
        st.download_button(
            label="Excel ダウンロード",
            data=st.session_state["excel_preview_bytes"],
            file_name="eidp_master.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
