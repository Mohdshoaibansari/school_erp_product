"""Client User Bootstrap — two-tier user model tables + data migration

Revision ID: 011_client_user_bootstrap
Revises: 010_add_config_keys
Create Date: 2026-08-01

Creates client_user (client-leadership-scope users: Client Director + future
Client Admins / Billing Contacts) and client_user_lifecycle_event (mirror
of user_lifecycle_event for client_user). Moves any app_user rows with
institution_id IS NULL into client_user (the old Client Director pattern).
Adds RLS: PO bypass (app.is_platform_owner=true) + CD own-row
(id = current_user_id() from session variable).

D1, D3, D5, D8, D10, D13, D14 from the client-user-bootstrap PRD.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "011_client_user_bootstrap"
down_revision = "010_add_config_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — client_user table (D1, D3)
    # ============================================================
    op.create_table(
        "client_user",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("user_category_id", UUID(as_uuid=True), sa.ForeignKey("user_category.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("role.id"), nullable=False),
        sa.Column("lifecycle_status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # NO institution_id column — CD manages the whole client (D1)

    # Index on client_id for list-by-client queries
    op.create_index("ix_client_user_client_id", "client_user", ["client_id"])

    # ============================================================
    # Section 2 — client_user_lifecycle_event table (D10)
    #   Mirrors user_lifecycle_event but FKs to client_user instead of app_user.
    #   No client_id column — inherited from client_user via FK.
    # ============================================================
    op.create_table(
        "client_user_lifecycle_event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_user_id", UUID(as_uuid=True), sa.ForeignKey("client_user.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("entered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ============================================================
    # Section 3 — RLS on client_user (D5, D8)
    # ============================================================
    op.execute("ALTER TABLE client_user ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_user FORCE ROW LEVEL SECURITY")

    # PO bypass: PO (with app.is_platform_owner=true) can CRUD any row
    op.execute("""
        CREATE POLICY client_user_platform_owner_all ON client_user
        FOR ALL
        USING (NULLIF(current_setting('app.is_platform_owner', true), '') = 'true')
        WITH CHECK (NULLIF(current_setting('app.is_platform_owner', true), '') = 'true');
    """)

    # CD own-row SELECT: CD (with app.current_user_id set) can read own row
    op.execute("""
        CREATE POLICY client_user_cd_select_own ON client_user
        FOR SELECT
        USING (
            id = current_setting('app.current_user_id', true)::uuid
        );
    """)

    # CD own-row UPDATE: CD can update own row (e.g., display name)
    op.execute("""
        CREATE POLICY client_user_cd_update_own ON client_user
        FOR UPDATE
        USING (
            id = current_setting('app.current_user_id', true)::uuid
        )
        WITH CHECK (
            id = current_setting('app.current_user_id', true)::uuid
        );
    """)

    # Grant table permissions to test_tenant_user
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON client_user TO test_tenant_user")
    op.execute("GRANT SELECT, INSERT ON client_user_lifecycle_event TO test_tenant_user")

    # ============================================================
    # Section 4 — Data migration: move NULL-institution_id
    #   app_user rows to client_user (D13)
    # ============================================================

    # Find the 'client_director' role ID
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM role WHERE name = 'client_director'")
    ).fetchone()
    cd_role_id = str(result[0]) if result else None

    # Move rows where institution_id IS NULL from app_user → client_user
    if cd_role_id:
        null_rows = conn.execute(sa.text(
            "SELECT id, client_id, email, name, user_category_id, lifecycle_status "
            "FROM app_user WHERE institution_id IS NULL"
        )).fetchall()

        for row in null_rows:
            row_id, row_client_id, row_email, row_name, row_uc_id, row_ls = row

            # Insert into client_user
            conn.execute(sa.text(
                "INSERT INTO client_user (id, client_id, email, name, user_category_id, "
                "role_id, lifecycle_status) "
                "VALUES (:id, :client_id, :email, :name, :uc_id, :role_id, :lifecycle_status) "
                "ON CONFLICT DO NOTHING"
            ), {
                "id": row_id,
                "client_id": row_client_id,
                "email": row_email,
                "name": row_name,
                "uc_id": row_uc_id,
                "role_id": cd_role_id,
                "lifecycle_status": row_ls if row_ls else "active",
            })

            # Record the move as a lifecycle event
            conn.execute(sa.text(
                "INSERT INTO client_user_lifecycle_event (client_user_id, state, reason, actor) "
                "VALUES (:uid, :state, :reason, :actor)"
            ), {
                "uid": row_id,
                "state": row_ls if row_ls else "active",
                "reason": "Migrated from app_user (institution_id was NULL) by migration 011",
                "actor": "migration_011",
            })

            # Remove from app_user
            conn.execute(sa.text(
                "DELETE FROM app_user WHERE id = :id"
            ), {"id": row_id})

    # ============================================================
    # Section 5 — Post-migration assertion (D13)
    # ============================================================
    null_count = conn.execute(sa.text(
        "SELECT count(*) FROM app_user WHERE institution_id IS NULL"
    )).scalar()

    if null_count > 0:
        raise RuntimeError(
            f"Migration 011 assertion FAILED: {null_count} rows in app_user "
            f"still have institution_id IS NULL after data migration. "
            f"Cannot proceed to migration 012."
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Move client_user rows back to app_user that were originally migrated
    rows = conn.execute(sa.text(
        "SELECT id, client_id, email, name, user_category_id, lifecycle_status "
        "FROM client_user"
    )).fetchall()

    for row in rows:
        row_id, row_client_id, row_email, row_name, row_uc_id, row_ls = row

        conn.execute(sa.text(
            "INSERT INTO app_user (id, client_id, email, name, user_category_id, "
            "institution_id, lifecycle_status) "
            "VALUES (:id, :client_id, :email, :name, :uc_id, NULL, :lifecycle_status) "
            "ON CONFLICT DO NOTHING"
        ), {
            "id": row_id,
            "client_id": row_client_id,
            "email": row_email,
            "name": row_name,
            "uc_id": row_uc_id,
            "lifecycle_status": row_ls if row_ls else "active",
        })

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS client_user_cd_update_own ON client_user;")
    op.execute("DROP POLICY IF EXISTS client_user_cd_select_own ON client_user;")
    op.execute("DROP POLICY IF EXISTS client_user_platform_owner_all ON client_user;")

    # Drop tables
    op.drop_table("client_user_lifecycle_event")
    op.execute("DROP INDEX IF EXISTS ix_client_user_client_id")
    op.drop_table("client_user")
