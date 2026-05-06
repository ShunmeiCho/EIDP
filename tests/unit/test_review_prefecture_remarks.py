from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from eidp.db.models import Base, ReviewItem, School
from eidp.review._pages.prefecture_remarks import (
    count_pending_prefecture_remark_reviews,
    list_prefecture_remark_reviews,
    parse_prefecture_remark_payload,
    prefecture_remark_tag_label,
    resolve_prefecture_remark_review,
)


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, school_id: int, *, school_type: str = "専門学校") -> None:
    session.add(School(
        id=school_id,
        school_code=f"S{school_id}",
        prefecture="千葉県",
        corporation_name=f"法人{school_id}",
        school_name=f"学校{school_id}",
        school_type=school_type,
        status="active",
    ))


def _review_item(session: Session, item_id: int, school_id: int, *, status: str = "pending") -> None:
    session.add(ReviewItem(
        id=item_id,
        item_type="prefecture_remark",
        reference_table="school",
        reference_id=school_id,
        status=status,
        priority=2,
        proposal_value=json.dumps(
            {"tags": ["new_accreditation", "name_change"], "remarks": "新規 / 名称変更"},
            ensure_ascii=False,
        ),
        proposal_source="prefecture_aggregator",
        evidence_url="https://pref.example/index.pdf",
    ))


def test_parse_prefecture_remark_payload_and_labels() -> None:
    tags, remarks = parse_prefecture_remark_payload(
        '{"tags":["new_accreditation","withdrawal"],"remarks":"新規"}'
    )

    assert tags == ("new_accreditation", "withdrawal")
    assert remarks == "新規"
    assert prefecture_remark_tag_label("withdrawal") == "辞退/取消/対象外"
    assert parse_prefecture_remark_payload("not-json") == ((), "not-json")


def test_list_prefecture_remark_reviews_filters_school_type_and_status() -> None:
    session = _session()
    try:
        _school(session, 1, school_type="専門学校")
        _school(session, 2, school_type="大学")
        _review_item(session, 11, 1)
        _review_item(session, 12, 2)
        _review_item(session, 13, 1, status="resolved")
        session.commit()

        rows = list_prefecture_remark_reviews(session, school_type="専門学校", status="pending")

        assert [row.item_id for row in rows] == [11]
        assert rows[0].tags == ("new_accreditation", "name_change")
        assert rows[0].remarks == "新規 / 名称変更"
        assert count_pending_prefecture_remark_reviews(session, school_type=None) == 2
        assert count_pending_prefecture_remark_reviews(session, school_type="専門学校") == 1
    finally:
        session.close()


def test_resolve_prefecture_remark_review_closes_pending_item() -> None:
    session = _session()
    try:
        _school(session, 1)
        _review_item(session, 11, 1)
        session.commit()

        assert resolve_prefecture_remark_review(
            session,
            item_id=11,
            resolution="approved",
            notes="確認済",
        ) is True
        session.commit()

        item = session.get(ReviewItem, 11)
        assert item is not None
        assert item.status == "resolved"
        assert item.resolution == "approved"
        assert item.notes == "確認済"
        assert item.resolved_at is not None
        assert resolve_prefecture_remark_review(session, item_id=11, resolution="approved") is False
    finally:
        session.close()
