"""Fees module — tables, RLS, C-04 permission extension

Revision ID: 005_fees_module
Revises: 004_c04_authorization
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005_fees_module"
down_revision = "004_c04_authorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 2 — Fee tables
    # ============================================================

    op.create_table(
        "fee_type",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "fee_assignment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("fee_type_id", UUID(as_uuid=True), sa.ForeignKey("fee_type.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("academic_term", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("assigned_by", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "payment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("fee_assignment_id", UUID(as_uuid=True), sa.ForeignKey("fee_assignment.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("payment_method", sa.Text(), nullable=False),
        sa.Column("receipt_number", sa.Text(), nullable=True),
        sa.Column("reference_number", sa.Text(), nullable=True),
        sa.Column("recorded_by", UUID(as_uuid=True), sa.ForeignKey("app_user.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # ============================================================
    # RLS policies
    # ============================================================
    _tables = ["fee_type", "fee_assignment", "payment"]
    for tbl in _tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {tbl}_tenant_select ON {tbl} FOR SELECT
            USING (is_platform_owner() OR client_id = current_client_id())
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_tenant_insert ON {tbl} FOR INSERT
            WITH CHECK (is_platform_owner() OR client_id = current_client_id())
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_tenant_update ON {tbl} FOR UPDATE
            USING (is_platform_owner() OR client_id = current_client_id())
            WITH CHECK (is_platform_owner() OR client_id = current_client_id())
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_tenant_delete ON {tbl} FOR DELETE
            USING (is_platform_owner())
        """)

    # ============================================================
    # C-04 permission extension (D8, D15)
    # ============================================================
    _fee_permissions = [
        ("fee.read", "View fee types", "fee", "read"),
        ("fee.create", "Create a fee type", "fee", "create"),
        ("fee.update", "Update a fee type", "fee", "update"),
        ("fee.delete", "Delete a fee type", "fee", "delete"),
        ("fee_assignment.read", "View fee assignments", "fee_assignment", "read"),
        ("fee_assignment.create", "Assign fees to students", "fee_assignment", "create"),
        ("fee_assignment.update", "Update a fee assignment", "fee_assignment", "update"),
        ("fee_assignment.waive", "Waive a fee", "fee_assignment", "waive"),
        ("payment.read", "View payments", "payment", "read"),
        ("payment.create", "Record a payment", "payment", "create"),
        ("receipt.read", "View receipts", "receipt", "read"),
    ]
    for name, desc, resource, action in _fee_permissions:
        safe_desc = desc.replace("'", "''")
        op.execute(sa.text(
            f"INSERT INTO permission (id, name, description, resource, action) "
            f"VALUES (gen_random_uuid(), '{name}', '{safe_desc}', '{resource}', '{action}') "
            f"ON CONFLICT (name) DO NOTHING"
        ))

    # Role → permission mappings
    _insert_rp = (
        "INSERT INTO role_permission (id, role_id, permission_id) "
        "SELECT gen_random_uuid(), r.id, p.id FROM role r, permission p "
        "WHERE r.name = '{role}' AND p.name = '{perm}' "
        "ON CONFLICT (role_id, permission_id) DO NOTHING"
    )

    # Admin: all 11
    for name, _, _, _ in _fee_permissions:
        op.execute(sa.text(_insert_rp.format(role="Admin", perm=name)))

    # Principal: fee.read, fee_assignment.read, payment.read, receipt.read
    for name in ["fee.read", "fee_assignment.read", "payment.read", "receipt.read"]:
        op.execute(sa.text(_insert_rp.format(role="Principal", perm=name)))

    # HOD: fee_assignment.read, payment.read
    for name in ["fee_assignment.read", "payment.read"]:
        op.execute(sa.text(_insert_rp.format(role="HOD", perm=name)))

    # Teacher: fee_assignment.read
    op.execute(sa.text(_insert_rp.format(role="Teacher", perm="fee_assignment.read")))

    # Staff: fee_assignment.read
    op.execute(sa.text(_insert_rp.format(role="Staff", perm="fee_assignment.read")))

    # Student: fee_assignment.read, payment.read
    for name in ["fee_assignment.read", "payment.read"]:
        op.execute(sa.text(_insert_rp.format(role="Student", perm=name)))


def downgrade() -> None:
    op.drop_table("payment")
    op.drop_table("fee_assignment")
    op.drop_table("fee_type")
    # Note: permission/role_permission rows are NOT removed on downgrade
    # (they're idempotent ON CONFLICT DO NOTHING, safe to leave)
