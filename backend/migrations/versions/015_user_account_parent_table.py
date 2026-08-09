"""D12: user_account parent table for cross-tier referential integrity.

Supersedes 014 (drop login_attempt FK). This migration:
1. Creates user_account table (shared identity parent)
2. Backfills from existing app_user + client_user
3. Adds FK on app_user.id → user_account.id
4. Adds FK on client_user.id → user_account.id
5. Changes role_assignment.user_id FK: app_user → user_account
6. Changes login_attempt.user_id FK: app_user → user_account

This enables both CD (client_user) and institution (app_user) users
to have role_assignment and login_attempt rows with full referential integrity.

Revision ID: 015
Down revision: 013_add_activation_base_url (skips 014 — consolidated into this migration)
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "013_add_activation_base_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Create user_account table ──
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), primary_key=True),
    )

    # ── Step 2: Backfill from existing app_user + client_user rows ──
    op.execute(
        "INSERT INTO user_account (id) SELECT id FROM app_user "
        "ON CONFLICT (id) DO NOTHING"
    )
    op.execute(
        "INSERT INTO user_account (id) SELECT id FROM client_user "
        "ON CONFLICT (id) DO NOTHING"
    )

    # ── Step 3: Add FK on app_user.id → user_account.id ──
    op.create_foreign_key(
        "app_user_id_fkey", "app_user", "user_account", ["id"], ["id"]
    )

    # ── Step 4: Add FK on client_user.id → user_account.id ──
    op.create_foreign_key(
        "client_user_id_fkey", "client_user", "user_account", ["id"], ["id"]
    )

    # ── Step 5: role_assignment.user_id FK: app_user → user_account ──
    op.drop_constraint(
        "role_assignment_user_id_fkey", "role_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "role_assignment_user_id_fkey",
        "role_assignment",
        "user_account",
        ["user_id"],
        ["id"],
    )

    # ── Step 6: login_attempt.user_id FK: app_user → user_account ──
    # Note: 014 already dropped this FK. If running fresh (013→015),
    # the constraint exists and needs dropping. If 014 was already applied,
    # this is a no-op. Use IF EXISTS pattern for safety.
    op.execute(
        "ALTER TABLE login_attempt DROP CONSTRAINT IF EXISTS login_attempt_user_id_fkey"
    )
    op.create_foreign_key(
        "login_attempt_user_id_fkey",
        "login_attempt",
        "user_account",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    # Reverse step 6
    op.drop_constraint(
        "login_attempt_user_id_fkey", "login_attempt", type_="foreignkey"
    )
    op.create_foreign_key(
        "login_attempt_user_id_fkey",
        "login_attempt",
        "app_user",
        ["user_id"],
        ["id"],
    )

    # Reverse step 5
    op.drop_constraint(
        "role_assignment_user_id_fkey", "role_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "role_assignment_user_id_fkey",
        "role_assignment",
        "app_user",
        ["user_id"],
        ["id"],
    )

    # Reverse steps 3-4
    op.drop_constraint("client_user_id_fkey", "client_user", type_="foreignkey")
    op.drop_constraint("app_user_id_fkey", "app_user", type_="foreignkey")

    # Reverse step 1
    op.drop_table("user_account")
