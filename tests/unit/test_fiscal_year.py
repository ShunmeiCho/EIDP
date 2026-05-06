from datetime import date

from eidp.fiscal_year import (
    JapaneseEra,
    current_fiscal_year,
    fiscal_year_from_japanese_era_text,
    fiscal_year_search_tokens,
    format_fiscal_year_as_japanese_era,
    format_fiscal_year_label,
    reiwa_year_for_fiscal_year,
)


def test_current_fiscal_year_uses_april_boundary() -> None:
    assert current_fiscal_year(date(2027, 3, 31)) == 2026
    assert current_fiscal_year(date(2027, 4, 1)) == 2027


def test_format_fiscal_year_label_adds_reiwa_for_operator_copy() -> None:
    assert reiwa_year_for_fiscal_year(2026) == 8
    assert format_fiscal_year_as_japanese_era(2026) == "令和8年度"
    assert format_fiscal_year_label(2026) == "2026年度（令和8年度）"
    assert format_fiscal_year_label(2026, include_era=False) == "2026年度"


def test_fiscal_year_search_tokens_roll_with_target_year() -> None:
    tokens = fiscal_year_search_tokens(2027)

    assert "2027" in tokens
    assert "令和9" in tokens
    assert "r9" in tokens
    assert "2026" not in tokens


def test_fiscal_year_from_japanese_era_text_parses_labels_and_dates() -> None:
    assert fiscal_year_from_japanese_era_text("令和8年度 確認申請書") == 2026
    assert fiscal_year_from_japanese_era_text("令和8年6月1日 提出") == 2026
    assert (
        fiscal_year_from_japanese_era_text(
            "令和8年6月1日 提出",
            include_filing_dates=False,
        )
        is None
    )


def test_era_alias_layer_can_be_reconfigured_for_future_era() -> None:
    # Test-only dummy eras. This is not a prediction about any real future
    # Japanese era name or start year.
    eras = (
        JapaneseEra(name="AlphaEra", romanized="alphaera", initial="a", start_fiscal_year=2000, end_fiscal_year=2009),
        JapaneseEra(name="BetaEra", romanized="betaera", initial="b", start_fiscal_year=2010),
    )

    assert format_fiscal_year_label(2010, eras=eras) == "2010年度（BetaEra1年度）"
    assert fiscal_year_from_japanese_era_text("BetaEra2年度 確認申請書", eras=eras) == 2011

    tokens = fiscal_year_search_tokens(2010, eras=eras)
    assert "2010" in tokens
    assert "BetaEra1" in tokens
    assert "b1" in tokens
    assert "a11" not in tokens
