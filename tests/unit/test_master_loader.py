"""Slice 4b (RED->GREEN): read-only master.xlsx loader.

Unit tests build a SYNTHETIC 学科別-shaped workbook in tmp_path (never data/master.xlsx)
and use fiscal_year=2019 (columns 7/8/9). A skip-if-absent smoke reads the real
data/master.xlsx READ-ONLY to prove the loader works on the actual sheet.
"""

from pathlib import Path

import pytest

from eidp.excel.master_loader import load_master_metric_rows


def _make_master(tmp_path: Path) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学科別"
    ws.append([None] * 7 + ["2019年度", None, None])  # row1: year-group header
    ws.append(["都道府県", "法人名", "学校名", "課程名", "学科名", "昼夜", "年限", "収定", "在籍", "留学生"])
    ws.append(["北海道", "大原学園", "大原簿記情報専門学校札幌校", "商業実務", "会計2年制学科", "昼", "2", 80, 70, 0])
    ws.append(["東京都", "他法人", "他校", "工業", "情報学科", "昼", "2", 40, 30, 5])
    path = tmp_path / "synthetic_master.xlsx"
    wb.save(str(path))
    wb.close()
    return path


def test_loads_only_target_school_metrics(tmp_path: Path) -> None:
    path = _make_master(tmp_path)
    rows = load_master_metric_rows(
        path, corporation_name="大原学園",
        school_name="大原簿記情報専門学校札幌校", fiscal_year=2019,
    )
    assert len(rows) == 3
    assert {r.metric: r.value for r in rows} == {"capacity": 80, "enrollment": 70, "intl_students": 0}
    assert all(r.source_sheet == "学科別" for r in rows)
    assert rows[0].department_key == "商業実務|会計2年制"  # 分野 folded + 学科 suffix stripped
    assert rows[0].school_key == "大原学園"
    assert rows[0].campus_key == "大原簿記情報専門学校札幌校"


def test_filters_out_other_schools(tmp_path: Path) -> None:
    path = _make_master(tmp_path)
    rows = load_master_metric_rows(
        path, corporation_name="他法人", school_name="他校", fiscal_year=2019,
    )
    assert {r.value for r in rows} == {40, 30, 5}


def test_read_only_does_not_mutate_the_workbook(tmp_path: Path) -> None:
    path = _make_master(tmp_path)
    before = path.read_bytes()
    load_master_metric_rows(
        path, corporation_name="大原学園",
        school_name="大原簿記情報専門学校札幌校", fiscal_year=2019,
    )
    assert path.read_bytes() == before  # loader never writes the source


def test_fiscal_year_beyond_master_raises(tmp_path: Path) -> None:
    path = _make_master(tmp_path)
    with pytest.raises(KeyError):
        load_master_metric_rows(
            path, corporation_name="大原学園",
            school_name="大原簿記情報専門学校札幌校", fiscal_year=2026,
        )


@pytest.mark.skipif(not Path("data/master.xlsx").exists(), reason="operator data/master.xlsx absent")
def test_real_master_loads_ohara_fy2025_read_only() -> None:
    rows = load_master_metric_rows(
        "data/master.xlsx", corporation_name="大原学園",
        school_name="大原簿記情報専門学校札幌校", fiscal_year=2025,
    )
    assert rows, "expected 札幌校 departments in the real master"
    assert all(r.source_sheet == "学科別" for r in rows)
    assert {r.metric for r in rows} <= {"capacity", "enrollment", "intl_students"}
