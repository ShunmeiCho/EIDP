"""Tests for src/eidp/scraper/school_website_crawl.py."""

from __future__ import annotations

import pytest

from eidp.scraper.anti_detection import CrawlThrottle
from eidp.scraper.school_url_errors import ScraplingUnavailableError
from eidp.scraper.school_website_crawl import (
    FetchedPage,
    SchoolUrlCrawler,
    SerpHit,
)
from eidp.scraper.url_scoring import UrlScoreThresholds


class FakeSerpFetcher:
    def __init__(self, hits_by_query: dict[str, list[SerpHit]]) -> None:
        self.hits_by_query = hits_by_query
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, *, max_results: int = 5) -> list[SerpHit]:
        self.calls.append((query, max_results))
        return self.hits_by_query.get(query, [])[:max_results]


class FakePageFetcher:
    def __init__(self, pages: dict[str, FetchedPage | Exception]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchedPage | None:
        self.calls.append(url)
        page = self.pages.get(url)
        if isinstance(page, Exception):
            raise page
        return page


def _throttle() -> CrawlThrottle:
    return CrawlThrottle(
        min_seconds_per_domain=0.0,
        min_jitter=0.0,
        max_jitter=0.0,
        cooldown_seconds=60.0,
    )


def test_discover_for_auto_accepts_official_school_site_after_page_fetch() -> None:
    url = "https://www.tokyo-design.ac.jp/"
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url=url, title="東京デザイン専門学校"),
                SerpHit(url="https://www.shingakunet.com/school/example", title="進学情報"),
            ],
        }),
        page_fetcher=FakePageFetcher({
            url: FetchedPage(
                url=url,
                status_code=200,
                title="東京デザイン専門学校 公式サイト",
                body_excerpt="情報公開 高等教育 修学支援 機関要件",
            ),
        }),
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "auto"
    assert result.best is not None
    assert result.best.candidate_url == url
    assert result.best.score >= UrlScoreThresholds().auto
    assert result.candidates[0].breakdown["disclosure_keyword"] == pytest.approx(1.0)


def test_discover_for_deduplicates_normalized_urls_before_fetching() -> None:
    page_fetcher = FakePageFetcher({
        "https://www.tokyo-design.ac.jp/": FetchedPage(
            url="https://www.tokyo-design.ac.jp/",
            status_code=200,
            title="東京デザイン専門学校 公式サイト",
            body_excerpt="情報公開 高等教育 修学支援 機関要件",
        ),
    })
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url="https://www.tokyo-design.ac.jp/", title="東京デザイン専門学校"),
                SerpHit(url="https://www.tokyo-design.ac.jp#top", title="東京デザイン専門学校"),
                SerpHit(url="https://www.tokyo-design.ac.jp", title="東京デザイン専門学校"),
            ],
        }),
        page_fetcher=page_fetcher,
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "auto"
    assert page_fetcher.calls == ["https://www.tokyo-design.ac.jp/"]
    assert len(result.candidates) == 1


def test_discover_for_returns_review_for_medium_confidence_serp_only_candidate() -> None:
    url = "https://design-tokyo.jp/"
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url=url, title="東京デザイン専門学校"),
            ],
        }),
        page_fetcher=FakePageFetcher({url: RuntimeError("network down")}),
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "review"
    assert result.best is not None
    assert result.best.candidate_url == url
    assert "serp_error" not in " ".join(result.notes)


def test_discover_for_raises_when_optional_runtime_is_unavailable() -> None:
    url = "https://www.tokyo-design.ac.jp/"
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url=url, title="東京デザイン専門学校"),
            ],
        }),
        page_fetcher=FakePageFetcher({url: ScraplingUnavailableError("scrapling missing")}),
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    with pytest.raises(ScraplingUnavailableError):
        crawler.discover_for(
            school_id=1,
            school_name="東京デザイン専門学校",
            prefecture="東京都",
            queries=["東京デザイン専門学校 公式サイト"],
        )


def test_discover_for_skips_blacklisted_third_party_without_fetching() -> None:
    page_fetcher = FakePageFetcher({})
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url="https://www.shingakunet.com/school/example", title="東京デザイン専門学校"),
            ],
        }),
        page_fetcher=page_fetcher,
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "reject"
    assert result.best is None
    assert page_fetcher.calls == []


def test_discover_for_records_blocked_response_and_falls_back_to_serp_score() -> None:
    url = "https://design-tokyo.jp/"
    throttle = _throttle()
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({
            "東京デザイン専門学校 公式サイト": [
                SerpHit(url=url, title="東京デザイン専門学校"),
            ],
        }),
        page_fetcher=FakePageFetcher({
            url: FetchedPage(
                url=url,
                status_code=503,
                title="",
                body_excerpt="Checking your browser",
                blocked=True,
            ),
        }),
        throttle=throttle,
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "review"
    assert "blocked_response" in result.notes
    assert "design-tokyo.jp" in throttle.quarantined_domains()


def test_discover_for_stops_when_global_circuit_is_open() -> None:
    throttle = CrawlThrottle(max_quarantined_domains=1)
    throttle.record_failure("https://blocked.example.ac.jp/", blocked=True)
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({}),
        page_fetcher=FakePageFetcher({}),
        throttle=throttle,
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "circuit_open"
    assert result.notes == ("global_circuit_breaker",)


def test_discover_for_handles_empty_serp_results() -> None:
    crawler = SchoolUrlCrawler(
        serp_fetcher=FakeSerpFetcher({"東京デザイン専門学校 公式サイト": []}),
        page_fetcher=FakePageFetcher({}),
        throttle=_throttle(),
        sleep=lambda _seconds: None,
    )

    result = crawler.discover_for(
        school_id=1,
        school_name="東京デザイン専門学校",
        prefecture="東京都",
        queries=["東京デザイン専門学校 公式サイト"],
    )

    assert result.decision == "no_candidates"
    assert result.best is None
