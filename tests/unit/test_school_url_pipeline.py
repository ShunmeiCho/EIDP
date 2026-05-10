"""Tests for src/eidp/scraper/school_url_pipeline.py."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog, School, SchoolSite
from eidp.scraper.school_url_pipeline import run_school_url_auto_crawl
from eidp.scraper.school_website_crawl import FetchedPage, SerpHit


class FakeSerpFetcher:
    def search(self, query: str, *, max_results: int = 5) -> list[SerpHit]:  # noqa: ARG002
        return [
            SerpHit(
                url="https://www.tokyo-design.ac.jp/",
                title="東京デザイン専門学校",
                snippet="公式サイト",
            )
        ]


class FakePageFetcher:
    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(
            url=url,
            status_code=200,
            title="東京デザイン専門学校 公式サイト",
            body_excerpt="情報公開 高等教育 修学支援 機関要件",
        )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_school(session: Session, *, school_id: int = 1) -> None:
    session.add(
        School(
            id=school_id,
            prefecture="東京都",
            corporation_name="学校法人東京デザイン",
            school_name="東京デザイン専門学校",
            status="active",
        )
    )
    session.flush()


def test_run_school_url_auto_crawl_persists_auto_result(tmp_path: Path) -> None:
    session = _session()
    try:
        _seed_school(session)
        evidence_path = tmp_path / "school_url_crawl.jsonl"

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            evidence_path=evidence_path,
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )
        session.commit()

        site = session.query(SchoolSite).one()
        log = session.query(ManualActionLog).one()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])

        assert stats["attempted"] == 1
        assert stats["auto_registered"] == 1
        assert site.url == "https://www.tokyo-design.ac.jp/"
        assert site.discovery_method == "scrapling_stealth"
        assert log.action_type == "url_auto_discovery"
        assert evidence["decision"] == "auto"
        assert evidence["candidate_url"] == "https://www.tokyo-design.ac.jp/"
    finally:
        session.close()


def test_run_school_url_auto_crawl_dry_run_writes_no_rows() -> None:
    session = _session()
    try:
        _seed_school(session)

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            dry_run=True,
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )
        session.commit()

        assert stats["attempted"] == 1
        assert stats["dry_run_auto"] == 1
        assert session.query(SchoolSite).count() == 0
        assert session.query(ManualActionLog).count() == 0
    finally:
        session.close()


def test_run_school_url_auto_crawl_skips_when_scrapling_missing(monkeypatch) -> None:
    import eidp.scraper.school_url_pipeline as pipeline

    session = _session()
    try:
        _seed_school(session)
        monkeypatch.setattr(pipeline, "scrapling_available", lambda: False)

        stats = run_school_url_auto_crawl(session, batch_size=1)

        assert stats["attempted"] == 0
        assert stats["unavailable"] == 1
    finally:
        session.close()


def test_run_school_url_auto_crawl_honors_prefecture_filter() -> None:
    session = _session()
    try:
        _seed_school(session)

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            prefecture="大阪府",
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )

        assert stats["attempted"] == 0
    finally:
        session.close()

