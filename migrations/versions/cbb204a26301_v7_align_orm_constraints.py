"""v7 align ORM constraints

Revision ID: cbb204a26301
Revises: 172e4c8ae384
Create Date: 2026-04-12 20:57:00.758021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbb204a26301'
down_revision: Union[str, Sequence[str], None] = '172e4c8ae384'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Align DB schema with ORM: dedup, add natural key constraints, fix duration_years type."""
    conn = op.get_bind()

    # Fix department.duration_years: integer -> numeric(3,1) to support fractional years
    op.alter_column(
        "department", "duration_years",
        type_=sa.Numeric(3, 1),
        existing_type=sa.Integer(),
        existing_nullable=True,
        postgresql_using="duration_years::numeric(3,1)",
    )

    # Merge duplicate departments before adding unique constraint.
    # Strategy: keep the department with the lowest id (survivor).
    # For yearly/change rows on duplicate departments:
    #   - Delete yearly rows that would collide with the survivor's existing rows
    #   - Reassign remaining yearly/change rows to the survivor
    #   - Delete the duplicate department rows

    # Step 1: Delete department_yearly rows from duplicates that would conflict
    # (same dept natural key + fiscal_year + revision already exists on survivor)
    conn.execute(sa.text("""
        WITH dups AS (
            SELECT id, school_id, canonical_name, course_type, course_name, duration_years,
                   ROW_NUMBER() OVER (
                       PARTITION BY school_id, canonical_name, course_type, course_name, duration_years
                       ORDER BY id
                   ) AS rn
            FROM department
        ),
        survivors AS (
            SELECT id AS survivor_id, school_id, canonical_name, course_type, course_name, duration_years
            FROM dups WHERE rn = 1
        ),
        to_merge AS (
            SELECT d.id AS old_id, s.survivor_id
            FROM dups d
            JOIN survivors s ON d.school_id = s.school_id
                AND d.canonical_name = s.canonical_name
                AND (d.course_type IS NOT DISTINCT FROM s.course_type)
                AND (d.course_name IS NOT DISTINCT FROM s.course_name)
                AND (d.duration_years IS NOT DISTINCT FROM s.duration_years)
            WHERE d.rn > 1
        ),
        conflicting_yearly AS (
            SELECT dy.id
            FROM department_yearly dy
            JOIN to_merge tm ON dy.department_id = tm.old_id
            WHERE EXISTS (
                SELECT 1 FROM department_yearly dy2
                WHERE dy2.department_id = tm.survivor_id
                  AND dy2.fiscal_year = dy.fiscal_year
                  AND dy2.revision = dy.revision
            )
        )
        DELETE FROM department_yearly WHERE id IN (SELECT id FROM conflicting_yearly)
    """))

    # Step 2: Reassign remaining yearly rows to survivor
    conn.execute(sa.text("""
        WITH dups AS (
            SELECT id, school_id, canonical_name, course_type, course_name, duration_years,
                   ROW_NUMBER() OVER (
                       PARTITION BY school_id, canonical_name, course_type, course_name, duration_years
                       ORDER BY id
                   ) AS rn
            FROM department
        ),
        survivors AS (
            SELECT id AS survivor_id, school_id, canonical_name, course_type, course_name, duration_years
            FROM dups WHERE rn = 1
        ),
        to_merge AS (
            SELECT d.id AS old_id, s.survivor_id
            FROM dups d
            JOIN survivors s ON d.school_id = s.school_id
                AND d.canonical_name = s.canonical_name
                AND (d.course_type IS NOT DISTINCT FROM s.course_type)
                AND (d.course_name IS NOT DISTINCT FROM s.course_name)
                AND (d.duration_years IS NOT DISTINCT FROM s.duration_years)
            WHERE d.rn > 1
        )
        UPDATE department_yearly SET department_id = tm.survivor_id
        FROM to_merge tm WHERE department_yearly.department_id = tm.old_id
    """))

    # Step 3: Reassign department_change rows
    conn.execute(sa.text("""
        WITH dups AS (
            SELECT id, school_id, canonical_name, course_type, course_name, duration_years,
                   ROW_NUMBER() OVER (
                       PARTITION BY school_id, canonical_name, course_type, course_name, duration_years
                       ORDER BY id
                   ) AS rn
            FROM department
        ),
        survivors AS (
            SELECT id AS survivor_id, school_id, canonical_name, course_type, course_name, duration_years
            FROM dups WHERE rn = 1
        ),
        to_merge AS (
            SELECT d.id AS old_id, s.survivor_id
            FROM dups d
            JOIN survivors s ON d.school_id = s.school_id
                AND d.canonical_name = s.canonical_name
                AND (d.course_type IS NOT DISTINCT FROM s.course_type)
                AND (d.course_name IS NOT DISTINCT FROM s.course_name)
                AND (d.duration_years IS NOT DISTINCT FROM s.duration_years)
            WHERE d.rn > 1
        )
        UPDATE department_change SET department_id = tm.survivor_id
        FROM to_merge tm WHERE department_change.department_id = tm.old_id
    """))

    # Step 4: Delete duplicate department rows
    conn.execute(sa.text("""
        WITH dups AS (
            SELECT id, school_id, canonical_name, course_type, course_name, duration_years,
                   ROW_NUMBER() OVER (
                       PARTITION BY school_id, canonical_name, course_type, course_name, duration_years
                       ORDER BY id
                   ) AS rn
            FROM department
        )
        DELETE FROM department WHERE id IN (SELECT id FROM dups WHERE rn > 1)
    """))

    # Now safe to add constraints
    op.create_unique_constraint(
        "uq_school_natural_key", "school",
        ["prefecture", "corporation_name", "school_name"],
    )

    op.create_unique_constraint(
        "uq_department_natural_key", "department",
        ["school_id", "canonical_name", "course_type", "course_name", "duration_years"],
    )


def downgrade() -> None:
    """Reverse v7 changes."""
    op.drop_constraint("uq_department_natural_key", "department", type_="unique")
    op.drop_constraint("uq_school_natural_key", "school", type_="unique")
    op.alter_column(
        "department", "duration_years",
        type_=sa.Integer(),
        existing_type=sa.Numeric(3, 1),
        existing_nullable=True,
    )
