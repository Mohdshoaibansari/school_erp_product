"""C-02 Identity & User Management — tables, RLS policies, seed data

Revision ID: 002_c02_identity_user_management
Revises: 001_c01_initial
Create Date: 2026-07-08 12:00:00.000000

Implements:
- Tasks 2.1-2.7: entity tables (user_category, role, user, user_profile,
  role_assignment, user_identifier, user_lifecycle_event)
- Tasks 3.1-3.2: seed data for user_category and role lookup tables
- Tasks 4.1-4.3: RLS policies on tenant-scoped tables
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "002_c02_identity_user_management"
down_revision = "001_c01_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 3 — Lookup tables (Decision 9, Decision 10)
    # ============================================================

    # 2.1 user_category lookup table
    op.create_table(
        "user_category",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    # 2.2 role lookup table
    op.create_table(
        "role",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    # ============================================================
    # Section 2 — C-02 entity tables (Decision 1, Decision 4, AC-4)
    # ============================================================

    # 2.3 user table — per-institution identity (Decision 1)
    # Table name "app_user" to avoid conflict with Postgres reserved word "user".
    op.create_table(
        "app_user",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("user_category_id", UUID(as_uuid=True), sa.ForeignKey("user_category.id"), nullable=False),
        sa.Column("lifecycle_status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2.4 user_profile table — 1:1 with user (Decision 5)
    op.create_table(
        "user_profile",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), unique=True, nullable=False),
        sa.Column("photo", sa.String(500), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("blood_group", sa.String(10), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2.5 role_assignment table (Decision 6)
    op.create_table(
        "role_assignment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("role.id"), nullable=False),
        sa.Column("scope", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2.6 user_identifier table (Decision 7)
    op.create_table(
        "user_identifier",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2.7 user_lifecycle_event table (Decision 8)
    op.create_table(
        "user_lifecycle_event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("entered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ============================================================
    # Section 4 — RLS policies (Decision 1, AC-1, AC-20) — raw SQL
    # ============================================================

    # 4.1 Enable FORCE RLS + create client_id-matching policy on tenant-scoped tables
    _tenant_scoped_tables = [
        "app_user",
        "role_assignment",
        "user_identifier",
        "user_lifecycle_event",
    ]

    for table_name in _tenant_scoped_tables:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        # SELECT policy: platform owner OR client_id match
        op.execute(f"""
            CREATE POLICY {table_name}_tenant_select ON {table_name}
            FOR SELECT
            USING (
                is_platform_owner()
                OR client_id = current_client_id()
            )
        """)
        # INSERT policy: platform owner OR same client_id
        op.execute(f"""
            CREATE POLICY {table_name}_tenant_insert ON {table_name}
            FOR INSERT
            WITH CHECK (
                is_platform_owner()
                OR client_id = current_client_id()
            )
        """)
        # UPDATE policy: platform owner OR same client_id
        op.execute(f"""
            CREATE POLICY {table_name}_tenant_update ON {table_name}
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
        op.execute(f"""
            CREATE POLICY {table_name}_tenant_delete ON {table_name}
            FOR DELETE
            USING (is_platform_owner())
        """)

    # 4.2 user_profile does NOT have RLS — accessed via User FK
    # 4.3 user_category and role do NOT have RLS — global/shared lookup tables

    # Grant permissions to test_tenant_user (created in 001_c01_initial)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_tenant_user")

    # ============================================================
    # Section 3 — Seed data (Decision 9, Decision 10, R6)
    # ============================================================

    # 3.1 Seed UserCategory lookup data
    op.execute("""
        INSERT INTO user_category (id, name) VALUES
        (gen_random_uuid(), 'Learner'),
        (gen_random_uuid(), 'Academic Staff'),
        (gen_random_uuid(), 'Academic Leadership'),
        (gen_random_uuid(), 'Administrative Staff'),
        (gen_random_uuid(), 'Executive Leadership')
    """)

    # 3.2 Seed Role lookup data
    op.execute("""
        INSERT INTO role (id, name) VALUES
        (gen_random_uuid(), 'Teacher'),
        (gen_random_uuid(), 'HOD'),
        (gen_random_uuid(), 'Principal'),
        (gen_random_uuid(), 'Student'),
        (gen_random_uuid(), 'Parent'),
        (gen_random_uuid(), 'Staff'),
        (gen_random_uuid(), 'Admin')
    """)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("user_lifecycle_event")
    op.drop_table("user_identifier")
    op.drop_table("role_assignment")
    op.drop_table("user_profile")
    op.drop_table("app_user")
    op.drop_table("role")
    op.drop_table("user_category")
