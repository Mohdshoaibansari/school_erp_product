# Spec Delta — Fees (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** fees
> **Impact:** ADDED (net-new frontend Fees UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D6, R6), `docs/prd/frontend-web-mobile.md` (P3-AC-1..P3-AC-3)

---

## ADDED Requirements

### REQ-FE-FEE-01: Fee Type Management

The app SHALL provide a Fee Types screen where the Institution Admin can list, create, and edit fee types (name, amount basis, defaults) (P3-AC-1).

#### Scenario: Manage fee types
- **WHEN** an Institution Admin works on the Fee Types screen
- **THEN** they can list, create, and edit fee types

---

### REQ-FE-FEE-02: Fee Assignment Management

The app SHALL provide a Fee Assignments screen where the Institution Admin can create, edit, and remove fee assignments, including recording a fee waiver for a student (P3-AC-2).

#### Scenario: Assign, edit, remove, and waive fees
- **WHEN** an Institution Admin works on fee assignments
- **THEN** they can create, edit, remove assignments, and record a fee waiver

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
