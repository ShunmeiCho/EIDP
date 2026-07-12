"""Run school website URL auto-discovery and persist outcomes.

The pipeline is used by both the CLI and the Linux/Web bootstrap path. It keeps
the batch bounded and uses optional Scrapling adapters so a core install can
skip cleanly when the extra is not present.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.locking import acquire_lock
from eidp.db.models import ReviewItem, School, SchoolSite
from eidp.scraper.anti_detection import CrawlThrottle
from eidp.scraper.school_url_errors import ScraplingUnavailableError
from eidp.scraper.school_url_persistence import (
    REVIEW_ITEM_TYPE,
    REVIEW_PROPOSAL_SOURCE,
    PersistenceOutcome,
    persist_discovery,
)
from eidp.scraper.school_website_crawl import PageFetcher, SchoolUrlCrawler, SerpFetcher
from eidp.scraper.scrapling_fetcher import (
    ScraplingFetchMode,
    ScraplingPageFetcher,
    SearchProviderSerpFetcher,
    scrapling_available,
)
from eidp.scraper.search_provider import create_provider

log = structlog.get_logger()


@dataclass(frozen=True)
class SchoolUrlCrawlEvidence:
    school_id: int
    school_name: str
    prefecture: str
    decision: str
    candidate_url: str
    score: float
    outcome: str
    skipped_reason: str
    queries: list[str]
    candidates: list[dict[str, object]]
    notes: list[str]
    dry_run: bool = False


SchoolUrlProgressCallback = Callable[[dict[str, int], int], None]


def run_school_url_auto_crawl(
    session: Session,
    *,
    batch_size: int = 25,
    school_id: int | None = None,
    prefecture: str | None = None,
    dry_run: bool = False,
    evidence_path: Path | None = None,
    progress_callback: SchoolUrlProgressCallback | None = None,
    serp_fetcher: SerpFetcher | None = None,
    page_fetcher: PageFetcher | None = None,
    fetch_mode: ScraplingFetchMode = "static",
) -> dict[str, int]:
    """Discover official school URLs for active schools still missing SchoolSite rows."""

    stats = {
        "attempted": 0,
        "auto_registered": 0,
        "auto_existing": 0,
        "auto_no_candidate": 0,
        "review_enqueued": 0,
        "review_existing": 0,
        "review_no_candidate": 0,
        "dry_run_auto": 0,
        "dry_run_review": 0,
        "dry_run_manual_required": 0,
        "manual_required_enqueued": 0,
        "manual_required_existing": 0,
        "rejected": 0,
        "no_candidates": 0,
        "circuit_open": 0,
        "errors": 0,
        "unavailable": 0,
    }
    bounded_batch_size = max(int(batch_size), 0)
    schools = _schools_without_url(
        session,
        bounded_batch_size,
        school_id=school_id,
        prefecture=prefecture,
    )
    if not schools:
        return stats
    if page_fetcher is None and not scrapling_available():
        stats["unavailable"] = 1
        return stats

    try:
        crawler = SchoolUrlCrawler(
            serp_fetcher=serp_fetcher or _default_serp_fetcher(),
            page_fetcher=page_fetcher or ScraplingPageFetcher(mode=fetch_mode),
            throttle=_default_crawl_throttle(),
        )
    except ScraplingUnavailableError:
        stats["unavailable"] = 1
        return stats

    evidence_writer = _EvidenceWriter(evidence_path)
    try:
        for school in schools:
            stats["attempted"] += 1
            try:
                discovery = crawler.discover_for(
                    school_id=int(school.id),
                    school_name=school.school_name,
                    prefecture=school.prefecture,
                    queries=_school_website_queries_for_school(school),
                )
                if dry_run:
                    outcome = _dry_run_outcome(discovery)
                else:
                    outcome = persist_discovery(session, discovery)
            except ScraplingUnavailableError:
                stats["attempted"] -= 1
                stats["unavailable"] = 1
                break
            except Exception as exc:
                stats["errors"] += 1
                log.warning("school_url_auto_crawl_failed", school_id=school.id, error=str(exc))
                continue

            _accumulate_outcome(stats, discovery_decision=discovery.decision, skipped_reason=outcome.skipped_reason)
            evidence_writer.write(SchoolUrlCrawlEvidence(
                school_id=int(school.id),
                school_name=school.school_name,
                prefecture=school.prefecture or "",
                decision=discovery.decision,
                candidate_url=discovery.best.candidate_url if discovery.best is not None else "",
                score=discovery.best.score if discovery.best is not None else 0.0,
                outcome=outcome.decision,
                skipped_reason=outcome.skipped_reason or "",
                queries=list(discovery.queries),
                candidates=_candidate_evidence(discovery),
                notes=list(discovery.notes),
                dry_run=dry_run,
            ))
            if progress_callback is not None:
                progress_callback(dict(stats), len(schools))
    finally:
        evidence_writer.close()

    session.flush()
    log.info("school_url_auto_crawl_complete", **stats)
    return stats


def _schools_without_url(
    session: Session,
    batch_size: int,
    *,
    school_id: int | None = None,
    prefecture: str | None = None,
) -> list[School]:
    if batch_size <= 0:
        return []
    query = (
        session.query(School)
        .outerjoin(SchoolSite, SchoolSite.school_id == School.id)
        .outerjoin(
            ReviewItem,
            (ReviewItem.reference_table == "school")
            & (ReviewItem.reference_id == School.id)
            & (ReviewItem.item_type == REVIEW_ITEM_TYPE)
            & (ReviewItem.proposal_source == REVIEW_PROPOSAL_SOURCE)
            & (ReviewItem.status == "pending"),
        )
        .filter(SchoolSite.id.is_(None))
        .filter(ReviewItem.id.is_(None))
        .filter(School.status == "active")
    )
    if school_id is not None:
        query = query.filter(School.id == school_id)
    if prefecture:
        query = query.filter(School.prefecture == prefecture)
    return query.order_by(School.prefecture.asc(), School.id.asc()).limit(batch_size).all()


def _dry_run_outcome(discovery: object) -> PersistenceOutcome:
    return PersistenceOutcome(
        school_id=int(getattr(discovery, "school_id", 0)),
        decision=str(getattr(discovery, "decision", "unknown")),
        skipped_reason="dry_run",
    )


def _default_serp_fetcher() -> SearchProviderSerpFetcher:
    api_key_map = {
        "brave": settings.brave_api_key,
        "google": settings.google_api_key,
        "serper": settings.serper_api_key,
        "duckduckgo": "",
    }
    provider = create_provider(
        provider_name=settings.search_provider,
        api_key=api_key_map.get(settings.search_provider, ""),
        google_cx=settings.google_cx,
        external_command=settings.external_search_command,
        external_timeout_seconds=settings.external_search_timeout_seconds,
    )
    return SearchProviderSerpFetcher(provider)


def _school_website_queries_for_school(school: School) -> list[str]:
    """Build official-site-first queries for SchoolSite auto-completion.

    This step wants a stable homepage or disclosure section, not a one-off
    PDF/form URL. Target-form PDF discovery starts only after a trusted
    SchoolSite entrance exists.
    """
    school_name = school.school_name.strip()
    corporation_name = (school.corporation_name or "").strip()
    school_name_variants = _school_name_query_variants(school_name)
    queries: list[str] = []
    for name_variant in school_name_variants:
        queries.extend([
            f"{name_variant} 公式サイト",
            f"{name_variant} 公式",
        ])
        if name_variant == school_name:
            queries.append(f"{name_variant} ホームページ")
        if corporation_name:
            queries.append(f"{corporation_name} {name_variant} 公式")
    queries.extend([
        f"{school_name} 情報公開",
        f"{school_name} 高等教育 修学支援",
    ])
    return _dedupe_preserve_order(queries)


def _school_name_query_variants(school_name: str) -> list[str]:
    """Return lightweight search variants for common official-name drift."""

    variants = [school_name]
    replacements = (
        ("ビューティ＆", "ビューティー＆"),
        ("ビューティ&", "ビューティー&"),
        ("＆", "&"),
        ("&", "＆"),
    )
    for source, replacement in replacements:
        if source in school_name:
            variants.append(school_name.replace(source, replacement))
    return _dedupe_preserve_order(variants)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _default_crawl_throttle() -> CrawlThrottle:
    min_jitter = max(0.0, settings.school_url_crawl_min_jitter)
    max_jitter = max(min_jitter, settings.school_url_crawl_max_jitter)
    return CrawlThrottle(
        min_seconds_per_domain=max(0.0, settings.school_url_crawl_min_seconds_per_domain),
        min_jitter=min_jitter,
        max_jitter=max_jitter,
    )


def _accumulate_outcome(
    stats: dict[str, int],
    *,
    discovery_decision: str,
    skipped_reason: str | None,
) -> None:
    if discovery_decision == "auto":
        if skipped_reason == "dry_run":
            stats["dry_run_auto"] += 1
        elif skipped_reason == "auto_without_best_candidate":
            stats["auto_no_candidate"] += 1
        elif skipped_reason:
            stats["auto_existing"] += 1
        else:
            stats["auto_registered"] += 1
    elif discovery_decision == "review":
        if skipped_reason == "dry_run":
            stats["dry_run_review"] += 1
        elif skipped_reason == "review_without_best_candidate":
            stats["review_no_candidate"] += 1
        elif skipped_reason:
            stats["review_existing"] += 1
        else:
            stats["review_enqueued"] += 1
    elif discovery_decision in {"reject", "no_candidates"}:
        if skipped_reason == "dry_run":
            stats["dry_run_manual_required"] += 1
        elif skipped_reason and "already_pending" in skipped_reason:
            stats["manual_required_existing"] += 1
        else:
            stats["manual_required_enqueued"] += 1
    elif discovery_decision == "circuit_open":
        stats["circuit_open"] += 1
    else:
        stats["rejected"] += 1


def _candidate_evidence(discovery: object) -> list[dict[str, object]]:
    candidates = getattr(discovery, "candidates", ())
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        rows.append({
            "url": str(getattr(candidate, "candidate_url", "")),
            "score": float(getattr(candidate, "score", 0.0) or 0.0),
            "decision": str(getattr(candidate, "decision", "")),
            "breakdown": dict(getattr(candidate, "breakdown", {}) or {}),
            "notes": list(getattr(candidate, "notes", ()) or ()),
        })
    return rows


class _EvidenceWriter:
    def __init__(self, path: Path | None) -> None:
        self._path = path
        if path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log.warning("school_url_evidence_prepare_failed", path=str(path), error=str(exc))
                self._path = None

    def write(self, evidence: SchoolUrlCrawlEvidence) -> None:
        if self._path is None:
            return
        lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        line = json.dumps(asdict(evidence), ensure_ascii=False, default=str) + "\n"
        try:
            with acquire_lock(lock_path, owner="school_url_evidence_writer", blocking=True, timeout=30.0):
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                    os.fsync(fh.fileno())
        except Exception as exc:  # pragma: no cover - disk full / stuck lock / permission
            log.warning("school_url_evidence_write_failed", path=str(self._path), error=str(exc))

    def close(self) -> None:
        return
