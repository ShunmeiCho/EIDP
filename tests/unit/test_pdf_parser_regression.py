from __future__ import annotations

from pathlib import Path

from eidp.pdf.extractor import _parse_department_section, parse_pdf

PDF_DIR = Path(__file__).resolve().parents[2] / "data" / "sample-pdfs"


def test_hal_tokyo_skips_course_breakdown_sections() -> None:
    annotation = parse_pdf(PDF_DIR / "nkz.pdf")

    assert len(annotation.departments) == 19
    assert [dept.name for dept in annotation.departments[:3]] == [
        "カーデザイン学科",
        "ミュージック学科（4年制）",
        "ゲーム学科",
    ]
    assert all("ゲーム4年制学科" not in dept.name for dept in annotation.departments)
    assert all("高度情報学科" not in dept.name for dept in annotation.departments)


def test_jec_enrollment_row_keeps_capacity_without_person_suffix() -> None:
    annotation = parse_pdf(PDF_DIR / "jec.pdf")

    dept = next(dept for dept in annotation.departments if dept.name == "情報システム開発科")

    assert dept.capacity == 160
    assert dept.enrollment == 153
    assert dept.intl_students == 54


def test_text_fallback_does_not_use_template_header_as_department_name() -> None:
    section_text = """
分野
課程名
学科名
専門士
高度専門士
医療関係
医療専門課程
修業 全課程の修了に必要な総 開設している授業の種類
看護学科
修業年限
3年 昼
生徒総定員数 生徒実員 うち留学生数 専任教員数 兼任教員数 総教員数
80 20人 16人 3人 2人 5人
"""

    dept = _parse_department_section(section_text)

    assert dept is not None
    assert dept.name == "看護学科"
    assert dept.capacity == 80
    assert dept.enrollment == 20
    assert dept.intl_students == 16
