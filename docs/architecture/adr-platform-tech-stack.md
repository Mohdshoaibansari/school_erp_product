# Platform Technology Stack — Architecture Decision Record

> **Status:** Final
> **Version:** 1.0
> **Last Updated:** 2026-07-05
> **Source:** `adr-c01-tenant-institution-implementation.md` (D1, D6, Q1, Q5, D11 presume a stack); POC (Supabase AuthN + Casbin + Postgres RLS, 12/12 Playwright tests)
> **Purpose:** Formally lock the platform-wide technology stack so every capability (starting with C-01) can be implemented against a fixed, POC-validated foundation.
> **Cross-References:**
> - [C-01 ADR](./adr-c01-tenant-institution-implementation.md) — D1 (RLS), D6 (recursive CTE), Q1/Q5 (JWT), D11 (Casbin) all presume this stack
> - [Architecture v1](./architecture-v1.md)
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md)

---

## 1. Context

The C-01 Tenant & Institution Management ADR locks 12 decisions (D1–D12) and 10 spec resolutions (Q1–Q10). Several of those decisions **presume** a specific technology stack without ever formally recording it as a decision:

- **D1** (hybrid isolation) requires **Postgres Row-Level Security (RLS)** as the defense-in-depth backstop.
- **D6** (OrgUnit hierarchy) relies on a **Postgres recursive CTE**.
- **Q1 / Q5** presume a **JWT** carrying `client_id` + `institution_id` (the Supabase Auth pattern).
- **D11** (permission matrix) is encoded as **Casbin RBAC+ABAC** policies.

A POC previously validated this exact combination (Postgres + Supabase AuthN + Casbin + FastAPI) with 12/12 passing Playwright tests. However, the repo is greenfield — there is no code, no `package.json`, no formal stack choice on record. Before the C-01 apply phase can implement anything, the stack must be a **locked decision**, not a presumption inherited by the spec/design/tasks artifacts. This ADR closes that gap.

## 2. Decision

The platform technology stack is locked as follows:

