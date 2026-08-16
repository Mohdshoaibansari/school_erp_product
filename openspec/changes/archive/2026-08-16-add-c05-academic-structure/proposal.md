# Proposal — C-05 Academic Structure Framework

> **Change:** add-c05-academic-structure
> **Status:** Draft
> **Last updated:** 2026-08-14
> **Source:** `docs/prd/c-05-academic-structure.md`, `docs/architecture/adr-c05-academic-structure-implementation.md`

---

## 1. Summary

Add C-05 Academic Structure Framework — a new kernel capability that defines the shared academic hierarchy (AcademicYear → Term → GradeLevel → Class → Section → Subject) consumed by Homework, Attendance, Exams, Timetable, and Report Cards.

## 2. Motivation

The platform has no formal academic structure. Academic concepts are free-text fields scattered across modules:
- `homework.grade_level` → "Grade 5" (free text)
- `homework.section` → "A" (free text)
- `homework.subject` → "Mathematics" (free text)
- `fee_assignment.academic_term` → "Q1" (free text)

This creates:
1. No referential integrity — free text can't enforce FK constraints
2. No shared model — each module invents its own academic fields
3. No historical snapshots — free text can't answer "What was 10A like in 2023?"

## 3. Scope

### In scope (Phase 1)

| Entity | Description |
|---|---|
| AcademicYear | Academic cycle with lifecycle (planning → active → closed) |
| Term | Academic sub-division, child of AcademicYear |
| GradeLevel | School-specific grade (Grade 1-12), year-specific |
| Class | Grade section grouping (10A, 10B), year-specific |
| Section | Home-room unit with homeroom_teacher_id, year-specific |
| Subject | Course/discipline, year-specific |
| SubjectGroup | Collection of subjects (Science Group) |
| SubjectGroupMember | Bridge table: Subject ↔ SubjectGroup |
| TeacherAssignment | Teacher → Section + Subject + AcademicYear |
| StudentEnrollment | Student → Section + AcademicYear |
| Academic structure template | Config-driven, stored in C-08 |
| Year cloning | Clone from previous year, fallback to template |

### Out of scope (Phase 2+)

- College/University model (Program, Semester, Batch)
- Elective capacity limits and waitlist
- Student promotion bulk operation
- Timetable scheduling
- Mid-year grade promotion
- Room/Building (stays as OrgUnit types)

## 4. Key Decisions (D1-D24)

| # | Decision |
|---|---|
| D1 | Institution-type templates auto-create academic structure |
| D2 | Class and Section are separate entities, not OrgUnit types |
| D3 | Subject belongs in C-05 |
| D4 | Room and Building stay in C-05 (but NOT in template — D19) |
| D5 | C-05 and OrgUnit are independent trees (no FK) |
| D6 | AcademicYear lifecycle: planning → active → closed |
| D7 | Config-driven template stored in C-08 |
| D8 | Student enrolled in Section (home-room unit) |
| D9 | Subject assigned to Section (different subjects per section) |
| D10 | Section has homeroom_teacher_id |
| D11 | TeacherAssignment as separate entity |
| D12 | StudentEnrollment as separate entity |
| D13 | SubjectGroup with many-to-many link |
| D14 | Term is child of AcademicYear |
| D15 | Everything is year-specific (GradeLevel, Class, Section per year) |
| D16 | Clone from previous year (first year uses config template) |
| D17 | Homework references Section and Subject directly |
| D18 | Current year inferred from lifecycle status |
| D19 | Template excludes Room and Building (12 tables) |
| D20 | AcademicYear close is non-blocking (soft-close) |
| D21 | Mid-year grade promotion is Phase 2 |
| D22 | Clone skips archived/deleted entities |
| D23 | Student promotion bulk operation is Phase 2 |
| D24 | Homework allowed in planning year |

## 5. Impact

### New entities (12 tables)

`academic_year`, `term`, `grade_level`, `class`, `section`, `subject`, `subject_group`, `subject_group_member`, `teacher_assignment`, `student_enrollment`, + 4 config keys in C-08

### Modified modules

- **Homework** — free-text fields become FKs (grade_level_id, section_id, subject_id)
- **Fees** — free-text academic_term becomes FK (term_id)

### New permissions (10)

`academic_year.create/read/update/transition`, `enrollment.create/read/update`, `teacher_assignment.create/read/update`

### Estimated effort

~12.5 days

## 6. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| C-01 Tenant & Institution | Hard | Institution must exist before AcademicYear |
| C-02 Identity & User | Hard | Teachers and students must exist |
| C-04 Authorization | Hard | Permissions for academic structure |
| C-08 Configuration | Hard | Template stored in config keys |
| Homework Module | Soft | FK migration |
| Fees Module | Soft | FK migration |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Year cloning creates many records | Batch insert, async processing |
| Data migration for Homework/FeeAssignment | Two-phase migration |
| Soft-close complexity | In-flight entities become read-only |
