"""Scrapling-backed fetcher adapters for school URL discovery.

This module is intentionally optional. Importing it must not require the
``scrapling`` package, because the default HTTP-first path does not require a
browser runtime.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import structlog

from eidp.scraper.anti_detection import is_block_signal
from eidp.scraper.school_url_errors import ScraplingUnavailableError
from eidp.scraper.school_website_crawl import FetchedPage, SerpHit
from eidp.scraper.search_provider import SearchProvider

ScraplingFetchMode = Literal["static", "dynamic", "stealthy"]
log = structlog.get_logger()


def scrapling_available() -> bool:
    """Return whether the optional Scrapling package is importable."""

    return importlib.util.find_spec("scrapling") is not None


def _ensure_playwright_browsers_path(*, app_root: Path | None = None) -> None:
    """Keep optional browser downloads inside the authorized application root."""

    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    root = app_root
    if root is None:
        try:
            from eidp.config import settings
        except Exception:
            return
        root = settings.app_root

    browsers_dir = Path(root) / ".cache" / "ms-playwright"
    if browsers_dir.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_dir)


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
        if self.mode == "static":
            return self._fetch_static(url)
        page = self._fetch_page(url)
        return _fetched_page_from_scrapling_page(page, fallback_url=url)

    def _fetch_static(self, url: str) -> FetchedPage:
        fetchers = _load_scrapling_fetchers()
        session_cls = getattr(fetchers, "FetcherSession")
        with session_cls(impersonate="chrome") as session:
            page = session.get(url, stealthy_headers=True)
            return _fetched_page_from_scrapling_page(page, fallback_url=url)

    def _fetch_page(self, url: str) -> Any:
        fetchers = _load_scrapling_fetchers()
        if self.mode in {"dynamic", "stealthy"}:
            _ensure_playwright_browsers_path()
        if self.mode == "dynamic":
            dynamic_fetcher = getattr(fetchers, "DynamicFetcher")
            return dynamic_fetcher.fetch(url, disable_resources=self.disable_resources)
        if self.mode == "stealthy":
            stealthy_fetcher = getattr(fetchers, "StealthyFetcher")
            return stealthy_fetcher.fetch(url, headless=self.headless, network_idle=self.network_idle)
        return self._fetch_static(url)


@dataclass(frozen=True)
class ScraplingHtmlFetcher:
    """Fetch rendered HTML with Scrapling for PDF link extraction."""

    mode: ScraplingFetchMode = "dynamic"
    disable_resources: bool = True
    headless: bool = True
    network_idle: bool = True

    def fetch_html(self, url: str) -> str | None:
        if self.mode == "static":
            log.warning("scrapling_html_static_unsupported", url=url)
            return None
        page = ScraplingPageFetcher(
            mode=self.mode,
            disable_resources=self.disable_resources,
            headless=self.headless,
            network_idle=self.network_idle,
        )._fetch_page(url)
        status = int(getattr(page, "status", 0) or 0)
        body_excerpt = _body_excerpt(page)
        if is_block_signal(status_code=status, body_excerpt=body_excerpt):
            return None
        return _page_html(page)


def _selector_first_text(page: Any, selector: str) -> str:
    try:
        value = page.css(selector).get()
    except Exception:
        return ""
    if value is None:
        return ""
    return str(value).strip()


def _load_scrapling_fetchers() -> Any:
    if not scrapling_available():
        raise ScraplingUnavailableError(
            "Scrapling is not installed. Install the scraper-scrapling extra to use school URL auto-crawl."
        )
    return importlib.import_module("scrapling.fetchers")


def _fetched_page_from_scrapling_page(page: Any, *, fallback_url: str) -> FetchedPage:
    status = int(getattr(page, "status", 0) or 0)
    title = _selector_first_text(page, "title::text")
    body_excerpt = _body_excerpt(page)
    final_url = str(getattr(page, "url", "") or fallback_url)
    return FetchedPage(
        url=final_url,
        status_code=status,
        title=title,
        body_excerpt=body_excerpt,
        blocked=is_block_signal(status_code=status, body_excerpt=body_excerpt),
    )


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


def _page_html(page: Any) -> str:
    for attr in ("html", "content"):
        value = getattr(page, attr, None)
        if isinstance(value, str) and value.strip():
            return value
        if callable(value):
            try:
                rendered = value()
            except Exception:
                rendered = None
            if isinstance(rendered, str) and rendered.strip():
                return rendered

    try:
        html_value = page.css("html").get()
    except Exception:
        html_value = None
    if html_value:
        return str(html_value)

    get_value = getattr(page, "get", None)
    if callable(get_value):
        try:
            rendered = get_value()
        except Exception:
            rendered = None
        if isinstance(rendered, str) and rendered.strip():
            return rendered

    rendered = str(page)
    return rendered if rendered and rendered != object.__str__(page) else ""
