# Spec Delta — Academic Structure (NEW)

> **Change:** add-c05-academic-structure
> **Domain:** academic-structure
> **Impact:** ADDED (new domain)
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md` (D1-D24)

---

## ADDED Requirements

### REQ-AC-01: AcademicYear Entity

An `AcademicYear` represents an academic cycle (e.g., "2025-26") for an institution.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `name` (Text, e.g., "2025-26")
- `start_date` (Date)
- `end_date` (Date)
- `status` (String: planning | active | closed)
- `created_at`, `updated_at`

**Rules:**
- Only one AcademicYear can be "active" per institution (D18)
- Lifecycle: planning → active → closed (D6)
- Transition to "active" auto-closes previous active year (D6)
- Close is non-blocking — in-flight entities become read-only (D20)

---

### REQ-AC-02: Term Entity

A `Term` represents an academic sub-division within an AcademicYear.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `name` (Text, e.g., "Term 1")
- `start_date` (Date)
- `end_date` (Date)
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Term is a child of AcademicYear (D14)
- Each year owns its own terms (not reusable across years)

---

### REQ-AC-03: GradeLevel Entity

A `GradeLevel` represents a school-specific grade (e.g., "Grade 10").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `name` (Text, e.g., "Grade 10")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Year-specific — created per AcademicYear (D15)
- Generated from template or cloned from previous year

---

### REQ-AC-04: Class Entity

A `Class` represents a grade section grouping (e.g., "10A").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `grade_level_id` (UUID, FK → grade_level.id)
- `name` (Text, e.g., "10A")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Year-specific (D15)
- Separate entity, not OrgUnit type (D2)

---

### REQ-AC-05: Section Entity

A `Section` represents a home-room unit (e.g., "Section A of Class 10A").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `class_id` (UUID, FK → class.id)
- `name` (Text, e.g., "A")
- `homeroom_teacher_id` (UUID, FK → app_user.id, nullable)
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Year-specific (D15)
- Has homeroom_teacher_id — one teacher per section (D10)
- The enrollment unit — students enroll in sections (D8)

---

### REQ-AC-06: Subject Entity

A `Subject` represents a course/discipline (e.g., "Mathematics").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `name` (Text, e.g., "Mathematics")
- `code` (Text, nullable, e.g., "MATH101")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Year-specific (D15)
- Assigned to Section (not Class) — different sections can have different subjects (D9)
- Belongs in C-05 (D3)

---

### REQ-AC-07: SubjectGroup Entity

A `SubjectGroup` represents a collection of subjects (e.g., "Science Group").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `name` (Text, e.g., "Science Group")
- `created_at`, `updated_at`

**Rules:**
- Many-to-many with Subject via SubjectGroupMember (D13)

---

### REQ-AC-08: SubjectGroupMember Entity

Bridge table linking Subject to SubjectGroup.

**Fields:**
- `id` (UUID, PK)
- `subject_group_id` (UUID, FK → subject_group.id)
- `subject_id` (UUID, FK → subject.id)

**Rules:**
- A subject can belong to multiple groups (D13)

---

### REQ-AC-09: TeacherAssignment Entity

Links a teacher to a subject within a section for an academic year.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `teacher_id` (UUID, FK → app_user.id)
- `section_id` (UUID, FK → section.id)
- `subject_id` (UUID, FK → subject.id)
- `status` (String: active | inactive)
- `created_at`, `updated_at`

**Rules:**
- Separate entity with lifecycle (D11)
- Multiple teachers can teach different subjects in the same section
- Same teacher can teach same subject in multiple sections

---

### REQ-AC-10: StudentEnrollment Entity

Links a student to a section for an academic year.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id, repo filter)
- `academic_year_id` (UUID, FK → academic_year.id)
- `student_id` (UUID, FK → app_user.id)
- `section_id` (UUID, FK → section.id)
- `enrolled_at` (DateTime)
- `status` (String: active | transferred | withdrawn)
- `created_at`, `updated_at`

**Rules:**
- Separate entity with history (D12)
- Transfer = deactivate old + create new enrollment
- Closed year enrollments are read-only

---

### REQ-AC-11: Academic Structure Template

Config-driven template stored in C-08 that defines the default academic structure for new institutions.

**Config Keys:**
- `academic.schoolTemplate` (json) — default structure
- `academic.cloneOnNewYear` (boolean, default: true)
- `academic.defaultSectionsPerClass` (number, default: 3)
- `academic.defaultSubjects` (json, default: ["Mathematics","Science","English","Hindi","Social Studies","Computer Science"])

**Rules:**
- Template is config-driven (D7)
- Template excludes Room and Building (D19)
- First AcademicYear uses config template; subsequent years clone from previous (D16)
- Clone skips archived/deleted entities (D22)

---

### REQ-AC-12: Year Cloning

When creating a new AcademicYear, the system clones structure from the previous year.

**Rules:**
- Clone from previous year (D16)
- First year falls back to config template
- Only active entities are cloned — archived/deleted are skipped (D22)
- Homeroom teacher is cleared on clone (new year needs fresh assignments)

---

### REQ-AC-13: Year Close (Soft-Close)

Closing an AcademicYear makes it read-only without blocking.

**Rules:**
- Close is non-blocking (D20)
- In-flight homework becomes read-only (can view/grade, no new submissions)
- In-flight enrollments become read-only (no new transfers)
- No data is cancelled or deleted

---

### REQ-AC-14: Homework in Planning Year

Homework creation is allowed in an AcademicYear with status = 'planning'.

**Rules:**
- Year status doesn't gate content creation (D24)
- Homework with no students enrolled is harmless (empty submission list)

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/academic-years` | Create academic year (with clone) |
| GET | `/api/v1/academic-years` | List academic years |
| GET | `/api/v1/academic-years/{id}` | Get academic year details |
| PATCH | `/api/v1/academic-years/{id}` | Update academic year |
| POST | `/api/v1/academic-years/{id}/transition` | Transition lifecycle |
| GET | `/api/v1/academic-years/{id}/structure` | Get full structure |
| POST | `/api/v1/sections/{id}/enrollments` | Enroll student |
| GET | `/api/v1/sections/{id}/enrollments` | List enrollments |
| DELETE | `/api/v1/enrollments/{id}` | Remove enrollment |
| POST | `/api/v1/teacher-assignments` | Assign teacher |
| GET | `/api/v1/teacher-assignments` | List assignments |
| DELETE | `/api/v1/teacher-assignments/{id}` | Remove assignment |
| GET | `/api/v1/subjects` | List subjects |
| GET | `/api/v1/subject-groups` | List subject groups |

