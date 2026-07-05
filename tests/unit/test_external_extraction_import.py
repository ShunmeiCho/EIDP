from __future__ import annotations

import csv
import io
from pathlib import Path

from eidp.pipeline.external_extraction_import import (
    ExternalSourceSystem,
    load_external_extraction_csv,
    load_external_extraction_xlsx,
)


def test_csv_import_normalizes_wide_external_rows() -> None:
    content = "\n".join(
        [
            "school_name,school_id,corporation_name,prefecture,field_category,course_name,department_name,"
            "fiscal_year,capacity,enrollment,intl_students,notes",
            "東京テスト専門学校,S-001,学校法人テスト,東京都,商業実務,専門課程,テスト学科,2025,40,37,3,checked",
        ]
    ).encode()

    rows = load_external_extraction_csv(
        content,
        source_system=ExternalSourceSystem.COPILOT,
        source_file="copilot.csv",
    )

    assert [row.metric for row in rows] == ["capacity", "enrollment", "intl_students"]
    assert {row.value for row in rows} == {40, 37, 3}
    assert {row.source_system for row in rows} == {ExternalSourceSystem.COPILOT}
    assert {row.source_file for row in rows} == {"copilot.csv"}
    assert {row.source_row_number for row in rows} == {2}
    assert all(row.school_name == "東京テスト専門学校" for row in rows)
    assert all(row.department_name == "テスト学科" for row in rows)
    assert all(row.notes == "checked" for row in rows)


def test_csv_import_accepts_long_metric_rows() -> None:
    content = "\n".join(
        [
            "学校名,学科名,年度,指標,値",
            "東京テスト専門学校,テスト学科,2025,在学者数,37",
        ]
    ).encode()

    rows = load_external_extraction_csv(
        content,
        source_system="notebooklm",
        source_file="notebooklm.csv",
    )

    assert len(rows) == 1
    assert rows[0].source_system == ExternalSourceSystem.NOTEBOOKLM
    assert rows[0].metric == "enrollment"
    assert rows[0].value == 37


def test_xlsx_import_normalizes_wide_external_rows(tmp_path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "external"
    ws.append(["学校名", "学科名", "年度", "収容定員", "在籍", "留学生"])
    ws.append(["東京テスト専門学校", "テスト学科", 2025, 40, 37, 3])
    path = tmp_path / "external.xlsx"
    wb.save(path)
    wb.close()
    before = path.read_bytes()

    rows = load_external_extraction_xlsx(
        path,
        source_system=ExternalSourceSystem.MANUAL_EXTERNAL,
    )

    assert path.read_bytes() == before
    assert [row.metric for row in rows] == ["capacity", "enrollment", "intl_students"]
    assert {row.value for row in rows} == {40, 37, 3}
    assert {row.source_file for row in rows} == {"external.xlsx"}


def test_import_report_rows_are_csv_safe() -> None:
    content = "\n".join(
        [
            "school_name,department_name,fiscal_year,capacity",
            "東京テスト専門学校,テスト学科,2025,\"1,200\"",
        ]
    ).encode()

    rows = load_external_extraction_csv(
        content,
        source_system=ExternalSourceSystem.COPILOT,
        source_file="copilot.csv",
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([rows[0].school_name, rows[0].metric, rows[0].value])

    assert rows[0].value == 1200
    assert "capacity" in output.getvalue()
