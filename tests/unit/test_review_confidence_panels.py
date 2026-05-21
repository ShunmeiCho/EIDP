"""Sprint 8.6.d.1 — UI helpers for confidence breakdown rendering."""

from __future__ import annotations

import json

import pytest

from eidp.extraction_confidence import (
    ConfidenceThresholds,
    breakdown_to_json,
    build_breakdown,
)
from eidp.review.confidence_panels import (
    ConfidencePanel,
    FactorRow,
    VerdictLabel,
    build_panel,
    method_label,
    panel_summary_line,
    panel_to_table_rows,
    verdict_label,
)


def _make_blob(*, f1: float, f2: float, f3: float, method: str = "pdf_parse") -> str:
    return breakdown_to_json(
        build_breakdown(f1=f1, f2=f2, f3=f3, method=method),
    )


# ---------------------------------------------------------------------------
# verdict_label
# ---------------------------------------------------------------------------


def test_verdict_label_auto():
    label = verdict_label("auto")
    assert isinstance(label, VerdictLabel)
    assert label.japanese == "自動採録"
    assert label.color == "green"


def test_verdict_label_review_pending_color():
    """Plan v6: review_pending must be a warning color so operators
    can spot rows that need them. Orange is the chosen palette."""
    assert verdict_label("review_pending").color == "orange"


def test_verdict_label_rejected_color():
    assert verdict_label("rejected").color == "red"


def test_verdict_label_unknown_falls_back_to_gray():
    """Defensive — unmapped verdicts get a gray badge instead of
    crashing the page."""
    label = verdict_label("future_bucket")  # type: ignore[arg-type]
    assert label.color == "gray"
    assert label.japanese == "future_bucket"


# ---------------------------------------------------------------------------
# method_label
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,expected", [
    ("pdf_parse", "PDF 直接抽出"),
    ("ocr_tesseract", "OCR (Tesseract)"),
    ("ocr_paddleocr", "OCR (PaddleOCR)"),
    ("ocr_pymupdf", "OCR (PyMuPDF)"),
    ("excel_import", "Excel 取込"),
    ("manual", "手入力"),
])
def test_method_label_known(method: str, expected: str):
    assert method_label(method) == expected


def test_method_label_unknown_passes_through():
    assert method_label("psychic") == "psychic"


# ---------------------------------------------------------------------------
# build_panel
# ---------------------------------------------------------------------------


def test_build_panel_auto_bucket():
    blob = _make_blob(f1=1.0, f2=1.0, f3=1.0)  # composite = 1.0
    panel = build_panel(blob)
    assert panel.verdict == "auto"
    assert panel.label.japanese == "自動採録"
    assert panel.composite == 1.0


def test_build_panel_auto_flag_bucket():
    blob = _make_blob(f1=1.0, f2=0.5, f3=0.7)
    # composite = 0.4 + 0.2 + 0.14 = 0.74 → auto_flag
    panel = build_panel(blob)
    assert panel.verdict == "auto_flag"
    assert panel.label.color == "blue"


def test_build_panel_review_pending_bucket():
    blob = _make_blob(f1=0.5, f2=0.5, f3=0.7)
    # composite = 0.2 + 0.2 + 0.14 = 0.54 → review_pending
    panel = build_panel(blob)
    assert panel.verdict == "review_pending"


def test_build_panel_rejected_bucket():
    blob = _make_blob(f1=0.0, f2=0.0, f3=0.0)
    panel = build_panel(blob)
    assert panel.verdict == "rejected"
    assert panel.label.color == "red"


def test_build_panel_factor_table_has_three_rows():
    blob = _make_blob(f1=0.92, f2=0.75, f3=0.7)
    panel = build_panel(blob)
    assert len(panel.factors) == 3
    factors_by_name = {fr.factor: fr for fr in panel.factors}
    assert set(factors_by_name) == {
        "f1_extraction", "f2_completeness", "f3_yoy_sanity",
    }


def test_build_panel_contribution_matches_value_times_weight():
    blob = _make_blob(f1=0.5, f2=0.5, f3=0.5)
    panel = build_panel(blob)
    contributions = [fr.contribution for fr in panel.factors]
    assert contributions == [pytest.approx(0.2), pytest.approx(0.2), pytest.approx(0.1)]


