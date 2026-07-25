"""Platform owner separation — client table RLS bypass

Revision ID: 007_platform_owner_rls
Revises: 006_homework_module
"""
from alembic import op

revision = "007_platform_owner_rls"
down_revision = "006_homework_module"
branch_labels = None
depends_on = None


def upgrade():
    # Add RLS policy on client table: platform owner bypass via session variable
    op.execute("""
        CREATE POLICY platform_owner_client_access ON client
        FOR ALL
        USING (NULLIF(current_setting('app.is_platform_owner', true), '') = 'true')
        WITH CHECK (NULLIF(current_setting('app.is_platform_owner', true), '') = 'true');
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS platform_owner_client_access ON client;")
