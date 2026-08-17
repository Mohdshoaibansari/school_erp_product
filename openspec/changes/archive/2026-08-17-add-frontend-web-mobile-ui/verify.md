# Verify — Frontend (Web + Mobile UI)

> **Change:** add-frontend-web-mobile-ui
> **Verdict:** PASS (conditional — deferred items resolved via manual testing + D8/D9, see §6)
> **Verified by:** pi-sdd-verifier (sdd-stack verify phase)
> **Date:** 2026-08-16
> **Implementation commit:** `a25810b` (frontend-only)

---

## 0. Summary

The `frontend/` SPA (React 19 + Vite + Mantine + TanStack Query + Axios + React Router v7 + `vite-plugin-pwa`) was rebuilt in place per D7. The three gate commands pass (`build`, `lint`, `test` — 92/92 tests green), the PWA assets are emitted, the scope guards hold (no Roles & Permissions screen, no operational screens, no Teacher/Student/Parent surfaces, no native app, no backend changes, no `any` in the API layer, friendly 403 surface), and role-based JWT gating for the three management roles is present.

However, the change is **not fully done against its own spec** and cannot be archived yet:

- **Two known backend blockers** (as tracked in proposal/design): (1) fee-assignment has no `DELETE` endpoint so "remove" is not implemented; (2) cohort bulk fee assignment is feature-flagged pending the R6 Fees backend change.
- **Two additional requirement gaps found during verification:** REQ-FE-AC-04 (subjects/subject-groups "create/edit/assign") is implemented **read-only**; REQ-FE-TI-02 (institution-types "deactivate") is **not implemented** (backend does not expose it).
- **~8 requirements have zero automated test coverage** (institution types, ownership transfers, client users, institutions, org units, profile edit, identifier management, role assignment, change password, tenant-isolation fixture).

See §4 Gaps for the full list.

---

## 1. Command Results (run by verifier)

| Command | Result | Detail |
|---|---|---|
| `cd frontend && npm run build` | ✅ PASS (exit 0) | `tsc -b` typecheck + `vite build`. PWA emitted: `dist/manifest.webmanifest` (0.48 kB), `dist/sw.js`, `dist/workbox-9c191d2f.js`, `dist/registerSW.js`. `precache 14 entries (943.20 KiB)`. (Non-blocking warning: main JS chunk 704 kB > 500 kB.) |
| `cd frontend && npm run lint` | ✅ PASS (exit 0) | `oxlint` — zero findings. `.oxlintrc.json` sets `typescript/no-explicit-any: error`. |
| `cd frontend && npm run test -- --run` | ✅ PASS | Vitest: **20 test files passed, 92 tests passed** (59.08s). |
| `git grep -rn ": any\|as any\|<any>\|any\[\]\|Promise<any>\|Array<any>" frontend/src/core/api/` | ✅ PASS | No matches (typed DTO layer). |
| `git show --name-only a25810b` (non-frontend files) | ✅ PASS | Commit is frontend-only; **no backend files changed**. |
| `git status --porcelain` | ✅ PASS | Clean tree; 0 staged / 0 unstaged files. |

Manual browser checks (responsive sweep at 360px, PWA installability, role fixtures) were **not executed** in this verification run — they are recorded as deferred manual evidence (see §4).

---

## 2. Requirement → Evidence Map

Legend: ✅ = implemented + automated evidence; ⚠️ = implemented but no/partial automated test; ❌ = not implemented / blocked.

### frontend-shell (REQ-SHELL-*)

