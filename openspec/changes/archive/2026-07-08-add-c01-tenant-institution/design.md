## Context

C-01 (Tenant & Institution Management) is the zero-dependency root capability of a multi-tenant School ERP SaaS. Every other module keys off it for the tenant boundary, the legal/billing entity, and the home of the hierarchical school structure. The `openspec/specs/` tree is empty, so this is greenfield: C-01 introduces the `tenant-institution` domain with ADDED requirements only.

The decisional source of truth for this design is `docs/architecture/adr-c01-tenant-institution-implementation.md` (ADR, Final v1.0), which records 12 locked implementation decisions (D1–D12) with rationale and alternatives-rejected tables, plus 10 spec-resolution decisions (Q1–Q10), §5 constraints, and §7 future-evolution. This design transcribes and structures those decisions (citing decision IDs); it does **not** re-derive them — the ADR *is* the tradeoff analysis.

Two additional platform ADRs were locked after the C-01 ADR and are decisional input to this design's architectural frame (the §"Platform Architecture & Module Integration" section): `docs/architecture/adr-platform-software-architecture.md` (decisions A1–A11 — modular monolith, tier law, module manifest, hybrid service access, monorepo layout, single Alembic env, frontend direction) and `docs/architecture/adr-platform-tech-stack.md` (the locked stack: Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin RBAC+ABAC, pytest). Where this design previously flagged the stack as "TBD," the tech-stack ADR has now resolved it — those items are updated accordingly.

A working proof-of-concept (Supabase AuthN + Casbin AuthZ + Postgres RLS, multi-tenant, with attendance/grades modules and 12/12 Playwright isolation tests) de-risks the hardest integration wiring (ADR §1). Migration-readiness is a hard constraint (architecture-v1 §12, §19 rule 6): the platform must later be able to move from shared-tables → separate-schema → separate-database without rewriting business logic.

