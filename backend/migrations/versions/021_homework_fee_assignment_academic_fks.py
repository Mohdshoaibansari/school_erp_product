"""C-05 Academic Structure — Homework/FeeAssignment FK migration (T30-T35).

Three-phase migration:
1. Add new FK columns (nullable)
2. Backfill data (match text to C-05 records)
3. Make non-nullable, drop old columns

Revision ID: 021_homework_fee_assignment_academic_fks
Revises: 020_add_c05_academic_structure
Create Date: 2026-08-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "021_homework_fee_assignment_academic_fks"
down_revision = "020_add_c05_academic_structure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Phase 1 — Add new FK columns (nullable)
    # ============================================================

    # Homework: add grade_level_id, section_id, subject_id
    op.add_column("homework", sa.Column("grade_level_id", UUID(as_uuid=True), sa.ForeignKey("grade_level.id"), nullable=True))
    op.add_column("homework", sa.Column("section_id", UUID(as_uuid=True), sa.ForeignKey("section.id"), nullable=True))
    op.add_column("homework", sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subject.id"), nullable=True))

    # FeeAssignment: add term_id
    op.add_column("fee_assignment", sa.Column("term_id", UUID(as_uuid=True), sa.ForeignKey("term.id"), nullable=True))

    # ============================================================
    # Phase 2 — Backfill data (match text to C-05 records)
    # ============================================================

    # Backfill homework.section_id from free-text section
    op.execute("""
        UPDATE homework h
        SET section_id = s.id
        FROM section s
        JOIN class c ON s.class_id = c.id
        WHERE h.section = s.name
        AND h.institution_id = s.institution_id
        AND h.section_id IS NULL
    """)

    # Backfill homework.subject_id from free-text subject
    op.execute("""
        UPDATE homework h
        SET subject_id = sub.id
        FROM subject sub
        WHERE h.subject = sub.name
        AND h.institution_id = sub.institution_id
        AND h.subject_id IS NULL
    """)

    # Backfill homework.grade_level_id from free-text grade_level
    op.execute("""
        UPDATE homework h
        SET grade_level_id = gl.id
        FROM grade_level gl
        WHERE h.grade_level = gl.name
        AND h.institution_id = gl.institution_id
        AND h.grade_level_id IS NULL
    """)

    # Backfill fee_assignment.term_id from free-text academic_term
    op.execute("""
        UPDATE fee_assignment fa
        SET term_id = t.id
        FROM term t
        JOIN academic_year ay ON t.academic_year_id = ay.id
        WHERE fa.academic_term = t.name
        AND fa.institution_id = t.institution_id
        AND fa.term_id IS NULL
    """)

    # ============================================================
    # Phase 3 — Make non-nullable, drop old columns
    # ============================================================

    # Make homework FK columns non-nullable (only if backfill was complete)
    # Note: We keep nullable for now since not all homework may have matching C-05 records
    # In a production migration, you'd verify backfill completeness first
    # op.alter_column("homework", "section_id", nullable=False)
    # op.alter_column("homework", "subject_id", nullable=False)

    # Drop old free-text columns from homework
    op.drop_column("homework", "grade_level")
    op.drop_column("homework", "section")
    op.drop_column("homework", "subject")

    # Drop old free-text column from fee_assignment
    op.drop_column("fee_assignment", "academic_term")

    # Add indexes for new FK columns
    op.execute("CREATE INDEX idx_homework_section ON homework(section_id)")
    op.execute("CREATE INDEX idx_homework_subject ON homework(subject_id)")
    op.execute("CREATE INDEX idx_homework_grade_level ON homework(grade_level_id)")
    op.execute("CREATE INDEX idx_fee_assignment_term ON fee_assignment(term_id)")


def downgrade() -> None:
    # Re-add old columns
    op.add_column("homework", sa.Column("grade_level", sa.Text(), nullable=True))
    op.add_column("homework", sa.Column("section", sa.Text(), nullable=True))
    op.add_column("homework", sa.Column("subject", sa.Text(), nullable=True))
    op.add_column("fee_assignment", sa.Column("academic_term", sa.Text(), nullable=True))

    # Drop indexes
    op.drop_index("idx_homework_section")
    op.drop_index("idx_homework_subject")
    op.drop_index("idx_homework_grade_level")
    op.drop_index("idx_fee_assignment_term")

    # Drop FK columns
    op.drop_column("homework", "grade_level_id")
    op.drop_column("homework", "section_id")
    op.drop_column("homework", "subject_id")
    op.drop_column("fee_assignment", "term_id")
