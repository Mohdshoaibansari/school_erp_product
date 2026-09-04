# Spec — Academic Structure (Refactored)

> **Change:** refactor-c05-academic-structure
> **Domain:** academic-structure
> **Impact:** MODIFIED (complete refactoring)
> **Source:** `docs/prd/C-05-Academic-Structure-enhanced.md`, grill session 2026-09-02

---

## ADDED Requirements

### Requirement: AcademicYear Entity

An `AcademicYear` SHALL represent an institution's academic operating period.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `name` (Text, e.g., "2027-28")
- `start_date` (Date)
- `end_date` (Date)
- `status` (String: planning | active | closed | cancelled)
- `closed_at` (DateTime, nullable — actual closure timestamp for early closure)
- `created_at`, `updated_at`

**Rules:**
- Only one AcademicYear SHALL be "active" per institution
- Lifecycle: planning → active → closed, or planning → cancelled
- AcademicYears belonging to the same Institution MUST NOT overlap
- AcademicYears do not have to be contiguous (gaps allowed)
- Once Active: start_date and end_date SHALL be immutable
- Early closure: closed_at SHALL be set separately from end_date
- Cancelled is terminal for Planning years (no delete)

#### Scenario: Create AcademicYear

- **WHEN** admin creates an AcademicYear with name, start_date, end_date
- **THEN** AcademicYear SHALL be created with status = "planning"
- **AND** ClassAcademicYear SHALL be automatically created for every existing Class

#### Scenario: Activate AcademicYear

- **WHEN** admin activates a Planning AcademicYear
- **THEN** status SHALL change to "active"
- **AND** the system SHALL verify no other Active AcademicYear exists for the institution
- **AND** the system SHALL verify start_date and end_date are set

#### Scenario: Close AcademicYear

- **WHEN** admin closes an Active AcademicYear
- **THEN** status SHALL change to "closed"
- **AND** closed_at SHALL be set to current timestamp
- **AND** all existing Sections SHALL become immutable (cannot rename/delete)

#### Scenario: Early Closure

- **WHEN** admin closes an Active AcademicYear before end_date
- **THEN** status SHALL change to "closed"
- **AND** closed_at SHALL be set to current timestamp
- **AND** end_date SHALL remain unchanged (planned end date preserved)

#### Scenario: Cancel Planning AcademicYear

- **WHEN** admin cancels a Planning AcademicYear
- **THEN** status SHALL change to "cancelled"
- **AND** the AcademicYear SHALL be terminal (cannot be reactivated)

#### Scenario: AcademicYear Overlap Validation

- **WHEN** admin creates or updates an AcademicYear
- **THEN** the system SHALL validate no date overlap with other AcademicYears of the same institution

---

### Requirement: Term Entity

A `Term` SHALL belong to an AcademicYear and represent an academic sub-division.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `academic_year_id` (UUID, FK → academic_year.id)
- `name` (Text, e.g., "Term 1")
- `start_date` (Date)
- `end_date` (Date)
- `created_at`, `updated_at`

**Rules:**
- Term SHALL be a child of AcademicYear
- One or more Terms SHALL be allowed per AcademicYear
- Terms MUST NOT overlap within an AcademicYear
- Term names MUST be unique within an AcademicYear
- Term.start_date MUST be >= AcademicYear.start_date
- Term.end_date MUST be <= AcademicYear.end_date
- Term.start_date MUST be < Term.end_date
- Terms do not need to cover the complete AcademicYear (gaps allowed)
- Term status SHALL be computed dynamically (no status column):
  - Today < start_date → PLANNED
  - start_date <= Today <= end_date → ACTIVE
  - Today > end_date → COMPLETED

#### Scenario: Create Term

- **WHEN** admin creates a Term within an AcademicYear
- **THEN** Term SHALL be created with name, start_date, end_date
- **AND** dates SHALL be validated against AcademicYear boundaries
- **AND** no overlap with existing Terms in the same AcademicYear

#### Scenario: Term Status Computation

- **WHEN** system queries Term status
- **THEN** status SHALL be computed dynamically based on current date vs start_date/end_date

