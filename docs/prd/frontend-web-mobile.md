# PRD — Frontend (Web + Mobile UI)

> **Capability:** Frontend (Web + Mobile UI)
> **Status:** Draft — PRD phase of the sdd-stack flow (input to impact classification → proposal → spec → design → tasks)
> **Last updated:** 2026-08-16
> **Decisional source of truth:** `docs/architecture/adr-frontend-implementation.md` (D1–D7)
> **Scope note:** This is a **product** requirements document. The UI will serve the **already-built** backend modules only. Implementation detail (framework, component wiring, API DTOs) belongs in the spec/design phase. Decisions are referenced by ID (e.g., "per D1").

---

## 1. Problem

The backend is API-first and has already built and archived its first wave of capabilities — C-01 Tenant & Institution Management, C-02 Identity & User Management, C-03 Authentication, C-04 Authorization, C-05 Academic Structure, C-08 Configuration Framework, plus the Fees and Homework business modules. **None of them has a production UI.**

Two throwaway frontends exist today, and neither is usable:

1. **The repo demo UI** (`frontend/`) is an explicitly-labeled "Test UI." It covers only Login, Platform (Clients/Institutions/Users), Fees, and Homework; it has no academic-structure, roles/permissions, or config screens, and it was never meant to ship.
2. **The Figma Make export** is a visually polished design system and app shell, but its real screens (Dashboard, Students, Attendance) target operational modules that have **no backend yet**, while the actually-built admin/config modules have almost no screens in it.

The result: the platform's management work — creating tenants, onboarding institutions, provisioning users, granting roles, building the academic year, configuring the system, and running fees and homework — can only be done against raw APIs. There is no product surface for the three management roles the platform actually serves today.

This PRD defines the first UI-bearing build: a responsive web + PWA frontend (single codebase, desktop and mobile browsers) that exposes the **built modules only**, in three sequenced phases, with the Figma used strictly as the design-system and app-shell reference (D1, D2, D6).

---

## 2. Goals and Non-goals

### 2.1 Goals

| # | Goal |
|---|---|
| G1 | Provide a single responsive web + installable PWA surface that works in desktop and mobile browsers (D2). |
| G2 | Cover the built backend modules end-to-end: tenant/institution (C-01), users (C-02), auth (C-03), roles/permissions (C-04), academic structure (C-05), config (C-08), Fees, Homework (D1). |
| G3 | Serve the three management roles — Platform Owner, Client Director, Institution Admin — with navigation and actions gated by JWT roles (D5). |
| G4 | Visually match the Figma design system: primary `#2563EB`, Inter body / DM Sans headings, semantic colors, card/table/status-pill patterns (D4). |
| G5 | Deliver in three reviewable phases by domain, matching the repo's capability-at-a-time discipline (D6). |
| G6 | Replace the demo `frontend/` completely, keeping only the reusable app-shell base (D7). |

### 2.2 Non-goals (explicit)

| # | Non-goal |
|---|---|
| N1 | No native mobile app or separate mobile codebase (D2). |
| N2 | No operational screens — Dashboard, Students, Attendance, Timetable, Exams, Report Cards (those modules have no backend) (D1). |
| N3 | No non-management roles — Teacher, Student, Parent — until their operational backend exists (D5). |
| N4 | No new design system or design invention; the UI matches the Figma (D4). |
| N5 | No frontend-side authorization enforcement — the UI hides/shows by JWT role but never enforces access; the backend (Casbin RBAC+ABAC) remains authoritative and blocked actions render a friendly 403. |
| N6 | No new backend endpoints or backend behavior changes as part of this capability; this is UI-only against the existing API surface. |
| N7 | No offline data editing or background sync in this build (PWA caching depth is deferred). |

### 2.3 Scope boundary (which screens are in/out)

**In scope (built modules have APIs):** auth (login/OTP/password/activate/logout), clients, institution types, ownership transfers, institutions, org units, client users, users, profiles, roles/identifiers assignment, academic years + structure, teacher assignments, section enrollments, subjects, subject groups, config keys/values/audit/resolve, fee types, fee assignments, payments, homework, submissions, grades.

