# Tasks — Refactor C-05 Academic Structure

> **Change:** refactor-c05-academic-structure
> **Date:** 2026-09-02

---

## 1. Database Schema (Alembic Migration)

- [x] 1.1 Drop existing C-05 tables (academic_year, term, grade_level, class, section, subject, subject_group, subject_group_member, teacher_assignment, student_enrollment)
- [x] 1.2 Create `academic_year` table (add closed_at, add cancelled status)
- [x] 1.3 Create `term` table (no status column)
- [x] 1.4 Create `grade_level` table (remove academic_year_id, add org_unit_id)
- [x] 1.5 Create `class` table (remove academic_year_id)
- [x] 1.6 Create `class_academic_year` table (new)
- [x] 1.7 Create `section` table (remove academic_year_id, add class_academic_year_id)
- [x] 1.8 Create `curriculum` table (new)
- [x] 1.9 Create `curriculum_version` table (new)
- [x] 1.10 Create `subject` table (remove academic_year_id, add curriculum_version_id)
- [x] 1.11 Create `section_subject` table (new)
- [x] 1.12 Create `grade_academic_year_curriculum` table (new)
- [x] 1.13 Add RLS policies for all C-05 tables
- [x] 1.14 Seed permissions in `permission` and `role_permission`

## 2. Models

- [x] 2.1 Update `AcademicYear` model (add closed_at, cancelled status)
- [x] 2.2 Update `Term` model (remove status column)
- [x] 2.3 Update `GradeLevel` model (remove academic_year_id, add org_unit_id)
- [x] 2.4 Update `Class` model (remove academic_year_id)
- [x] 2.5 Create `ClassAcademicYear` model
- [x] 2.6 Update `Section` model (remove academic_year_id, add class_academic_year_id)
- [x] 2.7 Create `Curriculum` model
- [x] 2.8 Create `CurriculumVersion` model
- [x] 2.9 Update `Subject` model (remove academic_year_id, add curriculum_version_id)
- [x] 2.10 Create `SectionSubject` model
- [x] 2.11 Create `GradeAcademicYearCurriculum` model
- [x] 2.12 Remove `SubjectGroup` and `SubjectGroupMember` models
- [x] 2.13 Remove `TeacherAssignment` model
- [x] 2.14 Remove `StudentEnrollment` model
- [x] 2.15 Update `__init__.py` exports

## 3. Repositories

- [x] 3.1 Create `ClassAcademicYearRepo`
- [x] 3.2 Create `CurriculumRepo`
- [x] 3.3 Create `CurriculumVersionRepo`
- [x] 3.4 Create `SectionSubjectRepo`
- [x] 3.5 Create `GradeAcademicYearCurriculumRepo`
- [x] 3.6 Update `AcademicYearRepo` (new fields, lifecycle)
- [x] 3.7 Update `TermRepo` (dynamic status)
- [x] 3.8 Update `GradeLevelRepo` (new fields)
- [x] 3.9 Update `ClassRepo` (new fields)
- [x] 3.10 Update `SectionRepo` (new fields)
- [x] 3.11 Update `SubjectRepo` (new fields)
- [x] 3.12 Remove `SubjectGroupRepo`
- [x] 3.13 Remove `TeacherAssignmentRepo`
- [x] 3.14 Remove `StudentEnrollmentRepo`

## 4. Services

- [x] 4.1 Update `AcademicYearService` (auto-create ClassAcademicYear, lifecycle transitions)
- [x] 4.2 Create `ClassAcademicYearService` (offered flag, add Class to AcademicYear)
- [x] 4.3 Create `CurriculumService` (create curriculum)
- [x] 4.4 Create `CurriculumVersionService` (create version, immutability enforcement)
- [x] 4.5 Create `SectionSubjectService` (assign/disable, validation against CurriculumVersion)
- [x] 4.6 Create `GradeAcademicYearCurriculumService` (assign CurriculumVersion to AcademicYear)
- [x] 4.7 Update `SectionService` (mutability rules, created_at tracking)
- [x] 4.8 Update `TermService` (dynamic status computation)
- [x] 4.9 Remove template/clone services

## 5. DTOs / Schemas

- [x] 5.1 Create DTOs for ClassAcademicYear
- [x] 5.2 Create DTOs for Curriculum
- [x] 5.3 Create DTOs for CurriculumVersion
- [x] 5.4 Create DTOs for SectionSubject
- [x] 5.5 Create DTOs for GradeAcademicYearCurriculum
- [x] 5.6 Update DTOs for AcademicYear (closed_at, cancelled)
- [x] 5.7 Update DTOs for Term (no status)
- [x] 5.8 Update DTOs for GradeLevel (org_unit_id)
- [x] 5.9 Update DTOs for Section (class_academic_year_id)
- [x] 5.10 Update DTOs for Subject (curriculum_version_id)

## 6. Routes

- [x] 6.1 Create routes for ClassAcademicYear
- [x] 6.2 Create routes for Curriculum
- [x] 6.3 Create routes for CurriculumVersion
- [x] 6.4 Create routes for SectionSubject
- [x] 6.5 Create routes for GradeAcademicYearCurriculum
- [x] 6.6 Update routes for AcademicYear (lifecycle endpoints)
- [x] 6.7 Update routes for Term (CRUD under AcademicYear)
- [x] 6.8 Update routes for Section (under ClassAcademicYear)
- [x] 6.9 Remove template/clone endpoints
- [x] 6.10 Remove TeacherAssignment routes
- [x] 6.11 Remove StudentEnrollment routes
- [x] 6.12 Remove SubjectGroup routes

## 7. Permissions

- [x] 7.1 Define new permissions (19 permissions)
- [x] 7.2 Seed permissions in database
- [x] 7.3 Update Casbin policies

## 8. Tests

- [x] 8.1 Unit tests for AcademicYear lifecycle (planning → active → closed, cancelled)
- [x] 8.2 Unit tests for Term dynamic status
- [x] 8.3 Unit tests for ClassAcademicYear auto-creation
- [x] 8.4 Unit tests for SectionSubject validation against CurriculumVersion
- [x] 8.5 Unit tests for Section mutability rules
- [x] 8.6 Unit tests for CurriculumVersion immutability
- [x] 8.7 Integration tests for full flow (create year → create sections → assign subjects)
- [x] 8.8 Authorization tests for all new permissions

## 9. Documentation

- [x] 9.1 Update existing ADR (`docs/architecture/adr-c05-academic-structure-implementation.md`)
- [x] 9.2 Update API documentation
- [x] 9.3 Run `openspec validate refactor-c05-academic-structure --type change --strict`
