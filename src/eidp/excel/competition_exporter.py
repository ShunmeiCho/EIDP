"""Template-preserving exporter for 競合校の在校生数.xlsx.

Reads the担当者 template workbook and overlays new fiscal-year columns
without disturbing the existing 16-sheet structure or row order.

Output:
- Filled workbook (template clone + new fiscal-year columns)
- Gap report CSV listing template rows that could not be matched to DB

Match strategy (in order):
1. Exact school_name match after NFKC + whitespace strip
2. SchoolAlias table fallback
3. Department canonical_name match within school
"""

from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, School, SchoolAlias

log = structlog.get_logger(__name__)

# Header row contains "在籍数" and (one row above) the fiscal year integer.
_ENROLLMENT_HEADER_TEXT = "在籍数"
_INTL_HEADER_TEXT = "留学生"


def _norm(s: object) -> str:
    """NFKC normalize and strip ALL whitespace for matching."""
    if s is None:
        return ""
    text = str(s)
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", "", text)


@dataclass(frozen=True)
class YearColumns:
    """Where to read/write a fiscal-year's pair of cells."""

    fiscal_year: int
    zaiseki_col: int  # 在籍数 column (1-indexed)
    intl_col: int  # 留学生 column (1-indexed)


@dataclass(frozen=True)
class TemplateRow:
    """A single school+dept entry in the template."""

    row_index: int
    school_name: str
    dept_name: str | None
    duration_label: str | None  # e.g. "4年制", "2年制"


@dataclass
class SheetSchema:
    """Parsed structure of one template sheet."""

    name: str
    header_row: int
    year_cols: list[YearColumns]
    data_rows: list[TemplateRow]
    school_col: int  # 1-indexed
    dept_col: int | None  # None for 学校単位 rollup sheet
    duration_col: int | None
    is_rollup: bool  # True for 学校単位での比較


def _find_header_row(ws: Worksheet) -> tuple[int, list[YearColumns]]:
    """Locate the row containing 在籍数 markers and infer per-year columns."""
    for r in range(1, min(8, ws.max_row + 1)):
        year_cols: list[YearColumns] = []
        for c in range(1, ws.max_column + 1):
            v = ws.cell(r, c).value
            if v != _ENROLLMENT_HEADER_TEXT:
                continue
            # Year is in the row above (or two rows above for some sheets)
            year: int | None = None
            for offset in (1, 2):
                if r - offset < 1:
                    continue
                cand = ws.cell(r - offset, c).value
                if isinstance(cand, int) and 2010 <= cand <= 2100:
                    year = cand
                    break
                if isinstance(cand, str):
                    m = re.search(r"(20\d{2})", cand)
                    if m:
                        year = int(m.group(1))
                        break
            if year is None:
                continue
            # 留学生 column is the cell immediately to the right
            intl_col = c + 1
            if ws.cell(r, intl_col).value != _INTL_HEADER_TEXT:
                continue
            year_cols.append(
                YearColumns(fiscal_year=year, zaiseki_col=c, intl_col=intl_col)
            )
        if year_cols:
            return r, year_cols
    return -1, []


def _detect_school_columns(name: str) -> tuple[int, int | None, int | None]:
    """Return (school_col, dept_col, duration_col) for a sheet."""
    if name == "学校単位での比較":
        # Layout: A=blank, B=school, C+ year data
        return 2, None, None
    # Category sheets: A=school, B=dept, C=duration
    return 1, 2, 3


def parse_sheet_schema(ws: Worksheet) -> SheetSchema | None:
    """Parse one sheet to identify header, year columns, and data rows.

    Returns None if the sheet does not appear to be a competition sheet.
    """
    header_row, year_cols = _find_header_row(ws)
    if header_row < 0 or not year_cols:
        return None

    school_col, dept_col, duration_col = _detect_school_columns(ws.title)
    is_rollup = ws.title == "学校単位での比較"

    data_rows: list[TemplateRow] = []
    last_school: str = ""
    for r in range(header_row + 1, ws.max_row + 1):
        school_raw = ws.cell(r, school_col).value
        dept_raw = ws.cell(r, dept_col).value if dept_col else None
        duration_raw = ws.cell(r, duration_col).value if duration_col else None

        school = _norm(school_raw)
        if school:
            last_school = school
        dept = _norm(dept_raw) if dept_raw else None

        # Skip empty/ratio-only rows: a row counts if it has school OR dept identity
        if not school and not dept:
            continue
        # Skip rows that have only number data (the alternate ratio row already
        # belongs to the prior data row).
        if not school and not dept_raw:
            continue
        # Use last_school for category sheets where school spans multiple rows
        effective_school = school if school else last_school
        if not effective_school:
            continue
        # For rollup sheet, only school name matters (no dept)
        if is_rollup and not school:
            continue

        data_rows.append(
            TemplateRow(
                row_index=r,
                school_name=effective_school,
                dept_name=dept,
                duration_label=str(duration_raw) if duration_raw else None,
            )
        )

    return SheetSchema(
        name=ws.title,
        header_row=header_row,
        year_cols=year_cols,
        data_rows=data_rows,
        school_col=school_col,
        dept_col=dept_col,
        duration_col=duration_col,
        is_rollup=is_rollup,
    )