---

### Requirement: GradeLevel Entity

A `GradeLevel` SHALL be a persistent academic master (e.g., "Grade 1", "Grade 11").

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `org_unit_id` (UUID, FK → org_unit.id, nullable)
- `name` (Text, e.g., "Grade 11")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- GradeLevel SHALL be a permanent master (not tied to AcademicYear)
- GradeLevel SHALL belong to an Institution
- GradeLevel MAY be associated with an OrgUnit (optional)
- GradeLevel SHALL persist across AcademicYears
- GradeLevel SHALL anchor the Grade curriculum
- Creating a Grade SHALL NOT automatically create a Class

#### Scenario: Create GradeLevel

- **WHEN** admin creates a GradeLevel
- **THEN** GradeLevel SHALL be created as a permanent master
- **AND** no ClassAcademicYear SHALL be created automatically

---

### Requirement: Class Entity

A `Class` SHALL be a persistent academic group under GradeLevel.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `grade_level_id` (UUID, FK → grade_level.id)
- `name` (Text, e.g., "11")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Class SHALL be a permanent master (not tied to AcademicYear)
- Class and Section SHALL be separate concepts
- Section MUST NOT be encoded in the permanent Class identity (e.g., "11A" is wrong)
- Creating a Grade SHALL NOT automatically create a Class

#### Scenario: Create Class

- **WHEN** admin creates a Class under a GradeLevel
- **THEN** Class SHALL be created as a permanent master
- **AND** ClassAcademicYear SHALL NOT be created for existing Planning AcademicYears (admin must explicitly add)

---

### Requirement: ClassAcademicYear Entity

`ClassAcademicYear` SHALL be a first-class business entity representing the year-specific offering/configuration of a permanent Class.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `class_id` (UUID, FK → class.id)
- `academic_year_id` (UUID, FK → academic_year.id)
- `offered` (Boolean, default true)
- `created_at`, `updated_at`

**Rules:**
- At most one ClassAcademicYear SHALL exist for a given Class + AcademicYear combination
- ClassAcademicYear SHALL have no independent lifecycle (derived from AcademicYear)
- When AcademicYear is created, ClassAcademicYear SHALL be auto-created for every existing Class
- New Classes SHALL NOT be auto-added to existing Planning AcademicYears
- offered is configuration, not lifecycle

#### Scenario: Auto-create ClassAcademicYear on AcademicYear Creation

- **WHEN** admin creates a new AcademicYear
- **THEN** ClassAcademicYear SHALL be automatically created for every existing Class
- **AND** offered value SHALL be inherited from the latest applicable AcademicYear (if exists)

#### Scenario: Add Class to Existing Planning AcademicYear

- **WHEN** admin explicitly adds a Class to a Planning AcademicYear
- **THEN** ClassAcademicYear SHALL be created for that Class + AcademicYear
- **AND** offered SHALL default to true

#### Scenario: Configure Offered Flag

- **WHEN** admin updates ClassAcademicYear.offered
- **THEN** offered flag SHALL be updated
- **AND** if offered is set to false, system SHALL validate no Sections exist

---

### Requirement: Section Entity

A `Section` SHALL be a year-specific subdivision of a Class.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `class_academic_year_id` (UUID, FK → class_academic_year.id)
- `name` (Text, e.g., "A")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Section SHALL belong to ClassAcademicYear (not directly to AcademicYear)
- A Section SHALL exist only under an offered ClassAcademicYear
- ClassAcademicYear.offered = false → Section count SHALL be 0
- Section identity SHALL be immutable once AcademicYear is Active
- During Planning: Sections can be created, renamed, deleted
- During Active: existing Sections SHALL be protected; new Sections can be added
- During Closed: no normal Section creation or modification SHALL be allowed

#### Scenario: Create Section During Planning

- **WHEN** admin creates a Section under a Planning ClassAcademicYear
- **THEN** Section SHALL be created with name and sort_order
- **AND** ClassAcademicYear.offered MUST be true

#### Scenario: Delete Section During Planning

- **WHEN** admin deletes a Section during Planning
- **THEN** Section SHALL be deleted
- **AND** if this was the last Section, ClassAcademicYear can be set to offered=false

