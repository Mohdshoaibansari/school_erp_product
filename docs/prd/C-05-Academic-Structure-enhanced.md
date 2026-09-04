# C-05 Academic Structure Framework — Product Requirements Document

**Document Status:** Baseline / Business Decisions Consolidated  
**Capability:** C-05 — Academic Structure Framework  
**Primary Scope:** School academic structure  
**Future Scope:** College / University academic structure

---

## 1. Purpose

C-05 defines the academic structure used by an Institution. It separates permanent academic masters from academic-year-specific operational structure and provides the foundation for Teacher, Student, Attendance, Examination, Timetable, Reporting, and related capabilities.

The core principles are:

- Institution organizational structure is owned by C-01.
- Academic structure is owned by C-05.
- Grade and Class are persistent masters.
- ClassAcademicYear is the year-specific offering/configuration of a Class.
- Section is year-specific and belongs to ClassAcademicYear.
- Grade curriculum is versioned.
- An AcademicYear selects the applicable curriculum version.
- Actual subject applicability is determined at Section level.
- Historical academic configuration must not be retroactively altered.

---

# 2. Capability and Module Boundary

C-05 is one business capability/module.

```text
kernel/
└── academic/
    ├── models/
    ├── repos/
    ├── services/
    ├── routes/
    ├── schemas/
    └── tests/
```

Entities inside C-05 are not separate top-level business modules.

Core domain entities/concepts:

- AcademicYear
- Term
- GradeLevel
- Class
- ClassAcademicYear
- Section
- Curriculum
- CurriculumVersion
- Subject
- SectionSubject (or equivalent Section-to-Subject applicability entity)

The `kernel/academic` boundary remains the target module boundary. Internal aggregate/service organization can be refined during implementation.

---

# 3. Relationship with C-01 OrgUnit

`OrgUnit` belongs to **C-01 Tenant & Institution Management**. C-05 does not own or manage it.

```text
C-01
Client
  └── Institution
        └── OrgUnit
                 │
                 │ association/reference
                 ▼
C-05
GradeLevel
```

Example:

```text
School A1
├── OrgUnit: Primary
│   ├── Grade 1
│   ├── Grade 2
│   ├── Grade 3
│   └── Grade 4
│
└── OrgUnit: Secondary
    ├── Grade 5
    ├── Grade 6
    └── ...
```

From the administrator's perspective, an OrgUnit contains Grades. From an architectural ownership perspective:

- C-01 owns OrgUnit.
- C-05 owns GradeLevel.
- C-05 maintains the academic association to an OrgUnit.

Institution boundaries must always be respected. A Grade must not reference an OrgUnit belonging to another Institution.

C-05 should consume C-01's stable contract/reference rather than manipulate C-01 internals directly.

---

# 4. School vs College/University

The model is designed to support alternative academic structures.

Current implementation scope is **School**.

School:

```text
OrgUnit
  ↓
GradeLevel
  ↓
Class
  ↓
ClassAcademicYear
  ↓
Section
```

Future College/University:

```text
OrgUnit
  ↓
Program
  ↓
Batch
```

These are alternatives, not simultaneous mandatory levels.

| Concept | School | College | University |
|---|---:|---:|---:|
| GradeLevel | Yes | No | No |
| Program | No | Yes | Yes |
| Class | Yes | No | No |
| Batch | No | Yes | Yes |
| Section | Yes | No | No |

College/University implementation is deferred.

---

# 5. Canonical Domain Model

```text
                         C-01
                  Tenant & Institution
                         │
                    Institution
                         │
                      OrgUnit
                         │
                  association/reference
                         │
                         ▼
                         C-05
                  Academic Structure
                         │
            ┌────────────┴─────────────┐
            │                          │
       GradeLevel                  AcademicYear
            │                          │
       ┌────┴────┐                     ├── Term
       │         │                     │
 Curriculum    Class                   │
       │         │                     │
 Curriculum   ClassAcademicYear ◄──────┘
 Version        │
       │        ▼
    Subject   Section
                │
                ▼
        Section Subjects
```

The important relationships are:

