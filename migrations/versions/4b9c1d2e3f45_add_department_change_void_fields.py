"""add department_change void fields

Revision ID: 4b9c1d2e3f45
Revises: 3f5d8a9c7b12
Create Date: 2026-05-11 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4b9c1d2e3f45"
down_revision = "3f5d8a9c7b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "department_change",
        sa.Column("voided", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "department_change",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "department_change",
        sa.Column("voided_by", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "department_change",
        sa.Column("void_reason", sa.Text(), nullable=True),
    )
    op.alter_column("department_change", "voided", server_default=None)


def downgrade() -> None:
    op.drop_column("department_change", "void_reason")
    op.drop_column("department_change", "voided_by")
    op.drop_column("department_change", "voided_at")
    op.drop_column("department_change", "voided")
