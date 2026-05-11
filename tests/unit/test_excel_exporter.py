from __future__ import annotations

import openpyxl
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, School, SupportRecipient
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.excel.exporter import _write_sairoku, export_master_workbook


@pytest.fixture()
def sqlite_engine(tmp_path):
    db_path = tmp_path / "exporter.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


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
                    status TEXT,
                    -- Sprint 8.2.a added is_current as the discriminator for
                    -- the partial unique index. The exporter (Sprint 8.2.1)
                    -- now joins on it so demoted revisions don't shadow
                    -- current ones.
                    is_current INTEGER NOT NULL DEFAULT 1
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
                INSERT INTO school_year_status (school_id, fiscal_year, legacy_status, status, is_current)
                VALUES (1, 2025, '○', 'verified', 1)
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


def test_export_master_filters_low_confidence_rows_and_reports_auto_flag(sqlite_engine, tmp_path) -> None:
    with Session(sqlite_engine) as session:
        low_school = School(
            prefecture="東京都",
            corporation_name="低信頼法人",
            school_name="低信頼専門学校",
            school_type="専門学校",
            status="active",
        )
        auto_school = School(
            prefecture="東京都",
            corporation_name="要確認法人",
            school_name="要確認専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add_all([low_school, auto_school])
        session.flush()

        low_dept = Department(school_id=low_school.id, canonical_name="低信頼学科")
        auto_dept = Department(school_id=auto_school.id, canonical_name="要確認学科")
        session.add_all([low_dept, auto_dept])
        session.flush()

        session.add_all(
            [
                DepartmentYearly(
                    department_id=low_dept.id,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    capacity=10,
                    enrollment=20,
                    extraction_confidence=0.64,
                    extraction_method="pdf_parse",
                ),
                DepartmentYearly(
                    department_id=auto_dept.id,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    capacity=30,
                    enrollment=40,
                    extraction_confidence=0.80,
                    extraction_method="pdf_parse",
                ),
                SupportRecipient(
                    school_id=low_school.id,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    annual_total=11,
                    grand_total=11,
                    extraction_confidence=0.64,
                ),
                SupportRecipient(
                    school_id=auto_school.id,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    annual_total=33,
                    grand_total=33,
                    extraction_confidence=0.80,
                ),
            ]
        )
        session.commit()

        output = tmp_path / "master.xlsx"
        stats = export_master_workbook(session, output)

    assert stats["quality_department_yearly_low_confidence_current"] == 1
    assert stats["quality_department_yearly_auto_flag_current"] == 1
    assert stats["quality_support_recipient_low_confidence_current"] == 1
    assert stats["quality_support_recipient_auto_flag_current"] == 1

    wb = openpyxl.load_workbook(output, data_only=True)
    try:
        taisho = wb["対象比率"]
        taisho_school_names = [taisho.cell(row=row, column=6).value for row in range(2, taisho.max_row + 1)]
        assert taisho_school_names == ["要確認専門学校"]

        gakka = wb["学科別"]
        rows_by_school = {
            gakka.cell(row=row, column=3).value: row
            for row in range(3, gakka.max_row + 1)
        }
        assert "低信頼専門学校" in rows_by_school
        assert "要確認専門学校" in rows_by_school

        year_col = next(
            col
            for col in range(1, gakka.max_column + 1)
            if gakka.cell(row=1, column=col).value == "2026年度"
        )
        assert gakka.cell(row=rows_by_school["低信頼専門学校"], column=year_col).value is None
        assert gakka.cell(row=rows_by_school["要確認専門学校"], column=year_col).value == 30
    finally:
        wb.close()
