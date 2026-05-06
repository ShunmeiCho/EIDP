from __future__ import annotations

import json
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


def test_search_and_discover_registers_best_result(tmp_path: Path, monkeypatch) -> None:
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

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        site = session.query(SchoolSite).one()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://example.edu/disclosure/"
        assert site.discovery_method == "web_search"
        assert site.confidence > 0.9
        assert evidence["school_id"] == 1
        assert evidence["query"] == "日本語専門学校 情報公開 高等教育 修学支援"
        assert evidence["result_url"] == "https://example.edu/disclosure/"
        assert evidence["decision"] == "accepted"
        assert evidence["reason"] == "registered_school_site"
    finally:
        session.close()


def test_search_and_discover_rejects_low_confidence_results(tmp_path: Path, monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        queries: list[str] = []

        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            self.queries.append(query)
            return [
                SearchResult(
                    title="一般的なお知らせ",
                    url="https://unrelated.example/news/",
                    description="学校とは無関係のページ",
                )
            ]

    provider = FakeProvider()

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: provider)
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
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        evidence_rows = [
            json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()
        ]

        assert stats == {"searched": 1, "found": 0, "no_result": 1, "errors": 0}
        assert session.query(SchoolSite).count() == 0
        assert provider.queries == url_discovery.search_queries_for_school(session.get(School, 1))
        assert len(evidence_rows) == len(provider.queries)
        assert {row["decision"] for row in evidence_rows} == {"rejected"}
        assert {row["reason"] for row in evidence_rows} == {"low_confidence"}
        assert all(row["result_url"] == "https://unrelated.example/news/" for row in evidence_rows)
    finally:
        session.close()


def test_search_and_discover_accepts_corporation_description_match(monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="情報公開",
                    url="https://corp.example/disclosure/",
                    description="学校法人テストが公開する高等教育の修学支援新制度",
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
                school_name="東京デザイン学院",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.search_and_discover(session, batch_size=1)
        site = session.query(SchoolSite).one()

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://corp.example/disclosure/"
        assert site.confidence >= url_discovery.SEARCH_RESULT_MIN_CONFIDENCE
    finally:
        session.close()


def test_search_queries_use_university_terms_for_universities() -> None:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="公立大学法人テスト",
        school_name="東京都立大学",
        school_type="大学",
        status="active",
    )

    queries = url_discovery.search_queries_for_school(school)

    assert "東京都立大学 情報公開 高等教育 修学支援" in queries
    assert "東京都立大学 確認申請書 様式第2号" in queries
    assert "公立大学法人テスト 東京都立大学 情報公開" in queries
    assert all("専門学校" not in query for query in queries)
    assert queries[-1] == "東京都立大学 公式"


def test_search_queries_keep_vocational_homepage_terms_for_senmon() -> None:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京デザイン学院",
        school_type="専門学校",
        status="active",
    )

    queries = url_discovery.search_queries_for_school(school)

    assert "東京デザイン学院 専門学校" in queries
    assert "学校法人テスト 東京デザイン学院 情報公開" in queries


def test_search_queries_support_junior_college_and_kosen_terms() -> None:
    junior_college = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京短期カレッジ",
        school_type="短期大学",
        status="active",
    )
    kosen = School(
        id=2,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京工業高専",
        school_type="高等専門学校",
        status="active",
    )

    assert "東京短期カレッジ 短期大学" in url_discovery.search_queries_for_school(junior_college)
    assert "東京工業高専 高等専門学校" in url_discovery.search_queries_for_school(kosen)
