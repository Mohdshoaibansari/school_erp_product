"""C-01 create all tables, RLS policies, and seed lookups

Revision ID: 001_c01_initial
Revises:
Create Date: 2026-07-06 06:00:00.000000

Implements tasks 2.1-2.4 (entity tables), 3.1-3.4 (lookup tables + seeds),
4.1-4.4 (lifecycle/transfer/approval tables), 5.1-5.4 (RLS policies).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "001_c01_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 3 — Lookup tables (Q2, AC-20)
    # ============================================================

    # 3.1 legal_entity_type
    op.create_table(
        "legal_entity_type",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    # 3.2 org_unit_type
    op.create_table(
        "org_unit_type",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    # 3.3 institution_type_name
    op.create_table(
        "institution_type_name",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    # ============================================================
    # Section 2 — C-01 entity tables (D2, D4, D5, D6, D7)
    # ============================================================

    # 2.1 client table (D4) — NO client_id column (Q1)
    op.create_table(
        "client",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(63), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("legal_entity_type_id", UUID(as_uuid=True), sa.ForeignKey("legal_entity_type.id"), nullable=False),
        sa.Column("tax_registration_number", sa.String(100), nullable=True),
        sa.Column("primary_contact_email", sa.String(255), nullable=False),
        sa.Column("primary_contact_phone", sa.String(50), nullable=True),
        sa.Column("billing_contact_email", sa.String(255), nullable=True),
        sa.Column("address_id", UUID(as_uuid=True), nullable=True),  # FK → C-13 (future)
        sa.Column("current_lifecycle_status", sa.String(20), nullable=False, server_default="prospective"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 2.3 institution_type table (D7)
    op.create_table(
        "institution_type",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name_id", UUID(as_uuid=True), sa.ForeignKey("institution_type_name.id"), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("default_org_unit_template", JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2.2 institution table (D5)
    op.create_table(
        "institution",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_type_id", UUID(as_uuid=True), sa.ForeignKey("institution_type.id"), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("primary_contact_email", sa.String(255), nullable=True),
        sa.Column("primary_contact_phone", sa.String(50), nullable=True),
        sa.Column("address_id", UUID(as_uuid=True), nullable=True),  # FK → C-13 (future)
        sa.Column("current_lifecycle_status", sa.String(20), nullable=False, server_default="onboarding"),
        sa.Column("established_year", sa.Integer, nullable=True),
        sa.Column("affiliation_number", sa.String(100), nullable=True),
        sa.Column("affiliation_board", sa.String(100), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("client_id", "code", name="uq_institution_client_code"),
    )

    # 2.4 org_unit table (D6)
    op.create_table(
        "org_unit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("org_unit.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type_id", UUID(as_uuid=True), sa.ForeignKey("org_unit_type.id"), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("current_lifecycle_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("institution_id", "code", name="uq_org_unit_institution_code"),
    )

    # ============================================================
    # Section 4 — Lifecycle/transfer/approval tables (D8, D9, D12, Q3)
    # ============================================================

    # 4.4 approval table (Q3)
    op.create_table(
        "approval",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("context_type", sa.String(50), nullable=True),
        sa.Column("context_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
    )

    # 4.1 client_lifecycle_event table (D8)
    op.create_table(
        "client_lifecycle_event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("entered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approval.id"), nullable=True),
    )

    # 4.2 institution_lifecycle_event table (D9)
    op.create_table(
        "institution_lifecycle_event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("entered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approval.id"), nullable=True),
    )

    # 4.3 ownership_transfer_event table (D12)
    op.create_table(
        "ownership_transfer_event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("from_client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("to_client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=False),
        sa.Column("consent_source", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("consent_dest", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("transferred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("approval_id", UUID(as_uuid=True), sa.ForeignKey("approval.id"), nullable=True),
    )

    # ============================================================
    # Section 5 — RLS policies (D1, Q1, AC-1, AC-14) — raw SQL
    # ============================================================

    # Helper functions for RLS (GUC-based tenant context)
    op.execute("""
        CREATE OR REPLACE FUNCTION current_client_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.current_client_id', true), '')::uuid;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION is_platform_owner()
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN COALESCE(current_setting('app.is_platform_owner', true) = 'true', false);
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # 5.2 — Self-visible RLS on client table (Q1, AC-14)
    # FORCE RLS so even the table owner (postgres) is subject to RLS in tests.
    # Production roles (non-owner) are always subject to RLS anyway.
    op.execute("ALTER TABLE client ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY client_self_visible ON client
        FOR SELECT
        USING (
            is_platform_owner()
            OR id = current_client_id()
        )
    """)
    # Allow platform owners to insert/update clients; tenant users cannot
    op.execute("""
        CREATE POLICY client_platform_write ON client
        FOR ALL
        USING (is_platform_owner())
        WITH CHECK (is_platform_owner())
    """)

    # 5.1 — client_id-matching RLS on every tenant-scoped table (AC-1)
    _tenant_scoped_tables = [
        "institution",
        "org_unit",
        "client_lifecycle_event",
        "institution_lifecycle_event",
        "ownership_transfer_event",
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

    # 5.4 — Platform Owner bypass is via is_platform_owner() in all policies above (D11)

    # Create a non-superuser role for RLS testing.
    # postgres is a superuser and bypasses RLS even with FORCE; this role is subject to RLS.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'test_tenant_user') THEN
                CREATE ROLE test_tenant_user NOBYPASSRLS NOSUPERUSER;
            END IF;
        END
        $$;
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_tenant_user")
    op.execute("GRANT USAGE ON SCHEMA public TO test_tenant_user")
    # Grant test_tenant_user to postgres so tests can SET ROLE to a non-BYPASSRLS role
    op.execute("GRANT test_tenant_user TO postgres")

    # ============================================================
    # Section 3.4 — Seed initial lookup data (Q2, AC-20)
    # ============================================================

    # Legal entity types (D4)
    op.execute("""
        INSERT INTO legal_entity_type (id, name) VALUES
        (gen_random_uuid(), 'Sole Proprietor'),
        (gen_random_uuid(), 'Partnership'),
        (gen_random_uuid(), 'Pvt Ltd'),
        (gen_random_uuid(), 'Trust'),
        (gen_random_uuid(), 'Society')
    """)

    # OrgUnit types (D6)
    op.execute("""
        INSERT INTO org_unit_type (id, name) VALUES
        (gen_random_uuid(), 'Department'),
        (gen_random_uuid(), 'Faculty'),
        (gen_random_uuid(), 'Grade'),
        (gen_random_uuid(), 'Division'),
        (gen_random_uuid(), 'Section'),
        (gen_random_uuid(), 'Class'),
        (gen_random_uuid(), 'Program'),
        (gen_random_uuid(), 'Batch'),
        (gen_random_uuid(), 'Course')
    """)

    # InstitutionType names (D7)
    op.execute("""
        INSERT INTO institution_type_name (id, name) VALUES
        (gen_random_uuid(), 'School'),
        (gen_random_uuid(), 'College'),
        (gen_random_uuid(), 'University'),
        (gen_random_uuid(), 'Coaching Institute')
    """)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("ownership_transfer_event")
    op.drop_table("institution_lifecycle_event")
    op.drop_table("client_lifecycle_event")
    op.drop_table("approval")
    op.drop_table("org_unit")
    op.drop_table("institution")
    op.drop_table("institution_type")
    op.drop_table("client")
    op.drop_table("institution_type_name")
    op.drop_table("org_unit_type")
    op.drop_table("legal_entity_type")
    op.execute("DROP FUNCTION IF EXISTS is_platform_owner()")
    op.execute("DROP FUNCTION IF EXISTS current_client_id()")
    # Do not drop the test_tenant_user role (it's idempotent and reusable across migration runs)
