# PRD — C-05 Academic Structure Framework

> **Capability:** C-05 Academic Structure Framework
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-14
> **Decisional source of truth:** `docs/architecture/adr-c05-academic-structure-implementation.md` (D1–D18, grill-me session 2026-08-14)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-05; `docs/architecture/adr-c01-tenant-institution-implementation.md`; `docs/architecture/adr-c02-identity-user-management-implementation.md`; `docs/prd/c-08-configuration-framework.md`
> **Scope note:** This is a **product** requirements document. Implementation detail (DB columns, API shapes, RLS policies) belongs in the spec/design phase. Decisions are referenced by ID (e.g., "per D1").

---

## 1. Problem

The platform has no formal academic structure. Academic concepts are free-text fields scattered across modules:

- `homework.grade_level` → `"Grade 5"` (free text)
- `homework.section` → `"A"` (free text)
- `homework.subject` → `"Mathematics"` (free text)
- `fee_assignment.academic_term` → `"Q1"` (free text)

This creates three problems:

1. **No referential integrity** — A student can be enrolled in "Grade 5" (text) while homework is assigned to "grade 5" (lowercase). No FK enforcement.
2. **No shared model** — Attendance, Exams, Timetable, Report Cards all need academic structure. Without C-05, each module invents its own.
3. **No historical snapshots** — Free text can't answer "What was the class structure in 2023?" or "Which students were in Section A last year?"

C-05 is the **academic backbone** of the platform. It defines the shared hierarchy (AcademicYear → Term → GradeLevel → Class → Section → Subject) that every academic module consumes.

---

## 2. Goals & Non-goals

### 2.1 In scope — C-05 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **AcademicYear** (academic cycle) | D6, D15, D18 | Year-scoped container (e.g., "2025-26"). Lifecycle: `planning → active → closed`. Only one active per institution. Current year inferred from lifecycle status. |
| **Term** (academic sub-division) | D14 | Child of AcademicYear. Each year owns its own terms (e.g., "Term 1 Apr-Sep", "Term 2 Oct-Mar"). Not reusable across years. |
| **GradeLevel** (school-specific grade) | D2, D15 | Year-specific. "Grade 1" through "Grade 12" for schools. Created per AcademicYear via template. |
| **Class** (grade section grouping) | D2, D15 | Year-specific. "10A", "10B". Created per AcademicYear via template. |
| **Section** (home-room unit) | D8, D10, D15 | Year-specific. The enrollment unit — students belong to a section for the year. Has `homeroom_teacher_id`. |
| **Subject** (course/discipline) | D3, D9 | Year-specific. "Mathematics", "Science". Assigned to sections (not classes) — different sections can have different subjects. |
| **SubjectGroup** (subject collection) | D13 | Many-to-many with Subject. "Science Group = Physics + Chemistry + Biology". |
| **Room** (physical classroom/lab) | D4 | Part of C-05. Has capacity, type (classroom/lab/library). |
| **Building** (campus building) | D4 | Part of C-05. Room belongs to a Building. |
| **TeacherAssignment** (teacher → section + subject) | D11 | Separate entity with lifecycle. Links a teacher to a subject within a section for an academic year. |
| **StudentEnrollment** (student → section) | D12 | Separate entity with history. Links a student to a section for an academic year. Transfer = deactivate old + create new. |
| **Academic structure template** (config-driven) | D1, D7 | Stored in C-08 config (`academic.schoolTemplate`). Auto-creates structure when institution is created. |
| **Year cloning** (copy from previous year) | D16 | New AcademicYear clones structure from previous year. First year falls back to config template. |
| **Lifecycle management** | D6 | AcademicYear: `planning → active → closed`. State transitions with audit trail. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Per | Notes |
|---|---|---|---|
| **College/University model** (Program, Semester, Batch) | C-05 Phase 2 | D2, platform-capabilities-v3 | Phase 1 is school-optimized. College model adds Program, Semester, Batch entities later. |
| **Elective capacity limits** | C-05 Phase 2 | — | Subject can have max seats, triggering waitlist logic. |
| **Student promotion** (automated year-end) | C-05 Phase 2 | — | Automated process to promote students to next grade. |
| **Timetable** (scheduling) | C-05 Phase 2 | — | Room + Subject + Section + Teacher scheduling. Depends on C-05 entities. |
| **Attendance** (daily/period) | Separate capability | — | Consumes C-05 (Section, Subject, StudentEnrollment). |
| **Examination** (exam scheduling, grading) | Separate capability | — | Consumes C-05 (Section, Subject, Term). |
| **Report Card** (grade compilation) | Separate capability | — | Consumes C-05 (Section, Subject, Term, GradeLevel). |
| **OrgUnit changes** | None | D5 | C-05 and OrgUnit are independent trees. No changes to OrgUnit. |
| **Homework FK migration** | Homework module | D17 | Homework changes free-text fields to FKs. Separate migration. |
| **FeeAssignment FK migration** | Fees module | — | FeeAssignment changes `academic_term` free-text to FK. Separate migration. |

