"""Excel importer — reads 4 sheets from master Excel into DB.

Sheets: 採録状況, 対象比率, 学科別, 在籍のみ抜粋 (snapshot, import skipped — re-derivable)
"""

from pathlib import Path

import openpyxl
import structlog
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, School, SchoolYearStatus, SupportRecipient

log = structlog.get_logger()

# Year columns in 採録状況 (0-indexed from col B onward, after key columns)
SAIROKU_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

# Status mapping: Excel free-text -> DB status enum
LEGACY_TO_STATUS = {
    "〇": "collected",
    "〇（一部欠損）": "collected",
    "〇（一部昨年？）": "collected",
    "△": "collected",
    "△（不足）": "collected",
    "△（前年データ）": "stale",
    "△（前年）": "stale",
    "△（同一データ）": "stale",
    "対象外": "excluded",
    "学校なし": "excluded",
    "統合": "excluded",
    "統廃合": "excluded",
    "閉校": "excluded",
    "募集停止": "excluded",
    "リンクミス": "error",
    "職実": "collected",
    "職実代用": "collected",
    "一部職実": "collected",
    "一部職実代用": "collected",
    "一部学科職実": "collected",
    "不足": "collected",
    "欠損データ": "error",
    "データなし": "error",
    "前年データ": "stale",
    "日付は変更されるが内容同じ": "stale",
    "情報公開": "collected",
    "事業報告": "collected",
    "新規申請": "pending",
    "不明": "pending",
    "他法人": "excluded",
}

EXCLUDED_REASONS = {"対象外", "学校なし", "統合", "統廃合", "閉校", "募集停止", "他法人"}

# 学科別 year block layout per field-spec
# 2019: 10 cols (no 備考), 2020-2025: 11 cols (with 備考)
YEAR_BLOCK_FIELDS_NO_BIKO = [
    "capacity", "enrollment", "intl_students", "graduates",
    "advanced", "employed", "other", "prev_enrollment",
    "dropouts", "dropout_rate",
]
YEAR_BLOCK_FIELDS_WITH_BIKO = YEAR_BLOCK_FIELDS_NO_BIKO + ["notes"]

GAKKA_KEY_COLS = 7  # 都道府県, 法人名, 学校名, 課程名, 学科名, 昼夜, 年限


def _safe_int(val: object) -> int | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def _safe_float(val: object) -> float | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return None


def _safe_str(val: object) -> str:
    if val is None:
        return ""
    return str(val).strip()


def import_sairoku(ws: openpyxl.worksheet.worksheet.Worksheet, session: Session) -> dict[str, int]:
    """Import 採録状況 sheet -> school + school_year_status tables."""
    school_cache: dict[tuple[str, str, str], int] = {}
    stats = {"schools": 0, "statuses": 0}

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        prefecture = _safe_str(row[0])
        corp_name = _safe_str(row[1])
        school_name = _safe_str(row[2])

        if not school_name:
            continue

        cache_key = (prefecture, corp_name, school_name)
        if cache_key in school_cache:
            school_id = school_cache[cache_key]
        else:
            # Upsert: find existing or create
            existing = (
                session.query(School)
                .filter(
                    School.prefecture == prefecture,
                    School.corporation_name == corp_name,
                    School.school_name == school_name,
                )
                .first()
            )
            if existing:
                school_id = existing.id
            else:
                school = School(
                    prefecture=prefecture,
                    corporation_name=corp_name,
                    school_name=school_name,
                    school_type="専門学校",
                )
                session.add(school)
                session.flush()
                school_id = school.id
                stats["schools"] += 1
            school_cache[cache_key] = school_id

        # Year status columns: cols 3-9 (0-indexed) for 2019-2025
        for i, year in enumerate(SAIROKU_YEARS):
            col_idx = 3 + i
            raw_val = _safe_str(row[col_idx]) if col_idx < len(row) else ""
            if not raw_val:
                status = "pending"
                legacy = None
            else:
                legacy = raw_val
                status = LEGACY_TO_STATUS.get(raw_val, "pending")

            excluded_reason = raw_val if raw_val in EXCLUDED_REASONS else None

            sys = SchoolYearStatus(
                school_id=school_id,
                fiscal_year=year,
                status=status,
                legacy_status=legacy,
                excluded_reason=excluded_reason,
            )
            session.add(sys)
            stats["statuses"] += 1

    session.flush()
    log.info("sairoku_imported", **stats)
    return stats


