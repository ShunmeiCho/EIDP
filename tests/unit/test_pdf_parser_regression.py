from __future__ import annotations

from pathlib import Path

from eidp.pdf.extractor import (
    _extract_dept_identity_from_table,
    _extract_school_name,
    _find_dept_table,
    _is_template_header_text,
    _parse_department_section,
    parse_pdf,
)

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


def test_school_name_noise_strip_preserves_legitimate_leading_name_character() -> None:
    assert _extract_school_name("学校名 名古屋医専\n設置者名 学校法人") == "名古屋医専"
    assert _extract_school_name("学校名 称】名古屋医専\n設置者名 学校法人") == "名古屋医専"


def test_graduation_row_with_blank_advanced_and_other_keeps_graduate_count() -> None:
    section_text = """
生徒総定員数 生徒実員 うち留学生数 専任教員数 兼任教員数 総教員数
300 人 263 人 0人 26 人 22 人 48 人

卒業者数、進学者数、就職者数（直近の年度の状況を記載）

就職者数
卒業者数 進学者数 その他
（自営業を含む。）
86 人 人 86 人 人
（100％） （ ％） （ ％） （ ％）
"""

    dept = _parse_department_section(
        section_text,
        table_dept_name="第一学科",
        table_course_name="看護専門課程",
    )

    assert dept is not None
    assert dept.capacity == 300
    assert dept.enrollment == 263
    assert dept.graduates == 86
    assert dept.employed == 86


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


def test_find_dept_table_skips_school_info_table() -> None:
    """Caught in Path F' doc=329: 学校名 table comes before dept table."""
    tables = [
        [["学校名", "葵会仙台看護専門学校"], ["設置者名", "学校法人 医療創生大学"]],
        [["財務諸表等", "公表方法"], ["貸借対照表", "https://example.com"]],
        [
            ["分野", None, "課程名", None, "学科名", None, "専門士"],
            ["医療", None, "医療専門課程", None, "看護学科", None, "〇"],
            ["修業\n年限", "昼夜", "全課程の修了に必要な総\n授業時数又は総単位数", None, None, None, None],
            ["3年", "昼", "3000単位時間／単位", None, None, None, None],
        ],
    ]
    target, hidx = _find_dept_table(tables)
    assert target is tables[2]
    assert hidx == 0


def test_template_numeric_unit_pattern_rejected() -> None:
    """Caught in Path F' doc=329: parser leaked '1965単位 1035単位' as dept name."""
    assert _is_template_header_text("1965単位1035単位")
    assert _is_template_header_text("1230時間480時間900時間")
    assert not _is_template_header_text("看護学科")


def test_extract_dept_identity_strips_leading_field_prefix() -> None:
    """Caught in Path F' batch 50 doc=341: 分野 文化・教養 leaked into dept/course."""

    class FakePage:
        def extract_tables(self) -> list[list[list]]:
            return [
                [
                    ["分野", "課程名", "学科名", "専門士", "高度専門士"],
                    ["文化・教養", "文化・教養", "文化・教養グラフィックデザイン学科", "", "〇"],
                    ["修業年限", "昼夜", None, None, None],
                    ["2年", "昼", None, None, None],
                ]
            ]

    dept_name, course_name, duration, day_night = _extract_dept_identity_from_table(FakePage())
    assert dept_name == "グラフィックデザイン学科"
    # course_name was just the 分野 term with no 課程/本科 suffix -> dropped
    assert course_name == ""
    assert duration == 2
    assert day_night == "昼"


def test_leading_field_strip_preserves_legit_dept_names() -> None:
    """Legit names like 医療事務科 / 工業技術科 should not be stripped."""
    from eidp.pdf.extractor import _strip_leading_field_prefix

    # Strip: 分野 + proper 学科 suffix
    assert _strip_leading_field_prefix("文化・教養グラフィックデザイン学科") == "グラフィックデザイン学科"
    assert _strip_leading_field_prefix("医療看護学科") == "看護学科"
    # Preserve: name that happens to start with 分野 word but remainder is too short
    assert _strip_leading_field_prefix("工業科") == "工業科"
    # Preserve: no matching suffix after strip
    assert _strip_leading_field_prefix("医療センター職員") == "医療センター職員"


def test_extract_dept_identity_strips_marker_and_dedupe_field_prefix() -> None:
    """Caught in Path F' doc=336: course_name had '医療医療専門課程' duplicated prefix
    and '〇' marker bleed."""

    class FakePage:
        def extract_tables(self) -> list[list[list]]:
            return [
                [
                    ["分野", "課程名", "学科名", "専門士"],
                    ["医療", "医療医療専門課程看護学科〇", "看護学科〇", "〇"],
                    ["修業年限", "昼夜", None, None],
                    ["3年", "昼", None, None],
                ]
            ]

    dept_name, course_name, duration, day_night = _extract_dept_identity_from_table(FakePage())
    assert dept_name == "看護学科"
    assert course_name == "医療専門課程看護学科"
    assert duration == 3
    assert day_night == "昼"
