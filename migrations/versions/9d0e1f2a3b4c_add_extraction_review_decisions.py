"""add extraction review decisions

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9d0e1f2a3b4c"
down_revision = "8c9d0e1f2a3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_review_decision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("review_id", sa.String(length=80), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("corrected_value", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("identity_source", sa.String(length=32), nullable=False),
        sa.Column("audit_action_id", sa.String(length=36), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision != 'exclude' OR "
            "length(trim(coalesce(note, ''))) BETWEEN 1 AND 500",
            name="ck_extraction_review_decision_exclude_reason",
        ),
        sa.ForeignKeyConstraint(
            ["audit_action_id"],
            ["manual_action_log.action_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audit_action_id",
            name="uq_extraction_review_decision_audit_action_id",
        ),
        sa.UniqueConstraint(
            "decision_id",
            name="uq_extraction_review_decision_decision_id",
        ),
        sa.UniqueConstraint(
            "review_id",
            "revision",
            name="uq_extraction_review_decision_review_revision",
        ),
        comment="Append-only audited extraction review decisions",
    )
    op.create_index(
        "ix_extraction_review_decision_review_id",
        "extraction_review_decision",
        ["review_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_extraction_review_decision_review_id",
        table_name="extraction_review_decision",
    )
    op.drop_table("extraction_review_decision")
