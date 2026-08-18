"""C-02 Identity Person-Model Revamp (T-01, T-02).

Clean-cut migration: introduces `person` table, adds `person_id` FKs to
app_user and client_user, drops user_category_id from both account tables,
drops user_profile and user_category tables, adds RLS on person, and removes
user_profile permissions from role_permission/permission.

Revision ID: 022_person_model_revamp
Revises: 021_homework_fee_assignment_academic_fks
Create Date: 2026-08-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "022_person_model_revamp"
down_revision = "021_homework_fee_academic_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. Create person table
    # ============================================================
    op.create_table(
        "person",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("blood_group", sa.String(10), nullable=True),
        sa.Column("photo", sa.String(500), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("demographics", JSONB, nullable=True),
        sa.Column(
            "status",
            sa.String(25),
            nullable=False,
            server_default="Active",
        ),
        sa.Column("is_minor", sa.Boolean(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # CHECK constraint on person.status
    op.execute(
        "ALTER TABLE person ADD CONSTRAINT chk_person_status "
        "CHECK (status IN ('Active','Inactive','Deceased','ErasureRequested','Anonymized'))"
    )

    # ============================================================
    # 2. Add person_id to app_user and client_user (nullable FK)
    # ============================================================
    op.add_column("app_user", sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("person.id"), nullable=True))
    op.add_column("client_user", sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("person.id"), nullable=True))

    # ============================================================
    # 3. Drop user_category_id from app_user
    # ============================================================
    op.drop_constraint("app_user_user_category_id_fkey", "app_user", type_="foreignkey")
    op.drop_column("app_user", "user_category_id")

    # ============================================================
    # 4. Drop user_category_id from client_user
    # ============================================================
    op.drop_constraint("client_user_user_category_id_fkey", "client_user", type_="foreignkey")
    op.drop_column("client_user", "user_category_id")

    # ============================================================
    # 5. Drop user_profile table
    # ============================================================
    op.drop_table("user_profile")

    # ============================================================
    # 6. Drop user_category table
    # ============================================================
    op.drop_table("user_category")

    # ============================================================
    # 7. Remove user_profile permissions from role_permission + permission
    # ============================================================
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE resource = 'user_profile')"
    )
    op.execute("DELETE FROM permission WHERE resource = 'user_profile'")

    # ============================================================
    # 8. RLS on person (tenant-scoped, same pattern as app_user)
    # ============================================================
    op.execute("ALTER TABLE person ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE person FORCE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY person_tenant_select ON person FOR SELECT "
        "USING (is_platform_owner() OR client_id = current_client_id())"
    )
    op.execute(
        "CREATE POLICY person_tenant_insert ON person FOR INSERT "
        "WITH CHECK (is_platform_owner() OR client_id = current_client_id())"
    )
    op.execute(
        "CREATE POLICY person_tenant_update ON person FOR UPDATE "
        "USING (is_platform_owner() OR client_id = current_client_id()) "
        "WITH CHECK (is_platform_owner() OR client_id = current_client_id())"
    )
    op.execute(
        "CREATE POLICY person_tenant_delete ON person FOR DELETE "
        "USING (is_platform_owner())"
    )

    # ============================================================
    # 9. Grant permissions
    # ============================================================
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON person TO test_tenant_user")

    # ============================================================
    # 10. Index on person.client_id
    # ============================================================
    op.execute("CREATE INDEX ix_person_client_id ON person(client_id)")


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS person_tenant_select ON person")
    op.execute("DROP POLICY IF EXISTS person_tenant_insert ON person")
    op.execute("DROP POLICY IF EXISTS person_tenant_update ON person")
    op.execute("DROP POLICY IF EXISTS person_tenant_delete ON person")

    # Drop index
    op.execute("DROP INDEX IF EXISTS ix_person_client_id")

    # Drop person table
    op.drop_table("person")

    # Re-create user_category table
    op.create_table(
        "user_category",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
    )

    # Re-create user_profile table
    op.create_table(
        "user_profile",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("user_account.id"), unique=True, nullable=False),
        sa.Column("photo", sa.String(500), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("blood_group", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Re-add user_category_id to client_user
    op.add_column("client_user", sa.Column("user_category_id", UUID(as_uuid=True), sa.ForeignKey("user_category.id"), nullable=True))
    # Re-add user_category_id to app_user
    op.add_column("app_user", sa.Column("user_category_id", UUID(as_uuid=True), sa.ForeignKey("user_category.id"), nullable=True))

    # Drop person_id from client_user and app_user
    op.drop_column("client_user", "person_id")
    op.drop_column("app_user", "person_id")
