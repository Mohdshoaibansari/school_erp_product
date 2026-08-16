# Spec Delta — Identity & User Management (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** identity-user-management
> **Impact:** ADDED (net-new frontend C-02 UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D5, R1), `docs/prd/frontend-web-mobile.md` (P1-AC-19..P1-AC-24)

---

## ADDED Requirements

### REQ-FE-USR-01: Users List/Create/Edit/Transition

The app SHALL provide a Users screen (scoped to the user's client/institution) where the Client Director or Institution Admin can list, create (category, identifiers, contact), edit, and transition the status (activate/suspend/deactivate) of users, and open a user's profile (P1-AC-19).

#### Scenario: Manage users scoped to tenant
- **WHEN** a Client Director or Institution Admin acts on the Users screen
- **THEN** they can list, create, edit, and transition users within their client/institution scope, and open a user's profile

---

### REQ-FE-USR-02: Profile View and Edit

The app SHALL provide a user profile view where profile fields can be edited (CRUD on profile fields) (P1-AC-20).

#### Scenario: Edit profile fields
- **WHEN** a user opens another user's profile
- **THEN** they can view and edit the profile fields

---

### REQ-FE-USR-03: Identifier Management

The app SHALL provide identifier management on a user's profile: list, create, edit, and remove identifiers (P1-AC-21).

#### Scenario: Manage identifiers
- **WHEN** a user opens a profile's identifiers
- **THEN** they can list, create, edit, and remove identifiers

---

### REQ-FE-USR-04: Role Assignment

The app SHALL provide a roles view on a user's profile where roles can be viewed, assigned, and removed from the available role catalog (P1-AC-22).

#### Scenario: Assign and remove roles
- **WHEN** a user opens a profile's roles
- **THEN** they can view current roles and assign/remove roles from the available role catalog

---

### REQ-FE-USR-05: Lookups-Driven Reference Dropdowns

Reference dropdowns on user forms (user-category, role, institution-type, org-unit-type, legal-entity-type) SHALL be populated from the lookups API as the single source of truth for reference data (P1-AC-23).

#### Scenario: Dropdowns sourced from lookups API
- **WHEN** a user form renders a reference dropdown
- **THEN** its values are populated from the lookups API

---

### REQ-FE-USR-06: No Roles & Permissions Screen

The app SHALL NOT provide a Roles & Permissions screen in this build because C-04 exposes no HTTP routes. Role-based gating is derived from the JWT `roles` claim, and the backend enforces Casbin (P1-AC-24, R1).

#### Scenario: No roles/permissions management screen
- **WHEN** a user inspects available navigation
- **THEN** there is no Roles & Permissions screen; navigation and actions are role-gated from the JWT `roles` claim
