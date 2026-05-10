"""Utilities for reading and summarizing discovery gold-set demonstrations."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiscoveryGoldEntry:
    """A single manual discovery demonstration."""

    entry_id: str
    target_fiscal_year: int
    outcome: str
    strict_target_year_success: bool
    site_family: str


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


def load_discovery_gold_entries(gold_set_dir: Path) -> list[DiscoveryGoldEntry]:
    """Load discovery gold-set entries from ``entries/*.json``."""

    entry_dir = gold_set_dir / "entries"
    entries: list[DiscoveryGoldEntry] = []
    for path in sorted(entry_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected_result = payload.get("expected_result", {})
        automation_pattern = payload.get("automation_pattern", {})
        entries.append(
            DiscoveryGoldEntry(
                entry_id=str(payload["entry_id"]),
                target_fiscal_year=int(payload["target_fiscal_year"]),
                outcome=str(payload["outcome"]),
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
