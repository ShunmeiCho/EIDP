"""Utilities for reading and summarizing discovery gold-set demonstrations."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eidp.scraper.url_normalization import normalize_candidate_url


@dataclass(frozen=True)
class DiscoveryGoldEntry:
    """A single manual discovery demonstration."""

    entry_id: str
    target_fiscal_year: int
    outcome: str
    pdf_url: str
    fiscal_year: int | None
    strict_target_year_success: bool
    site_family: str


@dataclass(frozen=True)
class DiscoveryGoldPrediction:
    """A crawler or agent prediction for a gold-set entry."""

    entry_id: str
    outcome: str
    pdf_url: str
    fiscal_year: int | None
    strict_target_year_success: bool


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "outcome_counts": self.outcome_counts,
            "target_fiscal_year_counts": self.target_fiscal_year_counts,
            "strict_target_year_successes": self.strict_target_year_successes,
            "operator_review_entries": self.operator_review_entries,
            "publication_lag_entries": self.publication_lag_entries,
            "site_families": self.site_families,
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
    entries: list[DiscoveryGoldEntry] = []
    for path in sorted(entry_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected_result = payload.get("expected_result", {})
        automation_pattern = payload.get("automation_pattern", {})
        fiscal_year = expected_result.get("fiscal_year")
        entries.append(
            DiscoveryGoldEntry(
                entry_id=str(payload["entry_id"]),
                target_fiscal_year=int(payload["target_fiscal_year"]),
                outcome=str(payload["outcome"]),
                pdf_url=str(expected_result.get("pdf_url") or ""),
                fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
                strict_target_year_success=bool(expected_result.get("strict_target_year_success", False)),
                site_family=str(automation_pattern.get("site_family") or ""),
            )
        )
    return entries


def summarize_discovery_gold_entries(entries: list[DiscoveryGoldEntry]) -> DiscoveryGoldSummary:
    """Summarize the gold set in buckets used by discovery release gates."""

    outcome_counts = Counter(entry.outcome for entry in entries)
    target_year_counts = Counter(entry.target_fiscal_year for entry in entries)
    site_families = sorted({entry.site_family for entry in entries if entry.site_family})
    return DiscoveryGoldSummary(
        total_entries=len(entries),
        outcome_counts=dict(sorted(outcome_counts.items())),
        target_fiscal_year_counts=dict(sorted(target_year_counts.items())),
        strict_target_year_successes=sum(1 for entry in entries if entry.strict_target_year_success),
        operator_review_entries=outcome_counts.get("needs_operator_review", 0),
        publication_lag_entries=outcome_counts.get("publication_lag_latest_public", 0),
        site_families=site_families,
    )


def render_discovery_gold_summary(summary: DiscoveryGoldSummary) -> str:
    """Render a deterministic JSON payload for CLI and audit logs."""

    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


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
            )
        )
    return predictions


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
