"""add persistent external comparisons and double-check resolutions

Revision ID: ae1f2a3b4c5d
Revises: 9d0e1f2a3b4c
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ae1f2a3b4c5d"
down_revision = "9d0e1f2a3b4c"
branch_labels = None
depends_on = None

_SQLITE_IMMUTABLE_TABLES = (
    "external_comparison_run",
    "external_comparison_result",
    "double_check_resolution",
)


def _sqlite_immutability_trigger_ddl(table_name: str, operation: str) -> str:
    trigger_name = f"trg_{table_name}_immutable_{operation.lower()}"
    return f"""
        CREATE TRIGGER IF NOT EXISTS {trigger_name}
        BEFORE {operation} ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, '{table_name} is immutable');
        END
    """


def upgrade() -> None:
    op.create_table(
        "external_comparison_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("source_system", sa.String(length=32), nullable=False),
        sa.Column("external_file_sha256", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("external_file_path", sa.Text(), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_path", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("identity_source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_system IN ('copilot', 'notebooklm', 'manual_external')",
            name="ck_external_comparison_run_source_system",
        ),
        sa.CheckConstraint(
            "length(external_file_sha256) = 64",
            name="ck_external_comparison_run_file_sha256",
        ),
        sa.CheckConstraint(
            "length(report_sha256) = 64",
            name="ck_external_comparison_run_report_sha256",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_external_comparison_run_run_id"),
        sa.UniqueConstraint(
            "run_id",
            "external_file_sha256",
            name="uq_external_comparison_run_run_hash",
        ),
        comment="Immutable external comparison run and content-addressed artifacts",
    )
    op.create_index(
        "ix_external_comparison_run_external_file_sha256",
        "external_comparison_run",
        ["external_file_sha256"],
        unique=False,
    )
    op.create_index(
        "uq_extraction_review_decision_provenance",
        "extraction_review_decision",
        ["review_id", "revision", "audit_action_id"],
        unique=True,
        if_not_exists=True,
    )

    op.create_table(
        "external_comparison_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("row_key", sa.String(length=64), nullable=False),
        sa.Column("comparison_key", sa.Text(), nullable=False),
        sa.Column("review_id", sa.String(length=80), nullable=True),
        sa.Column("review_decision_revision", sa.Integer(), nullable=True),
        sa.Column("review_audit_action_id", sa.String(length=36), nullable=True),
        sa.Column("external_source_row_key", sa.Text(), nullable=True),
        sa.Column("external_value", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("external_file_sha256", sa.String(length=64), nullable=False),
        sa.Column("eidp_value", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("comparison_status", sa.String(length=48), nullable=False),
        sa.Column("mismatch_reason", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "comparison_status IN ("
            "'match', 'value_mismatch', 'missing_in_eidp', 'missing_in_external', "
            "'ambiguous_key_not_comparable', 'needs_review_not_comparable', "
            "'excluded_not_comparable')",
            name="ck_external_comparison_result_status",
        ),
        sa.CheckConstraint(
            "length(external_file_sha256) = 64",
            name="ck_external_comparison_result_file_sha256",
        ),
        sa.CheckConstraint(
            "review_decision_revision IS NULL OR review_decision_revision >= 1",
            name="ck_external_comparison_result_review_revision",
        ),
        sa.CheckConstraint(
            "(review_decision_revision IS NULL AND review_audit_action_id IS NULL) OR "
            "(review_id IS NOT NULL AND review_decision_revision IS NOT NULL "
            "AND review_audit_action_id IS NOT NULL)",
            name="ck_external_comparison_result_review_provenance",
        ),
        sa.ForeignKeyConstraint(
            ["review_id", "review_decision_revision", "review_audit_action_id"],
            [
                "extraction_review_decision.review_id",
                "extraction_review_decision.revision",
                "extraction_review_decision.audit_action_id",
            ],
            name="fk_external_comparison_result_review_provenance",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["external_comparison_run.run_id"],
            name="fk_external_comparison_result_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "external_file_sha256"],
            [
                "external_comparison_run.run_id",
                "external_comparison_run.external_file_sha256",
            ],
            name="fk_external_comparison_result_run_hash",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "row_key",
            name="uq_external_comparison_result_run_row",
        ),
        comment="Immutable per-row external comparison snapshot",
    )

    op.create_table(
        "double_check_resolution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.String(length=36), nullable=False),
        sa.Column("comparison_result_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("corrected_value", sa.Integer(), nullable=True),
        sa.Column("effective_value", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("identity_source", sa.String(length=32), nullable=False),
        sa.Column("audit_action_id", sa.String(length=36), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("revision >= 1", name="ck_double_check_resolution_revision"),
        sa.CheckConstraint(
            "outcome IN ('accept_eidp', 'accept_external', 'correct', 'exclude')",
            name="ck_double_check_resolution_outcome",
        ),
        sa.CheckConstraint(
            "length(trim(coalesce(reason, ''))) BETWEEN 1 AND 500",
            name="ck_double_check_resolution_reason",
        ),
        sa.CheckConstraint(
            "(outcome = 'accept_eidp' AND corrected_value IS NULL AND effective_value IS NOT NULL) OR "
            "(outcome = 'accept_external' AND corrected_value IS NOT NULL "
            "AND effective_value = corrected_value) OR "
            "(outcome = 'correct' AND corrected_value IS NOT NULL AND corrected_value >= 0 "
            "AND effective_value = corrected_value) OR "
            "(outcome = 'exclude' AND corrected_value IS NULL AND effective_value IS NULL)",
            name="ck_double_check_resolution_value_contract",
        ),
        sa.ForeignKeyConstraint(
            ["audit_action_id"],
            ["manual_action_log.action_id"],
            name="fk_double_check_resolution_audit_action_id",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_result_id"],
            ["external_comparison_result.id"],
            name="fk_double_check_resolution_comparison_result_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_action_id", name="uq_double_check_resolution_audit_action_id"),
        sa.UniqueConstraint(
            "comparison_result_id",
            "revision",
            name="uq_double_check_resolution_result_revision",
        ),
        sa.UniqueConstraint("resolution_id", name="uq_double_check_resolution_resolution_id"),
        comment="Append-only audited double-check resolutions",
    )
    if op.get_bind().dialect.name == "sqlite":
        for table_name in _SQLITE_IMMUTABLE_TABLES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(sa.text(_sqlite_immutability_trigger_ddl(table_name, operation)))


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for table_name in _SQLITE_IMMUTABLE_TABLES:
            for operation in ("UPDATE", "DELETE"):
                trigger_name = f"trg_{table_name}_immutable_{operation.lower()}"
                op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
    op.drop_table("double_check_resolution")
    op.drop_table("external_comparison_result")
    op.drop_index(
        "uq_extraction_review_decision_provenance",
        table_name="extraction_review_decision",
        if_exists=True,
    )
    op.drop_index(
        "ix_external_comparison_run_external_file_sha256",
        table_name="external_comparison_run",
    )
    op.drop_table("external_comparison_run")