Stakeholders: Platform Owner (SaaS provider), Client Director (client's top admin), Institution Admin / Principal, and cross-institution oversight roles (Regional Manager, Group Academic Head, Finance Controller) — see the D11 permission matrix.

**References:**
- Proposal: `openspec/changes/add-c01-tenant-institution/proposal.md`
- Spec: `openspec/changes/add-c01-tenant-institution/specs/tenant-institution/spec.md`
- ADR: `docs/architecture/adr-c01-tenant-institution-implementation.md`
- Platform software-architecture ADR: `docs/architecture/adr-platform-software-architecture.md`
- Platform tech-stack ADR: `docs/architecture/adr-platform-tech-stack.md`
- PRD: `docs/prd/c-01-tenant-institution.md`
- Impact classification: `docs/prd/c-01-impact-classification.md`
- Architecture: `docs/architecture/architecture-v1.md` §3/§5.3/§12/§19
- Capability catalog: `docs/platform-capabilities/platform-capabilities-v3.md` §C-01

## Goals / Non-Goals

**Goals:**
- Record the technical approach for each locked ADR decision (D1–D12, Q1–Q10) so the apply phase can implement against an unambiguous design.
- Preserve C-01's zero-dependency property: no FK from C-01 to C-05; UUID v4 (not C-12) PKs.
- Preserve migration-readiness (§12): repositories are the storage-agnostic data-access contract; RLS is a deployment-local hardening layer that can be dropped on a future separate-schema/DB move.
- Define cross-capability coordination contracts (C-02/C-03/C-04/C-05/C-07/C-08/C-11/C-12/C-13/C-23) as boundary declarations within C-01's own scope.
- Provide a request-flow sketch and the data-flow so downstream capabilities know where to plug in (subdomain → client resolution → JWT → tenant-aware repository → RLS backstop).

**Non-Goals:**
- Re-deriving the tradeoff analysis (the ADR owns that; this design cites it).
- Re-deriving the platform architecture or tech stack. The platform software-architecture (A1–A11) and tech-stack ADRs are the decisional source for the architectural frame; this design cites them — it does not re-derive them.
- Modifying any other capability's spec. Cross-capability items are boundary declarations only.
- Designing C-02/C-03/C-04/C-05/C-07/C-08/C-11/C-12/C-13/C-23 internals. Each owns its own schema/behavior in a future change.
- Phase-1-deferred items: temporal/per-row `client_id` history (Q10, ADR §7); lifecycle-event table partitioning (Q8); async event bus (Q4); UUID v7 (D2 revisit); watermark ownership transfer (D12 alternative).

## Platform Architecture & Module Integration

This section records the platform-level architectural frame that C-01's apply phase must build within. It is decisional input from two platform ADRs locked after the C-01 ADR: `docs/architecture/adr-platform-software-architecture.md` (decisions A1–A11) and `docs/architecture/adr-platform-tech-stack.md` (the locked stack). The C-01 ADR's decisions (D1–D12, Q1–Q10) remain authoritative for C-01's behavior; this section wraps them in the platform structure — it does not override them.

### C-01 is a kernel-tier module (A2)

Per A2, C-01 (Tenant & Institution Management) is a **kernel-tier** module — a foundational capability everything transitively depends on, alongside C-02 (users), C-03 (auth), C-04 (authz), C-08 (config), and C-11 (audit). Its code lives under `/backend/kernel/` as an in-process Python package (A1 — modular monolith, one deployable FastAPI app, one Postgres; not a separate service). The concrete package name chosen for this design is `kernel/tenant_institution/` (flagged as a naming choice in the open questions — `kernel/c01_tenant_institution/` is a viable alternative if a capability-prefixed convention is preferred).

C-01 is **the first kernel module** and its apply phase bootstraps the entire project structure: the monorepo layout (A10), the FastAPI app factory + module manifest skeleton (A5), the single Alembic environment (A7), and the pytest + Supabase-CLI test harness. Later kernel/shared/business modules plug into the structure C-01 establishes.

### Module manifest + app factory (A5)

Per A5, module composition is via a **manifest + app factory** — not auto-discovery. Each module is a Python package exposing a manifest object with hooks. C-01's manifest exposes:

- `register_routes(app)` — mounts C-01's FastAPI routers: the subdomain-resolved client-portal router (Institution/OrgUnit endpoints, Q5, AC-12) and the platform-scoped router (Client lifecycle, InstitutionType management, ownership-transfer approval — Platform-Owner-only per D11).
- `register_casbin_policies(enforcer)` — registers the D11 permission-matrix policies (Casbin encoding is C-04's framework, but C-01 supplies the matrix content and registers its own policies).
- `on_startup()` / `on_shutdown()` — lifecycle hooks (e.g., seeding InstitutionType lookup data if configured).
- `register_cli(cli)` — C-01 CLI commands (e.g., seed, tenant provisioning helpers).

The kernel app factory (`/backend/kernel/app_factory.py`) reads a configured module list (explicit Python list, NOT entry-point auto-discovery) and invokes the hooks in **dependency order**: kernel tier first, then shared, then business (A2/A3). C-01, as the zero-dependency root, is composition-order position 0.

### Hybrid service access (A6)

Per A6, kernel-service consumption is **hybrid** — request-scoped values via FastAPI `Depends` sourcing a contextvar, and module-scoped singletons via constructor injection wired by the manifest.

**Request-scoped (TenantContext, current user, per-request AuditEmitter):** subdomain + JWT middleware (the subdomain→Client resolver per D3/Q5, the Supabase JWT validator per the tech-stack ADR) parses the request and populates a contextvar as the single source of truth. Endpoints read `TenantContext` via `Depends(get_tenant_context)`, which reads the contextvar. The dependency is explicit in the handler signature (testable, visible, overrideable in tests) and cannot leak across requests.

**Invariant: endpoints access `TenantContext` ONLY via `Depends(get_tenant_context)`, NEVER by reading the contextvar directly.** This is the multi-tenant safety invariant (A6 §5 constraint 5; the mechanism behind D1's repository contract — the repository obtains `client_id` from the TenantContext surfaced by the dependency).

**Module-scoped singletons (repos, Casbin enforcer, configured clients):** constructor injection, wired by the manifest at startup. C-01's tenant-aware repositories (D1) are constructed with their dependencies (session factory, Casbin enforcer) and registered as singletons; endpoints receive them via `Depends`.

### Monorepo layout (A10)

Per A10, the repository is a monorepo:

```
/                  repo root
  /backend         Python (uv) — FastAPI app + kernel/shared/business modules + Alembic
  /frontend        Vite + React SPA (pnpm) — deferred (C-01 is API-first)
  /packages        shared TypeScript (generated API types; future RN-sharing seam)
```

C-01's apply produces the `/backend` scaffolding (`kernel/`, `app_factory.py`, `migrations/`, `pyproject.toml`, `alembic.ini`). `/frontend` is established as a placeholder directory (the monorepo root structure is set now even though C-01 ships no UI — A8/A9 are web-first but C-01's scope is API-first). `/packages` is a placeholder for future shared TypeScript (the OpenAPI→TypeScript types seam per A11).

### Single Alembic environment, module-prefixed migration files (A7)

Per A7, there is **one Alembic environment** at `/backend/` with a single linear migration history. C-01's migration files are prefixed `NNN_c01_*` (e.g., `001_c01_create_clients.py`, `002_c01_institutions.py`, `003_c01_institution_types.py`, …). One `alembic upgrade head` brings the whole database current across all modules; cross-module foreign keys (e.g., a future C-05→C-01 OrgUnit FK) are handled by migration ordering within the single history. Modules do NOT run their own migration environments.

Per the tech-stack ADR, **RLS policies are written as raw SQL inside the same Alembic migrations** — `CREATE POLICY` statements are emitted in the migration files alongside the `CREATE TABLE` statements, keeping schema + RLS versioned together. C-01's RLS policies (D1 client_id enforcement, Q1 self-visible Client) live in `001_c01_*` (or a dedicated `NNN_c01_rls_policies.py`). Alembic owns all schema migrations; the Supabase CLI migration system is NOT used for schema (tech-stack ADR §3).

### import-linter enforcement of the dependency law (A3/A4)

Per A3, the dependency law is: `kernel → ∅` (kernel depends on nothing in-app); `shared → kernel` (acyclic); `business → kernel + shared + other business` (acyclic, public interfaces only). Never: kernel→shared, kernel→business, shared→business. Per A4, cross-module calls go to a module's **published service interface** only (never internal repo/model imports), synchronously, acyclic, enforced by **`import-linter`**. No event bus for synchronous needs (consistent with Q4).

C-01's apply adds the `.importlinter` configuration enforcing A3/A4 and the kernel-tier contract: C-01 (kernel) imports nothing from shared or business; C-01 exposes a `services/` package (published interfaces) while its `repos/`, `models/`, and internal helpers are not importable across modules. The config is added from day one — without enforcement, the dependency law is aspirational (platform software-architecture ADR §3).

### Request flow (platform-level view)

This request-flow sketch (adapted from the platform software-architecture ADR §4 Model) sits *above* the D1 three-layer defense-in-depth flow recorded later in this design — the two are complementary (platform composition feeds into the C-01-specific isolation layers).

```
HTTPS  Host: <client-slug>.app.example.com
   │
   ▼
FastAPI app (kernel app factory composed all module manifests, hook order kernel→shared→business)
   │
  1. Subdomain+JWT middleware  resolve Client (D3/Q5) → validate Supabase JWT → set contextvar
   2. Endpoint handler
        def handler(tenant: TenantContext = Depends(get_tenant_context),
                    audit: AuditEmitter = Depends(get_audit),
                    repo: TenantInstitutionRepo = Depends(get_tenant_institution_repo)): ...
           │
           ├─ Depends reads contextvar (explicit, testable, no leak; A6)
           ├─ Casbin enforcer check (role, action, resource, tenant)  [D11, registered via manifest hook]
           └─ repo (singleton, manifest-wired) → tenant-aware query → DTO (not ORM object)
   3. SQL w/ SET LOCAL client_id GUC → Postgres RLS backstop (D1)
```

### Cross-references

- C-01 ADR decisions D1–D12, Q1–Q10: the behavioral/contractual source of truth (unchanged).
- Platform software-architecture ADR decisions A1–A11: the structural frame (this section).
- Platform tech-stack ADR: the locked stack (Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin, pytest).
- A1 (modular monolith) ⟶ D1 (shared-schema + RLS) — the one-Postgres model.
- A2 (kernel tier) ⟶ C-01's zero-dependency property (ADR §1) — C-01 is the root kernel module.
- A3/A4 (dependency law + published interfaces) ⟶ D10 (no FK from C-01 to C-05) — the dependency law enforces what D10 models behaviorally.
- A5 (manifest) ⟶ D11 (permission matrix registered via `register_casbin_policies`) + Q5 (routes registered via `register_routes`).
- A6 (hybrid Depends + contextvar) ⟶ D1 (repo obtains client_id from TenantContext via `Depends(get_tenant_context)`).
- A7 (single Alembic env, module-prefixed) ⟶ D1/D6 (RLS + recursive CTE in Alembic migrations) + tech-stack ADR (RLS as raw SQL).
- A10/A8/A9 (monorepo + web-first) ⟶ C-01 is API-first; frontend deferred.

## Decisions

### D1 — Isolation enforcement: hybrid (tenant-aware repositories + RLS backstop)

**Approach.** Two-level hybrid model:
- **Repository contract (data-access layer):** business logic calls tenant-aware repositories only — never writes SQL directly, never relies on RLS as the primary filter (ADR §5 constraint 1). The repository injects `client_id` (from the TenantContext) and applies an `institution_id` default business filter on every tenant-scoped query.
- **RLS backstop (DB layer):** Postgres RLS enforces `client_id` on every tenant-scoped table as the hard legal boundary (ADR §5 constraint 2). `institution_id` is NOT in RLS — it is a business filter, overridable by cross-institution roles.

**Rationale.** A working POC proved Supabase + Casbin + RLS composes. The repository is the §12 migration-readiness contract; RLS is the *current deployment's* hardening layer — drop RLS + swap repo impl on a future separate-schema/DB move; business logic is untouched. The two-level split maps cleanly onto the architecture's distinction between a hard security boundary (client) and a default business filter (institution).

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| App-level repositories only (no RLS) | A single repository method that forgets to inject `client_id` = a data leak; the docs call client isolation a *legal* risk. Defensible as "ship faster, RLS later" but accepts accidental-leak risk until RLS lands. |
| RLS only (no repository abstraction) | Couples business logic to Postgres + shared-tables; migrating to separate-schema/DB (§11 future path) means rewriting all queries; breaks §12/§19 rule 6. |
| Both `client_id` + `institution_id` enforced in RLS | Institution isolation isn't a hard boundary (cross-institution access is documented for Client Director etc.); RLS would need bypass logic for those roles — complexity that fights the model. |

### D2 — ID strategy: UUID v4 for all C-01 entities

**Approach.** UUID v4 primary keys for Client, Institution, OrgUnit, InstitutionType, and all lifecycle/event entities. C-12 reserved for institution-scoped human-readable business codes (Student ID, Employee ID, receipt numbers) — NOT used for C-01 PKs.

**Rationale.** Globally unique; Supabase-native (matches the POC); migration-ready (no sequence collisions on §12 move); no central coordination. Keeping C-12 off C-01 PKs preserves C-01's **zero-dependency** property — C-12 is institution-scoped (needs an Institution from C-01), so depending on it for Client/Institution IDs would create a circular dependency.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| UUID v7 (time-ordered) | Newer; needs uuidv7 support in Postgres/Supabase (extension or app-side generation). Time-sortability is a nice-to-have, not a C-01 requirement. Deferred (ADR §7). |
| C-12-generated codes for all entities | Wrong fit: C-12 is institution-scoped + human-readable; Client is the scoper of institutions; InstitutionType is platform-level. Creates the C-01 ↔ C-12 circular dependency. |
| Autoincrement serial | Leaks tenant counts (guessable IDs); collides on DB migration (sequence reset); breaks §12. Excluded. |

### D3 — Subdomain slug rules + immutability

**Approach.** The subdomain identifies the **Client** (per architecture §5.3), never the institution. Format: lowercase, 3–63 chars, `[a-z0-9-]`, alphanumeric at both ends. Globally unique. Reserved platform labels blocked. Collision returns "taken" with no suggestions (see Q9). Immutable after creation; display name is mutable. Multi-institution Clients use the same portal subdomain + in-app institution switcher (no per-institution subdomains).

**Rationale.** Matches the documented model (§5.3) and keeps routing a single lookup (subdomain → client). Immutability eliminates redirect chains, stale links, a historical-slug table, and the phishing/tenant-isolation risk of reusing a freed slug. The in-app switcher handles the multi-institution case without per-institution DNS/CNAME overhead.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Slug = client + optional institution path slug (`/i/oakwood`) | Adds institution-slug uniqueness within client, extra routing/validation, and a redirect strategy when slugs change. |
| Per-institution subdomains | Contradicts §5.3 (subdomain identifies the client); routing now maps subdomain → institution → client (extra hop); a chain/trust client has no single portal subdomain; cross-institution admin roles have no natural entry point. |
| Mutable slug with permanent redirect table | Adds a historical-slug table + lookup on every unmatched subdomain, orphaned-slug cleanup policy, possible redirect chains, and collision risk on reuse. |
| Mutable slug, no redirect | Old links break; an old slug can route to a *different* client if reassigned — tenant-isolation and phishing risk. |

### D4 — Client entity field schema (purity + config delegation)

**Approach.** Client carries identity + legal-identity + contact + lifecycle + an `address_id` FK to C-13 only. Intrinsic fields: `id` (UUID v4), `slug` (immutable, globally unique), `display_name` (mutable), `legal_name`, `legal_entity_type` (configurable enum via lookup table — Q2), `tax_registration_number`, `primary_contact_email`, `primary_contact_phone`, `billing_contact_email`, `address_id` (FK → C-13), `current_lifecycle_status` (D8), audit timestamps. Timezone/locale/branding → C-08; subscription state → C-07; billing/contract/payment → C-23. No commercial metadata on C-01.

**Rationale.** Keeps C-01 pure identity/lifecycle; respects C-08 as the single config framework; branding/theme changes never require schema migrations.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| tz/locale intrinsic columns; branding in C-08 | Mild C-08 boundary blur; schema migration to add/change those two; the config-lookup cost on the hot path is negligible with caching. |
| All of tz/locale/branding as intrinsic columns | Branding changes (logos, colors, seasonal themes) require schema changes; maximally blurs C-08; least flexible. |

### D5 — Institution entity field schema (purity + config delegation)

**Approach.** Institution carries identity + type-FK + contact + address-FK + lifecycle only. Intrinsic fields: `id` (UUID v4), `client_id` (FK → Client; RLS tenant column per D1), `institution_type_id` (FK → InstitutionType; immutable after creation per D7), `display_name` (mutable), `legal_name` (optional), `code` (within-client unique optional short code), contact fields, `address_id` (FK → C-13), `current_lifecycle_status` (D9), `established_year`, `affiliation_number`/`affiliation_board`, audit timestamps. tz/locale/currency/branding/`academic_year_start`/`grading_scale` → C-08. Academic structure → C-05.

**Rationale.** Parallel boundary to D4 — C-01 stays identity/lifecycle; all tunable behavior lives in C-08; academic structure is C-05's domain (see D10).

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| tz/locale/currency intrinsic; branding+academic in C-08 | Currency is read by C-23 billing; tz/locale are foundational — but C-08 caching keeps the config-lookup cost negligible, and intrinsic columns blur the C-08 boundary and need migrations. |
| All config fields intrinsic | Schema migrations for any branding/grading-scale change; rejects C-08's role; maximally rigid. |

### D6 — OrgUnit hierarchy: adjacency list + recursive CTE; archive-only; type immutable

**Approach.** Adjacency list (`parent_id` self-FK, nullable = root) + Postgres `WITH RECURSIVE` for subtree/ancestor queries. No separate closure table. OrgUnit intrinsic fields: `id` (UUID v4), `client_id` (RLS), `institution_id` (default repo filter), `parent_id`, `name`, `type` (configurable enum via lookup table per Q2; immutable after creation), `sort_order`, `code` (within-institution unique), `current_lifecycle_status` (`active`/`inactive`/`archived`), audit timestamps. Restructuring rules: archive-only (soft-delete with reactivation); move is allowed but audited + cycle-prevented (app-side per Q6) + subtree moves with the node; type immutable after creation (to change type, archive + recreate).

**Rationale.** School org structures are shallow (~4–6 levels); adjacency list + recursive CTE is simplest + most migration-friendly, with trivial inserts/moves. Archive-only preserves audit integrity and downstream referential safety. Type immutability avoids cascade-invalidations from in-place type changes.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Closure table (`OrgUnitClosure`) | Extra table; every insert/move rewrites closure rows for the moved subtree; more storage + write complexity. Justified only for deep or frequently-queried trees — overkill for shallow school structures. |
| Materialized path (path string) | Rewrites path of moved subtree + descendants on every move; harder FK enforcement; path-length limits; less standard. |
| Hard-delete when empty; freely mutable type | Weakest audit integrity; risk of orphaned downstream data; type-change cascades break invariants; not aligned with the archive-only principle. |

### D7 — InstitutionType: JSONB template, setup-time only, configurable via API

**Approach.** InstitutionType intrinsic fields: `id` (UUID v4), `name` (configurable enum via lookup table per Q2), `code`, `is_system`, `default_org_unit_template` (JSONB nested tree of `{ org_unit_type, sort_order, children: [...] }`), audit timestamps. At Institution creation, the template is **materialized** into actual OrgUnit rows stamped with the new `client_id` + `institution_id`; application-side validation ensures referenced OrgUnit types are valid and the tree is acyclic. InstitutionType on an Institution is immutable after creation. It does NOT drive runtime module behavior.

**Rationale.** JSONB matches "configurable, not hardcoded" (C-01 §4 rule 3) — admins add new InstitutionTypes + templates via API without code changes. Templates are read once at institution creation then never queried, so a normalized table would add overhead without payoff.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Normalized `OrgUnitTemplate` + `OrgUnitTemplateNode` tables | Extra tables and joins; FK-enforced but templates are read once then never queried, so normalization overhead doesn't pay off; larger migration surface. |
| Hardcoded templates in code/seed files | Contradicts C-01 §4 rule 3; every new InstitutionType requires a code change and redeploy; clients/admins cannot add types without engineering. |

### D8 — Client lifecycle state machine

**Approach.** States: `Prospective`, `Active`, `Suspended`, `Archived`, `Terminated`. Allowed arcs per ADR §2.D8. `Terminated` terminal; `Archived` the only re-activatable inactive state. Every transition requires reason + Platform Owner approval (Approval flow per Q3) and is recorded in `client_lifecycle_events` + audited via C-11.

**Rationale.** Standard SaaS lifecycle with `Terminated` as a true terminal state. Aligns with the docs' explicit re-activation principle (C-01 §4 rule 6) — `Archived → Active` is allowed.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| `Terminated → Prospective` (re-onboard same client_id) | Re-using the same Client record for a new contract blurs audit history and billing continuity; usual practice is a new Client record on re-onboarding. |
| No `Archived` re-activation (stricter) | Contradicts the docs' explicit re-activation principle; loses client continuity; forces a new subdomain slug on return. |

### D9 — Institution lifecycle + Client coupling (runtime effective-state gating)

**Approach.** States: `Onboarding`, `Active`, `Inactive`, `Archived` — **no `Terminated`** for institutions. Allowed arcs per ADR §2.D9. All transitions audited via C-11 (ClientId + InstitutionId) and recorded in `institution_lifecycle_events`. Client-state coupling: an Institution is operationally Active only if its Client is Active. If the Client enters Suspended/Archived/Terminated, the Institution's access is gated at **runtime (effective state)** without cascading persisted state changes onto the Institution row.

**Rationale.** Runtime gating preserves institution lifecycle integrity during transient client suspensions; cascade-state-changes would mutate institution state on client events (mass state churn on large clients) and require remembering each institution's pre-suspension state to restore it.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Cascade state changes on Client suspension | Mutates Institution state on Client events (mass churn); must remember pre-suspension state to restore; race conditions; against the preserve-lifecycle principle. |
| No `Archived` re-activation (stricter) | Contradicts the re-activation principle; loses institution continuity and its OrgUnit/academic-structure setup; forces re-onboarding. |

### D10 — OrgUnit (C-01) ↔ Academic Structure (C-05) boundary

**Approach.** C-01 owns the structural/administrative container including Grade/Class/Section/Program/Batch as OrgUnit *types*. Pure structure only — no academic metadata. C-05 owns the academic layer on top: `AcademicYear`, `Term`, `Subject`, and academic assignments (`Subject → OrgUnit`, `AcademicYear → Institution`, class-subject mapping, homeroom-teacher assignment). C-05 entities hold FKs to C-01 OrgUnits/Institution. **C-01 has NO FK to C-05** — preserves zero-dependency. `homeroom_teacher_id` moves OUT of the C-01 OrgUnit into C-05 (academic assignment) or C-02 `RoleAssignment` scoped to OrgUnit + AcademicYear. A "class" used by Attendance/Exams = an OrgUnit (structural container) + its C-05 academic metadata for the current academic year.

**Rationale.** Honors the c-01 doc (lists Grade/Class/Section/Program/Batch as OrgUnit types in the template). Preserves C-01's zero-dependency invariant (no FK to C-05).

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| C-05 owns Grade/Class/Section; C-01 only Dept/Faculty | Contradicts the c-01 doc; moves template ownership from C-01 to C-05; breaks stated C-01 entity ownership; forces a redesign of the InstitutionType concept (D7). |
| Overlapping ownership with a sync mapping | Duplicate source of truth, sync complexity, ambiguity; violates the "single source of truth" principle applied to C-01. |

### D11 — C-01 write-permission matrix (tiered delegation, first cut)

**Approach.** Tiered delegation matrix (see ADR §2.D11 table). Platform Owner: ALL. Client Director (own client only): institutional CRUD + identity + OrgUnits; cannot mutate the Client itself. Institution Admin (own institution only): OrgUnit management + identity; cannot mutate the institution itself. Cross-institution roles: READ-only on C-01. All writes audited via C-11 with actor identity. Casbin RBAC+ABAC encodes this at the API layer (C-04 owns the framework); RLS enforces `client_id` at the DB layer as the backstop. Cross-tenant writes Platform-gated.

**Rationale.** Tiered delegation gives clients self-service over their own institutions and OrgUnits (low platform support load) while keeping cross-tenant boundary changes (Client lifecycle, ownership transfer) under Platform control.

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Platform-centralized (stricter) | Platform-side bottleneck for institution lifecycle; slower for multi-institution clients; less self-service; more support load on the SaaS provider. |
| Broad client self-service (looser) | Maximum autonomy, minimal platform control; risk of a Client Director archiving institutions without platform oversight; depends on a high-trust model and strong audit. |

### D12 — Institution ownership transfer (Platform-approved full transfer, immutable audit)

**Approach.** Platform-approved **full operational transfer** with immutable audit. Workflow: request → both clients consent → Platform Owner approves → execute in a **single transaction** (Client A→B across Institution row, OrgUnits, C-05 academic structure, student records, user-institution assignments) with isolation verified post-move → record an `OwnershipTransferEvent`. Audit events (C-11) created before the transfer stay immutable under their original ClientId. Users whose only Institution is the transferred one migrate to Client B; users with other Client-A Institutions stay in Client A and lose the transferred Institution (C-02 coordination). Billing moves to Client B's invoice effective next billing cycle (C-07/C-23 coordination).

**Rationale.** A cross-tenant boundary change must be Platform-approved (neither side can self-serve). One-transaction operational transfer preserves continuity; immutable audit preserves historical truth. Matches the docs' "approved migration process" (C-01 §4 rule 7).

**Alternatives rejected:**
| Alternative | Reason rejected |
|---|---|
| Split at transfer point (watermark) | Every historical query needs watermark logic; reports straddle two clients; the institution's "current state" is under B but history split across two tenants; rarely worth the cost. |
| No transfer; archive + recreate | Contradicts the docs; loses the institution's OrgUnit/academic-structure setup and historical continuity; forces full re-onboarding. |

### Q1 — RLS on the `client` table itself: self-visible

**Approach.** The `client` table has no `client_id` column (the Client *is* the tenant). RLS policy: `id = current_client_id` — a Client Director can read their own Client row. Platform Owners read all Clients (D11).

**Rationale.** Necessary because the tenant-defining table cannot carry a `client_id` self-reference; self-visibility gives the client's own admin read access to their own record, while `client_id` RLS on every other table enforces the cross-tenant boundary.

### Q2 — Configurable enums: lookup tables

**Approach.** `legal_entity_type`, OrgUnit `type`, InstitutionType `name` stored as lookup tables (`id` + `name`), FK-referenced by entity tables. Adding a new type = a data insert, no code/deploy. Honors D7's "configurable, not hardcoded" rule.

**Rationale.** Lookup tables preserve referential integrity while allowing runtime-configurable enum values without redeploy.

**Alternatives rejected (implicit):** hardcoded check constraints in schema would require a code/deploy per new value, contradicting the configurable rule.

### Q3 — Approval record storage: separate `Approval` table

**Approach.** Separate `Approval` table — one row per approval: `requested_by`, `approved_by`, `status`, `timestamps`. Supports the pending-approval state and the request→approve flow in D8/D9 lifecycle transitions and D12 ownership transfer.

**Rationale.** Lifecycle transitions requiring approval need an explicit pending state and an auditable approver; embedding approval state in the lifecycle event rows would conflate the request with the decision.

### Q4 — Async events on lifecycle/transfer: C-11 audit only, no message broker

**Approach.** C-11 audit only (synchronous, internal). No message broker for C-01. Consumers wire in directly or poll.

**Rationale.** Avoids premature event-bus infrastructure. Deferred until a cross-capability event-bus requirement materializes.

**Alternatives rejected (implicit):** a message broker would add infrastructure + operational cost before a cross-capability bus requirement exists.

### Q5 — API base shape: subdomain-resolved (supersedes the client-in-path example)

**Approach.** Subdomain-resolved. `POST /api/v1/institutions` with client implicit from subdomain (per D3). **Supersedes** the c-01-explained illustrative example `POST /api/clients/{slug}/institutions` — that form MUST NOT be used. Platform-Owner-only endpoints under a platform-scoped base.

**Rationale.** Matches D3's "subdomain identifies the client" rule and keeps the client implicit in every tenant-portal request. The client-in-path example was illustrative only and would leak the client identity into the path (and require extra validation). The explainer doc should get a "Superseded by API contracts doc" note (PRD OQ-4 — housekeeping, not blocking).

### Q6 — OrgUnit cycle-prevention: application/repository side, NOT a DB trigger

**Approach.** App-side — the repository checks before update. The DB schema MUST NOT add a duplicating trigger. Matches the repository-first principle (D1).

**Rationale.** Keeps all write-path logic in the repository (the storage-agnostic contract) so it survives a future separate-schema/DB move (§12). A DB trigger would need porting per deployment topology.

**Alternatives rejected (implicit):** a DB-level trigger would duplicate the logic in a deployment-local layer and break migration-readiness for zero benefit.

### Q7 — OrgUnit move audit: C-11 only (generic `org_unit_moved` event)

**Approach.** C-11 only — generic audit event `action="org_unit_moved"`, `payload={from_parent, to_parent, moved_by, ...}`. No dedicated `org_unit_move_event` table.

**Rationale.** Avoids a dedicated table for a low-volume event; the generic C-11 event carries all needed provenance. Aligns with the C-01→C-11 consumer boundary.

### Q8 — Lifecycle-event history table partitioning: deferred

**Approach.** Defer. Phase 1 = no partitioning. Candidate: monthly partitioning on `entered_at`. Revisit when volume matters.

**Rationale.** Premature partitioning adds operational complexity before volume justifies it.

### Q9 — Slug-collision "suggestions" behavior: return "taken", no suggestions

**Approach.** Return "taken" with no suggestions. No auto-suffix, no near-match algorithm. Caller must propose a new slug.

**Rationale.** Auto-suffixing/ near-match creates ambiguity about which slug was actually assigned; the caller should choose their own unique slug.

### Q10 — Pre-build temporal/`client_id` row-history tracking: do not pre-build

**Approach.** Do not pre-build. The full-transfer model (D12) + immutable C-11 audit log cover provenance. Revisit only if a concrete near-term requirement for per-row ownership history emerges — that would be a D12 redesign, not a toggle.

**Rationale.** Avoids speculative schema/complexity before a requirement exists.

## Request flow — three-layer defense in depth + repository contract

```
   ┌──────────────────────────────────────────────────────────────────┐
   │ LAYER 1 — AuthN (Supabase)               "Who are you?"            │
   │  JWT carries: sub (user id), role, client_id, selected             │
   │  institution_id (set by in-app switcher after login)              │
   └──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ LAYER 2 — AuthZ (Casbin)                 "What can you DO?"      │
   │  RBAC + ABAC (relationship rules); enforces D11 permission        │
   │  matrix; client_fence (r.sub.client_id == r.dom); super_admin     │
   │  bypass; cross-institution role overrides on institution scope    │
   └──────────────────────────────────────────────────────────────────┘
                                 │  if Casbin says yes
                                 ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ REPOSITORY CONTRACT (tenant-aware)        "Hide the SQL"         │
   │  Business logic calls repo.listX(institutionId, filters) —        │
   │  never passes client_id, never writes SQL, never knows RLS.       │
   │  Repo injects client_id (from TenantContext) + institution_id    │
   │  default filter into every query. Preserves §12 migration-        │
   │  readiness: swap repo impl + drop RLS on separate-DB move.       │
   └──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ LAYER 3 — AuthZ (Postgres RLS)           "Which ROWS can you     │
   │                                           actually SEE?"         │
   │  Hard boundary: client_id must match JWT on every tenant-scoped   │
   │  table. Defense in depth — filters even if repo is bypassed.      │
   │  institution_id is NOT in RLS (business filter, not hard fence). │
   └──────────────────────────────────────────────────────────────────┘
```

### Data-flow sketch (subdomain → repository → RLS)

1. **Subdomain → client resolution (C-03 owns the resolver):** the request subdomain is looked up to resolve the Client identity (D3).
2. **JWT carries `client_id` + selected `institution_id`:** after login, the user picks/switches the active institution via the in-app switcher; the selected `institution_id` rides alongside the resolved `client_id` in the JWT/TenantContext (D1, D3).
3. **Tenant-aware repository:** business logic invokes repositories that inject `client_id` (from TenantContext) and apply the `institution_id` default business filter, with cross-institution role overrides (D1).
4. **RLS backstop:** Postgres RLS on `client_id` enforces the hard legal boundary on every tenant-scoped table; the `client` table itself uses `id = current_client_id` (Q1).

### Cross-capability coordination points

- **D12 ownership transfer → C-05 + C-02:** C-01 orchestrates the transfer; the single transaction updates C-05 academic structure and C-02 student records / user-institution assignments. C-01 owns the transfer workflow and the `OwnershipTransferEvent`; C-05 and C-02 own their own schemas (each will define them in their own future change spec). The C-01 spec states the orchestration contract and the no-FK-from-C-01-to-C-05 invariant (D10); the downstream update is described as "coordinated with C-05/C-02, owned by C-05/C-02."
- **D12 ownership transfer → C-07/C-23 billing handoff:** C-01 notes the billing-handoff coordination point (subscription moves to Client B next billing cycle); C-07 and C-23 own the billing behavior in their own specs.
- **C-11 audit emission contract:** C-01 emits synchronous C-11 audit events tagged with ClientId + InstitutionId on every lifecycle transition, OrgUnit move, and ownership transfer; C-11 owns the immutable event log. The immutability invariant (audit events keep the ClientId they were recorded with, even across transfers — ADR §5 constraint 14) is the contract that D12 relies on.
- **C-08 config delegation:** C-01 explicitly excludes tz/locale/currency/branding/`academic_year_start`/`grading_scale` from its schema and delegates to C-08's Platform→Client→Institution→Module inheritance (D4, D5).

## Risks / Trade-offs

- **[R1] Cross-tenant data leakage** if a tenant-aware repository method forgets to inject `client_id` — a single missed call leaks data across Clients; this is a *legal* boundary. → Mitigation: hybrid isolation — repositories are the data-access contract **plus** Postgres RLS as a defense-in-depth backstop that filters even if the repo is bypassed (D1, ADR §5 constraints 1–2). Enforce the repository-first rule in code review and linting. (PRD R1)
- **[R2] Partial-failure rollback on ownership transfer** — D12 transfers Institution row + OrgUnits + C-05 academic structure + student records + user-institution assignments in one cross-table transaction; a partial failure could leave the institution half-attached to two Clients. → Mitigation: single-transaction execution (D12); careful test coverage of the transfer path; isolation verification post-move (D12). (PRD R2)
- **[R3] Cycle creation in OrgUnit moves** if the app-side cycle-prevention check (Q6) is bypassed by direct SQL or a future repository method that skips the check. → Mitigation: repository-first rule (D1/AC-9); the DB schema deliberately does not add a trigger, so all writes flow through the checked repository path. (PRD R3)
- **[R4] Historical ownership ambiguity** — D12's full-transfer model moves audit-eligible operational data to Client B; past audit events stay under their original ClientId (immutable). A downstream report needing "history of this institution including pre-transfer period" must span two Client contexts. → Mitigation: acknowledged in ADR §3/§7 as the cost of rejecting the watermark alternative. If a concrete requirement emerges for historical data staying with the seller, D12 must be redesigned (not a toggle). (PRD R4)
- **[R4b] Explainer doc drift** — `c-01-tenant-institution-explained.md` shows an illustrative `POST /api/clients/{slug}/institutions` API example superseded by Q5's subdomain-resolved form. Readers following the explainer will be misled. → Mitigation: flag in Open Questions (OQ-4); the parent should schedule a small follow-up doc update adding a "Superseded by" note. This change does not edit the explainer. (PRD R4b)
- **[R5] Two isolation layers to build and maintain from day one** (repositories + RLS) — more upfront setup than app-level-only. → Mitigation: accepted in ADR §3; the layered model preserves §12 migration-readiness and is the foundation for future separate-schema/DB moves. (PRD R5)
- **[R6] JSONB template validation has no DB-level enforcement** (D7) — invalid/acyclic violations of `default_org_unit_template` are app-side only. → Mitigation: application-side validation + test coverage of template materialization (D7). (PRD R6)
- **[R7] Module-boundary discipline must be enforced from day one** (A3/A4) — `import-linter` must be configured or the kernel→∅ / no-shared→business / no-internal-cross-module dependency law is aspirational. C-01 is the first kernel module and establishes the contract; later kernel modules (C-02, C-03, C-04, C-08, C-11) and shared/business modules build on it. If the contract is not enforced from the first commit, early violations calcify. → Mitigation: C-01's apply adds the `.importlinter` config + a sample contract test (A3, A4). (platform software-architecture ADR §3)
- **[Trade-off — RESOLVED] Stack now locked.** The platform tech-stack ADR locks Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin, pytest. The layered model (repo + RLS + Casbin) is no longer presumptive — it is the locked stack. The platform software-architecture ADR (A1–A11) locks the modular-monolith + module-manifest + monorepo structure. The pre-existing "stack TBD" flags (OQ-1, the Non-Goal "Pinning a tech stack", and the tasks.md stack-confirmation gate) are superseded — see the architectural-frame section and the updated scaffold tasks.

## Migration Plan

This is a greenfield capability (no baseline spec to migrate from), so there is no in-place data migration. Deployment/rollback strategy:

- **Deploy:** stand up the new tables (`clients`, `institutions`, `institution_types`, `org_units`, lookup tables, `approvals`, `client_lifecycle_events`, `institution_lifecycle_events`, `ownership_transfer_events`), RLS policies on `client_id`, the self-visible `client` RLS policy (Q1), and the lookup-table seed data. Then deploy the tenant-aware repositories, API layer (subdomain-resolved + platform-scoped bases), Casbin policy seed for the D11 matrix, and C-11 audit-emission wiring. Seed InstitutionTypes and their templates via API/data inserts (D7).
- **Rollback (pre-launch):** drop the new tables/policies and the deployed code; no existing data depends on C-01 yet because no downstream capability has shipped.
- **Rollback (post-launch, with downstream deps):** once C-02+ depend on C-01, a rollback is no longer a clean drop — it would break downstream FKs. From that point, rollback = forward-fix only. Mitigation: thorough verification (verify phase) before downstream capabilities are fed.

## Open Questions

- **OQ-1 — Tech stack choice (RESOLVED).** The platform tech-stack ADR locks Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin, pytest; the platform software-architecture ADR locks the modular-monolith + module-manifest + monorepo structure (A1–A11). The pre-existing "stack TBD" flags in `tasks.md` (task 1.1/1.2) are superseded by concrete scaffold tasks (see the updated task 1). No longer an open question.
- **OQ-2 — `c-01-explained` supersede note.** Per PRD OQ-4 and Q5, the explainer's `POST /api/clients/{slug}/institutions` example is superseded by the subdomain-resolved `POST /api/v1/institutions` form. The parent should schedule a small follow-up docs/ edit adding a "Superseded by API contracts doc" note to `docs/platform-capabilities/c-01-tenant-institution-explained.md`. This change does not edit `docs/` (per AGENTS.md).
- **OQ-3 — OpenSpec-git-discipline skill.** The local `openspec-git-discipline` skill enforces proposal-commit-before-apply and merge-before-archive discipline. Per task constraints, the worker does not run git commits; the parent handles the proposal commit before the apply phase. Confirm the parent will run `openspec-git-discipline` (or commit the planning artifacts) before `/opsx-apply`.
- **OQ-4 — Deferred ADR items (no action now).** Q4 (async event bus), Q8 (lifecycle-event partitioning), Q10 (temporal/`client_id` row-history), D2 UUID v7 revisit, D12 watermark alternative. All deferred per ADR §7; revisited only if a concrete requirement emerges.