### 2.3 Explicit non-goals for Phase 1

- No college/university model (Program, Semester, Batch).
- No elective capacity limits or waitlist.
- No automated student promotion.
- No timetable scheduling.
- No cross-year analytics.
- No room booking system.

---

## 3. Users / Personas

### 3.1 Platform Owner
- Creates institution types and default templates
- No direct interaction with academic structure

### 3.2 Client Director
- Manages institutions under their client
- Can view academic structure across institutions
- No direct academic structure management

### 3.3 Institution Admin (Primary Actor)
- **Creates AcademicYear** and triggers template generation
- **Customizes structure** — add/remove sections, subjects, assign teachers
- **Manages enrollment** — enroll students in sections
- **Assigns teachers** to subjects within sections
- **Transitions AcademicYear lifecycle** — planning → active → closed

### 3.4 Principal
- Views academic structure (read-only)
- Can update institution-level academic settings
- Cannot create AcademicYear or modify structure

### 3.5 HOD (Head of Department)
- Views academic structure for their department (read-only)
- Cannot modify structure

### 3.6 Teacher
- Views their assigned sections and subjects
- Creates homework for their assigned sections
- Marks attendance for their assigned sections
- Cannot modify academic structure

### 3.7 Student
- Views their enrolled section, subjects, and timetable
- Cannot modify academic structure

### 3.8 Parent
- Views their child's section, subjects, and grades
- Cannot modify academic structure

---

## 4. User Journeys

### 4.1 Institution Admin — Create New Academic Year

```
Admin logs in
  → Navigates to Academic Structure
  → Clicks "Create New Academic Year"
  → Enters: "2026-27", start date, end date
  → System clones structure from 2025-26 (or config template if first year)
  → System shows preview: 12 grade levels, 36 classes, 108 sections
  → Admin reviews and confirms
  → System creates AcademicYear in "planning" status
  → Admin customizes: removes Section C from Grade 1, adds Section D to Grade 10
  → Admin assigns homeroom teachers to sections
  → Admin assigns subjects to sections
  → Admin assigns teachers to subjects
  → Admin transitions year to "active"
  → Previous year auto-transitions to "closed"
```

### 4.2 Institution Admin — Enroll Students

```
Admin logs in
  → Navigates to Academic Structure → Grade 10 → Section A
  → Clicks "Manage Enrollment"
  → System shows current students in Section A
  → Admin clicks "Add Student"
  → Search/select student from institution's student list
  → System creates StudentEnrollment record
  → Student now appears in Section A roster
```

### 4.3 Teacher — View Assigned Sections

```
Teacher logs in
  → Dashboard shows: "You teach Mathematics in 10A-Section A, Science in 10A-Section B"
  → Clicks on "10A-Section A"
  → Sees: student roster, subject assignments, timetable
  → Creates homework for Mathematics in 10A-Section A
```

### 4.4 Student — View Enrolled Section

```
Student logs in
  → Dashboard shows: "You are in Grade 10, Section A"
  → Sees: subjects (Math, Science, English), timetable, homework
  → Cannot modify any academic structure
```

---

## 5. Acceptance Criteria

### 5.1 AcademicYear

| # | Criterion |
|---|---|
| AC-1 | Admin can create AcademicYear with name, start_date, end_date |
| AC-2 | System clones structure from previous year (or config template for first year) |
| AC-3 | Only one AcademicYear can be "active" per institution |
| AC-4 | AcademicYear lifecycle: planning → active → closed |
| AC-5 | Transition to "active" auto-closes previous active year |
| AC-6 | Closed year is read-only (no structure changes, no new enrollments) |
| AC-7 | Planning year is editable (add/remove sections, subjects, teachers) |

