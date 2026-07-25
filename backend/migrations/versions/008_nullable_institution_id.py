"""Make institution_id nullable on app_user — Client Directors manage whole client.

Revision ID: 008_nullable_institution_id
Revises: 007_platform_owner_rls
"""
from alembic import op

revision = "008_nullable_institution_id"
down_revision = "007_platform_owner_rls"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("app_user", "institution_id", nullable=True)


def downgrade():
    op.alter_column("app_user", "institution_id", nullable=False)
