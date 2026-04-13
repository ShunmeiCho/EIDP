"""add null-safe department natural key index

Revision ID: 94884a1f8586
Revises: 0460bf821bfe
Create Date: 2026-04-13 14:24:23.339720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94884a1f8586'
down_revision: Union[str, Sequence[str], None] = '0460bf821bfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add null-safe unique index on department natural key.

    PostgreSQL treats NULLs as distinct in unique constraints, so
    (school_id=1, name='X', NULL, NULL, NULL) can appear multiple times.
    This index uses COALESCE to treat NULLs as empty/zero for uniqueness.
    """
    op.execute(sa.text("""
        CREATE UNIQUE INDEX idx_department_natural_key_nullsafe
        ON department (
            school_id,
            canonical_name,
            COALESCE(course_type, ''),
            COALESCE(course_name, ''),
            COALESCE(duration_years, 0)
        )
    """))


def downgrade() -> None:
    """Remove null-safe unique index."""
    op.drop_index("idx_department_natural_key_nullsafe", table_name="department")
