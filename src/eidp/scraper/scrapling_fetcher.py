"""Scrapling-backed fetcher adapters for school URL discovery.

This module is intentionally optional. Importing it must not require the
``scrapling`` package, because the Windows core ZIP remains HTTP-first and the
browser-capable crawler is distributed as an add-on.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any, Literal

from eidp.scraper.anti_detection import is_block_signal
from eidp.scraper.school_website_crawl import FetchedPage, SerpHit
from eidp.scraper.search_provider import SearchProvider

ScraplingFetchMode = Literal["static", "dynamic", "stealthy"]


class ScraplingUnavailableError(RuntimeError):
    """Raised when the optional Scrapling runtime is not installed."""


def scrapling_available() -> bool:
    """Return whether the optional Scrapling package is importable."""

    return importlib.util.find_spec("scrapling") is not None


@dataclass(frozen=True)
class SearchProviderSerpFetcher:
    """Adapter from EIDP's SearchProvider to SchoolUrlCrawler's SERP protocol."""

    provider: SearchProvider

    def search(self, query: str, *, max_results: int = 5) -> list[SerpHit]:
        return [
            SerpHit(url=result.url, title=result.title, snippet=result.description)
            for result in self.provider.search(query, count=max_results)
        ]


@dataclass(frozen=True)
class ScraplingPageFetcher:
    """Fetch candidate pages with Scrapling and return only scoring signals."""

    mode: ScraplingFetchMode = "static"
    disable_resources: bool = True
    headless: bool = True
    network_idle: bool = True

    def fetch(self, url: str) -> FetchedPage | None:
        page = self._fetch_page(url)
        status = int(getattr(page, "status", 0) or 0)
        title = _selector_first_text(page, "title::text")
        body_excerpt = _body_excerpt(page)
        final_url = str(getattr(page, "url", "") or url)
        return FetchedPage(
            url=final_url,
            status_code=status,
            title=title,
            body_excerpt=body_excerpt,
            blocked=is_block_signal(status_code=status, body_excerpt=body_excerpt),
        )

    def _fetch_page(self, url: str) -> Any:
        if not scrapling_available():
            raise ScraplingUnavailableError(
                "Scrapling is not installed. Install the scraper-scrapling add-on to use school URL auto-crawl."
            )
        fetchers = importlib.import_module("scrapling.fetchers")
        if self.mode == "dynamic":
            dynamic_fetcher = getattr(fetchers, "DynamicFetcher")
            return dynamic_fetcher.fetch(url, disable_resources=self.disable_resources)
        if self.mode == "stealthy":
            stealthy_fetcher = getattr(fetchers, "StealthyFetcher")
            return stealthy_fetcher.fetch(url, headless=self.headless, network_idle=self.network_idle)

        session_cls = getattr(fetchers, "FetcherSession")
        with session_cls(impersonate="chrome") as session:
            return session.get(url, stealthy_headers=True)


def _selector_first_text(page: Any, selector: str) -> str:
    try:
        value = page.css(selector).get()
    except Exception:
        return ""
    if value is None:
        return ""
    return str(value).strip()


def _body_excerpt(page: Any, *, limit: int = 4000) -> str:
    body = ""
    try:
        body_selection = page.css("body")
        text_getter = getattr(body_selection, "get_all_text", None)
        if callable(text_getter):
            body = str(text_getter(strip=True))
    except Exception:
        body = ""
    if not body:
        try:
            values = page.css("body ::text").getall()
        except Exception:
            values = []
        body = " ".join(str(v).strip() for v in values if str(v).strip())
    return body[:limit]
