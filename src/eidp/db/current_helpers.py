"""Current-revision filters for SR / SchoolYearStatus reads (Sprint 8.2.1).

Sprint 8.2.a/b made ``support_recipient`` and ``school_year_status`` append-only
with ``is_current=true`` semantics, but the EXISTING read paths (Excel
exporter, review UI, pdf_discovery, reconciler) didn't yet filter to current.
That meant a fresh override or revision could leave Excel showing both old
and new values, and the scraper's "already collected" check would
double-count.

This module is the single canonical source of truth for "is_current"
filtering. Read paths must import from here so any future contract change
(e.g. switching to a different sentinel) lands in one place.

Usage
-----
SQLAlchemy ORM filter::

    from eidp.db.current_helpers import current_school_year_status_q
    rows = current_school_year_status_q(session.query(SchoolYearStatus)).all()

Raw SQL (text()) filter — pass as a parameterized condition that both
PostgreSQL and SQLite accept::

    from eidp.db.current_helpers import IS_CURRENT_TRUE_SQL
    text(f"... WHERE sys.is_current = {IS_CURRENT_TRUE_SQL}")

The constant ``TRUE`` is portable across PG (boolean literal) and SQLite
(parsed as integer 1), so the rendered SQL is safe in raw text() blocks.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from sqlalchemy import and_, func
from sqlalchemy.orm import Query, Session

from eidp.db.models import SchoolYearStatus, SupportRecipient

# Portable SQL literal — PostgreSQL parses TRUE as boolean true, SQLite as 1.
# Used inside raw text() SQL blocks where bind parameters would be awkward
# (e.g. exporter.py's CASE WHEN aggregations).
IS_CURRENT_TRUE_SQL = "TRUE"


def current_school_year_status_q(query: Query[SchoolYearStatus]) -> Query[SchoolYearStatus]:
    """Add ``SchoolYearStatus.is_current=True`` to an ORM Query."""
    return query.filter(SchoolYearStatus.is_current.is_(True))


def current_support_recipient_q(query: Query[SupportRecipient]) -> Query[SupportRecipient]:
    """Add ``SupportRecipient.is_current=True`` to an ORM Query."""
    return query.filter(SupportRecipient.is_current.is_(True))


def latest_excluded_school_ids(session: Session) -> Iterable[tuple[int]]:
    """Return a Query yielding ``SchoolYearStatus.school_id`` for schools
    whose **current** revision in their **latest** fiscal year carries an
    ``excluded_reason`` (i.e. 閉校 / 統合 / 学校なし etc).

    Sprint 8.2.1 (current-read-path). Single canonical implementation
    consumed by:

    * ``review.app._load_dashboard_stats``
    * ``review.populate``
    * ``scraper.pdf_discovery.run_pdf_discovery``
    * ``matcher.reconciler.verify_identity``

    Without the ``is_current=True`` filter, a stale "閉校" revision from a
    prior import / override could shadow a current "active" revision and
    silently drop the school from the review queue or rediscovery pool.
    """
    latest_year_subq = (
        session.query(
            SchoolYearStatus.school_id,
            func.max(SchoolYearStatus.fiscal_year).label("max_fy"),
        )
        .filter(SchoolYearStatus.is_current.is_(True))
        .group_by(SchoolYearStatus.school_id)
        .subquery()
    )
    query = (
        session.query(SchoolYearStatus.school_id)
        .join(
            latest_year_subq,
            and_(
                SchoolYearStatus.school_id == latest_year_subq.c.school_id,
                SchoolYearStatus.fiscal_year == latest_year_subq.c.max_fy,
            ),
        )
        .filter(SchoolYearStatus.is_current.is_(True))
        .filter(SchoolYearStatus.excluded_reason.isnot(None))
    )
    return cast(Iterable[tuple[int]], query)
