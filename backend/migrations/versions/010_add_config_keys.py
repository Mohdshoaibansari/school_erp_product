"""Add 6 new config keys + module integration seed data.

Revision ID: 010_add_config_keys
Revises: 009_c08_configuration
Create Date: 2026-07-30

Adds:
- auth.jwtExpirySeconds (number, 3600)
- auth.inviteExpiryDays (number, 7)
- auth.passwordResetRedirectUrl (string, http://localhost:3000/reset-password)
- homework.lateSubmissionPolicy (string, submitted)
- platform.configDeprecatedHideDays (number, 90)
- homework.closedStatusValues (json, ["active"])

Also inserts 6 audit rows (one per key, actor=system).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "010_add_config_keys"
down_revision = "009_c08_configuration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Seed 6 new config keys
    # ============================================================
    _new_keys = [
        # (key, type, default_value_json, merge_strategy, category, module, description, is_feature_toggle)
        ("auth.jwtExpirySeconds", "number", "3600", "replace", "Business Rules", "auth",
         "JWT token expiry in seconds (default 1 hour)", False),
        ("auth.inviteExpiryDays", "number", "7", "replace", "Business Rules", "auth",
         "Invite token expiry in days", False),
        ("auth.passwordResetRedirectUrl", "string",
         '"http://localhost:3000/reset-password"', "replace", "Business Rules", "auth",
         "Redirect URL for password reset emails", False),
        ("homework.lateSubmissionPolicy", "string", '"submitted"', "replace",
         "Business Rules", "homework",
         "Policy for late homework submissions: submitted (always on-time), late (mark as late), rejected (block after deadline)", False),
        ("platform.configDeprecatedHideDays", "number", "90", "replace",
         "Platform", "config",
         "Number of days after which deprecated config keys are hidden from default list", False),
        ("homework.closedStatusValues", "json", '["active"]', "replace",
         "Business Rules", "homework",
         "List of homework statuses that accept student submissions", False),
    ]

    for key_name, key_type, default_value, merge_strategy, category, module, description, is_feature_toggle in _new_keys:
        op.execute(sa.text("""
            INSERT INTO configuration_key (
                id, key, type, default_value, merge_strategy, category, module,
                description, is_feature_toggle
            ) VALUES (
                gen_random_uuid(), :key_name, :key_type, CAST(:default_value AS jsonb),
                :merge_strategy, :category, :module, :description, :is_feature_toggle
            )
            ON CONFLICT (key) DO NOTHING
        """).bindparams(
            key_name=key_name,
            key_type=key_type,
            default_value=default_value,
            merge_strategy=merge_strategy,
            category=category,
            module=module,
            description=description,
            is_feature_toggle=is_feature_toggle,
        ))

    # ============================================================
    # Section 2 — Seed audit rows for new keys
    # ============================================================
    op.execute("""
        INSERT INTO configuration_audit (
            id, key_id, scope_type, scope_id, action, actor_user_id, actor_role
        )
        SELECT
            gen_random_uuid(),
            k.id,
            NULL,
            NULL,
            'key_created',
            NULL,
            'system'
        FROM configuration_key k
        WHERE k.key IN (
            'auth.jwtExpirySeconds',
            'auth.inviteExpiryDays',
            'auth.passwordResetRedirectUrl',
            'homework.lateSubmissionPolicy',
            'platform.configDeprecatedHideDays',
            'homework.closedStatusValues'
        )
        AND NOT EXISTS (
            SELECT 1 FROM configuration_audit a
            WHERE a.key_id = k.id AND a.action = 'key_created'
        )
    """)


def downgrade() -> None:
    # Delete audit rows for these keys
    op.execute("""
        DELETE FROM configuration_audit
        WHERE key_id IN (
            SELECT id FROM configuration_key
            WHERE key IN (
                'auth.jwtExpirySeconds',
                'auth.inviteExpiryDays',
                'auth.passwordResetRedirectUrl',
                'homework.lateSubmissionPolicy',
                'platform.configDeprecatedHideDays',
                'homework.closedStatusValues'
            )
        )
    """)

    # Delete the keys themselves
    op.execute(sa.text("""
        DELETE FROM configuration_key
        WHERE key IN (
            'auth.jwtExpirySeconds',
            'auth.inviteExpiryDays',
            'auth.passwordResetRedirectUrl',
            'homework.lateSubmissionPolicy',
            'platform.configDeprecatedHideDays',
            'homework.closedStatusValues'
        )
    """))