### 5.2 Template

| # | Criterion |
|---|---|
| AC-8 | Config key `academic.schoolTemplate` defines default structure |
| AC-9 | Template is editable per client (different clients can have different templates) |
| AC-10 | First AcademicYear uses config template; subsequent years clone from previous |
| AC-11 | Template generates GradeLevels, Classes, Sections, Subjects, Terms |

### 5.3 Enrollment

| # | Criterion |
|---|---|
| AC-12 | Student enrolled in Section via StudentEnrollment entity |
| AC-13 | Enrollment is year-specific (section implies academic year) |
| AC-14 | Transfer = deactivate old enrollment + create new enrollment |
| AC-15 | Enrollment history preserved for all years |
| AC-16 | Closed year enrollments are read-only |

### 5.4 Teacher Assignment

| # | Criterion |
|---|---|
| AC-17 | Teacher assigned to Subject within Section via TeacherAssignment entity |
| AC-18 | Multiple teachers can teach different subjects in the same section |
| AC-19 | Same teacher can teach same subject in multiple sections |
| AC-20 | Teacher assignment is year-specific |

### 5.5 Subject

| # | Criterion |
|---|---|
| AC-21 | Subject assigned to Section (not Class) |
| AC-22 | Different sections can have different subjects (elective streams) |
| AC-23 | SubjectGroup links subjects via many-to-many |
| AC-24 | Subject can belong to multiple SubjectGroups |

### 5.6 Section

| # | Criterion |
|---|---|
| AC-25 | Section has homeroom_teacher_id (one teacher per section) |
| AC-26 | Section is the enrollment unit (students enroll in sections) |
| AC-27 | Section is year-specific (created per AcademicYear) |

### 5.7 Downstream Integration

| # | Criterion |
|---|---|
| AC-28 | Homework references section_id and subject_id (not free text) |
| AC-29 | FeeAssignment references academic_term via FK (not free text) |
| AC-30 | Existing free-text data migrated to FK references |

---

## 6. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Year cloning creates many records (12 grades × 3 sections × 6 subjects = 216+ per year) | High | Low | Batch insert, async processing |
| R2 | Data migration for Homework/FeeAssignment free-text → FK | Medium | Medium | Two-phase migration: add FK columns first, backfill second |
| R3 | Performance with year-specific queries across many years | Low | Medium | Index on academic_year_id, archive old years |
| R4 | Template changes don't retroactively fix existing years | Low | Low | By design — template affects new years only |
| R5 | Homeroom teacher assignment conflicts with teacher's department (OrgUnit) | Low | Low | Independent trees (D5) — no conflict possible |
| R6 | Mid-year grade promotion (Grade 9 → Grade 10 within same year) | Low | Medium | Deferred to Phase 2 — manual workaround via transfer |

---

## 7. Open Questions

| # | Question | Status |
|---|---|---|
| Q1 | Should the template auto-create Rooms and Buildings, or are those managed separately? | Open |
| Q2 | What happens to in-flight Homework when an AcademicYear is closed? | Open |
| Q3 | Should StudentEnrollment support mid-year grade promotion (e.g., Grade 9 → Grade 10 within the same year)? | Open |
| Q4 | How does the clone handle deleted subjects from previous year? | Open |
| Q5 | Should there be a "promote students" bulk operation at year-end? | Open |
| Q6 | Should the system prevent creating Homework for a "planning" year? | Open |

---

## 8. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| C-01 Tenant & Institution | Hard | Institution must exist before AcademicYear |
| C-02 Identity & User | Hard | Teachers and students must exist for assignment/enrollment |
| C-04 Authorization | Hard | Permissions for academic structure management |
| C-08 Configuration | Hard | Template stored in config keys |
| Homework Module | Soft | Homework needs FK migration to reference C-05 |
| Fees Module | Soft | FeeAssignment needs FK migration to reference C-05 |

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| Admin time to create new academic year | < 5 minutes (with cloning) |
| Structure creation for first year | < 2 minutes (from template) |
| Student enrollment throughput | < 10 seconds per student |
| Query performance for current year structure | < 200ms |
| Zero free-text academic fields in Homework/FeeAssignment | 100% FK references |