| Layer | Decision | Rationale |
|---|---|---|
| **Database** | **PostgreSQL** via **Supabase** (cloud for staging/prod; Supabase CLI local stack for tests) | Mandated by D1 (RLS) and D6 (recursive CTE). Supabase provides managed Postgres + Auth + storage. The Supabase CLI runs an identical local stack for fast, resettable test runs. |
| **Backend runtime** | **Python** + **FastAPI** | POC-validated. Async, type-hinted, Pydantic-native, excellent for a contract-first multi-tenant API. |
| **ORM / migrations** | **SQLAlchemy 2.0** (typed async ORM) + **Alembic** (migrations) | Mature, async, typed models pair with FastAPI/Pydantic. Alembic gives schema-as-code migrations across 25 capabilities. Recursive CTE + RLS well-supported. Repositories return **DTOs, not ORM objects** (see §3). |
| **AuthN** | **Supabase Auth** (JWT with `sub`, `role`, `tenant_id`/`client_id`, `institution_id`) | POC-validated. C-01 **consumes** JWTs to populate `TenantContext`; it does **not** issue them (auth issuance is C-03's job). Tests mint their own JWTs with a test secret — no live Supabase instance needed for C-01's test suite. |
| **AuthZ** | **Casbin** (RBAC + ABAC) | POC-validated. C-01 supplies the D11 permission-matrix *content*; C-04 owns the framework and policy encoding. |
| **Test framework** | **pytest** (unit + integration) | Python standard; FastAPI-native. RLS isolation tests run against the local Supabase Postgres with `supabase db reset` between runs for clean state. Playwright (E2E/UI) is retained from the POC but deferred until a UI-bearing capability is built. |
| **Test DB target** | **Supabase CLI local dev** (`supabase start` + `supabase db reset`) | Fast, offline, resettable, CI-friendly, mirrors cloud behavior. Cloud Supabase project(s) used for staging/prod/manual testing. |
| **Frontend** | **Deferred** | C-01 is API-first; no UI is built in C-01's apply. The framework choice (e.g., React/Next.js vs Vue/Nuxt) is deferred to the first UI-bearing capability. |
| **Prod deployment** | **Deferred** | Premature for the first capability. Hosting (cloud, containers vs serverless) decided when we approach a deployable slice. |

## 3. Consequences

**Positive:**
- The C-01 spec/design/tasks artifacts (already produced) are valid as-written — no ADR amendment needed, because the locked stack matches what the ADR presumed.
- POC-proven combination lowers implementation risk; the 12/12 POC tests are a known-good reference.
- One stack across all 25 capabilities — no per-capability tooling fragmentation.

**Discipline required (non-negotiable):**
- **Repositories return DTOs, not ORM objects.** A lazy-loaded ORM relationship accessed *outside* the tenant-scoped session could bypass `client_id` filtering and leak data across tenants. Returning DTOs (read-only, fully materialized) closes this hole at the repository boundary. This aligns with the backend-architecture skill's DTO-based API principle.
- **RLS policies are written as raw SQL inside Alembic migrations.** SQLAlchemy does not model RLS natively; policies are emitted as `CREATE POLICY` statements in migration files. This keeps schema + RLS versioned together.
- **Alembic owns migrations — not the Supabase CLI `supabase/migrations/` system.** Running both would conflict. Alembic targets the Supabase Postgres connection string directly (local in tests, cloud in prod).
- **C-01 consumes JWTs, never issues them.** The subdomain→client resolution and JWT parsing middleware populate `TenantContext`; C-03 owns issuance. For C-01's tests, JWTs are minted in-process with a test signing secret.
- **The test DB is reset between runs** (`supabase db reset`) so RLS isolation tests start from a known-empty state.

**Negative / cost:**
- Two isolation layers (repositories + RLS) must be built and kept in sync from day one — accepted in the C-01 ADR (D1) as the cost of defense-in-depth and §12 migration-readiness.
- Supabase CLI local dev requires Docker on developer machines.

## 4. Model

```
                         Request flow (C-01 apply)

  Browser / client
       │
       ▼  HTTPS, Host: <client-slug>.app.example.com
  ┌─────────────────────────────────────────────────────────────┐
  │ FastAPI app (Python)                                          │
  │   1. Subdomain middleware  → resolve Client from slug (D3/Q5)  │
  │   2. Supabase Auth JWT     → validate, extract client_id +    │
  │                               institution_id → TenantContext  │
  │   3. Casbin enforcer       → RBAC+ABAC check on (role, action, │
  │                               resource, client/institution)   │
  │   4. Tenant-aware repo     → injects client_id on every query; │
  │                               returns DTOs (never ORM objects)│
  └─────────────────────────────────────────────────────────────┘
       │                                            │
       ▼ SQL (w/ SET LOCAL client_id GUC)           ▼ audit event
  ┌──────────────────────┐              ┌──────────────────────┐
  │ PostgreSQL (Supabase)│              │ C-11 audit log        │
  │   - Tables (Alembic) │              │ (ClientId+InstId tag) │
  │   - RLS on client_id │              └──────────────────────┘
  │     (defense-in-depth│
  │      backstop, D1)   │
  │   - Recursive CTE    │
  │     (OrgUnit, D6)    │
  └──────────────────────┘

  Test target: `supabase start` (local Docker Postgres+auth),
  `supabase db reset` between pytest runs for clean state.
```

## 5. Constraints

Non-negotiable constraints this ADR imposes:

1. **Postgres is mandated.** D1 (RLS) and D6 (recursive CTE) require it. Choosing a different database requires amending the C-01 ADR — not just this stack ADR.
2. **Repository pattern (D1).** Business logic never writes SQL; all data access flows through tenant-aware repositories that inject `client_id` from `TenantContext`.
3. **Repositories return DTOs.** ORM objects never cross the repository boundary (prevents lazy-load tenant bypass).
4. **Alembic owns all schema migrations**, including RLS policies (as raw SQL). The Supabase CLI migration system is not used for schema.
5. **C-01 consumes JWTs; it does not issue them.** Issuance is C-03's responsibility.
6. **Casbin encodes the D11 matrix.** C-01 supplies matrix content; C-04 owns the framework.

## 6. Alternatives Considered

| Decision point | Alternative | Reason for rejection |
|---|---|---|
| Stack approach | Keep Postgres but revisit the app layer (backend/ORM/auth/authz) | Unnecessary — POC validated the full stack with 12/12 tests; no specific dissatisfaction to drive a re-pick. |
| Stack approach | Full reconsideration incl. database | Would force amending D1 (no RLS) and D6 (no recursive CTE); high cost, no justification. |
| ORM | SQLAlchemy 2.0 Core (query builder, no ORM mapper) | Loses model-as-documentation and typed-model ergonomics; more boilerplate across 25 capabilities with no real gain over the DTO-return discipline. |
| ORM | No ORM — raw asyncpg/psycopg + separate migration runner | Maximum control but no model definitions, more boilerplate, and a separate migration tool to maintain. Poor fit for a 25-capability schema. |
| Test DB target | Dedicated Supabase cloud dev project | Network-slow tests; second cloud project to manage; no offline capability. |
| Test DB target | Single cloud project for dev+test+prod | Test data shares space with dev/manual work — pollution risk for RLS isolation tests; no clean reset. |

## 7. Future Evolution

- **Frontend framework.** Deferred. Locked when the first UI-bearing capability is built (or earlier if the user wants to pin it). The POC's Playwright suite implies a frontend existed; that choice is re-opened, not inherited.
- **Prod deployment.** Deferred. Hosting (cloud provider, containers vs serverless, CI/CD) decided when approaching a deployable slice.
- **UUID v7.** Per C-01 ADR D2/§7 — drop-in candidate if pagination/indexing benchmarks show value. No action now.
- **Separate-schema / separate-database multi-tenancy.** Per C-01 ADR §11 future path — if the platform migrates away from shared-schema, RLS policies are dropped and a new repository implementation is written; business logic untouched.
- **Supabase CLI migration system.** If a future capability needs Supabase-native tooling (e.g., Supabase Edge Functions, Storage triggers), revisit the migration ownership split. For now Alembic owns all schema.

---

> **ADR Status:** This ADR records the platform technology stack. It is the decisional input that unblocks the C-01 apply phase (and every subsequent capability's implementation). It does **not** supersede the C-01 ADR — it formalizes the stack that ADR presumed.
