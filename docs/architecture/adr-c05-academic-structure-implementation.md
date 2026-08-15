# C-05 Academic Structure — Architecture Decision Record

> **Status:** Draft
> **Version:** 1.0
> **Last Updated:** 2026-08-14
> **Author:** MiMo (Xiaomi MiMo Team)
> **Source:** [platform-capabilities-v3.md](../platform-capabilities/platform-capabilities-v3.md) §C-05; grill-me session 2026-08-14
> **Purpose:** Define architectural decisions for C-05 Academic Structure Framework.
> **Cross-References:**
> - [C-05 Platform Capabilities](../platform-capabilities/platform-capabilities-v3.md) §C-05
> - [C-08 Configuration Framework PRD](../prd/c-08-configuration-framework.md)
> - [ADR C-01 Tenant & Institution](adr-c01-tenant-institution-implementation.md)
> - [ADR C-02 Identity & User Management](adr-c02-identity-user-management-implementation.md)

---

## 1. Context

### Problem

The platform has no formal academic structure. Academic concepts are free-text fields scattered across modules:

- `homework.grade_level` → `"Grade 5"` (free text)
- `homework.section` → `"A"` (free text)
- `fee_assignment.academic_term` → `"Q1"` (free text)

Downstream modules (Attendance, Exams, Timetable, Report Cards) all need a shared academic model. Without C-05, each module invents its own.

### Requirements

1. Support school structure today, college/university later
2. Auto-create academic structure when institution is created (template)
3. Year-specific snapshots for historical data integrity
4. Lifecycle management for academic years
5. Student enrollment tracking with section-level granularity
6. Teacher-to-subject assignment within sections
7. Configurable via C-08 Configuration Framework

### Existing Implementation

- **OrgUnit** — structural/administrative hierarchy (departments, buildings). Independent of academic structure.
- **C-08 Configuration** — has3 academic config keys: `academic.gradingScale`, `academic.passPercentage`, `academic.termStructure`. These are SETTINGS, not data entities.
- **Homework** — uses free-text `grade_level`, `section`, `subject` fields.
- **FeeAssignment** — uses free-text `academic_term` field.

---

## 2. Decisions

### D1: Institution-Type Templates

**Decision:** When an institution is created, C-05 auto-creates a standard academic structure based on institution type.

**Rationale:** Reduces admin setup burden. A "School" type automatically gets GradeLevels 1-12, standard sections, and default subjects.

**Implementation:** Template is config-driven (D7), stored in C-08 config values. Admin can customize after creation.

---

### D2: Separate Entities for Class and Section

**Decision:** `Class` and `Section` are new C-05 entities, not `OrgUnit` types.

**Rationale:** Academic entities need academic-specific fields (grade_level_id, academic_year_id, homeroom_teacher_id). These don't fit the generic OrgUnit model.

**Rejected Alternative:** Adding "Class" and "Section" as `org_unit_type` lookup values. Academic fields would feel bolted-on to a generic structure entity.

---

### D3: Subject Belongs in C-05

**Decision:** `Subject` ("Mathematics", "Science") is owned by C-05 Academic Structure.

**Rationale:**
- Subject is part of the academic hierarchy tree
- SubjectGroup depends on Subject
- Downstream modules (Homework, Exams, Timetable) need the bundle together
- C-05 at ~10 entities is comparable to C-02 which works fine

**Rejected Alternative:** Separate "Academic Content" capability. Would add unnecessary cross-capability dependencies.

---

### D4: Room and Building in C-05

**Decision:** `Room` and `Building` are part of C-05, not OrgUnit or a separate Facilities capability.

**Rationale:**
- Timetable (primary consumer) needs Room + Subject + Class from one capability
- Building is needed for Room
- C-05 at ~10 entities is manageable

**Rejected Alternatives:**
- Building as OrgUnit type + Room in C-05 (split related entities)
- Both as OrgUnit types (Room needs capacity/equipment fields)
- Separate Facilities capability (over-engineering for Phase 1)

