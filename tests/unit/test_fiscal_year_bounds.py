from __future__ import annotations

from eidp.pdf.extractor import _extract_fiscal_year
from eidp.pipeline.ingest import _parse_fiscal_year_from_annotation


def test_future_reiwa_year_is_rejected() -> None:
    assert _parse_fiscal_year_from_annotation("令和9年度", max_fiscal_year=2026) is None


def test_past_reiwa_year_is_accepted() -> None:
    assert _parse_fiscal_year_from_annotation("令和7年度", max_fiscal_year=2026) == 2025


def test_current_reiwa_year_is_accepted() -> None:
    assert _parse_fiscal_year_from_annotation("令和8年度", max_fiscal_year=2026) == 2026


def test_current_fiscal_year_is_accepted_even_when_source_url_has_prior_year() -> None:
    assert (
        _parse_fiscal_year_from_annotation(
            "令和8年度",
            source_url="https://example.ac.jp/wp-content/uploads/2025/confirmation.pdf",
            max_fiscal_year=2026,
        )
        == 2026
    )


def test_extractor_ignores_future_policy_year_references() -> None:
    assert _extract_fiscal_year("2025_confirmation.pdf 2027年度決算", max_fiscal_year=2026) == ""


def test_extractor_falls_through_past_future_reiwa_reference() -> None:
    assert _extract_fiscal_year("令和9年度決算資料\n2025.06.01", max_fiscal_year=2026) == "令和7年度"
