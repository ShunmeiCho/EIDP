"""Slice 2/3 (RED->GREEN): table-aware, grid-position extraction of enrollment
numbers from a 機関要件確認申請書 part-5 department table.

The fixture mirrors the REAL 大原 part-5 table layout (verified via find_tables):
one table per 学科, with an identity header (分野/課程名/学科名) and an enrollment
header (学生総定員数/学生実員/うち留学生数 + teacher-staffing columns that MUST be
ignored). Values are public institutional aggregates, not personal data.

This tests the load-bearing SEMANTIC MAPPING the adversarial review flagged: which
column is capacity vs enrollment vs intl, and never reading a teacher count as one.
"""

import os
from pathlib import Path

import pytest

from eidp.pdf.table_grid_extractor import (
    TableDepartmentRecord,
    extract_table_grid_records,
    map_table_to_record,
)

# Real 大原 2026-1-01-01-5.pdf page-8 table (商業実務 / ビジネスキャリア２年制).
OHARA_PART5_TABLE = [
    ["分野", "", "課程名", "", "学科名", "", "", "", "専門士", "", "", "高度専門士", "", ""],
    ["商業実務", "", "専門課程", "", "ビジネスキャリア\n２年制", "", "", "", "〇", "", "", "―", "", ""],
    ["修業\n年限", "昼夜", "全課程の修了に必要な総\n", "", "",
     "開設している授業の種類", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "講義", "", "演習", "", "実習", "実験", "", "", "実技"],
    ["2 年", "昼", "62 単位", "", "", "247 単位", "", "49 単位", "", "0 単位", "0 単位", "", "", "0 単位"],
    ["", "", "", "", "", "296 単位", "", "", "", "", "", "", "", ""],
    ["学生総定員数", "", "学生実員", "うち留学生数", "", "",
     "専任教員数", "", "", "兼任教員数", "", "", "総教員数", ""],
    ["120 人", "", "104 人", "0 人", "", "", "6 人", "", "", "0 人", "", "", "6 人", ""],
]


def test_maps_ohara_part5_table_to_canonical_record() -> None:
    rec = map_table_to_record(OHARA_PART5_TABLE, page_no=8, table_index=2)
    assert isinstance(rec, TableDepartmentRecord)
    assert rec.field_category == "商業実務"
    assert rec.course_name == "専門課程"
    # NFKC folds ２->2 and the stray newline is stripped; 学科 suffix is a Slice-4 concern.
    assert rec.department_name == "ビジネスキャリア2年制"
    assert rec.capacity == 120
    assert rec.enrollment == 104
    assert rec.intl_students == 0


def test_teacher_columns_never_become_metric_values() -> None:
    rec = map_table_to_record(OHARA_PART5_TABLE, page_no=8, table_index=2)
    assert rec is not None
    metrics = {e.canonical_metric for e in rec.evidence}
    assert metrics <= {"capacity", "enrollment", "intl_students"}
    # 6 (専任教員数 / 総教員数) must never be mistaken for capacity/enrollment/intl.
    assert 6 not in {rec.capacity, rec.enrollment, rec.intl_students}


def test_evidence_pins_page_table_row_col_and_raw_value() -> None:
    rec = map_table_to_record(OHARA_PART5_TABLE, page_no=8, table_index=2)
    assert rec is not None
    cap = next(e for e in rec.evidence if e.canonical_metric == "capacity")
    assert cap.page_no == 8
    assert cap.table_index == 2
    assert cap.col_index == 0
    assert "120" in cap.raw_value
    assert cap.confidence == 1.0


def test_seito_and_gakusei_headers_both_extract() -> None:
    seito = [row[:] for row in OHARA_PART5_TABLE]
    seito[6] = ["生徒総定員数", "", "生徒実員", "うち留学生数", "", "",
                "専任教員数", "", "", "兼任教員数", "", "", "総教員数", ""]
    rec = map_table_to_record(seito, page_no=8, table_index=2)
    assert rec is not None
    assert rec.capacity == 120
    assert rec.enrollment == 104


def test_table_without_enrollment_header_returns_none() -> None:
    junk = [["分野", "課程名", "学科名"], ["工業", "専門課程", "情報システム学科"]]
    assert map_table_to_record(junk, page_no=1, table_index=0) is None


def test_zero_enrollment_is_kept_not_dropped() -> None:
    # A brand-new 学科 with 実員 0 is valid data (0), not a missing value.
    zero = [row[:] for row in OHARA_PART5_TABLE]
    zero[7] = ["40 人", "", "0 人", "0 人", "", "", "0 人", "", "", "0 人", "", "", "0 人", ""]
    rec = map_table_to_record(zero, page_no=4, table_index=2)
    assert rec is not None
    assert rec.capacity == 40
    assert rec.enrollment == 0
    assert rec.intl_students == 0


_SAMPLE_DIR = os.environ.get("EIDP_OHARA_SAMPLE_DIR")


@pytest.mark.skipif(not _SAMPLE_DIR, reason="set EIDP_OHARA_SAMPLE_DIR to a dir with real 大原 part-5 PDFs")
def test_real_ohara_part5_pdf_yields_enrollment_records() -> None:
    pdf = Path(_SAMPLE_DIR or ".") / "2026-1-01-01-5.pdf"
    if not pdf.exists():
        pytest.skip(f"sample not found: {pdf}")
    records = extract_table_grid_records(pdf)
    assert records, "expected at least one department record from the real PDF"
    assert any(r.enrollment is not None for r in records)
    assert all(r.capacity is None or r.capacity >= 0 for r in records)