---

### D5: C-05 and OrgUnit Are Independent Trees

**Decision:** C-05 entities and OrgUnit have no FK between them. They are two separate hierarchies coexisting at the same institution.

**Rationale:** Academic structure (GradeLevel → Class → Section) and structural organization (Building → Department → Wing) serve different purposes. Linking them creates unnecessary coupling.

**Implementation:** A teacher is assigned to both an OrgUnit (department) and C-05 entities (subject/class) independently.

---

### D6: AcademicYear Lifecycle

**Decision:** `AcademicYear` has formal lifecycle states: `planning → active → closed`.

**Rationale:**
- **Planning** — Admin creates the year, sets terms, assigns subjects (not visible to teachers/students)
- **Active** — Current year in progress (homework submitted, attendance marked)
- **Closed** — Year ended, data is read-only (grades locked)

**Implementation:** State transitions follow the same pattern as Institution lifecycle (C-01). Only one year can be active at a time per institution.

---

### D7: Config-Driven Template

**Decision:** Academic structure template is stored in C-08 Configuration Framework as config values.

**Rationale:**
- Consistent with C-08 philosophy ("configuration requires no code changes")
- Different clients can have different templates
- Admin can edit the template before creating institutions
- No code deploy needed for template changes

**Config Key:** `academic.schoolTemplate` (type: json)

**Example Value:**
```json
{
  "gradeLevels": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"],
  "sections": ["A", "B", "C"],
  "defaultSubjects": ["Mathematics", "Science", "English", "Hindi", "Social Studies", "Computer Science"],
  "termStructure": "yearly"
}
```

---

### D8: Student Enrolled in Section

**Decision:** A student is enrolled in a `Section` (home-room unit) for the academic year.

**Rationale:** In Indian schools, the section is the home-room unit — same group of students for all subjects. Simpler than per-subject section assignment.

**Rejected Alternatives:**
- Enrolled in Class (section is just for scheduling) — doesn't match Indian school model
- Enrolled in Class, optionally assigned to Section per subject — too complex for Phase 1

---

### D9: Subject Assigned to Section

**Decision:** Each section can have different subjects. Subjects are assigned at the section level, not the class level.

**Rationale:** Needed for elective streams in senior classes (Science vs Commerce in Grade 11). Sections within the same class can study different subjects.

**Rejected Alternative:** Subject assigned to Class (all sections study the same subjects) — doesn't support elective streams.

---

### D10: Homeroom Teacher on Section

**Decision:** `Section` has a `homeroom_teacher_id` field. One teacher per section as class teacher.

**Rationale:** In Indian schools, the "class teacher" is responsible for attendance, parent communication, and report card distribution for their section.

**Implementation:** `Section.homeroom_teacher_id` → FK to `app_user.id`. The homeroom teacher gets special permissions for their section.

---

### D11: Separate TeacherAssignment Entity

**Decision:** Teacher-to-subject assignment within a section is a separate `TeacherAssignment` entity.

**Rationale:**
- Explicit assignment with its own lifecycle
- Audit trail for assignment changes
- Extensible (substitute teachers, co-teachers, start/end dates)

**Fields:** `teacher_id`, `section_id`, `subject_id`, `academic_year_id`, `status`

---

### D12: Separate StudentEnrollment Entity

**Decision:** Student enrollment is a separate `StudentEnrollment` entity with history.

**Rationale:**
- History preserved — all section assignments for all years
- Transfer = deactivate old record + create new record
- Audit trail for enrollment events
- Consistent with TeacherAssignment pattern (D11)

**Fields:** `student_id`, `section_id`, `academic_year_id`, `enrolled_at`, `status`

---

### D13: SubjectGroup with Many-to-Many Link

**Decision:** `SubjectGroup` is a separate entity with a many-to-many `SubjectGroupMember` link to `Subject`.

