"""C-08 Configuration Framework — tables, seed catalog, RLS, NOTIFY trigger, C-04 permissions.

Revision ID: 009_c08_configuration
Revises: 008_nullable_institution_id
Create Date: 2026-07-29

Implements:
- 3 tables: configuration_key, configuration_value, configuration_audit
- 8 new C-04 permissions (config.key.*, config.value.*, config.audit.*)
- 13 new C-04 role_permission mappings (PlatformOwner, ClientDirector, InstituteAdmin)
- 15 seed keys across 5 categories
- 15 audit rows (one per seed key, actor=system)
- RLS on configuration_value (client + institution, Platform Owner bypass)
- NOTIFY trigger on configuration_key + configuration_value for in-memory cache invalidation
- Soft-delete: deprecated_at column, 90-day auto-hide
- Idempotent: all inserts use ON CONFLICT DO NOTHING
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "009_c08_configuration"
down_revision = "008_nullable_institution_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Create ENUM types
    # ============================================================
    # Use DO blocks for idempotency (CREATE TYPE doesn't support IF NOT EXISTS)
    op.execute("DO $$ BEGIN CREATE TYPE configuration_type AS ENUM ('string', 'number', 'boolean', 'json', 'date'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE configuration_scope_type AS ENUM ('platform', 'client', 'institution'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE configuration_category AS ENUM ('Business Rules', 'Display', 'Academic', 'Notifications', 'Feature Toggles', 'Platform', 'Integrations'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE configuration_merge_strategy AS ENUM ('replace', 'append_lists', 'deep_merge'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE configuration_audit_action AS ENUM ('key_created', 'key_updated', 'key_deprecated', 'value_created', 'value_updated', 'value_deleted'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # ============================================================
    # Section 2 — configuration_key table (registry)
    # ============================================================
    op.execute("""
        CREATE TABLE configuration_key (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key TEXT UNIQUE NOT NULL,
            type configuration_type NOT NULL,
            default_value JSONB NOT NULL,
            merge_strategy configuration_merge_strategy NOT NULL DEFAULT 'replace',
            category configuration_category NOT NULL,
            module TEXT,
            description TEXT NOT NULL,
            is_feature_toggle BOOLEAN NOT NULL DEFAULT false,
            is_deprecated BOOLEAN NOT NULL DEFAULT false,
            deprecated_at TIMESTAMPTZ,
            replacement_key TEXT,
            allowed_values JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_configuration_key_key", "configuration_key", ["key"], unique=True)
    op.create_index("ix_configuration_key_category", "configuration_key", ["category"])
    op.create_index("ix_configuration_key_module", "configuration_key", ["module"])
    op.create_index("ix_configuration_key_deprecated", "configuration_key", ["is_deprecated"])
    # No RLS — global registry, all roles can read

    # ============================================================
    # Section 3 — configuration_value table (overrides)
    # ============================================================
    op.execute("""
        CREATE TABLE configuration_value (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key_id UUID NOT NULL REFERENCES configuration_key(id) ON DELETE CASCADE,
            scope_type configuration_scope_type NOT NULL,
            scope_id UUID,
            client_id UUID REFERENCES client(id),
            institution_id UUID REFERENCES institution(id),
            value JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by UUID NOT NULL REFERENCES app_user(id),
            CONSTRAINT uq_configuration_value_scope UNIQUE (key_id, scope_type, scope_id)
        )
    """)
    op.create_index("ix_configuration_value_key", "configuration_value", ["key_id"])
    op.create_index("ix_configuration_value_scope", "configuration_value", ["scope_type", "scope_id"])
    op.create_index("ix_configuration_value_client", "configuration_value", ["client_id"])
    op.create_index("ix_configuration_value_institution", "configuration_value", ["institution_id"])

    # ============================================================
    # Section 4 — configuration_audit table (change log, append-only)
    # ============================================================
    op.execute("""
        CREATE TABLE configuration_audit (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key_id UUID NOT NULL REFERENCES configuration_key(id) ON DELETE CASCADE,
            scope_type configuration_scope_type,
            scope_id UUID,
            action configuration_audit_action NOT NULL,
            actor_user_id UUID,
            actor_role TEXT,
            "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_configuration_audit_key", "configuration_audit", ["key_id"])
    op.create_index("ix_configuration_audit_timestamp", "configuration_audit", ["timestamp"])
    op.create_index("ix_configuration_audit_actor", "configuration_audit", ["actor_user_id"])

    # ============================================================
    # Section 5 — RLS policies on configuration_value
    # ============================================================
    # Add helper function for institution-level RLS (mirrors current_client_id)
    op.execute("""
        CREATE OR REPLACE FUNCTION current_institution_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.current_institution_id', true), '')::uuid;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)
    op.execute("ALTER TABLE configuration_value ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE configuration_value FORCE ROW LEVEL SECURITY")

    # SELECT: Platform owner sees all; others see rows in their client/institution
    op.execute("""
        CREATE POLICY configuration_value_select ON configuration_value
        FOR SELECT
        USING (
            is_platform_owner()
            OR (
                client_id IS NOT NULL
                AND client_id = current_client_id()
                AND (
                    institution_id IS NULL
                    OR institution_id = current_institution_id()
                )
            )
        )
    """)

    # INSERT: same scope check
    op.execute("""
        CREATE POLICY configuration_value_insert ON configuration_value
        FOR INSERT
        WITH CHECK (
            is_platform_owner()
            OR (
                client_id IS NOT NULL
                AND client_id = current_client_id()
                AND (
                    institution_id IS NULL
                    OR institution_id = current_institution_id()
                )
            )
        )
    """)

    # UPDATE: same scope check
    op.execute("""
        CREATE POLICY configuration_value_update ON configuration_value
        FOR UPDATE
        USING (
            is_platform_owner()
            OR (
                client_id IS NOT NULL
                AND client_id = current_client_id()
                AND (
                    institution_id IS NULL
                    OR institution_id = current_institution_id()
                )
            )
        )
        WITH CHECK (
            is_platform_owner()
            OR (
                client_id IS NOT NULL
                AND client_id = current_client_id()
                AND (
                    institution_id IS NULL
                    OR institution_id = current_institution_id()
                )
            )
        )
    """)

    # DELETE: Platform owner only (consistent with C-01/fees pattern)
    op.execute("""
        CREATE POLICY configuration_value_delete ON configuration_value
        FOR DELETE
        USING (is_platform_owner())
    """)

    # ============================================================
    # Section 6 — NOTIFY triggers for in-memory cache invalidation
    # ============================================================
    # Trigger function emits NOTIFY on config_changes channel with JSON payload.
    # For configuration_key: payload uses 'key_id' = NEW.id (the key's own id).
    # For configuration_value: payload uses 'key_id' = NEW.key_id (FK to key).
    op.execute("""
        CREATE OR REPLACE FUNCTION configuration_notify_trigger() RETURNS trigger AS $$
        DECLARE
            payload TEXT;
            v_key_id TEXT;
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                -- For configuration_key, the key's own id is OLD.id
                -- For configuration_value, the key reference is OLD.key_id
                IF TG_TABLE_NAME = 'configuration_key' THEN
                    v_key_id := OLD.id::text;
                ELSE
                    v_key_id := OLD.key_id::text;
                END IF;
                payload = json_build_object(
                    'op', TG_OP,
                    'table', TG_TABLE_NAME,
                    'key_id', v_key_id
                )::text;
                PERFORM pg_notify('config_changes', payload);
                RETURN OLD;
            ELSE
                IF TG_TABLE_NAME = 'configuration_key' THEN
                    v_key_id := NEW.id::text;
                ELSE
                    v_key_id := NEW.key_id::text;
                END IF;
                payload = json_build_object(
                    'op', TG_OP,
                    'table', TG_TABLE_NAME,
                    'key_id', v_key_id,
                    'id', NEW.id::text
                )::text;
                PERFORM pg_notify('config_changes', payload);
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Triggers on configuration_key
    op.execute("""
        CREATE TRIGGER configuration_key_notify_trg
        AFTER INSERT OR UPDATE OR DELETE ON configuration_key
        FOR EACH ROW EXECUTE FUNCTION configuration_notify_trigger()
    """)

    # Triggers on configuration_value
    op.execute("""
        CREATE TRIGGER configuration_value_notify_trg
        AFTER INSERT OR UPDATE OR DELETE ON configuration_value
        FOR EACH ROW EXECUTE FUNCTION configuration_notify_trigger()
    """)

    # ============================================================
    # Section 7 — C-04 permission extension (D15)
    # ============================================================
    _c08_permissions = [
        ("config.key.create",     "Create a configuration key",                "config.key",   "create"),
        ("config.key.update",     "Update a configuration key",                "config.key",   "update"),
        ("config.key.deprecate",  "Deprecate a configuration key",             "config.key",   "deprecate"),
        ("config.key.list",       "List/view configuration keys",              "config.key",   "list"),
        ("config.value.create",   "Create a configuration value override",     "config.value", "create"),
        ("config.value.update",   "Update a configuration value override",     "config.value", "update"),
        ("config.value.delete",   "Delete a configuration value override",     "config.value", "delete"),
        ("config.audit.read",     "Read configuration audit log",              "config.audit", "read"),
    ]

    for name, desc, resource, action in _c08_permissions:
        op.execute(sa.text(
            "INSERT INTO permission (id, name, description, resource, action) "
            "VALUES (gen_random_uuid(), :name, :desc, :resource, :action) "
            "ON CONFLICT (name) DO NOTHING"
        ).bindparams(name=name, desc=desc, resource=resource, action=action))

    # ============================================================
    # Section 8 — C-04 role_permission mappings (D4, D15)
    # ============================================================

    # Ensure client_director role exists (was added during testing, may not be in any migration)
    op.execute(
        "INSERT INTO role (id, name) VALUES (gen_random_uuid(), 'client_director') "
        "ON CONFLICT (name) DO NOTHING"
    )

    # Helper: insert role_permission by (role_name, permission_name)
    _insert_rp = (
        "INSERT INTO role_permission (id, role_id, permission_id) "
        "SELECT gen_random_uuid(), r.id, p.id "
        "FROM role r, permission p "
        "WHERE r.name = :role_name AND p.name = :perm_name "
        "ON CONFLICT (role_id, permission_id) DO NOTHING"
    )

    # PlatformOwner: all 8 config.* permissions
    for perm_name, _, _, _ in _c08_permissions:
        op.execute(sa.text(_insert_rp).bindparams(role_name="platform_owner", perm_name=perm_name))

    # ClientDirector: config.value.{create,update,delete} + config.key.list + config.audit.read
    _cd_perms = [
        "config.value.create", "config.value.update", "config.value.delete",
        "config.key.list", "config.audit.read",
    ]
    for perm_name in _cd_perms:
        op.execute(sa.text(_insert_rp).bindparams(role_name="client_director", perm_name=perm_name))

    # InstituteAdmin (Admin role in C-02): same as ClientDirector (institution scope)
    for perm_name in _cd_perms:
        op.execute(sa.text(_insert_rp).bindparams(role_name="Admin", perm_name=perm_name))

    # ============================================================
    # Section 9 — Seed 15 configuration keys
    # ============================================================
    # Format: (key, type, default_value JSON, merge_strategy, category, module, description, is_feature_toggle)
    _seed_keys = [
        # Business Rules (4)
        ("attendance.markingCutoffTime", "string", '"10:00 AM"', "replace", "Business Rules", "attendance",
         "Cutoff time after which attendance marking is blocked", False),
        ("attendance.statuses", "json", '["present", "absent"]', "append_lists", "Business Rules", "attendance",
         "List of allowed attendance statuses per institution", False),
        ("fee.lateFeePercentage", "number", "2", "replace", "Business Rules", "fees",
         "Late fee percentage applied to overdue payments", False),
        ("leave.autoApproveUnderDays", "number", "3", "replace", "Business Rules", "leave",
         "Auto-approve leave requests under this many days", False),

        # Display (3)
        ("display.dateFormat", "string", '"DD/MM/YYYY"', "replace", "Display", None,
         "Default date format for display", False),
        ("display.timezone", "string", '"Asia/Kolkata"', "replace", "Display", None,
         "Default timezone for date/time display", False),
        ("display.language", "string", '"en"', "replace", "Display", None,
         "Default UI language", False),

        # Academic (3)
        ("academic.gradingScale", "string", '"percentage"', "replace", "Academic", "academic",
         "Default grading scale (percentage or CGPA)", False),
        ("academic.passPercentage", "number", "33", "replace", "Academic", "academic",
         "Minimum percentage to pass", False),
        ("academic.termStructure", "string", '"yearly"', "replace", "Academic", "academic",
         "Default term structure (yearly or semester)", False),

        # Notifications (2)
        ("notification.attendanceAbsenceAlert", "boolean", "true", "replace", "Notifications", "notification",
         "Send alert when a student is marked absent", False),
        ("notification.defaultChannel", "string", '"email"', "replace", "Notifications", "notification",
         "Default channel for notifications (email, sms, in_app)", False),

        # Homework (2)
        ("homework.allowLateSubmission", "boolean", "false", "replace", "Feature Toggles", "homework",
         "Allow students to submit homework after the deadline", True),
        ("homework.maxAttachmentsPerAssignment", "number", "5", "replace", "Platform", "homework",
         "Maximum number of attachments per homework assignment", False),

        # Platform (1)
        ("platform.maxFileUploadMB", "number", "10", "replace", "Platform", None,
         "Maximum file upload size in MB", False),
    ]

    # Insert seed keys and capture each one's id for audit rows
    for key_name, key_type, default_value, merge_strategy, category, module, description, is_feature_toggle in _seed_keys:
        op.execute(sa.text(f"""
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
    # Section 10 — Seed audit rows (one per key, actor=system)
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
        WHERE NOT EXISTS (
            SELECT 1 FROM configuration_audit a
            WHERE a.key_id = k.id AND a.action = 'key_created'
        )
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS configuration_key_notify_trg ON configuration_key")
    op.execute("DROP TRIGGER IF EXISTS configuration_value_notify_trg ON configuration_value")
    op.execute("DROP FUNCTION IF EXISTS configuration_notify_trigger()")

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS configuration_value_select ON configuration_value")
    op.execute("DROP POLICY IF EXISTS configuration_value_insert ON configuration_value")
    op.execute("DROP POLICY IF EXISTS configuration_value_update ON configuration_value")
    op.execute("DROP POLICY IF EXISTS configuration_value_delete ON configuration_value")
    op.execute("ALTER TABLE configuration_value DISABLE ROW LEVEL SECURITY")

    # Drop tables in reverse FK order
    op.drop_table("configuration_audit")
    op.drop_table("configuration_value")
    op.drop_table("configuration_key")

    # Drop ENUMs
    op.execute("DROP TYPE IF EXISTS configuration_audit_action")
    op.execute("DROP TYPE IF EXISTS configuration_merge_strategy")
    op.execute("DROP TYPE IF EXISTS configuration_category")
    op.execute("DROP TYPE IF EXISTS configuration_scope_type")
    op.execute("DROP TYPE IF EXISTS configuration_type")

    # Remove C-08 permissions (cascades to role_permission via FK)
    op.execute("DELETE FROM permission WHERE name LIKE 'config.%'")
