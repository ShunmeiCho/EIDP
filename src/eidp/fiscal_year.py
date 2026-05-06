"""Fiscal-year presentation helpers.

EIDP stores fiscal years as western years (for example 2026). Japanese
operator-facing copy often also needs the Reiwa label (令和8年度).
"""

from __future__ import annotations

from datetime import date, datetime


def current_fiscal_year(today: date | datetime | None = None) -> int:
    """Return the Japanese fiscal year for ``today``.

    Japanese academic/business fiscal years run April through March. This is
    the default operational target year when the operator has not pinned an
    explicit override in ``EIDP_TARGET_FISCAL_YEAR``.
    """
    current = today or date.today()
    return current.year if current.month >= 4 else current.year - 1


def reiwa_year_for_fiscal_year(fiscal_year: int) -> int | None:
    """Return the Reiwa year for a western fiscal year, if in Reiwa era."""
    if fiscal_year < 2019:
        return None
    return fiscal_year - 2018


def format_fiscal_year_label(fiscal_year: int) -> str:
    """Format a fiscal year for operator-facing UI labels."""
    reiwa_year = reiwa_year_for_fiscal_year(fiscal_year)
    if reiwa_year is None:
        return f"{fiscal_year}年度"
    return f"{fiscal_year}年度（令和{reiwa_year}年度）"


def fiscal_year_search_tokens(fiscal_year: int) -> tuple[str, ...]:
    """Return URL/anchor tokens that indicate a fiscal year in disclosure links."""
    tokens = [str(fiscal_year)]
    reiwa_year = reiwa_year_for_fiscal_year(fiscal_year)
    if reiwa_year is not None:
        tokens.extend(
            [
                f"令和{reiwa_year}",
                f"令和{reiwa_year:02d}",
                f"r{reiwa_year}",
                f"r{reiwa_year:02d}",
                f"reiwa{reiwa_year}",
            ]
        )
    return tuple(tokens)
