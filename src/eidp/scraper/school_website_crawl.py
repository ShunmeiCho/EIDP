"""Auto-discovery of a school's official website (v104+).

Third URL-discovery channel after ``prefecture_aggregator`` (official
prefectural index) and the existing ``url_discovery`` (seed CSV /
corporation-pattern / web search). Runs when those upstream channels did
not produce a SchoolSite for an active school.

Design choices that keep this safe in a single-PC operator deployment:

* All HTTP work is delegated through Protocol-typed fetchers so tests can
  inject deterministic fakes and so we can swap Scrapling for ``httpx``
  on machines without Chromium.
* Scoring decisions go through ``url_scoring.score_school_url_candidate``
  so the same point system applies regardless of channel.
* Throttling, jitter, and per-domain cooldown are enforced by
  ``CrawlThrottle`` so a single misbehaving school site cannot get the
  operator's IP blocked from a whole CDN.
* Results are returned as a value object; the bootstrap pipeline is the
  layer that decides what to insert into ``SchoolSite`` /
  ``ReviewItem`` / ``ManualActionLog``.

Out of scope: actually loading Scrapling, registering DB rows, or
rendering UI. Those concerns live in the bootstrap step and the
persistence layer.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from eidp.scraper.anti_detection import CrawlThrottle, is_block_signal
from eidp.scraper.url_scoring import (
    UrlScore,
    UrlScoreThresholds,
    best_candidate,
    score_school_url_candidate,
    thresholds_from_env,
)

log = structlog.get_logger()


@dataclass(frozen=True)
class SerpHit:
    """One result row from a SERP-style search."""

    url: str
    title: str
    snippet: str = ""


class SerpFetcher(Protocol):
    """Looks up SERP hits for a single text query."""

    def search(self, query: str, *, max_results: int = 5) -> list[SerpHit]: ...


@dataclass(frozen=True)
class FetchedPage:
    """A successfully fetched candidate page."""

    url: str
    status_code: int
    title: str
    body_excerpt: str
    blocked: bool = False


class PageFetcher(Protocol):
    """Fetches a candidate URL and returns enough text to score it."""

    def fetch(self, url: str) -> FetchedPage | None: ...


@dataclass(frozen=True)
class SchoolUrlDiscovery:
    """Result of running the crawler for a single school."""

    school_id: int
    school_name: str
    queries: tuple[str, ...]
    candidates: tuple[UrlScore, ...]
    best: UrlScore | None
    # decision in {"auto", "review", "reject", "circuit_open", "no_candidates"}
    decision: str
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class SchoolUrlCrawler:
    """Orchestrates SERP -> page-fetch -> scoring for one school at a time."""

    serp_fetcher: SerpFetcher
    page_fetcher: PageFetcher
    throttle: CrawlThrottle
    thresholds: UrlScoreThresholds = field(default_factory=thresholds_from_env)
    max_results_per_query: int = 5
    max_pages_to_fetch: int = 3
    sleep: Callable[[float], None] = field(default=time.sleep)

    def discover_for(
        self,
        *,
        school_id: int,
        school_name: str,
        prefecture: str | None,
        queries: list[str],
    ) -> SchoolUrlDiscovery:
        """Run the SERP -> score -> fetch-for-context -> rescore loop."""
        notes: list[str] = []

        if self.throttle.is_circuit_open():
            return SchoolUrlDiscovery(
                school_id=school_id,
                school_name=school_name,
                queries=tuple(queries),
                candidates=(),
                best=None,
                decision="circuit_open",
                notes=("global_circuit_breaker",),
            )

        seen_urls: set[str] = set()
        ranked: list[UrlScore] = []

        for query in queries:
            try:
                hits = self.serp_fetcher.search(
                    query, max_results=self.max_results_per_query,
                )
            except Exception as exc:
                log.warning("serp_fetch_failed", query=query, error=str(exc))
                notes.append(f"serp_error:{type(exc).__name__}")
                continue

            for hit in hits:
                if hit.url in seen_urls:
                    continue
                seen_urls.add(hit.url)
                ranked.append(score_school_url_candidate(
                    candidate_url=hit.url,
                    school_name=school_name,
                    prefecture=prefecture,
                    page_title=hit.title,
                    page_excerpt=hit.snippet or None,
                    thresholds=self.thresholds,
                ))

        ranked.sort(key=lambda s: s.score, reverse=True)
        rescored: list[UrlScore] = []
        for cand in ranked[: self.max_pages_to_fetch]:
            if cand.decision == "reject":
                # Hard-blacklisted; do not fetch.
                continue
            throttle_decision = self.throttle.acquire(cand.candidate_url)
            if not throttle_decision.proceed:
                notes.append(f"throttle_skip:{throttle_decision.reason}")
                continue
            self.sleep(throttle_decision.wait_seconds)
            page = self._safe_fetch(cand.candidate_url)
            if page is None:
                continue
            if page.blocked or is_block_signal(
                status_code=page.status_code, body_excerpt=page.body_excerpt,
            ):
                self.throttle.record_failure(cand.candidate_url, blocked=True)
                notes.append("blocked_response")
                continue
            self.throttle.record_success(cand.candidate_url)
            rescored.append(score_school_url_candidate(
                candidate_url=page.url,
                school_name=school_name,
                prefecture=prefecture,
                page_title=page.title,
                page_excerpt=page.body_excerpt,
                thresholds=self.thresholds,
            ))

        # Combine: prefer rescored entries (richer signal), fall back to
        # SERP-only entries for candidates we could not fetch.
        rescored_urls = {s.candidate_url for s in rescored}
        combined: list[UrlScore] = list(rescored)
        for s in ranked:
            if s.candidate_url in rescored_urls:
                continue
            combined.append(s)

        if not combined:
            return SchoolUrlDiscovery(
                school_id=school_id,
                school_name=school_name,
                queries=tuple(queries),
                candidates=(),
                best=None,
                decision="no_candidates",
                notes=tuple(notes),
            )

        best = best_candidate(combined)
        decision = best.decision if best is not None else "reject"

        return SchoolUrlDiscovery(
            school_id=school_id,
            school_name=school_name,
            queries=tuple(queries),
            candidates=tuple(combined),
            best=best,
            decision=decision,
            notes=tuple(notes),
        )

    def _safe_fetch(self, url: str) -> FetchedPage | None:
        try:
            return self.page_fetcher.fetch(url)
        except Exception as exc:
            log.warning("page_fetch_failed", url=url, error=str(exc))
            self.throttle.record_failure(url)
            return None