#### Scenario: Add Section During Active Year

- **WHEN** admin adds a Section to an Active ClassAcademicYear
- **THEN** Section SHALL be created
- **AND** operation SHALL be audited
- **AND** Section SHALL be operational immediately

#### Scenario: Protect Existing Sections During Active Year

- **WHEN** AcademicYear is Active
- **THEN** existing Sections SHALL NOT be renamed or deleted
- **AND** new Sections SHALL still be allowed to be added

---

### Requirement: Curriculum Entity

A `Curriculum` SHALL belong to a GradeLevel and represent the curriculum framework.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `grade_level_id` (UUID, FK → grade_level.id)
- `name` (Text, e.g., "Grade 11 Curriculum")
- `created_at`, `updated_at`

**Rules:**
- Curriculum SHALL belong to GradeLevel
- Each GradeLevel SHALL have one Curriculum
- Curriculum SHALL contain versioned CurriculumVersions

#### Scenario: Create Curriculum

- **WHEN** admin creates a Curriculum for a GradeLevel
- **THEN** Curriculum SHALL be created
- **AND** GradeLevel SHALL be able to have CurriculumVersions

---

### Requirement: CurriculumVersion Entity

A `CurriculumVersion` SHALL belong to a Curriculum and represent a versioned snapshot of subjects.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `curriculum_id` (UUID, FK → curriculum.id)
- `version_number` (Integer, e.g., 1, 2, 3)
- `name` (Text, e.g., "V1", "V2")
- `created_at`, `updated_at`

**Rules:**
- CurriculumVersion SHALL belong to Curriculum
- CurriculumVersion SHALL be immutable once created (enforced at app level — no update API)
- Historical versions SHALL NEVER be mutated
- Curriculum changes SHALL create a new version
- Different CurriculumVersions under the same Curriculum MAY have different Subjects

#### Scenario: Create CurriculumVersion

- **WHEN** admin creates a CurriculumVersion
- **THEN** CurriculumVersion SHALL be created with version_number and name
- **AND** Subjects SHALL be able to be added to this version

#### Scenario: Immutability Enforcement

- **WHEN** admin attempts to update a CurriculumVersion
- **THEN** system SHALL reject the request (no update API)

---

### Requirement: Subject Entity

A `Subject` SHALL belong to a CurriculumVersion and represent a course/discipline.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `curriculum_version_id` (UUID, FK → curriculum_version.id)
- `name` (Text, e.g., "Mathematics")
- `code` (Text, nullable, e.g., "MATH101")
- `sort_order` (Integer)
- `created_at`, `updated_at`

**Rules:**
- Subject SHALL belong to CurriculumVersion (not a standalone master)
- Different CurriculumVersions MAY have different Subjects
- Subject SHALL be part of the curriculum hierarchy: GradeLevel → Curriculum → CurriculumVersion → Subject

#### Scenario: Create Subject

- **WHEN** admin creates a Subject under a CurriculumVersion
- **THEN** Subject SHALL be created with name, code, sort_order

---

### Requirement: GradeAcademicYearCurriculum Entity

`GradeAcademicYearCurriculum` SHALL be a bridge entity that assigns a CurriculumVersion to a Grade for a specific AcademicYear.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `grade_level_id` (UUID, FK → grade_level.id)
- `academic_year_id` (UUID, FK → academic_year.id)
- `curriculum_version_id` (UUID, FK → curriculum_version.id)
- `created_at`, `updated_at`

**Rules:**
- One CurriculumVersion SHALL be assigned per Grade per AcademicYear
- Historical assignments SHALL remain unchanged
- Curriculum changes SHALL be prospective (new version applied to current/future years)

#### Scenario: Assign CurriculumVersion to AcademicYear

- **WHEN** admin assigns a CurriculumVersion to a Grade for an AcademicYear
- **THEN** GradeAcademicYearCurriculum record SHALL be created
- **AND** all Classes under that Grade in that AcademicYear SHALL use this CurriculumVersion

#### Scenario: Validate Uniqueness