**Rationale:** A subject can belong to multiple groups (Physics in both "Science Group" and "Honors Group").

**Tables:** `subject_group`, `subject_group_member` (bridge table)

---

### D14: Term Is a Child of AcademicYear

**Decision:** Each AcademicYear owns its own Terms. Terms are not reusable across years.

**Rationale:** Terms can have different date ranges per year. "Term 1" in 2025-26 might be Apr-Sep, but in 2026-27 it might be Apr-Jul.

**Rejected Alternative:** Term as a standalone entity with a bridge table — "Term 1" must mean the same thing every year, which is too rigid.

---

### D15: Everything Is Year-Specific

**Decision:** GradeLevel, Class, and Section are created per AcademicYear. They are not reusable across years.

**Rationale:**
- Full snapshot per year — clean historical data
- Complete isolation between years
- "What was 10A like in 2023?" is a simple query
- No cross-year data contamination

**Implementation:** When a new AcademicYear is created, the template generates fresh GradeLevel, Class, Section, and Subject records for that year.

---

### D16: Clone from Previous Year

**Decision:** New AcademicYear structure is cloned from the previous year. First year falls back to config template.

**Rationale:**
- Preserves customizations year over year (admin added extra sections, custom subjects)
- Reduces setup effort for subsequent years
- First year uses config template as fallback

**Implementation:** `POST /api/v1/academic-years` with `clone_from: <previous_year_id>` (optional, defaults to latest closed year).

---

### D17: Homework References Section and Subject

**Decision:** Homework links to C-05 via `section_id` and `subject_id` directly. No separate `academic_year_id` on Homework.

**Rationale:** Section is year-specific (D15), so `section_id` already implies the academic year. Fewer FKs, simpler queries.

**Migration:** Existing free-text `grade_level`, `section`, `subject` fields become FKs. Data migration converts text to IDs.

---

### D18: Current Year Inferred from Lifecycle Status

**Decision:** The current AcademicYear is the one with `status = 'active'`. No separate `is_current` flag.

**Rationale:
- Lifecycle state IS the indicator — no redundant field
- Only one year can be active at a time (enforced in code)
- Simpler queries: `WHERE status = 'active'`

**Rejected Alternative:** `is_current` boolean flag — redundant with lifecycle status, requires additional management.

---

## 3. Consequences

### Positive

1. **Single source of truth** for academic structure — all modules consume C-05
2. **Year-specific snapshots** — historical data preserved, no cross-year contamination
3. **Config-driven templates** — no code changes needed for different school structures
4. **Clone from previous year** — reduces admin effort for annual setup
5. **Lifecycle management** — clean transitions between planning, active, and closed states
6. **Extensible** — TeacherAssignment and StudentEnrollment have their own lifecycle for future features (substitute teachers, mid-year transfers)

### Negative

1. **More tables** — ~14 new entities (vs 2-3 if we used OrgUnit types)
2. **Year-specific cloning** — each year creates many records (12 grade levels × 3 sections × 6 subjects = 216+ records per year)
3. **Migration complexity** — existing free-text fields in Homework and FeeAssignment need data migration
4. **Downstream module changes** — Homework, Fees, Attendance, Exams all need to update their FK references

### Neutral

1. **OrgUnit unchanged** — C-05 is independent, no changes to existing OrgUnit model
2. **C-08 extended** — adds academic template config keys, no changes to C-08 framework

---

## 4. Model

### Entity Hierarchy

```
AcademicYear 2025-26 (status: active)
├── Term 1 (Apr-Sep)
├── Term 2 (Oct-Mar)
│
├── GradeLevel "Grade 10"
│   ├── Class "10A"
│   │   ├── Section "A" (homeroom_teacher: Mr. Sharma)
│   │   │   ├── StudentEnrollment → [Alice, Bob]
│   │   │   ├── TeacherAssignment → Math: Mr. Rao, Science: Mrs. Gupta
│   │   │   └── Subjects → [Math, Science, English]
│   │   └── Section "B" (homeroom_teacher: Mrs. Patel)
│   │       ├── StudentEnrollment → [Charlie, Dave]
│   │       └── Subjects → [Math, Commerce, Economics]
│   └── Class "10B"
│       └── ...
└── GradeLevel "Grade 11"
    └── ...
```

