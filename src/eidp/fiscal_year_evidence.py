"""Fiscal-year evidence ladder.

The same PDF can expose different year signals: URL/anchor hints, parsed PDF
text, or an operator override. The ladder keeps those signals ordered so old
year PDFs are not promoted just because their URL contains the target year.
"""

from __future__ import annotations

from dataclasses import dataclass

from eidp.db.models import Document
from eidp.fiscal_year import fiscal_year_search_tokens

EVIDENCE_RANK: dict[str, int] = {
    "none": 0,
    "conflict": 0,
    "download_time": 1,
    "url_hint": 2,
    "pdf_text": 3,
    "prev_year_diff": 4,
    "operator_override": 5,
}


@dataclass(frozen=True)
class FiscalYearEvidence:
    level: str
    rank: int
    detected_fiscal_year: int | None = None
    conflict_reason: str | None = None

    @property
    def confirms_target(self) -> bool:
        return self.detected_fiscal_year is not None and self.conflict_reason is None


def fiscal_year_evidence_for_document(
    doc: Document,
    *,
    target_fiscal_year: int,
) -> FiscalYearEvidence:
    """Return the strongest fiscal-year evidence visible on ``doc``.

    Parsed/operator fiscal years outrank URL hints. If parsed text says FY2025
    but the URL says FY2026, the result is ``conflict`` rather than ``url_hint``.
    """
    if doc.fiscal_year_override is not None:
        if doc.fiscal_year_override == target_fiscal_year:
            return FiscalYearEvidence("operator_override", EVIDENCE_RANK["operator_override"], target_fiscal_year)
        return FiscalYearEvidence(
            "conflict",
            EVIDENCE_RANK["conflict"],
            doc.fiscal_year_override,
            "operator_override_mismatch",
        )

    if doc.fiscal_year is not None:
        if doc.fiscal_year == target_fiscal_year:
            return FiscalYearEvidence("pdf_text", EVIDENCE_RANK["pdf_text"], target_fiscal_year)
        return FiscalYearEvidence(
            "conflict",
            EVIDENCE_RANK["conflict"],
            doc.fiscal_year,
            "pdf_text_mismatch",
        )

    text = " ".join(part for part in (doc.source_url, doc.discovered_from) if part).lower()
    if any(token.lower() in text for token in fiscal_year_search_tokens(target_fiscal_year)):
        return FiscalYearEvidence("url_hint", EVIDENCE_RANK["url_hint"], target_fiscal_year)

    return FiscalYearEvidence("none", EVIDENCE_RANK["none"])
