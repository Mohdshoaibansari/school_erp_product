# Tasks — Frontend (Web + Mobile UI)

> **Change:** add-frontend-web-mobile-ui
> **Status:** Draft
> **Last updated:** 2026-08-16
> **Source:** `design.md`, `specs/`, `docs/prd/frontend-web-mobile.md`, `docs/architecture/adr-frontend-implementation.md` (D1–D7, R1–R8)

---

## How to read this file

- Tasks are split into **Phase 1 (P1)**, **Phase 2 (P2)**, and **Phase 3 (P3)** per ADR **D6** (capability-at-a-time discipline). Each phase is reviewable before the next begins.
- Every task carries a **spec mapping** (e.g. `REQ-SHELL-02`) and an **Evidence** line that names the concrete artifact or command that proves completion. A task is only "done" when its evidence is produced and passes.
- Cross-cutting requirements (`REQ-SHELL-*`) are built in P1 and then re-verified against every later screen.
- The **Requirements Coverage** table at the end maps every spec requirement to the task(s) that satisfy it.

**Verification commands (run at the end of every phase):**

| Command | What it proves |
|---|---|
| `cd frontend && npm run build` | TypeScript typecheck (`tsc -b`) + production Vite build succeed; PWA assets emitted |
| `cd frontend && npm run lint` | oxlint passes (no `any` in `core/api`, no unused/dead code) |
| `cd frontend && npm run test -- --run` | Vitest unit + component/integration tests pass |
| `cd frontend && npm run dev` + browser | Manual responsive/PWA/role-fixture checks documented in `verify.md` |

> **Scope guard (non-negotiable, from ADR/PRD):** no native app, no operational screens (Dashboard/Students/Attendance/Timetable/Exams/Report Cards), no Teacher/Student/Parent surfaces, no Roles & Permissions screen, no frontend-side authorization enforcement, no new backend endpoints or behavior changes (except the flagged R6 Fees dependency tracked as a separate change), no offline data editing/background sync.

---

## Phase 1 — Theme, Shell, Auth, Tenant/Institution, Users & Roles

### 1. Tooling & PWA foundation

- [ ] **1.1** Add `vite-plugin-pwa` (dev dependency) and register it in `frontend/vite.config.ts` with `registerType: 'autoUpdate'`, a `manifest` (name/short_name, `theme_color: #2563EB`, `background_color: #F1F5F9`, `display: standalone`, icons from `public/`), and a `workbox` config that **precaches the static shell only** (app HTML/JS/CSS), never API responses. → `REQ-SHELL-01`
  - **Evidence:** `vite.config.ts` contains the `VitePWA` plugin; `npm run build` exits 0 and emits `dist/manifest.webmanifest` + `dist/sw.js`; manifest `theme_color` equals `#2563EB`.

- [ ] **1.2** Add PWA meta tags to `frontend/index.html`: `<meta name="theme-color" content="#2563EB">`, manifest link, `apple-touch-icon`, and any mobile viewport refinements. → `REQ-SHELL-01`
  - **Evidence:** `index.html` contains the theme-color meta (value `#2563EB`) and the manifest link.

- [ ] **1.3** Add test tooling as dev dependencies: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `msw`, `jsdom`; add a `"test": "vitest"` script and a `vitest.config` (or extend `vite.config.ts` `test` block) with a `setupTests.ts` that loads jest-dom matchers and configures the MSW server. (Minimal — required to make the verification hooks below evidence-checkable.) → *enables* `REQ-SHELL-03/05/06/07/08/09/12` verification
  - **Evidence:** `package.json` has a `test` script; `npm run test -- --run` executes (a trivial smoke test passes); setup file is referenced in config.

### 2. Theme — Figma design system

- [ ] **2.1** Create `frontend/src/theme/tokens.ts` with the Figma tokens as constants: primary `#2563EB`; backgrounds `#F1F5F9`/`#FFFFFF`; text `#0F172A`/`#475569`/`#94A3B8`; semantic success `#16A34A`, warning `#D97706`, danger `#DC2626`; radii `6/10/14/18`. → `REQ-SHELL-02`
  - **Evidence:** `theme/tokens.ts` exists and exports the named constants with the exact hex values above.

- [ ] **2.2** Create `frontend/src/theme/index.ts` calling Mantine `createTheme({ colors, primaryColor, fontFamily, headings, radius, spacing, components })` that maps the tokens into a Mantine theme (Inter body, DM Sans headings). → `REQ-SHELL-02`
  - **Evidence:** `theme/index.ts` exports a `theme` object; a unit test asserts `theme.primaryColor === 'blue'` resolves to `#2563EB` and `theme.fontFamily`/`headings` reference Inter/DM Sans.

- [ ] **2.3** Load Inter and DM Sans fonts (self-hosted files or a font provider) and apply via the theme/global styles. → `REQ-SHELL-02`
  - **Evidence:** font assets exist (or provider link in `index.html`); rendered headings use DM Sans and body uses Inter (manual check in `verify.md`).

- [ ] **2.4** Create shared primitives `StatusPill`, `DataTable`, `PageHeader`, `FormCard`, `ConfirmModal` under `frontend/src/components/` wrapping Mantine with themed defaults. `DataTable` SHALL support a collapse/horizontal-scroll strategy for narrow viewports. → `REQ-SHELL-02`, `REQ-SHELL-12`
  - **Evidence:** component files exist; a `DataTable` unit test asserts the responsive prop (collapse vs horizontal scroll) is applied below a breakpoint.

- [ ] **2.5** Theme fidelity check: no new design invention; every screen reuses the themed Mantine theme and shared primitives. → `REQ-SHELL-02`
  - **Evidence:** lint/visual sweep documented in `verify.md`; a test asserts a sample screen renders with primary color `#2563EB` applied (CSS variable/theme).

### 3. Core infrastructure — auth, tenant, access, API

- [ ] **3.1** Create `frontend/src/core/api/client.ts`: Axios instance with `baseURL: ''`, a request interceptor that attaches `Authorization: Bearer <token>` from `sessionStorage`. → `REQ-SHELL-08`
  - **Evidence:** `client.ts` exists; a unit test asserts the bearer header is attached when a token is present and omitted otherwise.

- [ ] **3.2** Create `frontend/src/core/api/errors.ts`: normalize backend errors into a consistent `ApiError { status, message, code?, forbidden? }`, with a `forbidden` flag for 403. → `REQ-SHELL-07`
  - **Evidence:** `errors.ts` exists; a unit test maps a 403 response to `ApiError` with `forbidden === true` and a 422/400 to a non-forbidden `ApiError` with the backend `detail`.

- [ ] **3.3** Implement response interceptors: on 401 for non-auth calls, perform a **single-flight queued** silent refresh via `/api/auth/refresh` then retry the original request once; on refresh 401, clear tokens and redirect to `/login`; on 401 for `/api/auth/*`, do not refresh-loop (surface inline error); on 403, do not redirect (set `forbidden` flag). → `REQ-SHELL-06`, `REQ-SHELL-07`, `REQ-FE-AUTH-07`
  - **Evidence:** interceptor tests cover: single refresh for N concurrent 401s, retry-once on refresh success, redirect on refresh 401, no refresh loop on auth-route 401, no redirect on 403.

- [ ] **3.4** Create `frontend/src/core/auth/AuthProvider.tsx`: session state, silent refresh scheduling, logout; decode the JWT `roles` claim plus `client_id`/`institution_id` and expose them. → `REQ-SHELL-06`
  - **Evidence:** provider file exists; a test verifies roles and tenant ids are parsed from a fixture JWT payload.

- [ ] **3.5** Create `frontend/src/core/auth/useSession.ts` and `RequireAuth.tsx` route guard: redirect to `/login` with a `redirect` state when no valid session. → `REQ-SHELL-06`
  - **Evidence:** a route-guard test renders children for an authed session and redirects to `/login` (preserving `redirect` state) when unauthenticated.

- [ ] **3.6** Create `frontend/src/core/context/TenantProvider.tsx` + `useTenant.ts`: the **single source** of `client_id`/`institution_id`; switcher state; last-used persistence with fallback to first institution (R4); Institution Admin has a fixed context (no switcher). → `REQ-SHELL-05`, `REQ-SHELL-08`
  - **Evidence:** provider files exist; a unit test covers last-used → first fallback and fixed Admin context.

- [ ] **3.7** Create `frontend/src/core/access/roles.ts` (role constants + `hasRole`), `navConfig.ts` (nav item → required role(s) map), and `usePermissions.ts` (derives `can(role)` from the JWT `roles` claim). Management roles only. → `REQ-SHELL-03`, `REQ-SHELL-10`
  - **Evidence:** files exist; a unit test asserts `navConfig` maps each P1 module to its correct role(s) and `hasRole`/`can` behave correctly for the three roles.

- [ ] **3.8** Create typed DTO modules under `frontend/src/core/api/dto/` for `auth`, `platform`, `institutions`, `users`, `lookups`, mirroring backend `response_model` names; **no `any`**. → `REQ-SHELL-09`
  - **Evidence:** DTO files exist; `oxlint`/`tsc` flags no `any` in `core/api/` (lint rule / typecheck passes).

### 4. App shell

- [ ] **4.1** Create `frontend/src/shell/AppShell.tsx` using Mantine `AppShell`: persistent sidebar at ≥1024px, off-canvas drawer below 1024px. → `REQ-SHELL-04`
  - **Evidence:** file exists; a component test (or `verify.md` manual check) asserts sidebar at desktop and drawer toggle at mobile width.

- [ ] **4.2** Create `frontend/src/shell/Sidebar.tsx` rendering nav entries filtered by the `navConfig` role map. → `REQ-SHELL-03`
  - **Evidence:** a test renders the sidebar for each role and asserts only allowed modules appear.

- [ ] **4.3** Create `frontend/src/shell/Header.tsx`: context switcher (Platform Owner → client, Client Director → institution; hidden for Institution Admin) + user menu + logout. → `REQ-SHELL-05`, `REQ-FE-AUTH-06`
  - **Evidence:** a test asserts the switcher renders for PO/CD and not for Admin; logout action clears session and returns to login.

- [ ] **4.4** Create `frontend/src/shell/Forbidden.tsx` (friendly permission-denied surface) and `NotFound.tsx`. → `REQ-SHELL-07`
  - **Evidence:** files exist; a test asserts `Forbidden` renders a friendly message (never a raw error/stack trace) when fed a `forbidden` `ApiError`.

- [ ] **4.5** Create `frontend/src/App.tsx` as the **route table only** (library-mode React Router v7): `PublicOnly` group (login/activate/otp/reset), `RequireAuth` → `AppShell` group (all protected feature routes), and `*` → `NotFound`. → `REQ-SHELL-06`
  - **Evidence:** `App.tsx` contains the route table matching `design.md` §3.1; a route test confirms catch-all → NotFound.

- [ ] **4.6** Wire providers in `frontend/src/main.tsx`: `QueryClientProvider`, `MantineProvider` (themed), `Router`, `Notifications`. → `REQ-SHELL-02`
  - **Evidence:** `main.tsx` renders the provider hierarchy; app boots with the themed Mantine provider.

- [ ] **4.7** Remove demo pages and the "Test UI" header; keep only the Vite + Mantine base. → `REQ-SHELL-11`
  - **Evidence:** `git grep -i "test ui"` in `frontend/src` returns nothing; `frontend/src/pages/` demo files removed or replaced; `npm run build` passes.

### 5. Auth screens

- [ ] **5.1** Login screen `frontend/src/features/auth/Login.tsx`: email + password; on success load shell with role-filtered nav; on failure inline error, no route change. → `REQ-FE-AUTH-01`
  - **Evidence:** `Login` component + a component test (MSW) covering success (shell loads) and failure (inline error, same route).

- [ ] **5.2** Activation screen (invite link): confirm credentials; on success redirect to `/login` (R3). → `REQ-FE-AUTH-02`
  - **Evidence:** component + test asserting post-activation redirect to `/login`.

- [ ] **5.3** OTP request/verify flow for activation + password reset only; wrong/expired OTP shows inline error and allows re-request; no login 2FA step-up. → `REQ-FE-AUTH-03`
  - **Evidence:** component + test for request/verify, error/re-request path, and a negative assertion that login has no OTP step.

- [ ] **5.4** Forgot-password → reset → new-password flow, redirect to `/login` with success state. → `REQ-FE-AUTH-04`
  - **Evidence:** component + test asserting the complete flow ends at login with a success message.

- [ ] **5.5** Change-password (logged-in) screen from profile/settings. → `REQ-FE-AUTH-05`
  - **Evidence:** component + test asserting current + new + confirm submission and success confirmation.

- [ ] **5.6** Logout action wired in the header/user menu; terminates session, returns to login. → `REQ-FE-AUTH-06`
  - **Evidence:** covered by task 4.3 test (session cleared + redirect to login).

- [ ] **5.7** Auth screens responsive + themed. → `REQ-FE-AUTH-08`
  - **Evidence:** manual sweep documented in `verify.md`; theme applied via shared primitives (no per-screen styling).

### 6. Tenant/institution screens (C-01)

- [ ] **6.1** Clients (Platform Owner): list (searchable/filterable), detail, create, edit, lifecycle transition; view client's institutions and users. → `REQ-FE-TI-01`
  - **Evidence:** `features/platform/Clients.tsx` (+ detail) + MSW-backed test covering list/create/edit/transition and nested institutions/users.

- [ ] **6.2** Institution types catalog (Platform Owner): list/create/edit/deactivate. → `REQ-FE-TI-02`
  - **Evidence:** component + test covering CRUD and deactivate.

- [ ] **6.3** Ownership transfers (Platform Owner): initiate, review/complete, reflect on affected tenant. → `REQ-FE-TI-03`
  - **Evidence:** component + test covering initiate → complete and the resulting tenant ownership state.

- [ ] **6.4** Client users (Platform Owner) via `/api/v1/platform/clients/{client_id}/users`: list/create/edit/transition. → `REQ-FE-TI-04`
  - **Evidence:** component + test asserting requests hit the platform client-users endpoint.

- [ ] **6.5** Institutions (Client Director): list/create/edit/transition + go-live, scoped to director's client. → `REQ-FE-TI-05`
  - **Evidence:** component + test covering CRUD, lifecycle, and go-live.

- [ ] **6.6** Org units (Client Director): tree/subtree navigation, create/edit, move, reorder siblings, archive/reactivate. → `REQ-FE-TI-06`
  - **Evidence:** component + test covering tree render, move/reorder, and archive/reactivate.

### 7. Users & roles screens (C-02 / C-04)

- [ ] **7.1** Users (Director/Admin, scoped): list/create (category, identifiers, contact)/edit/transition status; open profile. → `REQ-FE-USR-01`
  - **Evidence:** component + test covering CRUD + status transitions scoped to client/institution.

- [ ] **7.2** Profile view/edit. → `REQ-FE-USR-02`
  - **Evidence:** component + test covering view and edit of profile fields.

- [ ] **7.3** Identifier management on profile (list/create/edit/remove). → `REQ-FE-USR-03`
  - **Evidence:** component + test covering identifier CRUD.

- [ ] **7.4** Role assignment on profile (view/assign/remove from role catalog). → `REQ-FE-USR-04`
  - **Evidence:** component + test covering assign/remove and catalog source.

- [ ] **7.5** Reference dropdowns sourced from the lookups API (user-category, role, institution-type, org-unit-type, legal-entity-type). → `REQ-FE-USR-05`
  - **Evidence:** component + test asserting dropdown options come from the lookups endpoints (MSW fixtures), not hardcoded.

- [ ] **7.6** Assert no Roles & Permissions screen/route exists. → `REQ-FE-USR-06`, `REQ-SHELL-03`
  - **Evidence:** route-table test asserts no roles/permissions route is registered.

### 8. Phase 1 verification

- [ ] **8.1** Role fixture matrix: a 3-role × P1-module test asserts nav visibility and route-guard behavior per role. → `REQ-SHELL-03`, `REQ-SHELL-10`, `P1-AC-1`
  - **Evidence:** `src/core/access/__tests__/roleFixture.test.tsx` (or equivalent) passes for Platform Owner / Client Director / Institution Admin.

- [ ] **8.2** Friendly-403 check: force a 403 on an allowed-looking action; assert `Forbidden` renders (never raw error). → `REQ-SHELL-07`, `P1-AC-5`, R8
  - **Evidence:** a test intercepts a 403 and asserts the friendly surface renders in place of the action.

- [ ] **8.3** Tenant isolation check: two-tenant fixture; switch context; assert no cross-tenant/cross-institution rows. → `REQ-SHELL-08`, `CC-AC-4`
  - **Evidence:** a test with two MSW tenant fixtures asserts scoped rows only; query keys include tenant context.

- [ ] **8.4** Responsive check: `DataTable` collapse/scroll at 360px preserves required columns/actions. → `REQ-SHELL-12`, `CC-AC-3`
  - **Evidence:** `DataTable` responsive test + manual 360px sweep documented in `verify.md`.

- [ ] **8.5** Typed-DTO check: `core/api/` has no `any`. → `REQ-SHELL-09`, `CC-AC-5`
  - **Evidence:** `npm run build` (tsc) and `npm run lint` pass with a `no-explicit-any` lint rule.

- [ ] **8.6** PWA installability check: manifest + service worker present; installable on desktop/mobile. → `REQ-SHELL-01`, `CC-AC-2`
  - **Evidence:** build emits `manifest.webmanifest` + `sw.js`; manual install/Lighthouse check documented in `verify.md`.

- [ ] **8.7** Phase 1 build gate: `npm run build`, `npm run lint`, `npm run test -- --run` all pass. → *phase gate*
  - **Evidence:** all three commands exit 0 with the Phase 1 test suite green.

---

## Phase 2 — Academic Structure + Configuration

### 9. Phase 2 DTOs

- [ ] **9.1** Add typed DTO modules `dto/academic.ts` (`AcademicYearDTO`, `AcademicStructureDTO`, `TeacherAssignmentDTO`, `StudentEnrollmentDTO`, `SubjectDTO`, `SubjectGroupDTO`) and `dto/config.ts` (key/value/resolve/audit DTOs); no `any`. → `REQ-SHELL-09`
  - **Evidence:** DTO files exist; typecheck/lint pass with no `any`.

### 10. Academic structure screens (C-05)

- [ ] **10.1** Create academic year (name, start/end dates) with clone-previous-year / template generation, structure preview, confirm → "planning" status. → `REQ-FE-AC-01`
  - **Evidence:** `features/academic/AcademicYears.tsx` + test asserting clone/template call, preview render, and planning status on confirm.

- [ ] **10.2** Structure navigation: grade levels → classes → sections for a selected year. → `REQ-FE-AC-02`
  - **Evidence:** `StructureView` + test asserting hierarchy navigation.

- [ ] **10.3** Academic year lifecycle transition (planning → active → closed); activate auto-closes previous; closed = read-only. → `REQ-FE-AC-03`
  - **Evidence:** component + test for transition, auto-close-previous, and read-only closed state.

- [ ] **10.4** Subjects + subject groups: list/create/edit/assign via subjects/subject-groups endpoints. → `REQ-FE-AC-04`
  - **Evidence:** `Subjects.tsx` + `SubjectGroups.tsx` + tests covering CRUD and assignment.

- [ ] **10.5** Teacher assignments per section (teacher → subject): create/list/remove. → `REQ-FE-AC-05`
  - **Evidence:** component + test covering create/list/remove.

- [ ] **10.6** Section enrollments (student → section): list/enroll from roster/remove. → `REQ-FE-AC-06`
  - **Evidence:** component + test covering list, roster search/select enroll, and remove.

- [ ] **10.7** Assert no direct CRUD UI for sections/grades/terms; structure changes only via clone/template flows. → `REQ-FE-AC-07`, `P2-AC-7`
  - **Evidence:** route/component test asserts no free-form CRUD routes/controls exist for structure nodes.

### 11. Configuration screens (C-08)

- [ ] **11.1** Config keys + values: browse institution-scoped keys; view/edit values with type-aware input. → `REQ-FE-CFG-01`
  - **Evidence:** `features/config/ConfigKeys.tsx` + test asserting key browse and type-aware value editing.

- [ ] **11.2** Resolved (effective) value view accounting for scope fallbacks (Institution → Client → Platform → default). → `REQ-FE-CFG-02`
  - **Evidence:** component + test asserting resolved value + source scope display.

- [ ] **11.3** Config audit trail (who changed what, when). → `REQ-FE-CFG-03`
  - **Evidence:** `ConfigAudit.tsx` + test asserting audit rows render with actor/action/timestamp.

- [ ] **11.4** All keys editable; unsafe edits blocked by backend validation and surfaced as a friendly error (UI never pre-hides keys). → `REQ-FE-CFG-04`, R5
  - **Evidence:** a test asserts a backend-rejected edit surfaces a friendly error rather than the UI hiding the key.

### 12. Phase 2 verification

- [ ] **12.1** Academic lifecycle + no-direct-CRUD tests green (tasks 10.3, 10.7). → `REQ-FE-AC-03`, `REQ-FE-AC-07`
- [ ] **12.2** Config type-aware input / resolve / audit / backend-validation tests green (tasks 11.1–11.4). → `REQ-FE-CFG-01..04`
- [ ] **12.3** Role gating: academic/config screens visible only to Institution Admin; tenant-scoped queries carry institution context. → `REQ-SHELL-03`, `REQ-SHELL-08`
- [ ] **12.4** Responsive + build gate: `npm run build`, `npm run lint`, `npm run test -- --run` pass; 360px sweep documented in `verify.md`. → `REQ-SHELL-12`, `CC-AC-3`

---

## Phase 3 — Fees + Homework

### 13. Fees screens

- [ ] **13.1** Fee types: list/create/edit (name, amount basis, defaults). → `REQ-FE-FEE-01`
  - **Evidence:** `features/fees/FeeTypes.tsx` + test covering CRUD.

- [ ] **13.2** Fee assignments: create/edit/remove + record a fee waiver for a student. → `REQ-FE-FEE-02`
  - **Evidence:** `features/fees/FeeAssignments.tsx` + test covering CRUD and waiver.

- [ ] **13.3** Payments: record a payment against a fee assignment; view payments filterable by student/fee/date/status. → `REQ-FE-FEE-03`
  - **Evidence:** `features/fees/Payments.tsx` + test covering record and filters.

- [ ] **13.4** Cohort bulk + per-student fee assignment. ⚠️ **Dependency R6:** this is gated on a separate Fees backend change for cohort-level targets. Implement per-student now; gate the cohort-bulk UI behind a backend capability check and mark the cohort path as blocked/pending if unsupported. → `REQ-FE-FEE-04`
  - **Evidence:** a test asserts per-student assignment works and the cohort path is feature-flagged; a skipped/pending test documents the R6 backend dependency.

### 14. Homework screens

- [ ] **14.1** Homework: create (subject, section/scope, title, instructions, due date)/list/edit/close. → `REQ-FE-HW-01`
  - **Evidence:** `features/homework/Homeworks.tsx` + test covering CRUD and close.

- [ ] **14.2** Submissions per homework: list (per student), open/view submitted work, grade a submission. → `REQ-FE-HW-02`
  - **Evidence:** `Submissions.tsx` + test covering list/view/grade.

- [ ] **14.3** Grade views: per homework and per student; update where the API supports it. → `REQ-FE-HW-03`
  - **Evidence:** `Grades.tsx` + test covering per-homework and per-student views and update.

- [ ] **14.4** Homework authoring/grading restricted to management roles (Institution Admin); no teacher UI. → `REQ-FE-HW-04`, R7
  - **Evidence:** role-fixture test asserts only Institution Admin sees homework authoring/grading actions.

### 15. Phase 3 DTOs + verification

- [ ] **15.1** Add typed DTO modules `dto/fees.ts` (`FeeTypeDTO`, `FeeAssignmentDTO`, `PaymentDTO`) and `dto/homework.ts` (`HomeworkDTO`, `HomeworkCreateDTO`, `HomeworkUpdateDTO`, `SubmissionDTO`, `SubmissionCreateDTO`, `GradeDTO`, `GradeCreateDTO`, `GradeUpdateDTO`); no `any`. → `REQ-SHELL-09`
  - **Evidence:** DTO files exist; typecheck/lint pass with no `any`.

- [ ] **15.2** Fees/homework tests green (tasks 13.1–13.4, 14.1–14.4). → `REQ-FE-FEE-01..04`, `REQ-FE-HW-01..04`
- [ ] **15.3** R6 dependency flag verified: cohort fee assignment documented as blocked pending the Fees backend change. → `REQ-FE-FEE-04`, R6
- [ ] **15.4** Role gating + tenant scoping + responsive verified for fees/homework. → `REQ-SHELL-03`, `REQ-SHELL-08`, `REQ-SHELL-12`
- [ ] **15.5** Phase 3 build gate: `npm run build`, `npm run lint`, `npm run test -- --run` pass. → *phase gate*

---

## 16. Cross-cutting final verification (whole capability)

- [ ] **16.1** Full role fixture matrix across all three phases (3 roles × all modules) — nav visibility + route guards. → `REQ-SHELL-03`, `REQ-SHELL-10`
- [ ] **16.2** End-to-end tenant isolation: two-tenant fixture exercised across all domains; no cross-tenant/cross-institution data. → `REQ-SHELL-08`, `CC-AC-4`
- [ ] **16.3** Responsive sweep: no in-scope screen unusable at 360px (collapse/scroll applied). → `REQ-SHELL-12`, `CC-AC-3`
- [ ] **16.4** Typed-DTO + no-`any` assertion across `core/api` and all `dto/` modules. → `REQ-SHELL-09`, `CC-AC-5`
- [ ] **16.5** PWA installability final check (desktop + mobile). → `REQ-SHELL-01`, `CC-AC-2`
- [ ] **16.6** Negative scope assertions: no Roles & Permissions route; no operational screens (Dashboard/Students/Attendance); no Teacher/Student/Parent surfaces; no free-form structure CRUD. → `REQ-SHELL-03`, `REQ-SHELL-10`, `REQ-FE-USR-06`, `REQ-FE-AC-07`
- [ ] **16.7** Final build gate: `npm run build`, `npm run lint`, `npm run test -- --run` all green; full test suite passing. → *capability gate*

---

## Evidence Map

| Task(s) | Evidence |
|---|---|
| 1.1–1.2, 8.6, 16.5 | PWA: `manifest.webmanifest` + `sw.js` emitted; `theme_color #2563EB`; installable |
| 1.3 | Vitest + RTL + MSW configured; `npm run test -- --run` executes |
| 2.1–2.5 | `theme/tokens.ts`, `theme/index.ts`, shared primitives; unit test asserts primary color/typography |
| 3.1–3.8 | `core/api/client.ts`, `errors.ts`, interceptors, `AuthProvider`, `TenantProvider`, `access/*`, `dto/*`; unit tests for bearer header, 403 normalization, single-flight refresh, role map, tenant fallback |
| 4.1–4.7 | `shell/*`, `App.tsx`, `main.tsx`; route-table + sidebar + switcher + Forbidden/NotFound tests; demo UI removed |
| 5.1–5.7 | Auth screens + MSW tests; post-activation → login; OTP error/re-request; no login 2FA |
| 6.1–6.6 | C-01 screens + MSW tests for clients, institution types, transfers, client users, institutions, org units |
| 7.1–7.6 | C-02 screens + tests; lookups-sourced dropdowns; no Roles & Permissions route |
| 8.1–8.7 | Phase 1 role matrix, 403, tenant-isolation, responsive, typed-DTO, PWA, build gate |
| 9.1, 10.1–10.7 | Academic DTOs + screens + tests; no direct structure CRUD |
| 11.1–11.4 | Config screens + tests; resolve fallback; audit; backend-validation error |
| 12.1–12.4 | Phase 2 verification + build gate |
| 13.1–13.4 | Fees screens + tests; R6 cohort dependency flag |
| 14.1–14.4, 15.1 | Homework screens + tests; management-roles-only; fees/homework DTOs |
| 15.2–15.5 | Phase 3 verification + build gate |
| 16.1–16.7 | Cross-cutting final verification + capability gate |

## Requirements Coverage

| Requirement | Task(s) |
|---|---|
| REQ-SHELL-01 | 1.1, 1.2, 8.6, 16.5 |
| REQ-SHELL-02 | 2.1, 2.2, 2.3, 2.4, 2.5, 4.6 |
| REQ-SHELL-03 | 3.7, 4.2, 7.6, 8.1, 12.3, 15.4, 16.1, 16.6 |
| REQ-SHELL-04 | 4.1 |
| REQ-SHELL-05 | 3.6, 4.3 |
| REQ-SHELL-06 | 3.3, 3.4, 3.5, 4.5 |
| REQ-SHELL-07 | 3.2, 3.3, 4.4, 8.2 |
| REQ-SHELL-08 | 3.1, 3.6, 8.3, 12.3, 15.4, 16.2 |
| REQ-SHELL-09 | 3.8, 8.5, 9.1, 15.1, 16.4 |
| REQ-SHELL-10 | 3.7, 8.1, 16.1, 16.6 |
| REQ-SHELL-11 | 4.7 |
| REQ-SHELL-12 | 2.4, 8.4, 12.4, 15.4, 16.3 |
| REQ-FE-AUTH-01 | 5.1 |
| REQ-FE-AUTH-02 | 5.2 |
| REQ-FE-AUTH-03 | 5.3 |
| REQ-FE-AUTH-04 | 5.4 |
| REQ-FE-AUTH-05 | 5.5 |
| REQ-FE-AUTH-06 | 4.3, 5.6 |
| REQ-FE-AUTH-07 | 3.3 |
| REQ-FE-AUTH-08 | 5.7 |
| REQ-FE-TI-01 | 6.1 |
| REQ-FE-TI-02 | 6.2 |
| REQ-FE-TI-03 | 6.3 |
| REQ-FE-TI-04 | 6.4 |
| REQ-FE-TI-05 | 6.5 |
| REQ-FE-TI-06 | 6.6 |
| REQ-FE-USR-01 | 7.1 |
| REQ-FE-USR-02 | 7.2 |
| REQ-FE-USR-03 | 7.3 |
| REQ-FE-USR-04 | 7.4 |
| REQ-FE-USR-05 | 7.5 |
| REQ-FE-USR-06 | 7.6, 16.6 |
| REQ-FE-AC-01 | 10.1 |
| REQ-FE-AC-02 | 10.2 |
| REQ-FE-AC-03 | 10.3, 12.1 |
| REQ-FE-AC-04 | 10.4 |
| REQ-FE-AC-05 | 10.5 |
| REQ-FE-AC-06 | 10.6 |
| REQ-FE-AC-07 | 10.7, 12.1, 16.6 |
| REQ-FE-CFG-01 | 11.1 |
| REQ-FE-CFG-02 | 11.2 |
| REQ-FE-CFG-03 | 11.3 |
| REQ-FE-CFG-04 | 11.4 |
| REQ-FE-FEE-01 | 13.1 |
| REQ-FE-FEE-02 | 13.2 |
| REQ-FE-FEE-03 | 13.3 |
| REQ-FE-FEE-04 | 13.4, 15.3 |
| REQ-FE-HW-01 | 14.1 |
| REQ-FE-HW-02 | 14.2 |
| REQ-FE-HW-03 | 14.3 |
| REQ-FE-HW-04 | 14.4 |

---

## Definition of Done (capability)

All three phases applied and verified; every task checkbox ticked with its evidence produced; `npm run build`, `npm run lint`, and `npm run test -- --run` pass; `verify.md` records the role-fixture matrix, friendly-403, tenant-isolation, responsive sweep, typed-DTO, and PWA checks; scope guards (no Roles & Permissions screen, no operational screens, no native app, no backend changes) hold.
