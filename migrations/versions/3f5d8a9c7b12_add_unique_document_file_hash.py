"""add unique document file hash index

Revision ID: 3f5d8a9c7b12
Revises: b7a1f3d5c9e2
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f5d8a9c7b12"
down_revision: str | Sequence[str] | None = "b7a1f3d5c9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enforce one stored Document row per content hash."""
    conn = op.get_bind()

    # Preserve rows on existing databases while making future inserts safe:
    # the first row per content hash keeps the hash, later duplicate rows lose
    # the derived hash metadata and leave the ingest queue so the unique index
    # can be created without reprocessing duplicate PDFs.
    conn.execute(sa.text("""
        WITH duplicate_hashes AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY file_hash
                    ORDER BY id
                ) AS rn
            FROM document
            WHERE file_hash IS NOT NULL
        )
        UPDATE document
        SET
            file_hash = NULL,
            ingest_status = CASE
                WHEN ingest_status IN ('non_target', 'permanent_error', 'no_file') THEN ingest_status
                ELSE 'school_mismatch'
            END
        WHERE id IN (
            SELECT id FROM duplicate_hashes WHERE rn > 1
        )
    """))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_document_file_hash"))
    op.create_index("uq_document_file_hash", "document", ["file_hash"], unique=True)


def downgrade() -> None:
    """Restore the previous non-unique hash lookup index."""
    op.drop_index("uq_document_file_hash", table_name="document")
    op.create_index("ix_document_file_hash", "document", ["file_hash"])
