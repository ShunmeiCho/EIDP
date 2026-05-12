"""Excel exporter -- generates master workbook from PostgreSQL database.

Produces 4 sheets matching the legacy format:
  Sheet 1: 採録状況 (school columns + fiscal-year status columns)
  Sheet 2: 対象比率 (22 cols)
  Sheet 3: 学科別 (dynamic fiscal-year blocks, multi-row header)
  Sheet 4: 在籍のみ抜粋 (one-year-lag enrollment blocks, multi-row header)
"""

from pathlib import Path

import openpyxl
import structlog
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import text
from sqlalchemy.orm import Session

from eidp.db.current_helpers import IS_CURRENT_TRUE_SQL
from eidp.extraction_confidence import thresholds_from_env

log = structlog.get_logger()

def _compute_fiscal_years() -> list[int]:
    """Compute fiscal years dynamically based on current date (April-March boundary)."""
    from datetime import datetime
    now = datetime.now()
    current_fy = now.year if now.month >= 4 else now.year - 1
    return list(range(2019, current_fy + 1))

FISCAL_YEARS = _compute_fiscal_years()
ENROLLMENT_YEARS = FISCAL_YEARS[:-1]  # enrollment data lags by 1 year

# 学科別: year block fields (DB column order)
YEAR_BLOCK_FIELDS = [
    "capacity", "enrollment", "intl_students", "graduates",
    "advanced", "employed", "other", "prev_enrollment",
    "dropouts", "dropout_rate",
]
# Excel headers for year block columns
YEAR_BLOCK_HEADERS = [
    "収定", "在籍", "留学生", "卒業", "進学", "就職",
    "その他", "前年在籍", "中退", "中退率",
]
_EXCEL_CONFIDENCE_THRESHOLDS = thresholds_from_env()
EXCEL_MIN_EXTRACTION_CONFIDENCE = _EXCEL_CONFIDENCE_THRESHOLDS.review
EXCEL_AUTO_FLAG_EXTRACTION_CONFIDENCE = _EXCEL_CONFIDENCE_THRESHOLDS.auto
LOW_CONFIDENCE_EXCLUSION_SHEET = "出力除外_低信頼"


def _exportable_confidence_sql(alias: str) -> str:
    return (
        f"({alias}.extraction_confidence IS NULL "
        f"OR {alias}.extraction_confidence >= {EXCEL_MIN_EXTRACTION_CONFIDENCE})"
    )


def _low_confidence_reason() -> str:
    return f"confidence<{EXCEL_MIN_EXTRACTION_CONFIDENCE:.2f}"


def export_quality_warnings(session: Session) -> dict[str, int]:
    """Count current rows that need Excel export quality attention."""
    params = {
        "min_confidence": EXCEL_MIN_EXTRACTION_CONFIDENCE,
        "auto_flag_confidence": EXCEL_AUTO_FLAG_EXTRACTION_CONFIDENCE,
    }
    checks = {
        "department_yearly_low_confidence_current": text(f"""
            SELECT COUNT(*)
            FROM department_yearly dy
            WHERE dy.is_current = {IS_CURRENT_TRUE_SQL}
              AND dy.extraction_confidence IS NOT NULL
              AND dy.extraction_confidence < :min_confidence
        """),
        "department_yearly_auto_flag_current": text(f"""
            SELECT COUNT(*)
            FROM department_yearly dy
            WHERE dy.is_current = {IS_CURRENT_TRUE_SQL}
              AND dy.extraction_confidence IS NOT NULL
              AND dy.extraction_confidence >= :min_confidence
              AND dy.extraction_confidence < :auto_flag_confidence
        """),
        "support_recipient_low_confidence_current": text(f"""
            SELECT COUNT(*)
            FROM support_recipient sr
            WHERE sr.is_current = {IS_CURRENT_TRUE_SQL}
              AND sr.extraction_confidence IS NOT NULL
              AND sr.extraction_confidence < :min_confidence
        """),
        "support_recipient_auto_flag_current": text(f"""
            SELECT COUNT(*)
            FROM support_recipient sr
            WHERE sr.is_current = {IS_CURRENT_TRUE_SQL}
              AND sr.extraction_confidence IS NOT NULL
              AND sr.extraction_confidence >= :min_confidence
              AND sr.extraction_confidence < :auto_flag_confidence
        """),
    }
    return {
        key: int(session.execute(query, params).scalar() or 0)
        for key, query in checks.items()
    }