def test_build_panel_passes_through_method():
    blob = _make_blob(f1=1.0, f2=1.0, f3=1.0, method="ocr_tesseract")
    panel = build_panel(blob)
    assert panel.method == "ocr_tesseract"


def test_build_panel_threshold_override_via_argument():
    blob = _make_blob(f1=0.5, f2=0.5, f3=0.7)  # composite 0.54
    strict = ConfidenceThresholds(auto=0.6, review=0.55, reject=0.4)
    panel = build_panel(blob, thresholds=strict)
    # 0.54 < strict.review (0.55) but >= strict.reject (0.4) → review_pending
    assert panel.verdict == "review_pending"


def test_build_panel_threshold_via_env_consults_passed_env():
    blob = _make_blob(f1=0.5, f2=0.5, f3=0.7)  # composite 0.54
    panel = build_panel(blob, env={
        "EIDP_CONFIDENCE_AUTO": "0.95",
        "EIDP_CONFIDENCE_REVIEW": "0.40",
        "EIDP_CONFIDENCE_REJECT": "0.20",
    })
    # With review=0.40 the same composite promotes to auto_flag.
    assert panel.verdict == "auto_flag"


def test_build_panel_handles_legacy_blob_without_composite():
    """Older rows may have been written without the composite field —
    breakdown_from_json recomputes; build_panel must surface the same
    verdict as ingest."""
    blob = json.dumps({
        "f1_extraction": 1.0, "f2_completeness": 1.0, "f3_yoy_sanity": 1.0,
        "method": "pdf_parse", "weights": [0.4, 0.4, 0.2],
    })
    panel = build_panel(blob)
    assert panel.composite == pytest.approx(1.0)
    assert panel.verdict == "auto"


# ---------------------------------------------------------------------------
# panel_to_table_rows
# ---------------------------------------------------------------------------


def test_panel_to_table_rows_shape():
    blob = _make_blob(f1=0.92, f2=0.75, f3=0.7)
    panel = build_panel(blob)
    rows = panel_to_table_rows(panel)
    # header + 3 factor rows + footer
    assert len(rows) == 5
    assert rows[0] == ["項目", "値", "重み", "寄与"]
    # Footer carries composite to 3 decimals.
    assert rows[-1][0] == "合計"


def test_panel_to_table_rows_formats_two_decimals():
    blob = _make_blob(f1=1.0, f2=0.123456, f3=0.987654)
    panel = build_panel(blob)
    rows = panel_to_table_rows(panel)
    # F2 row formatted to 2 decimals
    assert rows[2][1] == "0.12"


# ---------------------------------------------------------------------------
# panel_summary_line
# ---------------------------------------------------------------------------


def test_panel_summary_line_shape():
    blob = _make_blob(f1=0.5, f2=0.5, f3=0.7, method="pdf_parse")
    panel = build_panel(blob)
    line = panel_summary_line(panel)
    assert "▲ 要レビュー" in line
    assert "composite=0.54" in line
    assert "PDF 直接抽出" in line


def test_panel_summary_line_for_ocr():
    blob = _make_blob(f1=1.0, f2=1.0, f3=1.0, method="ocr_tesseract")
    panel = build_panel(blob)
    line = panel_summary_line(panel)
    assert "OCR (Tesseract)" in line
    assert "● 自動採録" in line


# ---------------------------------------------------------------------------
# Sprint 8.6.c P2 watch: locate_tessdata exported from eidp.ocr
# ---------------------------------------------------------------------------


def test_locate_tessdata_is_exported_from_eidp_ocr():
    """Owner P2 watch: 8.6.d UI/queue should be able to do
    ``from eidp.ocr import locate_tessdata`` without going through
    the submodule. Pin the contract."""
    from eidp import ocr

    assert hasattr(ocr, "locate_tessdata")
    assert "locate_tessdata" in ocr.__all__


# ---------------------------------------------------------------------------
# Sanity: panel exposes all the dataclass fields
# ---------------------------------------------------------------------------


def test_panel_dataclass_shape():
    blob = _make_blob(f1=1.0, f2=1.0, f3=1.0)
    panel = build_panel(blob)
    assert isinstance(panel, ConfidencePanel)
    assert isinstance(panel.factors[0], FactorRow)
    assert panel.raw.method == "pdf_parse"
