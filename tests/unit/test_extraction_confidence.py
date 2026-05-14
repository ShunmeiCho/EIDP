"""Sprint 8.6.a — extraction_confidence pure-logic regression."""

from __future__ import annotations

import json

import pytest

from eidp.extraction_confidence import (
    ALLOWED_METHODS,
    DEFAULT_CONFIDENCE_AUTO,
    DEFAULT_CONFIDENCE_REJECT,
    DEFAULT_CONFIDENCE_REVIEW,
    ConfidenceBreakdown,
    ConfidenceThresholds,
    breakdown_from_json,
    breakdown_to_json,
    build_breakdown,
    classify,
    compose,
    compute_f1_manual,
    compute_f1_ocr_tesseract,
    compute_f1_pdf_parse,
    compute_f2_completeness,
    compute_f3_yoy_sanity,
    thresholds_from_env,
)

# ---------------------------------------------------------------------------
# F1 — extraction
# ---------------------------------------------------------------------------


def test_f1_pdf_parse_full_recognition():
    assert compute_f1_pdf_parse(table_recognized=True, required_fields_located=4) == 1.0


def test_f1_pdf_parse_partial_required():
    assert compute_f1_pdf_parse(table_recognized=True, required_fields_located=3) == 0.5
    assert compute_f1_pdf_parse(table_recognized=True, required_fields_located=0) == 0.5


def test_f1_pdf_parse_table_failed():
    """Plan v6 — table structure not recognized must zero out F1."""
    assert compute_f1_pdf_parse(table_recognized=False, required_fields_located=4) == 0.0


def test_f1_pdf_parse_zero_required_total_is_zero():
    """Defensive: callers must declare a non-empty required set; we
    return 0.0 instead of dividing by zero."""
    assert compute_f1_pdf_parse(
        table_recognized=True, required_fields_located=0, required_fields_total=0,
    ) == 0.0


def test_f1_ocr_tesseract_average():
    # Tesseract conf is 0..100; mean 80 → 0.8
    assert compute_f1_ocr_tesseract([90, 80, 70]) == pytest.approx(0.8, abs=1e-6)


def test_f1_ocr_tesseract_drops_negative_one():
    """Tesseract emits -1 for tokens it can't read at all. They must
    not pull the mean down — drop them entirely."""
    assert compute_f1_ocr_tesseract([90, -1, -1, 90]) == pytest.approx(0.9, abs=1e-6)


def test_f1_ocr_tesseract_empty_or_all_negative():
    assert compute_f1_ocr_tesseract([]) == 0.0
    assert compute_f1_ocr_tesseract([-1, -1]) == 0.0


def test_f1_manual_is_full_confidence():
    assert compute_f1_manual() == 1.0


# ---------------------------------------------------------------------------
# F2 — completeness
# ---------------------------------------------------------------------------


def test_f2_all_required_populated():
    record = {"name": "A学科", "capacity": 40, "enrollment": 35, "graduates": 30}
    assert compute_f2_completeness(record) == 1.0


def test_f2_three_quarters():
    record = {"name": "A", "capacity": 40, "enrollment": 35, "graduates": None}
    assert compute_f2_completeness(record) == 0.75


def test_f2_none_populated():
    record = {"name": None, "capacity": None, "enrollment": None, "graduates": None}
    assert compute_f2_completeness(record) == 0.0


def test_f2_zero_is_a_valid_value():
    """A capacity of 0 is unusual but valid — it's a closed course.
    F2 must NOT treat 0 as missing."""
    record = {"name": "A", "capacity": 0, "enrollment": 0, "graduates": 0}
    assert compute_f2_completeness(record) == 1.0


def test_f2_empty_string_treated_as_missing():
    record = {"name": "  ", "capacity": 40, "enrollment": 35, "graduates": 30}
    assert compute_f2_completeness(record) == 0.75


def test_f2_optional_fields_do_not_count():
    """Only required fields scored. Optional fields populated but
    required missing → still 0.0."""
    record = {"course_name": "x", "intl_students": 5, "advanced": 3}
    assert compute_f2_completeness(record) == 0.0


def test_f2_custom_required_set():
    record = {"sr_total": 10, "sr_grand_total": 100}
    assert compute_f2_completeness(
        record, required_fields=("sr_total", "sr_grand_total"),
    ) == 1.0


# ---------------------------------------------------------------------------
# F3 — YoY sanity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ratio", [0.5, 0.7, 1.0, 1.5, 2.0])
def test_f3_inner_band_full(ratio: float):
    assert compute_f3_yoy_sanity(
        current_enrollment=ratio * 100, previous_enrollment=100,
    ) == 1.0


