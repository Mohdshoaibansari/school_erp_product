"""D13: user_profile.admin permission for admin roles.

Adds user_profile.admin permission for Admin/CD/institution_admin.
Enables admin management of any profile via Casbin check.

Revision ID: 019
Down revision: 018
"""

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure user_profile.admin permission exists
    op.execute(
        "INSERT INTO permission (id, name, description, resource, action) "
        "VALUES (gen_random_uuid(), 'user_profile.admin', 'Manage any user profile', 'user_profile', 'admin') "
        "ON CONFLICT (name) DO NOTHING"
    )

    # Admin roles get user_profile.admin with appropriate scope
    admin_roles_tenant = ["client_director"]
    admin_roles_institution = ["Admin", "institution_admin"]

    for role_name in admin_roles_tenant:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'tenant' "
            "FROM role r, permission p "
            f"WHERE r.name = '{role_name}' AND p.name = 'user_profile.admin' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )

    for role_name in admin_roles_institution:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'institution' "
            "FROM role r, permission p "
            f"WHERE r.name = '{role_name}' AND p.name = 'user_profile.admin' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )


def downgrade() -> None:
    # Remove user_profile.admin for all roles
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE name = 'user_profile.admin')"
    )
    # Remove the permission itself
    op.execute("DELETE FROM permission WHERE name = 'user_profile.admin'")
