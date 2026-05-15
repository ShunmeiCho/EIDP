import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import ReviewItem, School, SchoolYearStatus
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.matcher.reconciler import ReconcileCandidate, ReconcileReport
from eidp.review import populate


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'review_populate.sqlite3'}", future=True)
    bootstrap_sqlite(engine)
    return Session(engine)


def _school(session: Session, school_id: int, name: str) -> School:
    school = School(
        id=school_id,
        prefecture="東京都",
        corporation_name=f"法人{school_id}",
        school_name=name,
        school_type="専門学校",
        status="active",
        school_code=None,
    )
    session.add(school)
    return school


def _candidate(school_id: int, *, confidence: float) -> ReconcileCandidate:
    return ReconcileCandidate(
        school_id=school_id,
        school_name=f"学校{school_id}",
        prefecture="東京都",
        corporation_name=f"法人{school_id}",
        candidate_code=f"C{school_id:04d}",
        candidate_name=f"候補{school_id}",
        match_method="name_containment",
        confidence=confidence,
    )


def test_populate_review_items_creates_candidate_and_no_candidate_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_reconcile(session: Session, data_dir: Path) -> ReconcileReport:
        return ReconcileReport(needs_manual=[_candidate(1, confidence=0.92)])

    monkeypatch.setattr(populate, "reconcile", fake_reconcile)

    with _session(tmp_path) as session:
        _school(session, 1, "候補あり")
        _school(session, 2, "候補なし")
        session.commit()

        stats = populate.populate_review_items(session, tmp_path)
        session.commit()

        rows = session.query(ReviewItem).order_by(ReviewItem.reference_id).all()

    assert stats == {"created": 2, "skipped_existing": 0, "skipped_excluded": 0, "total_unresolved": 2}
    assert [(row.reference_id, row.priority, row.proposal_source) for row in rows] == [
        (1, 2, "reconciler"),
        (2, 8, "reconciler"),
    ]
    assert rows[0].proposal_value is not None
    assert json.loads(rows[0].proposal_value) == {
        "candidate_code": "C0001",
        "candidate_name": "候補1",
        "match_method": "name_containment",
    }
    assert "score=0.92" in (rows[0].proposal_reason or "")
    assert rows[1].proposal_value is None
    assert "No fuzzy match found" in (rows[1].proposal_reason or "")


def test_populate_review_items_skips_existing_pending_and_current_excluded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        populate,
        "reconcile",
        lambda session, data_dir: ReconcileReport(needs_manual=[_candidate(1, confidence=0.71)]),
    )

    with _session(tmp_path) as session:
        _school(session, 1, "既存レビュー")
        _school(session, 2, "除外校")
        _school(session, 3, "新規レビュー")
        session.flush()
        session.add(
            ReviewItem(
                item_type="school_code",
                reference_id=1,
                reference_table="school",
                status="pending",
            )
        )
        session.add(
            SchoolYearStatus(
                school_id=2,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                status="excluded",
                excluded_reason="閉校",
            )
        )
        session.commit()

        stats = populate.populate_review_items(session, tmp_path)
        session.commit()

        rows = (
            session.query(ReviewItem)
            .filter(ReviewItem.reference_table == "school", ReviewItem.item_type == "school_code")
            .order_by(ReviewItem.reference_id)
            .all()
        )

    assert stats == {"created": 1, "skipped_existing": 1, "skipped_excluded": 1, "total_unresolved": 2}
    assert [row.reference_id for row in rows] == [1, 3]
    assert rows[1].priority == 8


def test_get_review_stats_counts_school_code_resolutions(tmp_path: Path) -> None:
    with _session(tmp_path) as session:
        session.add_all(
            [
                ReviewItem(item_type="school_code", status="pending"),
                ReviewItem(item_type="school_code", status="resolved", resolution="approved"),
                ReviewItem(item_type="school_code", status="resolved", resolution="rejected"),
                ReviewItem(item_type="school_code", status="resolved", resolution="corrected"),
                ReviewItem(item_type="url_candidate", status="pending", resolution="approved"),
            ]
        )
        session.commit()

        stats = populate.get_review_stats(session)

    assert stats == {
        "total": 4,
        "pending": 1,
        "approved": 1,
        "rejected": 1,
        "corrected": 1,
    }
