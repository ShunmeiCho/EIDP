"""Sprint 8.6.a — extraction confidence model.

Three-factor weighted composite that lets the pipeline decide whether
an extracted ``DepartmentRecord`` (or equivalent SR row) should:

* flow straight to ``current`` (auto)
* flow to ``current`` with a UI flag (auto_flag)
* be parked at ``is_current=False`` and routed to the manual queue
  (review_pending)
* be rejected entirely with the document marked ``parse_failed``
  (rejected)

Factors (per Sprint 8 v6 plan):

* **F1 extraction** — how confident the source layer is in what it
  read. ``pdf_parse`` returns a 0/0.5/1.0 quality based on whether
  required fields were located. ``ocr_tesseract`` averages the
  per-word confidence reported by Tesseract TSV. ``manual`` is always
  1.0.
* **F2 completeness** — what fraction of the required field set was
  actually populated.
* **F3 YoY sanity** — does the enrollment number fall inside a
  plausible band relative to last year. Helps catch off-by-an-order
  OCR mistakes.

Composite formula::

    composite = 0.4 * F1 + 0.4 * F2 + 0.2 * F3   clamped to [0, 1]

Thresholds default to ``0.85 / 0.70 / 0.50`` and can be overridden via
``EIDP_CONFIDENCE_AUTO`` / ``EIDP_CONFIDENCE_REVIEW`` /
``EIDP_CONFIDENCE_REJECT`` for an operator-PC-specific tuning pass.

This module is *pure logic*. It does not touch the database, does not
read settings beyond environment variables, and does not import the
ORM. ``8.6.b`` is where ``ingest.py`` consumes the API; ``8.6.c``
plugs the OCR path into F1; ``8.6.d`` surfaces the breakdown in the UI.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

#: Verdict buckets — what the pipeline should do with this row.
ConfidenceVerdict = Literal["auto", "auto_flag", "review_pending", "rejected"]

#: Fields required for a DepartmentRecord to be considered "complete".
#: Mirrors the v6 plan and ``pdf.schema.DepartmentRecord``.
DEFAULT_REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "capacity",
    "enrollment",
    "graduates",
)

#: Optional fields are tracked but do not lower F2.
DEFAULT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "course_name",
    "intl_students",
    "advanced",
    "employed",
    "other",
    "prev_enrollment",
    "dropouts",
    "dropout_rate",
    "duration_years",
    "day_or_evening",
)

#: Composite weights. Plan v6 §Confidence Architecture.
DEFAULT_WEIGHTS: tuple[float, float, float] = (0.4, 0.4, 0.2)

#: Default composite cutoffs for auto, operator-visible, and rejected rows.
DEFAULT_CONFIDENCE_AUTO = 0.85
DEFAULT_CONFIDENCE_REVIEW = 0.70
DEFAULT_CONFIDENCE_REJECT = 0.50

#: Methods that produce confidence rows.
ExtractionMethod = Literal["pdf_parse", "ocr_tesseract", "ocr_paddleocr", "ocr_pymupdf", "manual"]
ALLOWED_METHODS: frozenset[str] = frozenset({
    "pdf_parse",
    "ocr_tesseract",
    "ocr_paddleocr",
    "ocr_pymupdf",
    "manual",
})
ConfidenceRecordValue = str | int | float | None
ConfidenceRecord = Mapping[str, ConfidenceRecordValue]


@dataclass(frozen=True)
class ConfidenceThresholds:
    """Cutoffs for the four-bucket verdict. Values must satisfy
    ``0 <= reject <= review <= auto <= 1``."""

    auto: float = DEFAULT_CONFIDENCE_AUTO
    review: float = DEFAULT_CONFIDENCE_REVIEW
    reject: float = DEFAULT_CONFIDENCE_REJECT

    def __post_init__(self) -> None:
        for name in ("auto", "review", "reject"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"threshold {name}={value} not in [0, 1]")
        if not (self.reject <= self.review <= self.auto):
            raise ValueError(
                f"threshold ordering violated: reject={self.reject} "
                f"review={self.review} auto={self.auto}"
            )


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Per-row record of the three factors and the composite score.

    Serialized to ``DepartmentYearly.confidence_breakdown`` /
    ``SupportRecipient.confidence_breakdown`` (TEXT JSON in SQLite,
    JSONB in Postgres). Frozen so the value can't be mutated after
    classification.
    """

    f1_extraction: float
    f2_completeness: float
    f3_yoy_sanity: float
    method: str
    weights: tuple[float, float, float]
    composite: float


# ---------------------------------------------------------------------------
# Factor calculators
# ---------------------------------------------------------------------------


