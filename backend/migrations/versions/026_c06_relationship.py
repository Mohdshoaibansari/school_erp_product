"""C-06 Relationship Management — Migration 026.

Creates:
- 5 relationship management tables with RLS policies
- Default RelationshipTypes with inverse pairs
- Default ContactRoles
- Compatibility matrix
- 11 new permissions

Revision ID: 026_c06_relationship
Revises: 025_c05_refactor
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "026_c06_relationship"
down_revision = "025_c05_refactor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Create tables
    # ============================================================

    # RelationshipType
    op.execute("""
        CREATE TABLE relationship_type (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            inverse_relationship_type_id UUID REFERENCES relationship_type(id),
            is_symmetric BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ContactRole
    op.execute("""
        CREATE TABLE contact_role (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # RelationshipTypeContactRole (compatibility matrix)
    op.execute("""
        CREATE TABLE relationship_type_contact_role (
            relationship_type_id UUID NOT NULL REFERENCES relationship_type(id),
            contact_role_id UUID NOT NULL REFERENCES contact_role(id),
            CONSTRAINT uq_rel_type_contact_role UNIQUE (relationship_type_id, contact_role_id),
            PRIMARY KEY (relationship_type_id, contact_role_id)
        )
    """)

    # Relationship
    op.execute("""
        CREATE TABLE relationship (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            person_a_id UUID NOT NULL REFERENCES person(id),
            person_b_id UUID NOT NULL REFERENCES person(id),
            relationship_type_id UUID NOT NULL REFERENCES relationship_type(id),
            valid_from DATE NOT NULL,
            valid_to DATE,
            normalized_pair VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_no_self_relationship CHECK (person_a_id != person_b_id),
            CONSTRAINT chk_relationship_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
        )
    """)

    # ContactRoleAssignment
    op.execute("""
        CREATE TABLE contact_role_assignment (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            relationship_id UUID NOT NULL REFERENCES relationship(id),
            contact_role_id UUID NOT NULL REFERENCES contact_role(id),
            valid_from DATE NOT NULL,
            valid_to DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_role_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
        )
    """)

    # ============================================================
    # Section 2 — RLS policies
    # ============================================================
    for tbl in [
        "relationship_type", "contact_role", "relationship",
        "contact_role_assignment",
    ]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {tbl}_sel ON {tbl} FOR SELECT USING (
                is_platform_owner() OR client_id = current_client_id()
            )
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_ins ON {tbl} FOR INSERT WITH CHECK (
                is_platform_owner() OR client_id = current_client_id()
            )
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_upd ON {tbl} FOR UPDATE USING (
                is_platform_owner() OR client_id = current_client_id()
            )
        """)
        op.execute(f"""
            CREATE POLICY {tbl}_del ON {tbl} FOR DELETE USING (
                is_platform_owner() OR client_id = current_client_id()
            )
        """)

    # relationship_type_contact_role has no client_id
    op.execute("ALTER TABLE relationship_type_contact_role ENABLE ROW LEVEL SECURITY")

    # ============================================================
    # Section 3 — Indexes
    # ============================================================
    op.execute("CREATE INDEX idx_relationship_person_a ON relationship(person_a_id)")
    op.execute("CREATE INDEX idx_relationship_person_b ON relationship(person_b_id)")
    op.execute("CREATE INDEX idx_relationship_type ON relationship(relationship_type_id)")
    op.execute("CREATE INDEX idx_relationship_valid_from ON relationship(valid_from)")
    op.execute("CREATE INDEX idx_relationship_valid_to ON relationship(valid_to)")
    op.execute("CREATE INDEX idx_contact_role_assignment_relationship ON contact_role_assignment(relationship_id)")
    op.execute("CREATE INDEX idx_contact_role_assignment_role ON contact_role_assignment(contact_role_id)")
    op.execute("CREATE INDEX idx_contact_role_assignment_valid_from ON contact_role_assignment(valid_from)")
    op.execute("CREATE INDEX idx_contact_role_assignment_valid_to ON contact_role_assignment(valid_to)")

    # ============================================================
    # Section 4 — Seed default RelationshipTypes
    # ============================================================
    # First get a client_id to use for seeding
    op.execute("""
        DO $$
        DECLARE
            v_client_id UUID;
            v_mother UUID;
            v_child UUID;
            v_father UUID;
            v_guardian UUID;
            v_sibling UUID;
            v_grandparent UUID;
            v_grandchild UUID;
            v_foster_parent UUID;
            v_foster_child UUID;
            v_step_parent UUID;
            v_step_child UUID;
        BEGIN
            SELECT id INTO v_client_id FROM client LIMIT 1;

            IF v_client_id IS NOT NULL THEN
                -- Create primary types first
                INSERT INTO relationship_type (id, client_id, code, name, is_symmetric)
                VALUES
                    (gen_random_uuid(), v_client_id, 'mother', 'Mother', FALSE),
                    (gen_random_uuid(), v_client_id, 'father', 'Father', FALSE),
                    (gen_random_uuid(), v_client_id, 'guardian', 'Guardian', FALSE),
                    (gen_random_uuid(), v_client_id, 'sibling', 'Sibling', TRUE),
                    (gen_random_uuid(), v_client_id, 'grandparent', 'Grandparent', FALSE),
                    (gen_random_uuid(), v_client_id, 'foster_parent', 'Foster Parent', FALSE),
                    (gen_random_uuid(), v_client_id, 'step_parent', 'Step Parent', FALSE)
                ON CONFLICT (code) DO NOTHING;

                -- Create inverse types
                INSERT INTO relationship_type (id, client_id, code, name, is_symmetric)
                VALUES
                    (gen_random_uuid(), v_client_id, 'child', 'Child', FALSE),
                    (gen_random_uuid(), v_client_id, 'grandchild', 'Grandchild', FALSE),
                    (gen_random_uuid(), v_client_id, 'foster_child', 'Foster Child', FALSE),
                    (gen_random_uuid(), v_client_id, 'step_child', 'Step Child', FALSE)
                ON CONFLICT (code) DO NOTHING;

                -- Get IDs
                SELECT id INTO v_mother FROM relationship_type WHERE code = 'mother';
                SELECT id INTO v_child FROM relationship_type WHERE code = 'child';
                SELECT id INTO v_father FROM relationship_type WHERE code = 'father';
                SELECT id INTO v_guardian FROM relationship_type WHERE code = 'guardian';
                SELECT id INTO v_sibling FROM relationship_type WHERE code = 'sibling';
                SELECT id INTO v_grandparent FROM relationship_type WHERE code = 'grandparent';
                SELECT id INTO v_grandchild FROM relationship_type WHERE code = 'grandchild';
                SELECT id INTO v_foster_parent FROM relationship_type WHERE code = 'foster_parent';
                SELECT id INTO v_foster_child FROM relationship_type WHERE code = 'foster_child';
                SELECT id INTO v_step_parent FROM relationship_type WHERE code = 'step_parent';
                SELECT id INTO v_step_child FROM relationship_type WHERE code = 'step_child';

                -- Link inverses
                UPDATE relationship_type SET inverse_relationship_type_id = v_child WHERE id = v_mother;
                UPDATE relationship_type SET inverse_relationship_type_id = v_mother WHERE id = v_child;
                UPDATE relationship_type SET inverse_relationship_type_id = v_child WHERE id = v_father;
                UPDATE relationship_type SET inverse_relationship_type_id = v_father WHERE id = v_child;
                UPDATE relationship_type SET inverse_relationship_type_id = v_child WHERE id = v_guardian;
                UPDATE relationship_type SET inverse_relationship_type_id = v_guardian WHERE id = v_child;
                UPDATE relationship_type SET inverse_relationship_type_id = v_grandchild WHERE id = v_grandparent;
                UPDATE relationship_type SET inverse_relationship_type_id = v_grandparent WHERE id = v_grandchild;
                UPDATE relationship_type SET inverse_relationship_type_id = v_foster_child WHERE id = v_foster_parent;
                UPDATE relationship_type SET inverse_relationship_type_id = v_foster_parent WHERE id = v_foster_child;
                UPDATE relationship_type SET inverse_relationship_type_id = v_step_child WHERE id = v_step_parent;
                UPDATE relationship_type SET inverse_relationship_type_id = v_step_parent WHERE id = v_step_child;

                -- Seed ContactRoles
                INSERT INTO contact_role (id, client_id, code, name)
                VALUES
                    (gen_random_uuid(), v_client_id, 'primary_guardian', 'Primary Guardian'),
                    (gen_random_uuid(), v_client_id, 'guardian', 'Guardian'),
                    (gen_random_uuid(), v_client_id, 'financial_responsible', 'Financial Responsible'),
                    (gen_random_uuid(), v_client_id, 'emergency_contact', 'Emergency Contact'),
                    (gen_random_uuid(), v_client_id, 'pickup_authorized', 'Pickup Authorized')
                ON CONFLICT (code) DO NOTHING;
            END IF;
        END $$;
    """)

    # ============================================================
    # Section 5 — Seed compatibility matrix
    # ============================================================
    op.execute("""
        DO $$
        DECLARE
            v_mother UUID;
            v_father UUID;
            v_guardian UUID;
            v_grandparent UUID;
            v_foster_parent UUID;
            v_step_parent UUID;
            v_sibling UUID;
            v_primary_guardian UUID;
            v_guardian_role UUID;
            v_financial UUID;
            v_emergency UUID;
            v_pickup UUID;
        BEGIN
            SELECT id INTO v_mother FROM relationship_type WHERE code = 'mother';
            SELECT id INTO v_father FROM relationship_type WHERE code = 'father';
            SELECT id INTO v_guardian FROM relationship_type WHERE code = 'guardian';
            SELECT id INTO v_grandparent FROM relationship_type WHERE code = 'grandparent';
            SELECT id INTO v_foster_parent FROM relationship_type WHERE code = 'foster_parent';
            SELECT id INTO v_step_parent FROM relationship_type WHERE code = 'step_parent';
            SELECT id INTO v_sibling FROM relationship_type WHERE code = 'sibling';

            SELECT id INTO v_primary_guardian FROM contact_role WHERE code = 'primary_guardian';
            SELECT id INTO v_guardian_role FROM contact_role WHERE code = 'guardian';
            SELECT id INTO v_financial FROM contact_role WHERE code = 'financial_responsible';
            SELECT id INTO v_emergency FROM contact_role WHERE code = 'emergency_contact';
            SELECT id INTO v_pickup FROM contact_role WHERE code = 'pickup_authorized';

            IF v_mother IS NOT NULL AND v_primary_guardian IS NOT NULL THEN
                -- Mother: all roles
                INSERT INTO relationship_type_contact_role (relationship_type_id, contact_role_id)
                VALUES
                    (v_mother, v_primary_guardian), (v_mother, v_guardian_role),
                    (v_mother, v_financial), (v_mother, v_emergency), (v_mother, v_pickup),
                    (v_father, v_primary_guardian), (v_father, v_guardian_role),
                    (v_father, v_financial), (v_father, v_emergency), (v_father, v_pickup),
                    (v_guardian, v_primary_guardian), (v_guardian, v_guardian_role),
                    (v_guardian, v_financial), (v_guardian, v_emergency), (v_guardian, v_pickup),
                    (v_grandparent, v_guardian_role), (v_grandparent, v_emergency), (v_grandparent, v_pickup),
                    (v_foster_parent, v_primary_guardian), (v_foster_parent, v_guardian_role),
                    (v_foster_parent, v_financial), (v_foster_parent, v_emergency), (v_foster_parent, v_pickup),
                    (v_step_parent, v_guardian_role), (v_step_parent, v_emergency), (v_step_parent, v_pickup),
                    (v_sibling, v_emergency)
                ON CONFLICT DO NOTHING;
            END IF;
        END $$;
    """)

    # ============================================================
    # Section 6 — Permissions
    # ============================================================
    permissions = [
        ("relationship.create", "Create relationship", "relationship", "create"),
        ("relationship.read", "Read relationships", "relationship", "read"),
        ("relationship.update", "Update relationship", "relationship", "update"),
        ("relationship.end", "End relationship", "relationship", "end"),
        ("relationship.change_type", "Change relationship type", "relationship", "change_type"),
        ("relationship_type.create", "Create relationship type", "relationship_type", "create"),
        ("relationship_type.read", "Read relationship types", "relationship_type", "read"),
        ("contact_role.read", "Read contact roles", "contact_role", "read"),
        ("contact_role_assignment.create", "Add contact role to relationship", "contact_role_assignment", "create"),
        ("contact_role_assignment.update", "Update contact role period", "contact_role_assignment", "update"),
        ("contact_role_assignment.end", "End contact role", "contact_role_assignment", "end"),
    ]

    for perm_name, description, resource, action in permissions:
        op.execute(f"""
            INSERT INTO permission (id, name, description, resource, action)
            VALUES (gen_random_uuid(), '{perm_name}', '{description}', '{resource}', '{action}')
            ON CONFLICT (name) DO NOTHING
        """)

    # Role-permission mappings
    admin_roles = ["Admin", "institution_admin"]
    read_roles = ["Principal", "HOD", "Teacher", "Staff", "Student", "Parent"]

    for role_name in admin_roles:
        for perm_name, _, _, _ in permissions:
            op.execute(f"""
                INSERT INTO role_permission (id, role_id, permission_id, scope)
                SELECT gen_random_uuid(), r.id, p.id, 'institution'
                FROM role r, permission p
                WHERE r.name = '{role_name}' AND p.name = '{perm_name}'
                ON CONFLICT DO NOTHING
            """)

    # Read-only roles get read permissions
    read_perms = ["relationship.read", "relationship_type.read", "contact_role.read"]
    for role_name in read_roles:
        for perm_name in read_perms:
            op.execute(f"""
                INSERT INTO role_permission (id, role_id, permission_id, scope)
                SELECT gen_random_uuid(), r.id, p.id, 'institution'
                FROM role r, permission p
                WHERE r.name = '{role_name}' AND p.name = '{perm_name}'
                ON CONFLICT DO NOTHING
            """)

    # client_director gets all at tenant scope
    for perm_name, _, _, _ in permissions:
        op.execute(f"""
            INSERT INTO role_permission (id, role_id, permission_id, scope)
            SELECT gen_random_uuid(), r.id, p.id, 'tenant'
            FROM role r, permission p
            WHERE r.name = 'client_director' AND p.name = '{perm_name}'
            ON CONFLICT DO NOTHING
        """)


def downgrade() -> None:
    # Remove permissions
    op.execute("DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE resource IN ('relationship', 'relationship_type', 'contact_role', 'contact_role_assignment'))")
    op.execute("DELETE FROM permission WHERE resource IN ('relationship', 'relationship_type', 'contact_role', 'contact_role_assignment')")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS contact_role_assignment CASCADE")
    op.execute("DROP TABLE IF EXISTS relationship CASCADE")
    op.execute("DROP TABLE IF EXISTS relationship_type_contact_role CASCADE")
    op.execute("DROP TABLE IF EXISTS contact_role CASCADE")
    op.execute("DROP TABLE IF EXISTS relationship_type CASCADE")