- **WHEN** admin attempts to assign a second CurriculumVersion to the same Grade + AcademicYear
- **THEN** system SHALL reject the request (uniqueness constraint)

---

### Requirement: SectionSubject Entity

`SectionSubject` SHALL represent the applicability of a Subject to a Section.

**Fields:**
- `id` (UUID, PK)
- `client_id` (UUID, FK → client.id, RLS)
- `institution_id` (UUID, FK → institution.id)
- `section_id` (UUID, FK → section.id)
- `subject_id` (UUID, FK → subject.id)
- `is_active` (Boolean, default true)
- `created_at` (Timestamp)

**Rules:**
- A Section SHALL only select a Subject available in its applicable Grade CurriculumVersion
- Different Sections of the same Class MAY select different subsets
- The Class itself SHALL NOT own subjects
- ClassAcademicYear SHALL NOT own subjects

**Validation Flow:**
1. Get Section's ClassAcademicYear
2. From ClassAcademicYear, get parent Class → GradeLevel
3. From GradeLevel + AcademicYear, look up GradeAcademicYearCurriculum → CurriculumVersion
4. Validate Subject belongs to that CurriculumVersion

#### Scenario: Assign Subject to Section

- **WHEN** admin assigns a Subject to a Section
- **THEN** system SHALL validate Subject belongs to the applicable Grade CurriculumVersion
- **AND** SectionSubject record SHALL be created with is_active = true

#### Scenario: Disable Subject for Section

- **WHEN** admin disables a Subject for a Section
- **THEN** SectionSubject.is_active SHALL be set to false
- **AND** record SHALL be preserved for audit

#### Scenario: Validate Subject Against CurriculumVersion

- **WHEN** admin attempts to assign a Subject not in the applicable CurriculumVersion
- **THEN** system SHALL reject the request

---

### Requirement: AcademicYear Automatic ClassAcademicYear Creation

When an AcademicYear is created, the system SHALL automatically create ClassAcademicYear for every existing Class.

#### Scenario: Auto-create on AcademicYear Creation

- **WHEN** admin creates a new AcademicYear
- **THEN** system SHALL create ClassAcademicYear for every existing Class
- **AND** offered value SHALL be inherited from the latest applicable AcademicYear
- **AND** if no previous AcademicYear exists, offered SHALL default to true

---

### Requirement: New Class and Existing Planning Years

Creating a new permanent Class SHALL NOT silently modify existing Planning AcademicYears.

#### Scenario: New Class Does Not Auto-add to Planning Years

- **WHEN** admin creates a new Class
- **THEN** system SHALL NOT automatically insert it into existing Planning AcademicYears
- **AND** admin MUST explicitly add the Class to selected Planning AcademicYears

---

### Requirement: Section Identity Immutability

Once an AcademicYear is Active, Section identity SHALL be immutable.

#### Scenario: Cannot Rename Section After Activation

- **WHEN** AcademicYear is Active
- **THEN** admin SHALL NOT be able to rename existing Sections

#### Scenario: Cannot Delete Section After Activation

- **WHEN** AcademicYear is Active
- **THEN** admin SHALL NOT be able to delete existing Sections

---

### Requirement: Closed AcademicYear Immutability

Closed AcademicYears SHALL be immutable through normal Academic operations.

#### Scenario: Cannot Modify Closed Year

- **WHEN** AcademicYear is Closed
- **THEN** no normal Section creation or modification SHALL be allowed
- **AND** no normal Term creation or modification SHALL be allowed

---

### Requirement: SectionSubject Validation Against CurriculumVersion

A Section SHALL only use Subjects available in the applicable Grade CurriculumVersion.

#### Scenario: Validate Subject Availability

- **WHEN** admin assigns a Subject to a Section
- **THEN** system SHALL look up the applicable CurriculumVersion via:
  1. Section → ClassAcademicYear → Class → GradeLevel
  2. GradeLevel + AcademicYear → GradeAcademicYearCurriculum → CurriculumVersion
- **AND** SHALL validate Subject belongs to that CurriculumVersion

---

## REMOVED Requirements

