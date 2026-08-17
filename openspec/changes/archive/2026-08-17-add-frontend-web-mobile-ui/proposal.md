# Proposal — Frontend (Web + Mobile UI)

> **Change:** add-frontend-web-mobile-ui
> **Status:** Draft
> **Last updated:** 2026-08-16
> **Source:** `docs/prd/frontend-web-mobile.md`, `docs/architecture/adr-frontend-implementation.md` (D1–D7, R1–R8)

---

## 1. Summary

Add the first UI-bearing capability: a responsive web + installable PWA frontend (single codebase) that exposes the **already-built backend modules only** — C-01 Tenant & Institution, C-02 Identity & User, C-03 Auth, C-05 Academic Structure, C-08 Configuration, plus the Fees and Homework business modules. The UI is themed to the Figma design system (primary `#2563EB`) and role-gated from the JWT `roles` claim for the three management roles: Platform Owner, Client Director, and Institution Admin. Delivery is sequenced in three phases (P1 = shell + auth + tenant/institution + users/roles; P2 = academic structure + config; P3 = fees + homework).

## 2. Motivation

The backend is API-first and has built and archived C-01, C-02, C-03, C-04, C-05, C-08, Fees, and Homework — but none has a production UI. The two existing frontend inputs are unusable: the repo demo UI (`frontend/`) is an explicitly-labeled "Test UI" covering only Login, Platform, Fees, and Homework, and the Figma Make export is visually polished but its real screens target operational modules with no backend. Management work today can only be done against raw APIs. This change delivers the product surface for the three management roles the platform serves.

## 3. Scope

### In scope (built backend modules)

| Phase | Domain | Screens |
|---|---|---|
| P1 | App shell + auth | Login, activation, OTP, password reset/change, logout, silent refresh, role-filtered nav, client/institution switcher |
| P1 | C-01 Tenant/Institution | Clients, institution types, ownership transfers, client users (Platform Owner); institutions + go-live, org units (Client Director) |
| P1 | C-02 / C-04 Users & roles | Users, profiles, identifiers, role assignment, lookups-driven dropdowns |
| P2 | C-05 Academic Structure | Academic years (clone/template), structure navigation, lifecycle transition, subjects, subject groups, teacher assignments, section enrollments |
| P2 | C-08 Configuration | Config keys, values, resolved (effective) values, audit trail |
| P3 | Fees | Fee types, fee assignments + waivers, payments |
| P3 | Homework | Homeworks, submissions, grading, grade views |

### Out of scope (explicit non-goals)

- No native mobile app or separate mobile codebase (N1, D2).
- No operational screens — Dashboard, Students, Attendance, Timetable, Exams, Report Cards (N2, D1).
- No non-management roles — Teacher, Student, Parent (N3, D5).
- No new design invention (N4, D4).
- No frontend-side authorization enforcement (N5); no Roles & Permissions screen — no C-04 routes consumed (R1, P1-AC-24).
- No new backend endpoints or backend behavior changes (N6).
- No offline data editing or background sync in this build (N7).

## 4. Key Decisions (D1–D7, R1–R8)

| # | Decision |
|---|---|
| D1 | Build for built backend modules only; Figma is design-system + app-shell reference, not the screen inventory |
| D2 | Responsive web + PWA, single codebase; no native app |
| D3 | React 19 + TypeScript + Vite + Mantine + TanStack Query + Axios + React Router v7 + `vite-plugin-pwa` |
| D4 | Mantine theme recreates the Figma design system (primary `#2563EB`, Inter body / DM Sans headings, semantic colors, radii, card/table/status-pill patterns) |
| D5 | Management roles only; navigation/actions role-gated from the JWT `roles` claim (no C-04 authz routes consumed); backend stays authoritative |
| D6 | Three phases by domain: P1 shell+auth+tenant/users, P2 academic+config, P3 fees+homework |
| D7 | Replace `frontend/` completely; keep only the Vite + Mantine base |
| R1 | Roles & Permissions screen deferred entirely (no C-04 routes) |
| R2 | OTP for activation + password reset only (no login 2FA step-up) |
| R3 | Post-activation landing: land on login |
| R4 | Institution switcher default: last-used (persisted), fallback to first |
| R5 | All config keys editable; backend validates unsafe edits |
| R6 | Fee assignment target: cohort bulk + per-student (⚠️ may require Fees backend change) |
| R7 | Homework author: management roles only |
| R8 | Blocked actions render a friendly 403, never a raw error |

## 5. Impact

### New domain

- **frontend-shell** — app shell, navigation, context switcher, session/access control, PWA, design system, responsive behavior, typed API layer, friendly 403.

### Existing domains extended with net-new frontend UI (ADDED requirements)

- **authentication** (C-03) — login/activation/OTP/password/logout UI.
- **tenant-institution** (C-01) — clients, institution types, ownership transfers, client users, institutions, org units UI.
- **identity-user-management** (C-02) — users, profiles, identifiers, role assignment, lookups UI.
- **academic-structure** (C-05) — academic years, structure navigation, transitions, subjects, subject groups, teacher assignments, enrollments UI.
- **configuration** (C-08) — config keys, values, resolve, audit UI.
- **fees** — fee types, assignments, payments UI.
- **homework** — homeworks, submissions, grading UI.

### No backend changes

This capability is UI-only against the existing API surface (N6). The only flagged exception is R6 (cohort fee assignment), which may require a separate Fees backend change **before** Phase 3 — tracked here as a dependency, not implemented in this change.

## 6. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| C-01 Tenant & Institution backend | Hard | P1 screens consume its routes |
| C-02 Identity & User backend | Hard | P1 users/profile/identifiers/roles screens |
| C-03 Auth backend | Hard | P1 auth flows |
| C-04 Authorization backend | Indirect | Not consumed (no routes); backend enforces Casbin and returns 403 |
| C-05 Academic Structure backend | Hard | P2 academic screens |
| C-08 Config backend | Hard | P2 config screens |
| Fees backend | Hard | P3 fees screens |
| Homework backend | Hard | P3 homework screens |
| Figma design system | Hard | Design tokens + component patterns |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Figma screens imply unbuilt modules (R1) | Figma is design-system/app-shell reference only; screen inventory = built-module API surface |
| Responsive tables on phones (R2) | Per-table collapse/scroll; CC-AC-3 |
| Roles/permissions UI gap (R3) | Explicitly out of scope; role-gated nav from JWT |
| Frontend/backend gating drift (R4) | Backend-authoritative; friendly 403; per-role fixture verification |
| Tenant-scoping bugs (R5) | Single context provider + switcher as sole source of tenant context |
| Figma-fidelity cost (R6) | Themed shell + core patterns built first in P1 |
| Academic-structure UI overreach (R7) | No direct CRUD UI; clone/template flows only |
| PWA expectations (R8) | Installable + responsive now; offline sync deferred |
