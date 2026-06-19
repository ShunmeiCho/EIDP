"""Tests for src/eidp/scraper/school_url_pipeline.py."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog, ReviewItem, School, SchoolSite
from eidp.scraper.school_url_errors import ScraplingUnavailableError
from eidp.scraper.school_url_persistence import REVIEW_ITEM_TYPE, REVIEW_PROPOSAL_SOURCE
from eidp.scraper.school_url_pipeline import (
    SchoolUrlCrawlEvidence,
    _accumulate_outcome,
    _default_crawl_throttle,
    _EvidenceWriter,
    _school_website_queries_for_school,
    _schools_without_url,
    run_school_url_auto_crawl,
)
from eidp.scraper.school_website_crawl import FetchedPage, SchoolUrlDiscovery, SerpHit


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


class MissingScraplingPageFetcher:
    def fetch(self, url: str) -> FetchedPage:
        raise ScraplingUnavailableError(f"missing optional runtime for {url}")


class MissingRuntimeCrawler:
    def discover_for(self, **_kwargs: object) -> SchoolUrlDiscovery:
        raise ScraplingUnavailableError("scrapling missing after startup")


def _crawl_evidence(*, school_id: int = 1, decision: str = "auto") -> SchoolUrlCrawlEvidence:
    return SchoolUrlCrawlEvidence(
        school_id=school_id,
        school_name=f"学校{school_id}",
        prefecture="東京都",
        decision=decision,
        candidate_url=f"https://example.com/{school_id}/",
        score=0.91,
        outcome="registered",
        skipped_reason="",
        queries=[f"学校{school_id} 公式"],
        candidates=[],
        notes=[],
    )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_school(session: Session, *, school_id: int = 1, school_name: str = "東京デザイン専門学校") -> None:
    session.add(
        School(
            id=school_id,
            prefecture="東京都",
            corporation_name="学校法人東京デザイン",
            school_name=school_name,
            status="active",
        )
    )
    session.flush()


def test_school_website_queries_include_common_school_name_variants() -> None:
    school = School(
        id=41,
        prefecture="埼玉県",
        corporation_name="三幸学園",
        school_name="大宮ビューティ＆ブライダル専門学校",
        status="active",
    )

    queries = _school_website_queries_for_school(school)

    assert "大宮ビューティー＆ブライダル専門学校 公式サイト" in queries
    assert "三幸学園 大宮ビューティー＆ブライダル専門学校 公式" in queries


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
        assert site.url == "https://www.tokyo-design.ac.jp"
        assert site.discovery_method == "scrapling_stealth"
        assert log.action_type == "url_auto_discovery"
        assert evidence["decision"] == "auto"
        assert evidence["candidate_url"] == "https://www.tokyo-design.ac.jp/"
    finally:
        session.close()


def test_run_school_url_auto_crawl_dry_run_writes_no_rows(tmp_path: Path) -> None:
    session = _session()
    try:
        _seed_school(session)
        evidence_path = tmp_path / "dry-run.jsonl"

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            dry_run=True,
            evidence_path=evidence_path,
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )
        session.commit()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])

        assert stats["attempted"] == 1
        assert stats["dry_run_auto"] == 1
        assert session.query(SchoolSite).count() == 0
        assert session.query(ManualActionLog).count() == 0
        assert evidence["dry_run"] is True
        assert evidence["skipped_reason"] == "dry_run"
    finally:
        session.close()


class RejectOnlySerpFetcher:
    def search(self, query: str, *, max_results: int = 5) -> list[SerpHit]:  # noqa: ARG002
        return [
            SerpHit(
                url="https://unrelated.example/news/",
                title="Unrelated news",
                snippet="オープンキャンパス",
            )
        ]


def test_run_school_url_auto_crawl_evidence_records_rejected_candidates(tmp_path: Path) -> None:
    session = _session()
    try:
        _seed_school(session)
        evidence_path = tmp_path / "reject.jsonl"

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            evidence_path=evidence_path,
            serp_fetcher=RejectOnlySerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )

        evidence = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])

        assert stats["attempted"] == 1
        assert stats["manual_required_enqueued"] == 1
        assert stats["rejected"] == 0
        assert evidence["decision"] == "reject"
        assert evidence["candidate_url"] == ""
        assert evidence["queries"] == [
            "東京デザイン専門学校 公式サイト",
            "東京デザイン専門学校 公式",
            "東京デザイン専門学校 ホームページ",
            "学校法人東京デザイン 東京デザイン専門学校 公式",
            "東京デザイン専門学校 情報公開",
            "東京デザイン専門学校 高等教育 修学支援",
        ]
        assert evidence["candidates"] == [
            {
                "url": "https://unrelated.example/news/",
                "score": -2.0,
                "decision": "reject",
                "breakdown": {"low_value_path": -2.0},
                "notes": ["low_value_path"],
            }
        ]
    finally:
        session.close()


def test_evidence_writer_locks_each_jsonl_append(tmp_path: Path, monkeypatch) -> None:
    import eidp.scraper.school_url_pipeline as pipeline

    evidence_path = tmp_path / "school_url_crawl.jsonl"
    lock_calls: list[tuple[Path, str, bool, float | None]] = []

    @contextmanager
    def spy_acquire_lock(
        lock_path: Path,
        *,
        owner: str = "weekly_runner",
        blocking: bool = False,
        timeout: float | None = None,
    ):
        lock_calls.append((lock_path, owner, blocking, timeout))
        yield

    monkeypatch.setattr(pipeline, "acquire_lock", spy_acquire_lock, raising=False)

    writer = _EvidenceWriter(evidence_path)
    writer.write(_crawl_evidence(school_id=1))
    writer.write(_crawl_evidence(school_id=2, decision="review"))
    writer.close()

    assert lock_calls == [
        (evidence_path.with_suffix(".jsonl.lock"), "school_url_evidence_writer", True, 30.0),
        (evidence_path.with_suffix(".jsonl.lock"), "school_url_evidence_writer", True, 30.0),
    ]
    rows = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
    assert [row["school_id"] for row in rows] == [1, 2]
    assert [row["decision"] for row in rows] == ["auto", "review"]


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


def test_run_school_url_auto_crawl_stops_when_page_runtime_disappears() -> None:
    session = _session()
    try:
        _seed_school(session)

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=MissingScraplingPageFetcher(),
        )

        assert stats["attempted"] == 0
        assert stats["unavailable"] == 1
        assert stats["auto_registered"] == 0
        assert session.query(SchoolSite).count() == 0
    finally:
        session.close()


def test_run_school_url_auto_crawl_does_not_count_unavailable_school_as_attempted(monkeypatch) -> None:
    import eidp.scraper.school_url_pipeline as pipeline

    session = _session()
    try:
        _seed_school(session)
        monkeypatch.setattr(pipeline, "SchoolUrlCrawler", lambda **_kwargs: MissingRuntimeCrawler())

        stats = run_school_url_auto_crawl(
            session,
            batch_size=1,
            serp_fetcher=FakeSerpFetcher(),
            page_fetcher=FakePageFetcher(),
        )

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


def test_default_crawl_throttle_uses_school_url_specific_settings(monkeypatch) -> None:
    import eidp.scraper.school_url_pipeline as pipeline

    monkeypatch.setattr(pipeline.settings, "school_url_crawl_min_seconds_per_domain", 5.0)
    monkeypatch.setattr(pipeline.settings, "school_url_crawl_min_jitter", 0.5)
    monkeypatch.setattr(pipeline.settings, "school_url_crawl_max_jitter", 1.5)

    throttle = _default_crawl_throttle()

    assert throttle.min_seconds_per_domain == 5.0
    assert throttle.min_jitter == 0.5
    assert throttle.max_jitter == 1.5


def test_default_crawl_throttle_clamps_reversed_jitter_settings(monkeypatch) -> None:
    import eidp.scraper.school_url_pipeline as pipeline

    monkeypatch.setattr(pipeline.settings, "school_url_crawl_min_seconds_per_domain", -1.0)
    monkeypatch.setattr(pipeline.settings, "school_url_crawl_min_jitter", 3.0)
    monkeypatch.setattr(pipeline.settings, "school_url_crawl_max_jitter", 1.0)

    throttle = _default_crawl_throttle()

    assert throttle.min_seconds_per_domain == 0.0
    assert throttle.min_jitter == 3.0
    assert throttle.max_jitter == 3.0


def test_schools_without_url_uses_outer_join_not_subquery() -> None:
    session = _session()
    statements: list[str] = []
    try:
        _seed_school(session, school_id=1)
        _seed_school(session, school_id=2, school_name="東京デザイン第二専門学校")
        session.add(
            SchoolSite(
                school_id=1,
                url="https://www.tokyo-design.ac.jp/",
                discovery_method="operator_manual",
            )
        )
        session.commit()

        def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ARG001
            statements.append(statement)

        assert session.bind is not None
        event.listen(session.bind, "before_cursor_execute", capture_statement)
        try:
            schools = _schools_without_url(session, batch_size=10)
        finally:
            event.remove(session.bind, "before_cursor_execute", capture_statement)

        assert [school.id for school in schools] == [2]
        select_sql = " ".join(statements)
        assert "LEFT OUTER JOIN" in select_sql.upper()
        assert "NOT IN" not in select_sql.upper()
    finally:
        session.close()


def test_schools_without_url_skips_pending_url_candidate_review_items() -> None:
    session = _session()
    try:
        _seed_school(session, school_id=1)
        _seed_school(session, school_id=2, school_name="東京デザイン第二専門学校")
        session.add(
            ReviewItem(
                item_type=REVIEW_ITEM_TYPE,
                reference_table="school",
                reference_id=1,
                status="pending",
                proposal_source=REVIEW_PROPOSAL_SOURCE,
                proposal_value='{"manual_required": true}',
            )
        )
        session.commit()

        schools = _schools_without_url(session, batch_size=10)

        assert [school.id for school in schools] == [2]
    finally:
        session.close()


def test_accumulate_outcome_separates_auto_without_best_candidate() -> None:
    stats = {
        "auto_registered": 0,
        "auto_existing": 0,
        "auto_no_candidate": 0,
        "review_enqueued": 0,
        "review_existing": 0,
        "dry_run_auto": 0,
        "dry_run_review": 0,
        "dry_run_manual_required": 0,
        "rejected": 0,
        "no_candidates": 0,
        "circuit_open": 0,
        "manual_required_enqueued": 0,
        "manual_required_existing": 0,
    }

    _accumulate_outcome(
        stats,
        discovery_decision="auto",
        skipped_reason="auto_without_best_candidate",
    )

    assert stats["auto_no_candidate"] == 1
    assert stats["auto_existing"] == 0


def test_accumulate_outcome_reports_manual_required_queue() -> None:
    stats = {
        "auto_registered": 0,
        "auto_existing": 0,
        "auto_no_candidate": 0,
        "review_enqueued": 0,
        "review_existing": 0,
        "review_no_candidate": 0,
        "dry_run_auto": 0,
        "dry_run_review": 0,
        "dry_run_manual_required": 0,
        "rejected": 0,
        "no_candidates": 0,
        "circuit_open": 0,
        "manual_required_enqueued": 0,
        "manual_required_existing": 0,
    }

    _accumulate_outcome(stats, discovery_decision="reject", skipped_reason=None)
    _accumulate_outcome(
        stats,
        discovery_decision="no_candidates",
        skipped_reason="manual_required_already_pending",
    )

    assert stats["manual_required_enqueued"] == 1
    assert stats["manual_required_existing"] == 1
    assert stats["rejected"] == 0
    assert stats["no_candidates"] == 0
