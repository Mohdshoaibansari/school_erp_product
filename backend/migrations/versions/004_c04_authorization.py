"""C-04 Authorization — permission + role_permission tables, seed data, platform_owner role

Revision ID: 004_c04_authorization
Revises: 003_c03_authentication
Create Date: 2026-07-14 12:00:00.000000

Implements:
- Tasks 3.1-3.2: permission table + 26 seed rows (14 C-01 + 12 C-02)
- Tasks 3.3-3.4: role_permission table + ~40 seed rows (mapping C-02 roles → permissions)
- Task 3.5: platform_owner row in C-02's role table
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "004_c04_authorization"
down_revision = "003_c03_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — permission table (D8, D18, D30)
    # ============================================================

    op.create_table(
        "permission",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # No RLS — global data shared across all clients

    # ============================================================
    # Section 2 — role_permission table (D8)
    # ============================================================

    op.create_table(
        "role_permission",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("role.id"), nullable=False),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("permission.id"), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    # No RLS — global data shared across all clients

    # ============================================================
    # Section 3 — Seed 26 permissions (D18, AC-1, AC-2)
    # ============================================================

    # 14 C-01 permissions
    _c01_permissions = [
        ("client.read",       "View client details",              "client",          "read"),
        ("client.update",     "Update client details",            "client",          "update"),
        ("client.transfer_ownership", "Transfer client ownership","client",          "transfer_ownership"),
        ("client.transition_lifecycle", "Transition client lifecycle", "client",     "transition_lifecycle"),
        ("institution.read",  "View institution",                 "institution",     "read"),
        ("institution.create","Create a new institution",         "institution",     "create"),
        ("institution.update","Update institution details",       "institution",     "update"),
        ("institution.transition_lifecycle", "Transition institution lifecycle", "institution", "transition_lifecycle"),
        ("org_unit.read",     "View organizational unit",         "org_unit",        "read"),
        ("org_unit.create",   "Create an organizational unit",    "org_unit",        "create"),
        ("org_unit.update",   "Update an organizational unit",    "org_unit",        "update"),
        ("org_unit.delete",   "Delete an organizational unit",    "org_unit",        "delete"),
        ("org_unit.move",     "Move an organizational unit",      "org_unit",        "move"),
        ("institution_type.read", "View institution types",       "institution_type","read"),
    ]

    # 12 C-02 permissions
    _c02_permissions = [
        ("user.read",         "View user profile",                "user",            "read"),
        ("user.create",       "Create a new user",                "user",            "create"),
        ("user.update",       "Update user details",              "user",            "update"),
        ("user.suspend",      "Suspend or archive a user",        "user",            "suspend"),
        ("user_profile.read", "View user profile details",        "user_profile",    "read"),
        ("user_profile.update","Update user profile details",     "user_profile",    "update"),
        ("role_assignment.read",  "View role assignments",        "role_assignment",  "read"),
        ("role_assignment.create","Create a role assignment",     "role_assignment",  "create"),
        ("role_assignment.delete","Delete a role assignment",     "role_assignment",  "delete"),
        ("user_identifier.read",   "View user identifiers",       "user_identifier",   "read"),
        ("user_identifier.create", "Create a user identifier",    "user_identifier",   "create"),
        ("user_identifier.delete", "Delete a user identifier",    "user_identifier",   "delete"),
    ]

    all_permissions = _c01_permissions + _c02_permissions

    for name, desc, resource, action in all_permissions:
        # Escape single quotes in values
        safe_desc = desc.replace("'", "''") if desc else ""
        op.execute(sa.text(
            f"INSERT INTO permission (id, name, description, resource, action) "
            f"VALUES (gen_random_uuid(), '{name}', '{safe_desc}', '{resource}', '{action}') "
            f"ON CONFLICT (name) DO NOTHING"
        ))

    # ============================================================
    # Section 4 — Seed ~40 role_permission rows (D15, AC-3)
    # ============================================================

    # Helper: insert role_permission by (role_name, permission_name)
    _insert_rp = (
        "INSERT INTO role_permission (id, role_id, permission_id) "
        "SELECT gen_random_uuid(), r.id, p.id "
        "FROM role r, permission p "
        "WHERE r.name = '{role_name}' AND p.name = '{perm_name}' "
        "ON CONFLICT (role_id, permission_id) DO NOTHING"
    )

    # Admin: user.*, user_profile.*, role_assignment.*, user_identifier.*,
    #        institution.read, org_unit.*, institution_type.read
    _admin_perms = [
        "user.read", "user.create", "user.update", "user.suspend",
        "user_profile.read", "user_profile.update",
        "role_assignment.read", "role_assignment.create", "role_assignment.delete",
        "user_identifier.read", "user_identifier.create", "user_identifier.delete",
        "institution.read", "institution.update", "institution.transition_lifecycle",
        "org_unit.read", "org_unit.create", "org_unit.update", "org_unit.delete", "org_unit.move",
        "institution_type.read",
    ]
    for perm in _admin_perms:
        op.execute(sa.text(_insert_rp.format(role_name="Admin", perm_name=perm)))

    # Principal: user.read, role_assignment.read, user_identifier.read,
    #            institution.read, institution.update, org_unit.*, institution_type.read
    _principal_perms = [
        "user.read",
        "role_assignment.read",
        "user_identifier.read",
        "institution.read", "institution.update",
        "org_unit.read", "org_unit.create", "org_unit.update", "org_unit.delete", "org_unit.move",
        "institution_type.read",
    ]
    for perm in _principal_perms:
        op.execute(sa.text(_insert_rp.format(role_name="Principal", perm_name=perm)))

    # HOD: user.read, role_assignment.read,
    #      org_unit.read, org_unit.update, institution_type.read
    _hod_perms = [
        "user.read",
        "role_assignment.read",
        "org_unit.read", "org_unit.update",
        "institution_type.read",
    ]
    for perm in _hod_perms:
        op.execute(sa.text(_insert_rp.format(role_name="HOD", perm_name=perm)))

    # Teacher: user.read, user.update
    _teacher_perms = ["user.read", "user.update"]
    for perm in _teacher_perms:
        op.execute(sa.text(_insert_rp.format(role_name="Teacher", perm_name=perm)))

    # Staff: user.read, user.update
    for perm in _teacher_perms:
        op.execute(sa.text(_insert_rp.format(role_name="Staff", perm_name=perm)))

    # Student: user.read
    op.execute(sa.text(_insert_rp.format(role_name="Student", perm_name="user.read")))

    # Parent: user.read
    op.execute(sa.text(_insert_rp.format(role_name="Parent", perm_name="user.read")))

    # ============================================================
    # Section 5 — platform_owner role (D28, AC-3)
    # ============================================================

    op.execute(
        "INSERT INTO role (id, name) VALUES (gen_random_uuid(), 'platform_owner') "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("role_permission")
    op.drop_table("permission")
    op.execute("DELETE FROM role WHERE name = 'platform_owner'")
