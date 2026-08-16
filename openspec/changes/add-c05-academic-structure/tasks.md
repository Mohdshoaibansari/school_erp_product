# Tasks — C-05 Academic Structure Framework

> **Change:** add-c05-academic-structure
> **Status:** Draft
> **Last updated:** 2026-08-14
> **Source:** `design.md`, `specs/`

---

## Task List

### Phase 1: Models + Migration

- [x] **T01** Create `academic_year` model (`kernel/academic/models/academic_year.py`)
- [x] **T02** Create `term` model (`kernel/academic/models/term.py`)
- [x] **T03** Create `grade_level` model (`kernel/academic/models/grade_level.py`)
- [x] **T04** Create `class` model (`kernel/academic/models/class_entity.py`)
- [x] **T05** Create `section` model (`kernel/academic/models/section.py`)
- [x] **T06** Create `subject` model (`kernel/academic/models/subject.py`)
- [x] **T07** Create `subject_group` + `subject_group_member` models (`kernel/academic/models/subject_group.py`)
- [x] **T08** Create `teacher_assignment` model (`kernel/academic/models/teacher_assignment.py`)
- [x] **T09** Create `student_enrollment` model (`kernel/academic/models/student_enrollment.py`)
- [x] **T10** Create Alembic migration 020 (tables + RLS policies)
- [x] **T11** Seed config keys in migration (academic.schoolTemplate, etc.)
- [x] **T12** Seed permissions in migration (10 new permissions)
- [x] **T13** Seed role-permission mappings in migration

### Phase 2: Repos

- [x] **T14** Create `AcademicYearRepo` (`kernel/academic/repos/academic_repo.py`)
- [x] **T15** Create `StructureRepo` for GradeLevel, Class, Section (`kernel/academic/repos/structure_repo.py`)
- [x] **T16** Create `SubjectRepo` for Subject, SubjectGroup (`kernel/academic/repos/subject_repo.py`)
- [x] **T17** Create `EnrollmentRepo` for StudentEnrollment (`kernel/academic/repos/enrollment_repo.py`)
- [x] **T18** Create `AssignmentRepo` for TeacherAssignment (`kernel/academic/repos/assignment_repo.py`)

### Phase 3: Services

- [x] **T19** Create `TemplateService` — generate structure from config template (`kernel/academic/services/template_service.py`)
- [x] **T20** Create `CloneService` — clone structure from previous year (`kernel/academic/services/clone_service.py`)
- [x] **T21** Create `LifecycleService` — AcademicYear state transitions (`kernel/academic/services/lifecycle_service.py`)
- [x] **T22** Create `AcademicService` — CRUD for all entities (`kernel/academic/services/service.py`)
- [x] **T23** Create DTOs (`kernel/academic/services/dtos.py`)

### Phase 4: Routes

- [x] **T24** Create AcademicYear routes (`kernel/academic/routes/academic_years.py`)
- [x] **T25** Create Enrollment routes (`kernel/academic/routes/enrollments.py`)
- [x] **T26** Create TeacherAssignment routes (`kernel/academic/routes/assignments.py`)
- [x] **T27** Create lookup routes for Subject, SubjectGroup (`kernel/academic/routes/lookups.py`)
- [x] **T28** Create manifest (`kernel/academic/manifest.py`)
- [x] **T29** Register manifest in app factory

### Phase 5: Downstream Migration

- [x] **T30** Add FK columns to Homework (grade_level_id, section_id, subject_id) — nullable
- [x] **T31** Backfill Homework FK data (match text to C-05 records)
- [x] **T32** Make Homework FK columns non-nullable, drop old text columns
- [x] **T33** Add FK column to FeeAssignment (term_id) — nullable
- [x] **T34** Backfill FeeAssignment FK data
- [x] **T35** Make FeeAssignment FK non-nullable, drop old text column

### Phase 6: Tests

- [x] **T36** Unit tests for TemplateService
- [x] **T37** Unit tests for CloneService
- [x] **T38** Unit tests for LifecycleService
- [x] **T39** Integration tests for AcademicYear CRUD + lifecycle
- [x] **T40** Integration tests for Enrollment + TeacherAssignment
- [x] **T41** Authorization tests (10 new permissions)
- [x] **T42** Migration tests (Homework/FeeAssignment backfill)

---

## Evidence Map

| Task | Evidence |
|---|---|
| T01-T09 | Model files exist, `python -c "from kernel.academic.models import ..."` works |
| T10 | Migration runs on clean DB, tables exist with RLS |
| T11-T13 | Config keys and permissions exist in DB after migration |
| T14-T18 | Repo CRUD operations work |
| T19 | Template generates correct structure for "School" type |
| T20 | Clone creates identical structure from previous year (minus archived) |
| T21 | Lifecycle transitions work: planning → active → closed |
| T22-T23 | Service CRUD operations work |
| T24-T29 | API endpoints return correct responses |
| T30-T35 | Homework/FeeAssignment FKs work, old columns dropped |
| T36-T42 | All tests pass |