```text
C-01 OrgUnit
      │
      ▼
C-05 GradeLevel
      │
      ├── Curriculum
      │     └── CurriculumVersion
      │            └── Subjects
      │
      └── Class
             └── ClassAcademicYear
                    └── Section
                           └── SectionSubject
```

and:

```text
AcademicYear
   ├── Term
   └── ClassAcademicYear
```

---

# 6. GradeLevel

GradeLevel is a persistent academic master such as Grade 1, Grade 5, or Grade 11.

Rules:

- Belongs to an Institution.
- Is associated with an OrgUnit.
- Is not directly tied to an AcademicYear.
- Persists across AcademicYears.
- Anchors the Grade curriculum.
- Creating a Grade does not automatically create a Class.

Example:

```text
Grade 11
```

remains the same Grade entity across:

```text
2025–26
2026–27
2027–28
```

The old pattern `GradeLevel.academic_year_id` is not part of the target design.

---

# 7. Class

Class is a persistent academic group under GradeLevel.

```text
Grade 11
└── Class 11
```

Rules:

- Class is not AcademicYear-specific.
- The same Class can participate in multiple AcademicYears through ClassAcademicYear.
- Class and Section are separate concepts.
- Do not encode a Section in the permanent Class identity.

Correct:

```text
Class = 11
Section = A
```

not:

```text
Class = 11A
```

Creating a Grade does not automatically create a Class. Grade and Class are separate creation operations.

The old `Class.academic_year_id` pattern is not part of the target design.

---

# 8. AcademicYear

AcademicYear represents an institution's academic operating period.

It belongs to an Institution and contains Terms and ClassAcademicYear relationships.

Core information:

- id
- institution_id
- name/label
- start_date
- end_date
- status
- audit/created/updated metadata

## Lifecycle

```text
PLANNING
   ├──→ ACTIVE → CLOSED
   │
   └──→ CANCELLED
```

## Planning

- Multiple Planning years are allowed.
- Dates are editable.
- Academic structure can be prepared in advance.
- A Planning year with no meaningful dependencies can be deleted.
- A Planning year that should not/cannot be deleted is cancelled.

## Active

- Only one Active AcademicYear per Institution.
- Start and end dates are immutable.
- Existing academic structure is operational and protected.
- Specific controlled administrative changes remain possible where explicitly permitted.

## Closed

- Historical.
- Immutable through normal Academic operations.
- No normal structural changes.
- Must not be reopened through ordinary workflows.

## Cancelled

- Terminal state for a Planning AcademicYear that is not deleted.

---

# 9. AcademicYear Date Rules

AcademicYears belonging to the same Institution must not overlap.

Valid example:

```text
2026–27: 01-Apr-2026 → 31-Mar-2027
2027–28: 01-Apr-2027 → 31-Mar-2028
```

AcademicYears do not have to be contiguous. Gaps are allowed.

Planning dates are editable subject to validation.

Once Active:

- start_date is immutable
- end_date is immutable

## Early closure

An Active AcademicYear may be closed early through a controlled administrative workflow.

The planned end date remains separate from the actual closure timestamp.

Example:

```text
end_date  = 31-Mar-2027
closed_at = 15-Mar-2027
```

The system must not rewrite the planned end date merely because the year was closed early.

---

# 10. AcademicYear Activation

Only one AcademicYear may be Active for an Institution.

The system must not automatically close the current Active year when another year is activated.

Correct sequence:

```text
Current year ACTIVE
      ↓
Explicitly CLOSE current year
      ↓
Activate another Planning year
```

Activation does not have to be chronological.

Example:

```text
2026–27 → ACTIVE
2027–28 → PLANNING
2028–29 → PLANNING
```

2028–29 may be activated without activating 2027–28 first.

No SKIPPED state is required.

---

# 11. Term

Term belongs to AcademicYear.

```text
AcademicYear
   └── Term
```

One or more Terms are allowed. There is no requirement for exactly two or three.

Each Term has:

- name
- start_date
- end_date
- status

## Date rules

```text
Term.start_date >= AcademicYear.start_date
Term.end_date   <= AcademicYear.end_date
Term.start_date < Term.end_date
```

Terms cannot overlap.

