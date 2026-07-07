# Platform Software Architecture & Frontend — Architecture Decision Record

> **Status:** Final
> **Version:** 1.0
> **Last Updated:** 2026-07-05
> **Source:** `adr-platform-tech-stack.md` (the locked stack this architecture runs on); `architecture-v1.md` ("modular monolith" principle); capability catalog dependency levels
> **Purpose:** Lock the modular software architecture (kernel/shared/business tiers, dependency law, integration model) and the frontend direction (React web-first, native-later) so the C-01 apply phase and every subsequent capability can be built against a fixed structural foundation.
> **Cross-References:**
> - [Platform Tech Stack ADR](./adr-platform-tech-stack.md) — Postgres/Supabase + FastAPI + SQLAlchemy + Casbin
> - [C-01 ADR](./adr-c01-tenant-institution-implementation.md) — D1 (RLS), D6 (recursive CTE), Q4 (no event bus), Q5 (subdomain API) all interact with this architecture
> - [Architecture v1](./architecture-v1.md) — "modular monolith" principle (confirmed here)

---

## 0. Decision Summary

| # | Decision | Lock |
|---|---|---|
| A1 | Deployment shape | Modular monolith — ONE deployable FastAPI app, ONE Postgres. Kernel/shared/business are in-process Python packages, not separate services. |
| A2 | Tier membership rule | Based on what every business module must import ("consumed-by-all" rule). **Kernel** = infrastructure services every business module depends on: `TenantContext`, subdomain+JWT middleware, `TenantAwareRepositoryBase`, `AuditEmitter` Protocol, `TransferCoordinator` Protocol, C-03 auth (infrastructure), C-04 authz (infrastructure), C-08 config, C-11 audit (infrastructure). **Business** = domain logic used only by the owning capability's workflows: tenant/institution domain (C-01b), user/role domain (C-02b), attendance, fees, homework, exams, timetable, … **Shared** = cross-cutting services reusable across business modules but not foundational (notifications, file management, C-13 address, C-12 business codes). See [platform-capabilities-v3.md](../platform-capabilities/platform-capabilities-v3.md) Appendix A for the complete classification matrix (Kernel\* footnoted capabilities produce both infrastructure and domain). |
| A3 | Dependency law | `kernel → ∅`; `shared → kernel (+ other shared, acyclic)`; `business → kernel + shared + other business (acyclic, public interfaces only)`. **Never:** kernel→shared/business, shared→business. |
| A4 | Cross-module communication | Synchronous direct call to a module's **published service interface** only — never internal repo/model imports. Dependency graph must stay acyclic. Enforced by `import-linter`. No event bus for synchronous needs (consistent with C-01 Q4). |
| A5 | Module composition | **Module manifest + app factory.** Each module is a Python package exposing a manifest with hooks (`register_routes`, `on_startup`, `register_casbin_policies`, `register_cli`, scheduled jobs, …). The kernel's app factory reads a configured module list and invokes the hooks. |
| A6 | Kernel-service consumption | **Hybrid.** Request-scoped kernel services (`TenantContext`, current user, per-request `AuditEmitter`) via FastAPI `Depends` that source a contextvar set by middleware. Module-scoped singletons (repos, Casbin enforcer, configured clients) via constructor injection, wired by the manifest. |
| A7 | Migrations | **Single Alembic env**, module-prefixed files (e.g., `001_c01_create_clients.py`). One `alembic upgrade head` brings the whole DB current. |
| A8 | Frontend — native need | **Web first for v1; native later.** v1 = responsive React web + PWA (add-to-home-screen, web push, basic offline). Revisit React Native only when a proven native need emerges (e.g., a dedicated parent app). |
| A9 | Frontend — framework | **Vite + React SPA.** FastAPI is the sole backend; the SPA talks to it via TanStack Query. No SSR/RSC (the ERP is auth-gated; SEO is irrelevant). |
| A10 | Frontend — repo layout | **Monorepo:** `/backend` (Python/uv) + `/frontend` (Vite/pnpm) + `/packages` (shared TS, e.g., generated API types — the future RN-sharing seam). |
| A11 | Frontend — state | **TanStack Query** (server state) + **Zustand** (UI state). OpenAPI → TypeScript for type sharing (tool picked at implementation). |

---

## 1. Context

The platform tech stack is locked ([tech-stack ADR](./adr-platform-tech-stack.md)), but two structural questions remained open and were never recorded as decisions:

