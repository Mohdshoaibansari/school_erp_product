"""Add app.activationBaseUrl config key.

Revision ID: 013_add_activation_base_url
Revises: 012_app_user_institution_id_not_null
Create Date: 2026-08-04

Seeds the app.activationBaseUrl config key used to construct invite/activation
URLs returned by user creation endpoints. Per D3 and AGENTS.md §8.

Also inserts an audit row (actor=system).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "013_add_activation_base_url"
down_revision = "012_app_user_inst_id_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Seed app.activationBaseUrl config key
    # ============================================================
    op.execute(sa.text("""
        INSERT INTO configuration_key (
            id, key, type, default_value, merge_strategy, category, module,
            description, is_feature_toggle
        ) VALUES (
            gen_random_uuid(), 'app.activationBaseUrl', 'string',
            CAST('"http://127.0.0.1:8000"' AS jsonb),
            'replace', 'Business Rules', 'app',
            'Base URL used to construct activation/invite links sent to new users.',
            FALSE
        )
        ON CONFLICT (key) DO NOTHING
    """))

    # ============================================================
    # Seed audit row
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
        WHERE k.key = 'app.activationBaseUrl'
        AND NOT EXISTS (
            SELECT 1 FROM configuration_audit a
            WHERE a.key_id = k.id AND a.action = 'key_created'
        )
    """)


def downgrade() -> None:
    # Delete audit row
    op.execute("""
        DELETE FROM configuration_audit
        WHERE key_id IN (
            SELECT id FROM configuration_key
            WHERE key = 'app.activationBaseUrl'
        )
    """)

    # Delete the key
    op.execute(sa.text("""
        DELETE FROM configuration_key
        WHERE key = 'app.activationBaseUrl'
    """))
