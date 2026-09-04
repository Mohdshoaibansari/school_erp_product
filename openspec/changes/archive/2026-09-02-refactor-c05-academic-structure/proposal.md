# Proposal — Refactor C-05 Academic Structure

> **Change:** refactor-c05-academic-structure
> **Status:** Draft
> **Date:** 2026-09-02

---

## Why

The current C-05 Academic Structure implementation uses year-specific entities (GradeLevel, Class, Section, Subject all have `academic_year_id`). This creates unnecessary data duplication, makes cross-year queries complex, and doesn't match the domain model where academic masters are permanent entities that participate in multiple years.

The enhanced PRD (`docs/prd/C-05-Academic-Structure-enhanced.md`) establishes a new model with permanent academic masters, ClassAcademicYear as a first-class entity, and curriculum versioning. This refactoring aligns the implementation with the target domain model.

## What Changes

### BREAKING Changes

- **GradeLevel** becomes a permanent master (remove `academic_year_id`, add `org_unit_id`)
- **Class** becomes a permanent master (remove `academic_year_id`)
- **Section** moves under ClassAcademicYear (remove `academic_year_id`, add `class_academic_year_id`)
- **Subject** moves under CurriculumVersion (remove `academic_year_id`, add `curriculum_version_id`)
- **Term** status becomes dynamically computed (remove `status` column)
- **AcademicYear** adds `closed_at` timestamp and `cancelled` status

### New Entities

- **ClassAcademicYear** — bridges Class and AcademicYear
- **Curriculum** — belongs to GradeLevel
- **CurriculumVersion** — belongs to Curriculum
- **SectionSubject** — Section-to-Subject applicability
- **GradeAcademicYearCurriculum** — bridge: GradeLevel + AcademicYear → CurriculumVersion

### Removed Entities

- **SubjectGroup** / **SubjectGroupMember** — replaced by Curriculum/CurriculumVersion
- **TeacherAssignment** — deferred to Teacher module
- **StudentEnrollment** — deferred to Student module

### Removed Config Keys

- `academic.schoolTemplate` — not needed with permanent masters
- `academic.cloneOnNewYear` — not needed
- `academic.defaultSectionsPerClass` — not needed
- `academic.defaultSubjects` — not needed

## Capabilities

### Modified Capabilities

- `academic-structure`: Complete refactoring of entity model, relationships, and business rules

### New Capabilities

None — this is a refactoring of existing capability.

### Removed Capabilities

None.

## Impact

### Affected Code

- `backend/kernel/academic/models/` — all entity models
- `backend/kernel/academic/repos/` — all repositories
- `backend/kernel/academic/services/` — all services
- `backend/kernel/academic/routes/` — all routes
- `backend/kernel/academic/schemas/` — all DTOs/schemas

### Affected APIs

All academic endpoints will change. See spec for new API design.

### Affected Dependencies

- C-01 (OrgUnit) — GradeLevel references OrgUnit
- C-04 (Authorization) — new permissions

### Migration Strategy

Greenfield implementation — drop and recreate tables. No production data to preserve.
