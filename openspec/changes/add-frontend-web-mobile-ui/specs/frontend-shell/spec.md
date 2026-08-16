# Spec Delta — Frontend Shell (NEW)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** frontend-shell
> **Impact:** ADDED (new domain)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D1–D7, R1, R4, R8), `docs/prd/frontend-web-mobile.md` (P1-AC-1..P1-AC-5, CC-AC-1..CC-AC-5)

---

## ADDED Requirements

### REQ-SHELL-01: Single Responsive Web + PWA Codebase

The frontend SHALL be delivered as a single responsive web application that is installable as a Progressive Web App (PWA) and usable in both desktop and mobile browsers from one codebase. It SHALL NOT introduce a separate native mobile codebase (D2, N1). PWA scope is installable + responsive only; offline data editing and background sync are explicitly deferred (N7, R8).

#### Scenario: Installable on desktop and mobile
- **WHEN** a user opens the app in a desktop or mobile browser
- **THEN** the app renders from the same codebase and offers PWA install affordances without a native app

#### Scenario: No offline data editing
- **WHEN** a user attempts offline data editing or background sync in this build
- **THEN** the app does not provide those features (deferred to a future capability)

---

### REQ-SHELL-02: Mantine Theme Matches the Figma Design System

The UI SHALL be built with Mantine restyled to match the Figma design system via a single theme override. Tokens SHALL match: primary `#2563EB`; backgrounds `#F1F5F9` / `#FFFFFF`; text `#0F172A` / `#475569` / `#94A3B8`; semantic success `#16A34A`, warning `#D97706`, danger `#DC2626`; typography Inter (body) + DM Sans (headings); radii `6 / 10 / 14 / 18`; and the Figma card, table, and status-pill patterns. No new design system or design invention is permitted (D4, N4, CC-AC-1).

#### Scenario: Primary color and typography match Figma tokens
- **WHEN** any screen renders
- **THEN** the primary color is `#2563EB` and body text uses Inter while headings use DM Sans

#### Scenario: No design invention
- **WHEN** a screen or component is built
- **THEN** it reuses the Figma-derived Mantine theme and component patterns rather than introducing new visual patterns

---

### REQ-SHELL-03: Role-Filtered Navigation from JWT Roles

The app shell SHALL render role-filtered navigation derived from the JWT `roles` claim. A nav item SHALL appear only if the user's JWT roles allow that module. No C-04 authorization routes are consumed; gating is role-based from the JWT only (D5, P1-AC-1, R1).

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

### REQ-SHELL-10: Management Roles Only

The frontend SHALL serve the three management roles — Platform Owner, Client Director, and Institution Admin — and SHALL NOT expose Teacher, Student, or Parent surfaces until their operational backend exists (D5, N3).

#### Scenario: Management roles only
- **WHEN** the app renders navigation and actions
- **THEN** they target Platform Owner, Client Director, and Institution Admin roles only

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