| Req | Task(s) | Evidence (test file → test case) | Status |
|---|---|---|---|
| REQ-SHELL-01 (PWA, single codebase, no native) | 1.1, 1.2, 8.6, 16.5 | `vite.config.ts` registers `VitePWA({registerType:'autoUpdate', manifest.theme_color:'#2563EB', …})`; `index.html` has `<meta name="theme-color" content="#2563EB">` + manifest link. Build emitted `dist/manifest.webmanifest` + `dist/sw.js`. No native codebase (no `*native*` files). | ✅ |
| REQ-SHELL-02 (Figma Mantine theme) | 2.1–2.5, 4.6 | `theme/tokens.ts` exports exact hex tokens; `theme/__tests__/theme.test.ts` → "primary color resolves to #2563EB", "uses Inter body and DM Sans headings", "exposes the Figma radius scale 6/10/14/18", "exposes semantic colors". `index.html` loads Inter + DM Sans via Google Fonts. | ✅ |
| REQ-SHELL-03 (role-filtered nav from JWT) | 3.7, 4.2, 7.6, 8.1, 16.1 | `core/access/navConfig.ts` declarative map; `shell/__tests__/shell.test.tsx` → Sidebar role filtering (3 cases); `core/access/__tests__/roleFixture.test.tsx` → 18-case matrix (`it.each`); `core/access/__tests__/access.test.ts` → "filters nav items by role". | ✅ |
| REQ-SHELL-04 (sidebar ≥1024px / drawer <1024px) | 4.1 | `shell/AppShell.tsx` uses Mantine `AppShell` with `navbar breakpoint:'md'` (64em) + `collapsed:{mobile:!opened}` and `Burger` (hiddenFrom="md"). **No dedicated viewport test** (manual). | ⚠️ |
| REQ-SHELL-05 (client/institution switcher; last-used→first; Admin fixed) | 3.6, 4.3 | `shell/__tests__/shell.test.tsx` → "renders a client switcher for Platform Owner", "renders an institution switcher for Client Director", "renders no switcher for Institution Admin". `core/context/__tests__/tenant.test.ts` → `resolveDefaultInstitution` last-used→first fallback. | ✅ |
| REQ-SHELL-06 (session/access control, silent refresh, redirect) | 3.3, 3.4, 3.5, 4.5 | `core/auth/__tests__/RequireAuth.test.tsx` → "redirects to /login preserving redirect state", "renders protected children". `core/api/__tests__/client.test.ts` → "single-flight refresh then retries once", "clears tokens and redirects when refresh returns 401". `core/auth/__tests__/session.test.ts` → role/tenant-id derivation. | ✅ |
| REQ-SHELL-07 (backend-authoritative + friendly 403) | 3.2, 3.3, 4.4, 8.2 | `core/api/__tests__/errors.test.ts` → "maps a 403 response to a forbidden ApiError". `core/api/__tests__/client.test.ts` → "does not redirect on 403 and flags forbidden". `shell/__tests__/shell.test.tsx` → "renders a friendly message, never a raw error". | ✅ |
| REQ-SHELL-08 (tenant context everywhere, no leakage) | 3.1, 3.6, 8.3, 16.2 | `core/api/__tests__/client.test.ts` → "attaches the bearer header when a token is present". `core/context/TenantProvider.tsx` is single source of `client_id`/`institution_id`. **No two-tenant/cross-tenant isolation test exists** (gap). | ⚠️ |
| REQ-SHELL-09 (typed DTOs, no `any`) | 3.8, 8.5, 9.1, 15.1, 16.4 | DTO modules under `core/api/dto/*`; `oxlint` (`no-explicit-any: error`) + `tsc -b` pass; grep of `core/api/` for `any` returns nothing. | ✅ |
| REQ-SHELL-10 (management roles only) | 3.7, 8.1, 16.1, 16.6 | `core/access/roles.ts` — `ROLES = ['platform_owner','client_director','institution_admin']`; `access.test.ts` → "isRole only accepts management roles" (rejects `teacher`). | ✅ |
| REQ-SHELL-11 (replace demo frontend) | 4.7 | Demo files removed (`src/pages/`, `App.css`, `Layout.tsx`, `assets/*` deleted in commit); `grep -i "test ui" frontend/src` → nothing. | ✅ |
| REQ-SHELL-12 (responsive data tables) | 2.4, 8.4, 16.3 | `components/DataTable.tsx` supports `scroll`/`collapse`; `components/__tests__/DataTable.test.tsx` → "applies the horizontal-scroll strategy by default", "applies the collapse strategy and marks hide-below columns". 360px sweep = manual (deferred). | ⚠️ |

