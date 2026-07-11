"""Tests for optional Scrapling fetcher adapters."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from eidp.scraper.school_url_errors import ScraplingUnavailableError
from eidp.scraper.scrapling_fetcher import (
    ScraplingHtmlFetcher,
    ScraplingPageFetcher,
    SearchProviderSerpFetcher,
    _ensure_playwright_browsers_path,
    _load_scrapling_fetchers,
    _page_html,
)
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
    def __init__(self) -> None:
        self._page = FakePage()

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *_args: object) -> None:
        self._page.closed = True
        return None

    def get(self, url: str, *, stealthy_headers: bool = False) -> object:
        assert stealthy_headers is True
        assert url == "https://www.tokyo-design.ac.jp/"
        return self._page


class FakePage:
    status = 200
    url = "https://www.tokyo-design.ac.jp/"
    closed = False

    def css(self, selector: str) -> FakeSelector:
        if self.closed:
            raise RuntimeError("page parsed after session closed")
        if selector == "title::text":
            return FakeSelector(first="東京デザイン専門学校 公式サイト")
        if selector == "body":
            return FakeSelector()
        if selector == "body ::text":
            return FakeSelector(all_values=["情報公開", "高等教育", "修学支援"])
        return FakeSelector()


class FakeHtmlPage:
    status = 200
    url = "https://www.tokyo-design.ac.jp/disclosure/"
    html = """
    <html>
      <body>
        <a href="/docs/r8-kakunin.pdf">令和8年度 確認申請書</a>
      </body>
    </html>
    """

    def css(self, selector: str) -> FakeSelector:
        if selector == "body":
            return FakeSelector()
        if selector == "body ::text":
            return FakeSelector(all_values=["令和8年度", "確認申請書"])
        return FakeSelector()


class FakeBlockedPage:
    status = 403
    url = "https://www.tokyo-design.ac.jp/blocked/"
    html = "<html><body>Access Denied</body></html>"

    def css(self, selector: str) -> FakeSelector:
        if selector == "body":
            return FakeSelector(all_values=["Access Denied"])
        if selector == "body ::text":
            return FakeSelector(all_values=["Access Denied"])
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


def test_scrapling_page_fetcher_maps_stealthy_page(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    class FakeStealthyFetcher:
        @staticmethod
        def fetch(url: str, *, headless: bool = True, network_idle: bool = True) -> FakeHtmlPage:
            assert url == "https://www.tokyo-design.ac.jp/"
            assert headless is False
            assert network_idle is False
            return FakeHtmlPage()

    monkeypatch.setattr(module, "scrapling_available", lambda: True)
    monkeypatch.setattr(module, "_ensure_playwright_browsers_path", lambda: None)
    monkeypatch.setattr(
        module.importlib,
        "import_module",
        lambda name: SimpleNamespace(StealthyFetcher=FakeStealthyFetcher),
    )
    fetcher = ScraplingPageFetcher(mode="stealthy", headless=False, network_idle=False)

    page = fetcher.fetch("https://www.tokyo-design.ac.jp/")

    assert page is not None
    assert page.url == "https://www.tokyo-design.ac.jp/disclosure/"
    assert "確認申請書" in page.body_excerpt


def test_scrapling_html_fetcher_returns_rendered_html(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    class FakeDynamicFetcher:
        @staticmethod
        def fetch(url: str, *, disable_resources: bool = True) -> FakeHtmlPage:
            assert url == "https://www.tokyo-design.ac.jp/disclosure/"
            assert disable_resources is True
            return FakeHtmlPage()

    monkeypatch.setattr(module, "scrapling_available", lambda: True)
    monkeypatch.setattr(
        module.importlib,
        "import_module",
        lambda name: SimpleNamespace(DynamicFetcher=FakeDynamicFetcher),
    )
    fetcher = ScraplingHtmlFetcher(mode="dynamic")

    html = fetcher.fetch_html("https://www.tokyo-design.ac.jp/disclosure/")

    assert html is not None
    assert "r8-kakunin.pdf" in html


def test_scrapling_html_fetcher_returns_none_for_blocked_page(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    class FakeDynamicFetcher:
        @staticmethod
        def fetch(url: str, *, disable_resources: bool = True) -> FakeBlockedPage:
            assert disable_resources is True
            return FakeBlockedPage()

    monkeypatch.setattr(module, "scrapling_available", lambda: True)
    monkeypatch.setattr(module, "_ensure_playwright_browsers_path", lambda: None)
    monkeypatch.setattr(
        module.importlib,
        "import_module",
        lambda name: SimpleNamespace(DynamicFetcher=FakeDynamicFetcher),
    )
    fetcher = ScraplingHtmlFetcher(mode="dynamic")

    assert fetcher.fetch_html("https://www.tokyo-design.ac.jp/blocked/") is None


def test_scrapling_html_fetcher_rejects_static_mode_without_fake_html(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    monkeypatch.setattr(module, "scrapling_available", lambda: True)
    monkeypatch.setattr(
        module.importlib,
        "import_module",
        lambda name: SimpleNamespace(FetcherSession=lambda impersonate: FakeSession()),
    )
    fetcher = ScraplingHtmlFetcher(mode="static")

    html = fetcher.fetch_html("https://www.tokyo-design.ac.jp/")

    assert html is None


def test_load_scrapling_fetchers_raises_when_extra_missing(monkeypatch) -> None:
    import eidp.scraper.scrapling_fetcher as module

    monkeypatch.setattr(module, "scrapling_available", lambda: False)

    with pytest.raises(ScraplingUnavailableError, match="Scrapling is not installed"):
        _load_scrapling_fetchers()


def test_ensure_playwright_browsers_path_uses_project_cache(monkeypatch, tmp_path) -> None:
    app_root = tmp_path / "EIDP"
    browsers = app_root / ".cache" / "ms-playwright"
    browsers.mkdir(parents=True)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    _ensure_playwright_browsers_path(app_root=app_root)

    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browsers)


def test_ensure_playwright_browsers_path_preserves_existing_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "/already/configured")
    browsers = tmp_path / "EIDP" / ".cache" / "ms-playwright"
    browsers.mkdir(parents=True)

    _ensure_playwright_browsers_path(app_root=tmp_path / "EIDP")

    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "/already/configured"


def test_page_html_uses_callable_content_then_css_and_get_fallbacks() -> None:
    class CallableContentPage:
        def content(self) -> str:
            return "<html>callable content</html>"

    class CssHtmlPage:
        def css(self, selector: str) -> FakeSelector:
            assert selector == "html"
            return FakeSelector(first="<html>css fallback</html>")

    class GetFallbackPage:
        html = ""
        content = ""

        def css(self, selector: str) -> FakeSelector:
            raise RuntimeError("no css")

        def get(self) -> str:
            return "<html>get fallback</html>"

    assert _page_html(CallableContentPage()) == "<html>callable content</html>"
    assert _page_html(CssHtmlPage()) == "<html>css fallback</html>"
    assert _page_html(GetFallbackPage()) == "<html>get fallback</html>"
