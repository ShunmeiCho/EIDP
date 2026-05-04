"""Sprint 8.2.c — audit log writer + JSONL outbox dedup contract.

Covers the data-integrity guarantees owner pinned for 8.2.c:

  * DB ``manual_action_log`` is the source of truth.
  * Each row gets a stable ``action_id`` UUID at insert.
  * After-commit JSONL outbox writes pending rows once, marks them with
    ``jsonl_exported_at``, leaves ``jsonl_export_error`` NULL on success.
  * Rerunning the flush after a partial JSONL write does not duplicate lines:
    rows whose ``action_id`` already appears in the file are stamped only.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.audit import log_manual_action
from eidp.db.audit_outbox import flush_audit_outbox
from eidp.db.models import ManualActionLog
from eidp.db.sqlite_bootstrap import bootstrap_sqlite


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "audit.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def test_log_manual_action_inserts_row_with_uuid(engine):
    with Session(engine) as session:
        row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=42,
            new_value={"enrollment": 100},
            reason="business user filled in image PDF data",
        )
        session.commit()

        # action_id must be a valid UUID string
        uuid.UUID(row.action_id)
        assert row.action_type == "manual_entry"
        assert row.target_table == "department_yearly"
        assert row.target_id == 42
        assert json.loads(row.new_value) == {"enrollment": 100}
        assert row.actor == "operator"
        assert row.jsonl_exported_at is None  # outbox has not run yet


def test_log_manual_action_serialises_old_value_and_new_value_as_json(engine):
    with Session(engine) as session:
        row = log_manual_action(
            session,
            action_type="fiscal_year_override",
            target_table="document",
            target_id=1,
            old_value={"fiscal_year": 2025},
            new_value={"fiscal_year": 2026},
            reason="business user identified PDF as 令和8",
        )
        session.commit()

        assert json.loads(row.old_value) == {"fiscal_year": 2025}
        assert json.loads(row.new_value) == {"fiscal_year": 2026}


def test_log_manual_action_none_values_remain_null(engine):
    """``None`` for old/new_value must NOT serialise to the JSON literal
    string "null" — callers need a way to distinguish "no prior state" from
    "state was JSON null"."""
    with Session(engine) as session:
        row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            new_value={"enrollment": 50},
        )
        session.commit()

        assert row.old_value is None
        assert row.new_value is not None


def test_flush_outbox_writes_pending_rows_to_jsonl(engine, tmp_path):
    jsonl = tmp_path / "manual-actions.jsonl"

    with Session(engine) as session:
        log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=1,
            new_value={"enrollment": 100},
        )
        log_manual_action(
            session,
            action_type="r8_override",
            target_table="document",
            target_id=2,
            new_value={"fiscal_year": 2026},
        )
        session.commit()

        stats = flush_audit_outbox(session, jsonl_path=jsonl)
        assert stats == {"exported": 2, "already_present": 0, "failed": 0}

    # Verify file content
    lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    action_types = {p["action_type"] for p in parsed}
    assert action_types == {"manual_entry", "r8_override"}

    # And both rows must now carry jsonl_exported_at
    with Session(engine) as session:
        rows = session.query(ManualActionLog).all()
        assert all(r.jsonl_exported_at is not None for r in rows)
        assert all(r.jsonl_export_error is None for r in rows)


def test_flush_outbox_dedups_when_action_id_already_in_file(engine, tmp_path):
    """Simulate a partial previous flush: the JSONL line was written but
    ``jsonl_exported_at`` failed to update. A subsequent flush must NOT
    duplicate the line; it should detect the existing action_id and just
    stamp the column."""
    jsonl = tmp_path / "manual-actions.jsonl"

    with Session(engine) as session:
        row = log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=1,
            new_value={"enrollment": 100},
        )
        session.commit()
        action_id = row.action_id

    # Pre-populate the JSONL file with the row's action_id (simulating a
    # previous successful write that crashed before updating the column).
    pre_seed = {"action_id": action_id, "old": "manual partial flush"}
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text(json.dumps(pre_seed) + "\n", encoding="utf-8")

    with Session(engine) as session:
        stats = flush_audit_outbox(session, jsonl_path=jsonl)
        assert stats == {"exported": 0, "already_present": 1, "failed": 0}

        # Column must still be stamped so the row isn't perpetually pending.
        row = session.query(ManualActionLog).one()
        assert row.jsonl_exported_at is not None
        assert row.jsonl_export_error is None

    # File must still hold exactly one line.
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


def test_flush_outbox_skips_already_exported_rows(engine, tmp_path):
    """Pending = jsonl_exported_at IS NULL. Already-exported rows must be
    skipped on subsequent flushes regardless of whether the JSONL file still
    contains them."""
    jsonl = tmp_path / "manual-actions.jsonl"
    with Session(engine) as session:
        log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=1,
            new_value={"enrollment": 100},
        )
        session.commit()
        first = flush_audit_outbox(session, jsonl_path=jsonl)
        assert first["exported"] == 1

        second = flush_audit_outbox(session, jsonl_path=jsonl)
        assert second == {"exported": 0, "already_present": 0, "failed": 0}

    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


def test_flush_outbox_creates_parent_directory(engine, tmp_path):
    """Outbox path may live under a not-yet-existing ``data/audit/`` folder
    on a fresh business-user install. Flush must mkdir it on demand."""
    jsonl = tmp_path / "audit" / "deeply" / "nested" / "manual-actions.jsonl"
    with Session(engine) as session:
        log_manual_action(
            session,
            action_type="manual_entry",
            target_table="department_yearly",
            target_id=1,
            new_value={"enrollment": 100},
        )
        session.commit()
        flush_audit_outbox(session, jsonl_path=jsonl)

    assert jsonl.exists()