def _write_sairoku(ws: Worksheet, session: Session) -> int:
    """Sheet 1: 採録状況 -- school collection status per year.

    Returns the number of data rows written.
    """
    headers = ["都道府県", "法人名", "学校名"] + [f"{y}年度" for y in FISCAL_YEARS]
    ws.append(headers)

    # Generate CASE WHEN clauses dynamically from FISCAL_YEARS
    year_cols = ",\n            ".join(
        f"MAX(CASE WHEN sys.fiscal_year = {y} THEN COALESCE(sys.legacy_status, sys.status) END) AS y{y}"
        for y in FISCAL_YEARS
    )
    # Sprint 8.2.1: school_year_status is now append-only with revision support.
    # Filter the JOIN to is_current=true so Excel reflects only the latest
    # revision per (school, fiscal_year), never a stale 'partial' shadowing
    # a current 'collected'.
    query = text(f"""
        SELECT
            s.prefecture,
            s.corporation_name,
            s.school_name,
            {year_cols}
        FROM school s
        LEFT JOIN school_year_status sys
            ON sys.school_id = s.id
            AND sys.is_current = {IS_CURRENT_TRUE_SQL}
        GROUP BY s.id, s.prefecture, s.corporation_name, s.school_name
        ORDER BY s.id
    """)

    rows = session.execute(query).fetchall()
    for row in rows:
        ws.append(list(row))

    count = len(rows)
    log.info("sairoku_exported", rows=count)
    return count


def _write_taisho_hiritu(ws: Worksheet, session: Session) -> int:
    """Sheet 2: 対象比率 -- support recipient data.

    Returns the number of data rows written.
    """
    headers = [
        "番号", "年度", "学校番号", "都道府県", "法人名", "学校名",
        "前年在籍", "前半期", "第\u2160区分", "第\u2161区分", "第\u2162区分", "第\u2163区分",
        "後半期", "第\u2160区分", "第\u2161区分", "第\u2162区分", "第\u2163区分",
        "年間", "家計急変多子世帯", "総計", "備考", "受給比率",
    ]
    ws.append(headers)

    # Sprint 8.2.1: support_recipient is now append-only — filter to
    # is_current=true so the 対象比率 sheet shows exactly one row per
    # (school, fiscal_year), never an old + new pair side by side.
    query = text(f"""
        SELECT
            sr.id,
            sr.fiscal_year,
            sr.school_number,
            s.prefecture,
            s.corporation_name,
            s.school_name,
            sr.prev_enrollment,
            sr.first_half_total,
            sr.first_half_cat1,
            sr.first_half_cat2,
            sr.first_half_cat3,
            sr.first_half_cat4,
            sr.second_half_total,
            sr.second_half_cat1,
            sr.second_half_cat2,
            sr.second_half_cat3,
            sr.second_half_cat4,
            sr.annual_total,
            sr.household_change,
            sr.grand_total,
            sr.notes,
            sr.recipient_rate
        FROM support_recipient sr
        JOIN school s ON s.id = sr.school_id
        WHERE sr.is_current = {IS_CURRENT_TRUE_SQL}
          AND {_exportable_confidence_sql("sr")}
        ORDER BY sr.id
    """)

    rows = session.execute(query).fetchall()
    for row in rows:
        raw = list(row)
        # Format fiscal_year as "XXXX年度"
        raw[1] = f"{raw[1]}年度" if raw[1] else raw[1]
        ws.append(raw)

    count = len(rows)
    log.info("taisho_hiritu_exported", rows=count)
    return count


def _write_gakka(ws: Worksheet, session: Session) -> int:
    """Sheet 3: 学科別 -- department yearly data with multi-row header.

    Row 1: year group labels (merged spans in original, None-padded here)
    Row 2: field name headers
    Data rows start at row 3.

    Returns the number of data rows written.
    """
    # Row 1: year group header
    row1 = [None] * 7  # key columns have no year label
    for year in FISCAL_YEARS:
        label = f"{year}年度"
        if year == 2019:
            block_size = 10
        else:
            block_size = 11
        row1.append(label)
        row1.extend([None] * (block_size - 1))
    ws.append(row1)

    # Row 2: field name header
    row2 = ["都道府県", "法人名", "学校名", "課程名", "学科名", "昼夜", "年限"]
    for year in FISCAL_YEARS:
        row2.extend(YEAR_BLOCK_HEADERS)
        if year >= 2020:
            row2.append("備考")
    ws.append(row2)

    # Data query: join department + department_yearly (pivoted)
    query = text("""
        SELECT
            s.prefecture,
            s.corporation_name,
            s.school_name,
            d.course_name,
            d.canonical_name,
            d.course_type,
            d.duration_years,
            d.id AS dept_id
        FROM department d
        JOIN school s ON s.id = d.school_id
        ORDER BY s.id, d.id
    """)

    depts = session.execute(query).fetchall()

    # Pre-fetch all yearly data keyed by (department_id, fiscal_year)
    yearly_query = text(f"""
        SELECT
            department_id, fiscal_year,
            capacity, enrollment, intl_students, graduates,
            advanced, employed, other, prev_enrollment,
            dropouts, dropout_rate, notes
        FROM department_yearly
        WHERE is_current = {IS_CURRENT_TRUE_SQL}
          AND {_exportable_confidence_sql("department_yearly")}
        ORDER BY department_id, fiscal_year
    """)
    yearly_rows = session.execute(yearly_query).fetchall()

    yearly_map: dict[tuple[int, int], tuple] = {}
    for yr in yearly_rows:
        yearly_map[(yr[0], yr[1])] = yr[2:]  # skip dept_id and fiscal_year

    count = 0
    for dept in depts:
        prefecture, corp, school, course, dept_name, day_night, duration, dept_id = dept
        row: list = [prefecture, corp, school, course, dept_name, day_night, duration]

        for year in FISCAL_YEARS:
            yd = yearly_map.get((dept_id, year))
            if yd is not None:
                # yd = (capacity, enrollment, intl, graduates, advanced, employed,
                #        other, prev_enrollment, dropouts, dropout_rate, notes)
                row.extend(list(yd[:10]))  # 10 numeric fields
                if year >= 2020:
                    row.append(yd[10])  # notes
            else:
                if year == 2019:
                    row.extend([None] * 10)
                else:
                    row.extend([None] * 11)

        ws.append(row)
        count += 1

    log.info("gakka_exported", rows=count)
    return count