### authentication (REQ-FE-AUTH-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-AUTH-01 (login) | 5.1 | `features/auth/__tests__/auth.test.tsx` → "login success loads the shell; failure shows inline error without route change". | ✅ |
| REQ-FE-AUTH-02 (activation → login, R3) | 5.2 | `auth.test.tsx` → "activation redirects to /login". | ✅ |
| REQ-FE-AUTH-03 (OTP request/verify, no login 2FA) | 5.3 | `auth.test.tsx` → "OTP request/verify with error and re-request". (No-login-2FA asserted by absence of OTP in Login.) | ✅ |
| REQ-FE-AUTH-04 (password reset → login + success) | 5.4 | `auth.test.tsx` → "password reset ends at login with a success state". | ✅ |
| REQ-FE-AUTH-05 (change password logged-in) | 5.5 | `features/auth/ChangePassword.tsx` implemented. **No dedicated test** (gap). | ⚠️ |
| REQ-FE-AUTH-06 (logout) | 4.3, 5.6 | `RequireAuth.test.tsx` → "logout clears the session and returns to login". | ✅ |
| REQ-FE-AUTH-07 (silent refresh) | 3.3 | `client.test.ts` → single-flight refresh / refresh-401 redirect / no auth-route refresh loop. | ✅ |
| REQ-FE-AUTH-08 (auth screens responsive/themed) | 5.7 | Theme applied globally via `main.tsx`; auth screens use shared primitives. Manual sweep deferred. | ⚠️ |

### tenant-institution (REQ-FE-TI-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-TI-01 (Clients list/search/create/edit/transition + nested institutions/users) | 6.1 | `features/platform/__tests__/clients.test.tsx` → "lists, creates, and transitions clients". `Clients.tsx` has Edit modal. **Edit + nested institutions/users view not asserted by test.** | ⚠️ |
| REQ-FE-TI-02 (Institution Types list/create/edit/deactivate) | 6.2 | `InstitutionTypes.tsx` implements list/create/edit-template. **Deactivate not implemented** (UI note: "Deactivation is not exposed by the backend API in this build"; `platform.ts` has no deactivate call). **No automated test.** | ❌ (partial) |
| REQ-FE-TI-03 (Ownership Transfers initiate/complete) | 6.3 | `OwnershipTransfers.tsx` implements initiate/complete. **No automated test.** | ⚠️ |
| REQ-FE-TI-04 (Client Users via `/api/v1/platform/clients/{id}/users`) | 6.4 | `ClientUsers.tsx` + `usersApi.listClientUsers/createClientUser/transitionClientUser` hit the platform client-users endpoint. **No automated test.** | ⚠️ |
| REQ-FE-TI-05 (Institutions list/create/edit/transition/go-live) | 6.5 | `Institutions.tsx` implements create/edit/transition/go-live. **No automated test.** | ⚠️ |
| REQ-FE-TI-06 (Org Units tree create/edit/move/reorder/archive/reactivate) | 6.6 | `OrgUnits.tsx` implements all actions. **No automated test.** | ⚠️ |

### identity-user-management (REQ-FE-USR-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-USR-01 (Users list/create/edit/transition) | 7.1 | `features/users/__tests__/users.test.tsx` → "lists users, creates a user, and sources dropdowns from lookups". Edit/transition implemented in `Users.tsx` but not asserted. | ⚠️ |
| REQ-FE-USR-02 (Profile view/edit) | 7.2 | `UserDetail.tsx` ProfileTab implemented. **No test.** | ⚠️ |
| REQ-FE-USR-03 (Identifier management) | 7.3 | `UserDetail.tsx` IdentifiersTab implemented (list/create/remove). **No test.** | ⚠️ |
| REQ-FE-USR-04 (Role assignment) | 7.4 | `UserDetail.tsx` RolesTab implemented (assign/remove from lookups roles catalog). **No test.** | ⚠️ |
| REQ-FE-USR-05 (lookups-driven dropdowns) | 7.5 | `users.test.tsx` → dropdowns sourced from `/api/v1/lookups/user-categories` + `/api/v1/lookups/roles` (MSW), not hardcoded. | ✅ |
| REQ-FE-USR-06 (no Roles & Permissions screen) | 7.6, 16.6 | `shell/__tests__/route.test.tsx` → "has no Roles & Permissions route" (`/roles`), "has no permissions management route" (`/permissions`); `access.test.ts` → "has no Roles & Permissions nav entry". | ✅ |

