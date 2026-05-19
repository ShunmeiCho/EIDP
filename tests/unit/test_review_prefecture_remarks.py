from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from eidp.db.models import Base, ManualActionLog, ReviewItem, School
from eidp.review._pages import prefecture_remarks
from eidp.review._pages.prefecture_remarks import (
    count_pending_prefecture_remark_reviews,
    list_prefecture_remark_reviews,
    load_prefecture_seed_coverage,
    parse_prefecture_remark_payload,
    prefecture_remark_tag_label,
    prefecture_seed_status_label,
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


def test_prefecture_seed_coverage_summarizes_automation_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prefecture_remarks, "SUPPORTED_PREFECTURE_PARSERS", frozenset({"tokyo"}))
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "\n".join([
            (
                "pref_key,pref_jp,schools_in_db,artifact_url,verified_status,has_url_col,"
                "has_hyperlink_annot,as_of_date,notes,supplemental_artifact_urls"
            ),
            "tokyo,東京都,314,https://pref.example/tokyo.pdf,url_found,yes,no,2026-04-01,URLs",
            "kyoto,京都府,46,unknown,todo,unknown,unknown,,needs check",
            (
                "akita,秋田県,unknown,https://pref.example/akita.pdf,url_found,no,yes,2025-08-29,"
                "links,https://pref.example/akita-old.pdf|https://pref.example/akita-extra.pdf"
            ),
        ])
        + "\n",
        encoding="utf-8",
    )

    summary, rows = load_prefecture_seed_coverage(seed)

    assert summary.total == 3
    assert summary.automatic_targets == 1
    assert summary.parser_supported == 1
    assert summary.needs_structure_review == 2
    assert summary.school_link_signal == 2
    assert summary.no_school_link_signal == 1
    assert summary.known_school_total == 360
    assert summary.automatic_target_schools == 314
    assert summary.structure_review_schools == 46
    assert summary.parser_unsupported_schools == 0
    assert summary.no_school_link_signal_schools == 46
    assert summary.unknown_school_rows == 1
    assert summary.supplemental_artifact_rows == 1
    assert [row.status for row in rows] == ["自動取込対象", "構造確認待ち", "parser未対応"]
    assert [row.schools_in_db for row in rows] == [314, 46, None]
    assert [row.supplemental_artifacts for row in rows] == [0, 0, 2]
    assert rows[0].school_link_signal is True
    assert rows[1].school_link_signal is False


def test_prefecture_seed_status_label() -> None:
    assert prefecture_seed_status_label(
        parser_supported=True,
        verified_status="url_found",
        artifact_url="https://pref.example/index.pdf",
    ) == "自動取込対象"
    assert prefecture_seed_status_label(
        parser_supported=False,
        verified_status="url_found",
        artifact_url="https://pref.example/index.pdf",
    ) == "parser未対応"
    assert prefecture_seed_status_label(
        parser_supported=False,
        verified_status="todo",
        artifact_url="unknown",
    ) == "構造確認待ち"


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

        audit = session.query(ManualActionLog).one()
        assert audit.action_type == "prefecture_remark_approved"
        assert audit.target_table == "review_item"
        assert audit.target_id == 11
        assert '"item_id": 11' in (audit.new_value or "")
        assert '"school_id": 1' in (audit.new_value or "")
        assert '"resolution": "approved"' in (audit.new_value or "")
        assert resolve_prefecture_remark_review(session, item_id=11, resolution="approved") is False
    finally:
        session.close()
