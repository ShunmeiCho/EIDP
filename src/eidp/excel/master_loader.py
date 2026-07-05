"""Read-only loader that projects data/master.xlsx 学科別 rows into canonical,
melted metric rows for the extraction ground-truth diff (Slice 4b).

data/master.xlsx is a RED-LINE file: opened with ``read_only=True`` and NEVER written.
Only capacity/enrollment/intl_students are projected in this slice. Department keys are
composed as ``<canonical 分野>|<学科 key>`` so departments that share a 学科名 across
different 分野 do not collide.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eidp.pdf.master_ground_truth import (
    canonical_field_category,
    department_key,
    fy_metric_columns,
    normalize_text,
)

__all__ = ["MasterMetricRow", "compose_department_key", "load_master_metric_rows"]

_SHEET = "学科別"
_METRIC_LABELS = ("capacity", "enrollment", "intl_students")


@dataclass(frozen=True)
class MasterMetricRow:
    school_key: str  # normalized 法人名
    campus_key: str | None  # normalized 学校名
    department_key: str  # "<canonical 分野>|<学科 key>"
    fiscal_year: int
    metric: str  # capacity | enrollment | intl_students
    value: int | float | str | None
    source_sheet: str
    source_cell: str | None


def compose_department_key(field_category: str | None, department_name: str | None) -> str:
    return f"{canonical_field_category(field_category)}|{department_key(department_name)}"


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "‐", "―"):
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def load_master_metric_rows(
    master_path: Path | str,
    *,
    corporation_name: str,
    school_name: str,
    fiscal_year: int,
    prefecture: str | None = None,
) -> list[MasterMetricRow]:
    """Load the (capacity/enrollment/intl_students) metric rows for one school+FY.

    Filters the 学科別 sheet to the given (法人名, 学校名) [+ optional 都道府県], reads the
    fiscal-year metric column triple, and emits one MasterMetricRow per (dept, metric).
    Raises ``KeyError`` if the fiscal year is outside master coverage (e.g. 2026).
    """
    import openpyxl  # type: ignore[import-untyped]  # noqa: PLC0415

    cap_col, enr_col, intl_col = fy_metric_columns(fiscal_year)
    target_corp = normalize_text(corporation_name)
    target_school = normalize_text(school_name)
    target_pref = normalize_text(prefecture) if prefecture else None

    wb = openpyxl.load_workbook(master_path, read_only=True, data_only=True)
    try:
        worksheet = wb[_SHEET]
        rows: list[MasterMetricRow] = []
        for row in worksheet.iter_rows(min_row=3, values_only=True):
            if row is None or len(row) <= intl_col:
                continue
            if normalize_text(str(row[1] or "")) != target_corp:
                continue
            if normalize_text(str(row[2] or "")) != target_school:
                continue
            if target_pref and normalize_text(str(row[0] or "")) != target_pref:
                continue
            dept = compose_department_key(str(row[3] or ""), str(row[4] or ""))
            if _safe_int(row[enr_col]) is None:
                # A department with no FY 在籍 (enrollment) value is inactive for that FY;
                # master carries legacy dept rows with blank cells. Skip the whole dept so
                # its blanks never become phantom missing_actual diffs. 在籍=0 (募集停止,
                # still counted) is a real value (not None) and is kept.
                continue
            for metric, col in zip(_METRIC_LABELS, (cap_col, enr_col, intl_col), strict=True):
                rows.append(
                    MasterMetricRow(
                        school_key=target_corp,
                        campus_key=target_school,
                        department_key=dept,
                        fiscal_year=fiscal_year,
                        metric=metric,
                        value=_safe_int(row[col]),
                        source_sheet=_SHEET,
                        source_cell=None,
                    )
                )
        return rows
    finally:
        wb.close()