**Out of scope:** anything requiring an unbuilt backend module (e.g., student/attendance operational screens), any screen the Figma shows but the API surface does not support.

---

## 3. Users / Personas

The frontend serves **management roles only** (D5). All navigation and actions are role-gated from the JWT `roles` claim; the backend remains authoritative.

### 3.1 Platform Owner

- Operates at the **platform** level (multi-client).
- Creates and manages **clients** (tenants) and their lifecycle transitions.
- Manages **institution types** (shared platform catalog).
- Handles **ownership transfers** of institutions/clients.
- Manages **client users** on behalf of a client.
- Can see across all clients and institutions; never works inside a single institution's day-to-day operations.

### 3.2 Client Director

- Operates at the **client** level (one client, possibly multiple institutions).
- Creates and manages **institutions** under their client, including lifecycle transitions and **go-live**.
- Manages the client's **org units** (subtree, move, archive/reactivate, reorder).
- Manages **users** for their client's institutions and assigns roles.
- Cannot see or act outside their own client.

### 3.3 Institution Admin (primary day-to-day actor)

- Operates at the **institution** level (one institution).
- Manages users and their profiles, identifiers, and role assignments within the institution.
- Builds and manages the **academic structure** (academic years, subjects, subject groups, teacher assignments, section enrollments).
- Manages **configuration** keys and values for the institution.
- Manages **fees** (fee types, assignments, payments) and **homework** (homeworks, submissions, grading).
- Cannot act outside their institution.

> **Note on roles/permissions UI (C-04):** no C-04 routes are consumed by this frontend. UI gating is **role-based from the JWT `roles` claim**. The Roles & Permissions management screen is **out of scope** (deferred until authz routes exist).

---

## 4. User Journeys

Journeys are grouped by role and phase. Phases (D6):
- **Phase 1** — app shell + auth + tenant/institution (C-01) + users & roles (C-02/C-04)
- **Phase 2** — academic structure (C-05) + config (C-08)
- **Phase 3** — fees + homework

### 4.0 Cross-cutting app-shell journeys (all roles, all phases)

**App shell & navigation**
```
Any user opens the app → app shell loads (sidebar/header, role-filtered nav)
  → nav shows only the modules the user's JWT roles allow
  → on narrow screens, nav collapses into an off-canvas drawer
  → the app carries the current client/institution context everywhere (tenant scoping)
```

**Institution/client switcher**
```
A multi-scope user (Platform Owner or Client Director) sees a context switcher
  → selects a client (Platform Owner) or institution (Client Director)
  → all subsequent screens and requests are scoped to that selection
  → Institution Admin has a fixed institution context (no switcher needed)
```

**Session & access control**
```
User hits a protected route without a valid session → redirected to login
  → token refresh happens silently while the session is active
  → if refresh fails (401), the user is returned to login
  → actions the user's role doesn't allow are hidden (nav items, buttons); the backend still enforces on every request, and a blocked action shows a friendly permission-denied message
```

### 4.1 Phase 1 — Authentication, Tenant/Institution, Users & Roles

#### Auth (all roles)

**Login**
```
User opens the app → login screen
  → enters email + password
  → on success: JWT issued, app shell loads with the user's role-filtered nav
  → on failure: inline error, no route change
```

**Account activation**
```
User receives an activation invite/link
  → lands on activation screen
  → confirms their account (sets/confirms credentials as required)
  → activated → redirected to login (or straight into the app per policy)
```

**OTP flow**
```
User triggers an OTP-protected action (per policy: activation, password reset, or login step-up)
  → requests an OTP → receives it out-of-band
  → enters OTP → verifies → proceeds to the protected action
  → wrong/expired OTP → inline error, re-request allowed
```

**Password reset**
```
User on login screen → "Forgot password"
  → requests a reset → receives a reset link/code
  → opens reset → sets a new password → confirms
  → redirected to login with a success state
```

**Password change (logged in)**
```
Logged-in user → profile/settings → "Change password"
  → enters current + new password → confirms
  → on success: confirmation; session remains valid (or re-auth per policy)
```

**Logout**
```
Logged-in user → "Log out"
  → session terminated → returned to login
```

