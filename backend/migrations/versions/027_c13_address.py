"""C-13 Address Management — Migration 027.

Creates:
- 8 address management tables
- Default EntityTypes, AddressTypes, compatibility matrix
- India geographic data
- 8 new permissions

Revision ID: 027_c13_address
Revises: 026_c06_relationship
Create Date: 2026-09-07
"""

from __future__ import annotations

from alembic import op

revision = "027_c13_address"
down_revision = "026_c06_relationship"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Create tables
    # ============================================================

    # EntityType
    op.execute("""
        CREATE TABLE entity_type (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # AddressType
    op.execute("""
        CREATE TABLE address_type (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # AddressTypeEntityType (compatibility matrix)
    op.execute("""
        CREATE TABLE address_type_entity_type (
            address_type_id UUID NOT NULL REFERENCES address_type(id),
            entity_type_id UUID NOT NULL REFERENCES entity_type(id),
            CONSTRAINT uq_address_type_entity_type UNIQUE (address_type_id, entity_type_id),
            PRIMARY KEY (address_type_id, entity_type_id)
        )
    """)

    # Country
    op.execute("""
        CREATE TABLE country (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(10) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # State
    op.execute("""
        CREATE TABLE state (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            country_id UUID NOT NULL REFERENCES country(id),
            code VARCHAR(10) NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_state_country_code UNIQUE (country_id, code)
        )
    """)

    # City
    op.execute("""
        CREATE TABLE city (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            state_id UUID NOT NULL REFERENCES state(id),
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_city_state_code UNIQUE (state_id, code)
        )
    """)

    # Address
    op.execute("""
        CREATE TABLE address (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address_line_1 VARCHAR(500) NOT NULL,
            address_line_2 VARCHAR(500),
            locality VARCHAR(100),
            landmark VARCHAR(100),
            postal_code VARCHAR(20),
            city_id UUID NOT NULL REFERENCES city(id),
            state_id UUID NOT NULL REFERENCES state(id),
            country_id UUID NOT NULL REFERENCES country(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # AddressAssignment
    op.execute("""
        CREATE TABLE address_assignment (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type_id UUID NOT NULL REFERENCES entity_type(id),
            entity_id UUID NOT NULL,
            address_id UUID NOT NULL REFERENCES address(id),
            address_type_id UUID NOT NULL REFERENCES address_type(id),
            valid_from DATE NOT NULL,
            valid_to DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_assignment_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
        )
    """)

    # ============================================================
    # Section 2 — Indexes
    # ============================================================
    op.execute("CREATE INDEX idx_address_city ON address(city_id)")
    op.execute("CREATE INDEX idx_address_state ON address(state_id)")
    op.execute("CREATE INDEX idx_address_country ON address(country_id)")
    op.execute("CREATE INDEX idx_address_assignment_entity ON address_assignment(entity_type_id, entity_id)")
    op.execute("CREATE INDEX idx_address_assignment_address ON address_assignment(address_id)")
    op.execute("CREATE INDEX idx_address_assignment_type ON address_assignment(address_type_id)")
    op.execute("CREATE INDEX idx_address_assignment_valid_from ON address_assignment(valid_from)")
    op.execute("CREATE INDEX idx_address_assignment_valid_to ON address_assignment(valid_to)")
    op.execute("CREATE INDEX idx_state_country ON state(country_id)")
    op.execute("CREATE INDEX idx_city_state ON city(state_id)")

    # ============================================================
    # Section 3 — Seed EntityTypes
    # ============================================================
    op.execute("""
        INSERT INTO entity_type (id, code, name) VALUES
            (gen_random_uuid(), 'INSTITUTION', 'Institution'),
            (gen_random_uuid(), 'PERSON', 'Person')
        ON CONFLICT (code) DO NOTHING
    """)

    # ============================================================
    # Section 4 — Seed AddressTypes
    # ============================================================
    op.execute("""
        INSERT INTO address_type (id, code, name) VALUES
            (gen_random_uuid(), 'RESIDENTIAL', 'Residential'),
            (gen_random_uuid(), 'PERMANENT', 'Permanent'),
            (gen_random_uuid(), 'CORRESPONDENCE', 'Correspondence'),
            (gen_random_uuid(), 'OFFICE', 'Office'),
            (gen_random_uuid(), 'EMERGENCY', 'Emergency')
        ON CONFLICT (code) DO NOTHING
    """)

    # ============================================================
    # Section 5 — Seed compatibility matrix
    # ============================================================
    op.execute("""
        INSERT INTO address_type_entity_type (address_type_id, entity_type_id)
        SELECT at.id, et.id
        FROM address_type at, entity_type et
        WHERE at.code IN ('RESIDENTIAL', 'PERMANENT', 'CORRESPONDENCE', 'EMERGENCY')
          AND et.code = 'PERSON'
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO address_type_entity_type (address_type_id, entity_type_id)
        SELECT at.id, et.id
        FROM address_type at, entity_type et
        WHERE at.code IN ('OFFICE', 'CORRESPONDENCE', 'EMERGENCY')
          AND et.code = 'INSTITUTION'
        ON CONFLICT DO NOTHING
    """)

    # ============================================================
    # Section 6 — Seed geographic data (India)
    # ============================================================
    # Country
    op.execute("""
        INSERT INTO country (id, code, name) VALUES
            (gen_random_uuid(), 'IN', 'India')
        ON CONFLICT (code) DO NOTHING
    """)

    # States (sample - 28 states)
    op.execute("""
        INSERT INTO state (id, country_id, code, name)
        SELECT gen_random_uuid(), c.id, s.code, s.name
        FROM country c, (VALUES
            ('AP', 'Andhra Pradesh'),
            ('AR', 'Arunachal Pradesh'),
            ('AS', 'Assam'),
            ('BR', 'Bihar'),
            ('CG', 'Chhattisgarh'),
            ('GA', 'Goa'),
            ('GJ', 'Gujarat'),
            ('HR', 'Haryana'),
            ('HP', 'Himachal Pradesh'),
            ('JH', 'Jharkhand'),
            ('KA', 'Karnataka'),
            ('KL', 'Kerala'),
            ('MP', 'Madhya Pradesh'),
            ('MH', 'Maharashtra'),
            ('MN', 'Manipur'),
            ('ML', 'Meghalaya'),
            ('MZ', 'Mizoram'),
            ('NL', 'Nagaland'),
            ('OD', 'Odisha'),
            ('PB', 'Punjab'),
            ('RJ', 'Rajasthan'),
            ('SK', 'Sikkim'),
            ('TN', 'Tamil Nadu'),
            ('TS', 'Telangana'),
            ('TR', 'Tripura'),
            ('UP', 'Uttar Pradesh'),
            ('UK', 'Uttarakhand'),
            ('WB', 'West Bengal')
        ) AS s(code, name)
        WHERE c.code = 'IN'
        ON CONFLICT (country_id, code) DO NOTHING
    """)

    # Cities (sample - major cities per state)
    op.execute("""
        INSERT INTO city (id, state_id, code, name)
        SELECT gen_random_uuid(), st.id, ci.code, ci.name
        FROM state st, (VALUES
            ('AP', 'VISAKHAPATNAM', 'Visakhapatnam'),
            ('AP', 'VIJAYAWADA', 'Vijayawada'),
            ('AP', 'TIRUPATI', 'Tirupati'),
            ('AS', 'GUWAHATI', 'Guwahati'),
            ('BR', 'PATNA', 'Patna'),
            ('CG', 'RAIPUR', 'Raipur'),
            ('GA', 'PANAJI', 'Panaji'),
            ('GJ', 'AHMEDABAD', 'Ahmedabad'),
            ('GJ', 'SURAT', 'Surat'),
            ('GJ', 'VADODARA', 'Vadodara'),
            ('HR', 'GURUGRAM', 'Gurugram'),
            ('HR', 'FARIDABAD', 'Faridabad'),
            ('HP', 'SHIMLA', 'Shimla'),
            ('JH', 'RANCHI', 'Ranchi'),
            ('JH', 'JAMSHEDPUR', 'Jamshedpur'),
            ('KA', 'BANGALORE', 'Bangalore'),
            ('KA', 'MYSORE', 'Mysore'),
            ('KA', 'HUBLI', 'Hubli'),
            ('KL', 'KOCHI', 'Kochi'),
            ('KL', 'THIRUVANANTHAPURAM', 'Thiruvananthapuram'),
            ('MP', 'BHOPAL', 'Bhopal'),
            ('MP', 'INDORE', 'Indore'),
            ('MP', 'GWALIOR', 'Gwalior'),
            ('MH', 'MUMBAI', 'Mumbai'),
            ('MH', 'PUNE', 'Pune'),
            ('MH', 'NAGPUR', 'Nagpur'),
            ('MN', 'IMPHAL', 'Imphal'),
            ('ML', 'SHILLONG', 'Shillong'),
            ('MZ', 'AIZAWL', 'Aizawl'),
            ('NL', 'KOHIMA', 'Kohima'),
            ('OD', 'BHUBANESWAR', 'Bhubaneswar'),
            ('PB', 'CHANDIGARH', 'Chandigarh'),
            ('PB', 'LUDHIANA', 'Ludhiana'),
            ('RJ', 'JAIPUR', 'Jaipur'),
            ('RJ', 'JODHPUR', 'Jodhpur'),
            ('SK', 'GANGTOK', 'Gangtok'),
            ('TN', 'CHENNAI', 'Chennai'),
            ('TN', 'COIMBATORE', 'Coimbatore'),
            ('TS', 'HYDERABAD', 'Hyderabad'),
            ('TR', 'AGARTALA', 'Agartala'),
            ('UP', 'LUCKNOW', 'Lucknow'),
            ('UP', 'KANPUR', 'Kanpur'),
            ('UP', 'VARANASI', 'Varanasi'),
            ('UK', 'DEHRADUN', 'Dehradun'),
            ('WB', 'KOLKATA', 'Kolkata')
        ) AS ci(state_code, code, name)
        WHERE st.code = ci.state_code
        ON CONFLICT (state_id, code) DO NOTHING
    """)

    # ============================================================
    # Section 7 — Seed permissions
    # ============================================================
    permissions = [
        ("address.create", "Create address assignment", "address", "create"),
        ("address.read", "Read addresses", "address", "read"),
        ("address.update", "Update future address", "address", "update"),
        ("address.delete", "Delete address assignment + address", "address", "delete"),
        ("address.correct", "Correct effective address", "address", "correct"),
        ("address_type.read", "Read address types", "address_type", "read"),
        ("address_type.manage", "Manage address types", "address_type", "manage"),
        ("entity_type.read", "Read entity types", "entity_type", "read"),
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
    read_perms = ["address.read", "address_type.read", "entity_type.read"]
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
    op.execute("""
        DELETE FROM role_permission
        WHERE permission_id IN (SELECT id FROM permission WHERE resource IN ('address', 'address_type', 'entity_type'))
    """)
    op.execute("DELETE FROM permission WHERE resource IN ('address', 'address_type', 'entity_type')")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS address_assignment CASCADE")
    op.execute("DROP TABLE IF EXISTS address CASCADE")
    op.execute("DROP TABLE IF EXISTS city CASCADE")
    op.execute("DROP TABLE IF EXISTS state CASCADE")
    op.execute("DROP TABLE IF EXISTS country CASCADE")
    op.execute("DROP TABLE IF EXISTS address_type_entity_type CASCADE")
    op.execute("DROP TABLE IF EXISTS address_type CASCADE")
    op.execute("DROP TABLE IF EXISTS entity_type CASCADE")
