"""D13: UserProfile permission assignments.

Adds user_profile.create for admin roles and user_profile.update/read
for all roles. Enables self-service profile management.

Revision ID: 019
Down revision: 018
"""

from alembic import op
import sqlalchemy as sa

revision = "019b"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure user_profile.create permission exists
    op.execute(
        "INSERT INTO permission (id, name, description, resource, action) "
        "VALUES (gen_random_uuid(), 'user_profile.create', 'Create user profile', 'user_profile', 'create') "
        "ON CONFLICT (name) DO NOTHING"
    )

    # Admin roles get user_profile.create + read + update
    admin_roles = ["Admin", "client_director", "institution_admin"]
    for role_name in admin_roles:
        for perm_name in ["user_profile.create", "user_profile.read", "user_profile.update"]:
            op.execute(
                "INSERT INTO role_permission (id, role_id, permission_id, scope) "
                "SELECT gen_random_uuid(), r.id, p.id, 'institution' "
                "FROM role r, permission p "
                f"WHERE r.name = '{role_name}' AND p.name = '{perm_name}' "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            )

    # All roles get user_profile.read and user_profile.update
    all_roles = ["Teacher", "Staff", "Student", "Parent"]
    for role_name in all_roles:
        for perm_name in ["user_profile.read", "user_profile.update"]:
            op.execute(
                "INSERT INTO role_permission (id, role_id, permission_id, scope) "
                "SELECT gen_random_uuid(), r.id, p.id, 'institution' "
                "FROM role r, permission p "
                f"WHERE r.name = '{role_name}' AND p.name = '{perm_name}' "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            )


def downgrade() -> None:
    # Remove user_profile permissions for non-admin roles
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE resource = 'user_profile') "
        "AND role_id IN (SELECT id FROM role WHERE name IN ('Teacher', 'Staff', 'Student', 'Parent'))"
    )
    # Remove user_profile.create for admin roles
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE name = 'user_profile.create') "
        "AND role_id IN (SELECT id FROM role WHERE name IN ('Admin', 'client_director', 'institution_admin'))"
    )
