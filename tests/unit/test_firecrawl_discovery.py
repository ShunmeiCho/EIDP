from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolSite
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.scraper import firecrawl_discovery as module


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    bootstrap_sqlite(engine)
    return Session(engine)


def _school(session: Session, school_id: int, *, name: str, corp: str = "法人") -> School:
    school = School(
        id=school_id,
        prefecture="東京都",
        corporation_name=corp,
        school_name=name,
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    session.flush()
    return school


def test_firecrawl_map_posts_payload_and_accepts_string_or_dict_links(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "links": [
                    "https://safe.example/docs/a.pdf",
                    {"url": "https://safe.example/disclosure/"},
                    {"url": 123},
                    456,
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            calls.append({"timeout": timeout})

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "Client", FakeClient)

    urls = module._firecrawl_map("https://safe.example/", "確認申請書", limit=3, api_key="secret")

    assert urls == ["https://safe.example/docs/a.pdf", "https://safe.example/disclosure/"]
    assert calls[0] == {"timeout": 30.0}
    assert calls[1]["url"] == "https://api.firecrawl.dev/v1/map"
    assert calls[1]["headers"]["Authorization"] == "Bearer secret"
    assert calls[1]["json"] == {"url": "https://safe.example/", "search": "確認申請書", "limit": 3}


def test_firecrawl_map_returns_empty_on_http_error(monkeypatch) -> None:
    class FakeResponse:
        status_code = 429

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", "https://api.firecrawl.dev/v1/map")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "Client", FakeClient)

    assert module._firecrawl_map("https://safe.example/", "確認申請書", api_key="secret") == []


def test_discover_pdfs_for_corporation_matches_pdf_page_and_directory_fallback(monkeypatch) -> None:
    monkeypatch.setattr(module, "_is_safe_url", lambda url: url.startswith("https://safe.example"))
    monkeypatch.setattr(
        module,
        "_firecrawl_map",
        lambda *args, **kwargs: [
            "https://safe.example/docs/東京テスト専門学校.pdf",
            "https://safe.example/disclosure/大阪テスト専門学校/",
            "https://safe.example/public/joho/kikan-yoken.pdf?download=1",
            "https://unsafe.example/ignored.pdf",
        ],
    )

    with _session() as session:
        schools = [
            _school(session, 1, name="東京テスト専門学校"),
            _school(session, 2, name="大阪テスト専門学校"),
            _school(session, 3, name="京都テスト専門学校"),
            _school(session, 4, name="未一致校"),
        ]
        existing = SchoolSite(
            school_id=1,
            url="https://safe.example/docs/東京テスト専門学校.pdf",
            url_type="school",
            discovery_method="firecrawl_map",
            confidence=0.9,
        )
        session.add(existing)
        session.commit()

        stats = module.discover_pdfs_for_corporation(session, "https://safe.example/", schools)
        session.commit()

        sites = session.query(SchoolSite).order_by(SchoolSite.school_id, SchoolSite.url).all()

    assert stats == {"searched": 1, "matched": 4, "unmatched": 0, "errors": 0}
    assert [(site.school_id, site.url, float(site.confidence)) for site in sites] == [
        (1, "https://safe.example/docs/東京テスト専門学校.pdf", 0.9),
        (2, "https://safe.example/disclosure/大阪テスト専門学校/", 0.85),
        (3, "https://safe.example/public/joho/", 0.6),
        (4, "https://safe.example/public/joho/", 0.6),
    ]


def test_discover_pdfs_for_corporation_retries_second_search_and_counts_unmatched(monkeypatch) -> None:
    monkeypatch.setattr(module, "_is_safe_url", lambda url: url.startswith("https://safe.example"))
    calls: list[str] = []

    def fake_map(base_url: str, search: str, limit: int = 50, api_key: str = "") -> list[str]:
        calls.append(search)
        if len(calls) == 1:
            return []
        return ["https://safe.example/disclosure/other-page/"]

    monkeypatch.setattr(module, "_firecrawl_map", fake_map)

    with _session() as session:
        school = _school(session, 1, name="東京テスト専門学校")
        stats = module.discover_pdfs_for_corporation(session, "https://safe.example/", [school])

    assert calls == ["確認申請書 様式第2号 機関要件 情報公開", "情報公開 高等教育 修学支援"]
    assert stats == {"searched": 1, "matched": 0, "unmatched": 1, "errors": 0}


def test_discover_pdfs_for_corporation_rejects_unsafe_domain() -> None:
    with _session() as session:
        school = _school(session, 1, name="東京テスト専門学校")

        stats = module.discover_pdfs_for_corporation(session, "http://127.0.0.1/", [school])

    assert stats == {"searched": 0, "matched": 0, "unmatched": 0, "errors": 1}


def test_run_firecrawl_discovery_groups_active_schools_by_configured_corp(monkeypatch) -> None:
    monkeypatch.setattr(
        "eidp.scraper.url_discovery._load_corporation_domains",
        lambda: {"法人A": "https://safe.example/a/", "法人B": "https://safe.example/b/"},
    )
    seen: list[tuple[str, list[str]]] = []

    def fake_discover(session: Session, domain: str, schools: list[School]) -> dict[str, int]:
        seen.append((domain, [school.school_name for school in schools]))
        return {"searched": 1, "matched": len(schools), "unmatched": 0, "errors": 0}

    monkeypatch.setattr(module, "discover_pdfs_for_corporation", fake_discover)

    with _session() as session:
        _school(session, 1, name="A校", corp="法人A")
        inactive = _school(session, 2, name="休止校", corp="法人A")
        inactive.status = "closed"
        _school(session, 3, name="B校", corp="法人B")
        _school(session, 4, name="未設定法人", corp="法人C")
        session.commit()

        stats = module.run_firecrawl_discovery(session, batch_size=2)

    assert seen == [
        ("https://safe.example/a/", ["A校"]),
        ("https://safe.example/b/", ["B校"]),
    ]
    assert stats == {"corps_processed": 2, "schools_matched": 2, "schools_unmatched": 0}
