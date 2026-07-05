"""Slice 4a (RED->GREEN): join-key normalizers that reconcile PDF-extracted
department identity to data/master.xlsx 学科別 rows -- the load-bearing fix for the
"89 unmatched schools" class.

Verified mismatch shapes (data/master.xlsx 学科別, read-only):
- master 課程名 column holds the 8-value 分野 taxonomy (商業実務 ...); PDF gives
  分野 there and 課程名=専門課程 (the level) which is excluded from the join.
- master 学科名 carries a 学科/科 suffix and half-width digits (ビジネスキャリア2年制学科);
  the PDF gives ビジネスキャリア２年制 (full-width, no suffix, embedded newline).
- master metric columns are FY-blocked with a NON-uniform stride (2019 has no 備考).
  master tops out at FY2025 -> FY2026 has no ground truth here.
"""

import pytest

from eidp.pdf.master_ground_truth import (
    canonical_field_category,
    department_key,
    fy_metric_columns,
    normalize_text,
)


def test_normalize_text_folds_fullwidth_and_whitespace() -> None:
    assert normalize_text("　ビジネスキャリア\n２年制　") == "ビジネスキャリア2年制"


def test_field_category_is_middle_dot_insensitive() -> None:
    assert canonical_field_category("文化・教養") == canonical_field_category("文化教養")
    assert canonical_field_category("教育・社会福祉") == canonical_field_category("教育社会福祉")
    assert canonical_field_category("服飾・家政") == canonical_field_category("服飾家政")


def test_field_category_matches_pdf_to_master() -> None:
    # PDF field_category (商業実務) must equal master 課程名 (商業実務).
    assert canonical_field_category("商業実務") == canonical_field_category("商業実務")
    # 看護 is a known alias of the 医療 分野.
    assert canonical_field_category("看護") == canonical_field_category("医療")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ビジネスキャリア2年制学科", "ビジネスキャリア2年制"),  # strip 学科
        ("情報システム学科", "情報システム"),
        ("ITスペシャリスト科", "ITスペシャリスト"),  # strip 科 (not 学科)
        ("看護学科", "看護"),
        ("グラフィックデザイン", "グラフィックデザイン"),  # no suffix -> verbatim
    ],
)
def test_department_key_strips_one_trailing_suffix(raw: str, expected: str) -> None:
    assert department_key(raw) == expected


def test_department_key_lands_pdf_onto_master() -> None:
    # THE load-bearing 大原 proof: master 'ビジネスキャリア2年制学科' and the PDF's
    # 'ビジネスキャリア\n２年制' (full-width, newline, no suffix) must key identically.
    master_name = "ビジネスキャリア2年制学科"
    pdf_name = "ビジネスキャリア\n２年制"
    assert department_key(master_name) == department_key(pdf_name)


def test_department_key_drops_trailing_course_qualifier() -> None:
    # 8 山形校: PDF writes '(ビジネスコース)', master '（ビジネス）'. After NFKC the only
    # residue is コース; stripping it at the trailing edge makes both key identically.
    assert department_key("税理士・ビジネス学科(ビジネスコース)") == "税理士・ビジネス学科(ビジネス)"
    assert department_key("税理士・ビジネス学科(ビジネスコース)") == department_key(
        "税理士・ビジネス学科（ビジネス）"
    )
    # コース is only dropped at the trailing edge / before a closing paren, never mid-name.
    assert department_key("公務員学科2年制") == "公務員学科2年制"


def test_fy_metric_columns_capacity_enrollment_intl_offsets() -> None:
    # 収定 / 在籍 / 留学生 are consecutive; FY block start comes from the master layout.
    assert fy_metric_columns(2019) == (7, 8, 9)
    assert fy_metric_columns(2025) == (72, 73, 74)


def test_fy_block_stride_is_non_uniform_2019_has_no_biko() -> None:
    # 2019 (no 備考) -> 2020 is +10; 2020+ (with 備考) -> +11. Never a fixed stride.
    assert fy_metric_columns(2020)[0] - fy_metric_columns(2019)[0] == 10
    assert fy_metric_columns(2021)[0] - fy_metric_columns(2020)[0] == 11


def test_fy2026_is_unsupported_master_tops_at_2025() -> None:
    # data/master.xlsx has no FY2026 column: 2026 PDFs cannot be diffed here.
    with pytest.raises((KeyError, ValueError)):
        fy_metric_columns(2026)