### Requirement: SubjectGroup Entity

**Reason**: Replaced by Curriculum/CurriculumVersion hierarchy

**Migration**: Use Curriculum → CurriculumVersion → Subject hierarchy instead

### Requirement: SubjectGroupMember Entity

**Reason**: Replaced by Curriculum/CurriculumVersion hierarchy

**Migration**: Use Curriculum → CurriculumVersion → Subject hierarchy instead

### Requirement: TeacherAssignment Entity

**Reason**: Deferred to Teacher module (per PRD §32)

**Migration**: Will be implemented when Teacher module is addressed

### Requirement: StudentEnrollment Entity

**Reason**: Deferred to Student module (per PRD §33)

**Migration**: Will be implemented when Student module is addressed

### Requirement: Academic Structure Template

**Reason**: Not needed with permanent masters (admin-driven structure)

**Migration**: Admin creates GradeLevel, Class, Subject manually

### Requirement: Year Cloning

**Reason**: Not needed with permanent masters (structure persists across years)

**Migration**: Admin configures each AcademicYear independently

---

## API Endpoints

### AcademicYear

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/academic-years` | Create AcademicYear (auto-creates ClassAcademicYear) |
| GET | `/api/v1/academic-years` | List AcademicYears |
| GET | `/api/v1/academic-years/{id}` | Get AcademicYear details |
| PATCH | `/api/v1/academic-years/{id}` | Update Planning AcademicYear |
| POST | `/api/v1/academic-years/{id}/activate` | Activate AcademicYear |
| POST | `/api/v1/academic-years/{id}/close` | Close AcademicYear |
| POST | `/api/v1/academic-years/{id}/cancel` | Cancel Planning AcademicYear |

### Term

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/academic-years/{id}/terms` | Create Term |
| GET | `/api/v1/academic-years/{id}/terms` | List Terms |
| PATCH | `/api/v1/terms/{id}` | Update Planning Term |
| DELETE | `/api/v1/terms/{id}` | Delete Planning Term |

### GradeLevel

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/grade-levels` | Create GradeLevel |
| GET | `/api/v1/grade-levels` | List GradeLevels |
| PATCH | `/api/v1/grade-levels/{id}` | Update GradeLevel |

### Class

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/classes` | Create Class |
| GET | `/api/v1/classes` | List Classes |
| PATCH | `/api/v1/classes/{id}` | Update Class |

### ClassAcademicYear

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/academic-years/{id}/classes` | Add Class to AcademicYear |
| GET | `/api/v1/academic-years/{id}/classes` | List ClassAcademicYears |
| PATCH | `/api/v1/class-academic-years/{id}` | Update offered flag |

### Section

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/class-academic-years/{id}/sections` | Create Section |
| GET | `/api/v1/class-academic-years/{id}/sections` | List Sections |
| PATCH | `/api/v1/sections/{id}` | Update Section (Planning only) |
| DELETE | `/api/v1/sections/{id}` | Delete Section (Planning only) |

### Curriculum

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/grade-levels/{id}/curriculum` | Create Curriculum |
| GET | `/api/v1/grade-levels/{id}/curriculum` | Get Curriculum |

### CurriculumVersion

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/curricula/{id}/versions` | Create CurriculumVersion |
| GET | `/api/v1/curricula/{id}/versions` | List CurriculumVersions |

### Subject

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/curriculum-versions/{id}/subjects` | Create Subject |
| GET | `/api/v1/curriculum-versions/{id}/subjects` | List Subjects |

### GradeAcademicYearCurriculum

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/grade-levels/{id}/academic-years/{yearId}/curriculum` | Assign CurriculumVersion |
| GET | `/api/v1/grade-levels/{id}/academic-years/{yearId}/curriculum` | Get assigned CurriculumVersion |

### SectionSubject

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/sections/{id}/subjects` | Assign Subject to Section |
| GET | `/api/v1/sections/{id}/subjects` | List Section Subjects |
| PATCH | `/api/v1/section-subjects/{id}` | Enable/Disable SectionSubject |
| DELETE | `/api/v1/section-subjects/{id}` | Remove SectionSubject |