1. **Software architecture.** The repo is greenfield; `architecture-v1.md` states "modular monolith" as a principle but never defines the module tiers, the dependency law between them, or how the kernel composes with and provides services to modules. The 25-capability catalog is organized by dependency level, which strongly implies a layered model — but implication is not a locked decision. Without this, the C-01 apply phase cannot scaffold the project structure (where does `ClientRepository` live? how does a business module get `TenantContext`? where do migrations go?).

2. **Frontend direction.** The user wants React with "the same code for mobile/desktop." That phrase is overloaded — it could mean a single RN+RNW codebase, two codebases sharing logic, or responsive web only — and the choice is not reversible without a rewrite. It needed to be grilled to a concrete, phased decision.

This ADR records both, decided via a one-question-at-a-time grilling session in `docs/` (not sdd-stack).

## 2. Decision

### Software architecture (A1–A7)

**A1 — Modular monolith, one deployable.** Kernel, shared, and business modules are in-process Python packages composed into ONE FastAPI deployable running against ONE Postgres (the locked shared-schema + RLS model, D1). "Developed separately" means separate packages with enforced boundaries — not separate services or repos. This matches `architecture-v1.md`'s "modular monolith" principle and is consistent with the single-Postgres+RLS model.

**A2 — Tiers by consumed-by-all rule.**

| Tier | Contains | Examples |
|---|---|---|
| **kernel** | Infrastructure EVERY business module must import. Flat packages under `kernel/`. | `kernel/tenant_context.py` (TenantContext), `kernel/middleware.py` (subdomain+JWT), `kernel/repo_base.py` (TenantAwareRepositoryBase), `kernel/audit.py` (AuditEmitter), `kernel/transfer_coordinator.py` (TransferCoordinator), C-03 auth infrastructure, C-04 authz infrastructure, C-08 config, C-11 audit infrastructure |
| **shared** | Cross-cutting services reusable across business modules, not foundational | notifications, file management, C-13 address, C-12 business codes |
| **business** | Domain logic used only by the owning capability's workflows. Under `business/`. | `business/tenant_institution/` (Client/Institution/OrgUnit lifecycle, templates, transfers — C-01b), Attendance, Fees, Homework, Exams, Timetable, … |

Several capabilities produce BOTH kernel infrastructure AND a business domain module (e.g., C-01a Tenant Identity Infrastructure + C-01b Tenant & Institution Domain). The infrastructure lives under `kernel/`; the domain lives under `business/`. This split is recorded in the capability catalog's Classification Matrix ([platform-capabilities-v3.md](../platform-capabilities/platform-capabilities-v3.md) Appendix A) where `Kernel*` marks capabilities that will be split when built, following the C-01a/C-01b precedent.

C-01b is the first business module and the Level 1 zero-dependency root for the business tier — it depends only on C-01a (its own kernel infrastructure) and C-08 (configuration).

**A3 — Dependency law.**
- `kernel → ∅` (kernel depends on nothing in-app; only framework/stdlib)
- `shared → kernel` (and other shared, acyclic)
- `business → kernel + shared + other business` (acyclic, **public interfaces only**)
- **Never:** kernel→shared, kernel→business, shared→business

**A4 — Cross-module communication.** A business module may call another business module's **published service interface** (a defined contract — never internal repo/model imports), synchronously, as long as the dependency graph stays acyclic. Enforced by `import-linter` (Python's standard import-constraint linter). No event bus for synchronous needs — consistent with C-01 Q4 (async events deferred).

**A5 — Module composition: manifest + app factory.** Each module is a Python package exposing a manifest object with hooks:
- `register_routes(app)` — mount FastAPI routers
- `on_startup()` / `on_shutdown()` — lifecycle hooks
- `register_casbin_policies(enforcer)` — D11 matrix registration
- `register_cli(cli)` — CLI commands
- scheduled jobs, custom middleware, etc.

The kernel's app factory reads a configured module list (a Python list, not auto-discovery), imports each module, and invokes the hooks in dependency order (kernel first, then shared, then business).

**A6 — Kernel-service consumption: hybrid Depends + constructor.**
- **Request-scoped** (`TenantContext`, current user, per-request `AuditEmitter`): middleware parses the JWT + subdomain and populates a contextvar as the single source of truth; endpoints access it via FastAPI `Depends(get_tenant_context)` which reads the contextvar. The dependency is explicit in the signature (testable, visible, overrideable in tests) and cannot leak across requests.
- **Module-scoped singletons** (repos, Casbin enforcer, configured clients): constructor injection, wired by the manifest at startup.