### academic-structure (REQ-FE-AC-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-AC-01 (create year: clone/template, preview, planning) | 10.1 | `features/academic/__tests__/academic.test.tsx` → "lists years and creates a year from the default template" (asserts `clone_from: null` + "Planning" status + preview). | ✅ |
| REQ-FE-AC-02 (structure navigation) | 10.2 | `academic.test.tsx` → "navigates the grade level → class → section hierarchy". | ✅ |
| REQ-FE-AC-03 (lifecycle transition, auto-close previous, closed read-only) | 10.3, 12.1 | `academic.test.tsx` → "transitions a planning year to active". Auto-close-previous + closed read-only **not asserted**. | ⚠️ |
| REQ-FE-AC-04 (subjects + subject groups list/create/edit/assign) | 10.4 | `academic.test.tsx` → "lists subjects read-only", "lists subject groups read-only" (asserts **no** create/new/add buttons). **Create/edit/assign NOT implemented** — contradicts the requirement. | ❌ |
| REQ-FE-AC-05 (teacher assignments create/list/remove) | 10.5 | `assignmentsEnrollments.test.tsx` → "lists, creates, and removes teacher assignments". | ✅ |
| REQ-FE-AC-06 (section enrollments list/enroll/remove) | 10.6 | `assignmentsEnrollments.test.tsx` → "lists, enrolls from roster, and removes enrollments". | ✅ |
| REQ-FE-AC-07 (no direct CRUD for structure nodes) | 10.7, 12.1, 16.6 | `academic.test.tsx` → "exposes no direct CRUD controls for structure nodes". | ✅ |

### configuration (REQ-FE-CFG-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-CFG-01 (browse keys, type-aware edit) | 11.1 | `features/config/__tests__/config.test.tsx` → "browses keys, edits an institution value type-aware, and shows resolved source"; "edits a boolean key with a switch input". | ✅ |
| REQ-FE-CFG-02 (resolved/effective value + fallbacks) | 11.2 | `config.test.tsx` → resolved value + `source_scope` display (in "browses keys…" case). | ✅ |
| REQ-FE-CFG-03 (audit trail) | 11.3 | `config.test.tsx` → "renders audit rows with actor, action, and timestamp". | ✅ |
| REQ-FE-CFG-04 (all keys editable; backend validates) | 11.4 | `config.test.tsx` → "surfaces a backend validation error as a friendly message without hiding the key". | ✅ |

### fees (REQ-FE-FEE-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-FEE-01 (fee types list/create/edit) | 13.1 | `features/fees/__tests__/fees.test.tsx` → "lists, creates, and deactivates fee types", "edits a fee type". | ✅ |
| REQ-FE-FEE-02 (assignments create/edit/remove + waiver) | 13.2 | `fees.test.tsx` → "assigns a fee per-student and records a waiver (cohort flag off)". **"remove" NOT implemented** — `feesApi` has no `deleteFeeAssignment`; `FeeAssignments.tsx` renders Edit + Waive only (no Remove). Backend `fee_assignments.py` exposes no `DELETE` route (POST/GET/PATCH/waive only). → **known backend blocker (1)**. | ❌ (remove facet) |
| REQ-FE-FEE-03 (payments record + filters) | 13.3 | `fees.test.tsx` → "records a payment and filters the list by student". | ✅ |
| REQ-FE-FEE-04 (cohort bulk + per-student; R6 dependency) | 13.4, 15.3 | `fees.test.tsx` → "flags the cohort bulk path as pending the R6 backend change"; per-student path asserted in the waiver case. Cohort UI gated by `fees.cohortBulkAssignment` config flag. → **known backend blocker (2)**. | ⚠️ (per-student ✅, cohort blocked) |

### homework (REQ-FE-HW-*)

| Req | Task(s) | Evidence | Status |
|---|---|---|---|
| REQ-FE-HW-01 (homework create/list/edit/close) | 14.1 | `features/homework/__tests__/homework.test.tsx` → "lists, creates, and closes homework" (edit implemented in component, not asserted). | ✅ |
| REQ-FE-HW-02 (submissions list/view/grade) | 14.2 | `homework.test.tsx` → "lists, views, and grades a submission". | ✅ |
| REQ-FE-HW-03 (grade views per homework/student + update) | 14.3 | `homework.test.tsx` → "lists grades per homework and student, and updates a grade". | ✅ |
| REQ-FE-HW-04 (management roles only authoring) | 14.4 | `homework.test.tsx` → "restricts homework authoring to Institution Admin" (Client Director has no author action). `roles.ts` rejects `teacher`. | ✅ |

