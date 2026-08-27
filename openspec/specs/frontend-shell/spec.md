# frontend-shell Specification

## Purpose

Frontend (web + mobile UI) application shell: responsive + installable PWA, Minimalist Modern Mantine theme, role-filtered navigation across all 10 backend roles, context switcher, session/access control, typed API layer, and friendly 403. Derived from `docs/architecture/adr-frontend-implementation.md` (D1–D9, R1, R4, R8) and `docs/prd/frontend-web-mobile.md` (P1-AC-1..P1-AC-5, CC-AC-1..CC-AC-5).

## Requirements

### REQ-SHELL-01: Single Responsive Web + PWA Codebase

The frontend SHALL be delivered as a single responsive web application that is installable as a Progressive Web App (PWA) and usable in both desktop and mobile browsers from one codebase. It SHALL NOT introduce a separate native mobile codebase (D2, N1). PWA scope is installable + responsive only; offline data editing and background sync are explicitly deferred (N7, R8).

#### Scenario: Installable on desktop and mobile
- **WHEN** a user opens the app in a desktop or mobile browser
- **THEN** the app renders from the same codebase and offers PWA install affordances without a native app

#### Scenario: No offline data editing
- **WHEN** a user attempts offline data editing or background sync in this build
- **THEN** the app does not provide those features (deferred to a future capability)

---

### REQ-SHELL-02: Mantine Theme Uses the Minimalist Modern Design System

The UI SHALL be built with Mantine restyled via a single theme override using the "Minimalist Modern" design system (D9, amends D4). Tokens SHALL match: primary `#0052FF` (blue palette `#EEF4FF`→`#002D91`); app background `#FAFAFA`; surface `#FFFFFF`; muted `#F1F5F9`; text primary `#0F172A` / secondary `#64748B` / muted `#94A3B8`; border `#E2E8F0`; semantic success `#16A34A`, warning `#D97706`, danger `#DC2626`; typography Inter (body) + Calistoga (headings, Georgia fallback) + JetBrains Mono (labels); radii `8 / 12 / 16 / 20`; and the card, table, and status-pill patterns.

#### Scenario: Primary color and typography match the shipped tokens
- **WHEN** any screen renders
- **THEN** the primary color is `#0052FF` and body text uses Inter while headings use Calistoga

#### Scenario: No further design invention
- **WHEN** a screen or component is built
- **THEN** it reuses the Minimalist Modern Mantine theme and component patterns rather than introducing new visual patterns

---

### REQ-SHELL-03: Role-Filtered Navigation from JWT Roles

The app shell SHALL render role-filtered navigation derived from the JWT `roles` claim, across all 10 backend roles (D8). A nav item SHALL appear only if the user's JWT roles — mapped to their real Casbin `role_permission` grants — allow that module. No C-04 authorization routes are consumed; gating is role-based from the JWT only (D5/D8, P1-AC-1, R1).

#### Scenario: Nav shows only role-allowed modules
- **WHEN** a user loads the app shell
- **THEN** navigation shows only the modules permitted by the user's JWT `roles` claim

#### Scenario: No Roles & Permissions screen
- **WHEN** a user inspects available navigation
- **THEN** there is no Roles & Permissions screen because C-04 exposes no routes (R1, P1-AC-24)

---

### REQ-SHELL-04: Responsive App Shell with Off-Canvas Drawer

The app shell SHALL render a persistent sidebar on viewport widths ≥ 1024px and collapse primary navigation into an off-canvas drawer on viewport widths below 1024px (P1-AC-2).

#### Scenario: Desktop sidebar
- **WHEN** the viewport width is ≥ 1024px
- **THEN** primary navigation is rendered as a persistent sidebar

#### Scenario: Mobile off-canvas drawer
- **WHEN** the viewport width is below 1024px
- **THEN** primary navigation is reachable via an off-canvas drawer

---

### REQ-SHELL-05: Client/Institution Context Switcher

