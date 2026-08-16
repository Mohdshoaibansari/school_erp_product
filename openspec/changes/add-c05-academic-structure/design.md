# Design — C-05 Academic Structure Framework

> **Change:** add-c05-academic-structure
> **Status:** Draft
> **Last updated:** 2026-08-14
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md`, `docs/prd/c-05-academic-structure.md`

---

## 1. Architecture Overview

C-05 is a new kernel capability that follows the existing modular monolith pattern:

```
kernel/academic/
├── manifest.py              # Route + policy registration
├── models/
│   ├── academic_year.py     # AcademicYear entity
│   ├── term.py              # Term entity
│   ├── grade_level.py       # GradeLevel entity
│   ├── class_entity.py      # Class entity
│   ├── section.py           # Section entity
│   ├── subject.py           # Subject entity
│   ├── subject_group.py     # SubjectGroup + SubjectGroupMember
│   ├── teacher_assignment.py # TeacherAssignment entity
│   └── student_enrollment.py # StudentEnrollment entity
├── repos/
│   ├── academic_repo.py     # AcademicYear, Term repos
│   ├── structure_repo.py    # GradeLevel, Class, Section repos
│   ├── subject_repo.py      # Subject, SubjectGroup repos
│   ├── enrollment_repo.py   # StudentEnrollment repo
│   └── assignment_repo.py   # TeacherAssignment repo
├── services/
│   ├── service.py           # Core CRUD services
│   ├── template_service.py  # Template generation logic
│   ├── clone_service.py     # Year cloning logic
│   ├── lifecycle_service.py # AcademicYear lifecycle transitions
│   └── dtos.py              # Pydantic DTOs
├── routes/
│   ├── academic_years.py    # AcademicYear endpoints
│   ├── enrollments.py       # StudentEnrollment endpoints
│   ├── assignments.py       # TeacherAssignment endpoints
│   └── lookups.py           # Subject, SubjectGroup lookups
└── dependencies.py          # FastAPI DI
```

---

## 2. Entity Relationships

```
AcademicYear (1) ──── (N) Term
     │
     │ (1)
     │
     ├─── (N) GradeLevel ──── (N) Class ──── (N) Section
     │                                         │
     │                                         ├── (N) StudentEnrollment → app_user
     │                                         ├── (N) TeacherAssignment → app_user + Subject
     │                                         └── homeroom_teacher_id → app_user
     │
     └─── (N) Subject ──── (N) SubjectGroupMember ──── (1) SubjectGroup
```

---

## 3. Template Generation Flow

```
Institution created
  → C-08 config: academic.schoolTemplate
  → TemplateService.generate_from_template(institution_id, client_id)
    → Parse template JSON
    → For each gradeLevel in template:
        → Create GradeLevel record
        → For each section in template.sections:
            → Create Class record (e.g., "10A")
            → Create Section record (e.g., "A")
    → For each subject in template.defaultSubjects:
        → Create Subject record
    → Create Terms based on termStructure ("yearly" = [Term 1, Term 2])
```

---

## 4. Year Cloning Flow

```
Admin creates AcademicYear 2026-27
  → CloneService.clone_from_previous(new_year_id)
    → Find latest closed year (2025-26)
    → Clone GradeLevels (WHERE archived_at IS NULL)
    → Clone Classes (WHERE archived_at IS NULL)
    → Clone Sections (WHERE archived_at IS NULL, homeroom_teacher_id = NULL)
    → Clone Subjects (WHERE archived_at IS NULL)
    → Clone Terms (dates adjusted to new year)
    → Skip archived/deleted entities (D22)
```

---

## 5. Lifecycle State Machine

```
                  ┌─────────────┐
                  │   planning  │
                  └──────┬──────┘
                         │ transition("active")
                         │ (auto-closes previous active year)
                         ▼
                  ┌─────────────┐
                  │   active    │
                  └──────┬──────┘
                         │ transition("closed")
                         │ (soft-close — in-flight entities become read-only)
                         ▼
                  ┌─────────────┐
                  │   closed    │
                  └─────────────┘
```

**Transition rules:**
- planning → active: Only one active year per institution. Auto-closes previous active year.
- active → closed: Non-blocking. In-flight homework/enrollments become read-only.
- No reverse transitions (closed → active is not allowed).

---

## 6. Homework FK Migration

**Phase 1: Add new FK columns (nullable)**
```sql
ALTER TABLE homework ADD COLUMN grade_level_id UUID REFERENCES grade_level(id);
ALTER TABLE homework ADD COLUMN section_id UUID REFERENCES section(id);
ALTER TABLE homework ADD COLUMN subject_id UUID REFERENCES subject(id);
```

**Phase 2: Backfill data**
```python
# Match free-text to C-05 records
for homework in db.query(Homework).all():
    grade = db.query(GradeLevel).filter_by(name=homework.grade_level).first()
    section = db.query(Section).filter_by(name=homework.section).first()
    subject = db.query(Subject).filter_by(name=homework.subject).first()
    if grade and section and subject:
        homework.grade_level_id = grade.id
        homework.section_id = section.id
        homework.subject_id = subject.id
```

**Phase 3: Make non-nullable, drop old columns**
```sql
ALTER TABLE homework ALTER COLUMN section_id SET NOT NULL;
ALTER TABLE homework ALTER COLUMN subject_id SET NOT NULL;
ALTER TABLE homework DROP COLUMN grade_level;
ALTER TABLE homework DROP COLUMN section;
ALTER TABLE homework DROP COLUMN subject;
```

---

## 7. Soft-Close Implementation

When AcademicYear transitions to "closed":

1. Set `academic_year.status = 'closed'`
2. Update all Homework referencing sections in this year:
   - `WHERE section_id IN (SELECT id FROM section WHERE academic_year_id = :year_id)`
   - Set `homework.status = 'closed'` (read-only — can view/grade, no new submissions)
3. Update all StudentEnrollment in this year:
   - `WHERE academic_year_id = :year_id`
   - Set `status = 'archived'` (read-only — no new transfers)
4. Update all TeacherAssignment in this year:
   - `WHERE academic_year_id = :year_id`
   - Set `status = 'archived'` (read-only)

---

## 8. RLS Policies

All C-05 tables carry `client_id` and `institution_id`. RLS policies follow the existing pattern:

```sql
-- AcademicYear
CREATE POLICY academic_year_sel ON academic_year FOR SELECT USING (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY academic_year_ins ON academic_year FOR INSERT WITH CHECK (
  is_platform_owner() OR client_id = current_client_id()
);
-- Same pattern for all C-05 tables
```

---

## 9. Permission Model

10 new permissions (see authorization spec). Role assignments:

| Role | Permissions |
|---|---|
| Admin | All10 permissions |
| institution_admin | All10 permissions |
| Principal | academic_year.read, enrollment.read, teacher_assignment.read |
| HOD | academic_year.read, enrollment.read, teacher_assignment.read |
| Teacher | academic_year.read, enrollment.read, teacher_assignment.read |
| Student | academic_year.read (own section only) |
| Parent | academic_year.read (child's section only) |

---

## 10. Tradeoffs

| Decision | Tradeoff |
|---|---|
| Year-specific entities (D15) | More records per year, but clean historical data |
| Separate entities (D2) | More tables, but academic fields fit naturally |
| Soft-close (D20) | More complex than hard-reject, but workable for Indian schools |
| Config-driven template (D7) | More setup than code-driven, but flexible per client |
| Clone from previous year (D16) | Preserves customizations, but first year needs template |