#### Platform Owner — tenant management (C-01)

**Manage clients**
```
Platform Owner → Clients list (searchable/filterable)
  → view client details
  → create a new client (name, legal-entity type, contact, status)
  → edit client details
  → transition client lifecycle (state changes e.g. pending → active → suspended/closed)
  → view client's institutions and users
```

**Manage institution types**
```
Platform Owner → Institution Types (catalog)
  → list all institution types
  → create / edit / deactivate a type
  → (types are referenced when clients/institutions are created)
```

**Ownership transfer**
```
Platform Owner → Ownership Transfers
  → initiate a transfer (move an institution/client between owners)
  → review and complete the transfer
  → audit: the transfer is reflected in the affected tenant's ownership
```

**Manage client users**
```
Platform Owner → a client → Users
  → list the client's users
  → create a user under that client
  → edit / transition a client user
```

#### Client Director — tenant management (C-01)

**Manage institutions**
```
Client Director → Institutions list (their client's institutions)
  → create an institution (name, type, address, contact, academic context)
  → edit institution details
  → transition institution lifecycle (draft → active, etc.)
  → trigger go-live (move institution to operational status)
```

**Manage org units**
```
Client Director → an institution → Org Units
  → view the org-unit tree (subtree navigation)
  → create / edit org units
  → move an org unit within the tree
  → reorder siblings
  → archive / reactivate org units
```

#### Users & roles (C-02 / C-04) — Client Director and Institution Admin

**Manage users**
```
Director or Admin → Users list (scoped to their client/institution)
  → create a user (category, identifiers, contact)
  → edit user details
  → transition user status (activate/suspend/deactivate)
  → open a user's profile
```

**Manage profile & identifiers**
```
Open a user → profile
  → edit profile fields
  → manage identifiers (add / edit / remove)
```

**Assign roles**
```
Open a user → roles
  → view current roles
  → assign / remove roles (from the available role catalog)
```

**Lookups (reference data)**
```
Users form → dropdowns for user-category, role, institution-type, org-unit-type, legal-entity-type
  → values sourced from the lookups API (single source of truth for reference data)
```

**Roles & permissions (out of scope)**
```
No Roles & Permissions screen in this build — C-04 exposes no HTTP routes.
Navigation/actions are role-gated from the JWT; the backend enforces Casbin.
A blocked action shows a friendly 'permission denied' message.
```

### 4.2 Phase 2 — Academic Structure & Configuration

#### Academic structure (C-05) — Institution Admin

**Create academic year**
```
Institution Admin → Academic Structure → Academic Years
  → "Create academic year" (name, start/end dates)
  → system builds the structure by cloning the previous year (or from the configured template for the first year)
  → preview the generated structure (grade levels, classes, sections, terms)
  → confirm → year created in "planning" status
```

**Manage structure**
```
Admin opens an academic year → structure view
  → navigate grade levels → classes → sections
  → edit the structure via the supported operations (clone-from-year / template generation);
      no free-form CRUD of sections/grades/terms (backend does not expose it)
  → manage subjects and subject groups (create/edit/assign)
```

**Transition academic year**
```
Admin → Academic Years → select a year
  → transition lifecycle (planning → active → closed)
  → activating a year auto-closes the previously active year
  → closed years become read-only
```

**Teacher assignments**
```
Admin → a section → Teacher Assignments
  → assign a teacher to a subject within a section
  → view current assignments
  → remove an assignment
```

**Section enrollments**
```
Admin → a section → Enrollments
  → view enrolled students
  → enroll a student (search/select from institution roster)
  → remove an enrollment
```

#### Configuration (C-08) — Institution Admin

**Manage config keys & values**
```
Admin → Configuration
  → browse config keys (scoped to the institution)
  → view / edit config values (per key, with type-aware input)
  → view resolved values for a key (effective value accounting for fallbacks)
  → view config audit trail (who changed what, when)
```

### 4.3 Phase 3 — Fees & Homework

#### Fees — Institution Admin

**Manage fee types**
```
Admin → Fees → Fee Types
  → create / edit fee types (name, amount basis, defaults)
```