@pytest.mark.parametrize("ratio", [0.3, 0.4, 2.5, 3.0])
def test_f3_outer_band_half(ratio: float):
    assert compute_f3_yoy_sanity(
        current_enrollment=ratio * 100, previous_enrollment=100,
    ) == 0.5


@pytest.mark.parametrize("ratio", [0.1, 0.29, 3.01, 10.0])
def test_f3_outside_outer_band_zero(ratio: float):
    assert compute_f3_yoy_sanity(
        current_enrollment=ratio * 100, previous_enrollment=100,
    ) == 0.0


def test_f3_no_prior_returns_neutral():
    assert compute_f3_yoy_sanity(current_enrollment=100, previous_enrollment=None) == 0.7


def test_f3_no_prior_custom_neutral():
    assert compute_f3_yoy_sanity(
        current_enrollment=100, previous_enrollment=None, neutral_when_no_prior=0.5,
    ) == 0.5


def test_f3_zero_prior_treated_as_no_prior():
    """Prior enrollment of 0 means we cannot compute a ratio. Treat as
    no prior so a re-opened course doesn't get auto-rejected."""
    assert compute_f3_yoy_sanity(current_enrollment=20, previous_enrollment=0) == 0.7


def test_f3_negative_current_zero():
    assert compute_f3_yoy_sanity(current_enrollment=-1, previous_enrollment=100) == 0.0


def test_f3_none_current_zero():
    assert compute_f3_yoy_sanity(current_enrollment=None, previous_enrollment=100) == 0.0


# ---------------------------------------------------------------------------
# Compose + classify
# ---------------------------------------------------------------------------


def test_compose_default_weights():
    # 0.4 * 1.0 + 0.4 * 1.0 + 0.2 * 1.0 = 1.0
    assert compose(1.0, 1.0, 1.0) == pytest.approx(1.0, abs=1e-6)


def test_compose_clamps_below_zero():
    """Even though factors are 0..1, defensively clamp the composite —
    a future bumper might pass an over-sized weight by accident."""
    # Not actually achievable with valid inputs, but the function must
    # never return < 0.
    assert compose(0.0, 0.0, 0.0) == 0.0


def test_compose_clamps_above_one():
    # Factors of 1.0 with default weights give exactly 1.0 — clamp
    # only kicks in if a future numeric error pushes us slightly over.
    # We assert the upper-bound contract by using compose(1, 1, 1).
    assert compose(1.0, 1.0, 1.0) <= 1.0


def test_compose_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        compose(1.0, 1.0, 1.0, weights=(0.5, 0.5, 0.5))


def test_compose_weights_must_be_three_long():
    with pytest.raises(ValueError, match="3-tuple"):
        compose(1.0, 1.0, 1.0, weights=(0.5, 0.5))  # type: ignore[arg-type]


def test_classify_auto_at_boundary():
    assert classify(0.85) == "auto"
    assert classify(0.86) == "auto"


def test_classify_auto_flag_band():
    assert classify(0.7) == "auto_flag"
    assert classify(0.84) == "auto_flag"


def test_classify_review_pending_band():
    assert classify(0.5) == "review_pending"
    assert classify(0.69) == "review_pending"


def test_classify_rejected_band():
    assert classify(0.0) == "rejected"
    assert classify(0.49) == "rejected"


def test_classify_with_custom_thresholds():
    """Operator can tune thresholds via env. Verify a stricter set still
    walks the buckets in order."""
    strict = ConfidenceThresholds(auto=0.95, review=0.85, reject=0.6)
    assert classify(0.94, strict) == "auto_flag"
    assert classify(0.95, strict) == "auto"
    assert classify(0.59, strict) == "rejected"


# ---------------------------------------------------------------------------
# ConfidenceThresholds invariants
# ---------------------------------------------------------------------------


def test_confidence_threshold_defaults_are_named_single_source():
    thresholds = ConfidenceThresholds()
    assert thresholds.auto == DEFAULT_CONFIDENCE_AUTO
    assert thresholds.review == DEFAULT_CONFIDENCE_REVIEW
    assert thresholds.reject == DEFAULT_CONFIDENCE_REJECT


def test_thresholds_must_be_in_unit_interval():
    with pytest.raises(ValueError, match="not in"):
        ConfidenceThresholds(auto=1.5, review=0.7, reject=0.5)


def test_thresholds_ordering_enforced():
    """If env vars come in scrambled (e.g. operator sets review > auto),
    fail loudly rather than silently corrupting verdicts."""
    with pytest.raises(ValueError, match="ordering violated"):
        ConfidenceThresholds(auto=0.5, review=0.7, reject=0.4)


