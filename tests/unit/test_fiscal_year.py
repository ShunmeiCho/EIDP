from eidp.fiscal_year import (
    fiscal_year_search_tokens,
    format_fiscal_year_label,
    reiwa_year_for_fiscal_year,
)


def test_format_fiscal_year_label_adds_reiwa_for_operator_copy() -> None:
    assert reiwa_year_for_fiscal_year(2026) == 8
    assert format_fiscal_year_label(2026) == "2026年度（令和8年度）"


def test_fiscal_year_search_tokens_roll_with_target_year() -> None:
    tokens = fiscal_year_search_tokens(2027)

    assert "2027" in tokens
    assert "令和9" in tokens
    assert "r9" in tokens
    assert "2026" not in tokens
