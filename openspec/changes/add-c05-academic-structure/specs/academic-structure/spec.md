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
