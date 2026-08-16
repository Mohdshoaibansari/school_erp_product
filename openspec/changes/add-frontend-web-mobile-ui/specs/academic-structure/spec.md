# Spec Delta — Academic Structure (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** academic-structure
> **Impact:** ADDED (net-new frontend C-05 UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D6), `docs/prd/frontend-web-mobile.md` (P2-AC-1..P2-AC-7)

---

## ADDED Requirements

### REQ-FE-AC-01: Create Academic Year

The app SHALL provide a Create Academic Year flow (name, start/end dates). The system SHALL build the structure by cloning the previous year (or from the configured template for the first year), and the app SHALL preview the generated structure (grade levels, classes, sections, terms) before confirming. On confirm, the year SHALL be created in "planning" status (P2-AC-1).

#### Scenario: Clone or template generation
- **WHEN** an Institution Admin creates an academic year
- **THEN** the app generates the structure by cloning the previous year (or from the template for the first year), previews it, and creates the year in "planning" status on confirm

---

### REQ-FE-AC-02: View and Navigate Structure

The app SHALL provide a structure view where the Institution Admin can navigate grade levels → classes → sections for a selected academic year (P2-AC-2).

#### Scenario: Navigate structure hierarchy
- **WHEN** an Institution Admin opens an academic year's structure
- **THEN** they can navigate grade levels → classes → sections

---

### REQ-FE-AC-03: Transition Academic Year Lifecycle

The app SHALL allow an Institution Admin to transition an academic year's lifecycle (planning → active → closed). Activating a year SHALL auto-close the previously active year, and closed years SHALL become read-only (P2-AC-3).

#### Scenario: Activate auto-closes previous
- **WHEN** an Institution Admin activates an academic year
- **THEN** the app transitions it to "active" and the previously active year is auto-closed

#### Scenario: Closed year read-only
- **WHEN** an academic year is closed
- **THEN** the app renders it read-only

---

### REQ-FE-AC-04: Subjects and Subject Groups

The app SHALL provide listing and management (create/edit/assign) of subjects and subject groups via the subjects/subject-groups endpoints (P2-AC-4).

#### Scenario: Manage subjects and subject groups
- **WHEN** an Institution Admin works with subjects and subject groups
- **THEN** they can list, create, edit, and assign them

---

### REQ-FE-AC-05: Teacher Assignments

The app SHALL allow an Institution Admin to create, list, and remove teacher assignments for a section (teacher → subject within a section) (P2-AC-5).

#### Scenario: Assign teacher to subject in section
- **WHEN** an Institution Admin works on a section's teacher assignments
- **THEN** they can create, list, and remove teacher-to-subject assignments

---

### REQ-FE-AC-06: Section Enrollments

The app SHALL allow an Institution Admin to create, list, and remove section enrollments (student → section), searching/selecting from the institution roster (P2-AC-6).

#### Scenario: Enroll and remove students
- **WHEN** an Institution Admin works on a section's enrollments
- **THEN** they can list enrolled students, enroll a student from the roster, and remove an enrollment

---

### REQ-FE-AC-07: No Direct CRUD for Structure Nodes

The app SHALL provide no direct CRUD UI for sections, grades, or terms. Structure changes SHALL go through clone/template generation only, matching the backend (P2-AC-7).

#### Scenario: Structure changed only via clone/template
- **WHEN** an Institution Admin needs to change the structure
- **THEN** the app guides them to clone/template flows and offers no free-form CRUD of sections/grades/terms
