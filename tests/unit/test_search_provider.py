from __future__ import annotations

import sys
import types
from types import TracebackType

import pytest

from eidp.scraper.search_provider import DuckDuckGoProvider


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