This is the disciplined multi-tenant pattern: the dependency is explicit (no hidden inputs in the signature), but the source is middleware (no re-parsing per endpoint), and there's no contextvar-leak footgun because endpoints never touch the contextvar directly.

**A7 — Single Alembic env, module-prefixed files.** One Alembic environment at the repo root with a single linear migration history. Each module contributes migration files prefixed by module (`001_c01_create_clients.py`, `002_c01_institutions.py`, `003_c05_academic_years.py`). One `alembic upgrade head` brings the whole DB current. Cross-module FKs (e.g., C-05 → C-01 OrgUnit) are handled by migration ordering within the single history.

### Frontend (A8–A11)

**A8 — Web first, native later.** v1 ships a responsive React web app + PWA (add-to-home-screen, web push, basic offline). React Native is revisited only when a concrete, proven native need emerges (e.g., a dedicated parent app requiring native device features, app-store distribution, or deep offline). This avoids committing to RN prematurely on a greenfield product with many unknowns.

**A9 — Vite + React SPA.** The frontend is a single-page app built with Vite + React, talking to FastAPI via TanStack Query. No SSR, no React Server Components, no Next.js/Remix server layer. Rationale: the ERP is auth-gated (SEO irrelevant), FastAPI is already the sole backend (a meta-framework's server would create a two-backend confusion), and an ERP admin/teacher UI (tables, forms, dashboards) is web-native. The PWA shell provides install + push + basic offline.

**A10 — Monorepo layout.**
```
/                  repo root
  /backend         Python (uv) — FastAPI app + kernel/shared/business modules + Alembic
  /frontend        Vite + React SPA (pnpm)
  /packages        shared TypeScript (generated API types; future RN-sharing seam)
```
One git repo, one CI, atomic cross-stack commits. `/packages` holds generated OpenAPI types and any future shared TS; it is the seam a future RN app would import when native arrives.

**A11 — State management.** TanStack Query for all server state (caching, invalidation, retries, background refetch). Zustand for UI-only state (filters, modals, institution-switcher selection, UI toggles). API types generated from FastAPI's OpenAPI schema → TypeScript (tool picked at implementation; `openapi-typescript`/`orval`/`heyapi` are the candidates).

## 3. Consequences

**Positive:**
- One deployable + one DB = simplest possible operational model; matches the locked stack.
- Module manifest gives uniform extension points (routes, startup, Casbin, CLI, jobs) without auto-discovery magic.
- Hybrid Depends+contextvar gives multi-tenant safety (no leak) + testability + visible dependencies.
- Single Alembic history avoids multi-env migration orchestration pain.
- Web-first frontend avoids RN commitment; `/packages` keeps the native-later option cheap.
- TanStack Query + Zustand is the modern, lightweight, hooks-native default — minimal boilerplate.

**Discipline required (non-negotiable):**
- **`import-linter`** must be configured from day one to enforce A3/A4 (no kernel→shared, no shared→business, no internal cross-module imports, acyclic). Without enforcement, the dependency law is aspirational.
- **Modules expose `services/` (published interfaces); internals (`models/`, `repos/`, internal helpers) are not importable across modules.** Code review + lint enforce.
- **Endpoints access `TenantContext` only via `Depends(get_tenant_context)`**, never by reading the contextvar directly. This is the tenant-safety invariant.
- **Repositories return DTOs, not ORM objects** (per tech-stack ADR §3) — prevents lazy-load tenant bypass at the repository boundary.
- **One Alembic env.** Modules do not run their own migration environments. New module = new module-prefixed migration files in the single history.
- **Frontend logic/view separation is NOT structured from day one** (the lighter monorepo option was chosen). When native is revisited, logic (hooks, API client, state) may need to be extracted into `/packages`. This is an accepted future refactor, not a day-one cost.

**Negative / cost:**
- `import-linter` + published-interface discipline adds upfront tooling and review overhead.
- The manifest's explicit module list means adding a module = editing the list (not auto-discovered). Accepted — explicit > magic.
- Web-first means no app-store native app in v1. If a native need materializes, the RN build is a new effort (mitigated by `/packages` shared types).
- Two toolchains (Python + JS) in one repo — normal, but two dependency graphs to maintain.

## 4. Model

```
Modular monolith — one deployable, one Postgres

  /backend  (Python / uv / FastAPI)
    kernel/
      app_factory.py         create_app() + ModuleManifest Protocol (A5)
      db.py                  SQLAlchemy DeclarativeBase
      tenant_context.py      TenantContext + Depends(get_tenant_context)
      middleware.py           Subdomain+JWT middleware → sets contextvar (A6)
      repo_base.py            TenantAwareRepositoryBase (returns DTOs, injects client_id)
      audit.py                AuditEmitter Protocol + DefaultAuditEmitter
      transfer_coordinator.py TransferCoordinator Protocol + defaults
      casbin/                 enforcer; business modules register policies (C-04)
    shared/
      notifications/          manifest: register_routes, on_startup, ...
      files/, address/, codes/
    business/                 business tier (domain logic)
      tenant_institution/     C-01b — Client/Institution/OrgUnit lifecycle + transfers
        manifest.py           registers routes, Casbin policies, middleware
        models/               SQLAlchemy models (client, institution, org_unit, ...)
        repos/                tenant-aware repos (inherit from kernel.repo_base)
        routes/               platform-scoped + client-portal routers
        services/             state machines, approval, DTOs, service layer
        policies.py           D11 Casbin permission matrix
      attendance/             (future)
      fees/                   (future)
      ...
    migrations/               ONE Alembic env, module-prefixed files
      001_c01_initial.py      all C-01 tables + RLS + seeds
      ...
    alembic.ini
  /frontend  (Vite + React + pnpm)
    src/
      api/        TanStack Query hooks + generated client (from /packages types)
      features/   feature-based modules (attendance, fees, ...)
      stores/     Zustand stores (UI state)
      routes/     React Router / TanStack Router
  /packages
    api-types/   OpenAPI → TypeScript (consumed by /frontend; future RN seam)
```

```
Request flow (multi-tenant, A5 + A6)

  HTTPS  Host: <client-slug>.app.example.com
     │
     ▼
  FastAPI app (kernel app factory composed all module manifests)
     │
     ├─ 1. Subdomain middleware  → resolve Client (D3/Q5) → set contextvar
     ├─ 2. Supabase JWT middleware → validate, extract client_id+institution_id
     │                                 → set contextvar (single source of truth)
     ├─ 3. Endpoint handler
     │      def handler(tenant: TenantContext = Depends(get_tenant_context),
     │                   audit: AuditEmitter = Depends(get_audit),
     │                   fees: FeesService = Depends(get_fees_service)): ...
     │        │
     │        ├─ Depends reads contextvar (explicit, testable, no leak)
     │        ├─ Casbin enforcer checks (role, action, resource, tenant)  [D11]
     │        └─ Business module calls published service interface (A4)
     │              └─ service → tenant-aware repo → DTO (not ORM object)
     │
     └─ 4. SQL w/ SET LOCAL client_id GUC → Postgres RLS backstop (D1)
```

## 5. Constraints

Non-negotiable constraints this ADR imposes:

1. **One deployable, one Postgres.** No microservices, no per-module databases. (A1, D1)
2. **`import-linter` enforces the dependency law.** The build/CI must fail on kernel→shared, shared→business, internal cross-module imports, or cycles. (A3, A4)
3. **Modules expose published `services/`; internals are not cross-module-importable.** (A4)
4. **Module composition is via the manifest + app factory.** No auto-discovery, no entry-point plugins. (A5)
5. **`TenantContext` is accessed only via `Depends(get_tenant_context)`.** Endpoints never read the contextvar directly. (A6) — multi-tenant safety invariant.
6. **One Alembic environment.** No per-module migration envs. (A7)
7. **Frontend is web-first (Vite + React SPA + PWA).** No native app in v1. (A8, A9)
8. **Monorepo** — backend + frontend + packages in one git repo. (A10)

## 6. Alternatives Considered

| Decision point | Alternative | Reason for rejection |
|---|---|---|
| Module boundary (A1) | Versioned packages in monorepo; separate deployable services (microservices); polyrepo | Versioned packages: more ceremony than warranted for greenfield. Microservices: breaks the single-Postgres+RLS model (D1), adds distributed-systems complexity. Polyrepo: cross-repo changes + contract drift, premature for greenfield. |
| Tier rule (A2) | By change rate/stability; by team ownership; two tiers (fold kernel into shared) | Change-rate: subjective, tiers shift over time breaking dependents. Team-ownership: collapses to "one team owns everything" for a small team. Two tiers: loses the foundational-vs-cross-cutting distinction that the capability catalog already encodes. |
| Cross-module deps (A4) | Only via shared tier (lift common needs); events only (pub/sub); full isolation | Shared-tier-only: bloats shared with non-cross-cutting concerns, premature abstraction. Events-only: contradicts Q4 (no broker), forces eventual consistency. Full isolation: unrealistic for an ERP (Exams needs Fees/Attendance data). |
| Composition (A5) | Manual wiring in main.py; entry-point auto-discovery; hexagonal ports-and-adapters | Manual: doesn't scale to 25+ capabilities, no uniform hook for non-route concerns. Entry-points: requires installable packages, debugging discovery is hard, "installed = live" surprises. Hexagonal: high ceremony, non-idiomatic for FastAPI, overkill for greenfield. |
| Service access (A6) | Pure contextvar (implicit); DI container; pure constructor injection | Pure contextvar: hidden deps, hard to test, contextvar-leak footgun across async requests (multi-tenant risk). DI container: heavier dep, non-idiomatic for FastAPI, becomes magic service-locator. Pure constructor: request-scoped TenantContext doesn't fit without contextvar underneath (becomes hybrid anyway). |
| Migrations (A7) | Per-module Alembic envs; single env + autogenerate per module | Per-module: fiddly cross-module ordering, shared-table (RLS) coordination. Autogenerate: misses RLS (raw SQL anyway), noisy diffs, conflates model-change with migration-needed. |
| Mobile need (A8) | Native required now; responsive web sufficient forever | Native-now: premature RN commitment on greenfield with unknowns. Responsive-forever: closes the door on native even if a real need emerges; "native later" keeps the option open. |
| React framework (A9) | Next.js (App Router, SSR/RSC); Remix | Next.js: SSR/SEO wasted on auth-gated ERP, RSC mental-model tax, server layer conflicts with FastAPI (two backends). Remix: same SSR tradeoffs, niche, fewer resources. |
| Repo layout (A10) | Two repos; monorepo with split frontend workspaces from day one | Two repos: coordinated PRs, contract drift, two CIs. Split workspaces day-one: more upfront structure than warranted (C-01 is API-first; no frontend yet); `/packages` is the lighter future seam. |
| State management (A11) | TanStack Query + Redux Toolkit; TanStack Query + React Context | RTK: heavier boilerplate, steeper curve, overkill for most SPAs. Context only: re-render/perf risk for frequently-changing UI state; verbose for complex state (institution switcher, multi-step forms). |

## 7. Future Evolution

- **React Native (when native arrives).** Revisit per A8 when a proven native need emerges. The `/packages` seam + TanStack Query hooks + Zustand stores are the reusable logic; a future RN app imports `/packages` and writes native views. The lighter v1 structure (no day-one workspaces split) means a one-time extraction of hooks/API client/state into `/packages/shared` at that point — an accepted future refactor.
- **Event bus (cross-capability).** Per C-01 Q4 — deferred. If a cross-capability event-bus requirement materializes, it slots into the kernel (`kernel/events/`) and modules opt in via the manifest; A4's synchronous published-interface rule still governs direct calls.
- **Separate-schema / separate-database tenancy.** Per C-01 ADR §11 — if the platform migrates away from shared-schema, RLS policies drop and a new repository implementation is written; business logic untouched. A1's one-deployable shape is preserved unless volume forces service extraction.
- **Frontend meta-framework.** If a public marketing site is ever needed (SEO), it can live as a separate Next.js app in `/apps/marketing` without disturbing the Vite SPA — the monorepo accommodates it.
- **Module extraction to services.** If a single module's scale demands it, the manifest + published-interface discipline means a module can be extracted to a separate service with its interface becoming an HTTP client — the dependency law (A3) ensures no inversion. Not anticipated for greenfield.

---

> **ADR Status:** This ADR records the modular software architecture and frontend direction. It complements the [tech-stack ADR](./adr-platform-tech-stack.md) (the stack) and the [C-01 ADR](./adr-c01-tenant-institution-implementation.md) (C-01's decisions). Together they fully unblock the C-01 apply phase.
