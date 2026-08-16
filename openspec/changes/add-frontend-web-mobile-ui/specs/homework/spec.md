# Spec Delta — Homework (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** homework
> **Impact:** ADDED (net-new frontend Homework UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D6, R7), `docs/prd/frontend-web-mobile.md` (P3-AC-4..P3-AC-6)

---

## ADDED Requirements

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
