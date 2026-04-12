"""Search provider abstraction — supports Brave, Google, or any future API.

Usage:
    provider = create_provider("brave", api_key="...")
    results = provider.search("日本工学院専門学校 情報公開")
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    description: str


class SearchProvider(abc.ABC):
    """Abstract search provider interface."""

    @abc.abstractmethod
    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        ...

    @abc.abstractmethod
    def name(self) -> str:
        ...


class BraveSearchProvider(SearchProvider):
    """Brave Search API (free tier: 2,000 queries/month)."""

    API_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def name(self) -> str:
        return "brave"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params = {"q": query, "count": count, "search_lang": "jp", "country": "JP"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(self.API_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for item in data.get("web", {}).get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                )
            )
        return results


class GoogleSearchProvider(SearchProvider):
    """Google Custom Search API (free tier: 100 queries/day)."""

    API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cx: str) -> None:
        self._api_key = api_key
        self._cx = cx

    def name(self) -> str:
        return "google"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        params = {
            "key": self._api_key,
            "cx": self._cx,
            "q": query,
            "num": min(count, 10),
            "lr": "lang_ja",
            "gl": "jp",
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for item in data.get("items", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    description=item.get("snippet", ""),
                )
            )
        return results


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search via duckduckgo_search. No API key needed."""

    def name(self) -> str:
        return "duckduckgo"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:
            raise ImportError(
                "ddgs package not installed. Run: uv sync --extra scraper"
            )

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="jp-jp", max_results=count):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        description=r.get("body", ""),
                    )
                )
        return results


class SerperProvider(SearchProvider):
    """Serper.dev Google Search API (free: 2,500 queries/month)."""

    API_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def name(self) -> str:
        return "serper"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": count, "gl": "jp", "hl": "ja"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(self.API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for item in data.get("organic", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    description=item.get("snippet", ""),
                )
            )
        return results


def create_provider(
    provider_name: str = "duckduckgo",
    api_key: str = "",
    google_cx: str = "",
) -> SearchProvider:
    """Factory function. Switch providers by changing config.

    Supported: duckduckgo (default, no key), brave, google, serper
    """
    if provider_name == "duckduckgo":
        return DuckDuckGoProvider()
    elif provider_name == "brave":
        if not api_key:
            raise ValueError("BRAVE_API_KEY required")
        return BraveSearchProvider(api_key)
    elif provider_name == "google":
        if not api_key or not google_cx:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CX required")
        return GoogleSearchProvider(api_key, google_cx)
    elif provider_name == "serper":
        if not api_key:
            raise ValueError("SERPER_API_KEY required. Get one at https://serper.dev/")
        return SerperProvider(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: duckduckgo, brave, google, serper")