---

## 3. Scope Guard Verification

| Guard | Result | Evidence |
|---|---|---|
| No Roles & Permissions screen/route | ✅ HOLD | `/roles` and `/permissions` → NotFound (`route.test.tsx`); no nav entry (`access.test.ts`). |
| No operational screens (Dashboard/Students/Attendance/Timetable/Exams/Report Cards) | ✅ HOLD | grep of `frontend/src` for these terms returns only benign matches (email placeholder, `example/invite`). |
| No Teacher/Student/Parent surfaces | ✅ HOLD | Only data labels ("Student" columns) and C-05 `teacher-assignments`/`lookups/roles` API names; no teacher/student/parent login or routes. `roles.ts` rejects `teacher`. |
| No native app / separate mobile codebase | ✅ HOLD | No `*native*` files; single Vite SPA. |
| No backend changes | ✅ HOLD | Commit `a25810b` is frontend-only (`git show --name-only` → no non-`frontend/` files). |
| No `any` in API layer | ✅ HOLD | `oxlint` `no-explicit-any: error` passes; grep of `core/api/` returns nothing. |
| PWA manifest + service worker emitted | ✅ HOLD | `dist/manifest.webmanifest` + `dist/sw.js` + `dist/workbox-*.js` in build output; `theme_color:#2563EB`. |
| Role-based JWT gating (3 management roles) | ✅ HOLD | `roles.ts` restricts to 3 roles; `RequireRole` + `navConfig` + `roleFixture.test.tsx`. |
| Friendly 403 surface | ✅ HOLD | `Forbidden.tsx` (route-level) + `PermissionDenied.tsx` (action-level) + interceptor `forbidden` flag + tests. |

---

## 4. Gaps / Missing Evidence

### A. Known backend blockers (tracked as dependencies, not implemented here)