Multi-scope users (Platform Owner, Client Director) SHALL be able to switch their active client (Platform Owner) or institution (Client Director) context via a context switcher, and every subsequent request SHALL be scoped to that selection. On first load, the switcher SHALL default to the last-used institution (persisted), falling back to the first institution when none is remembered (R4). Institution Admin SHALL have a fixed institution context with no switcher (P1-AC-3).

#### Scenario: Client Director switches institution
- **WHEN** a Client Director selects an institution in the switcher
- **THEN** all subsequent screens and requests are scoped to that institution, and the selection persists as last-used

#### Scenario: Last-used fallback
- **WHEN** a Client Director has no remembered institution
- **THEN** the switcher defaults to the first institution in their client

#### Scenario: Institution Admin has fixed context
- **WHEN** an Institution Admin loads the app
- **THEN** their institution context is fixed and no switcher is shown

---

### REQ-SHELL-06: Session and Access Control

The app SHALL redirect to login when a protected route is accessed without a valid session. While a session is active, token refresh SHALL happen silently; if refresh fails with a 401, the user SHALL be returned to login (P1-AC-4).

#### Scenario: Protected route without session
- **WHEN** a user accesses a protected route without a valid session
- **THEN** the app redirects to the login screen

#### Scenario: Failed silent refresh
- **WHEN** a silent token refresh returns 401
- **THEN** the app returns the user to the login screen

---

### REQ-SHELL-07: Backend-Authoritative Authorization with Friendly 403

The frontend SHALL hide or show navigation and actions by JWT role only and SHALL NEVER enforce access itself. The backend (Casbin RBAC+ABAC) remains authoritative on every request. When the backend blocks an action the role-based UI allowed (e.g., a future ABAC scope), the app SHALL render a friendly permission-denied message, never a raw error (N5, D5, R8, P1-AC-5).

#### Scenario: Backend blocks an action
- **WHEN** the backend rejects a UI-initiated action with 403
- **THEN** the app renders a friendly permission-denied message rather than a raw error or stack trace

#### Scenario: Frontend never enforces
- **WHEN** a user forges or directly invokes an action their role is not permitted to perform
- **THEN** the backend independently rejects it, regardless of any UI hiding

---

### REQ-SHELL-08: Tenant Context Everywhere

The UI SHALL carry `client_id`/`institution_id` from the JWT plus the context switcher as the single source of tenant context, and every request SHALL be tenant-scoped to that context. There SHALL be no cross-tenant or cross-institution data leakage in the UI (D5 constraint 5, CC-AC-4).

#### Scenario: Requests carry active context
- **WHEN** a request is made
- **THEN** it is scoped to the active client/institution context from the context provider

#### Scenario: No cross-tenant leakage
- **WHEN** a user operates under a mismatched context in verification fixtures
- **THEN** no data from another client or institution appears

---

### REQ-SHELL-09: Typed DTO API Layer

All API responses SHALL map to typed DTOs in the UI API layer (mirroring backend DTOs). The use of `any` SHALL be disallowed in the API layer (D5 constraint 4, CC-AC-5).

#### Scenario: Responses are typed
- **WHEN** the API layer receives a response
- **THEN** it is mapped to a typed DTO, and untyped `any` handling is disallowed

---

### REQ-SHELL-10: All 10 Backend Roles with Permission-Accurate Gating

The frontend SHALL serve all 10 backend roles — `platform_owner`, `client_director`, `institution_admin`, `admin`, `teacher`, `hod`, `principal`, `student`, `parent`, `staff` — derived from the JWT roles array (case-insensitively normalized) with `user_tier`/`is_platform_owner` fallback (D8, amends D5). Each role SHALL be gated to only the nav items matching its real Casbin `role_permission` grants (migrations 002-020). Non-management roles SHALL receive read-only or limited surfaces only; no C-04 authorization routes are consumed.

#### Scenario: Management roles get full module surfaces
- **WHEN** a Platform Owner, Client Director, or Institution Admin loads the app
- **THEN** they see the modules permitted by their role's Casbin grants (Platform Owner and Client Director see Academic/Config/Fees/Homework per backend permissions)

#### Scenario: Non-management roles get limited surfaces
- **WHEN** a non-management role (admin, teacher, hod, principal, student, parent, staff) loads the app
- **THEN** they see only read-only or limited surfaces matching their Casbin permissions, with no operational screens until their backend exists