def import_gakka(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    session: Session,
    school_lookup: dict[tuple[str, str, str], int],
) -> dict[str, int]:
    """Import 学科別 sheet -> department + department_yearly tables.

    Multi-row header: row 1 = year groups, row 2 = field names. Data starts row 3.
    """
    stats = {"departments": 0, "yearly_rows": 0, "school_misses": 0, "yearly_dupes": 0}
    dept_cache: dict[tuple[int, str, str, str | None, int | None], int] = {}
    yearly_seen: set[tuple[int, int]] = set()  # (department_id, fiscal_year)

    for row_idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        prefecture = _safe_str(row[0])
        corp_name = _safe_str(row[1])
        school_name = _safe_str(row[2])
        course_name = _safe_str(row[3])  # 課程名
        dept_name = _safe_str(row[4])    # 学科名
        day_night = _safe_str(row[5])    # 昼夜
        duration = _safe_int(row[6])     # 年限

        if not dept_name:
            continue

        school_key = (prefecture, corp_name, school_name)
        school_id = school_lookup.get(school_key)
        if school_id is None:
            stats["school_misses"] += 1
            continue

        # Create or find department
        dept_key = (school_id, dept_name, day_night, course_name, duration)
        if dept_key in dept_cache:
            dept_id = dept_cache[dept_key]
        else:
            dept = Department(
                school_id=school_id,
                course_name=course_name if course_name else None,
                canonical_name=dept_name,
                course_type=day_night if day_night else None,
                duration_years=duration,
            )
            session.add(dept)
            session.flush()
            dept_id = dept.id
            dept_cache[dept_key] = dept_id
            stats["departments"] += 1

        # Parse year blocks
        col_offset = GAKKA_KEY_COLS  # start after key columns

        for year in range(2019, 2026):
            if year == 2019:
                fields = YEAR_BLOCK_FIELDS_NO_BIKO
                block_size = 10
            else:
                fields = YEAR_BLOCK_FIELDS_WITH_BIKO
                block_size = 11

            block_data: dict[str, int | float | str | None] = {}
            for fi, field_name in enumerate(fields):
                ci = col_offset + fi
                raw = row[ci] if ci < len(row) else None
                if field_name == "dropout_rate":
                    block_data[field_name] = _safe_float(raw)
                elif field_name == "notes":
                    block_data[field_name] = _safe_str(raw) if raw else None
                else:
                    block_data[field_name] = _safe_int(raw)

            col_offset += block_size

            # Only insert if there's any data
            has_data = any(
                v is not None and v != ""
                for k, v in block_data.items()
                if k != "notes"
            )
            if not has_data:
                continue

            yearly_key = (dept_id, year)
            if yearly_key in yearly_seen:
                stats["yearly_dupes"] += 1
                continue
            yearly_seen.add(yearly_key)

            dy = DepartmentYearly(
                department_id=dept_id,
                fiscal_year=year,
                revision=1,
                is_current=True,
                capacity=block_data.get("capacity"),
                enrollment=block_data.get("enrollment"),
                intl_students=block_data.get("intl_students"),
                graduates=block_data.get("graduates"),
                advanced=block_data.get("advanced"),
                employed=block_data.get("employed"),
                other=block_data.get("other"),
                prev_enrollment=block_data.get("prev_enrollment"),
                dropouts=block_data.get("dropouts"),
                dropout_rate=block_data.get("dropout_rate"),
                notes=block_data.get("notes"),
                extraction_method="excel_import",
            )
            session.add(dy)
            stats["yearly_rows"] += 1

    session.flush()
    log.info("gakka_imported", **stats)
    return stats


