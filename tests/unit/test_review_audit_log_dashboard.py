"""Sprint 8.6.d.4 — queue depth dashboard for the audit log page."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Document, School
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.review.pages.audit_log import QueueDepth, queue_depth


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "depth.sqlite3"
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(eng)
    yield eng
    eng.dispose()


def _seed_school(session: Session) -> School:
    s = School(
        prefecture="東京都", corporation_name="法人", school_name="A学校",
        school_type="専門学校", status="active",
    )
    session.add(s)
    session.flush()
    return s


def _add_doc(session: Session, school_id: int, *, status: str | None,
             url_suffix: str, file_hash: str) -> Document:
    doc = Document(
        school_id=school_id,
        source_url=f"https://example.com/{url_suffix}.pdf",
        file_hash=file_hash,
        pdf_type="target",
        content_type="text",
        ingest_status=status,
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    return doc


# ---------------------------------------------------------------------------
# queue_depth
# ---------------------------------------------------------------------------


def test_empty_db_returns_zero_depth(engine):
    with Session(engine) as session:
        depth = queue_depth(session)
    assert depth == QueueDepth(
        review_pending=0, ocr_pending=0, parse_failed=0,
        school_mismatch=0, ingested=0, support_only=0,
        other=0, total=0,
    )


def test_queue_depth_groups_each_known_status(engine):
    with Session(engine) as session:
        school = _seed_school(session)
        _add_doc(session, school.id, status="review_pending",
                 url_suffix="r1", file_hash="0" * 64)
        _add_doc(session, school.id, status="review_pending",
                 url_suffix="r2", file_hash="1" * 64)
        _add_doc(session, school.id, status="ocr_pending",
                 url_suffix="o1", file_hash="2" * 64)
        _add_doc(session, school.id, status="parse_failed",
                 url_suffix="p1", file_hash="3" * 64)
        _add_doc(session, school.id, status="school_mismatch",
                 url_suffix="s1", file_hash="4" * 64)
        _add_doc(session, school.id, status="ingested",
                 url_suffix="i1", file_hash="5" * 64)
        _add_doc(session, school.id, status="support_only",
                 url_suffix="x1", file_hash="6" * 64)
        session.commit()

        depth = queue_depth(session)

    assert depth.review_pending == 2
    assert depth.ocr_pending == 1
    assert depth.parse_failed == 1
    assert depth.school_mismatch == 1
    assert depth.ingested == 1
    assert depth.support_only == 1
    assert depth.other == 0
    assert depth.total == 7


def test_queue_depth_treats_unknown_status_as_other(engine):
    """A future status drift (e.g. someone adding 'permanent_error')
    must NOT silently drop documents from the total. Catch-all bucket
    surfaces them under 'other' so the operator notices."""
    with Session(engine) as session:
        school = _seed_school(session)
        _add_doc(session, school.id, status="ingested",
                 url_suffix="i", file_hash="7" * 64)
        _add_doc(session, school.id, status="permanent_error",
                 url_suffix="x", file_hash="8" * 64)
        _add_doc(session, school.id, status="some_new_state",
                 url_suffix="y", file_hash="9" * 64)
        session.commit()

        depth = queue_depth(session)

    assert depth.ingested == 1
    assert depth.other == 2
    assert depth.total == 3


def test_queue_depth_counts_null_status_as_other(engine):
    """Documents in 'pending' state (None ingest_status) should still
    be visible in the audit dashboard total — they are partially
    initialized, not invisible."""
    with Session(engine) as session:
        school = _seed_school(session)
        _add_doc(session, school.id, status=None,
                 url_suffix="n1", file_hash="a" * 64)
        _add_doc(session, school.id, status="ingested",
                 url_suffix="n2", file_hash="b" * 64)
        session.commit()

        depth = queue_depth(session)

    assert depth.ingested == 1
    assert depth.other == 1
    assert depth.total == 2


def test_queue_depth_dataclass_is_frozen():
    depth = QueueDepth(
        review_pending=0, ocr_pending=0, parse_failed=0,
        school_mismatch=0, ingested=0, support_only=0,
        other=0, total=0,
    )
    with pytest.raises(Exception):
        depth.review_pending = 99  # type: ignore[misc]


def test_queue_depth_ignores_other_tables(engine):
    """The query must scope to Document only — schools, departments,
    etc. should not bleed into the count."""
    with Session(engine) as session:
        # School is added but no Document.
        _seed_school(session)
        session.commit()
        depth = queue_depth(session)
    assert depth.total == 0