Terms do not need to cover the complete AcademicYear. Gaps are allowed.

Terms do not need equal durations.

## Boundary semantics

Non-overlapping half-open semantics are used conceptually:

```text
Term 1 = [01-Apr, 01-Jul)
Term 2 = [01-Jul, 01-Oct)
```

---

# 12. Term Lifecycle and Mutability

Lifecycle:

```text
PLANNED → ACTIVE → COMPLETED
```

There is no Term CANCELLED state in the current design.

Term status is date-driven:

```text
Today < start_date
    → PLANNED

start_date <= Today <= end_date
    → ACTIVE

Today > end_date
    → COMPLETED
```

While Planning:

- name editable
- dates editable

Once Active:

- name immutable
- dates immutable

Once Completed:

- configuration immutable

Term names must be unique within an AcademicYear.

---

# 13. ClassAcademicYear

ClassAcademicYear is a first-class business entity.

It represents:

> The year-specific offering/configuration of a permanent Class.

Relationship:

```text
GradeLevel
   └── Class
         └── ClassAcademicYear
                ├── AcademicYear
                └── Sections
```

It is not merely an incidental database join.

There must be at most one ClassAcademicYear for a given Class + AcademicYear combination.

---

# 14. ClassAcademicYear Lifecycle

ClassAcademicYear has **no independent lifecycle**.

Its context is determined by AcademicYear:

```text
AcademicYear = PLANNING
    → planning context

AcademicYear = ACTIVE
    → operational context

AcademicYear = CLOSED
    → historical context
```

Do not create an independent:

```text
PLANNED → ACTIVE → CLOSED
```

lifecycle for ClassAcademicYear.

---

# 15. Automatic ClassAcademicYear Creation

When an AcademicYear is created, the system immediately creates ClassAcademicYear for every existing Class.

Example:

```text
Existing:
Grade 1 → Class 1
Grade 2 → Class 2
...
Grade 11 → Class 11
```

Creating:

```text
2027–28 → PLANNING
```

automatically creates:

```text
Class 1 / 2027–28
Class 2 / 2027–28
...
Class 11 / 2027–28
```

This occurs at AcademicYear creation, not activation.

---

# 16. ClassAcademicYear Offered Configuration

ClassAcademicYear has a year-specific `offered` flag/configuration.

Example:

```text
Class 11

2025–26 → offered = true
2026–27 → offered = true
2027–28 → offered = false
2028–29 → offered = true
```

`offered` is configuration, not lifecycle.

## Initialization

When a new AcademicYear is created, the offered value is inherited from the latest applicable AcademicYear.

Example:

```text
2026–27
Class 3 → offered = false
```

New year:

```text
2027–28
Class 3 → offered = false
```

Administrators can change the new year's configuration while it is Planning.

Historical years are not modified.

---

# 17. New Classes and Existing Planning Years

Creating a new permanent Class must not silently modify existing Planning AcademicYears.

Example:

```text
2027–28 → PLANNING
2028–29 → PLANNING
```

Create:

```text
Class 12
```

The system does not automatically insert it into those already-prepared years.

If needed, the administrator explicitly adds the Class to a selected Planning AcademicYear.

Principle:

> Changes to permanent academic masters must not silently mutate already-prepared AcademicYear-specific configuration.

---

# 18. Class Master Changes

ClassAcademicYear references the permanent Class; it is not a snapshot.

Therefore permanent Class master changes naturally appear in all references.

Example:

```text
Class 3
Name = "Class 3"
```

renamed to:

```text
Grade 3
```

will display the new Class name wherever that Class is referenced.

This does not change year-specific configuration such as:

- offered
- Sections
- Section subjects

---

# 19. Section

Section is a year-specific subdivision of a Class.

```text
Class
   ↓
ClassAcademicYear
   ↓
Section
```

Example:

```text
Class 11 / 2026–27
├── Section A
└── Section B

Class 11 / 2027–28
├── Section A
├── Section B
└── Section C
```

The number of Sections can increase or decrease between AcademicYears.

A ClassAcademicYear may exist without Sections, particularly during Planning.

---

# 20. Section Invariants

A Section can exist only under an offered ClassAcademicYear.

