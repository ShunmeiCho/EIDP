import eidp.pdf.extractor as extractor_module
from eidp.fiscal_year import JapaneseEra, active_japanese_eras, configure_japanese_eras
from eidp.pdf.extractor import _extract_fiscal_year


def test_extract_fiscal_year_accepts_2030s_western_filing_date() -> None:
    text = "確認申請書\n提出日 2030.6.1\n"

    assert _extract_fiscal_year(text, max_fiscal_year=2030) == "令和12年度"


def test_extract_fiscal_year_default_cap_uses_configured_target(monkeypatch) -> None:
    monkeypatch.setattr(extractor_module.settings, "target_fiscal_year", 2030)

    assert _extract_fiscal_year("令和12年度 確認申請書") == "令和12年度"


def test_extract_fiscal_year_uses_active_era_configuration() -> None:
    original = active_japanese_eras()
    try:
        configure_japanese_eras((
            JapaneseEra(name="BetaEra", romanized="betaera", initial="b", start_fiscal_year=2030),
        ))

        assert _extract_fiscal_year("BetaEra2年度 確認申請書", max_fiscal_year=2031) == "BetaEra2年度"
    finally:
        configure_japanese_eras(original)


def test_extract_fiscal_year_fallback_accepts_2030s_western_year() -> None:
    text = "2031年度 申請内容\n2031年 在学者数\n2030年度 参考値\n"

    assert _extract_fiscal_year(text, max_fiscal_year=2031) == "令和13年度"


def test_extract_fiscal_year_ignores_pre_supported_western_years() -> None:
    text = "2005年度 沿革\n2018年度 旧制度説明\n"

    assert _extract_fiscal_year(text, max_fiscal_year=2030) == ""


def test_extract_fiscal_year_fallback_skips_pre_supported_years() -> None:
    text = "2018年度 沿革\n2018年 旧制度\n2030年度 申請内容\n"

    assert _extract_fiscal_year(text, max_fiscal_year=2030) == "令和12年度"


def test_extract_fiscal_year_ignores_post_supported_japanese_era_year() -> None:
    text = "令和82年度 確認申請書\n2100年度 申請内容\n"

    assert _extract_fiscal_year(text, max_fiscal_year=2100) == ""
