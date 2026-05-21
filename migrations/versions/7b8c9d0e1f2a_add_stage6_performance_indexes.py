"""add stage6 performance indexes

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
Create Date: 2026-05-15 18:15:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "7b8c9d0e1f2a"
down_revision = "6a7b8c9d0e1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_document_school_id", "document", ["school_id"])
    op.create_index(
        "idx_document_fiscal_year_pdf_type_ingest_status",
        "document",
        ["fiscal_year", "pdf_type", "ingest_status"],
    )
    op.create_index(
        "idx_school_site_school_id_http_status",
        "school_site",
        ["school_id", "http_status"],
    )
    op.create_index(
        "idx_department_yearly_document_id",
        "department_yearly",
        ["document_id"],
    )
    op.create_index(
        "idx_manual_action_log_jsonl_exported_table_document",
        "manual_action_log",
        ["jsonl_exported_at", "target_table", "document_id"],
    )
    op.create_index("idx_school_alias_school_id", "school_alias", ["school_id"])
    op.create_index(
        "idx_department_change_department_id",
        "department_change",
        ["department_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_department_change_department_id", table_name="department_change")
    op.drop_index("idx_school_alias_school_id", table_name="school_alias")
    op.drop_index("idx_manual_action_log_jsonl_exported_table_document", table_name="manual_action_log")
    op.drop_index("idx_department_yearly_document_id", table_name="department_yearly")
    op.drop_index("idx_school_site_school_id_http_status", table_name="school_site")
    op.drop_index("idx_document_fiscal_year_pdf_type_ingest_status", table_name="document")
    op.drop_index("idx_document_school_id", table_name="document")