---

### REQ-SHELL-11: Replace Demo Frontend

The existing `frontend/` demo UI SHALL be replaced completely; only the Vite + Mantine base is retained and pages are rebuilt (D7, G6).

#### Scenario: Demo UI replaced
- **WHEN** the capability is delivered
- **THEN** the "Test UI" demo pages are removed and rebuilt against the themed shell

---

### REQ-SHELL-12: Responsive Data Tables

Data tables SHALL remain usable on narrow screens by collapsing or horizontal-scrolling, without losing required columns or actions (CC-AC-3).

#### Scenario: Table usable at narrow viewport
- **WHEN** a data table renders at a narrow viewport (e.g., 360px)
- **THEN** it collapses or scrolls horizontally while retaining required columns and actions

---

# Delta Spec — Frontend Shell (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** frontend-shell
> **Delta type:** MODIFIED (Breaking)
> **Base spec:** `openspec/specs/frontend-shell/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D6a, D3d, D8)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-25, AC-26)

---

## MODIFIED Requirements

### REQ-SHELL-09: Typed DTO API Layer (Modified — person projection, breaking)

All API responses SHALL map to typed DTOs in the UI API layer (mirroring backend DTOs). The `UserDTO` type SHALL be updated to include a `person` projection (`PersonDTO`: name, dob, gender, blood_group, photo, contact, demographics) sourced from the `person` entity. The `UserDTO` type SHALL NOT include `user_category_id` or any flat `user_profile` fields. The use of `any` SHALL remain disallowed in the API layer. This is a **breaking contract change** — the frontend's user-display and user-filter paths SHALL be updated to source human data from `user.person.*` and SHALL NOT reference `user.user_category_id` or `user.user_profile.*`. Per AC-25, AC-26.

#### Scenario: UserDTO typed with person projection
- **WHEN** the API layer receives a user response
- **THEN** it SHALL map to a typed `UserDTO` containing a `person: PersonDTO` field
- **AND** the `UserDTO` type SHALL NOT include `user_category_id` or flat `user_profile` fields
- **AND** untyped `any` handling SHALL remain disallowed

#### Scenario: Frontend user-display reads from person projection
- **WHEN** the frontend displays a user's name or profile fields
- **THEN** it SHALL read from `user.person.name` / `user.person.*`
- **AND** SHALL NOT attempt to read `user.user_category_id` or `user.user_profile.*`

#### Scenario: user_category filter removed
- **WHEN** the frontend renders user-list filters
- **THEN** there SHALL be no `user_category` dropdown or filter
- **AND** filtering SHALL be by role/institution (not by category)

---

### REQ-SHELL-10: All 10 Backend Roles (Modified — no role change, DTO only)

The frontend SHALL serve all 10 backend roles derived from the JWT roles array with `user_tier`/`is_platform_owner` fallback. Role definitions and permission-accurate gating are **unchanged** (D3d, D8 — roles stay on accounts; no authz policy/role-definition change). The only change in this domain is the `UserDTO` type update (REQ-SHELL-09). Per AC-17, AC-18.

#### Scenario: Role list unchanged (no regression)
- **WHEN** the frontend renders role-filtered navigation
- **THEN** the 10 roles SHALL be served as before
- **AND** `is_platform_owner` fallback SHALL remain
- **AND** no role definition or permission gating SHALL change

#### Scenario: Platform owner discovery via flag (not category)
- **WHEN** the frontend determines if a user is a Platform Owner
- **THEN** it SHALL use the `is_platform_owner` claim from the JWT
- **AND** SHALL NOT reference any `user_category` value

---

## Notes

- **PRD Q5 (sequencing):** The frontend is already archived. Whether the frontend update lands in this revamp's PR or as a residual follow-up is a product decision. This delta flags the breaking change; the parent session determines sequencing.
- **No authz route consumption:** The frontend does not consume C-04 authorization routes. Role-based gating is derived from the JWT `roles` claim only (R1). This is unchanged by the person-model revamp.
