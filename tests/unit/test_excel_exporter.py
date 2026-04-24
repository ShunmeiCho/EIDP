from __future__ import annotations

import openpyxl
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from eidp.excel.exporter import _write_sairoku


def test_sairoku_export_preserves_schools_without_year_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE school (
                    id INTEGER PRIMARY KEY,
                    prefecture TEXT,
                    corporation_name TEXT,
                    school_name TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE school_year_status (
                    school_id INTEGER NOT NULL,
                    fiscal_year INTEGER NOT NULL,
                    legacy_status TEXT,
                    status TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO school (id, prefecture, corporation_name, school_name)
                VALUES
                    (1, '東京都', '学校法人A', '採録済み学校'),
                    (2, '大阪府', '学校法人B', '未採録学校')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO school_year_status (school_id, fiscal_year, legacy_status, status)
                VALUES (1, 2025, '○', 'verified')
                """
            )
        )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    with Session(engine) as session:
        count = _write_sairoku(worksheet, session)

    assert count == 2
    assert worksheet.cell(row=2, column=3).value == "採録済み学校"
    assert worksheet.cell(row=3, column=3).value == "未採録学校"
    assert all(cell.value is None for cell in worksheet[3][3:])