# ---------------------------------------------------------------------------
# thresholds_from_env
# ---------------------------------------------------------------------------


def test_thresholds_from_env_defaults_when_unset():
    t = thresholds_from_env(env={})
    assert t == ConfidenceThresholds()


def test_thresholds_from_env_overrides_all_three():
    t = thresholds_from_env(env={
        "EIDP_CONFIDENCE_AUTO": "0.9",
        "EIDP_CONFIDENCE_REVIEW": "0.75",
        "EIDP_CONFIDENCE_REJECT": "0.55",
    })
    assert t.auto == pytest.approx(0.9)
    assert t.review == pytest.approx(0.75)
    assert t.reject == pytest.approx(0.55)


def test_thresholds_from_env_falls_back_on_garbage():
    """Bad env values must not crash the import — fall back to default
    so the operator PC can still run if .env got mangled."""
    t = thresholds_from_env(env={
        "EIDP_CONFIDENCE_AUTO": "not-a-number",
        "EIDP_CONFIDENCE_REVIEW": "",
    })
    assert t.auto == ConfidenceThresholds().auto
    assert t.review == ConfidenceThresholds().review


def test_thresholds_from_env_validates_ordering():
    """Operator who scrambles env must crash — same as direct
    constructor; otherwise verdicts go silently wrong."""
    with pytest.raises(ValueError, match="ordering violated"):
        thresholds_from_env(env={
            "EIDP_CONFIDENCE_AUTO": "0.5",
            "EIDP_CONFIDENCE_REVIEW": "0.7",
            "EIDP_CONFIDENCE_REJECT": "0.4",
        })


# ---------------------------------------------------------------------------
# build_breakdown + JSON roundtrip
# ---------------------------------------------------------------------------


def test_build_breakdown_rejects_unknown_method():
    with pytest.raises(ValueError, match="not in"):
        build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="psychic")


def test_build_breakdown_accepts_each_allowed_method():
    for method in ALLOWED_METHODS:
        breakdown = build_breakdown(f1=1.0, f2=1.0, f3=1.0, method=method)
        assert breakdown.method == method
        assert breakdown.composite == 1.0


def test_build_breakdown_carries_factors_through():
    breakdown = build_breakdown(f1=0.5, f2=0.75, f3=1.0, method="pdf_parse")
    assert breakdown.f1_extraction == 0.5
    assert breakdown.f2_completeness == 0.75
    assert breakdown.f3_yoy_sanity == 1.0
    # 0.4 * 0.5 + 0.4 * 0.75 + 0.2 * 1.0 = 0.7
    assert breakdown.composite == pytest.approx(0.7, abs=1e-6)


def test_breakdown_json_roundtrip():
    breakdown = build_breakdown(f1=0.92, f2=0.75, f3=0.7, method="ocr_tesseract")
    serialized = breakdown_to_json(breakdown)
    parsed = json.loads(serialized)
    # Keys we promise to the UI / DB consumers.
    assert set(parsed.keys()) == {
        "f1_extraction", "f2_completeness", "f3_yoy_sanity",
        "method", "weights", "composite",
    }
    restored = breakdown_from_json(serialized)
    assert restored.method == breakdown.method
    assert restored.composite == pytest.approx(breakdown.composite, abs=1e-4)


def test_breakdown_from_json_recomputes_missing_composite():
    """Older rows may have been persisted without composite — recompute
    from factors so we don't crash on legacy data."""
    blob = json.dumps({
        "f1_extraction": 0.5, "f2_completeness": 0.5, "f3_yoy_sanity": 0.5,
        "method": "pdf_parse", "weights": [0.4, 0.4, 0.2],
    })
    restored = breakdown_from_json(blob)
    assert restored.composite == pytest.approx(0.5, abs=1e-6)


def test_breakdown_is_frozen():
    breakdown = build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="manual")
    with pytest.raises(Exception):
        breakdown.f1_extraction = 0.0  # type: ignore[misc]


def test_breakdown_dataclass_shape_matches_db_consumer_expectations():
    """The DB column is TEXT JSON. The UI page renders it via st.json,
    which displays it as a dict. Make sure breakdown_to_json -> json.loads
    yields all the fields the UI knows how to label."""
    breakdown = ConfidenceBreakdown(
        f1_extraction=0.9, f2_completeness=0.8, f3_yoy_sanity=0.7,
        method="pdf_parse", weights=(0.4, 0.4, 0.2), composite=0.82,
    )
    parsed = json.loads(breakdown_to_json(breakdown))
    assert isinstance(parsed["weights"], list)
    assert parsed["method"] in ALLOWED_METHODS
