from __future__ import annotations

from pathlib import Path

from eidp.pdf.extractor import parse_pdf

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
