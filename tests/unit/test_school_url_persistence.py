"""Tests for src/eidp/scraper/school_url_persistence.py."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog, ReviewItem, School, SchoolSite
from eidp.scraper.school_url_persistence import (
    ACTION_MANUAL_REQUIRED,
    AUTO_CONFIDENCE,
    DISCOVERY_METHOD,
    REVIEW_ITEM_TYPE,
    REVIEW_PROPOSAL_SOURCE,
    persist_discovery,
)
from eidp.scraper.school_website_crawl import SchoolUrlDiscovery
from eidp.scraper.url_scoring import UrlScore


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def _seed_school(
    session: Session, *, school_id: int = 1, name: str = "テスト専門学校",
) -> School:
    school = School(
        id=school_id,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name=name,
        status="active",
    )
    session.add(school)
    session.flush()
    return school


def _make_discovery(
    *,
    school_id: int = 1,
    school_name: str = "テスト専門学校",
    decision: str = "auto",
    best_url: str = "https://www.test.ac.jp/",
    best_score: float = 8.0,
    best_breakdown: dict | None = None,
    extras: list[UrlScore] | None = None,
) -> SchoolUrlDiscovery:
    breakdown = best_breakdown or {
        "domain_tld": 3.0, "domain_name_match": 2.0,
        "page_title_match": 2.0, "disclosure_keyword": 1.0,
    }
    inner_decision = decision if decision in {"auto", "review"} else "review"
    best = UrlScore(
        candidate_url=best_url,
        score=best_score,
        decision=inner_decision,
        breakdown=breakdown,
        notes=("name_token=test",),
    )
    candidates = (best, *(extras or ()))
    return SchoolUrlDiscovery(
        school_id=school_id,
        school_name=school_name,
        queries=("テスト専門学校 公式",),
        candidates=candidates,
        best=best,
        decision=decision,
    )


def test_auto_inserts_school_site_with_expected_metadata(session: Session):
    _seed_school(session)
    discovery = _make_discovery(decision="auto")
    outcome = persist_discovery(session, discovery)
    session.commit()

    site = session.query(SchoolSite).filter(SchoolSite.school_id == 1).one()
    assert site.url == "https://www.test.ac.jp"
    assert site.url_type == "school"
    assert site.discovery_method == DISCOVERY_METHOD
    assert float(site.confidence) == AUTO_CONFIDENCE
    assert site.verified is False

    assert outcome.decision == "auto"
    assert outcome.school_site_id == site.id
    assert outcome.audit_log_id is not None


def test_auto_persists_same_host_disclosure_candidate(session: Session):
    _seed_school(session)
    discovery = _make_discovery(
        decision="auto",
        best_url="https://www.test.ac.jp/",
        extras=[
            UrlScore(
                candidate_url="https://www.test.ac.jp/disclosure/",
                score=5.0,
                decision="review",
                breakdown={"domain_tld": 3.0, "page_title_match": 2.0},
                notes=(),
            ),
            UrlScore(
                candidate_url="https://www.example-u.ac.jp/disclosure/",
                score=5.0,
                decision="review",
                breakdown={"domain_tld": 3.0, "disclosure_keyword": 1.0},
                notes=(),
            ),
        ],
    )

    persist_discovery(session, discovery)
    session.commit()

    sites = session.query(SchoolSite).order_by(SchoolSite.url.asc()).all()
    audits = session.query(ManualActionLog).order_by(ManualActionLog.id.asc()).all()

    assert [(site.url, site.url_type) for site in sites] == [
        ("https://www.test.ac.jp", "school"),
        ("https://www.test.ac.jp/disclosure", "disclosure"),
    ]
    assert [audit.action_type for audit in audits] == ["url_auto_discovery", "url_auto_discovery"]


def test_auto_writes_manual_action_log_audit(session: Session):
    _seed_school(session)
    discovery = _make_discovery(decision="auto")
    persist_discovery(session, discovery)
    session.commit()

    log = session.query(ManualActionLog).one()
    assert log.action_type == "url_auto_discovery"
    assert log.target_table == "school_site"
    assert log.actor == DISCOVERY_METHOD
    payload = json.loads(log.new_value)
    assert payload["url"] == "https://www.test.ac.jp"
    assert payload["score"] == pytest.approx(8.0)


def test_auto_is_idempotent_on_existing_school_site(session: Session):
    _seed_school(session)
    existing = SchoolSite(
        school_id=1,
        url="https://www.test.ac.jp/",
        discovery_method="operator_manual",
    )
    session.add(existing)
    session.flush()

    discovery = _make_discovery(decision="auto")
    outcome = persist_discovery(session, discovery)
    session.commit()

    sites = session.query(SchoolSite).filter(SchoolSite.school_id == 1).all()
    assert len(sites) == 1
    assert outcome.skipped_reason == "school_site_already_exists"
    assert outcome.school_site_id == existing.id


def test_auto_normalizes_url_before_idempotency_check(session: Session):
    _seed_school(session)
    existing = SchoolSite(
        school_id=1,
        url="https://www.test.ac.jp",
        discovery_method="operator_manual",
    )
    session.add(existing)
    session.flush()

    discovery = _make_discovery(decision="auto", best_url="https://www.test.ac.jp/#top")
    outcome = persist_discovery(session, discovery)
    session.commit()

    sites = session.query(SchoolSite).filter(SchoolSite.school_id == 1).all()
    assert len(sites) == 1
    assert outcome.skipped_reason == "school_site_already_exists"
    assert outcome.school_site_id == existing.id


def test_auto_normalizes_duplicate_path_slashes_before_idempotency_check(session: Session):
    _seed_school(session)
    existing = SchoolSite(
        school_id=1,
        url="https://www.test.ac.jp/foo/bar",
        discovery_method="operator_manual",
    )
    session.add(existing)
    session.flush()

    discovery = _make_discovery(decision="auto", best_url="https://www.test.ac.jp/foo//bar/#top")
    outcome = persist_discovery(session, discovery)
    session.commit()

    sites = session.query(SchoolSite).filter(SchoolSite.school_id == 1).all()
    assert len(sites) == 1
    assert outcome.skipped_reason == "school_site_already_exists"
    assert outcome.school_site_id == existing.id


def test_review_inserts_review_item_with_proposal_payload(session: Session):
    _seed_school(session)
    discovery = _make_discovery(
        decision="review",
        best_url="https://design-tokyo.jp/",
        best_score=4.5,
        best_breakdown={
            "domain_tld": 1.0, "domain_name_match": 2.0,
            "prefecture_in_url": 1.0, "official_word": 0.5,
        },
    )
    outcome = persist_discovery(session, discovery)
    session.commit()

    item = session.query(ReviewItem).one()
    assert item.item_type == REVIEW_ITEM_TYPE
    assert item.reference_table == "school"
    assert item.reference_id == 1
    assert item.status == "pending"
    assert item.proposal_source == REVIEW_PROPOSAL_SOURCE
    assert item.evidence_url == "https://design-tokyo.jp"
    payload = json.loads(item.proposal_value)
    assert payload["url"] == "https://design-tokyo.jp"
    assert payload["score"] == pytest.approx(4.5)
    assert "breakdown" in payload
    assert payload["alternates"] == []

    assert outcome.decision == "review"
    assert outcome.review_item_id == item.id
    assert outcome.audit_log_id is not None


def test_review_is_idempotent_on_pending_review_item(session: Session):
    _seed_school(session)
    discovery = _make_discovery(
        decision="review", best_url="https://design-tokyo.jp/", best_score=4.5,
    )
    persist_discovery(session, discovery)
    session.commit()

    outcome2 = persist_discovery(session, discovery)
    session.commit()

    items = session.query(ReviewItem).all()
    assert len(items) == 1
    assert outcome2.skipped_reason == "review_item_already_pending"
    assert outcome2.review_item_id == items[0].id


def test_review_normalizes_url_before_dedup(session: Session):
    _seed_school(session)
    persist_discovery(session, _make_discovery(
        decision="review", best_url="https://design-tokyo.jp/#top", best_score=4.5,
    ))
    session.commit()

    outcome2 = persist_discovery(session, _make_discovery(
        decision="review", best_url="https://design-tokyo.jp/", best_score=4.5,
    ))
    session.commit()

    items = session.query(ReviewItem).all()
    assert len(items) == 1
    assert items[0].evidence_url == "https://design-tokyo.jp"
    assert outcome2.skipped_reason == "review_item_already_pending"


def test_review_re_inserts_after_resolution(session: Session):
    _seed_school(session)
    discovery = _make_discovery(
        decision="review", best_url="https://design-tokyo.jp/", best_score=4.5,
    )
    persist_discovery(session, discovery)
    session.commit()

    item = session.query(ReviewItem).one()
    item.status = "rejected"
    session.commit()

    outcome2 = persist_discovery(session, discovery)
    session.commit()

    items = session.query(ReviewItem).all()
    assert len(items) == 2
    assert outcome2.skipped_reason is None
    assert outcome2.review_item_id != item.id


def test_review_payload_includes_alternates(session: Session):
    _seed_school(session)
    extras = [
        UrlScore(
            candidate_url=f"https://alt{i}.example.com/",
            score=2.0,
            decision="reject",
            breakdown={},
            notes=(),
        )
        for i in range(3)
    ]
    discovery = _make_discovery(
        decision="review",
        best_url="https://design-tokyo.jp/",
        best_score=4.0,
        extras=extras,
    )
    persist_discovery(session, discovery)
    session.commit()

    item = session.query(ReviewItem).one()
    payload = json.loads(item.proposal_value)
    assert len(payload["alternates"]) == 3
    assert payload["alternates"][0]["url"].startswith("https://alt")


def test_circuit_open_writes_nothing(session: Session):
    _seed_school(session)
    discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("q",),
        candidates=(),
        best=None,
        decision="circuit_open",
    )
    outcome = persist_discovery(session, discovery)
    session.commit()

    assert session.query(SchoolSite).count() == 0
    assert session.query(ReviewItem).count() == 0
    assert session.query(ManualActionLog).count() == 0
    assert outcome.decision == "circuit_open"
    assert outcome.skipped_reason == "non_actionable:circuit_open"


@pytest.mark.parametrize("decision", ["reject", "no_candidates"])
def test_manual_required_decisions_enqueue_review_item(session: Session, decision: str):
    _seed_school(session)
    discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("テスト専門学校 公式",),
        candidates=(
            UrlScore(
                candidate_url="https://third-party.example/school",
                score=-5.0,
                decision="reject",
                breakdown={"third_party_directory": -5.0},
                notes=("blacklisted_third_party_directory",),
            ),
        ),
        best=None,
        decision=decision,
    )

    outcome = persist_discovery(session, discovery)
    session.commit()

    assert session.query(SchoolSite).count() == 0
    item = session.query(ReviewItem).one()
    audit = session.query(ManualActionLog).one()
    payload = json.loads(item.proposal_value)

    assert item.item_type == REVIEW_ITEM_TYPE
    assert item.reference_table == "school"
    assert item.reference_id == 1
    assert item.status == "pending"
    assert item.proposal_source == REVIEW_PROPOSAL_SOURCE
    assert item.evidence_url is None
    assert payload["url"] == ""
    assert payload["decision"] == decision
    assert payload["manual_required"] is True
    assert payload["queries"] == ["テスト専門学校 公式"]
    assert payload["alternates"][0]["url"] == "https://third-party.example/school"
    assert outcome.review_item_id == item.id
    assert audit.action_type == ACTION_MANUAL_REQUIRED


def test_manual_required_review_item_is_idempotent(session: Session):
    _seed_school(session)
    discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("テスト専門学校 公式",),
        candidates=(),
        best=None,
        decision="no_candidates",
    )

    first = persist_discovery(session, discovery)
    session.commit()
    second = persist_discovery(session, discovery)
    session.commit()

    assert session.query(ReviewItem).count() == 1
    assert first.review_item_id == second.review_item_id
    assert second.skipped_reason == "manual_required_already_pending"


def test_manual_required_reuses_existing_pending_url_candidate(session: Session):
    _seed_school(session)
    review_discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("テスト専門学校 公式",),
        candidates=(
            UrlScore(
                candidate_url="https://example.ac.jp/",
                score=5.0,
                decision="review",
                breakdown={"domain_tld": 3.0},
                notes=(),
            ),
        ),
        best=UrlScore(
            candidate_url="https://example.ac.jp/",
            score=5.0,
            decision="review",
            breakdown={"domain_tld": 3.0},
            notes=(),
        ),
        decision="review",
    )
    manual_discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("テスト専門学校 情報公開",),
        candidates=(),
        best=None,
        decision="no_candidates",
    )

    review = persist_discovery(session, review_discovery)
    session.commit()
    manual = persist_discovery(session, manual_discovery)
    session.commit()

    assert session.query(ReviewItem).count() == 1
    assert manual.review_item_id == review.review_item_id
    assert manual.skipped_reason == "manual_required_already_pending"


def test_auto_without_best_is_skipped_safely(session: Session):
    _seed_school(session)
    discovery = SchoolUrlDiscovery(
        school_id=1,
        school_name="テスト専門学校",
        queries=("q",),
        candidates=(),
        best=None,
        decision="auto",
    )
    outcome = persist_discovery(session, discovery)
    session.commit()
    assert outcome.skipped_reason == "auto_without_best_candidate"
    assert session.query(SchoolSite).count() == 0
