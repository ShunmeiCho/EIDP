"""Utilities for reading and summarizing discovery gold-set demonstrations."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError, ValidationError  # type: ignore[import-untyped]

from eidp.config import (
    MAX_SUPPORTED_TARGET_FISCAL_YEAR,
    MIN_SUPPORTED_TARGET_FISCAL_YEAR,
    SUPPORTED_TARGET_FISCAL_YEAR_RANGE_LABEL,
)
from eidp.scraper.url_normalization import normalize_candidate_url

log = structlog.get_logger()

DISCOVERY_GOLD_ALLOWED_OUTCOMES = frozenset({
    "accepted_target_pdf",
    "publication_lag_latest_public",
    "no_target_candidate_found",
    "needs_operator_review",
    "site_fetch_error",
})
DISCOVERY_GOLD_NO_TARGET_EVIDENCE_REASONS = frozenset({
    "all_negative_score",
    "classified_non_target",
    "pre_filtered_non_target_hint",
})
DISCOVERY_GOLD_TRACKED_EXTRACTOR_SOURCES = (
    "embed",
    "wordpress_download_manager",
)
DISCOVERY_GOLD_EXPERIMENTAL_EXTRACTOR_SOURCES = (
    "data_attribute",
    "form_action",
    "input_control",
    "meta_refresh",
    "onclick",
    "select_option",
)


@dataclass(frozen=True)
class DiscoveryGoldEntry:
    """A single manual discovery demonstration."""

    entry_id: str
    school_id: int
    school_name: str
    prefecture: str
    corporation_name: str
    target_fiscal_year: int
    outcome: str
    school_url: str
    disclosure_url: str
    pdf_url: str
    pdf_type: str
    fiscal_year: int | None
    strict_target_year_success: bool
    site_family: str
    pattern_type: str = ""


@dataclass(frozen=True)
class DiscoveryGoldPrediction:
    """A crawler or agent prediction for a gold-set entry."""

    entry_id: str
    outcome: str
    pdf_url: str
    fiscal_year: int | None
    strict_target_year_success: bool
    pattern_type: str = ""


@dataclass(frozen=True)
class DiscoveryGoldRunPlanItem:
    """One bounded input for a discovery gold-set PDF run."""

    entry_id: str
    school_id: int
    site_url: str
    target_fiscal_year: int
    expected_outcome: str
    expected_pdf_url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "school_id": self.school_id,
            "site_url": self.site_url,
            "target_fiscal_year": self.target_fiscal_year,
            "expected_outcome": self.expected_outcome,
            "expected_pdf_url": self.expected_pdf_url,
        }


@dataclass(frozen=True)
class DiscoveryGoldSummary:
    """Release-relevant rollup for the discovery gold set."""

    total_entries: int
    outcome_counts: dict[str, int]
    target_fiscal_year_counts: dict[int, int]
    strict_target_year_successes: int
    operator_review_entries: int
    publication_lag_entries: int
    site_families: list[str]
    pattern_type_counts: dict[str, int]
    pattern_source_counts: dict[str, int]
    undemonstrated_pattern_sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "outcome_counts": self.outcome_counts,
            "target_fiscal_year_counts": self.target_fiscal_year_counts,
            "strict_target_year_successes": self.strict_target_year_successes,
            "operator_review_entries": self.operator_review_entries,
            "publication_lag_entries": self.publication_lag_entries,
            "site_families": self.site_families,
            "pattern_type_counts": self.pattern_type_counts,
            "pattern_source_counts": self.pattern_source_counts,
            "undemonstrated_pattern_sources": self.undemonstrated_pattern_sources,
        }


@dataclass(frozen=True)
class DiscoveryGoldEvalReport:
    """Comparison between discovery predictions and gold-set expectations."""

    total_gold_entries: int
    predicted_entries: int
    exact_matches: int
    failed_predictions: int
    missing_entries: int
    unexpected_predictions: int
    failures: list[dict[str, Any]]
    missing_entry_ids: list[str]
    unexpected_entry_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_gold_entries": self.total_gold_entries,
            "predicted_entries": self.predicted_entries,
            "exact_matches": self.exact_matches,
            "failed_predictions": self.failed_predictions,
            "missing_entries": self.missing_entries,
            "unexpected_predictions": self.unexpected_predictions,
            "failures": self.failures,
            "missing_entry_ids": self.missing_entry_ids,
            "unexpected_entry_ids": self.unexpected_entry_ids,
        }


def load_discovery_gold_entries(gold_set_dir: Path) -> list[DiscoveryGoldEntry]:
    """Load discovery gold-set entries from ``entries/*.json``."""

    entry_dir = gold_set_dir / "entries"
    schema_validator = _load_discovery_gold_schema_validator(gold_set_dir)
    entries: list[DiscoveryGoldEntry] = []
    for path in sorted(entry_dir.glob("*.json")):
        payload = _load_and_validate_discovery_gold_payload(path, validator=schema_validator)
        expected_result = payload.get("expected_result", {})
        automation_pattern = payload.get("automation_pattern", {})
        fiscal_year = expected_result.get("fiscal_year")
        entries.append(
            DiscoveryGoldEntry(
                entry_id=str(payload["entry_id"]),
                school_id=int(payload["school"]["school_id"]),
                school_name=str(payload["school"]["school_name"]),
                prefecture=str(payload["school"]["prefecture"]),
                corporation_name=str(payload["school"].get("corporation_name") or ""),
                target_fiscal_year=int(payload["target_fiscal_year"]),
                outcome=str(payload["outcome"]),
                school_url=str(expected_result.get("school_url") or ""),
                disclosure_url=str(expected_result.get("disclosure_url") or ""),
                pdf_url=str(expected_result.get("pdf_url") or ""),
                pdf_type=str(expected_result.get("pdf_type") or ""),
                fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
                strict_target_year_success=bool(expected_result.get("strict_target_year_success", False)),
                site_family=str(automation_pattern.get("site_family") or ""),
                pattern_type=str(expected_result.get("pattern_type") or ""),
            )
        )
    return entries


def _load_discovery_gold_schema_validator(gold_set_dir: Path) -> Any:
    schema_path = gold_set_dir / "schema.json"
    schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema_payload, dict):
        raise ValueError(f"{schema_path}: discovery gold-set schema must be a JSON object")
    schema = cast(dict[str, Any], schema_payload)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"{schema_path}: invalid discovery gold-set JSON schema: {exc.message}") from exc
    return Draft202012Validator(schema)


def _load_and_validate_discovery_gold_payload(
    path: Path,
    *,
    validator: Any,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: discovery gold-set entry must be a JSON object")
    entry = cast(dict[str, Any], payload)
    try:
        validator.validate(entry)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValueError(
            f"{path}: discovery gold-set schema validation failed at {location}: {exc.message}"
        ) from exc
    return entry


def seed_discovery_gold_sites(
    session: Any,
    entries: list[DiscoveryGoldEntry],
    *,
    apply: bool,
    safe_url_checker: Callable[[str], bool] | None = None,
) -> dict[str, int | bool]:
    """Seed gold-set schools and disclosure sites into a DB session."""

    from eidp.db.models import School, SchoolSite
    from eidp.scraper.url_discovery import _is_safe_url

    validation_errors = validate_discovery_gold_entries(entries)
    if validation_errors:
        preview = "; ".join(validation_errors[:5])
        if len(validation_errors) > 5:
            preview += f"; ... ({len(validation_errors)} total)"
        raise ValueError(f"invalid discovery gold-set entries: {preview}")

    checker = safe_url_checker or _is_safe_url
    stats: dict[str, int | bool] = {
        "applied": apply,
        "schools_to_create": 0,
        "sites_to_add": 0,
        "sites_existing": 0,
        "invalid_site_urls": 0,
    }
    for entry in entries:
        site_url = _canonical_seed_site_url(entry.disclosure_url or entry.school_url)
        if not site_url or not checker(site_url):
            stats["invalid_site_urls"] = int(stats["invalid_site_urls"]) + 1
            log.warning(
                "discovery_gold_seed_site_url_rejected",
                entry_id=entry.entry_id,
                school_id=entry.school_id,
                url=site_url,
            )
            continue

        school = session.get(School, entry.school_id)
        if school is None:
            stats["schools_to_create"] = int(stats["schools_to_create"]) + 1
            if apply:
                session.add(
                    School(
                        id=entry.school_id,
                        prefecture=entry.prefecture,
                        corporation_name=entry.corporation_name,
                        school_name=entry.school_name,
                        school_type="専門学校",
                        status="active",
                    )
                )

        if _school_site_exists(session, school_id=entry.school_id, url=site_url):
            stats["sites_existing"] = int(stats["sites_existing"]) + 1
            continue

        stats["sites_to_add"] = int(stats["sites_to_add"]) + 1
        if apply:
            session.add(
                SchoolSite(
                    school_id=entry.school_id,
                    url=site_url,
                    url_type="disclosure",
                    discovery_method="discovery_gold_set",
                    confidence=0.99,
                    verified=True,
                    http_status=200,
                )
            )
    return stats


def _canonical_seed_site_url(url: str) -> str:
    """Normalize seed URLs without changing directory URLs used as crawl entrypoints."""

    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    base = normalize_candidate_url(url)
    if not parsed.path.endswith("/") or parsed.path == "/":
        return base

    base_parsed = urlparse(base)
    path = base_parsed.path
    if path and not path.endswith("/"):
        path = f"{path}/"
    query_pairs = parse_qsl(base_parsed.query, keep_blank_values=True)
    query = urlencode(query_pairs, doseq=True)
    return urlunparse((base_parsed.scheme, base_parsed.netloc, path, "", query, ""))


def build_discovery_gold_run_plan(entries: list[DiscoveryGoldEntry]) -> list[DiscoveryGoldRunPlanItem]:
    """Build bounded PDF discovery run inputs from the gold set."""

    plan: list[DiscoveryGoldRunPlanItem] = []
    for entry in entries:
        site_url = entry.disclosure_url or entry.school_url
        plan.append(
            DiscoveryGoldRunPlanItem(
                entry_id=entry.entry_id,
                school_id=entry.school_id,
                site_url=site_url,
                target_fiscal_year=entry.target_fiscal_year,
                expected_outcome=entry.outcome,
                expected_pdf_url=entry.pdf_url,
            )
        )
    return plan


def build_discovery_gold_expected_predictions(
    entries: list[DiscoveryGoldEntry],
) -> list[DiscoveryGoldPrediction]:
    """Build the canonical expected-predictions fixture from gold entries."""

    return [
        DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome=entry.outcome,
            pdf_url=entry.pdf_url,
            fiscal_year=entry.fiscal_year,
            strict_target_year_success=entry.strict_target_year_success,
            pattern_type=entry.pattern_type,
        )
        for entry in entries
    ]


def summarize_discovery_gold_entries(entries: list[DiscoveryGoldEntry]) -> DiscoveryGoldSummary:
    """Summarize the gold set in buckets used by discovery release gates."""

    outcome_counts = Counter(entry.outcome for entry in entries)
    target_year_counts = Counter(entry.target_fiscal_year for entry in entries)
    site_families = sorted({entry.site_family for entry in entries if entry.site_family})
    pattern_type_counts = Counter(entry.pattern_type for entry in entries if entry.pattern_type)
    pattern_source_counts = Counter(
        source
        for entry in entries
        if entry.pattern_type
        for source in [_pattern_source(entry.pattern_type)]
        if source
    )
    return DiscoveryGoldSummary(
        total_entries=len(entries),
        outcome_counts=dict(sorted(outcome_counts.items())),
        target_fiscal_year_counts=dict(sorted(target_year_counts.items())),
        strict_target_year_successes=sum(1 for entry in entries if entry.strict_target_year_success),
        operator_review_entries=outcome_counts.get("needs_operator_review", 0),
        publication_lag_entries=outcome_counts.get("publication_lag_latest_public", 0),
        site_families=site_families,
        pattern_type_counts=dict(sorted(pattern_type_counts.items())),
        pattern_source_counts=dict(sorted(pattern_source_counts.items())),
        undemonstrated_pattern_sources=[
            source
            for source in DISCOVERY_GOLD_TRACKED_EXTRACTOR_SOURCES
            if source not in pattern_source_counts
        ],
    )


def validate_discovery_gold_entries(entries: list[DiscoveryGoldEntry]) -> list[str]:
    """Return semantic validation errors for committed discovery demonstrations."""

    errors: list[str] = []
    seen_entry_ids: set[str] = set()
    seen_school_years: set[tuple[int, int]] = set()

    for entry in entries:
        prefix = f"{entry.entry_id}: "
        if entry.entry_id in seen_entry_ids:
            errors.append(prefix + "duplicate entry_id")
        seen_entry_ids.add(entry.entry_id)

        school_year = (entry.school_id, entry.target_fiscal_year)
        if school_year in seen_school_years:
            errors.append(prefix + "duplicate school_id + target_fiscal_year")
        seen_school_years.add(school_year)

        if (
            entry.target_fiscal_year < MIN_SUPPORTED_TARGET_FISCAL_YEAR
            or entry.target_fiscal_year > MAX_SUPPORTED_TARGET_FISCAL_YEAR
        ):
            errors.append(
                prefix + f"target_fiscal_year outside supported range {SUPPORTED_TARGET_FISCAL_YEAR_RANGE_LABEL}"
            )
        if entry.outcome not in DISCOVERY_GOLD_ALLOWED_OUTCOMES:
            errors.append(prefix + f"unsupported outcome {entry.outcome!r}")
        site_url = entry.disclosure_url or entry.school_url
        if not site_url:
            errors.append(prefix + "expected_result.school_url or expected_result.disclosure_url is required")
        elif not _is_absolute_http_url(site_url):
            errors.append(prefix + "seed site URL must be an absolute http(s) URL")
        if entry.pdf_url and not _is_absolute_http_url(entry.pdf_url):
            errors.append(prefix + "expected_result.pdf_url must be an absolute http(s) URL")

        if entry.outcome == "accepted_target_pdf":
            if not entry.pdf_url:
                errors.append(prefix + "accepted_target_pdf requires expected_result.pdf_url")
            if entry.pdf_type != "target":
                errors.append(prefix + "accepted_target_pdf requires expected_result.pdf_type=target")
            if entry.fiscal_year != entry.target_fiscal_year:
                errors.append(prefix + "accepted_target_pdf fiscal_year must equal target_fiscal_year")
            if not entry.strict_target_year_success:
                errors.append(prefix + "accepted_target_pdf requires strict_target_year_success=true")
        elif entry.outcome == "publication_lag_latest_public":
            if not entry.pdf_url:
                errors.append(prefix + "publication_lag_latest_public requires expected_result.pdf_url")
            if entry.pdf_type != "target":
                errors.append(prefix + "publication_lag_latest_public requires expected_result.pdf_type=target")
            if entry.fiscal_year is None or entry.fiscal_year >= entry.target_fiscal_year:
                errors.append(
                    prefix + "publication_lag_latest_public fiscal_year must be older than target_fiscal_year"
                )
            if entry.strict_target_year_success:
                errors.append(prefix + "publication_lag_latest_public requires strict_target_year_success=false")
        elif entry.outcome == "needs_operator_review":
            if entry.strict_target_year_success:
                errors.append(prefix + "needs_operator_review requires strict_target_year_success=false")
        elif entry.outcome in {"no_target_candidate_found", "site_fetch_error"}:
            if entry.pdf_url:
                errors.append(prefix + f"{entry.outcome} must not carry expected_result.pdf_url")
            if entry.fiscal_year is not None:
                errors.append(prefix + f"{entry.outcome} must not carry expected_result.fiscal_year")
            if entry.strict_target_year_success:
                errors.append(prefix + f"{entry.outcome} requires strict_target_year_success=false")

    return errors


def render_discovery_gold_summary(summary: DiscoveryGoldSummary) -> str:
    """Render a deterministic JSON payload for CLI and audit logs."""

    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def render_discovery_gold_run_plan(plan: list[DiscoveryGoldRunPlanItem]) -> str:
    """Render bounded run-plan inputs as deterministic JSON."""

    return json.dumps([item.to_dict() for item in plan], ensure_ascii=False, indent=2, sort_keys=True)


def render_discovery_gold_predictions(predictions: list[DiscoveryGoldPrediction]) -> str:
    """Render discovery predictions as deterministic JSONL."""

    lines = []
    for prediction in predictions:
        payload: dict[str, Any] = {
            "entry_id": prediction.entry_id,
            "outcome": prediction.outcome,
            "pdf_url": prediction.pdf_url,
            "fiscal_year": prediction.fiscal_year,
            "strict_target_year_success": prediction.strict_target_year_success,
        }
        if prediction.pattern_type:
            payload["pattern_type"] = prediction.pattern_type
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def load_discovery_gold_predictions(predictions_path: Path) -> list[DiscoveryGoldPrediction]:
    """Load JSONL predictions emitted by a crawler or agent."""

    predictions: list[DiscoveryGoldPrediction] = []
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        fiscal_year = payload.get("fiscal_year")
        predictions.append(
            DiscoveryGoldPrediction(
                entry_id=str(payload["entry_id"]),
                outcome=str(payload["outcome"]),
                pdf_url=str(payload.get("pdf_url") or ""),
                fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
                strict_target_year_success=bool(payload.get("strict_target_year_success", False)),
                pattern_type=str(payload.get("pattern_type") or ""),
            )
        )
    return predictions


def load_discovery_gold_predictions_from_pdf_evidence(
    evidence_path: Path,
    entries: list[DiscoveryGoldEntry],
) -> list[DiscoveryGoldPrediction]:
    """Convert existing discover-pdfs evidence JSONL into gold-set predictions."""

    entries_by_key = {
        (entry.school_id, entry.target_fiscal_year): entry
        for entry in entries
    }
    school_id_counts = Counter(entry.school_id for entry in entries)
    entries_by_school_id = {
        entry.school_id: entry
        for entry in entries
        if school_id_counts[entry.school_id] == 1
    }
    predictions_by_entry_id: dict[str, tuple[int, DiscoveryGoldPrediction]] = {}

    for line_number, line in enumerate(evidence_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            log.warning(
                "discovery_gold_pdf_evidence_jsonl_skipped",
                path=str(evidence_path),
                line_number=line_number,
                error=str(exc),
            )
            continue
        school_id = _int_or_none(payload.get("school_id"))
        if school_id is None:
            continue
        target_fiscal_year = _target_fiscal_year_from_evidence_payload(payload)
        entry = (
            entries_by_key.get((school_id, target_fiscal_year))
            if target_fiscal_year is not None
            else entries_by_school_id.get(school_id)
        )
        if entry is None:
            continue

        prediction = _prediction_from_pdf_evidence_payload(entry, payload)
        if prediction is None:
            continue
        priority = _prediction_priority(prediction.outcome)
        current = predictions_by_entry_id.get(prediction.entry_id)
        if current is None or priority > current[0] or (
            priority == current[0] and _is_better_tie_break_prediction(prediction, current[1])
        ):
            predictions_by_entry_id[prediction.entry_id] = (priority, prediction)

    return [item[1] for item in sorted(predictions_by_entry_id.values(), key=lambda item: item[1].entry_id)]


def evaluate_discovery_gold_predictions(
    entries: list[DiscoveryGoldEntry],
    predictions: list[DiscoveryGoldPrediction],
) -> DiscoveryGoldEvalReport:
    """Compare crawler predictions against discovery gold-set expectations."""

    entries_by_id = {entry.entry_id: entry for entry in entries}
    predicted_ids = {prediction.entry_id for prediction in predictions}
    failures: list[dict[str, Any]] = []
    unexpected_entry_ids: list[str] = []
    exact_matches = 0

    for prediction in predictions:
        expected = entries_by_id.get(prediction.entry_id)
        if expected is None:
            unexpected_entry_ids.append(prediction.entry_id)
            continue

        reasons: list[str] = []
        if prediction.outcome != expected.outcome:
            reasons.append("outcome_mismatch")
        if normalize_candidate_url(prediction.pdf_url) != normalize_candidate_url(expected.pdf_url):
            reasons.append("pdf_url_mismatch")
        if prediction.fiscal_year != expected.fiscal_year:
            reasons.append("fiscal_year_mismatch")
        if prediction.strict_target_year_success != expected.strict_target_year_success:
            reasons.append("strict_target_year_success_mismatch")
        if expected.pattern_type and prediction.pattern_type != expected.pattern_type:
            reasons.append("pattern_type_mismatch")

        if reasons:
            failures.append({"entry_id": prediction.entry_id, "reasons": reasons})
        else:
            exact_matches += 1

    missing_entry_ids = sorted(set(entries_by_id) - predicted_ids)
    unexpected_entry_ids.sort()
    return DiscoveryGoldEvalReport(
        total_gold_entries=len(entries),
        predicted_entries=len(predictions),
        exact_matches=exact_matches,
        failed_predictions=len(failures),
        missing_entries=len(missing_entry_ids),
        unexpected_predictions=len(unexpected_entry_ids),
        failures=failures,
        missing_entry_ids=missing_entry_ids,
        unexpected_entry_ids=unexpected_entry_ids,
    )


def render_discovery_gold_eval_report(report: DiscoveryGoldEvalReport) -> str:
    """Render a deterministic JSON evaluation report."""

    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def _prediction_from_pdf_evidence_payload(
    entry: DiscoveryGoldEntry,
    payload: dict[str, Any],
) -> DiscoveryGoldPrediction | None:
    reason = str(payload.get("reason") or "")
    pdf_url = str(payload.get("pdf_url") or "")
    if reason == "accepted_downloaded":
        raw_extra = payload.get("extra")
        extra: dict[str, Any] = raw_extra if isinstance(raw_extra, dict) else {}
        fiscal_year = _int_or_none(extra.get("detected_fiscal_year")) or _int_or_none(extra.get("target_fiscal_year"))
        return DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome="accepted_target_pdf",
            pdf_url=pdf_url,
            fiscal_year=fiscal_year,
            strict_target_year_success=True,
            pattern_type=str(payload.get("pattern_type") or ""),
        )

    if reason.startswith("fiscal_year_mismatch:"):
        fiscal_year = _int_or_none(reason.split(":", 1)[1])
        if str(payload.get("pdf_type") or "") == "image_only":
            return DiscoveryGoldPrediction(
                entry_id=entry.entry_id,
                outcome="needs_operator_review",
                pdf_url=pdf_url,
                fiscal_year=fiscal_year,
                strict_target_year_success=False,
                pattern_type=str(payload.get("pattern_type") or ""),
            )
        return DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome="publication_lag_latest_public",
            pdf_url=pdf_url,
            fiscal_year=fiscal_year,
            strict_target_year_success=False,
            pattern_type=str(payload.get("pattern_type") or ""),
        )

    if reason == "target_fiscal_year_not_detected":
        return DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome="needs_operator_review",
            pdf_url=pdf_url,
            fiscal_year=None,
            strict_target_year_success=False,
            pattern_type=str(payload.get("pattern_type") or ""),
        )

    if reason == "no_candidates_found" or reason in DISCOVERY_GOLD_NO_TARGET_EVIDENCE_REASONS:
        return DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome="no_target_candidate_found",
            pdf_url="",
            fiscal_year=None,
            strict_target_year_success=False,
            pattern_type="",
        )

    if reason in {"discovery_error"} or reason.startswith("http_error:"):
        return DiscoveryGoldPrediction(
            entry_id=entry.entry_id,
            outcome="site_fetch_error",
            pdf_url="",
            fiscal_year=None,
            strict_target_year_success=False,
            pattern_type="",
        )

    return None


def _prediction_priority(outcome: str) -> int:
    return {
        "accepted_target_pdf": 5,
        "publication_lag_latest_public": 4,
        "needs_operator_review": 3,
        "site_fetch_error": 2,
        "no_target_candidate_found": 1,
    }.get(outcome, 0)


def _is_better_tie_break_prediction(candidate: DiscoveryGoldPrediction, current: DiscoveryGoldPrediction) -> bool:
    """Return whether a same-priority prediction is the more useful replay result."""

    if candidate.outcome == current.outcome == "publication_lag_latest_public":
        return (candidate.fiscal_year or 0) > (current.fiscal_year or 0)
    return False


def _pattern_source(pattern_type: str) -> str:
    if pattern_type == "wordpress_download_manager":
        return pattern_type
    for suffix in ("_cache_busted", "_direct", "_wordpress"):
        if pattern_type.endswith(suffix):
            return pattern_type.removesuffix(suffix)
    return pattern_type


def _is_absolute_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _target_fiscal_year_from_evidence_payload(payload: dict[str, Any]) -> int | None:
    raw_extra = payload.get("extra")
    extra: dict[str, Any] = raw_extra if isinstance(raw_extra, dict) else {}
    return _int_or_none(extra.get("target_fiscal_year"))


def _school_site_exists(session: Any, *, school_id: int, url: str) -> bool:
    from eidp.db.models import SchoolSite

    rows = session.query(SchoolSite).filter(SchoolSite.school_id == school_id).all()
    normalized_url = normalize_candidate_url(url)
    return any(normalize_candidate_url(str(row.url)) == normalized_url for row in rows)
