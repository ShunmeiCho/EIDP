"""Anti-detection helpers for school-website crawling (v104+).

Layered defenses so the operator's single Windows PC does not look like
an aggressive bot to school websites or to public SERP endpoints.

Layers
------
1. Per-domain throttle: the same domain is hit at most once every
   ``min_seconds_per_domain`` seconds even when other domains run in parallel.
2. Random jitter: each request is preceded by a random wait between
   ``min_jitter`` and ``max_jitter`` seconds so we do not produce a perfect
   timer pattern.
3. Cooldown on repeated failure: after ``failure_threshold`` consecutive
   429/503/Cloudflare-block responses, the domain is parked for
   ``cooldown_seconds`` and is reported back to the caller as a quarantine
   signal.
4. Global circuit breaker: if more than ``max_quarantined_domains`` distinct
   domains land in quarantine the whole crawl aborts, so a network-wide
   incident does not turn into a multi-hour pointless retry storm.

This module is pure logic: it does not perform any network IO so it stays
testable without monkey-patching httpx or Scrapling.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final
from urllib.parse import urlparse

DEFAULT_MIN_SECONDS_PER_DOMAIN: Final = 30.0
DEFAULT_MIN_JITTER: Final = 2.0
DEFAULT_MAX_JITTER: Final = 5.0
DEFAULT_FAILURE_THRESHOLD: Final = 3
DEFAULT_COOLDOWN_SECONDS: Final = 3600.0
DEFAULT_MAX_QUARANTINED_DOMAINS: Final = 5


def domain_of(url: str) -> str:
    """Return the lowercased registered hostname for a URL, or '' if unparseable."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    return host


@dataclass(frozen=True)
class ThrottleDecision:
    """Outcome of consulting the throttle before a request."""

    proceed: bool
    wait_seconds: float
    reason: str


@dataclass
class _DomainState:
    last_request_at: float = 0.0
    consecutive_failures: int = 0
    quarantined_until: float = 0.0


@dataclass
class CrawlThrottle:
    """Thread-safe per-domain throttle + global circuit breaker.

    Caller pattern::

        decision = throttle.acquire(url)
        if not decision.proceed:
            log.info("throttle_skip", url=url, reason=decision.reason)
            continue
        time.sleep(decision.wait_seconds)
        try:
            resp = fetch(url)
        except BlockedError:
            throttle.record_failure(url, blocked=True)
            continue
        throttle.record_success(url)
    """

    min_seconds_per_domain: float = DEFAULT_MIN_SECONDS_PER_DOMAIN
    min_jitter: float = DEFAULT_MIN_JITTER
    max_jitter: float = DEFAULT_MAX_JITTER
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS
    max_quarantined_domains: int = DEFAULT_MAX_QUARANTINED_DOMAINS

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _state: dict[str, _DomainState] = field(default_factory=dict, repr=False)
    _quarantined: set[str] = field(default_factory=set, repr=False)
    _now: Callable[[], float] = field(default=time.monotonic, repr=False)
    _rand: Callable[[float, float], float] = field(default=random.uniform, repr=False)

    def __post_init__(self) -> None:
        if self.min_jitter > self.max_jitter:
            raise ValueError("min_jitter must be <= max_jitter")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")

    def acquire(self, url: str) -> ThrottleDecision:
        """Check whether a request to ``url`` is currently allowed.

        Returns a decision with ``wait_seconds`` the caller MUST sleep for
        before issuing the request, and ``proceed=False`` when the domain is
        in cooldown or the global circuit breaker has tripped.
        """
        host = domain_of(url)
        if not host:
            return ThrottleDecision(False, 0.0, "invalid_url")
        now = self._now()
        with self._lock:
            self._prune_expired_quarantines(now)
            if len(self._quarantined) >= self.max_quarantined_domains:
                return ThrottleDecision(False, 0.0, "global_circuit_breaker")
            state = self._state.setdefault(host, _DomainState())
            if state.quarantined_until > now:
                remaining = state.quarantined_until - now
                return ThrottleDecision(
                    False, remaining, f"domain_cooldown:{int(remaining)}s",
                )
            since_last = now - state.last_request_at
            wait = max(0.0, self.min_seconds_per_domain - since_last)
        jitter = self._rand(self.min_jitter, self.max_jitter)
        return ThrottleDecision(True, wait + jitter, "ok")

    def record_success(self, url: str) -> None:
        host = domain_of(url)
        if not host:
            return
        now = self._now()
        with self._lock:
            state = self._state.setdefault(host, _DomainState())
            state.last_request_at = now
            state.consecutive_failures = 0
            state.quarantined_until = 0.0
            self._quarantined.discard(host)

    def record_failure(self, url: str, *, blocked: bool = False) -> str | None:
        """Record a failure. Returns the quarantine reason when this call
        triggers a cooldown, otherwise ``None``.

        ``blocked=True`` indicates a hard block signal (HTTP 429/503,
        Cloudflare interstitial, captcha challenge) which immediately
        quarantines the domain regardless of failure count.
        """
        host = domain_of(url)
        if not host:
            return None
        now = self._now()
        with self._lock:
            state = self._state.setdefault(host, _DomainState())
            state.last_request_at = now
            state.consecutive_failures += 1
            if blocked or state.consecutive_failures >= self.failure_threshold:
                state.quarantined_until = now + self.cooldown_seconds
                self._quarantined.add(host)
                return "blocked" if blocked else "failure_threshold"
        return None

    def quarantined_domains(self) -> tuple[str, ...]:
        with self._lock:
            self._prune_expired_quarantines(self._now())
            return tuple(sorted(self._quarantined))

    def is_circuit_open(self) -> bool:
        with self._lock:
            self._prune_expired_quarantines(self._now())
            return len(self._quarantined) >= self.max_quarantined_domains

    def _prune_expired_quarantines(self, now: float) -> None:
        """Drop cooldown entries whose deadline has passed.

        Must be called with ``_lock`` held. Without this cleanup the global
        circuit breaker never reopens after cooldown expiry.
        """
        for host in tuple(self._quarantined):
            state = self._state.get(host)
            if state is None or state.quarantined_until <= now:
                self._quarantined.discard(host)
                if state is not None:
                    state.quarantined_until = 0.0
                    state.consecutive_failures = 0


def stealthy_request_headers(
    *, accept_language: str = "ja-JP,ja;q=0.9,en-US;q=0.5",
) -> dict[str, str]:
    """Return browser-like default headers for static httpx requests.

    Used for the small number of fetches where we do not want to spin up
    Scrapling's Chromium engine but still want to look like a real browser.
    """
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }


_BLOCK_BODY_MARKERS: Final = (
    "cf-chl-bypass",
    "cf-ray",
    "checking your browser",
    "access denied",
    "you have been blocked",
    "captcha",
    "perimeterx",
    "imperva incapsula",
)


def is_block_signal(*, status_code: int | None, body_excerpt: str | None) -> bool:
    """Detect HTTP block / Cloudflare interstitial signals from a response.

    The body excerpt should be the first ~2KB of the response body. Cloudflare,
    Akamai, and similar CDNs all expose recognisable strings when they serve
    a challenge page rather than the requested content.
    """
    if status_code in {403, 418, 429, 503}:
        return True
    if not body_excerpt:
        return False
    excerpt = body_excerpt.lower()
    return any(marker in excerpt for marker in _BLOCK_BODY_MARKERS)
