"""expand extraction confidence precision

Revision ID: 6a7b8c9d0e1f
Revises: 4b9c1d2e3f45
Create Date: 2026-05-15 17:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6a7b8c9d0e1f"
down_revision = "4b9c1d2e3f45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "department_yearly",
        "extraction_confidence",
        existing_type=sa.Numeric(precision=3, scale=2),
        type_=sa.Numeric(precision=4, scale=3),
        existing_nullable=True,
    )
    op.alter_column(
        "support_recipient",
        "extraction_confidence",
        existing_type=sa.Numeric(precision=3, scale=2),
        type_=sa.Numeric(precision=4, scale=3),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "support_recipient",
        "extraction_confidence",
        existing_type=sa.Numeric(precision=4, scale=3),
        type_=sa.Numeric(precision=3, scale=2),
        existing_nullable=True,
    )
    op.alter_column(
        "department_yearly",
        "extraction_confidence",
        existing_type=sa.Numeric(precision=4, scale=3),
        type_=sa.Numeric(precision=3, scale=2),
        existing_nullable=True,
    )
