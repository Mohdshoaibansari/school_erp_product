# homework Specification

## Purpose

Frontend (web + mobile UI) for the Homework business module: homework management, submissions and grading, and grade views. Derived from `docs/architecture/adr-frontend-implementation.md` (D6, R7) and `docs/prd/frontend-web-mobile.md` (P3-AC-4..P3-AC-6).

## Requirements

### REQ-FE-HW-01: Homework Management

The app SHALL provide a Homework screen where the Institution Admin can create (subject, section/scope, title, instructions, due date), list, edit, and close homework (P3-AC-4).

#### Scenario: Manage homework
- **WHEN** an Institution Admin works on the Homework screen
- **THEN** they can create, list, edit, and close homework

---

### REQ-FE-HW-02: Submissions and Grading

The app SHALL provide a Submissions view per homework where the Institution Admin can list submissions (per student), open a submission to view the submitted work, and grade a submission (P3-AC-5).

#### Scenario: View and grade submissions
- **WHEN** an Institution Admin opens a homework's submissions
- **THEN** they can list submissions, view submitted work, and grade a submission

---

### REQ-FE-HW-03: Grade Views

The app SHALL allow grades to be viewed per homework and per student, and updated where the API supports it (P3-AC-6).

#### Scenario: View and update grades
- **WHEN** an Institution Admin views grades
- **THEN** they can view grades per homework/per student and update them where the API supports it

---

### REQ-FE-HW-04: Management Roles Only as Author

The app SHALL expose homework authoring and grading to management roles only (Institution Admin in this build); teacher UI SHALL be deferred with the teacher role (R7).

#### Scenario: Management-role authoring only
- **WHEN** homework is authored or graded in this build
- **THEN** it is done by a management role (Institution Admin); teacher UI is not exposed

---
<!-- Synced from add-c02-identity-person-model-revamp delta spec -->
## Person-Model Revamp — Homework

### REQ-FE-HW-02-MOD: Submissions and Grading (Modified — student key shift)

Submissions are per-student. The student key SHALL shift from `app_user`-keyed to `student`-keyed (via `person`). Frontend behavior is unchanged (still lists per-student submissions), but the underlying student identity is `student.id` (linked to `person`), not `app_user.id`. Per AC-16.

> **Note:** The `student` table lands in the next capability (domain split). This revamp delivers `person` as the anchor; the actual `student`-keyed submission executes after the domain split.

#### Scenario: Submissions keyed by student entity (after domain split)
- **WHEN** an Institution Admin opens a homework's submissions
- **THEN** submissions SHALL be listed per `student.id` (linked to `person`)
- **AND** SHALL NOT use `app_user.id` as the submission student identity

### Cross-Cutting Notes (backend)

> **Gap:** There is no archived backend-homework OpenSpec spec. The `submission.student_id` FK repoint is an implementation/migration concern, not spec'd behavior.

- **`submission.student_id` FK** repoints `app_user.id` → `student.id` (via `person`). Setup in this revamp's migration; execution in the next capability.