**Manage fee assignments**
```
Admin → Fees → Assignments
  → assign a fee type to a student/cohort (e.g., per section or grade)
  → edit / remove assignments
  → waive a fee for a student (record the waiver)
```

**Record payments**
```
Admin → Fees → Payments
  → record a payment against a fee assignment
  → view payments (filter by student, fee, date, status)
```

#### Homework — Institution Admin (and later teacher roles)

**Manage homework**
```
Admin → Homework
  → create homework (subject, section/scope, title, instructions, due date)
  → view homework list
  → edit homework
  → close homework (stop accepting submissions)
```

**Submissions & grading**
```
Admin → a homework → Submissions
  → view submissions (per student)
  → open a submission (view submitted work)
  → grade a submission
  → view grades (per homework / per student)
```

---

## 5. Acceptance Criteria

### 5.1 Phase 1 acceptance criteria

#### App shell & session

| # | Criterion |
|---|---|
| P1-AC-1 | The app renders a responsive shell with role-filtered navigation; nav items appear only if the user's JWT roles allow them. |
| P1-AC-2 | On viewport widths below 1024px, primary navigation is reachable via an off-canvas drawer; on desktop it is a persistent sidebar. |
| P1-AC-3 | Multi-scope users (Platform Owner, Client Director) can switch client/institution context, and every subsequent request is tenant-scoped to that selection. |
| P1-AC-4 | Accessing a protected route without a valid session redirects to login; a failed token refresh (401) also returns the user to login. |
| P1-AC-5 | The UI hides actions the user's role is not permitted to perform, and the backend independently rejects any direct/forged attempt (frontend never enforces access); a blocked action renders a friendly permission-denied message, never a raw error. |

#### Auth (C-03)

| # | Criterion |
|---|---|
| P1-AC-6 | A user can log in with email + password; success loads the shell, failure shows an inline error. |
| P1-AC-7 | A user can complete account activation and reach an authenticated or login state afterward. |
| P1-AC-8 | A user can request and verify an OTP for OTP-protected flows, with re-request and error states. |
| P1-AC-9 | A user can request a password reset and complete it by setting a new password. |
| P1-AC-10 | A logged-in user can change their password with current + new password confirmation. |
| P1-AC-11 | A user can log out and is returned to the login screen with the session terminated. |
| P1-AC-12 | All auth screens are responsive and match the Figma design system (primary `#2563EB`, Inter/DM Sans, semantic colors). |

#### Tenant/institution — Platform (C-01)

| # | Criterion |
|---|---|
| P1-AC-13 | Platform Owner can list, create, edit, and transition clients (lifecycle state changes) via the Clients screen. |
| P1-AC-14 | Platform Owner can manage institution types (list/create/edit/deactivate) via the Institution Types screen. |
| P1-AC-15 | Platform Owner can initiate and complete an ownership transfer, and the transfer is reflected on the affected tenant. |
| P1-AC-16 | Platform Owner can list, create, edit, and transition client users via `/api/v1/platform/clients/{client_id}/users`. |

#### Tenant/institution — Client portal (C-01)

| # | Criterion |
|---|---|
| P1-AC-17 | Client Director can list, create, edit, transition, and go-live institutions under their client. |
| P1-AC-18 | Client Director can view the org-unit subtree, create/edit org units, move them, reorder siblings, and archive/reactivate them. |

#### Users & roles (C-02 / C-04)

| # | Criterion |
|---|---|
| P1-AC-19 | Director/Admin can list, create, edit, and transition users scoped to their client/institution. |
| P1-AC-20 | A user's profile can be viewed and edited (CRUD on profile fields). |
| P1-AC-21 | A user's identifiers can be listed, created, edited, and removed. |
| P1-AC-22 | Roles can be assigned to and removed from a user from the available role catalog. |
| P1-AC-23 | Reference dropdowns (user-category, role, institution-type, org-unit-type, legal-entity-type) are populated from the lookups API. |
| P1-AC-24 | There is **no** Roles & Permissions screen in this build (C-04 exposes no routes); role-based gating is derived from the JWT `roles` claim. |

### 5.2 Phase 2 acceptance criteria

#### Academic structure (C-05)