def _write_zaiseki(ws: Worksheet, session: Session) -> int:
    """Sheet 4: 在籍のみ抜粋 -- enrollment-only extract.

    Multi-row header:
      Row 1: group labels (在籍者数, 留学生数)
      Row 2: key + year column headers
    Data starts row 3. Uses years from 2019 through one year before the current fiscal year.

    Returns the number of data rows written.
    """
    # Row 1: group header (dynamic year count)
    n_years = len(ENROLLMENT_YEARS)
    row1 = [None] * 7  # key columns
    row1.append("在籍者数")
    row1.extend([None] * (n_years - 1))
    row1.append("留学生数")
    row1.extend([None] * (n_years - 1))
    ws.append(row1)

    # Row 2: field names
    row2 = ["都道府県", "法人名", "学校名", "課程名", "学科名", "昼夜", "年限"]
    for year in ENROLLMENT_YEARS:
        row2.append(f"{year}年度")
    for year in ENROLLMENT_YEARS:
        row2.append(f"{year}年度")
    ws.append(row2)

    # Data query: department joined with yearly enrollment/intl_students
    query = text("""
        SELECT
            s.prefecture,
            s.corporation_name,
            s.school_name,
            d.course_name,
            d.canonical_name,
            d.course_type,
            d.duration_years,
            d.id AS dept_id
        FROM department d
        JOIN school s ON s.id = d.school_id
        ORDER BY s.id, d.id
    """)
    depts = session.execute(query).fetchall()

    # Pre-fetch enrollment data for dynamic year range
    min_ey = min(ENROLLMENT_YEARS)
    max_ey = max(ENROLLMENT_YEARS)
    yearly_query = text(f"""
        SELECT department_id, fiscal_year, enrollment, intl_students
        FROM department_yearly
        WHERE is_current = {IS_CURRENT_TRUE_SQL}
          AND fiscal_year BETWEEN {min_ey} AND {max_ey}
          AND {_exportable_confidence_sql("department_yearly")}
        ORDER BY department_id, fiscal_year
    """)
    yearly_rows = session.execute(yearly_query).fetchall()

    enroll_map: dict[tuple[int, int], tuple[int | None, int | None]] = {}
    for yr in yearly_rows:
        enroll_map[(yr[0], yr[1])] = (yr[2], yr[3])

    count = 0
    for dept in depts:
        prefecture, corp, school, course, dept_name, day_night, duration, dept_id = dept
        row: list = [prefecture, corp, school, course, dept_name, day_night, duration]

        # Enrollment values for the one-year-lag range.
        for year in ENROLLMENT_YEARS:
            data = enroll_map.get((dept_id, year))
            row.append(data[0] if data else None)

        # International student values for the one-year-lag range.
        for year in ENROLLMENT_YEARS:
            data = enroll_map.get((dept_id, year))
            row.append(data[1] if data else None)

        ws.append(row)
        count += 1

    log.info("zaiseki_exported", rows=count)
    return count