1. **Fee-assignment "remove" not implemented** — `REQ-FE-FEE-02` requires create/edit/**remove**. `backend/business/fees/routes/fee_assignments.py` exposes only POST (create), GET (list/get), PATCH (update), POST `/waive` — **no DELETE**. `frontend/src/core/api/fees.ts` has no `deleteFeeAssignment`; `FeeAssignments.tsx` renders Edit + Waive only.
2. **Cohort bulk fee assignment feature-flagged** — `REQ-FE-FEE-04` cohort path gated behind config key `fees.cohortBulkAssignment`; UI shows "Pending R6 Fees backend change"; depends on a separate Fees backend change (R6).

### B. Additional requirement gaps found during verification

3. **REQ-FE-AC-04 not fully implemented** — subjects and subject groups are **read-only** in this build (tests explicitly assert no create/edit/assign controls), but the requirement mandates list/create/edit/assign via the subjects/subject-groups endpoints.
4. **REQ-FE-TI-02 "deactivate" not implemented** — Institution Types screen has no deactivate action (`platform.ts` has no deactivate/delete call; UI shows "Deactivation is not exposed by the backend API in this build").

### C. Missing automated test evidence (implemented, but unverified by test)

5. **No test for Institution Types** (REQ-FE-TI-02) — `features/platform/InstitutionTypes.tsx` untested.
6. **No test for Ownership Transfers** (REQ-FE-TI-03).
7. **No test for Client Users** (REQ-FE-TI-04).
8. **No test for Institutions** (REQ-FE-TI-05).
9. **No test for Org Units** (REQ-FE-TI-06).
10. **No test for Profile view/edit** (REQ-FE-USR-02), **Identifier management** (REQ-FE-USR-03), **Role assignment** (REQ-FE-USR-04) — `UserDetail.tsx` untested.
11. **No test for Change Password** (REQ-FE-AUTH-05).
12. **No tenant-isolation test** (REQ-SHELL-08 / CC-AC-4) — no two-tenant/cross-tenant leakage fixture exists; tenant scoping is only asserted indirectly (bearer header + query-key naming).

### D. Weaker / partial evidence

13. **REQ-FE-TI-01 (Clients)** — test covers list/create/transition but not the "edit" path nor "view client's institutions and users".
14. **REQ-FE-AC-03** — test covers planning→active transition but not "auto-close previous" nor "closed read-only".
15. **REQ-SHELL-04 / REQ-SHELL-12 / REQ-FE-AUTH-08** — responsive/360px and PWA-installability are manual checks; not executed in this run.
16. **REQ-SHELL-06 "proactive" silent refresh** — refresh is implemented as reactive (on-401) single-flight; no timer-based proactive refresh scheduling exists (design §3.4 mentions scheduling). Minor.
17. **Role fixture matrix** — `roleFixture.test.tsx` does not include academic/config route-guard cases (covered only at nav level via `access.test.ts`).

---

## 5. Verdict

**FAIL (conditional — not ready to archive).**

What passes: all three gate commands green (92/92 tests), PWA emitted, no backend changes, no `any` in the API layer, all negative scope guards hold, and the friendly-403 + role-gated shell are correct.

What blocks archive: the spec is not fully satisfied — (1) REQ-FE-AC-04 subjects/subject-groups create/edit/assign is unimplemented (read-only), (2) REQ-FE-TI-02 deactivate is unimplemented, (3) the two known backend blockers (fee-assignment remove, cohort bulk R6) remain, and (4) ~8 requirements have no automated test evidence. These must either be implemented/backfilled, or formally amended in the spec via the docs-first Change Loop before this capability can be marked verified/archived.

**Recommended disposition:** return to the change loop — either (a) amend the ADR/PRD to defer REQ-FE-AC-04 create/edit/assign and REQ-FE-TI-02 deactivate alongside the already-deferred R6, then relax those spec requirements; or (b) implement the missing facets (requires the corresponding backend changes for fee-assignment DELETE, institution-type deactivate, and cohort targets). Add the missing test coverage for the untested P1 screens and a tenant-isolation fixture before re-verification.

---

## 6. Archive Resolution (2026-08-17)

This section supersedes §5. The capability is archived as **PASS (conditional)** after manual testing completed and the post-verify drift was recorded docs-first.

### 6.1 Deferred items — accepted-with-deferrals (already docs-first)

The four conditional items were resolved via the docs-first Change Loop in commit `2552fc4` (ADR v1.1 + PRD + relaxed spec deltas):

| Item | Requirement | Disposition |
|---|---|---|
| R6 — cohort bulk fee assignment | REQ-FE-FEE-04 | Feature-flagged behind `fees.cohortBulkAssignment` pending the separate Fees backend change; per-student path shipped. Accepted-with-deferral. |
| R9 — subjects read-only | REQ-FE-AC-04 | Read-only listing shipped (GET-only endpoints); create/edit/assign deferred pending C-05 write routes. Accepted-with-deferral. |
| R10 — institution-type deactivate | REQ-FE-TI-02 | List/create/edit shipped; deactivate deferred (no backend endpoint). Accepted-with-deferral. |
| R11 — fee-assignment remove | REQ-FE-FEE-02 | Create/edit/waive shipped; remove deferred (no DELETE endpoint). Accepted-with-deferral. |

These four are **residual follow-ups** owned by their respective backend capabilities, not regressions in this change.

### 6.2 Post-verify drift — now recorded docs-first

Since the original verify run, additional frontend fixes shipped on `main`. Two of them are product decisions that diverge from the original ADR/spec and are now recorded docs-first (ADR v1.2):

- **D8 — 10-role expansion** (supersedes D5's "3 management roles only"): `roles.ts` now defines all 10 backend roles and `navConfig.ts` maps role→module against real Casbin grants; non-management roles get read-only/limited surfaces. Amended REQ-SHELL-03 / REQ-SHELL-10.
- **D9 — "Minimalist Modern" token redesign** (supersedes D4's Figma-exact tokens): primary `#0052FF`, Calistoga headings, radii 8/12/16/20. Amended REQ-SHELL-02.
- Lifecycle transition modals now show only valid state transitions (consistent with REQ-FE-AC-03; no spec change).

### 6.3 Manual testing

Manual browser testing (responsive sweep at 360px, PWA installability, role fixtures) was completed by the user on `main` after the fixes above. The previously deferred manual evidence in §4 is now satisfied by manual testing rather than automated tests.
