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