---

### REQ-FE-AC-01: Create Academic Year

The app SHALL provide a Create Academic Year flow (name, start/end dates). The system SHALL build the structure by cloning the previous year (or from the configured template for the first year), and the app SHALL preview the generated structure (grade levels, classes, sections, terms) before confirming. On confirm, the year SHALL be created in "planning" status (P2-AC-1).

#### Scenario: Clone or template generation
- **WHEN** an Institution Admin creates an academic year
- **THEN** the app generates the structure by cloning the previous year (or from the template for the first year), previews it, and creates the year in "planning" status on confirm

---

### REQ-FE-AC-02: View and Navigate Structure

The app SHALL provide a structure view where the Institution Admin can navigate grade levels → classes → sections for a selected academic year (P2-AC-2).

#### Scenario: Navigate structure hierarchy
- **WHEN** an Institution Admin opens an academic year's structure
- **THEN** they can navigate grade levels → classes → sections

---

### REQ-FE-AC-03: Transition Academic Year Lifecycle

The app SHALL allow an Institution Admin to transition an academic year's lifecycle (planning → active → closed). Activating a year SHALL auto-close the previously active year, and closed years SHALL become read-only (P2-AC-3).

#### Scenario: Activate auto-closes previous
- **WHEN** an Institution Admin activates an academic year
- **THEN** the app transitions it to "active" and the previously active year is auto-closed

#### Scenario: Closed year read-only
- **WHEN** an academic year is closed
- **THEN** the app renders it read-only

---

### REQ-FE-AC-04: Subjects and Subject Groups (read-only; management deferred)

The app SHALL provide read-only listing of subjects and subject groups via the GET-only subjects/subject-groups endpoints. Create/edit/assign is DEFERRED pending C-05 write routes (P2-AC-4, ADR R9).

