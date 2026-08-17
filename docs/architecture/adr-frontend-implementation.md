# Frontend (Web + Mobile UI) — Architecture Decision Record

> **Status:** Final
> **Version:** 1.2
> **Last Updated:** 2026-08-17
> **Author:** AI (grill session with product owner)
> **Source:** `adr-platform-tech-stack.md` (§2 "Frontend: Deferred", §7 "Frontend framework"); backend surface map; Figma Make export review; grill-session decisions
> **Purpose:** Lock the frontend architecture for the first UI-bearing build, resolving the deferred frontend decision in `adr-platform-tech-stack.md`.
> **Cross-References:**
> - [Platform Technology Stack](./adr-platform-tech-stack.md)
> - [Architecture v1](./architecture-v1.md)
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md)

---

## 1. Context

The backend is API-first and all of the following capabilities are **implemented and archived**: C-01 Tenant & Institution Management, C-02 Identity & User Management, C-03 Authentication, C-04 Authorization (Casbin RBAC + ABAC), C-05 Academic Structure, C-08 Configuration Framework, plus the **Fees** and **Homework** business modules. `adr-platform-tech-stack.md` explicitly deferred the frontend framework choice to "the first UI-bearing capability" — this is that capability.

Two frontend inputs exist today:

1. **`frontend/` (repo root)** — a throwaway "School ERP — Test UI" (React 19 + Vite + Mantine + TanStack Query + Axios + React Router v7). It covers Login, Platform (Clients/Institutions/Users), Fees, and Homework only; it has no academic-structure, roles/permissions, or config screens.
2. **`School ERP UI Design.zip`** — not static images, but a **Figma Make-generated React app** (Vite + react-native-web + Tailwind). It establishes a clean, modern design system and a responsive app shell, but its *real* screens are operational (Dashboard, Students, Attendance, Fees), most of which have **no backend yet**, while the built admin/config modules have almost no screens in it.

The product owner ran a structured grill session and locked seven decisions (D1–D7 below), which this ADR records.

