# Impact Classification — C-05 Academic Structure Framework

> **Capability:** C-05 Academic Structure Framework
> **Status:** Draft
> **Last updated:** 2026-08-14
> **Source:** `docs/prd/c-05-academic-structure.md`, `docs/architecture/adr-c05-academic-structure-implementation.md`

---

## 1. Impact Summary

C-05 is a **new kernel capability** that adds 14 new entities and modifies 2 existing business modules. It is a cross-cutting feature that touches the academic domain, configuration framework, and downstream business modules.

| Impact Type | Count |
|---|---|
| **ADDED** (new domain) | 14 new entities |
| **MODIFIED** (existing behavior) | 2 existing modules |
| **REMOVED** (deprecated behavior) | 0 |
| **CROSS-CUTTING** (multiple domains) | 3 capabilities affected |

---

## 2. ADDED — New Domain (C-05)

### 2.1 New Entities

| Entity | Table | Description |
|---|---|---|
| AcademicYear | `academic_year` | Academic cycle with lifecycle (planning → active → closed) |
| Term | `term` | Academic sub-division, child of AcademicYear |
| GradeLevel | `grade_level` | School-specific grade (Grade 1-12), year-specific |
| Class | `class` | Grade section grouping (10A, 10B), year-specific |
| Section | `section` | Home-room unit with homeroom_teacher_id, year-specific |
| Subject | `subject` | Course/discipline, year-specific |
| SubjectGroup | `subject_group` | Collection of subjects (Science Group) |
| SubjectGroupMember | `subject_group_member` | Bridge table: Subject ↔ SubjectGroup |
| Room | `room` | Physical classroom/lab with capacity and type |
| Building | `building` | Campus building |
| TeacherAssignment | `teacher_assignment` | Teacher → Section + Subject + AcademicYear |
| StudentEnrollment | `student_enrollment` | Student → Section + AcademicYear |
| AcademicStructureTemplate | (config) | Template stored in C-08 config keys |

### 2.2 New Config Keys (C-08)

| Key | Type | Default | Category | Module |
|---|---|---|---|---|
| `academic.schoolTemplate` | json | (see below) | Academic | academic |
| `academic.cloneOnNewYear` | boolean | `true` | Academic | academic |
| `academic.defaultSectionsPerClass` | number | `3` | Academic | academic |
| `academic.defaultSubjects` | json | `["Mathematics","Science","English","Hindi","Social Studies","Computer Science"]` | Academic | academic |

**Default `academic.schoolTemplate` value:**
```json
{
  "gradeLevels": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"],
  "sections": ["A", "B", "C"],
  "defaultSubjects": ["Mathematics", "Science", "English", "Hindi", "Social Studies", "Computer Science"],
  "termStructure": "yearly"
}
```

### 2.3 New Permissions (C-04)

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

### 2.4 New API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/academic-years` | Create academic year (with clone) |
| GET | `/api/v1/academic-years` | List academic years |
| GET | `/api/v1/academic-years/{id}` | Get academic year details |
| PATCH | `/api/v1/academic-years/{id}` | Update academic year |
| POST | `/api/v1/academic-years/{id}/transition` | Transition lifecycle |
| GET | `/api/v1/academic-years/{id}/structure` | Get full structure (grades, classes, sections) |
| POST | `/api/v1/sections/{id}/enrollments` | Enroll student in section |
| GET | `/api/v1/sections/{id}/enrollments` | List section enrollments |
| DELETE | `/api/v1/enrollments/{id}` | Remove enrollment |
| POST | `/api/v1/teacher-assignments` | Assign teacher to subject in section |
| GET | `/api/v1/teacher-assignments` | List teacher assignments |
| DELETE | `/api/v1/teacher-assignments/{id}` | Remove teacher assignment |
| GET | `/api/v1/subjects` | List subjects |
| GET | `/api/v1/subject-groups` | List subject groups |
| GET | `/api/v1/rooms` | List rooms |
| GET | `/api/v1/buildings` | List buildings |

### 2.5 New RLS Policies

All C-05 tables carry `client_id` and `institution_id` for tenant isolation. RLS policies follow the existing pattern:

