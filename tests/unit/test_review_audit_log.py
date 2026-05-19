"""Sprint 8.4.c.4 — 監査ログ page helper regression."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.locking import acquire_lock
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.review._pages.audit_log import (
    ACTION_TYPES,
    TARGET_TABLES,
    FlushOutcome,
    flush_outbox_via_ui,
    flush_outbox_with_lock,
    list_recent_actions,
    outbox_pending_count,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "audit_log.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _seed_actions(session: Session) -> None:
    """Seed three audit rows. document_id=None keeps the seed
    self-contained — we don't need to create matching Document rows
    just to exercise the audit-log helpers."""
    log_manual_action(
        session, action_type="manual_entry", target_table="department_yearly",
        target_id=1, document_id=None,
        old_value=None, new_value={"enrollment": 50},
        reason="image PDF",
    )
    log_manual_action(
        session, action_type="fiscal_year_override", target_table="document",
        target_id=10, document_id=None,
        old_value={"fiscal_year": 2025}, new_value={"fiscal_year": 2026},
        reason="cover page R8",
    )
    log_manual_action(
        session, action_type="manual_entry", target_table="department",
        target_id=2, document_id=None,
        old_value=None, new_value={"canonical_name": "B学科"},
    )


# ---------------------------------------------------------------------------
# list_recent_actions
# ---------------------------------------------------------------------------


def test_list_recent_actions_orders_newest_first(engine):
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        rows = list_recent_actions(session)
        assert len(rows) == 3
        # IDs descend.
        assert [r.id for r in rows] == sorted([r.id for r in rows], reverse=True)


def test_list_recent_actions_filters_by_action_type(engine):
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        rows = list_recent_actions(session, action_type="fiscal_year_override")
        assert len(rows) == 1
        assert rows[0].action_type == "fiscal_year_override"
        assert rows[0].old_value == {"fiscal_year": 2025}
        assert rows[0].new_value == {"fiscal_year": 2026}


def test_list_recent_actions_filters_by_target_table(engine):
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        rows = list_recent_actions(session, target_table="department")
        assert len(rows) == 1
        assert rows[0].target_table == "department"


def test_list_recent_actions_respects_limit(engine):
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        rows = list_recent_actions(session, limit=2)
        assert len(rows) == 2


def test_list_recent_actions_parses_json_values(engine):
    """``old_value`` / ``new_value`` are stored as JSON text; the row
    projection must surface them as parsed Python objects so the UI
    can render them via st.json without re-parsing."""
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        rows = list_recent_actions(session, action_type="manual_entry", target_table="department_yearly")
        assert len(rows) == 1
        assert rows[0].new_value == {"enrollment": 50}
        assert rows[0].old_value is None


# ---------------------------------------------------------------------------
# outbox_pending_count + flush_outbox_via_ui
# ---------------------------------------------------------------------------


def test_outbox_pending_count_initially_equals_action_count(engine):
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        # All 3 rows are pending until flush runs.
        assert outbox_pending_count(session) == 3


def test_flush_outbox_via_ui_drains_pending(engine, tmp_path):
    jsonl = tmp_path / "manual-actions.jsonl"
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        stats = flush_outbox_via_ui(session, jsonl)
        assert stats == {"exported": 3, "already_present": 0, "failed": 0}
        assert jsonl.exists()
        # No more pending after flush.
        assert outbox_pending_count(session) == 0


def test_flush_outbox_via_ui_is_idempotent(engine, tmp_path):
    jsonl = tmp_path / "manual-actions.jsonl"
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        first = flush_outbox_via_ui(session, jsonl)
        assert first["exported"] == 3
        second = flush_outbox_via_ui(session, jsonl)
        assert second == {"exported": 0, "already_present": 0, "failed": 0}


def test_flush_outbox_with_lock_drains_when_free(engine, tmp_path):
    jsonl = tmp_path / "manual-actions.jsonl"
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        outcome = flush_outbox_with_lock(session, jsonl_path=jsonl, lock_path=lock)
        assert outcome.ok is True
        assert outcome.lock_busy is False
        assert outcome.stats == {"exported": 3, "already_present": 0, "failed": 0}
        assert outbox_pending_count(session) == 0
        assert jsonl.exists()


def test_flush_outbox_with_lock_returns_busy_without_exporting(engine, tmp_path):
    jsonl = tmp_path / "manual-actions.jsonl"
    lock = tmp_path / ".lock"
    with Session(engine) as session:
        _seed_actions(session)
        session.commit()

        with acquire_lock(lock, owner="weekly_runner"):
            outcome = flush_outbox_with_lock(session, jsonl_path=jsonl, lock_path=lock)

        assert outcome.ok is False
        assert outcome.lock_busy is True
        assert outcome.lock_owner == "weekly_runner"
        assert outcome.stats is None
        assert outbox_pending_count(session) == 3
        assert not jsonl.exists()


def test_flush_outcome_default_shape():
    outcome = FlushOutcome(ok=True)
    assert outcome.lock_busy is False
    assert outcome.lock_owner is None
    assert outcome.stats is None


# ---------------------------------------------------------------------------
# Vocabulary constants
# ---------------------------------------------------------------------------


def test_action_types_and_target_tables_are_pinned():
    """Lock the dropdown vocabulary so a future caller adding a new
    action_type without surfacing it in the UI shows up in code review."""
    assert set(ACTION_TYPES) >= {
        "manual_entry",
        "fiscal_year_override",
        "r8_override",
        "dept_change",
        "operator_settings_saved",
        "excel_preview_generated",
        "excel_export_generated",
        "school_year_tasks_rebuilt",
        "operator_url_submitted",
        "operator_url_bulk_imported",
        "url_auto_discovery",
        "url_candidate_proposed",
        "url_candidate_manual_required",
        "url_candidate_approved",
        "url_candidate_rejected",
        "prefecture_remark_approved",
        "prefecture_remark_rejected",
        "school_code_approved",
        "school_code_corrected",
        "school_code_rejected",
        "school_code_skipped",
        "school_alias_approved",
        "dept_alias_approved",
        "dept_change_void",
    }
    assert set(TARGET_TABLES) >= {
        "document",
        "department",
        "department_yearly",
        "department_change",
        "support_recipient",
        "school_year_status",
        "school_fiscal_year_status",
        "school",
        "school_alias",
        "review_item",
        "school_site",
        "excel_export",
        "operator_settings",
    }
