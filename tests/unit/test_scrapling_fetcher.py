"""Tests for optional Scrapling fetcher adapters."""

from __future__ import annotations

from types import SimpleNamespace

from eidp.scraper.scrapling_fetcher import ScraplingPageFetcher, SearchProviderSerpFetcher
from eidp.scraper.search_provider import SearchResult


class FakeProvider:
    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        assert query == "東京デザイン専門学校 公式"
        assert count == 2
        return [
            SearchResult(
                title="東京デザイン専門学校",
                url="https://www.tokyo-design.ac.jp/",
                description="情報公開",
            )
        ]

    def name(self) -> str:
        return "fake"


class FakeSelector:
    def __init__(self, *, first: str = "", all_values: list[str] | None = None) -> None:
        self._first = first
        self._all_values = all_values or []

    def get(self) -> str:
        return self._first

    def getall(self) -> list[str]:
        return self._all_values


class FakeSession:
    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def get(self, url: str, *, stealthy_headers: bool = False) -> object:
        assert stealthy_headers is True
        assert url == "https://www.tokyo-design.ac.jp/"
        return FakePage()


class FakePage:
    status = 200
    url = "https://www.tokyo-design.ac.jp/"

    def css(self, selector: str) -> FakeSelector:
        if selector == "title::text":
            return FakeSelector(first="東京デザイン専門学校 公式サイト")
        if selector == "body":
            return FakeSelector()
        if selector == "body ::text":
            return FakeSelector(all_values=["情報公開", "高等教育", "修学支援"])
        return FakeSelector()


def test_search_provider_serp_fetcher_adapts_results() -> None:
    fetcher = SearchProviderSerpFetcher(FakeProvider())

    hits = fetcher.search("東京デザイン専門学校 公式", max_results=2)

    assert len(hits) == 1
    assert hits[0].url == "https://www.tokyo-design.ac.jp/"
    assert hits[0].title == "東京デザイン専門学校"
    assert hits[0].snippet == "情報公開"


def test_scrapling_page_fetcher_maps_static_page(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    monkeypatch.setattr(module, "scrapling_available", lambda: True)
    monkeypatch.setattr(
        module.importlib,
        "import_module",
        lambda name: SimpleNamespace(FetcherSession=lambda impersonate: FakeSession()),
    )
    fetcher = ScraplingPageFetcher(mode="static")

    page = fetcher.fetch("https://www.tokyo-design.ac.jp/")

    assert page is not None
    assert page.status_code == 200
    assert page.title == "東京デザイン専門学校 公式サイト"
    assert "修学支援" in page.body_excerpt
    assert page.blocked is False