```sql
-- Same pattern as existing tables
CREATE POLICY academic_year_sel ON academic_year FOR SELECT USING (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY academic_year_ins ON academic_year FOR INSERT WITH CHECK (
  is_platform_owner() OR client_id = current_client_id()
);
-- ... (same for all C-05 tables)
```

---

## 3. MODIFIED — Existing Behavior

### 3.1 Homework Module

| Change | Type | Impact |
|---|---|---|
| `homework.grade_level` | Column type change | Text → FK to `grade_level.id` |
| `homework.section` | Column type change | Text → FK to `section.id` |
| `homework.subject` | Column type change | Text → FK to `subject.id` |
| Homework create/update | Service change | Must validate section_id and subject_id against C-05 |
| Homework list | Query change | Join with C-05 tables for display names |

**Migration strategy:** Two-phase:
1. Add new FK columns (`grade_level_id`, `section_id`, `subject_id`) alongside existing text columns
2. Backfill data (match text to C-05 records)
3. Drop old text columns after backfill verification

### 3.2 Fees Module

| Change | Type | Impact |
|---|---|---|
| `fee_assignment.academic_term` | Column type change | Text → FK to `term.id` |
| FeeAssignment create/update | Service change | Must validate term_id against C-05 |
| FeeAssignment list | Query change | Join with C-05 tables for display names |

**Migration strategy:** Same two-phase as Homework.

### 3.3 C-08 Configuration Framework

| Change | Type | Impact |
|---|---|---|
| New config keys | Data addition | 4 new keys in `academic` category |
| Config key CRUD | No change | C-08 framework unchanged |

---

## 4. CROSS-CUTTING — Multiple Domains Affected

### 4.1 Authorization (C-04)

| Impact | Details |
|---|---|
| New permissions | 10 new permissions for academic structure management |
| Role assignments | Admin and institution_admin get academic permissions |
| Casbin policies | New policies for academic entities |

### 4.2 Tenant & Institution (C-01)

| Impact | Details |
|---|---|
| Institution creation | Must trigger C-05 template generation |
| Institution lifecycle | Closed institution → all academic years closed |
| No schema changes | C-01 tables unchanged |

### 4.3 Identity & User (C-02)

| Impact | Details |
|---|---|
| Teacher assignment | References `app_user.id` for homeroom_teacher_id and TeacherAssignment |
| Student enrollment | References `app_user.id` for StudentEnrollment |
| No schema changes | C-02 tables unchanged |

---

## 5. Migration Plan

### 5.1 Alembic Migration (020)

1. Create C-05 tables (14 tables)
2. Seed config keys in `configuration_key`
3. Seed permissions in `permission` and `role_permission`
4. Seed default SubjectGroup "General" and default Subjects
5. Add RLS policies for all C-05 tables

### 5.2 Data Migration (Homework/FeeAssignment)

1. Add new FK columns (nullable) alongside existing text columns
2. Backfill script: match text values to C-05 records
3. Verification: count mismatches, report orphans
4. Make FK columns non-nullable
5. Drop old text columns

### 5.3 Rollback Plan

- C-05 tables are new — drop on rollback
- Homework/FeeAssignment FK columns are additive — old text columns preserved until backfill verified
- Config keys are soft-deleted on rollback

---

## 6. Testing Strategy

| Test Type | Scope |
|---|---|
| Unit tests | C-05 services (template generation, cloning, lifecycle transitions) |
| Integration tests | Homework + C-05 FK validation, FeeAssignment + C-05 FK validation |
| Authorization tests | All 10 new permissions, role coverage |
| Migration tests | Data backfill for Homework/FeeAssignment |
| E2E tests | Full flow: create year → enroll students → assign teachers → create homework |

---

## 7. Effort Estimate

| Component | Estimate |
|---|---|
| C-05 models + repos | 2 days |
| C-05 services (template, cloning, lifecycle) | 3 days |
| C-05 routes + DTOs | 2 days |
| C-05 permissions + RLS | 1 day |
| Homework FK migration | 1 day |
| FeeAssignment FK migration | 0.5 day |
| Tests | 2 days |
| Documentation + verification | 1 day |
| **Total** | **~12.5 days** |