Therefore:

```text
ClassAcademicYear.offered = false
    → Sections = 0
```

If Sections exist, the ClassAcademicYear cannot be changed to `offered=false`.

During Planning:

```text
offered=true
Sections exist
    ↓
remove Sections
    ↓
offered=false
```

A Planning ClassAcademicYear with `offered=false` can later be changed back to true, after which Sections may be created.

---

# 21. Section Mutability

No independent Section lifecycle is introduced at this stage.

## Planning

Sections can be:

- created
- renamed/configured
- deleted

## Active

Existing Sections are protected:

- cannot be renamed
- cannot be deleted

A new Section may still be added through a controlled administrative operation.

## Closed

No normal Section creation or modification is allowed.

Closed AcademicYears are immutable.

---

# 22. Adding a Section During an Active AcademicYear

Schools may need to create a new Section after the AcademicYear has started.

Therefore a new Section can be created during an Active year through a controlled administrative operation.

Conceptual validation:

```text
ClassAcademicYear exists
        ↓
offered = true
        ↓
AcademicYear = ACTIVE
        ↓
Section identity valid and unique
        ↓
Create Section
        ↓
Audit operation
```

A newly created Section is operational immediately; no separate Section lifecycle is introduced.

---

# 23. Section Identity

Once an AcademicYear is Active, Section identity is immutable.

For example:

```text
Section B → Section C
```

is not allowed after activation.

If a different Section is required in a future year, configure it there.

Section identity must be unique within its relevant ClassAcademicYear context.

---

# 24. Closed AcademicYear and Sections

Closed AcademicYears are immutable through normal Academic operations.

Therefore a Section cannot be created, renamed, or deleted in a Closed year through the normal Academic API.

If historical correction is ever required, it must be handled by a separate controlled correction/audit mechanism rather than reopening the AcademicYear.

---

# 25. Curriculum Model

The Grade defines its curriculum.

```text
GradeLevel
   ↓
Curriculum
   ↓
CurriculumVersion
   ↓
Subjects
```

Example:

```text
Grade 11
├── Curriculum Version 1
│   ├── Mathematics
│   ├── Physics
│   ├── Chemistry
│   └── Biology
│
└── Curriculum Version 2
    ├── Mathematics
    ├── Physics
    └── Chemistry
```

The Grade curriculum represents subjects available to that Grade.

---

# 26. Curriculum Versioning

Curriculum changes create a new version.

Historical versions are never mutated.

Example:

```text
V1
Maths + Physics + Chemistry + Biology
```

becomes:

```text
V2
Maths + Physics + Chemistry
```

Historical AcademicYears retain their previous version.

This protects historical reports and records.

---

# 27. Curriculum Version Assignment

A Grade's CurriculumVersion is assigned to an AcademicYear.

Example:

```text
Grade 11

2025–26 → V1
2026–27 → V2
2027–28 → V2
```

A later change may result in:

```text
2028–29 → V3
```

Historical assignments remain unchanged.

The business rule is:

> Each Grade uses a specific CurriculumVersion for an AcademicYear, and historical AcademicYears retain their previous version.

The exact physical persistence model can be chosen during implementation, but the business semantics are fixed.

---

# 28. Curriculum Change Policy

Curriculum changes are prospective.

Administrators do not edit a historical AcademicYear's curriculum.

When the Grade curriculum changes, a new version is created and applied from the relevant current/future AcademicYear onward.

No retroactive mutation of historical curriculum records is allowed.

---

# 29. Subject Availability vs Section Applicability

This distinction is fundamental.

The Grade CurriculumVersion defines:

> What subjects are available for this Grade?

The Section defines:

> Which of those subjects does this particular Section actually take?

Example:

```text
Grade 11 Curriculum Version
├── Mathematics
├── Physics
├── Chemistry
└── Biology
```

Then:

```text
Class 11
├── Section A
│   ├── Mathematics
│   ├── Physics
│   └── Chemistry
│
└── Section B
    ├── Biology
    ├── Physics
    └── Chemistry
```

Therefore:

```text
Grade Curriculum Version
        ↓
Available Subjects
        ↓
Section
        ↓
Applicable/Selected Subjects
```

