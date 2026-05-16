"""Tests for the operator URL-candidate review helpers."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.locking import acquire_lock
from eidp.db.models import Base, ManualActionLog, ReviewItem, School, SchoolSite
from eidp.review._pages.url_candidate_review import (
    UrlCandidateActionOutcome,
    action_warning_message,
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


def _seed_manual_required_url_candidate(session: Session) -> ReviewItem:
    _seed_school(session)
    item = ReviewItem(
        id=11,
        item_type=REVIEW_ITEM_TYPE,
        reference_table="school",
        reference_id=1,
        status="pending",
        priority=3,
        confidence=0.0,
        proposal_source=REVIEW_PROPOSAL_SOURCE,
        evidence_url=None,
        proposal_reason="Manual URL required after scrapling_stealth returned no_candidates.",
        proposal_value=json.dumps(
            {
                "url": "",
                "score": 0.0,
                "decision": "no_candidates",
                "manual_required": True,
                "queries": ["東京テスト専門学校 公式"],
                "alternates": [],
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


def test_list_url_candidate_reviews_includes_manual_required_items(session: Session) -> None:
    _seed_manual_required_url_candidate(session)

    rows = list_url_candidate_reviews(session)

    assert len(rows) == 1
    row = rows[0]
    assert row.item_id == 11
    assert row.url == ""
    assert row.manual_required is True
    assert row.decision == "no_candidates"


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


def test_approve_url_candidate_can_store_disclosure_url_type(session: Session) -> None:
    _seed_url_candidate(session)

    approve_url_candidate(session, item_id=10, url_type="disclosure", actor="operator")

    site = session.query(SchoolSite).one()
    audit = session.query(ManualActionLog).one()

    assert site.url_type == "disclosure"
    assert json.loads(audit.new_value)["url_type"] == "disclosure"


def test_approve_url_candidate_refuses_when_weekly_lock_is_busy(session: Session, tmp_path) -> None:
    _seed_url_candidate(session)
    lock_path = tmp_path / "data" / ".lock"

    with acquire_lock(lock_path, owner="weekly_runner"):
        outcome = approve_url_candidate(session, item_id=10, actor="operator", lock_path=lock_path)

    item = session.get(ReviewItem, 10)
    assert outcome.skipped_reason == "lock_busy"
    assert session.query(SchoolSite).count() == 0
    assert session.query(ManualActionLog).count() == 0
    assert item is not None
    assert item.status == "pending"


def test_approve_manual_required_candidate_requires_operator_url(session: Session) -> None:
    _seed_manual_required_url_candidate(session)

    missing = approve_url_candidate(session, item_id=11, actor="operator")
    approved = approve_url_candidate(
        session,
        item_id=11,
        url_override="https://manual.example.ac.jp/",
        actor="operator",
    )

    site = session.query(SchoolSite).one()
    item = session.get(ReviewItem, 11)

    assert missing.skipped_reason == "missing_url"
    assert approved.decision == "approved"
    assert site.url == "https://manual.example.ac.jp"
    assert item is not None
    assert item.status == "resolved"
    assert item.resolved_value == "https://manual.example.ac.jp"


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


def test_reject_url_candidate_refuses_when_weekly_lock_is_busy(session: Session, tmp_path) -> None:
    _seed_url_candidate(session)
    lock_path = tmp_path / "data" / ".lock"

    with acquire_lock(lock_path, owner="weekly_runner"):
        outcome = reject_url_candidate(session, item_id=10, notes="busy", actor="operator", lock_path=lock_path)

    item = session.get(ReviewItem, 10)
    assert outcome.skipped_reason == "lock_busy"
    assert session.query(ManualActionLog).count() == 0
    assert item is not None
    assert item.status == "pending"


def test_action_warning_message_surfaces_lock_busy() -> None:
    message = action_warning_message(
        UrlCandidateActionOutcome(item_id=10, decision="missing", skipped_reason="lock_busy")
    )

    assert message == "週次処理中です。完了後にもう一度実行してください。"


def test_action_warning_message_surfaces_other_skip_reasons() -> None:
    message = action_warning_message(
        UrlCandidateActionOutcome(item_id=10, decision="missing", skipped_reason="missing_url")
    )

    assert message == "URL候補を更新できませんでした: missing_url"
