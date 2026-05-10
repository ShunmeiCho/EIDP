from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, ManualActionLog, ReviewItem, School
from eidp.review.app import (
    DETAIL_PAGES,
    PAGE_AUDIT_LOG,
    PAGE_SETTINGS,
    PAGE_URL_CANDIDATE_REVIEW,
    QUICK_PAGES,
    _approve_item,
    _approve_with_correction,
    _build_info_caption,
    _reject_item,
    _skip_item,
)


def test_build_info_caption_reads_packaged_commit(tmp_path):
    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "app": "EIDP",
                "built_at_utc": "2026-05-06T12:00:00+00:00",
                "git_commit": "1234567890abcdef1234567890abcdef12345678",
                "git_branch": "release/test",
                "git_dirty": "false",
            }
        ),
        encoding="utf-8",
    )

    caption = _build_info_caption(tmp_path)

    assert "build: 1234567" in caption
    assert "branch: release/test" in caption
    assert "built: 2026-05-06T12:00:00+00:00" in caption


def test_build_info_caption_marks_dirty_build(tmp_path):
    (tmp_path / "BUILD_INFO.json").write_text(
        json.dumps(
            {
                "app": "EIDP",
                "built_at_utc": "2026-05-06T12:00:00+00:00",
                "git_commit": "1234567890abcdef1234567890abcdef12345678",
                "git_branch": "release/test",
                "git_dirty": "true",
            }
        ),
        encoding="utf-8",
    )

    assert "build: 1234567 dirty" in _build_info_caption(tmp_path)


def test_build_info_caption_falls_back_for_source_checkout(tmp_path):
    assert _build_info_caption(tmp_path) == "build: source checkout"


def test_settings_is_visible_in_quick_navigation():
    quick_ids = [page_id for page_id, _label in QUICK_PAGES]
    detail_ids = [page_id for page_id, _label in DETAIL_PAGES]

    assert PAGE_SETTINGS in quick_ids
    assert PAGE_SETTINGS not in detail_ids
    assert PAGE_URL_CANDIDATE_REVIEW in detail_ids
    assert PAGE_AUDIT_LOG in detail_ids


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_school_code_review(session: Session) -> tuple[School, ReviewItem]:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京テスト専門学校",
        status="active",
    )
    item = ReviewItem(
        id=10,
        item_type="school_code",
        reference_table="school",
        reference_id=1,
        status="pending",
        priority=1,
        confidence=0.91,
        proposal_value=json.dumps(
            {
                "candidate_code": "H123456789012",
                "candidate_name": "東京テスト専門学校",
                "match_method": "exact",
            },
            ensure_ascii=False,
        ),
    )
    session.add_all([school, item])
    session.commit()
    return school, item


def _one_audit(session: Session) -> ManualActionLog:
    return session.query(ManualActionLog).one()


def test_school_code_approve_writes_manual_action_log() -> None:
    session = _session()
    try:
        school, item = _seed_school_code_review(session)

        _approve_item(session, item, school)

        audit = _one_audit(session)
        assert audit.action_type == "school_code_approved"
        assert audit.target_table == "school"
        assert audit.target_id == school.id
        assert json.loads(audit.new_value or "{}")["school_code"] == "H123456789012"
    finally:
        session.close()


def test_school_code_correction_writes_manual_action_log() -> None:
    session = _session()
    try:
        school, item = _seed_school_code_review(session)

        _approve_with_correction(session, item, school, "H999999999999")

        audit = _one_audit(session)
        assert audit.action_type == "school_code_corrected"
        assert audit.target_table == "school"
        assert audit.target_id == school.id
        assert json.loads(audit.new_value or "{}")["school_code"] == "H999999999999"
    finally:
        session.close()


def test_school_code_reject_writes_manual_action_log() -> None:
    session = _session()
    try:
        school, item = _seed_school_code_review(session)

        _reject_item(session, item, notes="wrong school")

        audit = _one_audit(session)
        assert audit.action_type == "school_code_rejected"
        assert audit.target_table == "review_item"
        assert audit.target_id == item.id
        assert audit.reason == "wrong school"
        assert json.loads(audit.new_value or "{}")["school_id"] == school.id
    finally:
        session.close()


def test_school_code_skip_writes_manual_action_log() -> None:
    session = _session()
    try:
        _school, item = _seed_school_code_review(session)

        _skip_item(session, item)

        audit = _one_audit(session)
        assert audit.action_type == "school_code_skipped"
        assert audit.target_table == "review_item"
        assert audit.target_id == item.id
        assert json.loads(audit.old_value or "{}")["priority"] == 1
        assert json.loads(audit.new_value or "{}")["priority"] == 3
    finally:
        session.close()
