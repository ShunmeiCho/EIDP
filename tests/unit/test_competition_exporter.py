from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from eidp.excel.competition_exporter import (
    _norm,
    parse_sheet_schema,
    parse_template,
)


SAMPLE_TEMPLATE = Path(__file__).resolve().parents[2] / "sample" / "20250826更新版_競合校の在校生数.xlsx"


def _build_category_sheet() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "ゲーム"
    # Row 2: year markers
    ws.cell(2, 4, value=2024)
    ws.cell(2, 6, value=2025)
    # Row 3: 在籍数 / 留学生 headers
    ws.cell(3, 4, value="在籍数")
    ws.cell(3, 5, value="留学生")
    ws.cell(3, 6, value="在籍数")
    ws.cell(3, 7, value="留学生")
    # Row 4: data
    ws.cell(4, 1, value="日本工学院（蒲田）")
    ws.cell(4, 2, value="ゲームクリエイター科")
    ws.cell(4, 3, value="2年制")
    ws.cell(4, 4, value=292)
    ws.cell(4, 5, value=50)
    # Row 5: ratio (no school)
    ws.cell(5, 4, value=None)
    return wb


def test_parse_sheet_schema_finds_year_columns_and_data_rows() -> None:
    wb = _build_category_sheet()
    schema = parse_sheet_schema(wb["ゲーム"])
    assert schema is not None
    assert schema.header_row == 3
    assert [yc.fiscal_year for yc in schema.year_cols] == [2024, 2025]
    assert schema.school_col == 1
    assert schema.dept_col == 2
    assert len(schema.data_rows) == 1
    row = schema.data_rows[0]
    assert row.school_name == "日本工学院(蒲田)"  # NFKC normalized
    assert row.dept_name == "ゲームクリエイター科"
    assert row.duration_label == "2年制"


def test_norm_strips_whitespace_and_normalizes_fullwidth() -> None:
    assert _norm("日本工学院 （蒲田）") == "日本工学院(蒲田)"
    assert _norm(None) == ""
    assert _norm("ｸﾞﾗﾌｨｯｸ") == "グラフィック"


@pytest.mark.skipif(not SAMPLE_TEMPLATE.exists(), reason="sample template absent")
def test_parse_template_recognises_all_16_sheets() -> None:
    schemas = parse_template(SAMPLE_TEMPLATE)
    # All sheets are competition sheets in the sample
    assert len(schemas) == 16
    # 学校単位 is the rollup, others have dept_col
    assert schemas["学校単位での比較"].is_rollup is True
    assert schemas["学校単位での比較"].dept_col is None
    assert schemas["ゲーム"].is_rollup is False
    assert schemas["ゲーム"].dept_col == 2
    # Every sheet must include 2025 (latest baseline) in year_cols
    for name, schema in schemas.items():
        years = {yc.fiscal_year for yc in schema.year_cols}
        assert 2025 in years, f"{name} missing 2025"


@pytest.mark.skipif(not SAMPLE_TEMPLATE.exists(), reason="sample template absent")
def test_parse_template_extracts_data_rows() -> None:
    schemas = parse_template(SAMPLE_TEMPLATE)
    # Sample sheets have at least one data row each
    for name, schema in schemas.items():
        assert len(schema.data_rows) > 0, f"{name} has no data rows"