def parse_template(template_path: Path) -> dict[str, SheetSchema]:
    """Parse all sheets from a template workbook."""
    wb = load_workbook(str(template_path), data_only=True)
    schemas: dict[str, SheetSchema] = {}
    for name in wb.sheetnames:
        schema = parse_sheet_schema(wb[name])
        if schema is not None:
            schemas[name] = schema
    return schemas


@dataclass
class MatchResult:
    """Outcome of matching a TemplateRow to DB entities."""

    template_row: TemplateRow
    sheet_name: str
    school_id: int | None
    department_ids: list[int] = field(default_factory=list)
    matched_via: str = "unmatched"  # exact | alias | dept | unmatched


class CompetitionMatcher:
    """Match template (school, dept) rows to DB entities."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._school_index: dict[str, int] = {}
        self._alias_index: dict[str, int] = {}
        self._dept_cache: dict[int, list[Department]] = {}
        self._build_indices()

    def _build_indices(self) -> None:
        for s in self.session.query(School).all():
            key = _norm(s.school_name)
            if key and key not in self._school_index:
                self._school_index[key] = s.id
        for a in self.session.query(SchoolAlias).all():
            key = _norm(a.alias_name)
            if key and key not in self._alias_index:
                self._alias_index[key] = a.school_id

    def _depts_for_school(self, school_id: int) -> list[Department]:
        if school_id not in self._dept_cache:
            self._dept_cache[school_id] = (
                self.session.query(Department)
                .filter(Department.school_id == school_id)
                .all()
            )
        return self._dept_cache[school_id]

    def match(self, sheet_name: str, row: TemplateRow) -> MatchResult:
        school_key = _norm(row.school_name)
        school_id = self._school_index.get(school_key)
        matched_via = "exact" if school_id is not None else ""
        if school_id is None:
            school_id = self._alias_index.get(school_key)
            matched_via = "alias" if school_id is not None else "unmatched"

        if school_id is None:
            return MatchResult(template_row=row, sheet_name=sheet_name,
                               school_id=None, matched_via="unmatched")

        # Rollup sheet: school-level only
        if row.dept_name is None:
            return MatchResult(template_row=row, sheet_name=sheet_name,
                               school_id=school_id, matched_via=matched_via)

        # Match dept by canonical_name within the school
        dept_key = _norm(row.dept_name)
        depts = self._depts_for_school(school_id)
        matching = [d.id for d in depts if _norm(d.canonical_name) == dept_key]
        if matching:
            return MatchResult(template_row=row, sheet_name=sheet_name,
                               school_id=school_id, department_ids=matching,
                               matched_via=matched_via + "+dept")
        # Substring fallback: dept_key contained in canonical_name (handles
        # template using shorter form of long dept names).
        for d in depts:
            cn = _norm(d.canonical_name)
            if dept_key and cn and (dept_key in cn or cn in dept_key):
                matching.append(d.id)
        return MatchResult(template_row=row, sheet_name=sheet_name,
                           school_id=school_id, department_ids=matching,
                           matched_via=matched_via + "+dept_substr" if matching
                           else matched_via + "+dept_unmatched")


@dataclass
class YearlyAggregate:
    """Aggregated yearly data for a (school, dept-set, year)."""

    enrollment: int | None
    intl_students: int | None


def _aggregate_yearly(
    session: Session, dept_ids: list[int], fiscal_year: int
) -> YearlyAggregate:
    if not dept_ids:
        return YearlyAggregate(enrollment=None, intl_students=None)
    rows = (
        session.query(DepartmentYearly)
        .filter(
            DepartmentYearly.department_id.in_(dept_ids),
            DepartmentYearly.fiscal_year == fiscal_year,
            DepartmentYearly.is_current.is_(True),
        )
        .all()
    )
    if not rows:
        return YearlyAggregate(enrollment=None, intl_students=None)
    enrollment = sum((r.enrollment or 0) for r in rows) if any(
        r.enrollment is not None for r in rows
    ) else None
    intl = sum((r.intl_students or 0) for r in rows) if any(
        r.intl_students is not None for r in rows
    ) else None
    return YearlyAggregate(enrollment=enrollment, intl_students=intl)


def _aggregate_school_yearly(
    session: Session, school_id: int, fiscal_year: int
) -> YearlyAggregate:
    """Sum across all departments of a school for the rollup sheet."""
    dept_ids = [d.id for d in session.query(Department).filter(
        Department.school_id == school_id
    ).all()]
    return _aggregate_yearly(session, dept_ids, fiscal_year)


def _append_year_columns(
    ws: Worksheet, schema: SheetSchema, fiscal_year: int
) -> YearColumns:
    """Write 在籍数 / 留学生 headers for a new fiscal year and return the cols."""
    new_zaiseki_col = ws.max_column + 1
    new_intl_col = new_zaiseki_col + 1
    # Year label one row above header row
    if schema.header_row > 1:
        ws.cell(schema.header_row - 1, new_zaiseki_col, value=fiscal_year)
    ws.cell(schema.header_row, new_zaiseki_col, value=_ENROLLMENT_HEADER_TEXT)
    ws.cell(schema.header_row, new_intl_col, value=_INTL_HEADER_TEXT)
    return YearColumns(
        fiscal_year=fiscal_year,
        zaiseki_col=new_zaiseki_col,
        intl_col=new_intl_col,
    )


def export_competition_workbook(
    session: Session,
    template_path: Path,
    output_path: Path,
    fiscal_year: int,
    gap_report_path: Path | None = None,
) -> dict[str, int]:
    """Generate the 競合校の在校生数 workbook for the given fiscal year.

    Returns counts: matched / unmatched / cells_written.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_path, output_path)

    wb = load_workbook(str(output_path))
    matcher = CompetitionMatcher(session)
    matched = 0
    unmatched_rows: list[MatchResult] = []
    cells_written = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        schema = parse_sheet_schema(ws)
        if schema is None:
            continue

        # Skip if year already present (idempotent re-runs)
        existing_years = {yc.fiscal_year for yc in schema.year_cols}
        if fiscal_year in existing_years:
            new_cols = next(yc for yc in schema.year_cols if yc.fiscal_year == fiscal_year)
        else:
            new_cols = _append_year_columns(ws, schema, fiscal_year)

        for row in schema.data_rows:
            result = matcher.match(sheet_name, row)
            if schema.is_rollup:
                if result.school_id is None:
                    unmatched_rows.append(result)
                    continue
                agg = _aggregate_school_yearly(session, result.school_id, fiscal_year)
                matched += 1
            else:
                if not result.department_ids:
                    unmatched_rows.append(result)
                    continue
                agg = _aggregate_yearly(session, result.department_ids, fiscal_year)
                matched += 1

            if agg.enrollment is not None:
                ws.cell(row.row_index, new_cols.zaiseki_col, value=agg.enrollment)
                cells_written += 1
            if agg.intl_students is not None:
                ws.cell(row.row_index, new_cols.intl_col, value=agg.intl_students)
                cells_written += 1

    wb.save(str(output_path))

    if gap_report_path is not None and unmatched_rows:
        gap_report_path.parent.mkdir(parents=True, exist_ok=True)
        with gap_report_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["sheet", "row", "school_name", "dept_name", "duration",
                 "school_id", "matched_via"]
            )
            for u in unmatched_rows:
                writer.writerow([
                    u.sheet_name,
                    u.template_row.row_index,
                    u.template_row.school_name,
                    u.template_row.dept_name or "",
                    u.template_row.duration_label or "",
                    u.school_id or "",
                    u.matched_via,
                ])

    log.info(
        "competition_export_complete",
        output=str(output_path),
        fiscal_year=fiscal_year,
        matched=matched,
        unmatched=len(unmatched_rows),
        cells_written=cells_written,
    )

    return {
        "matched": matched,
        "unmatched": len(unmatched_rows),
        "cells_written": cells_written,
    }
