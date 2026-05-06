from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from eidp.config import settings
from eidp.db.models import Base, School, SchoolSite
from eidp.scraper import url_discovery
from eidp.scraper.search_provider import SearchResult


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_import_seed_urls_reads_utf8_sig_csv(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "discovered-urls-50.csv"
    csv_path.write_text(
        "\ufeffprefecture,corporation,school_name,url_candidate_1,url_type,confidence,http_status\n"
        "東京都,学校法人テスト,日本語専門学校,https://example.edu/disclosure/,disclosure_page,0.9,200\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.import_seed_urls(session, csv_path)
        site = session.query(SchoolSite).one()

        assert stats == {"imported": 1, "skipped_no_school": 0, "skipped_existing": 0}
        assert site.url == "https://example.edu/disclosure/"
        assert site.discovery_method == "seed_csv"
    finally:
        session.close()


def test_load_corporation_domains_reads_utf8_sig_csv(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "corporation_domains.csv").write_text(
        "\ufeffcorporation_name,domain_url,notes\n"
        "学校法人テスト,https://corp.example,日本語メモ\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "data_dir", data_dir)

    domains = url_discovery._load_corporation_domains()

    assert domains == {"学校法人テスト": "https://corp.example"}


def test_search_and_discover_registers_best_result(monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="日本語専門学校 情報公開",
                    url="https://example.edu/disclosure/",
                    description="高等教育の修学支援新制度",
                )
            ]

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: FakeProvider())
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.search_and_discover(session, batch_size=1)
        site = session.query(SchoolSite).one()

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://example.edu/disclosure/"
        assert site.discovery_method == "web_search"
        assert site.confidence > 0.9
    finally:
        session.close()