There is intentionally no direct:

```text
Class → Subject
```

relationship.

There is intentionally no direct:

```text
ClassAcademicYear → Subject
```

relationship.

---

# 30. SectionSubject

The target domain requires a Section-to-Subject applicability relationship, represented by `SectionSubject` or an equivalent entity.

Conceptually:

```text
Section
   │
   └── SectionSubject
          └── Subject
```

Rules:

- A Section can only select a Subject available in its applicable Grade CurriculumVersion.
- Different Sections of the same Class may select different subsets.
- The Class itself does not own subjects.
- ClassAcademicYear does not own subjects.

Example:

```text
Grade 11 Curriculum
├── Maths
├── Physics
├── Chemistry
└── Biology

Section A → Maths, Physics, Chemistry
Section B → Biology, Physics, Chemistry
```

---

# 31. Earlier ClassOfferingSubject Concept

Earlier discussions used `ClassOfferingSubject` and `SectionSubject`.

The final model supersedes a Class-to-Subject ownership layer.

Because different Sections may take different subjects:

- Grade CurriculumVersion defines availability.
- Section defines actual applicability.
- Class/ClassAcademicYear does not own Subject associations.

Any earlier automatic SectionSubject creation idea must be adapted to this final model rather than introducing a Class-level subject ownership layer.

---

# 32. Teaching Assignment Boundary

Teaching Assignment belongs to the **Teacher module**, not C-05.

Teacher will reference academic entities such as:

- AcademicYear
- ClassAcademicYear
- Section
- Subject

Conceptually:

```text
C-05 Academic
      │
      │ academic context
      ▼
Teacher Module
      ├── Teacher
      └── TeachingAssignment
```

C-05 defines academic structure. Teacher defines which teacher is assigned to teach within that structure.

TeachingAssignment must not be implemented as part of C-05.

---

# 33. Student Boundary

Student-specific academic relationships are intentionally deferred.

This includes:

- Student
- Enrollment
- Student placement in Section
- Student progression
- Student-specific subject selection where applicable

These will be designed when the Student module is addressed.

C-05 provides the structures Student can reference.

---

# 34. Other Capability Boundaries

C-05 provides academic context to downstream capabilities but does not own their business responsibilities.

Potential consumers:

- Teacher
- Student
- Attendance
- Examination
- Timetable
- Reporting
- Parent communication

Examples:

```text
Academic
  → defines Section and Subject

Teacher
  → defines TeachingAssignment

Student
  → defines enrollment

Attendance
  → records attendance using those references
```

Timetable and TeachingAssignment are not C-05 entities.

---

# 35. Recommended Business Operations

The API should express business intent rather than expose unrestricted CRUD for every entity.

Expected operations include:

## AcademicYear

- Create AcademicYear
- Update Planning AcademicYear
- Activate AcademicYear
- Close AcademicYear
- Cancel Planning AcademicYear
- Delete eligible Planning AcademicYear

## Class / AcademicYear

- Add Class to an existing Planning AcademicYear
- Configure whether a Class is offered for a year

## Section

- Create Section during Planning
- Delete Section during Planning
- Add Section to an Active ClassAcademicYear through controlled operation

## Curriculum

- Create CurriculumVersion
- Assign CurriculumVersion to AcademicYear
- Change Grade curriculum prospectively

## Section Subjects

- Assign Subject to Section
- Remove/disable applicable Subject where permitted
- Validate that selected Subject belongs to the applicable Grade CurriculumVersion

Exact REST paths are implementation details.

---

# 36. Key Business Invariants

## Institution boundary

```text
Grade.institution_id
    must match
OrgUnit.institution_id
```

## AcademicYear overlap

No overlapping AcademicYears within an Institution.

## Active AcademicYear

At most one Active AcademicYear per Institution.

## Activation

The current Active AcademicYear must be explicitly closed before another becomes Active.

## Activation ordering

AcademicYears do not need to be activated chronologically.

## Terms

Terms must be contained within the AcademicYear and cannot overlap.

## ClassAcademicYear uniqueness

A Class has at most one ClassAcademicYear for a particular AcademicYear.

## Section ownership