### Independent Trees

```
OrgUnit (structural)          C-05 (academic)
├── Building A                AcademicYear 2025-26
│   ├── Department of Science  └── Term 1
│   └── Department of Arts         └── Grade 10
└── Building B                       └── Class 10A
                                        └── Section A
                                            └── Subject: Physics
```

No FK between them. A teacher can be in both "Department of Science" (OrgUnit) and "Teaching Physics in 10A-Section A" (C-05).

### Template Flow

```
Institution created (type: "School")
  → C-08 config: academic.schoolTemplate
  → C-05 creates:
    ├── GradeLevels 1-12
    ├── Classes per grade (e.g., "1A", "1B", "2A", "2B")
    ├── Sections per class (e.g., "A", "B", "C")
    ├── Subjects (Math, Science, English, ...)
    └── Terms (Term 1, Term 2)
```

### Year Cloning Flow

```
Admin creates AcademicYear 2026-27
  → System finds latest closed year (2025-26)
  → Clones:
    ├── GradeLevels (same set)
    ├── Classes (same set)
    ├── Sections (same set, homeroom_teacher cleared)
    ├── Subjects (same set)
    └── Terms (same set, dates adjusted)
  → Admin customizes as needed
```

---

## 5. Constraints

1. **Only one active AcademicYear per institution** — enforced in application code
2. **Section is the enrollment unit** — students enroll in sections, not classes or grade levels
3. **Subject is assigned to Section** — different sections can have different subjects
4. **Year-specific isolation** — GradeLevel, Class, Section records are scoped to one AcademicYear
5. **No cross-year references** — Homework from 2024-25 cannot reference Section from 2025-26
6. **Template is config-driven** — no code changes for different school structures
7. **Clone preserves customizations** — subsequent years inherit from previous year, not from template

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| Class/Section as OrgUnit types | Academic fields don't fit generic OrgUnit model |
| Subject in separate capability | Breaks academic hierarchy, adds cross-capability dependencies |
| Room/Building in separate capability | Over-engineering for Phase 1; Timetable needs them with Subject/Class |
| C-05 linked to OrgUnit via FK | Unnecessary coupling between structural and academic trees |
| AcademicYear with `is_current` flag | Redundant with lifecycle status |
| Term as standalone reusable entity | Too rigid — "Term 1" date ranges vary by year |
| Everything institution-level (not year-specific) | Loses historical data, cross-year contamination |
| Generate from template (not clone) | Loses year-over-year customizations |
| Subject assigned to Class | Doesn't support elective streams (Science vs Commerce) |
| Student enrolled in Class | Doesn't match Indian school home-room model |

---

## 7. Future Evolution

1. **College/University model** — Add `Program`, `Semester`, `Batch` entities when onboarding non-school institutions (Phase 2)
2. **Elective capacity limits** — Subject can have max seats, triggering waitlist logic (Phase 2)
3. **Room booking** — Room availability for timetable conflict detection (Phase 2)
4. **Student promotion** — Automated year-end process to promote students to next grade (Phase 2)
5. **Cross-year analytics** — Compare performance across academic years (Phase 3)

---

## 8. Open Questions

| # | Question | Status |
|---|---|---|
| Q1 | Should the template auto-create Rooms and Buildings, or are those managed separately? | Open |
| Q2 | What happens to in-flight Homework when an AcademicYear is closed? | Open |
| Q3 | Should StudentEnrollment support mid-year grade promotion (e.g., Grade 9 → Grade 10 within the same year)? | Open |
| Q4 | How does the clone handle deleted subjects from previous year? | Open |
