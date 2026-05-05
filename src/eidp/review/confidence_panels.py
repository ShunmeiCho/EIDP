"""Sprint 8.6.d.1 — UI render helpers for ``confidence_breakdown``.

Pure helpers consumed by the Streamlit pages (PDF確認・手入力 / 年度修正
/ Excel preview / 監査ログ). No ``streamlit`` imports — that lives in
the page renderers; this module produces the data shape they display.

The contract:

* parse the ``confidence_breakdown`` TEXT JSON column into a frozen
  ``ConfidenceBreakdown``,
* derive a 4-tier verdict (``auto`` / ``auto_flag`` / ``review_pending``
  / ``rejected``) using the same env-aware thresholds as ingest,
* surface a Japanese gloss + colored badge label so operators see
  the same wording across pages,
* lay out the per-factor breakdown as a list of ``FactorRow`` rows
  ready for ``st.table``.
"""

from __future__ import annotations

from dataclasses import dataclass

from eidp.extraction_confidence import (
    ConfidenceBreakdown,
    ConfidenceThresholds,
    ConfidenceVerdict,
    breakdown_from_json,
    classify,
    thresholds_from_env,
)


@dataclass(frozen=True)
class VerdictLabel:
    """UI presentation for a verdict bucket."""

    verdict: ConfidenceVerdict
    japanese: str
    color: str  # streamlit-friendly: green / blue / orange / red
    glyph: str  # short glyph for inline tags


@dataclass(frozen=True)
class FactorRow:
    """One row in the factor breakdown table."""

    factor: str
    label: str
    value: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class ConfidencePanel:
    """Everything a Streamlit page needs to render the breakdown."""

    composite: float
    verdict: ConfidenceVerdict
    label: VerdictLabel
    method: str
    factors: list[FactorRow]
    raw: ConfidenceBreakdown


_VERDICT_LABELS: dict[ConfidenceVerdict, VerdictLabel] = {
    "auto": VerdictLabel(
        verdict="auto", japanese="自動採録", color="green", glyph="●",
    ),
    "auto_flag": VerdictLabel(
        verdict="auto_flag", japanese="採録（要確認）", color="blue", glyph="◆",
    ),
    "review_pending": VerdictLabel(
        verdict="review_pending", japanese="要レビュー", color="orange", glyph="▲",
    ),
    "rejected": VerdictLabel(
        verdict="rejected", japanese="採録停止", color="red", glyph="■",
    ),
}


_FACTOR_LABELS: dict[str, str] = {
    "f1_extraction": "抽出 F1",
    "f2_completeness": "完整性 F2",
    "f3_yoy_sanity": "前年比 F3",
}


_METHOD_LABELS: dict[str, str] = {
    "pdf_parse": "PDF 直接抽出",
    "ocr_tesseract": "OCR (Tesseract)",
    "manual": "手入力",
}


def verdict_label(verdict: ConfidenceVerdict) -> VerdictLabel:
    """Return the UI presentation for ``verdict``."""
    label = _VERDICT_LABELS.get(verdict)
    if label is None:
        # Unknown verdict — surface a neutral gray badge rather than
        # crashing the page. Defensive against future verdict additions
        # that haven't been mapped yet.
        return VerdictLabel(
            verdict=verdict, japanese=str(verdict), color="gray", glyph="?",
        )
    return label


def method_label(method: str) -> str:
    """Japanese gloss for ``extraction_method``. Unknown methods pass
    through verbatim so the operator at least sees what the DB said."""
    return _METHOD_LABELS.get(method, method)


def build_panel(
    breakdown_json: str,
    *,
    thresholds: ConfidenceThresholds | None = None,
    env: dict[str, str] | None = None,
) -> ConfidencePanel:
    """Parse a confidence_breakdown JSON blob and prepare a ``ConfidencePanel``.

    Threshold resolution mirrors ingest: explicit ``thresholds`` argument
    wins, else ``thresholds_from_env(env)`` reads ``EIDP_CONFIDENCE_*``,
    else the defaults from the dataclass. UI must always agree with
    ingest on the verdict, so callers should not invent thresholds.
    """
    breakdown = breakdown_from_json(breakdown_json)
    cutoffs = thresholds or thresholds_from_env(env)
    verdict = classify(breakdown.composite, cutoffs)
    return ConfidencePanel(
        composite=breakdown.composite,
        verdict=verdict,
        label=verdict_label(verdict),
        method=breakdown.method,
        factors=_factor_rows(breakdown),
        raw=breakdown,
    )


def _factor_rows(breakdown: ConfidenceBreakdown) -> list[FactorRow]:
    """Produce a 3-row table mirroring the composite formula:

        composite = w1 * F1 + w2 * F2 + w3 * F3
    """
    pairs: list[tuple[str, float, float]] = [
        ("f1_extraction", breakdown.f1_extraction, breakdown.weights[0]),
        ("f2_completeness", breakdown.f2_completeness, breakdown.weights[1]),
        ("f3_yoy_sanity", breakdown.f3_yoy_sanity, breakdown.weights[2]),
    ]
    return [
        FactorRow(
            factor=name,
            label=_FACTOR_LABELS.get(name, name),
            value=value,
            weight=weight,
            contribution=value * weight,
        )
        for name, value, weight in pairs
    ]


def panel_to_table_rows(panel: ConfidencePanel) -> list[list[str]]:
    """Project a ``ConfidencePanel`` into a list-of-lists suitable for
    ``st.table``. Numeric fields rendered to 2 decimal places so the UI
    column widths stay stable across re-extractions."""
    header = ["項目", "値", "重み", "寄与"]
    rows: list[list[str]] = [header]
    for fr in panel.factors:
        rows.append([
            fr.label,
            f"{fr.value:.2f}",
            f"{fr.weight:.2f}",
            f"{fr.contribution:.3f}",
        ])
    rows.append(["合計", "", "", f"{panel.composite:.3f}"])
    return rows


def panel_summary_line(panel: ConfidencePanel) -> str:
    """One-line summary for the queue list (avoid expanding every row).

    Example output: ``▲ 要レビュー  composite=0.54  (PDF 直接抽出)``
    """
    return (
        f"{panel.label.glyph} {panel.label.japanese}  "
        f"composite={panel.composite:.2f}  "
        f"({method_label(panel.method)})"
    )
