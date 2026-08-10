"""C-04 Authorization Consolidation — Single Source of Truth.

Migrates C-01 hardcoded D11 permission matrix from policies.py to C-04's
role_permission DB table. Adds scope column, 9 missing permissions, and
C-01 role-permission mappings.

Revision ID: 016
Down revision: 015
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Add scope column to role_permission ──
    op.add_column(
        "role_permission",
        sa.Column("scope", sa.String(20), nullable=False, server_default="institution"),
    )

    # ── Step 2: Insert 9 missing permissions ──
    _new_permissions = [
        ("institution.archive", "Archive an institution", "institution", "archive"),
        ("institution.list", "List institutions", "institution", "list"),
        ("org_unit.archive", "Archive an org unit", "org_unit", "archive"),
        ("org_unit.reactivate", "Reactivate an org unit", "org_unit", "reactivate"),
        ("org_unit.reorder", "Reorder org units", "org_unit", "reorder"),
        ("institution_type.create", "Create institution types", "institution_type", "create"),
        ("institution_type.update", "Update institution types", "institution_type", "update"),
        ("user_profile.create", "Create user profile", "user_profile", "create"),
        ("user.delete", "Delete a user", "user", "delete"),
    ]

    for name, desc, resource, action in _new_permissions:
        safe_desc = desc.replace("'", "''")
        op.execute(
            f"INSERT INTO permission (id, name, description, resource, action) "
            f"VALUES (gen_random_uuid(), '{name}', '{safe_desc}', '{resource}', '{action}') "
            f"ON CONFLICT (name) DO NOTHING"
        )

    # ── Step 3: Migrate client_director role (tenant scope) ──
    # CD gets all Admin permissions plus CD-specific ones
    _cd_perms = [
        # CD-specific (C-01 D11 matrix)
        "institution.create", "institution.read", "institution.update",
        "institution.transition_lifecycle", "institution.archive", "institution.list",
        "client.read", "client.update",
        "org_unit.create", "org_unit.read", "org_unit.update", "org_unit.move",
        "org_unit.archive", "org_unit.reactivate", "org_unit.reorder", "org_unit.delete",
        # Admin permissions (CD has full admin access within tenant)
        "user.create", "user.read", "user.update", "user.suspend",
        "user_profile.read", "user_profile.update",
        "role_assignment.create", "role_assignment.read", "role_assignment.delete",
        "user_identifier.create", "user_identifier.read", "user_identifier.delete",
        "institution_type.read",
        "fee.create", "fee.read", "fee.update", "fee.delete",
        "fee_assignment.create", "fee_assignment.read", "fee_assignment.update", "fee_assignment.waive",
        "payment.create", "payment.read",
        "receipt.read",
        "homework.read",
        "submission.read",
        "grade.read",
    ]

    for perm_name in _cd_perms:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'tenant' "
            "FROM role r, permission p "
            f"WHERE r.name = 'client_director' AND p.name = '{perm_name}' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )

    # ── Step 4: Migrate institution_admin role (institution scope) ──
    _ia_perms = [
        "institution.read", "institution.update",
        "org_unit.create", "org_unit.read", "org_unit.update", "org_unit.move",
        "org_unit.archive", "org_unit.reactivate", "org_unit.reorder",
    ]

    for perm_name in _ia_perms:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'institution' "
            "FROM role r, permission p "
            f"WHERE r.name = 'institution_admin' AND p.name = '{perm_name}' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )

    # ── Step 5: Migrate cross_institution role (tenant scope, read-only) ──
    _ci_perms = ["client.read", "institution.read", "org_unit.read"]

    for perm_name in _ci_perms:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'tenant' "
            "FROM role r, permission p "
            f"WHERE r.name = 'cross_institution' AND p.name = '{perm_name}' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def downgrade() -> None:
    # Remove C-01 role-permission rows
    op.execute(
        "DELETE FROM role_permission WHERE role_id IN "
        "(SELECT id FROM role WHERE name IN "
        "('client_director', 'institution_admin', 'cross_institution'))"
    )

    # Remove 9 new permissions
    op.execute(
        "DELETE FROM permission WHERE name IN ("
        "'institution.archive', 'institution.list', "
        "'org_unit.archive', 'org_unit.reactivate', 'org_unit.reorder', "
        "'institution_type.create', 'institution_type.update', "
        "'user_profile.create', 'user.delete')"
    )

    # Drop scope column
    op.drop_column("role_permission", "scope")