| # | Criterion |
|---|---|
| P2-AC-1 | Institution Admin can create an academic year (name, start/end dates); the structure is generated by clone-from-previous-year or template, and the year is created in "planning" status. |
| P2-AC-2 | Institution Admin can view the generated structure and navigate grade levels → classes → sections. |
| P2-AC-3 | Institution Admin can transition academic-year lifecycle (planning → active → closed); activating a year auto-closes the previously active year, and closed years become read-only. |
| P2-AC-4 | Subjects and subject groups can be listed and managed (create/edit/assign) via the subjects/subject-groups endpoints. |
| P2-AC-5 | Teacher assignments can be created, listed, and removed for a section (teacher → subject within a section). |
| P2-AC-6 | Section enrollments can be created, listed, and removed (student → section). |
| P2-AC-7 | The UI provides **no direct CRUD** for sections/grades/terms — structure changes go through clone/template generation only (matching the backend). |

#### Configuration (C-08)

| # | Criterion |
|---|---|
| P2-AC-8 | Institution Admin can browse config keys scoped to the institution and view/edit config values. |
| P2-AC-9 | Institution Admin can view the resolved (effective) value for a key, accounting for fallbacks. |
| P2-AC-10 | Institution Admin can view the config audit trail (who changed what, when). |

### 5.3 Phase 3 acceptance criteria

#### Fees

| # | Criterion |
|---|---|
| P3-AC-1 | Institution Admin can list, create, and edit fee types. |
| P3-AC-2 | Institution Admin can create, edit, and remove fee assignments, including recording a fee waiver. |
| P3-AC-3 | Institution Admin can record a payment and view payments (filterable by student, fee, date, status). |

#### Homework

| # | Criterion |
|---|---|
| P3-AC-4 | Institution Admin can create, list, edit, and close homework. |
| P3-AC-5 | Submissions can be listed and opened (view submitted work), and a submission can be graded. |
| P3-AC-6 | Grades can be viewed per homework/per student and updated where the API supports it. |

### 5.4 Cross-cutting acceptance criteria (all phases)

| # | Criterion |
|---|---|
| CC-AC-1 | The UI visually matches the Figma design system (primary `#2563EB`, Inter body / DM Sans headings, semantic colors, radii, card/table/status-pill patterns) — no new design invention. |
| CC-AC-2 | The app is installable as a PWA and usable in desktop and mobile browsers from a single codebase. |
| CC-AC-3 | Data tables remain usable on narrow screens (collapse or horizontal scroll) without losing required columns/actions. |
| CC-AC-4 | All tenant-scoped data views reflect the active client/institution context; there is no cross-tenant data leakage in the UI. |
| CC-AC-5 | All API responses map to typed DTOs in the UI API layer (no untyped data handling). |

---

## 6. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Figma screens imply modules that don't exist yet** — the export's operational screens (Dashboard, Students, Attendance) could pull scope toward unbuilt backend. | Medium | High | Figma is design-system/app-shell reference only (D1); screen inventory is strictly the built-module API surface. |
| R2 | **Responsive tables are hard on phones** — admin/config screens are table-heavy; collapsing them can hide critical columns or break workflows. | High | Medium | Per-table collapse/scroll strategy; acceptance criterion CC-AC-3; verify on narrow viewports per phase. |
| R3 | **Roles/permissions UI gap (C-04)** — there is no Roles & Permissions screen because C-04 exposes no routes; users cannot manage roles/permissions from the UI. | High | Medium | Explicitly out of scope (P1-AC-24); role-gated nav from the JWT covers day-to-day needs; deferred until authz routes exist. |
| R4 | **Frontend/backend gating drift** — a role-based UI rule can diverge from a backend Casbin/ABAC decision, causing visible-but-blocked actions (or hidden-but-valid ones). | Medium | Medium | Backend-authoritative rule; the UI gates by role only and never enforces; any blocked action renders a friendly 403; verification checks shown actions are backend-allowed per role fixture. |
| R5 | **Tenant-scoping bugs** — a request carrying the wrong client/institution context leaks or mis-scopes data. | Medium | High | Single context provider + institution switcher as the only source of tenant context; per-request scoping verified against a two-tenant fixture. |
| R6 | **Figma-fidelity cost** — matching the design system closely (cards, tables, status pills) requires up-front theme/pattern work that delays first screens. | High | Low | Build the themed app shell + core component patterns first in Phase 1; reuse across all later phases. |
| R7 | **Academic-structure UI overreach** — users expect to add/remove sections/terms directly, but the backend only supports clone/template generation. | Medium | Medium | Enforce P2-AC-7 (no direct CRUD UI); guide users to clone/template flows with clear copy. |
| R8 | **PWA expectations** — "web + mobile" may be read as offline-capable; offline data editing is out of scope. | Low | Low | Scope PWA to installable + responsive now; offline caching/background sync explicitly deferred (N7). |

