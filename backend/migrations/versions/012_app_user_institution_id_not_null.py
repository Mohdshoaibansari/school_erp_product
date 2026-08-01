"""app_user.institution_id → NOT NULL (BREAKING)

Revision ID: 012_app_user_institution_id_not_null
Revises: 011_client_user_bootstrap
Create Date: 2026-08-01

Enforces the invariant that every app_user row belongs to exactly one institution.
Safe because migration 011 moved all NULL institution_id rows to client_user.
If any NULL rows remain, the ALTER fails gracefully.

D13 from the client-user-bootstrap PRD.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "012_app_user_inst_id_not_null"
down_revision = "011_client_user_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Pre-condition: assert zero NULL institution_id rows remain
    null_count = conn.execute(sa.text(
        "SELECT count(*) FROM app_user WHERE institution_id IS NULL"
    )).scalar()

    if null_count > 0:
        raise RuntimeError(
            f"Migration 012 pre-condition FAILED: {null_count} rows in app_user "
            f"still have institution_id IS NULL. Run migration 011 first, then retry."
        )

    # Safe ALTER because the pre-condition passed
    op.alter_column(
        "app_user",
        "institution_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    # Reverse: restore the nullable behavior (pre-011, migration 008 era)
    op.alter_column(
        "app_user",
        "institution_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )
