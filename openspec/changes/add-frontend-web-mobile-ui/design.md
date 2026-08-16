# Design — Frontend (Web + Mobile UI)

> **Change:** add-frontend-web-mobile-ui
> **Status:** Draft
> **Last updated:** 2026-08-16
> **Inputs:** `docs/prd/frontend-web-mobile.md`, `docs/architecture/adr-frontend-implementation.md` (D1–D7, R1–R8), spec deltas under `openspec/changes/add-frontend-web-mobile-ui/specs/`
> **Purpose:** Technical design for the first UI-bearing build — a responsive web + installable PWA exposing the already-built backend modules only.

---

## 1. Overview

This design turns the decisional record (ADR D1–D7, R1–R8) and the behavioral deltas into a concrete frontend architecture. The system is a **single SPA** (`frontend/`) built with **React 19 + TypeScript + Vite + Mantine + TanStack Query + Axios + React Router v7 + `vite-plugin-pwa`**, themed to the Figma design system, role-gated from the JWT `roles` claim, and delivered in three domain-phased increments.

The frontend is **UI-only**: it consumes the existing FastAPI surface and introduces no backend behavior change (N6). Authorization remains **backend-authoritative** (Casbin RBAC+ABAC); the UI only hides/shows by role and renders a friendly 403 when the backend blocks a visible action.

---

## 2. Frontend Architecture

### 2.1 Technology stack (per D3)

| Concern | Choice | Version in repo |
|---|---|---|
| UI runtime | React | 19.x |
| Language | TypeScript | ~6.0 (compiler) |
| Build | Vite | 8.x |
| Component library | Mantine Core + Dates + Hooks + Notifications | 9.x |
| Server state | TanStack Query | 5.x |
| HTTP | Axios | 1.x |
| Routing | React Router DOM | 7.x (library mode) |
| PWA | `vite-plugin-pwa` | added (dev dependency) |
| Styling | Mantine theme + Emotion (already present) | — |
| Dates | dayjs (already present) | 1.x |

### 2.2 Runtime topology

```
┌────────────────────────────────────────────────────────────────┐
│ Browser (desktop / mobile) — installable PWA                  │
│  React Router v7 (library mode, BrowserRouter)                │
│   ├─ AuthFlow routes (login/activate/otp/reset) — no shell    │
│   └─ ProtectedAppShell (role-filtered nav + context switcher) │
│        ├─ React Query cache (per-domain query keys)           │
│        └─ Axios instance (typed DTO modules)                  │
│             · bearer JWT, 401 → refresh → login               │
│             · 403 → friendly permission-denied surface        │
└───────────────────────────┬────────────────────────────────────┘
                            │ HTTPS  /api/auth/*  and  /api/v1/*
                            ▼
        FastAPI backend (Supabase Auth JWT → TenantContext
                         → Casbin RBAC+ABAC → tenant repo + RLS)
```

**Dev proxy** (unchanged from current `vite.config.ts`): Vite proxies `/api` → `http://127.0.0.1:8000` and injects `Host: test-school.localhost`. Auth routes live under `/api/auth/*`; all other routes under `/api/v1/*`.

### 2.3 High-level directory layout

```
frontend/
├─ vite.config.ts              # + VitePWA plugin, existing /api proxy
├─ index.html                  # PWA meta + theme-color
├─ src/
│  ├─ main.tsx                 # providers: QueryClient, Mantine, Router, Notifications
│  ├─ App.tsx                  # route table only
│  ├─ theme/
│  │  ├─ index.ts              # createTheme(Figma tokens)
│  │  └─ tokens.ts             # color/typography/radius/spacing constants
│  ├─ core/
│  │  ├─ auth/
│  │  │  ├─ AuthProvider.tsx   # session state, silent refresh, logout
│  │  │  ├─ useSession.ts      # current user + roles + tenant ids
│  │  │  └─ RequireAuth.tsx    # route guard (redirect → /login)
│  │  ├─ context/
│  │  │  ├─ TenantProvider.tsx # client_id / institution_id + switcher
│  │  │  └─ useTenant.ts
│  │  ├─ access/
│  │  │  ├─ roles.ts           # role constants + hasRole(...)
│  │  │  ├─ navConfig.ts       # nav item → required role mapping
│  │  │  └─ usePermissions.ts  # derived from JWT roles claim
│  │  └─ api/
│  │     ├─ client.ts          # Axios instance + interceptors
│  │     ├─ errors.ts          # ApiError normalization + friendly 403 mapping
│  │     └─ dto/               # typed DTOs (mirror backend DTOs)
│  ├─ shell/
│  │  ├─ AppShell.tsx          # Mantine AppShell (sidebar ≥1024px, drawer <1024px)
│  │  ├─ Sidebar.tsx           # role-filtered nav
│  │  ├─ Header.tsx            # context switcher + user menu + logout
│  │  └─ NotFound.tsx / Forbidden.tsx
│  ├─ features/
│  │  ├─ auth/                 # Login, Activate, OtpVerify, ResetRequest, ResetConfirm, ChangePassword
│  │  ├─ platform/             # Clients, InstitutionTypes, OwnershipTransfers, ClientUsers
│  │  ├─ institutions/         # Institutions, OrgUnits
│  │  ├─ users/                # Users, UserProfile, Identifiers, RoleAssignment
│  │  ├─ academic/             # AcademicYears, StructureView, Subjects, SubjectGroups, TeacherAssignments, Enrollments
│  │  ├─ config/               # ConfigKeys, ConfigValues, ConfigResolve, ConfigAudit
│  │  ├─ fees/                 # FeeTypes, FeeAssignments, Payments
│  │  └─ homework/             # Homeworks, Submissions, Grades
│  └─ components/              # shared: DataTable, StatusPill, PageHeader, FormCard, ConfirmModal
```

> **Rationale for `core/` + `features/` split:** the existing demo UI is page-per-file with no shared primitives. The rebuild promotes cross-phase primitives (auth, tenant, access, api, theme, shell) into `core/` so Phase 2/3 add features without touching infrastructure (supports G5/D6 and R6 "reuse core patterns").

---

## 3. Module / Route Layout

### 3.1 Route table (library-mode React Router v7)

Route table is the **single source of truth for the reachable surface**. Each protected route carries a `roles` requirement so the shell can both filter nav and guard direct navigation.

| Path | Feature | Roles | Phase |
|---|---|---|---|
| `/login` | Login | public | P1 |
| `/activate` | Account activation (invite link) | public | P1 |
| `/otp/verify` | OTP verify (activation/reset) | public | P1 |
| `/password/reset` | Forgot + reset confirm | public | P1 |
| `/account/change-password` | Change password (logged in) | all | P1 |
| `/platform/clients` | Clients (list/detail) | Platform Owner | P1 |
| `/platform/clients/:clientId` | Client detail + users + institutions | Platform Owner | P1 |
| `/platform/institution-types` | Institution types | Platform Owner | P1 |
| `/platform/ownership-transfers` | Ownership transfers | Platform Owner | P1 |
| `/platform/clients/:clientId/users` | Client users | Platform Owner | P1 |
| `/institutions` | Institutions (+ go-live) | Client Director | P1 |
| `/institutions/:institutionId/org-units` | Org units (tree) | Client Director | P1 |
| `/users` | Users list | Director, Institution Admin | P1 |
| `/users/:userId` | Profile + identifiers + roles | Director, Institution Admin | P1 |
| `/academic/years` | Academic years | Institution Admin | P2 |
| `/academic/years/:yearId/structure` | Structure navigation | Institution Admin | P2 |
| `/academic/subjects` | Subjects | Institution Admin | P2 |
| `/academic/subject-groups` | Subject groups | Institution Admin | P2 |
| `/config/keys` | Config keys + values + resolve | Institution Admin | P2 |
| `/config/audit` | Config audit trail | Institution Admin | P2 |
| `/fees/types` | Fee types | Institution Admin | P3 |
| `/fees/assignments` | Fee assignments + waivers | Institution Admin | P3 |
| `/fees/payments` | Payments | Institution Admin | P3 |
| `/homework` | Homeworks | Institution Admin | P3 |
| `/homework/:hwId/submissions` | Submissions + grading | Institution Admin | P3 |
| `/homework/grades` | Grade views | Institution Admin | P3 |

**Catch-all:** unknown routes render `NotFound`; a protected route hit without session redirects to `/login` with a `redirect` state so post-login returns to the intended destination.

### 3.2 Route grouping (App.tsx)

```
<Routes>
  <Route element={<PublicOnly/>}>          {/* redirect if already authed */}
    <Route path="/login" …/>
    <Route path="/activate" …/>
    <Route path="/otp/verify" …/>
    <Route path="/password/reset" …/>
  </Route>
  <Route element={<RequireAuth/>}>
    <Route element={<AppShell/>}>          {/* persistent shell */}
      …all protected feature routes…
    </Route>
  </Route>
  <Route path="*" element={<NotFound/>} />
</Routes>
```

### 3.3 Nav gating is a declarative map, not inline conditionals

`navConfig.ts` maps each module to its required role(s). The sidebar and the route guard both consume the same map so a role change cannot silently desync nav from route protection.

---

## 4. API Integration Layer (typed DTOs)

### 4.1 Axios instance

`baseURL` is **empty** (origin-relative). Endpoints carry their full backend prefixes — `/api/auth/*` vs `/api/v1/*` — matching the backend routers exactly and flowing through the existing `/api` Vite proxy.

```ts
// core/api/client.ts (concept)
const api = axios.create({ baseURL: '' });

api.interceptors.request.use((cfg) => {
  const token = sessionStorage.getItem('access_token'); // see §4.4 storage note
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});
```

### 4.2 Interceptor behavior (session + 401/403 semantics)

| Event | Behavior |
|---|---|
| 401 on a non-auth call | Attempt one silent refresh via `/api/auth/refresh`; on success retry the original request once; on refresh 401 → clear tokens, redirect `/login` (REQ-SHELL-06, REQ-FE-AUTH-07). |
| 401 on `/api/auth/*` | No refresh loop; surface inline auth error. |
| 403 | Do **not** redirect. Normalize to `ApiError` with a `forbidden` flag so the calling mutation/query renders the friendly 403 surface (REQ-SHELL-07, R8). |
| 4xx/5xx | Normalize backend `detail` into a consistent `ApiError { status, message, code? }` for Notifications/toasts. |

Refresh is implemented as a queued single-flight promise so concurrent 401s trigger one refresh, not N refreshes.

### 4.3 Typed DTO modules (mirror backend DTOs)

Each backend domain gets a frontend DTO module that mirrors the backend `response_model` names (no `any` — REQ-SHELL-09 / CC-AC-5). Representative inventory (names from the actual routers):

| Module | DTOs (mirroring backend) |
|---|---|
| `core/api/dto/auth.ts` | `LoginResponse`, `TokenResponse`, `ActivateResponse`, `LoginRequest`, `RefreshRequest`, `PasswordChangeRequest`, `OtpRequest`, `OtpVerify` |
| `dto/platform.ts` | `ClientDTO`, `InstitutionTypeDTO`, `ApprovalDTO`, `OwnershipTransferEventDTO`, `ClientUserDTO`, `ClientUserCreateDTO`, `ClientUserUpdateDTO`, `ClientUserTransitionDTO` |
| `dto/institutions.ts` | `InstitutionDTO`, `OrgUnitDTO` |
| `dto/users.ts` | `UserDTO`, `UserCreateResponseDTO`, `UserProfileDTO`, `UserIdentifierDTO`, `RoleAssignmentDTO` |
| `dto/lookups.ts` | `UserCategoryDTO`, `RoleDTO`, `InstitutionTypeLookupDTO`, `OrgUnitTypeLookupDTO`, `LegalEntityTypeLookupDTO` |
| `dto/academic.ts` | `AcademicYearDTO`, `AcademicStructureDTO`, `TeacherAssignmentDTO`, `StudentEnrollmentDTO`, `SubjectDTO`, `SubjectGroupDTO` |
| `dto/config.ts` | config key/value/resolve/audit DTOs |
| `dto/fees.ts` | `FeeTypeDTO`, `FeeAssignmentDTO`, `PaymentDTO` |
| `dto/homework.ts` | `HomeworkDTO`, `HomeworkCreateDTO`, `HomeworkUpdateDTO`, `SubmissionDTO`, `SubmissionCreateDTO`, `GradeDTO`, `GradeCreateDTO`, `GradeUpdateDTO` |

Each DTO is a plain `interface`/`type`; runtime validation stays lightweight (optional, via a tiny `isX` guard or a schema lib only if a field is nullable in practice). The hard rule is **no `any`** in the API layer.

### 4.4 Query-key and storage conventions

- **React Query keys** are namespaced by domain and tenant context, e.g. `['clients', clientId]`, `['config-keys', institutionId]`, `['homeworks', institutionId, filters]`. Tenant context is part of every query key so switching context auto-invalidates/re-fetches.
- **Token storage:** access + refresh tokens in `sessionStorage` (cleared on tab close) rather than the demo's `localStorage`, reducing cross-tab persistence risk; the refresh token rotation contract is respected in the interceptor. *(Decision recorded here; if the backend refresh flow requires `localStorage` for cross-tab continuity, this is a one-line change in `client.ts`.)*

---

## 5. Role-Based Nav Gating from JWT

### 5.1 Roles

Three management roles only (D5): `platform_owner`, `client_director`, `institution_admin`. The JWT `roles` claim (array of strings) is the single gating source; **no C-04 permission routes are consumed** (R1).

### 5.2 Gating flow

1. `AuthProvider` decodes the JWT `roles` claim (plus `client_id` / `institution_id`) after login/refresh and exposes it via `useSession()`.
2. `navConfig.ts` maps each nav entry to an allowed-role predicate.
3. `Sidebar` renders only entries whose predicate passes (REQ-SHELL-03, P1-AC-1).
4. `RequireAuth` route guard independently enforces the same predicate so hidden nav ≠ unprotected route (defense in depth against direct URL entry).
5. `usePermissions().can(role)` is the only API callers use for button/action visibility.

### 5.3 Explicit non-enforcement

The UI **never** treats role gating as security (N5, REQ-SHELL-07). Any forged/direct request is rejected by the backend. The nav/action filter exists only to reduce dead-ends; the friendly 403 is the fallback for anything the UI shows but the backend disallows (e.g., future ABAC scopes).

---

## 6. Friendly 403 Handling

- A 403 is **never rendered as a raw error/stack trace** (R8, P1-AC-5).
- **Action-level:** when a mutation/query returns 403, the `ApiError.forbidden` flag triggers the `Forbidden` surface in place of the action (inline alert + "You don't have permission for this action"), while the rest of the page stays usable.
- **Route-level:** if the whole route is forbidden, render a full-page `Forbidden.tsx` with a clear message and a "go back" affordance.
- **No redirect to a 403 route:** keeping the user on the current screen with an inline notice avoids destructive navigation and preserves form state.

---

## 7. PWA Setup (`vite-plugin-pwa`)

Scope is **installable + responsive only**; offline data editing and background sync are deferred (N7, R8).

- Add `vite-plugin-pwa` to `vite.config.ts` with `registerType: 'autoUpdate'`, `manifest` (name, short name, `theme_color` `#2563EB`, `background_color` `#F1F5F9`, display `standalone`, icons from `public/`), and a `workbox` config limited to **precaching the static shell** (app HTML/JS/CSS) — **not** API responses.
- `index.html` gets PWA meta tags (`theme-color`, apple-touch-icon, manifest link).
- **No offline data strategy** in this build; API routes are network-only. This keeps the PWA installable without implying offline editing.

---

## 8. Figma Theme Approach (D4)

A single Mantine theme override recreates the Figma design system — no new design invention (N4, REQ-SHELL-02).

| Token | Value |
|---|---|
| Primary | `#2563EB` |
| Backgrounds | `#F1F5F9` (app), `#FFFFFF` (surfaces) |
| Text | `#0F172A` (primary), `#475569` (secondary), `#94A3B8` (muted) |
| Semantic | success `#16A34A`, warning `#D97706`, danger `#DC2626` |
| Typography | Inter (body), DM Sans (headings) — loaded via self-hosted font files or a font provider |
| Radii | 6 / 10 / 14 / 18 |
| Components | card, table, status-pill patterns restyled via `createTheme({ components })` |

**Approach:** `theme/tokens.ts` holds the raw Figma values as constants; `theme/index.ts` maps them into Mantine's `createTheme({ colors, primaryColor, fontFamily, headings, radius, spacing, components })`. Shared primitives (`StatusPill`, `DataTable`, `PageHeader`, `FormCard`) wrap Mantine components with the themed defaults so each feature screen is visually consistent without per-screen style code (addresses risk R6 "Figma-fidelity cost" by front-loading pattern work in P1).

---

## 9. Phased Build Order (D6)

Each phase is independently reviewable and verified before the next begins (capability-at-a-time discipline).

| Phase | Scope | Core deliverables |
|---|---|---|
| **P1** | Theme + shell + auth + tenant/institution + users/roles | `theme/`, `core/auth`, `core/context`, `core/access`, `core/api` (client + interceptor + DTO infra), `shell/`, auth screens, platform/institutions/users features, lookups-driven dropdowns |
| **P2** | Academic structure + configuration | `features/academic` (years, structure nav, subjects, subject groups, teacher assignments, enrollments), `features/config` (keys/values/resolve/audit), type-aware config inputs |
| **P3** | Fees + homework | `features/fees`, `features/homework`; **R6 dependency** — cohort bulk fee assignment is gated on a separate Fees backend change (see §11) |

**Ordering rationale:** P1 delivers the themed shell and core patterns (R6 mitigation) plus all auth/tenant/user flows that every later screen reuses; P2 and P3 then add features with zero infrastructure work.

---

## 10. Key Tradeoffs