def import_taisho_hiritu(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    session: Session,
    school_lookup: dict[tuple[str, str, str], int],
) -> dict[str, int]:
    """Import 対象比率 sheet -> support_recipient table.

    Each Excel row = one DB row (period='full').
    Columns: 番号, 年度, 学校番号, 都道府県, 法人名, 学校名,
    前年在籍, 前半期, 第Ⅰ区分x4, 後半期, 第Ⅰ区分x4,
    年間, 家計急変多子世帯, 総計, 備考, 受給比率
    """
    stats = {"rows": 0, "school_misses": 0, "duplicates": 0}
    seen: set[tuple[int, int]] = set()  # (school_id, fiscal_year)

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        year_str = _safe_str(row[1])
        school_number = _safe_str(row[2])
        prefecture = _safe_str(row[3])
        corp_name = _safe_str(row[4])
        school_name = _safe_str(row[5])

        if not school_name or not year_str:
            continue

        fiscal_year = _parse_fiscal_year(year_str)
        if fiscal_year is None:
            continue

        school_key = (prefecture, corp_name, school_name)
        school_id = school_lookup.get(school_key)
        if school_id is None:
            stats["school_misses"] += 1
            continue

        dedup_key = (school_id, fiscal_year)
        if dedup_key in seen:
            stats["duplicates"] += 1
            continue
        seen.add(dedup_key)

        sr = SupportRecipient(
            school_id=school_id,
            school_number=school_number if school_number else None,
            fiscal_year=fiscal_year,
            prev_enrollment=_safe_int(row[6]),
            first_half_total=_safe_int(row[7]),
            first_half_cat1=_safe_int(row[8]),
            first_half_cat2=_safe_int(row[9]),
            first_half_cat3=_safe_int(row[10]),
            first_half_cat4=_safe_int(row[11]),
            second_half_total=_safe_int(row[12]),
            second_half_cat1=_safe_int(row[13]) if len(row) > 13 else None,
            second_half_cat2=_safe_int(row[14]) if len(row) > 14 else None,
            second_half_cat3=_safe_int(row[15]) if len(row) > 15 else None,
            second_half_cat4=_safe_int(row[16]) if len(row) > 16 else None,
            annual_total=_safe_int(row[17]) if len(row) > 17 else None,
            household_change=_safe_int(row[18]) if len(row) > 18 else None,
            grand_total=_safe_int(row[19]) if len(row) > 19 else None,
            recipient_rate=_safe_float(row[21]) if len(row) > 21 else None,
            notes=_safe_str(row[20]) if len(row) > 20 and row[20] else None,
        )
        session.add(sr)
        stats["rows"] += 1

    session.flush()
    log.info("taisho_hiritu_imported", **stats)
    return stats


def _parse_fiscal_year(val: str) -> int | None:
    """Parse fiscal year from various formats."""
    import re

    val = val.strip()

    # "2024年度" or just "2024"
    m = re.search(r"(20\d{2})", val)
    if m:
        return int(m.group(1))

    # "令和6年度" -> 2024
    m = re.match(r"令和(\d+)", val)
    if m:
        return 2018 + int(m.group(1))

    return None


def import_all(excel_path: Path, session: Session) -> dict[str, dict[str, int]]:
    """Import all 4 sheets from master Excel. Returns stats per sheet."""
    log.info("import_start", path=str(excel_path))

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)

    results: dict[str, dict[str, int]] = {}

    # Sheet 1: 採録状況 -> school + school_year_status
    ws_sairoku = wb["採録状況"]
    results["採録状況"] = import_sairoku(ws_sairoku, session)

    # Build school lookup for subsequent sheets
    schools = session.query(School).all()
    school_lookup: dict[tuple[str, str, str], int] = {
        (s.prefecture, s.corporation_name, s.school_name): s.id for s in schools
    }
    log.info("school_lookup_built", size=len(school_lookup))

    # Sheet 2: 対象比率 -> support_recipient
    ws_taisho = wb["対象比率"]
    results["対象比率"] = import_taisho_hiritu(ws_taisho, session, school_lookup)

    # Sheet 3: 学科別 -> department + department_yearly
    ws_gakka = wb["学科別"]
    results["学科別"] = import_gakka(ws_gakka, session, school_lookup)

    # Sheet 4: 在籍のみ抜粋 — snapshot, skip import (re-derivable from department_yearly)
    results["在籍のみ抜粋"] = {"skipped": 1, "reason": "re-derivable from department_yearly"}

    wb.close()
    log.info("import_complete", results=results)
    return results
