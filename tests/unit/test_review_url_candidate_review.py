"""Tests for the operator URL-candidate review helpers."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog, ReviewItem, School, SchoolSite
from eidp.review._pages.url_candidate_review import (
    approve_url_candidate,
    list_url_candidate_reviews,
    reject_url_candidate,
)
from eidp.scraper.school_url_persistence import REVIEW_ITEM_TYPE, REVIEW_PROPOSAL_SOURCE


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def _seed_school(session: Session) -> School:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京テスト専門学校",
        status="active",
    )
    session.add(school)
    session.flush()
    return school


def _seed_url_candidate(session: Session) -> ReviewItem:
    _seed_school(session)
    item = ReviewItem(
        id=10,
        item_type=REVIEW_ITEM_TYPE,
        reference_table="school",
        reference_id=1,
        status="pending",
        priority=2,
        confidence=0.62,
        proposal_source=REVIEW_PROPOSAL_SOURCE,
        evidence_url="https://www.test.ac.jp/",
        proposal_reason="Auto-suggested by scrapling_stealth; score below auto threshold.",
        proposal_value=json.dumps(
            {
                "url": "https://www.test.ac.jp/",
                "score": 5.2,
                "decision": "review",
                "breakdown": {"domain_tld": 3.0, "page_title_match": 1.0},
                "notes": ["title contains school name"],
                "alternates": [{"url": "https://alt.example.ac.jp/", "score": 4.1}],
            },
            ensure_ascii=False,
        ),
    )
    session.add(item)
    session.flush()
    return item


def test_list_url_candidate_reviews_parses_pending_items(session: Session) -> None:
    _seed_url_candidate(session)

    rows = list_url_candidate_reviews(session)

    assert len(rows) == 1
    row = rows[0]
    assert row.item_id == 10
    assert row.school_name == "東京テスト専門学校"
    assert row.url == "https://www.test.ac.jp"
    assert row.score == 5.2
    assert row.alternates == [{"url": "https://alt.example.ac.jp/", "score": 4.1}]


def test_approve_url_candidate_creates_school_site_and_audit(session: Session) -> None:
    _seed_url_candidate(session)

    outcome = approve_url_candidate(session, item_id=10, actor="operator")

    site = session.query(SchoolSite).one()
    item = session.get(ReviewItem, 10)
    audit = session.query(ManualActionLog).one()

    assert outcome.school_site_id == site.id
    assert site.school_id == 1
    assert site.url == "https://www.test.ac.jp"
    assert site.discovery_method == REVIEW_PROPOSAL_SOURCE
    assert site.url_type == "school"
    assert item is not None
    assert item.status == "resolved"
    assert item.resolution == "approved"
    assert item.resolved_value == "https://www.test.ac.jp"
    assert audit.action_type == "url_candidate_approved"
    assert audit.target_table == "school_site"
    assert audit.target_id == site.id


def test_reject_url_candidate_resolves_item_and_audits(session: Session) -> None:
    _seed_url_candidate(session)

    reject_url_candidate(session, item_id=10, notes="third-party directory", actor="operator")

    item = session.get(ReviewItem, 10)
    audit = session.query(ManualActionLog).one()

    assert session.query(SchoolSite).count() == 0
    assert item is not None
    assert item.status == "resolved"
    assert item.resolution == "rejected"
    assert item.notes == "third-party directory"
    assert audit.action_type == "url_candidate_rejected"
    assert audit.target_table == "review_item"
    assert audit.target_id == 10