| Tradeoff | Choice | Cost / consequence |
|---|---|---|
| **SPA (Vite) vs SSR (Next.js)** | Vite SPA + PWA | No SSR/SEO — acceptable for an authenticated internal ERP; simpler infra, matches existing repo (D3/ADR alternatives). |
| **Mantine vs Tailwind+shadcn** | Mantine, themed to Figma | Mature tables/forms/modals out of the box; needs a theme override to match Figma exactly (front-loaded in P1). |
| **Role gating (JWT) vs permission gating (C-04 read routes)** | Role gating from JWT `roles` | Coarser (role, not permission/ABAC-scope); zero backend change; friendly 403 covers the mismatch (R1/ADR alternatives). |
| **Backend-authoritative authz** | UI hides by role, never enforces | Some visible-but-blocked actions are possible → mitigated by friendly 403 and per-role fixture verification (R4). |
| **sessionStorage vs localStorage tokens** | sessionStorage | Tighter cross-tab hygiene; if cross-tab refresh continuity is needed, revert to localStorage (one-line change). |
| **PWA installable-only vs offline-capable** | Installable + responsive now | Offline editing deferred; avoids implying unsupported offline data behavior (N7/R8). |
| **Replace demo `frontend/` in place** | Keep Vite+Mantine base, rebuild pages | Clean start on structure; no demo page carryover (D7/G6). |
| **Cohort fee assignment (R6)** | Defer to separate backend change | Phase 3 fee assignment may be blocked pending a Fees backend change; tracked as a dependency, not implemented here. |

---

## 11. Risks and Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Figma operational screens pull scope toward unbuilt modules | Screen inventory strictly = built-module API surface; Figma is design-system reference only (D1). |
| R2 | Responsive tables break on phones | Shared `DataTable` with per-table collapse/horizontal-scroll strategy; verify at 360px per phase (CC-AC-3). |
| R3 | Roles/permissions screen gap | Explicitly out of scope; role-gated nav from JWT (P1-AC-24, R1). |
| R4 | Frontend/backend gating drift | Backend-authoritative; friendly 403; per-role fixture verification checks shown actions are backend-allowed. |
| R5 | Tenant-scoping bugs / cross-tenant leakage | Single `TenantProvider` + context switcher as sole source; `client_id`/`institution_id` in every request + query key (REQ-SHELL-08, CC-AC-4). |
| R6 | Figma-fidelity cost delays first screens | Themed shell + core component patterns built first in P1. |
| R7 | Academic-structure overreach (free-form CRUD expectation) | No direct CRUD UI; clone/template flows only, with clear copy (P2-AC-7). |
| R8 | PWA read as offline-capable | Scope to installable + responsive; offline sync deferred (N7). |
| R9 (new) | **R6 dependency — cohort fee assignment needs a backend change** | Phase 3 fee-assignment screen supports cohort bulk + per-student only if the Fees backend adds cohort targets; otherwise the P3 fee-assignment feature is flagged blocked and delivered after the backend change. |

---

## 12. Verification Hooks

Design-level verification hooks that map to the spec deltas; tasks/apply will turn these into concrete checks:

1. **Role fixture matrix** — a 3-role × module matrix asserts nav visibility and route-guard behavior (P1-AC-1, REQ-SHELL-03, REQ-SHELL-10).
2. **Friendly-403 check** — intercept/force a 403 on an allowed-looking action and assert the `Forbidden` surface renders (never raw error) (REQ-SHELL-07, R8).
3. **Tenant isolation check** — two-tenant fixture: switch context and assert no cross-tenant/cross-institution rows render (REQ-SHELL-08, CC-AC-4).
4. **Responsive check** — 360px viewport table collapse/scroll preserves required columns/actions (CC-AC-3).
5. **Typed-DTO check** — lint/typecheck asserts no `any` in `core/api/` (REQ-SHELL-09, CC-AC-5).
6. **Theme check** — primary `#2563EB`, Inter/DM Sans, semantic colors, radii match tokens (CC-AC-1, REQ-SHELL-02).
7. **PWA check** — manifest + service worker registration + installability in desktop/mobile browsers (CC-AC-2, REQ-SHELL-01).
8. **No-Roles-Screen check** — assert no Roles & Permissions route exists (P1-AC-24, R1).
9. **No-free-form-structure-CRUD check** — academic structure only reachable via clone/template flows (P2-AC-7, REQ-FE-AC-07).

---

## 13. Out of Scope (reaffirmed)

- No native app / separate mobile codebase (D2, N1).
- No operational screens (Dashboard, Students, Attendance, Timetable, Exams, Report Cards) (D1, N2).
- No Teacher/Student/Parent surfaces (D5, N3).
- No new design system (D4, N4).
- No frontend authorization enforcement; no Roles & Permissions screen (N5, R1).
- No backend endpoints or behavior changes (N6) — except the flagged R6 dependency, which is a separate change.
- No offline data editing / background sync (N7).
