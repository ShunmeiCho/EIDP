"""Fiscal-year presentation and parsing helpers.

EIDP stores fiscal years as western years (for example 2026). Japanese
operator-facing copy and official disclosure pages often also need Japanese
era aliases such as ``令和8年度``. The western year remains the source of truth;
era labels are replaceable presentation/search aliases.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class JapaneseEra:
    """Japanese era metadata used only for labels and search/parser aliases."""

    name: str
    romanized: str
    initial: str
    start_fiscal_year: int
    start_era_year: int = 1
    end_fiscal_year: int | None = None

    def year_for_fiscal_year(self, fiscal_year: int) -> int | None:
        if fiscal_year < self.start_fiscal_year:
            return None
        if self.end_fiscal_year is not None and fiscal_year > self.end_fiscal_year:
            return None
        return fiscal_year - self.start_fiscal_year + self.start_era_year

    def fiscal_year_for_era_year(self, era_year: int) -> int | None:
        if era_year < self.start_era_year:
            return None
        fiscal_year = self.start_fiscal_year + (era_year - self.start_era_year)
        if self.end_fiscal_year is not None and fiscal_year > self.end_fiscal_year:
            return None
        return fiscal_year


JAPANESE_ERAS: tuple[JapaneseEra, ...] = (
    JapaneseEra(name="令和", romanized="reiwa", initial="r", start_fiscal_year=2019),
)
_ACTIVE_JAPANESE_ERAS: tuple[JapaneseEra, ...] = JAPANESE_ERAS


def configure_japanese_eras(eras: Sequence[JapaneseEra]) -> None:
    """Replace the process-wide era alias table.

    The application does not predict future Japanese era changes. Admin/operator
    settings can call this when the official naming changes; the canonical
    fiscal-year value remains western year integers.
    """
    global _ACTIVE_JAPANESE_ERAS
    _ACTIVE_JAPANESE_ERAS = tuple(eras) if eras else ()


def active_japanese_eras() -> tuple[JapaneseEra, ...]:
    """Return the currently configured era aliases."""
    return _ACTIVE_JAPANESE_ERAS


def _eras_or_active(eras: Sequence[JapaneseEra] | None) -> Sequence[JapaneseEra]:
    return active_japanese_eras() if eras is None else eras


def current_fiscal_year(today: date | datetime | None = None) -> int:
    """Return the Japanese fiscal year for ``today``.

    Japanese academic/business fiscal years run April through March. This is
    the default operational target year when the operator has not pinned an
    explicit override in ``EIDP_TARGET_FISCAL_YEAR``.
    """
    current = today or date.today()
    return current.year if current.month >= 4 else current.year - 1


def japanese_era_for_fiscal_year(
    fiscal_year: int,
    *,
    eras: Sequence[JapaneseEra] | None = None,
) -> tuple[JapaneseEra, int] | None:
    """Return the configured Japanese era alias for ``fiscal_year`` if known."""
    for era in sorted(_eras_or_active(eras), key=lambda item: item.start_fiscal_year, reverse=True):
        era_year = era.year_for_fiscal_year(fiscal_year)
        if era_year is not None:
            return era, era_year
    return None


def reiwa_year_for_fiscal_year(fiscal_year: int) -> int | None:
    """Return the Reiwa year for compatibility with older callers/tests."""
    reiwa = next((era for era in active_japanese_eras() if era.name == "令和"), None)
    if reiwa is None:
        return None
    return reiwa.year_for_fiscal_year(fiscal_year)


def format_fiscal_year_as_japanese_era(
    fiscal_year: int,
    *,
    eras: Sequence[JapaneseEra] | None = None,
) -> str | None:
    """Format ``fiscal_year`` as a configured Japanese era label if possible."""
    active = japanese_era_for_fiscal_year(fiscal_year, eras=eras)
    if active is None:
        return None
    era, era_year = active
    return f"{era.name}{era_year}年度"


def format_fiscal_year_label(
    fiscal_year: int,
    *,
    include_era: bool = True,
    eras: Sequence[JapaneseEra] | None = None,
) -> str:
    """Format a fiscal year for operator-facing UI labels."""
    western_label = f"{fiscal_year}年度"
    if not include_era:
        return western_label
    era_label = format_fiscal_year_as_japanese_era(fiscal_year, eras=eras)
    if era_label is None:
        return western_label
    return f"{western_label}（{era_label}）"


def fiscal_year_search_tokens(
    fiscal_year: int,
    *,
    eras: Sequence[JapaneseEra] | None = None,
) -> tuple[str, ...]:
    """Return URL/anchor tokens that indicate a fiscal year in disclosure links."""
    tokens = [str(fiscal_year)]
    active = japanese_era_for_fiscal_year(fiscal_year, eras=eras)
    if active is not None:
        era, era_year = active
        tokens.extend(
            [
                f"{era.name}{era_year}",
                f"{era.name}{era_year:02d}",
                f"{era.initial}{era_year}",
                f"{era.initial}{era_year:02d}",
                f"{era.romanized}{era_year}",
            ]
        )
    return tuple(tokens)


def fiscal_year_from_japanese_era_text(
    text: str,
    *,
    include_fiscal_year_labels: bool = True,
    include_filing_dates: bool = True,
    eras: Sequence[JapaneseEra] | None = None,
) -> int | None:
    """Parse a western fiscal year from configured Japanese era text.

    Supported examples for the default era table:
    - ``令和8年度`` -> 2026
    - ``令和8年6月1日`` -> 2026 when ``include_filing_dates`` is true
    """
    normed = unicodedata.normalize("NFKC", text)
    for era in sorted(_eras_or_active(eras), key=lambda item: item.start_fiscal_year, reverse=True):
        escaped_name = re.escape(era.name)
        if include_fiscal_year_labels:
            m = re.search(rf"{escaped_name}\s*(\d+)\s*年度", normed)
            if m:
                return era.fiscal_year_for_era_year(int(m.group(1)))
        if include_filing_dates:
            m = re.search(rf"{escaped_name}\s*(\d+)\s*年\s*\d+\s*月\s*\d+\s*日", normed)
            if m:
                return era.fiscal_year_for_era_year(int(m.group(1)))
    return None
