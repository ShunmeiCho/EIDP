"""Sprint 8.2.b — Normal ingest must be append-only on the two tables that
got revision support in 8.2.a.

Regression contract: re-ingesting the same school+year for ``SupportRecipient``
and ``SchoolYearStatus`` must NOT raise on the new
``UNIQUE(school_id, fiscal_year, revision)`` constraints. Instead, the prior
current row is flipped to ``is_current=False`` and a new revision is inserted.

The merge semantics from before the rewrite are preserved:
  * SupportRecipient — fields the PDF doesn't supply inherit the prior
    current row's values (typically Excel-imported defaults).
  * SchoolYearStatus — does NOT downgrade ``collected`` to ``partial``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Department,
    Document,
    School,
    SchoolYearStatus,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.pdf.schema import (
    DepartmentRecord,
    SchoolAnnotation,
    SupportRecipientRecord,
)
from eidp.pipeline.ingest import ingest_document


@pytest.fixture()
def engine(tmp_path: Path):
    """Bootstrap a SQLite DB carrying the 8.2.a partial unique indexes — they
    are the whole point of this test file (without them the second ingest
    would simply overwrite, instead of revision)."""
    db_path = tmp_path / "ingest_appendonly.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _make_school(session: Session) -> School:
    school = School(
        prefecture="東京都",
        corporation_name="テスト法人",
        school_name="テスト専門学校",
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    session.flush()
    return school


def _make_document(
    session: Session,
    school_id: int,
    source_url: str,
    tmp_path: Path,
    *,
    pdf_name: str,
    file_hash: str | None = None,
) -> Document:
    """Each call gets a unique file_hash by default, otherwise the
    (school_id, file_hash) UNIQUE constraint on Document blocks the second
    insert before we even reach the SupportRecipient / SchoolYearStatus
    paths we want to test."""
    pdf = tmp_path / pdf_name
    pdf.write_bytes(b"%PDF-1.5\n" + b"x" * 2048)
    if file_hash is None:
        # Hash from the source_url so each test doc gets a distinct one.
        file_hash = (source_url.encode("ascii", "replace").hex() + "0" * 64)[:64]
    doc = Document(
        school_id=school_id,
        source_url=source_url,
        file_path=str(pdf),
        file_hash=file_hash,
        pdf_type="target",
        content_type="text",
        ingest_status="pending",
    )
    session.add(doc)
    session.flush()
    return doc


def _annotation(
    *, sr_total: int = 100, dept_capacity: int = 40,
    sr_overrides: dict | None = None,
) -> SchoolAnnotation:
    sr_kwargs: dict = {"annual_total": sr_total, "grand_total": sr_total}
    if sr_overrides is not None:
        sr_kwargs = sr_overrides
    return SchoolAnnotation(
        school_name="テスト専門学校",
        school_type="専門学校",
        operator_name="テスト法人",
        fiscal_year="令和8年度",
        source_pdf="test.pdf",
        departments=[
            DepartmentRecord(
                name="テスト学科",
                capacity=dept_capacity,
                enrollment=dept_capacity,
                graduates=10,
            ),
        ],
        support_recipient=SupportRecipientRecord(**sr_kwargs),
    )


def test_ingest_twice_creates_two_support_recipient_revisions(engine, tmp_path):
    """Two ingests of the same (school, fiscal_year) must produce two
    SupportRecipient revisions. Without 8.2.b's append-only rewrite, the
    second ingest would crash on the new partial unique index."""
    with Session(engine) as session:
        school = _make_school(session)
        doc1 = _make_document(session, school.id, "https://example.com/v1.pdf", tmp_path, pdf_name="v1.pdf")
        doc1.id = 101
        doc2 = _make_document(session, school.id, "https://example.com/v2.pdf", tmp_path, pdf_name="v2.pdf")
        doc2.id = 102
        session.commit()

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=_annotation(sr_total=100)):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=_annotation(sr_total=120)):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        rows = (
            session.query(SupportRecipient)
            .filter(SupportRecipient.school_id == school.id)
            .order_by(SupportRecipient.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert [r.annual_total for r in rows] == [100, 120]
        assert rows[1].document_id == doc2.id


def test_support_recipient_merge_preserves_fields_from_prior_revision(engine, tmp_path):
    """If the second PDF leaves a field as None, the new revision must
    inherit that field from the prior current row — preserving the
    "non-destructive" merge semantic from the pre-8.2 in-place update path."""
    with Session(engine) as session:
        school = _make_school(session)
        doc1 = _make_document(session, school.id, "https://example.com/v1.pdf", tmp_path, pdf_name="v1.pdf")
        doc2 = _make_document(session, school.id, "https://example.com/v2.pdf", tmp_path, pdf_name="v2.pdf")
        session.commit()

        ann_full = _annotation(sr_overrides={
            "first_half_total": 50,
            "second_half_total": 50,
            "annual_total": 100,
            "grand_total": 100,
        })
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_full):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        # Second ingest only updates annual_total; the other fields are None.
        ann_partial = _annotation(sr_overrides={"annual_total": 110})
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_partial):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        current = (
            session.query(SupportRecipient)
            .filter(
                SupportRecipient.school_id == school.id,
                SupportRecipient.is_current.is_(True),
            )
            .one()
        )
        assert current.revision == 2
        assert current.annual_total == 110, "PDF value must overlay"
        assert current.first_half_total == 50, "missing PDF value must inherit prior revision"
        assert current.second_half_total == 50


def test_ingest_twice_creates_two_school_year_status_revisions(engine, tmp_path):
    with Session(engine) as session:
        school = _make_school(session)
        # Pre-create matching dept so collection_status comes out 'collected'
        session.add(Department(school_id=school.id, canonical_name="テスト学科"))
        doc1 = _make_document(session, school.id, "https://example.com/v1.pdf", tmp_path, pdf_name="v1.pdf")
        doc2 = _make_document(session, school.id, "https://example.com/v2.pdf", tmp_path, pdf_name="v2.pdf")
        session.commit()

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=_annotation()):
            ingest_document(session, doc1, recorder=None)
        session.commit()
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=_annotation()):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        rows = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.school_id == school.id)
            .order_by(SchoolYearStatus.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert rows[1].document_id == doc2.id


def test_school_year_status_does_not_downgrade_from_collected_to_partial(engine, tmp_path):
    """If revision 1 was status='collected' (full ingest with all departments
    matched), a subsequent ingest that would normally classify as 'partial'
    must keep the new revision at 'collected' — same rule as the old in-place
    update path, just expressed in append-only form."""
    with Session(engine) as session:
        school = _make_school(session)
        session.add(Department(school_id=school.id, canonical_name="テスト学科"))
        doc1 = _make_document(session, school.id, "https://example.com/v1.pdf", tmp_path, pdf_name="v1.pdf")
        session.commit()

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=_annotation(dept_capacity=40)):
            ingest_document(session, doc1, recorder=None)
        session.commit()
        rev1 = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.school_id == school.id)
            .order_by(SchoolYearStatus.revision.desc())
            .first()
        )
        assert rev1 is not None
        prior_status = rev1.status

        # Revision 2: annotation contains a department that fails to match
        # against the existing Department row, so the new ingest would
        # classify as partial.
        doc2 = _make_document(session, school.id, "https://example.com/v2.pdf", tmp_path, pdf_name="v2.pdf")
        session.commit()
        ann_partial = SchoolAnnotation(
            school_name="テスト専門学校",
            school_type="専門学校",
            operator_name="テスト法人",
            fiscal_year="令和8年度",
            source_pdf="v2.pdf",
            departments=[
                DepartmentRecord(name="未登録学科", capacity=10, enrollment=10, graduates=2),
            ],
            support_recipient=SupportRecipientRecord(annual_total=80),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_partial):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        rev2 = (
            session.query(SchoolYearStatus)
            .filter(
                SchoolYearStatus.school_id == school.id,
                SchoolYearStatus.is_current.is_(True),
            )
            .one()
        )
        if prior_status == "collected":
            assert rev2.status == "collected", (
                "rev 2 must not downgrade from collected — the no-downgrade rule "
                "from pre-8.2 ingest must survive the append-only rewrite"
            )