def _low_confidence_exclusion_rows(session: Session) -> list[list]:
    params = {
        "min_confidence": EXCEL_MIN_EXTRACTION_CONFIDENCE,
        "low_confidence_reason": _low_confidence_reason(),
    }
    department_rows = session.execute(
        text(f"""
            SELECT
                'department_yearly' AS row_type,
                dy.id AS row_id,
                s.school_name,
                d.canonical_name AS department_name,
                dy.fiscal_year,
                dy.extraction_confidence,
                :low_confidence_reason AS reason,
                '学科別/在籍のみ抜粋' AS export_target
            FROM department_yearly dy
            JOIN department d ON d.id = dy.department_id
            JOIN school s ON s.id = d.school_id
            WHERE dy.is_current = {IS_CURRENT_TRUE_SQL}
              AND dy.extraction_confidence IS NOT NULL
              AND dy.extraction_confidence < :min_confidence
            ORDER BY dy.id
        """),
        params,
    ).fetchall()
    support_rows = session.execute(
        text(f"""
            SELECT
                'support_recipient' AS row_type,
                sr.id AS row_id,
                s.school_name,
                NULL AS department_name,
                sr.fiscal_year,
                sr.extraction_confidence,
                :low_confidence_reason AS reason,
                '対象比率' AS export_target
            FROM support_recipient sr
            JOIN school s ON s.id = sr.school_id
            WHERE sr.is_current = {IS_CURRENT_TRUE_SQL}
              AND sr.extraction_confidence IS NOT NULL
              AND sr.extraction_confidence < :min_confidence
            ORDER BY sr.id
        """),
        params,
    ).fetchall()
    rows: list[list] = []
    for row in [*department_rows, *support_rows]:
        raw = list(row)
        if raw[5] is not None:
            raw[5] = float(raw[5])
        rows.append(raw)
    return rows


def _write_low_confidence_exclusions(ws: Worksheet, rows: list[list]) -> int:
    ws.append(["種別", "行ID", "学校名", "学科名", "年度", "confidence", "理由", "転記先"])
    for row in rows:
        ws.append(row)
    return len(rows)


def export_master_workbook(session: Session, output_path: Path) -> dict[str, int]:
    """Generate the master Excel workbook from database.

    Args:
        session: SQLAlchemy session connected to the EIDP database.
        output_path: Where to write the .xlsx file.

    Returns:
        Dict mapping sheet name to number of data rows exported.
    """
    log.info("export_start", output=str(output_path))

    wb = openpyxl.Workbook()

    # Sheet 1: 採録状況
    ws_sairoku = wb.active
    ws_sairoku.title = "採録状況"
    sairoku_count = _write_sairoku(ws_sairoku, session)

    # Sheet 2: 対象比率
    ws_taisho = wb.create_sheet("対象比率")
    taisho_count = _write_taisho_hiritu(ws_taisho, session)

    # Sheet 3: 学科別
    ws_gakka = wb.create_sheet("学科別")
    gakka_count = _write_gakka(ws_gakka, session)

    # Sheet 4: 在籍のみ抜粋
    ws_zaiseki = wb.create_sheet("在籍のみ抜粋")
    zaiseki_count = _write_zaiseki(ws_zaiseki, session)
    quality_warnings = export_quality_warnings(session)
    low_confidence_exclusions = _low_confidence_exclusion_rows(session)
    low_confidence_exclusion_count = 0
    if low_confidence_exclusions:
        ws_exclusions = wb.create_sheet(LOW_CONFIDENCE_EXCLUSION_SHEET)
        low_confidence_exclusion_count = _write_low_confidence_exclusions(ws_exclusions, low_confidence_exclusions)
    if any(quality_warnings.values()):
        log.warning("excel_export_quality_warnings", **quality_warnings)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    wb.close()

    results = {
        "採録状況": sairoku_count,
        "対象比率": taisho_count,
        "学科別": gakka_count,
        "在籍のみ抜粋": zaiseki_count,
        **({LOW_CONFIDENCE_EXCLUSION_SHEET: low_confidence_exclusion_count} if low_confidence_exclusion_count else {}),
        **{f"quality_{key}": value for key, value in quality_warnings.items()},
    }
    log.info("export_complete", results=results, output=str(output_path))
    return results


def diff_workbooks(exported_path: Path, original_path: Path) -> dict[str, dict[str, int]]:
    """Compare row counts between exported and original Excel files.

    Args:
        exported_path: Path to the exported workbook.
        original_path: Path to the original reference workbook.

    Returns:
        Dict mapping sheet name to {exported, original, diff}.
    """
    wb_exp = openpyxl.load_workbook(exported_path, read_only=True, data_only=True)
    wb_orig = openpyxl.load_workbook(original_path, read_only=True, data_only=True)

    results: dict[str, dict[str, int]] = {}

    all_sheets = set(wb_exp.sheetnames) | set(wb_orig.sheetnames)
    for name in sorted(all_sheets):
        exp_rows = 0
        orig_rows = 0

        if name in wb_exp.sheetnames:
            ws = wb_exp[name]
            exp_rows = ws.max_row or 0

        if name in wb_orig.sheetnames:
            ws = wb_orig[name]
            orig_rows = ws.max_row or 0

        results[name] = {
            "exported": exp_rows,
            "original": orig_rows,
            "diff": exp_rows - orig_rows,
        }

    wb_exp.close()
    wb_orig.close()

    return results