def compute_f1_pdf_parse(
    *,
    table_recognized: bool,
    required_fields_located: int,
    required_fields_total: int = len(DEFAULT_REQUIRED_FIELDS),
) -> float:
    """F1 for the pdf_parse path.

    The plan v6 picked a 3-step approximation for v1 because per-cell
    column-width matching is a v1.1 feature:

    * table structure recognized AND every required field located → 1.0
    * table recognized but at least one required field missing → 0.5
    * table structure not recognized → 0.0
    """
    if not table_recognized:
        return 0.0
    if required_fields_total <= 0:
        return 0.0
    return 1.0 if required_fields_located >= required_fields_total else 0.5


def compute_f1_ocr_tesseract(per_word_confidences: Sequence[float | int]) -> float:
    """F1 for the OCR path.

    Tesseract TSV ``conf`` is per word and ranges 0..100. Tesseract
    encodes "no recognition for this token" as -1, which we drop.
    Returns the mean of the surviving values rescaled to 0..1, or 0.0
    if no usable words remain.
    """
    if not per_word_confidences:
        return 0.0
    usable = [float(c) for c in per_word_confidences if c >= 0]
    if not usable:
        return 0.0
    return min(1.0, max(0.0, sum(usable) / len(usable) / 100.0))


def compute_f1_manual() -> float:
    """Operator-entered values are trusted at full confidence."""
    return 1.0


def compute_f2_completeness(
    record: ConfidenceRecord,
    *,
    required_fields: tuple[str, ...] = DEFAULT_REQUIRED_FIELDS,
) -> float:
    """Fraction of required fields with a non-None, non-empty value.

    A field counts as populated when its value is not None, not the
    empty string, and not zero only-when-zero-is-meaningless. We do
    *not* treat 0 as missing — capacity=0 is a real number for a
    closed course. Optional fields are not counted; they live in
    ``DEFAULT_OPTIONAL_FIELDS`` for documentation, not scoring.
    """
    if not required_fields:
        return 0.0
    populated = 0
    for field in required_fields:
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        populated += 1
    return populated / len(required_fields)


def _is_populated_value(value: ConfidenceRecordValue) -> bool:
    if value is None:
        return False
    return not (isinstance(value, str) and not value.strip())


def _numeric_or_none(value: ConfidenceRecordValue) -> float | int | None:
    return value if isinstance(value, int | float) else None


