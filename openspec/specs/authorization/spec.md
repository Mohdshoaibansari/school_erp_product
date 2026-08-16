# Spec Delta — Authorization (MODIFIED)

> **Change:** add-c05-academic-structure
> **Domain:** authorization
> **Impact:** MODIFIED (new permissions)
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md`

---

## ADDED Requirements

### REQ-AUTHZ-AC-01: Academic Structure Permissions

Add10 new permissions for C-05 academic structure management.

| Permission | Description | Default Roles |
|---|---|---|
| `academic_year.create` | Create academic year | Admin, institution_admin |
| `academic_year.read` | Read academic year | All roles |
| `academic_year.update` | Update academic year | Admin, institution_admin |
| `academic_year.transition` | Transition lifecycle | Admin, institution_admin |
| `enrollment.create` | Enroll student in section | Admin, institution_admin |
| `enrollment.read` | Read enrollments | All roles |
| `enrollment.update` | Transfer student | Admin, institution_admin |
| `teacher_assignment.create` | Assign teacher to subject | Admin, institution_admin |
| `teacher_assignment.read` | Read teacher assignments | All roles |
| `teacher_assignment.update` | Update teacher assignment | Admin, institution_admin |

**Rules:**
- Permissions seeded in Alembic migration
- Role-permission mappings for Admin, institution_admin, Principal, HOD, Teacher, Student
- C-04 remains the single source of truth (Non-Negotiable Rule 3)