#### Scenario: List subjects and subject groups
- **WHEN** an Institution Admin works with subjects and subject groups
- **THEN** they can list them (read-only); create/edit/assign is deferred

---

### REQ-FE-AC-05: Teacher Assignments

The app SHALL allow an Institution Admin to create, list, and remove teacher assignments for a section (teacher → subject within a section) (P2-AC-5).

#### Scenario: Assign teacher to subject in section
- **WHEN** an Institution Admin works on a section's teacher assignments
- **THEN** they can create, list, and remove teacher-to-subject assignments

---

### REQ-FE-AC-06: Section Enrollments

The app SHALL allow an Institution Admin to create, list, and remove section enrollments (student → section), searching/selecting from the institution roster (P2-AC-6).

#### Scenario: Enroll and remove students
- **WHEN** an Institution Admin works on a section's enrollments
- **THEN** they can list enrolled students, enroll a student from the roster, and remove an enrollment

---

### REQ-FE-AC-07: No Direct CRUD for Structure Nodes

The app SHALL provide no direct CRUD UI for sections, grades, or terms. Structure changes SHALL go through clone/template generation only, matching the backend (P2-AC-7).

#### Scenario: Structure changed only via clone/template
- **WHEN** an Institution Admin needs to change the structure
- **THEN** the app guides them to clone/template flows and offers no free-form CRUD of sections/grades/terms

---

# Delta Spec — Academic Structure (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** academic-structure
> **Delta type:** MODIFIED
> **Base spec:** `openspec/specs/academic-structure/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a, D8)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-16)

---

## MODIFIED Requirements

### REQ-AC-10: StudentEnrollment Entity (Modified — student_id FK repoint setup)

`StudentEnrollment.student_id` SHALL repoint from `app_user.id` to `student.id` (the `student` domain entity, which links to `person` via `student.person_id`). The `student` table lands in the **next capability** (domain split); this revamp's migration delivers `person` as the anchor so the repoint is possible.

**Fields (modified):**
- `student_id` (UUID, FK → `student.id`) — **was FK → `app_user.id`**

**Rules (modified):**
- Student must exist in the `student` table (was: "Student must exist in `app_user` table")
- Student must be linked to a `person` via `student.person_id` (was: "Student must have 'Student' role validated in service layer")
- The `student`/`employee` tables do not exist yet — this revamp delivers `person` as the anchor; the actual `student` table creation + FK repoint execution is the next capability

Per D3a, AC-16.

#### Scenario: Enrollment references student domain entity (after domain split)
- **GIVEN** the domain split has created the `student` table linked to `person`
- **WHEN** a student is enrolled in a section
- **THEN** `student_enrollment.student_id` SHALL reference `student.id`
- **AND** the `student` SHALL link to a `person` via `student.person_id`
- **AND** validation SHALL verify the student exists in the `student` table (NOT `app_user`)

#### Scenario: Repoint setup delivered by this revamp
- **WHEN** this revamp's migration is applied
- **THEN** `person` SHALL exist as the anchor
- **AND** the domain split (next capability) SHALL be able to create `student` and repoint `student_enrollment.student_id` → `student.id`

---

## Unchanged Requirements (explicitly noted)

### REQ-AC-05: Section Entity — homeroom_teacher_id stays on app_user

`section.homeroom_teacher_id` (FK → `app_user.id`) SHALL remain on `app_user`. Teachers are accounts with roles (D8); the homeroom-teacher FK does NOT repoint to `person` or `employee`. No delta to this requirement. Per D8.

### REQ-AC-09: TeacherAssignment Entity — teacher_id stays on app_user

`teacher_assignment.teacher_id` (FK → `app_user.id`) SHALL remain on `app_user`. Teacher assignments are account-scoped (roles stay on accounts, D8); this FK does NOT repoint. No delta to this requirement. Per D8.

---

## Cross-Cutting Notes

- The enrollment FK repoint is a cross-cutting concern spanning `academic-structure` + `identity-user-management` (`REQ-USER-AC-02`) + the future domain-split. This revamp delivers `person` as the anchor; the actual `student` table creation + FK repoint execution is the next capability. This delta records the **setup** (anchor delivered, repoint declared).
