"""add audit identity source

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "8c9d0e1f2a3b"
down_revision = "7b8c9d0e1f2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "manual_action_log",
        sa.Column("identity_source", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("manual_action_log", "identity_source")