## 2. Decision

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | **Scope** | Build the frontend for the **built backend modules only**: C-01 Tenant/Institution, C-02 Users, C-03 Auth, C-04 Roles/Permissions, C-05 Academic Structure, C-08 Config, Fees, Homework. | The Figma's operational screens (Students, Attendance) have no backend. Figma is used as the **design-system + app-shell reference**, not as the screen inventory. |
| **D2** | **Delivery target** | **Responsive web + PWA** (single codebase). No native app in this build. | One codebase that works in desktop and mobile browsers and is installable as a PWA; no app-store overhead. |
| **D3** | **UI stack** | **React 19 + TypeScript + Vite + Mantine + TanStack Query + Axios + React Router v7**, plus `vite-plugin-pwa` for PWA support. | Resolves `adr-platform-tech-stack.md`'s deferred frontend choice. Retains the proven stack already in `frontend/`; Mantine gives mature table/form/modal components. |
| **D4** | **Design system** | **Match the Figma design system closely**, recreated as a Mantine theme. Tokens: primary `#2563EB`; backgrounds `#F1F5F9`/`#FFFFFF`; text `#0F172A`/`#475569`/`#94A3B8`; semantic success `#16A34A`, warning `#D97706`, danger `#DC2626`; typography Inter (body) + DM Sans (headings); radii 6/10/14/18; card, table, and status-pill patterns per the Figma. | The product owner wants visual polish to match the Figma; no new design invention. **Superseded/amended by D9 (Minimalist Modern tokens).** |
| **D5** | **Roles & access** | **Management roles only**: Platform Owner, Client Director, Institution Admin. Navigation and actions are **role-gated from the JWT `roles` claim** (no C-04 authz routes consumed). The backend stays authoritative via Casbin RBAC+ABAC; a blocked action renders a friendly permission-denied message. | These are the roles the built modules serve. Non-management roles (Teacher, Student, Parent) are deferred until operational modules exist. **Superseded/amended by D8 (all 10 backend roles).** |
| **D6** | **Sequencing** | **Three phases by domain**: Phase 1 = app shell + auth + tenant/institution (C-01) + users & roles (C-02/C-04); Phase 2 = academic structure (C-05) + config (C-08); Phase 3 = fees + homework. | Matches the repo's capability-at-a-time discipline and keeps each phase reviewable. |
| **D7** | **Replace existing frontend** | Replace `frontend/` **completely**; keep only the Mantine+Vite base, rebuild pages. | The demo UI is throwaway; the product owner authorized full replacement. |
| **D8** | **Role gating (10 roles)** | **Expands from 3 management roles to all 10 backend roles** (supersedes D5's "3 roles only"): `platform_owner`, `client_director`, `institution_admin`, `admin`, `teacher`, `hod`, `principal`, `student`, `parent`, `staff`. Roles are derived from the JWT roles array (case-insensitively normalized) with `user_tier`/`is_platform_owner` fallback, matching the backend middleware's DB role lookup. Each role is gated to the nav items matching its real Casbin `role_permission` grants (verified against migrations 002-020). Non-management roles get read-only or limited surfaces; no C-04 routes are still consumed. | During manual testing, admin/teacher login succeeded but showed "You don't have permission" because `deriveRoles()` filtered non-management roles out of the JWT/DB role set. The backend (C-02 migration 002 + Casbin) actually provisions 10 roles. D5 is amended, not deleted — the 3 management roles remain, but the surface now includes the 7 institution roles with permission-accurate gating. |
| **D9** | **Design tokens (Minimalist Modern)** | **Adopt the "Minimalist Modern" token redesign** (supersedes D4's Figma-exact tokens): primary `#0052FF` (blue palette `#EEF4FF`→`#002D91`), body Inter, headings Calistoga (Georgia fallback), mono JetBrains Mono, radii sm/md/lg/xl = `8/12/16/20px`, app background `#FAFAFA`, surface `#FFFFFF`, muted `#F1F5F9`, text primary `#0F172A` / secondary `#64748B` / muted `#94A3B8`, border `#E2E8F0`, success `#16A34A`, warning `#D97706`, danger `#DC2626`. | A post-Figma visual redesign shipped in the code (`tokens.ts` + `REDESIGN_NOTES.md`) replacing the Figma-derived palette/typography/radii. D4 is amended; REQ-SHELL-02 now asserts `#0052FF` / Calistoga / radii 8-12-16-20. |

### Open-question resolutions (from PRD §7, resolved 2026-08-16)

| Res | Question | Resolution |
|---|---|---|
| R1 | Roles & permissions screen (C-04) | **Deferred entirely** — no C-04 routes are consumed; the Roles & Permissions screen is out of scope. UI gating is role-based from the JWT `roles` claim instead. |
| R2 | OTP use cases | **Activation + password-reset only.** No login 2FA step-up in this build. |
| R3 | Post-activation landing | **Land on login** — activation completes, then the user signs in manually. |
| R4 | Institution switcher default | **Last-used institution (persisted)**, falling back to the first institution when none is remembered. |
| R5 | Config key editability | **All keys editable** through the C-08 UI; unsafe edits are blocked by backend validation, not the UI. |
| R6 | Fee assignment target unit | **Cohort bulk + per-student** — assign a fee to a section/grade in one action with per-student overrides. ⚠️ Depends on the Fees backend supporting cohort-level targets. |
| R7 | Homework author | **Management roles only** — Institution Admin authors/grades homework; teacher UI deferred with the teacher role. |
| R8 | Permission-denied handling | **Friendly 403 UI** — when the backend blocks an action the role-based UI allowed (e.g., future ABAC scope), render a clear permission-denied message, never a raw error. |
| R9 | Subjects & subject groups (C-05) | **Read-only in this build** — the backend exposes GET-only lookups (`/subjects`, `/subject-groups`); create/edit/assign is deferred until C-05 exposes write routes. |
| R10 | Institution-type deactivate (C-01) | **Deferred** — the backend has no deactivate endpoint; the UI offers list/create/edit only. |
| R11 | Fee-assignment remove (Fees) | **Deferred** — the backend `fee-assignments` router has no DELETE; the UI offers create/edit/waive only. |

## 3. Consequences

**Positive:**
- Single codebase serves desktop + mobile + installable PWA — no parallel native maintenance.
- Mantine + the Figma theme yields a polished, consistent UI with minimal custom component work.
- Role-based gating from the JWT keeps the frontend simple (no C-04 route dependency); the backend still enforces Casbin RBAC+ABAC on every request, so no security is lost.
- Phased-by-domain delivery aligns with the existing sdd-stack workflow and allows per-phase spec/design/verify/archive.

**Negative / cost:**
- Matching the Figma closely requires theme + component-pattern work up front (card, table, status-pill restyling).
- The built modules are admin/config-heavy; there is no polished "landing" experience until later phases (Dashboard is out of scope this build).
- Responsive tables are hard on phones; data tables must collapse/scroll on narrow screens (a known weakness of the Figma output).
- **R6 may require a backend change.** Cohort-level fee assignment depends on the Fees backend supporting section/grade targets; if the current `fee_assignment` model is per-student only, a separate Fees backend change is required before Phase 3 (flagged in the PRD).
- **Four capabilities are UI-deferred pending backend routes** (R6 + R9–R11): subjects/subject-groups create/edit/assign, institution-type deactivate, fee-assignment remove, and cohort bulk fee assignment — all require backend routes that do not exist yet.
- **D8 amends D5 (role scope)** — role gating now covers all 10 backend roles; the three management roles keep their full surfaces, while the seven institution roles (admin, teacher, hod, principal, student, parent, staff) receive read-only/limited surfaces gated by their real Casbin permissions.
- **D9 amends D4 (design system)** — the shipped tokens are the "Minimalist Modern" set (`#0052FF`/Calistoga/radii 8-12-16-20). Beyond tokens, the redesign restyles the app shell: deep-slate `#0F172A` grouped role-aware navigation with active gradient, a glassy header with context selectors, page headers, elevated data tables, refined form/status/stat cards, and a redesigned login screen (inverted textured hero); focus states, touch targets, and `prefers-reduced-motion` are supported.

## 4. Model

```
              Responsive SPA (React 19 + Vite) — installable PWA
  ┌──────────────────────────────────────────────────────────────┐
  │ React Router v7 (routes per module, deep-linkable)           │
  │   ┌────────────────────────────────────────────────────────┐ │
  │   │ Role-gated AppShell (collapsible sidebar +       │ │
  │   │ top header; off-canvas drawer < 1024px)                │ │
  │   │   · nav items filtered by Casbin permissions           │ │
  │   │   · institution switcher (client_id / institution_id)  │ │
  │   └────────────────────────────────────────────────────────┘ │
  │   API layer (Axios + TanStack Query) — typed DTOs, no `any` │
  │   · bearer JWT; 401 → /login                                │
  │   · Auth flows: login, OTP, password reset/change, refresh  │
  │   Mantine theme = Minimalist Modern tokens (primary #0052FF, Calistoga, …)  │
  └──────────────────────────────────────────────────────────────┘
                        │ HTTPS  /api/v1/*   Host: <slug>.app.example.com
                        ▼
        FastAPI backend (Supabase Auth JWT → TenantContext
                         → Casbin RBAC+ABAC → tenant repo + RLS)
```

## 5. Constraints

1. **Single codebase.** Responsive web + PWA only; no separate mobile repo or native app in this build.
2. **Backend-authoritative authorization.** The frontend hides/shows based on JWT roles; it never enforces access. Every protected action is still checked by the backend (Casbin RBAC+ABAC), and a blocked action renders a friendly 403 message.
3. **Match Figma tokens.** No new design system; the Mantine theme must implement the Figma color/typography/spacing/radius tokens and component patterns.
4. **Type-safe API layer.** All API responses map to typed DTOs (mirroring backend DTOs); `any` is disallowed in the API layer.
5. **Tenant context everywhere.** The UI must carry `client_id`/`institution_id` from the JWT + institution switcher; every request is tenant-scoped.
6. **Replace `frontend/` in place.** Keep the Vite + Mantine base, discard demo pages and the "Test UI" header.
7. **Capability-at-a-time.** Each domain phase is fed to sdd-stack (PRD → spec → design → tasks → apply → verify → archive) before starting the next.

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| **Expo / React Native** (web + iOS + Android from one codebase) | Native app-store distribution was not requested; heavier tooling; responsive web + PWA satisfies the stated "web and mobile" need now. |
| **react-native-web** (the stack Figma Make generated) | Unnecessary native portability today; Mantine is a mature web component library already proven in the repo and can be themed to the Figma. |
| **Tailwind + shadcn/ui** | Would rebuild tables/forms/modals by hand; Mantine already ships them and only needs a theme override to match the Figma. |
| **Next.js + Tailwind** | SSR/SEO and server rendering are overkill for an internal, authenticated ERP admin SPA; Vite SPA + PWA is sufficient. |
| **Reuse the Figma Make app as-is** | No backend integration, local `useState` navigation (no routing), only 4 of ~20 pages real, and its operational screens aren't backed by built modules. |
| **Extend the existing demo UI** | It is explicitly a throwaway test UI with inconsistent structure; the product owner authorized full replacement. |
| **Permission-based UI gating (consume C-04 read routes)** | Rejected — requires C-04 to expose read endpoints and couples the UI to the Casbin permission catalog; role-gating from the JWT covers the management-role UI with no backend change. |

## 7. Future Evolution

- **Native app** — if app-store distribution (iOS/Android) becomes a requirement, evaluate Expo/React Native; this ADR would be amended, not silently extended.
- **More roles** — Teacher, Student, Parent dashboards when operational backend modules (Students, Attendance, etc.) are built.
- **Operational screens** — the Figma's Dashboard, Students, and Attendance screens are out of scope now and become their own capabilities when their backend exists.
- **PWA depth** — offline caching and background sync are deferred; `vite-plugin-pwa` is included now so they can be added later without a rewrite.
- **SSR / public pages** — if public marketing or SEO pages are needed, revisit Next.js for the public surface only (the authenticated app stays a SPA).
- **Permission-driven navigation** — if finer-grained (permission/ABAC-scope) UI gating is ever needed, revisit exposing C-04 read routes; today role-based JWT gating + friendly 403 is sufficient.

---

> **ADR Status:** This ADR resolves the "Frontend: Deferred" entry in `adr-platform-tech-stack.md` and is the decisional input for the frontend capability's PRD → spec → design → tasks flow.