---

## 7. Open Questions

> **Resolved 2026-08-16** — all seven questions are decided (R1–R7 in `adr-frontend-implementation.md` §2.1). The table below records the final resolutions.

| # | Question | Context / notes | Resolution (final) |
|---|---|---|---|
| Q1 | **Roles & permissions surface** — should the permission catalog + role→permission mapping render read-only now, or be fully hidden until authz CRUD routes exist? | C-04 has no CRUD routes; shipping read-only avoids a dead-end screen but may feel incomplete. | **Resolved:** Role-based JWT gating; no Roles & Permissions screen (R1). |
| Q2 | **OTP use cases** — is OTP only for activation/password-reset, or also a login step-up (2FA) flow? | Affects which screens expose the OTP request/verify flow. | **Resolved:** Activation + password-reset only (R2). |
| Q3 | **Activation landing** — after activation, should the user land on login or be dropped straight into an authenticated session? | Product UX decision; both are supported by the activation endpoint. | **Resolved:** Land on login (R3). |
| Q4 | **Institution switcher default** — for a Client Director with multiple institutions, which institution is selected on first load (most-recent, first, or none-until-chosen)? | Affects first-screen state and tenant scoping on load. | **Resolved:** Last-used with fallback to first (R4). |
| Q5 | **Config key editability** — which config keys are user-editable vs read-only/system-managed in the C-08 UI? | Some keys are system-seeded and shouldn't be edited through the UI. | **Resolved:** All keys editable; backend validates (R5). |
| Q6 | **Fee assignment target** — what is the assignment unit for fees (per-student, per-section, per-grade)? | Determines the Fees→Assignments screen shape. | **Resolved:** Cohort bulk + per-student; may need a Fees backend change (R6). |
| Q7 | **Homework author** — is Institution Admin the only homework author in this build, or do we expose homework to teacher roles (out of scope per D5)? | D5 limits to management roles, but homework is teacher-adjacent. | **Resolved:** Management roles only (R7). |

---

## 8. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| C-01 Tenant & Institution backend | Hard | Phase 1 screens consume its routes. |
| C-02 Identity & User backend | Hard | Phase 1 users/profile/identifiers/roles screens. |
| C-03 Auth backend | Hard | Phase 1 auth flows. |
| C-04 Authorization backend | Indirect | Not consumed by the UI (no routes); the backend enforces Casbin RBAC+ABAC and returns 403, which the UI renders as a friendly message. |
| C-05 Academic Structure backend | Hard | Phase 2 academic screens. |
| C-08 Config backend | Hard | Phase 2 config screens. |
| Fees backend | Hard | Phase 3 fees screens. |
| Homework backend | Hard | Phase 3 homework screens. |
| Figma design system | Hard | Design tokens + component patterns (D4). |

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| Built-module coverage | 100% of the in-scope API surface has a reachable UI screen. |
| Role coverage | All three management roles can complete their core journeys without API access. |
| Responsive usability | No in-scope screen is unusable at a 360px viewport width (collapse/scroll applied). |
| Design fidelity | Primary/semantic colors and typography match Figma tokens across all screens. |
| Role-gating correctness | Shown actions are allowed for the user's role and hidden actions are not shown (verified per role fixture); any backend-blocked action renders a friendly 403. |
| Tenant isolation | No cross-tenant/cross-institution data appears under a mismatched context in verification fixtures. |
