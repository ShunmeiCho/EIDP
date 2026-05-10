"""Tests for src/eidp/scraper/anti_detection.py."""

from __future__ import annotations

import pytest

from eidp.scraper.anti_detection import (
    CrawlThrottle,
    ThrottleDecision,
    domain_of,
    is_block_signal,
    stealthy_request_headers,
)


class _ManualClock:
    """Deterministic monotonic-clock substitute for throttle tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _make_throttle(
    *,
    clock: _ManualClock | None = None,
    min_seconds_per_domain: float = 30.0,
    failure_threshold: int = 3,
    cooldown_seconds: float = 60.0,
    max_quarantined_domains: int = 5,
    jitter: float = 0.0,
) -> CrawlThrottle:
    clock = clock or _ManualClock()
    return CrawlThrottle(
        min_seconds_per_domain=min_seconds_per_domain,
        min_jitter=jitter,
        max_jitter=jitter,
        failure_threshold=failure_threshold,
        cooldown_seconds=cooldown_seconds,
        max_quarantined_domains=max_quarantined_domains,
        _now=clock,
        _rand=lambda _lo, _hi: jitter,
    )


def test_domain_of_returns_lowercased_hostname():
    assert domain_of("https://Example.AC.JP/path") == "example.ac.jp"


def test_domain_of_handles_invalid_input():
    assert domain_of("not a url") == ""
    assert domain_of("") == ""


def test_first_request_to_domain_is_allowed_with_only_jitter():
    clock = _ManualClock()
    throttle = _make_throttle(clock=clock, jitter=2.5)
    decision = throttle.acquire("https://a.example.ac.jp/info")
    assert decision.proceed is True
    assert decision.reason == "ok"
    assert decision.wait_seconds == pytest.approx(2.5)


def test_second_request_to_same_domain_waits_for_min_interval():
    clock = _ManualClock()
    throttle = _make_throttle(clock=clock, min_seconds_per_domain=30.0, jitter=1.0)
    throttle.acquire("https://a.example.ac.jp/page1")
    throttle.record_success("https://a.example.ac.jp/page1")
    clock.advance(10.0)
    decision = throttle.acquire("https://a.example.ac.jp/page2")
    assert decision.proceed is True
    assert decision.wait_seconds == pytest.approx(21.0)


def test_invalid_url_is_refused():
    throttle = _make_throttle()
    assert throttle.acquire("not a url").proceed is False


def test_failure_threshold_quarantines_domain():
    clock = _ManualClock()
    throttle = _make_throttle(clock=clock, failure_threshold=3, cooldown_seconds=60.0)
    url = "https://b.example.ac.jp/p"
    assert throttle.record_failure(url) is None
    assert throttle.record_failure(url) is None
    reason = throttle.record_failure(url)
    assert reason == "failure_threshold"
    assert "b.example.ac.jp" in throttle.quarantined_domains()


def test_blocked_signal_quarantines_immediately():
    throttle = _make_throttle(failure_threshold=10)
    url = "https://c.example.ac.jp/"
    assert throttle.record_failure(url, blocked=True) == "blocked"
    assert "c.example.ac.jp" in throttle.quarantined_domains()


def test_quarantined_domain_is_refused_until_cooldown_elapses():
    clock = _ManualClock()
    throttle = _make_throttle(clock=clock, cooldown_seconds=60.0)
    throttle.record_failure("https://d.example.ac.jp/", blocked=True)
    decision = throttle.acquire("https://d.example.ac.jp/page")
    assert decision.proceed is False
    assert decision.reason.startswith("domain_cooldown")


def test_global_circuit_breaker_blocks_all_when_too_many_quarantined():
    throttle = _make_throttle(max_quarantined_domains=2)
    throttle.record_failure("https://a.example.ac.jp/", blocked=True)
    throttle.record_failure("https://b.example.ac.jp/", blocked=True)
    decision = throttle.acquire("https://c.example.ac.jp/")
    assert decision.proceed is False
    assert decision.reason == "global_circuit_breaker"
    assert throttle.is_circuit_open() is True


def test_record_success_clears_consecutive_failure_count():
    throttle = _make_throttle(failure_threshold=3)
    url = "https://e.example.ac.jp/"
    throttle.record_failure(url)
    throttle.record_failure(url)
    throttle.record_success(url)
    assert throttle.record_failure(url) is None
    assert throttle.record_failure(url) is None
    assert throttle.record_failure(url) == "failure_threshold"


def test_invalid_jitter_raises():
    with pytest.raises(ValueError):
        CrawlThrottle(min_jitter=5.0, max_jitter=1.0)


def test_invalid_failure_threshold_raises():
    with pytest.raises(ValueError):
        CrawlThrottle(failure_threshold=0)


def test_invalid_cooldown_raises():
    with pytest.raises(ValueError):
        CrawlThrottle(cooldown_seconds=-1)


def test_headers_look_like_chrome_on_windows():
    headers = stealthy_request_headers()
    assert "Mozilla/5.0" in headers["User-Agent"]
    assert "Chrome/" in headers["User-Agent"]
    assert "Sec-Fetch-Mode" in headers
    assert headers["Accept-Language"].startswith("ja-JP")


def test_headers_accept_custom_language():
    headers = stealthy_request_headers(accept_language="en-US,en;q=0.5")
    assert headers["Accept-Language"] == "en-US,en;q=0.5"


@pytest.mark.parametrize("status_code", [403, 429, 503])
def test_block_status_codes_trigger_block_signal(status_code: int):
    assert is_block_signal(status_code=status_code, body_excerpt=None) is True


@pytest.mark.parametrize(
    "marker",
    ["cf-chl-bypass", "Cf-Ray", "checking your browser", "Captcha", "PerimeterX"],
)
def test_block_body_markers_trigger_block_signal(marker: str):
    assert is_block_signal(status_code=200, body_excerpt=f"<html>{marker}</html>") is True


def test_normal_html_response_is_not_a_block_signal():
    assert is_block_signal(status_code=200, body_excerpt="<html>Welcome</html>") is False


def test_empty_excerpt_with_normal_status_is_not_a_block():
    assert is_block_signal(status_code=200, body_excerpt=None) is False


def test_throttle_decision_is_frozen():
    d = ThrottleDecision(True, 1.0, "ok")
    with pytest.raises((AttributeError, Exception)):
        d.proceed = False  # type: ignore[misc]
