"""Search provider abstraction — supports Brave, Google, or any future API.

Usage:
    provider = create_provider("brave", api_key="...")
    results = provider.search("日本工学院専門学校 情報公開")
"""

from __future__ import annotations

import abc
import importlib
import json
import os
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

_EXTERNAL_STDOUT_MAX_BYTES = 2_000_000


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
        params: dict[str, str | int] = {"q": query, "count": count, "search_lang": "jp", "country": "JP"}

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
        params: dict[str, str | int] = {
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
    """DuckDuckGo search via the packaged DDGS client. No API key needed."""

    def name(self) -> str:
        return "duckduckgo"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        ddgs_cls: Any
        try:
            ddgs_cls = importlib.import_module("ddgs").DDGS
        except ImportError:
            try:
                ddgs_cls = importlib.import_module("duckduckgo_search").DDGS
            except ImportError as exc:
                raise ImportError(
                    "ddgs package not installed. Install EIDP with the scraper-basic extra."
                ) from exc

        results: list[SearchResult] = []
        with ddgs_cls() as ddgs:
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


def _external_command_args(command: str, *, query: str, count: int) -> list[str]:
    args = shlex.split(command, posix=os.name != "nt")
    if not args:
        raise ValueError("EIDP_EXTERNAL_SEARCH_COMMAND required for external search provider")
    replacements = {
        "{query_json}": json.dumps(query, ensure_ascii=False),
        "{query}": query,
        "{count}": str(count),
    }
    normalized_args = [_strip_wrapping_quotes(arg) for arg in args]
    return [
        arg.replace("{query_json}", replacements["{query_json}"])
        .replace("{query}", replacements["{query}"])
        .replace("{count}", replacements["{count}"])
        for arg in normalized_args
    ]


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _external_records(payload: object) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    if any(isinstance(payload.get(key), str) for key in ("url", "link", "href")):
        return [payload]
    for key in ("results", "items", "organic", "data", "links"):
        records = _external_records(payload.get(key))
        if records:
            return records
    return []


def _first_external_text(record: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


class ExternalCommandSearchProvider(SearchProvider):
    """Search provider backed by an operator-controlled local command.

    The command runs without a shell and must print JSON. It can read the query
    from ``EIDP_EXTERNAL_SEARCH_QUERY`` or use ``{query}`` / ``{query_json}``
    placeholders in the configured command string.
    """

    def __init__(self, command: str, *, timeout_seconds: float = 30.0) -> None:
        self._command = command.strip()
        self._timeout_seconds = max(float(timeout_seconds), 0.1)

    def name(self) -> str:
        return "external"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        bounded_count = max(int(count), 0)
        if bounded_count == 0:
            return []

        args = _external_command_args(self._command, query=query, count=bounded_count)
        env = os.environ.copy()
        env["EIDP_EXTERNAL_SEARCH_QUERY"] = query
        env["EIDP_EXTERNAL_SEARCH_COUNT"] = str(bounded_count)
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                check=False,
                env=env,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"External search command timed out after {self._timeout_seconds:g}s") from exc

        if completed.returncode != 0:
            stderr_tail = completed.stderr.strip().splitlines()[-1][:300] if completed.stderr.strip() else ""
            detail = f": {stderr_tail}" if stderr_tail else ""
            raise RuntimeError(f"External search command failed with exit code {completed.returncode}{detail}")
        if len(completed.stdout.encode("utf-8")) > _EXTERNAL_STDOUT_MAX_BYTES:
            raise RuntimeError("External search command returned too much output")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("External search command returned invalid JSON") from exc

        results: list[SearchResult] = []
        for record in _external_records(payload):
            url = _first_external_text(record, ("url", "link", "href"))
            if not url:
                continue
            title = _first_external_text(record, ("title", "name")) or url
            description = _first_external_text(record, ("description", "snippet", "summary", "body", "text", "content"))
            results.append(SearchResult(title=title, url=url, description=description))
        return results[:bounded_count]


def create_provider(
    provider_name: str = "duckduckgo",
    api_key: str = "",
    google_cx: str = "",
    external_command: str = "",
    external_timeout_seconds: float = 30.0,
) -> SearchProvider:
    """Factory function. Switch providers by changing config.

    Supported: duckduckgo (default, no key), brave, google, serper, external
    """
    normalized_provider = provider_name.strip().lower()
    if normalized_provider == "duckduckgo":
        return DuckDuckGoProvider()
    elif normalized_provider == "brave":
        if not api_key:
            raise ValueError("BRAVE_API_KEY required")
        return BraveSearchProvider(api_key)
    elif normalized_provider == "google":
        if not api_key or not google_cx:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CX required")
        return GoogleSearchProvider(api_key, google_cx)
    elif normalized_provider == "serper":
        if not api_key:
            raise ValueError("SERPER_API_KEY required. Get one at https://serper.dev/")
        return SerperProvider(api_key)
    elif normalized_provider == "external":
        if not external_command.strip():
            raise ValueError("EIDP_EXTERNAL_SEARCH_COMMAND required for external provider")
        return ExternalCommandSearchProvider(external_command, timeout_seconds=external_timeout_seconds)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: duckduckgo, brave, google, serper, external")