def compute_f3_yoy_sanity(
    *,
    current_enrollment: float | int | None,
    previous_enrollment: float | int | None,
    neutral_when_no_prior: float = 0.7,
) -> float:
    """F3 — does the enrollment number look sane next to last year.

    Bands per plan v6:

    * ratio in ``[0.5, 2.0]`` → 1.0
    * ratio in ``[0.3, 3.0]`` (and outside the inner band) → 0.5
    * ratio outside the outer band, or current ≤ 0 → 0.0

    When previous data is unavailable (new department, first observation,
    or operator hasn't backfilled), return ``neutral_when_no_prior``.
    Plan v6 sets that to 0.7 — neither penalize nor reward.
    """
    if previous_enrollment is None:
        return neutral_when_no_prior
    if current_enrollment is None:
        return 0.0
    if previous_enrollment <= 0:
        # Can't compute a ratio against zero or negative; treat as no prior
        # rather than a hard rejection — operator may have a legitimate
        # zero-enrollment year.
        return neutral_when_no_prior
    if current_enrollment < 0:
        return 0.0
    ratio = float(current_enrollment) / float(previous_enrollment)
    if 0.5 <= ratio <= 2.0:
        return 1.0
    if 0.3 <= ratio <= 3.0:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def compose(
    f1: float,
    f2: float,
    f3: float,
    *,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Weighted sum, clamped to ``[0, 1]``."""
    if len(weights) != 3:
        raise ValueError(f"weights must be a 3-tuple, got {weights!r}")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0, got {sum(weights)} ({weights})")
    raw = weights[0] * f1 + weights[1] * f2 + weights[2] * f3
    return max(0.0, min(1.0, raw))


def classify(composite: float, thresholds: ConfidenceThresholds | None = None) -> ConfidenceVerdict:
    """Map the composite score to one of four pipeline buckets."""
    cutoffs = thresholds or ConfidenceThresholds()
    if composite >= cutoffs.auto:
        return "auto"
    if composite >= cutoffs.review:
        return "auto_flag"
    if composite >= cutoffs.reject:
        return "review_pending"
    return "rejected"


def thresholds_from_env(env: dict[str, str] | None = None) -> ConfidenceThresholds:
    """Read ``EIDP_CONFIDENCE_*`` overrides from the environment.

    Missing or unparseable values fall back to the defaults. The
    resulting object goes through ``ConfidenceThresholds.__post_init__``
    so an out-of-order override (e.g. review > auto) raises loudly
    rather than silently corrupting verdicts.
    """
    env_map = env if env is not None else os.environ
    defaults = ConfidenceThresholds()
    return ConfidenceThresholds(
        auto=_float_or_default(env_map.get("EIDP_CONFIDENCE_AUTO"), defaults.auto),
        review=_float_or_default(env_map.get("EIDP_CONFIDENCE_REVIEW"), defaults.review),
        reject=_float_or_default(env_map.get("EIDP_CONFIDENCE_REJECT"), defaults.reject),
    )


def _float_or_default(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def build_breakdown(
    *,
    f1: float,
    f2: float,
    f3: float,
    method: ExtractionMethod | str,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> ConfidenceBreakdown:
    """Bundle the three factors plus the composite into a frozen
    record ready for serialization."""
    if method not in ALLOWED_METHODS:
        raise ValueError(f"method {method!r} not in {sorted(ALLOWED_METHODS)}")
    composite = compose(f1, f2, f3, weights=weights)
    return ConfidenceBreakdown(
        f1_extraction=f1,
        f2_completeness=f2,
        f3_yoy_sanity=f3,
        method=method,
        weights=weights,
        composite=composite,
    )


def breakdown_to_json(breakdown: ConfidenceBreakdown) -> str:
    """Serialize to JSON text for the DB ``confidence_breakdown``
    column. Stable key order so diffs over re-extraction are
    inspectable."""
    return json.dumps(
        {
            "f1_extraction": round(breakdown.f1_extraction, 4),
            "f2_completeness": round(breakdown.f2_completeness, 4),
            "f3_yoy_sanity": round(breakdown.f3_yoy_sanity, 4),
            "method": breakdown.method,
            "weights": list(breakdown.weights),
            "composite": round(breakdown.composite, 4),
        },
        ensure_ascii=False,
        sort_keys=False,
    )


def compute_pdf_parse_breakdown(
    record: ConfidenceRecord,
    *,
    prior_enrollment: float | int | None,
    required_fields: tuple[str, ...] = DEFAULT_REQUIRED_FIELDS,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    method: ExtractionMethod | str = "pdf_parse",
) -> ConfidenceBreakdown:
    """Convenience wrapper used by ingest.py for structured parser paths.

    F1 is approximated from required-field population (the v1 surrogate
    described in the plan): all 4 required → 1.0, partial → 0.5, none
    located → 0.0. F2 is the same population fraction. F3 reads the
    current-enrollment vs ``prior_enrollment``.

    Returns a frozen ``ConfidenceBreakdown`` ready for both
    ``extraction_confidence`` (composite) and the ``confidence_breakdown``
    JSON column.
    """
    populated = sum(1 for f in required_fields if _is_populated_value(record.get(f)))
    if populated == 0:
        f1 = 0.0
    elif populated >= len(required_fields):
        f1 = 1.0
    else:
        f1 = 0.5

    f2 = compute_f2_completeness(record, required_fields=required_fields)
    f3 = compute_f3_yoy_sanity(
        current_enrollment=_numeric_or_none(record.get("enrollment")),
        previous_enrollment=prior_enrollment,
    )
    return build_breakdown(f1=f1, f2=f2, f3=f3, method=method, weights=weights)


def compute_ocr_tesseract_breakdown(
    record: ConfidenceRecord,
    *,
    prior_enrollment: float | int | None,
    per_word_confidences: Sequence[float | int],
    required_fields: tuple[str, ...] = DEFAULT_REQUIRED_FIELDS,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> ConfidenceBreakdown:
    """Confidence wrapper for rows parsed from Tesseract OCR text.

    F1 comes from Tesseract's per-word TSV confidences. F2/F3 reuse the
    same completeness and YoY sanity checks as the pdf_parse path so the
    downstream classification thresholds remain identical.
    """
    f1 = compute_f1_ocr_tesseract(per_word_confidences)
    f2 = compute_f2_completeness(record, required_fields=required_fields)
    f3 = compute_f3_yoy_sanity(
        current_enrollment=_numeric_or_none(record.get("enrollment")),
        previous_enrollment=prior_enrollment,
    )
    return build_breakdown(f1=f1, f2=f2, f3=f3, method="ocr_tesseract", weights=weights)


def breakdown_from_json(blob: str) -> ConfidenceBreakdown:
    """Inverse of :func:`breakdown_to_json`. Tolerant of missing
    ``composite`` (recompute from factors) so older rows still load."""
    data = json.loads(blob)
    weights_raw = data.get("weights", list(DEFAULT_WEIGHTS))
    if len(weights_raw) != 3:
        raise ValueError(f"weights must be a 3-list, got {weights_raw!r}")
    weights = (float(weights_raw[0]), float(weights_raw[1]), float(weights_raw[2]))
    f1 = float(data["f1_extraction"])
    f2 = float(data["f2_completeness"])
    f3 = float(data["f3_yoy_sanity"])
    method = str(data.get("method", "pdf_parse"))
    composite = float(data["composite"]) if "composite" in data else compose(f1, f2, f3, weights=weights)
    return ConfidenceBreakdown(
        f1_extraction=f1,
        f2_completeness=f2,
        f3_yoy_sanity=f3,
        method=method,
        weights=weights,
        composite=composite,
    )
