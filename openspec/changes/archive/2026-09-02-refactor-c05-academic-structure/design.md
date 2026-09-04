# Design — Refactor C-05 Academic Structure

> **Change:** refactor-c05-academic-structure
> **Status:** Draft
> **Date:** 2026-09-02

---

## Context

The current C-05 Academic Structure implementation uses year-specific entities (GradeLevel, Class, Section, Subject all have `academic_year_id`). The enhanced PRD establishes a new model with permanent academic masters, ClassAcademicYear as a first-class entity, and curriculum versioning.

### Current State

- 10 entities: AcademicYear, Term, GradeLevel, Class, Section, Subject, SubjectGroup, SubjectGroupMember, TeacherAssignment, StudentEnrollment
- All entities have `academic_year_id` (year-specific)
- Template-based auto-creation and cloning from previous year
- Config keys in C-08 for template configuration

### Target State

- 11 entities: AcademicYear, Term, GradeLevel, Class, ClassAcademicYear, Section, Curriculum, CurriculumVersion, Subject, SectionSubject, GradeAcademicYearCurriculum
- Permanent masters: GradeLevel, Class, Curriculum, CurriculumVersion, Subject
- Year-specific: AcademicYear, Term, ClassAcademicYear, Section, SectionSubject, GradeAcademicYearCurriculum
- No template/cloning — admin-driven structure

---

## Goals / Non-Goals

### Goals

1. Refactor academic entities to match the target domain model
2. Implement permanent masters (GradeLevel, Class, Subject)
3. Implement ClassAcademicYear as first-class entity
4. Implement curriculum versioning (Curriculum → CurriculumVersion → Subject)
5. Implement SectionSubject with validation against CurriculumVersion
6. Implement GradeAcademicYearCurriculum bridge table
7. Remove deferred entities (TeacherAssignment, StudentEnrollment, SubjectGroup)
8. Remove config keys (not needed with permanent masters)

### Non-Goals

1. Teacher module implementation
2. Student module implementation
3. Homework/FeeAssignment FK migration
4. College/University model
5. Data migration (greenfield implementation)

---

## Decisions

### D1: Table Strategy

**Decision:** Drop and recreate all C-05 tables.

**Rationale:** Greenfield implementation — no production data to preserve. Clean slate avoids migration complexity.

**Alternative:** Alter existing tables — more complex, not needed for greenfield.

### D2: GradeLevel → OrgUnit Reference

**Decision:** Add `org_unit_id` FK on GradeLevel (nullable).

**Rationale:** Links academic grades to organizational units (Primary/Secondary). Nullable allows grades without OrgUnit association.

### D3: CurriculumVersion Persistence

**Decision:** `grade_academic_year_curriculum` bridge table with (grade_level_id, academic_year_id, curriculum_version_id).

**Rationale:** One CurriculumVersion per Grade per AcademicYear. Bridge table expresses this constraint clearly.

**Alternative:** Put `curriculum_version_id` on ClassAcademicYear — rejected because all classes under the same Grade must use the same CurriculumVersion.

### D4: Section Model

**Decision:** Section has `class_academic_year_id` FK (not `academic_year_id`).

**Rationale:** Section belongs to ClassAcademicYear, which bridges Class and AcademicYear. AcademicYear can be derived through the relationship.

### D5: Subject Model

**Decision:** Subject has `curriculum_version_id` FK.

**Rationale:** Subject belongs to CurriculumVersion, which belongs to Curriculum, which belongs to GradeLevel. This expresses the curriculum hierarchy.

### D6: SectionSubject Fields

**Decision:** SectionSubject has `section_id`, `subject_id`, `is_active`, `created_at`.

**Rationale:** `is_active` supports disable without delete. `created_at` for audit trail.

### D7: Term Status

**Decision:** Compute Term status dynamically (no `status` column).

**Rationale:** Avoids stale status values. Status is derived from current date vs start_date/end_date.

### D8: ClassAcademicYear Lifecycle

**Decision:** No independent lifecycle (no `status` column).

**Rationale:** ClassAcademicYear context is derived from parent AcademicYear (PLANNING/ACTIVE/CLOSED).

### D9: Section Mutability Tracking

**Decision:** Track with `created_at` timestamp.

**Rationale:** Distinguishes existing vs new sections during Active year. Existing sections (created before activation) are protected; new sections can be added.

### D10: CurriculumVersion Immutability

**Decision:** Enforce at application level (no update API).

**Rationale:** Simpler than database constraints. Application simply doesn't expose an update endpoint.

### D11: Early Closure

**Decision:** Add `closed_at` column on AcademicYear (nullable).

**Rationale:** Preserves planned end_date while recording actual closure timestamp.

### D12: AcademicYear Cancelled State

**Decision:** Add `cancelled` to status enum. No delete for Planning years.

**Rationale:** Cancelled is terminal state for Planning years that won't be used. Preserves audit trail.

---

## Risks / Trade-offs

### Risk: Breaking Change

**Impact:** All existing academic data will be lost.

**Mitigation:** Greenfield implementation — no production data. Test data can be reseeded.

### Risk: Complex Validation

**Impact:** SectionSubject validation requires traversing multiple relationships.

**Mitigation:** Clear validation flow documented in spec. Service layer handles validation.

### Risk: Admin Burden

**Impact:** Without templates/cloning, admin must manually create all structure.

**Mitigation:** Acceptable for Phase 1. Can add convenience features later if needed.

---

## Migration Plan

### Steps

1. Drop existing C-05 tables (or rename for backup)
2. Create new C-05 tables (11 tables)
3. Seed permissions in `permission` and `role_permission`
4. Add RLS policies for all C-05 tables
5. Update tests

### Rollback

- New tables are new — drop on rollback
- Permissions are soft-deleted on rollback

---

## Open Questions

None — all decisions resolved in grill session.
