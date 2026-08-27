# fees Specification

## Purpose

Frontend (web + mobile UI) for the Fees business module: fee types, fee assignments and waivers, payments, and cohort bulk assignment. Derived from `docs/architecture/adr-frontend-implementation.md` (D6, R6, R11) and `docs/prd/frontend-web-mobile.md` (P3-AC-1..P3-AC-3).

## Requirements

### REQ-FE-FEE-01: Fee Type Management

The app SHALL provide a Fee Types screen where the Institution Admin can list, create, and edit fee types (name, amount basis, defaults) (P3-AC-1).

#### Scenario: Manage fee types
- **WHEN** an Institution Admin works on the Fee Types screen
- **THEN** they can list, create, and edit fee types

---

### REQ-FE-FEE-02: Fee Assignment Management

The app SHALL provide a Fee Assignments screen where the Institution Admin can create, edit, and waive fee assignments. Remove is DEFERRED — the backend fee-assignments router has no DELETE endpoint (P3-AC-2, ADR R11).

#### Scenario: Assign, edit, and waive fees
- **WHEN** an Institution Admin works on fee assignments
- **THEN** they can create, edit, and waive assignments (remove deferred)

---

### REQ-FE-FEE-03: Payments

The app SHALL allow the Institution Admin to record a payment against a fee assignment and view payments filterable by student, fee, date, and status (P3-AC-3).

#### Scenario: Record and view payments
- **WHEN** an Institution Admin works on payments
- **THEN** they can record a payment against a fee assignment and view payments filtered by student, fee, date, and status

---

### REQ-FE-FEE-04: Cohort Bulk + Per-Student Assignment

The app SHALL support fee assignment at cohort level (section/grade) in one action, with per-student overrides. This SHALL depend on the Fees backend supporting cohort-level targets (R6).

#### Scenario: Cohort bulk assignment
- **WHEN** the Fees backend supports cohort-level targets
- **THEN** the app lets an Institution Admin assign a fee to a section/grade in one action with per-student overrides

#### Scenario: Dependency flagged
- **WHEN** the Fees backend does not yet support cohort-level targets
- **THEN** Phase 3 fee assignment is blocked pending the separate Fees backend change (R6)

---
<!-- Synced from add-c02-identity-person-model-revamp delta spec -->
## Person-Model Revamp — Fees

### REQ-FE-FEE-02-MOD: Fee Assignment Management (Modified — student key shift)

Fee assignments target a student. The student reference SHALL shift from `app_user`-keyed to `student`-keyed (via `person`). Frontend behavior is largely unchanged (the admin still picks from a roster), but the underlying student identity is `student.id` (linked to `person`), not `app_user.id`. The `user_category='Learner'` proxy check SHALL be dropped — student status is derived from the `student` domain entity (next capability) or `role_assignment`, never from `user_category`. Per AC-14, AC-16.

> **Note:** The `student` table lands in the next capability (domain split). This revamp delivers `person` as the anchor and drops the `Learner` proxy; the actual `student`-keyed fee assignment executes after the domain split.

#### Scenario: Fee assignment targets student entity (after domain split)
- **WHEN** an Institution Admin creates a fee assignment
- **THEN** the assignment SHALL target a `student.id` (linked to `person`)
- **AND** SHALL NOT reference `app_user.id` as the student identity

#### Scenario: No Learner proxy check
- **WHEN** the fees module determines whether a user is a student for fee assignment
- **THEN** it SHALL NOT check `user_category = 'Learner'`
- **AND** student status SHALL be derived from the `student` domain entity or `role_assignment`

### REQ-FE-FEE-03-MOD: Payments (Modified — student filter key shift)

Payments SHALL be filterable by student. The student filter key SHALL shift to `student`-keyed (via `person`). Frontend behavior is unchanged (still filters by student from a roster), but the underlying identity changes. Per AC-16.

#### Scenario: Payment filter by student entity
- **WHEN** an Institution Admin filters payments by student
- **THEN** the filter SHALL use the `student` identity (via `person`)
- **AND** SHALL NOT use `app_user.id` as the student filter key

### Cross-Cutting Notes (backend)

> **Gap:** There is no archived backend-fees OpenSpec spec. The `fee_assignment.student_id` FK repoint and the `user_category='Learner'` proxy drop are implementation/migration concerns, not spec'd behavior.

- **`fee_assignment.student_id` FK** repoints `app_user.id` → `student.id` (via `person`). Setup in this revamp's migration; execution in the next capability.
- **Drops `user_category='Learner'` proxy check** (AC-14, D6a).