Every Section belongs to exactly one ClassAcademicYear.

## Offered Class

```text
ClassAcademicYear.offered = false
    → Section count = 0
```

## Section subjects

A Section may only use Subjects available in the applicable Grade CurriculumVersion.

## Historical integrity

Closed AcademicYears cannot be changed through normal Academic operations.

## Curriculum integrity

Historical CurriculumVersions cannot be mutated.

---

# 37. Lifecycle Summary

```text
ACADEMIC YEAR

PLANNING
   │
   ├── configure dates
   ├── configure Terms
   ├── configure ClassAcademicYears
   ├── configure offered Classes
   ├── configure Sections
   └── configure curriculum/subject applicability
   │
   ▼
ACTIVE
   │
   ├── dates immutable
   ├── existing Section identity protected
   ├── controlled new Section creation allowed
   └── operational records may reference structure
   │
   ▼
CLOSED
   │
   └── immutable historical record
```

---

# 38. Complete School Example

```text
Client A
└── Institution: School A1
    │
    ├── OrgUnit: Primary
    │   ├── Grade 1
    │   │   └── Class 1
    │   │       └── ClassAcademicYear 2027–28
    │   │           ├── Section A
    │   │           └── Section B
    │   │
    │   └── Grade 4
    │
    └── OrgUnit: Secondary
        └── Grade 11
            │
            ├── Curriculum
            │   ├── V1
            │   │   ├── Maths
            │   │   ├── Physics
            │   │   ├── Chemistry
            │   │   └── Biology
            │   │
            │   └── V2
            │       ├── Maths
            │       ├── Physics
            │       └── Chemistry
            │
            └── Class 11
                │
                └── ClassAcademicYear 2027–28
                    │
                    ├── Section A
                    │   ├── Maths
                    │   ├── Physics
                    │   └── Chemistry
                    │
                    └── Section B
                        ├── Biology
                        ├── Physics
                        └── Chemistry
```

AcademicYear:

```text
2027–28
├── Term 1
├── Term 2
└── Term 3
```

Grade 11:

```text
2027–28 → Curriculum V2
```

---

# 39. Entity Relationship View

```text
Institution
│
├── AcademicYear
│    ├── Term
│    └── ClassAcademicYear
│
└── OrgUnit  [C-01 owned]
      │
      └── GradeLevel
            │
            ├── Curriculum
            │     └── CurriculumVersion
            │           └── Subject
            │
            └── Class
                  └── ClassAcademicYear
                        └── Section
                              └── SectionSubject
```

`ClassAcademicYear` is the first-class relationship between:

```text
Class
```

and:

```text
AcademicYear
```

---

# 40. Permanent vs Year-Specific Concepts

## Permanent/master concepts

```text
GradeLevel
Class
Curriculum
CurriculumVersion
Subject
```

## Year-specific concepts

```text
AcademicYear
Term
ClassAcademicYear
Section
SectionSubject applicability
```

The important distinction is that CurriculumVersion is itself a persistent historical version, while its assignment to an AcademicYear is year-specific.

---

# 41. Historical Integrity Principle

The fundamental C-05 rule is:

> Current academic configuration must never retroactively alter historical academic structure or curriculum.

Examples:

- Changing current curriculum creates a new CurriculumVersion.
- Changing current `offered` configuration does not change prior years.
- New Class creation does not silently modify already-prepared years.
- Historical Section identity is protected.
- Closed AcademicYears are immutable.
- Historical curriculum versions remain unchanged.

This is essential for reliable reporting, attendance, examination records, auditability, and historical reconstruction.

---

# 42. Existing Backend Drift to Address

The current backend's earlier assumptions that make academic masters directly AcademicYear-specific must be refactored toward the target model.

Examples of obsolete patterns:

```text
GradeLevel.academic_year_id
Class.academic_year_id
Section.academic_year_id
Subject.academic_year_id
```

Also obsolete:

```text
Class = 11A
```

and cloning the complete academic master structure for every AcademicYear.

The automatic closure of the current AcademicYear when activating another year is also not part of the target behavior.

The `kernel/academic` module boundary itself should be retained.

---

# 43. Explicitly Superseded Concepts

