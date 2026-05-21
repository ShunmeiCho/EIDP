"""audit + confidence + fiscal_year_override

Revision ID: 8a02_audit_confidence_override
Revises: 8a01_schema_contract
Create Date: 2026-05-04

Sprint 8.2.c — adds:
  * ``document.fiscal_year_override`` (Integer, nullable). Read by
    ``effective_fiscal_year(doc)`` for override + UI display only; coverage
    and exporter continue to read the real ``fiscal_year`` because the
    write-through path in ``pipeline.fiscal_year_override`` rewrites the
    underlying rows.
  * ``department_yearly.confidence_breakdown`` and
    ``support_recipient.confidence_breakdown`` (Text, nullable). JSON blobs
    documenting the F1/F2/F3 score components and weights, surfaced in the
    Streamlit UI so the business user sees *why* a number scored low.
  * ``manual_action_log`` table — DB-authoritative audit. JSONL at
    ``data/audit/manual-actions.jsonl`` is an after-commit outbox keyed off
    ``action_id`` (UUID), with ``jsonl_exported_at`` / ``jsonl_export_error``
    columns so a failed flush can be retried by ``eidp audit-flush``.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8a02_audit_confidence_override"
down_revision: Union[str, Sequence[str], None] = "8a01_schema_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document", sa.Column("fiscal_year_override", sa.Integer(), nullable=True))
    op.add_column("department_yearly", sa.Column("confidence_breakdown", sa.Text(), nullable=True))
    op.add_column("support_recipient", sa.Column("confidence_breakdown", sa.Text(), nullable=True))

    op.create_table(
        "manual_action_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=50), nullable=False, server_default=sa.text("'operator'")),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_table", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("jsonl_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("jsonl_export_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_id"),
    )


def downgrade() -> None:
    op.drop_table("manual_action_log")
    op.drop_column("support_recipient", "confidence_breakdown")
    op.drop_column("department_yearly", "confidence_breakdown")
    op.drop_column("document", "fiscal_year_override")
