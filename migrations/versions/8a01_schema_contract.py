"""schema contract: SupportRecipient & SchoolYearStatus revision support

Revision ID: 8a01_schema_contract
Revises: 94884a1f8586
Create Date: 2026-05-04

Sprint 8.2.a — adds ``is_current`` and ``revision`` columns to
``support_recipient`` and ``school_year_status`` so override rewrites can
follow the same append-only protocol the ``department_yearly`` table already
uses. Replaces the old ``UNIQUE(school_id, fiscal_year)`` constraints with
``UNIQUE(school_id, fiscal_year, revision)`` plus a partial unique index on
``is_current=true``.

This migration is PostgreSQL-side only. Linux/Web SQLite deployments use
``eidp.db.sqlite_bootstrap`` which builds the new schema directly from ORM
metadata — see Sprint 8.1 for that path.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8a01_schema_contract"
down_revision: Union[str, Sequence[str], None] = "94884a1f8586"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add revision/is_current to two tables, replace unique constraints."""

    # --- support_recipient -------------------------------------------------
    op.add_column(
        "support_recipient",
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "support_recipient",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # Backfill is implicit via server_default. Drop the defaults afterwards
    # so the application owns the values going forward.
    op.alter_column("support_recipient", "revision", server_default=None)
    op.alter_column("support_recipient", "is_current", server_default=None)

    # The old UNIQUE(school_id, fiscal_year) was created without an explicit
    # name in v5; alembic's auto-naming convention picks
    # "support_recipient_school_id_fiscal_year_key" on PostgreSQL.
    op.drop_constraint("support_recipient_school_id_fiscal_year_key", "support_recipient", type_="unique")
    op.create_unique_constraint(
        "uq_support_recipient_revision",
        "support_recipient",
        ["school_id", "fiscal_year", "revision"],
    )
    op.create_index(
        "idx_support_recipient_current",
        "support_recipient",
        ["school_id", "fiscal_year"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # --- school_year_status ------------------------------------------------
    op.add_column(
        "school_year_status",
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "school_year_status",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.alter_column("school_year_status", "revision", server_default=None)
    op.alter_column("school_year_status", "is_current", server_default=None)

    op.drop_constraint("school_year_status_school_id_fiscal_year_key", "school_year_status", type_="unique")
    op.create_unique_constraint(
        "uq_school_year_status_revision",
        "school_year_status",
        ["school_id", "fiscal_year", "revision"],
    )
    op.create_index(
        "idx_school_year_status_current",
        "school_year_status",
        ["school_id", "fiscal_year"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    """Revert revision/is_current additions."""

    # --- school_year_status ------------------------------------------------
    op.drop_index("idx_school_year_status_current", table_name="school_year_status")
    op.drop_constraint("uq_school_year_status_revision", "school_year_status", type_="unique")
    op.create_unique_constraint(
        "school_year_status_school_id_fiscal_year_key",
        "school_year_status",
        ["school_id", "fiscal_year"],
    )
    op.drop_column("school_year_status", "is_current")
    op.drop_column("school_year_status", "revision")

    # --- support_recipient -------------------------------------------------
    op.drop_index("idx_support_recipient_current", table_name="support_recipient")
    op.drop_constraint("uq_support_recipient_revision", "support_recipient", type_="unique")
    op.create_unique_constraint(
        "support_recipient_school_id_fiscal_year_key",
        "support_recipient",
        ["school_id", "fiscal_year"],
    )
    op.drop_column("support_recipient", "is_current")
    op.drop_column("support_recipient", "revision")
