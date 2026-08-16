# Verify — C-05 Academic Structure Framework

> **Change:** add-c05-academic-structure
> **Status:** Draft
> **Last updated:** 2026-08-14

---

## Requirements Coverage

| Requirement | Tasks | Evidence |
|---|---|---|
| REQ-AC-01: AcademicYear | T01, T10, T14, T21, T24 | Model exists, migration runs, lifecycle transitions work |
| REQ-AC-02: Term | T02, T10, T14 | Model exists, migration runs |
| REQ-AC-03: GradeLevel | T03, T10, T15 | Model exists, migration runs |
| REQ-AC-04: Class | T04, T10, T15 | Model exists, migration runs |
| REQ-AC-05: Section | T05, T10, T15 | Model exists, migration runs, homeroom_teacher_id works |
| REQ-AC-06: Subject | T06, T10, T16 | Model exists, migration runs |
| REQ-AC-07: SubjectGroup | T07, T10, T16 | Model exists, migration runs |
| REQ-AC-08: SubjectGroupMember | T07, T10, T16 | Bridge table works |
| REQ-AC-09: TeacherAssignment | T08, T10, T18, T26 | Model exists, migration runs, API works |
| REQ-AC-10: StudentEnrollment | T09, T10, T17, T25 | Model exists, migration runs, API works |
| REQ-AC-11: Template | T11, T19 | Config keys seeded, template generation works |
| REQ-AC-12: Year Cloning | T20 | Clone from previous year works, archived skipped |
| REQ-AC-13: Soft-Close | T21 | Close is non-blocking, in-flight entities read-only |
| REQ-AC-14: Homework in Planning | T21 | Homework creation allowed in planning year |
| REQ-CONFIG-AC-01 | T11 | Config keys seeded correctly |
| REQ-AUTHZ-AC-01 | T12, T13, T41 | Permissions seeded, role mappings work |
| REQ-USER-AC-01 | T08, T18 | TeacherAssignment FK to app_user works |
| REQ-USER-AC-02 | T09, T17 | StudentEnrollment FK to app_user works |

---

## Task Coverage

| Phase | Tasks | Status |
|---|---|---|
| Models + Migration | T01-T13 | Pending |
| Repos | T14-T18 | Pending |
| Services | T19-T23 | Pending |
| Routes | T24-T29 | Pending |
| Downstream Migration | T30-T35 | Pending |
| Tests | T36-T42 | Pending |

---

## Acceptance Criteria Coverage

| AC | Criterion | Tasks | Verified |
|---|---|---|---|
| AC-1 | Admin can create AcademicYear | T01, T14, T24 | Pending |
| AC-2 | System clones structure from previous year | T20 | Pending |
| AC-3 | Only one active AcademicYear per institution | T21 | Pending |
| AC-4 | AcademicYear lifecycle: planning → active → closed | T21 | Pending |
| AC-5 | Transition to "active" auto-closes previous | T21 | Pending |
| AC-6 | Closed year is read-only | T21 | Pending |
| AC-7 | Planning year is editable | T21 | Pending |
| AC-8 | Config key defines default structure | T11 | Pending |
| AC-9 | Template editable per client | T11 | Pending |
| AC-10 | First year uses template, subsequent clone | T19, T20 | Pending |
| AC-11 | Template generates GradeLevels, Classes, Sections, Subjects, Terms | T19 | Pending |
| AC-12 | Student enrolled via StudentEnrollment | T09, T17, T25 | Pending |
| AC-13 | Enrollment is year-specific | T09 | Pending |
| AC-14 | Transfer = deactivate old + create new | T17 | Pending |
| AC-15 | Enrollment history preserved | T09 | Pending |
| AC-16 | Closed year enrollments read-only | T21 | Pending |
| AC-17 | Teacher assigned via TeacherAssignment | T08, T18, T26 | Pending |
| AC-18 | Multiple teachers per section | T08 | Pending |
| AC-19 | Same teacher multiple sections | T08 | Pending |
| AC-20 | Teacher assignment year-specific | T08 | Pending |
| AC-21 | Subject assigned to Section | T06 | Pending |
| AC-22 | Different sections different subjects | T06 | Pending |
| AC-23 | SubjectGroup many-to-many | T07 | Pending |
| AC-24 | Subject in multiple groups | T07 | Pending |
| AC-25 | Section has homeroom_teacher_id | T05 | Pending |
| AC-26 | Section is enrollment unit | T09 | Pending |
| AC-27 | Section is year-specific | T05 | Pending |
| AC-28 | Homework references section_id, subject_id | T30-T32 | Pending |
| AC-29 | FeeAssignment references term_id | T33-T35 | Pending |
| AC-30 | Free-text data migrated | T31, T34 | Pending |
| AC-31 | Clone skips archived/deleted | T20 | Pending |
| AC-32 | Close is non-blocking | T21 | Pending |
| AC-33 | Homework allowed in planning year | T21 | Pending |
