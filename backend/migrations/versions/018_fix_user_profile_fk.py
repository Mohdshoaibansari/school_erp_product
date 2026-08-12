"""D13: UserProfile FK change to user_account.

user_profile.user_id FK changes from app_user.id to user_account.id.
Enables CD users (in client_user) to have profiles.

Revision ID: 018
Down revision: 017
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill: ensure all profile user_ids have user_account rows
    op.execute(
        "INSERT INTO user_account (id) "
        "SELECT DISTINCT up.user_id FROM user_profile up "
        "WHERE NOT EXISTS (SELECT 1 FROM user_account ua WHERE ua.id = up.user_id) "
        "ON CONFLICT (id) DO NOTHING"
    )

    # Drop old FK
    op.drop_constraint("user_profile_user_id_fkey", "user_profile", type_="foreignkey")

    # Create new FK to user_account
    op.create_foreign_key(
        "user_profile_user_id_fkey", "user_profile", "user_account",
        ["user_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("user_profile_user_id_fkey", "user_profile", type_="foreignkey")
    op.create_foreign_key(
        "user_profile_user_id_fkey", "user_profile", "app_user",
        ["user_id"], ["id"],
    )
