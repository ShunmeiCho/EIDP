"""Table-aware, grid-position extraction of enrollment metrics (Slice 2/3).

Mirrors the pattern already proven in extractor.py::_extract_dept_identity_from_table
(find header row -> read the data row -> map by column) but extends it to the
capacity/enrollment/intl_students numbers, which the legacy path scrapes from linear
text and drops on the first miss. Grid-position mapping + field_aliases fixes both the
seito/gakusei label mismatch and the reading-order scramble verified against 大原.

Design: a PURE mapper (``map_table_to_record`` / ``map_page_tables_to_records``) that
operates on already-extracted table grids (``list[list[str | None]]`` — what both
pdfplumber ``extract_tables`` and pymupdf ``find_tables().extract`` produce), plus a
thin I/O shell (``extract_table_grid_records``) that opens a PDF with pdfplumber. The
semantic mapping — the load-bearing, adversarially-flagged hard part — lives entirely
in the pure layer so it is unit-testable without a PDF.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eidp.pdf.field_aliases import canonicalize_metric_label

__all__ = [
    "CellEvidence",
    "TableDepartmentRecord",
    "extract_table_grid_records",
    "map_page_tables_to_records",
    "map_table_to_record",
]

# Metrics this slice extracts from the enrollment header row. Teacher-staffing
# columns (専任教員数/兼任教員数/総教員数) canonicalize to None and are skipped.
_ENROLLMENT_METRICS = ("capacity", "enrollment", "intl_students")

Grid = list[list[Any]]


@dataclass(frozen=True)
class CellEvidence:
    """Provenance for one extracted number, so a human can audit the mapping."""

    page_no: int
    table_index: int
    row_index: int
    col_index: int
    raw_label: str
    raw_value: str
    canonical_metric: str


@dataclass(frozen=True)
class TableDepartmentRecord:
    field_category: str  # 分野 (文化教養 / 工業 / 商業実務 ...)
    course_name: str  # 課程名 (専門課程 ...)
    department_name: str  # 学科名
    capacity: int | None
    enrollment: int | None
    intl_students: int | None
    evidence: tuple[CellEvidence, ...] = field(default_factory=tuple)


def _clean(cell: Any) -> str:
    """NFKC-fold and strip all whitespace (folds full-width, drops stray newlines)."""
    if cell is None:
        return ""
    return "".join(unicodedata.normalize("NFKC", str(cell)).split())


def _parse_int(cell: Any) -> int | None:
    if cell is None:
        return None
    m = re.search(r"\d+", str(cell).replace(",", ""))
    return int(m.group()) if m else None


def _first_data_row(grid: Grid, header_idx: int) -> int | None:
    """Index of the first non-empty row after ``header_idx``."""
    for idx in range(header_idx + 1, len(grid)):
        if any(_clean(c) for c in grid[idx]):
            return idx
    return None


def _extract_identity(grid: Grid) -> tuple[str, str, str]:
    """Return (field_category, course_name, department_name) from the 分野/課程名/学科名
    header row and its data row. Empty strings when not present."""
    for idx, row in enumerate(grid):
        if not any("学科名" in _clean(c) for c in row):
            continue
        data_idx = _first_data_row(grid, idx)
        if data_idx is None:
            return "", "", ""
        header = [_clean(c) for c in row]
        data = grid[data_idx]

        def value_for(label: str) -> str:
            for j, h in enumerate(header):
                if label in h and j < len(data):
                    return _clean(data[j])
            return ""

        return value_for("分野"), value_for("課程名"), value_for("学科名")
    return "", "", ""


def map_table_to_record(
    table: Grid, *, page_no: int, table_index: int
) -> TableDepartmentRecord | None:
    """Map one department table grid to a canonical record, or None if the table
    has no enrollment header (i.e. it is not a 学科 enrollment table)."""
    field_category, course_name, department_name = _extract_identity(table)

    enroll_header_idx = next(
        (
            idx
            for idx, row in enumerate(table)
            if any(canonicalize_metric_label(_clean(c)) == "capacity" for c in row)
        ),
        None,
    )
    if enroll_header_idx is None or not department_name:
        return None

    data_idx = _first_data_row(table, enroll_header_idx)
    if data_idx is None:
        return None

    header = table[enroll_header_idx]
    data = table[data_idx]
    values: dict[str, int | None] = {m: None for m in _ENROLLMENT_METRICS}
    evidence: list[CellEvidence] = []
    for col, cell in enumerate(header):
        metric = canonicalize_metric_label(_clean(cell))
        if metric not in _ENROLLMENT_METRICS or col >= len(data):
            continue
        parsed = _parse_int(data[col])
        if parsed is None:
            continue
        values[metric] = parsed
        evidence.append(
            CellEvidence(
                page_no=page_no,
                table_index=table_index,
                row_index=data_idx,
                col_index=col,
                raw_label=_clean(cell),
                raw_value=str(data[col]),
                canonical_metric=metric,
            )
        )

    return TableDepartmentRecord(
        field_category=field_category,
        course_name=course_name,
        department_name=department_name,
        capacity=values["capacity"],
        enrollment=values["enrollment"],
        intl_students=values["intl_students"],
        evidence=tuple(evidence),
    )


def map_page_tables_to_records(
    tables: list[Grid], *, page_no: int
) -> list[TableDepartmentRecord]:
    records = []
    for table_index, table in enumerate(tables):
        record = map_table_to_record(table, page_no=page_no, table_index=table_index)
        if record is not None:
            records.append(record)
    return records


def extract_table_grid_records(pdf_path: Path | str) -> list[TableDepartmentRecord]:
    """I/O shell: open a text PDF with pdfplumber and map every department table.

    pdfplumber is imported lazily so the pure mapper stays dependency-free.
    """
    import pdfplumber  # noqa: PLC0415 -- keep heavy dep out of the pure layer

    records: list[TableDepartmentRecord] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages):
            tables = page.extract_tables() or []
            records.extend(map_page_tables_to_records(tables, page_no=page_no))
    return records