The following earlier assumptions are not part of the final model:

- Grade directly tied to AcademicYear.
- Class directly tied to AcademicYear.
- Section directly tied to Class + AcademicYear instead of ClassAcademicYear.
- Section encoded inside Class identity.
- Subject directly tied to AcademicYear as the primary curriculum model.
- Class owning Subject associations.
- ClassAcademicYear having an independent lifecycle.
- Automatic closure of the current AcademicYear.
- Sequential AcademicYear activation requirement.
- Editing historical curriculum versions.
- TeachingAssignment inside Academic.
- Student design inside Academic.

---

# 44. Non-Goals

This PRD does not define the detailed business model for:

- Student
- Student enrollment
- Teacher
- TeachingAssignment
- Attendance
- Examination
- Timetable
- Parent communication
- College/University Program/Batch implementation
- C-01 Institution/OrgUnit internal ownership model

These capabilities may consume C-05 but remain outside its ownership boundary.

---

# 45. Architectural Principles

## 45.1 Permanent vs year-specific

Do not make permanent academic masters directly AcademicYear-specific.

## 45.2 Historical safety

Never modify historical academic configuration to satisfy a current requirement.

## 45.3 Business operations over raw CRUD

Use explicit domain operations for state-changing workflows.

## 45.4 Capability ownership

Each business module owns its own concepts.

## 45.5 Explicit cross-module references

C-05 references C-01 OrgUnit but does not own it.

## 45.6 Planning is a preparation environment

A Planning AcademicYear is a real configurable academic environment.

## 45.7 Active means operational

Once Active, existing academic identities are protected and exceptional changes require controlled operations.

## 45.8 Closed means historical

Closed academic structures are immutable through normal operations.

---

# 46. High-Level Acceptance Criteria

C-05 is aligned with this PRD when:

1. Grade can exist independently of AcademicYear.
2. Class can exist independently of AcademicYear.
3. ClassAcademicYear represents Class participation/configuration for a specific AcademicYear.
4. Creating an AcademicYear automatically creates ClassAcademicYear for all existing Classes.
5. New AcademicYears inherit the latest applicable `offered` configuration.
6. Creating a new Class does not silently modify existing Planning AcademicYears.
7. Administrators can explicitly add a new Class to an existing Planning AcademicYear.
8. Section belongs to ClassAcademicYear.
9. ClassAcademicYear may exist without Sections.
10. Section requires an offered ClassAcademicYear.
11. Sections can be created/deleted during Planning.
12. Existing Sections cannot be renamed/deleted after activation.
13. New Sections can be added to Active years through controlled operations.
14. Closed years are immutable through normal Academic operations.
15. AcademicYears cannot overlap.
16. Only one AcademicYear can be Active per Institution.
17. Current Active year must be explicitly closed before another becomes Active.
18. AcademicYear activation does not have to be chronological.
19. Terms belong to AcademicYear and cannot overlap.
20. Term status is date-driven.
21. Curriculum changes create new versions.
22. Historical curriculum versions remain unchanged.
23. AcademicYear can reference the applicable Grade CurriculumVersion.
24. Section subjects are selected from the applicable Grade CurriculumVersion.
25. Class and ClassAcademicYear do not own subject associations.
26. TeachingAssignment remains outside C-05.
27. Student-specific academic relationships remain outside the current C-05 scope.
28. C-05 remains contained within `kernel/academic`.

---

# 47. Final Summary

The canonical C-05 model is:

```text
                         C-01
                  Institution Management
                         │
                    Institution
                         │
                      OrgUnit
                         │
                  association/reference
                         │
                         ▼
                         C-05
                  Academic Structure
                         │
          ┌──────────────┴──────────────┐
          │                             │
     GradeLevel                     AcademicYear
          │                             │
     ┌────┴─────┐                       ├── Term
     │          │                       │
 Curriculum    Class                    │
     │          │                       │
 Version       ClassAcademicYear ◄──────┘
     │          │
 Subjects      Section
                  │
                  └── SectionSubject
```

This document is the consolidated business baseline for C-05 Academic Structure Framework. Implementation should be compared against this baseline before refactoring.
