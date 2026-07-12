"""C-03 Authentication — login_attempt table, RLS, platform owner seed

Revision ID: 003_c03_authentication
Revises: 002_c02_identity_user_management
Create Date: 2026-07-11 12:00:00.000000

Implements:
- Tasks 2.1: login_attempt table
- Tasks 2.2: RLS policies on login_attempt
- Tasks 2.3: Seed platform owner app_user row (data-only, no Supabase call)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "003_c03_authentication"
down_revision = "002_c02_identity_user_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — login_attempt table (D11, D28a, D33, AC-5, AC-21, AC-22)
    # ============================================================

    # 2.1 login_attempt table
    op.create_table(
        "login_attempt",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("ip_address", sa.Text, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ============================================================
    # Section 2 — RLS policies on login_attempt (D11, AC-5)
    # ============================================================

    # 2.2 Enable RLS + create client_id-matching policy
    op.execute("ALTER TABLE login_attempt ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE login_attempt FORCE ROW LEVEL SECURITY")
    # SELECT policy: platform owner OR client_id match
    op.execute("""
        CREATE POLICY login_attempt_tenant_select ON login_attempt
        FOR SELECT
        USING (
            is_platform_owner()
            OR client_id = current_client_id()
        )
    """)
    # INSERT policy: platform owner OR same client_id
    op.execute("""
        CREATE POLICY login_attempt_tenant_insert ON login_attempt
        FOR INSERT
        WITH CHECK (
            is_platform_owner()
            OR client_id = current_client_id()
        )
    """)
    # UPDATE policy: platform owner OR same client_id
    op.execute("""
        CREATE POLICY login_attempt_tenant_update ON login_attempt
        FOR UPDATE
        USING (
            is_platform_owner()
            OR client_id = current_client_id()
        )
        WITH CHECK (
            is_platform_owner()
            OR client_id = current_client_id()
        )
    """)
    # DELETE policy: platform owner only (tenants cannot delete)
    op.execute("""
        CREATE POLICY login_attempt_tenant_delete ON login_attempt
        FOR DELETE
        USING (is_platform_owner())
    """)

    # Grant permissions to test_tenant_user
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_tenant_user")

    # ============================================================
    # Section 3 — Seed platform owner app_user row (D30, data-only)
    # ============================================================

    # 2.3 Insert platform owner app_user row (no Supabase call)
    # The bootstrap CLI will create the matching Supabase Auth user
    op.execute("""
        INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status)
        SELECT
            gen_random_uuid(),
            c.id,
            i.id,
            'platform@school-erp.com',
            'Platform Owner',
            (SELECT id FROM user_category WHERE name = 'Executive Leadership' LIMIT 1),
            'active'
        FROM client c
        CROSS JOIN LATERAL (
            SELECT id FROM institution WHERE client_id = c.id LIMIT 1
        ) i
        WHERE c.slug = 'platform'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Drop login_attempt table (RLS policies drop with it)
    op.drop_table("login_attempt")
