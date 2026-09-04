"""C-05 Academic Structure Refactor — Migration 025.

Refactors academic structure to use permanent masters and ClassAcademicYear.

Changes:
- Drop: subject_group, subject_group_member, teacher_assignment, student_enrollment
- Alter: academic_year (add closed_at, cancelled status)
- Alter: grade_level (remove academic_year_id, add org_unit_id)
- Alter: class (remove academic_year_id)
- Alter: section (remove academic_year_id, add class_academic_year_id)
- Alter: subject (remove academic_year_id, add curriculum_version_id)
- Create: class_academic_year, curriculum, curriculum_version, section_subject, grade_academic_year_curriculum
- Update permissions

Revision ID: 025_refactor_c05_academic_structure
Revises: 024
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "025_c05_refactor"
down_revision = "024_add_employee_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Drop old tables
    # ============================================================
    op.execute("DROP TABLE IF EXISTS student_enrollment CASCADE")
    op.execute("DROP TABLE IF EXISTS teacher_assignment CASCADE")
    op.execute("DROP TABLE IF EXISTS subject_group_member CASCADE")
    op.execute("DROP TABLE IF EXISTS subject_group CASCADE")

    # ============================================================
    # Section 2 — Alter academic_year (add closed_at, cancelled status)
    # ============================================================
    op.execute("ALTER TABLE academic_year ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ")

    # ============================================================
    # Section 3 — Alter grade_level (remove academic_year_id, add org_unit_id)
    # ============================================================
    op.execute("ALTER TABLE grade_level DROP COLUMN IF EXISTS academic_year_id")
    op.execute("ALTER TABLE grade_level ADD COLUMN IF NOT EXISTS org_unit_id UUID REFERENCES org_unit(id)")

    # ============================================================
    # Section 4 — Alter class (remove academic_year_id)
    # ============================================================
    op.execute("ALTER TABLE class DROP COLUMN IF EXISTS academic_year_id")

    # ============================================================
    # Section 5 — Create class_academic_year table
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS class_academic_year (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            class_id UUID NOT NULL REFERENCES class(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            offered BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_class_academic_year UNIQUE (class_id, academic_year_id)
        )
    """)

    # ============================================================
    # Section 6 — Alter section (remove academic_year_id, add class_academic_year_id)
    # ============================================================
    op.execute("ALTER TABLE section DROP COLUMN IF EXISTS academic_year_id")
    op.execute("ALTER TABLE section DROP COLUMN IF EXISTS class_id")
    op.execute("ALTER TABLE section DROP COLUMN IF EXISTS homeroom_teacher_id")
    op.execute("ALTER TABLE section ADD COLUMN IF NOT EXISTS class_academic_year_id UUID REFERENCES class_academic_year(id)")

    # ============================================================
    # Section 7 — Create curriculum table
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            grade_level_id UUID NOT NULL UNIQUE REFERENCES grade_level(id),
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ============================================================
    # Section 8 — Create curriculum_version table
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_version (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            curriculum_id UUID NOT NULL REFERENCES curriculum(id),
            version_number INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_curriculum_version UNIQUE (curriculum_id, version_number)
        )
    """)

    # ============================================================
    # Section 9 — Alter subject (remove academic_year_id, add curriculum_version_id)
    # ============================================================
    op.execute("ALTER TABLE subject DROP COLUMN IF EXISTS academic_year_id")
    op.execute("ALTER TABLE subject ADD COLUMN IF NOT EXISTS curriculum_version_id UUID REFERENCES curriculum_version(id)")

    # ============================================================
    # Section 10 — Create section_subject table
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS section_subject (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            section_id UUID NOT NULL REFERENCES section(id),
            subject_id UUID NOT NULL REFERENCES subject(id),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_section_subject UNIQUE (section_id, subject_id)
        )
    """)

    # ============================================================
    # Section 11 — Create grade_academic_year_curriculum table
    # ============================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS grade_academic_year_curriculum (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            grade_level_id UUID NOT NULL REFERENCES grade_level(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            curriculum_version_id UUID NOT NULL REFERENCES curriculum_version(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_grade_academic_year_curriculum UNIQUE (grade_level_id, academic_year_id)
        )
    """)

    # ============================================================
    # Section 12 — RLS policies for new tables
    # ============================================================
    for tbl in [
        "class_academic_year", "curriculum", "curriculum_version",
        "section_subject", "grade_academic_year_curriculum",
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

    # ============================================================
    # Section 13 — Indexes for new tables
    # ============================================================
    op.execute("CREATE INDEX IF NOT EXISTS idx_class_academic_year_class ON class_academic_year(class_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_class_academic_year_year ON class_academic_year(academic_year_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_curriculum_grade_level ON curriculum(grade_level_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_curriculum_version_curriculum ON curriculum_version(curriculum_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subject_curriculum_version ON subject(curriculum_version_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_section_subject_section ON section_subject(section_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_section_subject_subject ON section_subject(subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grade_academic_year_curriculum_grade ON grade_academic_year_curriculum(grade_level_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grade_academic_year_curriculum_year ON grade_academic_year_curriculum(academic_year_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_section_class_academic_year ON section(class_academic_year_id)")

    # Update existing indexes
    op.execute("DROP INDEX IF EXISTS idx_grade_level_academic_year")
    op.execute("DROP INDEX IF EXISTS idx_class_academic_year")
    op.execute("DROP INDEX IF EXISTS idx_section_academic_year")
    op.execute("DROP INDEX IF EXISTS idx_subject_academic_year")
    op.execute("DROP INDEX IF EXISTS idx_section_class")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grade_level_org_unit ON grade_level(org_unit_id)")

    # ============================================================
    # Section 14 — Remove old config keys
    # ============================================================
    op.execute("DELETE FROM configuration_key WHERE module = 'academic'")

    # ============================================================
    # Section 15 — Update permissions
    # ============================================================
    # Remove old permissions
    op.execute("DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE resource IN ('enrollment', 'teacher_assignment'))")
    op.execute("DELETE FROM permission WHERE resource IN ('enrollment', 'teacher_assignment')")

    # Add new permissions
    new_permissions = [
        ("class_academic_year.create", "Create class academic year", "class_academic_year", "create"),
        ("class_academic_year.read", "Read class academic year", "class_academic_year", "read"),
        ("class_academic_year.update", "Update class academic year", "class_academic_year", "update"),
        ("section.create", "Create section", "section", "create"),
        ("section.read", "Read section", "section", "read"),
        ("section.update", "Update section", "section", "update"),
        ("section.delete", "Delete section", "section", "delete"),
        ("curriculum.create", "Create curriculum", "curriculum", "create"),
        ("curriculum.read", "Read curriculum", "curriculum", "read"),
        ("curriculum.update", "Update curriculum", "curriculum", "update"),
        ("curriculum_version.create", "Create curriculum version", "curriculum_version", "create"),
        ("curriculum_version.read", "Read curriculum version", "curriculum_version", "read"),
        ("section_subject.create", "Assign subject to section", "section_subject", "create"),
        ("section_subject.read", "Read section subjects", "section_subject", "read"),
        ("section_subject.update", "Update section subject", "section_subject", "update"),
    ]

    for perm_name, description, resource, action in new_permissions:
        op.execute(f"""
            INSERT INTO permission (id, name, description, resource, action)
            VALUES (gen_random_uuid(), '{perm_name}', '{description}', '{resource}', '{action}')
            ON CONFLICT (name) DO NOTHING
        """)

    # Role-permission mappings
    admin_roles = ["Admin", "institution_admin"]
    read_roles = ["Principal", "HOD", "Teacher", "Staff", "Student", "Parent"]

    for role_name in admin_roles:
        for perm_name, _, _, _ in new_permissions:
            op.execute(f"""
                INSERT INTO role_permission (id, role_id, permission_id, scope)
                SELECT gen_random_uuid(), r.id, p.id, 'institution'
                FROM role r, permission p
                WHERE r.name = '{role_name}' AND p.name = '{perm_name}'
                ON CONFLICT DO NOTHING
            """)

    # Read-only roles get read permissions
    read_perms = [p[0] for p in new_permissions if p[0].endswith('.read')]
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
    for perm_name, _, _, _ in new_permissions:
        op.execute(f"""
            INSERT INTO role_permission (id, role_id, permission_id, scope)
            SELECT gen_random_uuid(), r.id, p.id, 'tenant'
            FROM role r, permission p
            WHERE r.name = 'client_director' AND p.name = '{perm_name}'
            ON CONFLICT DO NOTHING
        """)


def downgrade() -> None:
    # Remove new permissions
    op.execute("DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE resource IN ('class_academic_year', 'section', 'curriculum', 'curriculum_version', 'section_subject'))")
    op.execute("DELETE FROM permission WHERE resource IN ('class_academic_year', 'section', 'curriculum', 'curriculum_version', 'section_subject')")

    # Drop new tables
    op.execute("DROP TABLE IF EXISTS grade_academic_year_curriculum CASCADE")
    op.execute("DROP TABLE IF EXISTS section_subject CASCADE")
    op.execute("DROP TABLE IF EXISTS curriculum_version CASCADE")
    op.execute("DROP TABLE IF EXISTS curriculum CASCADE")
    op.execute("DROP TABLE IF EXISTS class_academic_year CASCADE")

    # Restore old columns
    op.execute("ALTER TABLE subject DROP COLUMN IF EXISTS curriculum_version_id")
    op.execute("ALTER TABLE subject ADD COLUMN IF NOT EXISTS academic_year_id UUID REFERENCES academic_year(id)")

    op.execute("ALTER TABLE section DROP COLUMN IF EXISTS class_academic_year_id")
    op.execute("ALTER TABLE section ADD COLUMN IF NOT EXISTS class_id UUID REFERENCES class(id)")
    op.execute("ALTER TABLE section ADD COLUMN IF NOT EXISTS academic_year_id UUID REFERENCES academic_year(id)")
    op.execute("ALTER TABLE section ADD COLUMN IF NOT EXISTS homeroom_teacher_id UUID REFERENCES app_user(id)")

    op.execute("ALTER TABLE class ADD COLUMN IF NOT EXISTS academic_year_id UUID REFERENCES academic_year(id)")

    op.execute("ALTER TABLE grade_level DROP COLUMN IF EXISTS org_unit_id")
    op.execute("ALTER TABLE grade_level ADD COLUMN IF NOT EXISTS academic_year_id UUID REFERENCES academic_year(id)")

    op.execute("ALTER TABLE academic_year DROP COLUMN IF EXISTS closed_at")

    # Recreate old tables
    op.execute("""
        CREATE TABLE IF NOT EXISTS subject_group (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            name VARCHAR(200) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS subject_group_member (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            subject_group_id UUID NOT NULL REFERENCES subject_group(id),
            subject_id UUID NOT NULL REFERENCES subject(id),
            CONSTRAINT uq_subject_group_member UNIQUE (subject_group_id, subject_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_assignment (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            teacher_id UUID NOT NULL REFERENCES app_user(id),
            section_id UUID NOT NULL REFERENCES section(id),
            subject_id UUID NOT NULL REFERENCES subject(id),
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_teacher_assignment UNIQUE (teacher_id, section_id, subject_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS student_enrollment (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            student_id UUID NOT NULL REFERENCES app_user(id),
            section_id UUID NOT NULL REFERENCES section(id),
            enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_student_enrollment_year UNIQUE (student_id, academic_year_id)
        )
    """)
