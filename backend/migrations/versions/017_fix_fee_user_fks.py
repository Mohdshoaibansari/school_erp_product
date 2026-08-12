"""Fix fee FKs to reference user_account instead of app_user.

fee_assignment.user_id, fee_assignment.assigned_by, and payment.recorded_by
all reference app_user.id. CD users are in client_user, not app_user.
Change all three to reference user_account.id.

Revision ID: 017
Down revision: 016
"""

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fee_assignment.user_id: app_user → user_account
    op.drop_constraint("fee_assignment_user_id_fkey", "fee_assignment", type_="foreignkey")
    op.create_foreign_key(
        "fee_assignment_user_id_fkey", "fee_assignment", "user_account",
        ["user_id"], ["id"],
    )

    # fee_assignment.assigned_by: app_user → user_account
    op.drop_constraint("fee_assignment_assigned_by_fkey", "fee_assignment", type_="foreignkey")
    op.create_foreign_key(
        "fee_assignment_assigned_by_fkey", "fee_assignment", "user_account",
        ["assigned_by"], ["id"],
    )

    # payment.recorded_by: app_user → user_account
    op.drop_constraint("payment_recorded_by_fkey", "payment", type_="foreignkey")
    op.create_foreign_key(
        "payment_recorded_by_fkey", "payment", "user_account",
        ["recorded_by"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("payment_recorded_by_fkey", "payment", type_="foreignkey")
    op.create_foreign_key("payment_recorded_by_fkey", "payment", "app_user", ["recorded_by"], ["id"])

    op.drop_constraint("fee_assignment_assigned_by_fkey", "fee_assignment", type_="foreignkey")
    op.create_foreign_key("fee_assignment_assigned_by_fkey", "fee_assignment", "app_user", ["assigned_by"], ["id"])

    op.drop_constraint("fee_assignment_user_id_fkey", "fee_assignment", type_="foreignkey")
    op.create_foreign_key("fee_assignment_user_id_fkey", "fee_assignment", "app_user", ["user_id"], ["id"])
