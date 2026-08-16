"""C-05 Academic Structure — Migration 020.

Creates:
- 10 academic structure tables with RLS policies
- 4 config keys for academic template
- 10 new permissions for academic structure management
- Role-permission mappings

Revision ID: 020_add_c05_academic_structure
Revises: 019_user_profile_admin_permission
Create Date: 2026-08-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "020_add_c05_academic_structure"
down_revision = "019_user_profile_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # Section 1 — Academic structure tables
    # ============================================================

    # AcademicYear
    op.execute("""
        CREATE TABLE academic_year (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            name VARCHAR(50) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'planning',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_academic_year_institution_name UNIQUE (institution_id, name)
        )
    """)

    # Term
    op.execute("""
        CREATE TABLE term (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            name VARCHAR(100) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # GradeLevel
    op.execute("""
        CREATE TABLE grade_level (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            name VARCHAR(100) NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Class
    op.execute("""
        CREATE TABLE class (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            grade_level_id UUID NOT NULL REFERENCES grade_level(id),
            name VARCHAR(100) NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Section
    op.execute("""
        CREATE TABLE section (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            class_id UUID NOT NULL REFERENCES class(id),
            name VARCHAR(50) NOT NULL,
            homeroom_teacher_id UUID REFERENCES app_user(id),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Subject
    op.execute("""
        CREATE TABLE subject (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            academic_year_id UUID NOT NULL REFERENCES academic_year(id),
            name VARCHAR(200) NOT NULL,
            code VARCHAR(50),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # SubjectGroup
    op.execute("""
        CREATE TABLE subject_group (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES client(id),
            institution_id UUID NOT NULL REFERENCES institution(id),
            name VARCHAR(200) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # SubjectGroupMember (bridge table)
    op.execute("""
        CREATE TABLE subject_group_member (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            subject_group_id UUID NOT NULL REFERENCES subject_group(id),
            subject_id UUID NOT NULL REFERENCES subject(id),
            CONSTRAINT uq_subject_group_member UNIQUE (subject_group_id, subject_id)
        )
    """)

    # TeacherAssignment
    op.execute("""
        CREATE TABLE teacher_assignment (
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

    # StudentEnrollment
    op.execute("""
        CREATE TABLE student_enrollment (
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

    # ============================================================
    # Section 2 — RLS policies (same pattern as existing tables)
    # ============================================================
    for tbl in [
        "academic_year", "term", "grade_level", "class", "section",
        "subject", "subject_group", "teacher_assignment", "student_enrollment",
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

    # subject_group_member has no client_id — skip RLS for it
    op.execute("ALTER TABLE subject_group_member ENABLE ROW LEVEL SECURITY")

    # ============================================================
    # Section 3 — Indexes
    # ============================================================
    op.execute("CREATE INDEX idx_academic_year_institution ON academic_year(institution_id)")
    op.execute("CREATE INDEX idx_academic_year_status ON academic_year(status)")
    op.execute("CREATE INDEX idx_term_academic_year ON term(academic_year_id)")
    op.execute("CREATE INDEX idx_grade_level_academic_year ON grade_level(academic_year_id)")
    op.execute("CREATE INDEX idx_class_grade_level ON class(grade_level_id)")
    op.execute("CREATE INDEX idx_class_academic_year ON class(academic_year_id)")
    op.execute("CREATE INDEX idx_section_class ON section(class_id)")
    op.execute("CREATE INDEX idx_section_academic_year ON section(academic_year_id)")
    op.execute("CREATE INDEX idx_subject_academic_year ON subject(academic_year_id)")
    op.execute("CREATE INDEX idx_teacher_assignment_teacher ON teacher_assignment(teacher_id)")
    op.execute("CREATE INDEX idx_teacher_assignment_section ON teacher_assignment(section_id)")
    op.execute("CREATE INDEX idx_student_enrollment_student ON student_enrollment(student_id)")
    op.execute("CREATE INDEX idx_student_enrollment_section ON student_enrollment(section_id)")
    op.execute("CREATE INDEX idx_student_enrollment_academic_year ON student_enrollment(academic_year_id)")

    # ============================================================
    # Section 4 — Config keys (T11)
    # ============================================================
    op.execute("""
        INSERT INTO configuration_key (id, key, type, default_value, merge_strategy, category, module, description, is_feature_toggle)
        VALUES
            (gen_random_uuid(), 'academic.schoolTemplate', 'json',
             '{"gradeLevels":["Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6","Grade 7","Grade 8","Grade 9","Grade 10","Grade 11","Grade 12"],"sections":["A","B","C"],"defaultSubjects":["Mathematics","Science","English","Hindi","Social Studies","Computer Science"],"termStructure":"yearly"}'::jsonb,
             'replace', 'Academic', 'academic', 'Default academic structure template for new institutions', FALSE),
            (gen_random_uuid(), 'academic.cloneOnNewYear', 'boolean', 'true'::jsonb,
             'replace', 'Academic', 'academic', 'Whether to clone structure from previous year when creating new AcademicYear', FALSE),
            (gen_random_uuid(), 'academic.defaultSectionsPerClass', 'number', '3'::jsonb,
             'replace', 'Academic', 'academic', 'Default number of sections per class in template', FALSE),
            (gen_random_uuid(), 'academic.defaultSubjects', 'json',
             '["Mathematics","Science","English","Hindi","Social Studies","Computer Science"]'::jsonb,
             'replace', 'Academic', 'academic', 'Default subjects for academic template', FALSE)
        ON CONFLICT (key) DO NOTHING
    """)

    # ============================================================
    # Section 5 — Permissions (T12)
    # ============================================================
    permissions = [
        ("academic_year.create", "Create academic year", "academic_year", "create"),
        ("academic_year.read", "Read academic year", "academic_year", "read"),
        ("academic_year.update", "Update academic year", "academic_year", "update"),
        ("academic_year.transition", "Transition academic year lifecycle", "academic_year", "transition"),
        ("enrollment.create", "Enroll student in section", "enrollment", "create"),
        ("enrollment.read", "Read enrollments", "enrollment", "read"),
        ("enrollment.update", "Transfer student enrollment", "enrollment", "update"),
        ("teacher_assignment.create", "Assign teacher to subject", "teacher_assignment", "create"),
        ("teacher_assignment.read", "Read teacher assignments", "teacher_assignment", "read"),
        ("teacher_assignment.update", "Update teacher assignment", "teacher_assignment", "update"),
    ]

    for perm_name, description, resource, action in permissions:
        op.execute(f"""
            INSERT INTO permission (id, name, description, resource, action)
            VALUES (gen_random_uuid(), '{perm_name}', '{description}', '{resource}', '{action}')
            ON CONFLICT (name) DO NOTHING
        """)

    # ============================================================
    # Section 6 — Role-permission mappings (T13)
    # ============================================================
    # Admin and institution_admin get all academic permissions
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
    read_perms = ["academic_year.read", "enrollment.read", "teacher_assignment.read"]
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
    # Remove role-permission mappings
    op.execute("""
        DELETE FROM role_permission
        WHERE permission_id IN (SELECT id FROM permission WHERE resource IN ('academic_year', 'enrollment', 'teacher_assignment'))
    """)

    # Remove permissions
    op.execute("DELETE FROM permission WHERE resource IN ('academic_year', 'enrollment', 'teacher_assignment')")

    # Remove config keys
    op.execute("DELETE FROM configuration_key WHERE module = 'academic'")

    # Drop tables in reverse order
    for tbl in [
        "student_enrollment", "teacher_assignment", "subject_group_member",
        "subject_group", "subject", "section", "class", "grade_level",
        "term", "academic_year",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
