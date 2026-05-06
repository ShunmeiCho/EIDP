"""add school fiscal year status table

Revision ID: b7a1f3d5c9e2
Revises: 8a02_audit_confidence_override
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7a1f3d5c9e2"
down_revision: str | Sequence[str] | None = "8a02_audit_confidence_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "school_fiscal_year_status",
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("school.id"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("url_status", sa.String(length=30), nullable=False),
        sa.Column("pdf_status", sa.String(length=30), nullable=False),
        sa.Column("extract_status", sa.String(length=30), nullable=False),
        sa.Column("yoy_diff_status", sa.String(length=30), nullable=False),
        sa.Column("excel_ready", sa.Boolean(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("evidence_level", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("school_id", "fiscal_year"),
        comment="Denormalized School x fiscal-year operator task status",
    )
    op.create_index(
        "idx_school_fy_status_fy_pdf",
        "school_fiscal_year_status",
        ["fiscal_year", "pdf_status"],
    )
    op.create_index(
        "idx_school_fy_status_fy_ready",
        "school_fiscal_year_status",
        ["fiscal_year", "excel_ready"],
    )


def downgrade() -> None:
    op.drop_index("idx_school_fy_status_fy_ready", table_name="school_fiscal_year_status")
    op.drop_index("idx_school_fy_status_fy_pdf", table_name="school_fiscal_year_status")
    op.drop_table("school_fiscal_year_status")
