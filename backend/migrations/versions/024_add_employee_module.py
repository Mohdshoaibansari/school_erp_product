"""Employee business module — table, RLS, config keys, permissions.

Revision ID: 024_add_employee_module
Revises: 023_fix_c04_abac_po_permissions
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "024_add_employee_module"
down_revision = "023_fix_c04_abac_po_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. Employee table
    # ============================================================
    op.create_table(
        "employee",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("institution_id", UUID(as_uuid=True), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("employee_no", sa.String(20), nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("employment_type", sa.String(20), nullable=False),
        sa.Column("employment_status", sa.String(20), nullable=False, server_default="Hired"),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ============================================================
    # 2. CHECK constraints
    # ============================================================
    op.execute(
        "ALTER TABLE employee ADD CONSTRAINT chk_employee_employment_type "
        "CHECK (employment_type IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'TEMPORARY', 'INTERN', 'CONSULTANT'))"
    )
    op.execute(
        "ALTER TABLE employee ADD CONSTRAINT chk_employee_employment_status "
        "CHECK (employment_status IN ('Hired', 'Active', 'On-Leave', 'Suspended', 'Retired', 'Resigned', 'Terminated'))"
    )

    # ============================================================
    # 3. UNIQUE constraints
    # ============================================================
    op.execute(
        "ALTER TABLE employee ADD CONSTRAINT uq_employee_person_institution "
        "UNIQUE (person_id, institution_id)"
    )
    op.execute(
        "ALTER TABLE employee ADD CONSTRAINT uq_employee_no_institution "
        "UNIQUE (institution_id, employee_no)"
    )

    # ============================================================
    # 4. Indexes
    # ============================================================
    op.execute("CREATE INDEX ix_employee_institution_id ON employee(institution_id)")
    op.execute("CREATE INDEX ix_employee_person_id ON employee(person_id)")
    op.execute("CREATE INDEX ix_employee_employment_status ON employee(employment_status)")
    op.execute("CREATE INDEX ix_employee_employment_type ON employee(employment_type)")
    op.execute("CREATE INDEX ix_employee_department ON employee(department)")

    # ============================================================
    # 5. RLS (matching person/fee pattern)
    # ============================================================
    op.execute("ALTER TABLE employee ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE employee FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY employee_tenant_select ON employee FOR SELECT
        USING (is_platform_owner() OR client_id = current_client_id())
    """)
    op.execute("""
        CREATE POLICY employee_tenant_insert ON employee FOR INSERT
        WITH CHECK (is_platform_owner() OR client_id = current_client_id())
    """)
    op.execute("""
        CREATE POLICY employee_tenant_update ON employee FOR UPDATE
        USING (is_platform_owner() OR client_id = current_client_id())
        WITH CHECK (is_platform_owner() OR client_id = current_client_id())
    """)
    op.execute("""
        CREATE POLICY employee_tenant_delete ON employee FOR DELETE
        USING (is_platform_owner())
    """)

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON employee TO test_tenant_user")

    # ============================================================
    # 6. Config keys (C-08)
    # ============================================================
    _config_keys = [
        (
            "employee.departments", "json",
            '["Administration", "Mathematics", "Science", "English", "Social Studies", "Accounts", "Library", "Physical Education"]',
            "replace", "Business Rules", "employee",
            "List of allowed department names per institution", False,
        ),
        (
            "employee.designations", "json",
            '["Teacher", "Accountant", "Librarian", "Receptionist", "Peon", "Lab Assistant", "Office Superintendent"]',
            "replace", "Business Rules", "employee",
            "List of allowed designation names per institution", False,
        ),
    ]

    for key_name, key_type, default_value, merge_strategy, category, module, description, is_feature_toggle in _config_keys:
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
    # 7. Permissions (C-04)
    # ============================================================
    _employee_permissions = [
        ("employee.create",     "Create an employee",           "employee", "create"),
        ("employee.read",       "View employees",               "employee", "read"),
        ("employee.update",     "Update an employee",           "employee", "update"),
        ("employee.activate",   "Activate an employee",         "employee", "activate"),
        ("employee.suspend",    "Suspend an employee",          "employee", "suspend"),
        ("employee.deactivate", "Deactivate an employee",       "employee", "deactivate"),
        ("employee.terminate",  "Terminate an employee",        "employee", "terminate"),
    ]

    for name, desc, resource, action in _employee_permissions:
        safe_desc = desc.replace("'", "''")
        op.execute(sa.text(
            f"INSERT INTO permission (id, name, description, resource, action) "
            f"VALUES (gen_random_uuid(), '{name}', '{safe_desc}', '{resource}', '{action}') "
            f"ON CONFLICT (name) DO NOTHING"
        ))

    # ============================================================
    # 8. Role-permission mappings (institution scope)
    # ============================================================
    _insert_rp = (
        "INSERT INTO role_permission (id, role_id, permission_id, scope) "
        "SELECT gen_random_uuid(), r.id, p.id, 'institution' "
        "FROM role r, permission p "
        "WHERE r.name = :role_name AND p.name = :perm_name "
        "ON CONFLICT (role_id, permission_id) DO NOTHING"
    )

    _full_perms = [p[0] for p in _employee_permissions]
    _read_perms = ["employee.read"]

    # Admin / InstituteAdmin / Staff: full set
    for role in ["Admin", "Staff"]:
        for perm in _full_perms:
            op.execute(sa.text(_insert_rp).bindparams(role_name=role, perm_name=perm))

    # HOD / Principal / Teacher: read only
    for role in ["HOD", "Principal", "Teacher"]:
        for perm in _read_perms:
            op.execute(sa.text(_insert_rp).bindparams(role_name=role, perm_name=perm))


def downgrade() -> None:
    # Drop policies
    for suffix in ["select", "insert", "update", "delete"]:
        op.execute(f"DROP POLICY IF EXISTS employee_tenant_{suffix} ON employee")

    # Drop indexes
    for ix in ["ix_employee_institution_id", "ix_employee_person_id",
               "ix_employee_employment_status", "ix_employee_employment_type",
               "ix_employee_department"]:
        op.execute(f"DROP INDEX IF EXISTS {ix}")

    # Drop table
    op.drop_table("employee")

    # Remove permissions (cascades to role_permission)
    op.execute(
        "DELETE FROM permission WHERE name IN ("
        "'employee.create','employee.read','employee.update',"
        "'employee.activate','employee.suspend','employee.deactivate','employee.terminate'"
        ")"
    )

    # Remove config keys
    op.execute(
        "DELETE FROM configuration_key WHERE key IN ("
        "'employee.departments','employee.designations'"
        ")"
    )
