from __future__ import annotations

import sys
import types
from types import TracebackType

import pytest

from eidp.scraper import search_provider as module
from eidp.scraper.search_provider import (
    BraveSearchProvider,
    DuckDuckGoProvider,
    GoogleSearchProvider,
    SerperProvider,
    create_provider,
)


def test_duckduckgo_provider_uses_packaged_ddgs_module(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("ddgs")

    class FakeDDGS:
        def __enter__(self) -> FakeDDGS:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def text(self, query: str, *, region: str, max_results: int) -> list[dict[str, str]]:
            assert query == "学校 情報公開"
            assert region == "jp-jp"
            assert max_results == 2
            return [{
                "title": "学校 情報公開",
                "href": "https://example.ac.jp/disclosure/",
                "body": "公開情報",
            }]

    setattr(fake_module, "DDGS", FakeDDGS)
    monkeypatch.setitem(sys.modules, "ddgs", fake_module)

    results = DuckDuckGoProvider().search("学校 情報公開", count=2)

    assert len(results) == 1
    assert results[0].title == "学校 情報公開"
    assert results[0].url == "https://example.ac.jp/disclosure/"
    assert results[0].description == "公開情報"


def test_duckduckgo_provider_falls_back_to_legacy_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "ddgs", raising=False)
    legacy_module = types.ModuleType("duckduckgo_search")

    class FakeDDGS:
        def __enter__(self) -> FakeDDGS:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def text(self, query: str, *, region: str, max_results: int) -> list[dict[str, str]]:
            return [{"title": query, "href": "https://legacy.example/", "body": region}]

    setattr(legacy_module, "DDGS", FakeDDGS)
    monkeypatch.setitem(sys.modules, "duckduckgo_search", legacy_module)
    def fake_import_module(name: str) -> types.ModuleType:
        if name == "ddgs":
            raise ImportError(name)
        return legacy_module

    monkeypatch.setattr(module.importlib, "import_module", fake_import_module)

    result = DuckDuckGoProvider().search("legacy", count=1)[0]

    assert (result.title, result.url, result.description) == ("legacy", "https://legacy.example/", "jp-jp")


def test_duckduckgo_provider_raises_when_no_client_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module.importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError(name)))

    with pytest.raises(ImportError, match="ddgs package not installed"):
        DuckDuckGoProvider().search("missing")


def test_http_search_providers_map_api_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 15.0

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def get(self, url: str, **kwargs: object) -> FakeResponse:
            calls.append(("GET", url, dict(kwargs)))
            if "brave" in url:
                return FakeResponse(
                    {"web": {"results": [{"title": "B", "url": "https://b.example/", "description": "brave"}]}}
                )
            return FakeResponse({"items": [{"title": "G", "link": "https://g.example/", "snippet": "google"}]})

        def post(self, url: str, **kwargs: object) -> FakeResponse:
            calls.append(("POST", url, dict(kwargs)))
            return FakeResponse({"organic": [{"title": "S", "link": "https://s.example/", "snippet": "serper"}]})

    monkeypatch.setattr(module.httpx, "Client", FakeClient)

    brave = BraveSearchProvider("brave-key").search("q", count=2)
    google = GoogleSearchProvider("google-key", "cx").search("q", count=20)
    serper = SerperProvider("serper-key").search("q", count=3)

    assert [(r.title, r.url, r.description) for r in brave + google + serper] == [
        ("B", "https://b.example/", "brave"),
        ("G", "https://g.example/", "google"),
        ("S", "https://s.example/", "serper"),
    ]
    assert calls[0] == (
        "GET",
        BraveSearchProvider.API_URL,
        {
            "headers": {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": "brave-key",
            },
            "params": {"q": "q", "count": 2, "search_lang": "jp", "country": "JP"},
        },
    )
    assert calls[1][2]["params"] == {
        "key": "google-key",
        "cx": "cx",
        "q": "q",
        "num": 10,
        "lr": "lang_ja",
        "gl": "jp",
    }
    assert calls[2] == (
        "POST",
        SerperProvider.API_URL,
        {
            "headers": {"X-API-KEY": "serper-key", "Content-Type": "application/json"},
            "json": {"q": "q", "num": 3, "gl": "jp", "hl": "ja"},
        },
    )


def test_create_provider_validates_required_credentials() -> None:
    assert create_provider("duckduckgo").name() == "duckduckgo"
    assert create_provider("brave", api_key="key").name() == "brave"
    assert create_provider("google", api_key="key", google_cx="cx").name() == "google"
    assert create_provider("serper", api_key="key").name() == "serper"

    with pytest.raises(ValueError, match="BRAVE_API_KEY required"):
        create_provider("brave")
    with pytest.raises(ValueError, match="GOOGLE_API_KEY and GOOGLE_CX required"):
        create_provider("google", api_key="key")
    with pytest.raises(ValueError, match="SERPER_API_KEY required"):
        create_provider("serper")
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("unknown")
