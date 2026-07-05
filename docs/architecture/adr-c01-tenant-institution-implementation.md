# C-01 Tenant & Institution Management — Implementation Decisions

> **Status:** Final
> **Version:** 1.0
> **Last Updated:** 2026-07-05
> **Author:** Architecture (collaborative decision session)
> **Source:** [architecture-v1.md](architecture-v1.md) §3, §4, §5.3, §11, §12, §16, §19; [platform-capabilities-v3.md](../platform-capabilities/platform-capabilities-v3.md) C-01; [c-01-tenant-institution-explained.md](../platform-capabilities/c-01-tenant-institution-explained.md)
> **Purpose:** Record the 12 implementation-level decisions for C-01 that the planning docs left open, so database-schema, API contracts, and the C-01 technical spec can be authored without ambiguity.
> **Cross-References:**
> - [Architecture v1](architecture-v1.md) — tenant hierarchy, isolation, subdomain, DB strategy
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md) — C-01 capability definition, dependency map, non-negotiable rules
> - [C-01 Explained](../platform-capabilities/c-01-tenant-institution-explained.md) — entity/lifecycle deep-dive
> - [Functional Requirements](../requirements/functional-requirements.md) §1.1, §1.2

---

## 1. Context

C-01 (Tenant & Institution Management) is the root capability of the platform — it has zero upstream dependencies (dependency map Level 1) and **every** business module depends on it. The planning docs fully specify the *concept* (entities, lifecycles, isolation principles, InstitutionType semantics) but deliberately leave the *implementation* open on three grounds:

1. **Migration-readiness** (architecture-v1 §12, §19 rule 6) — the docs refuse to pin storage topology so the platform can later move from shared-tables → separate-schema → separate-database.
2. **Phase-1 pragmatism** — the docs enumerate lifecycle states but not the state-machine arcs, and defer schema/API-contract/technical-spec to "next documents to create" (docs/README.md).
3. **Boundary clarity** — several interface lines (OrgUnit ↔ Academic Structure, C-01 write permissions, ownership transfer) are referenced but not defined.

This ADR closes those 12 gaps in a single cohesive decision set. Each decision is independently reversible (see §7), but together they form the contract that unblocks the 🥇 technical spec, 🥇 API contracts, and 🥈 database schema for C-01.

**Inputs to this decision session:**
- The five planning docs listed above (read in full).
- A working proof-of-concept (Supabase AuthN + Casbin AuthZ + Postgres RLS, multi-tenant, with attendance/grades modules and 12/12 Playwright isolation tests) that de-risks the hardest integration wiring.

---

## 2. Decision

Twelve decisions, each resolving one open gap. Each sub-section states the resolution, the rationale, and the alternatives rejected.

### D1 — Isolation enforcement + column naming

**Decision:** Hybrid — **tenant-aware repositories as the data-access contract** (business logic never writes SQL, never relies on RLS directly) **+ Postgres RLS as the defense-in-depth backstop** underneath. Two-level model:

- **Client isolation** (hard legal boundary): enforced by RLS via a `client_id` column on every tenant-scoped table. This is the POC's tenant fence, renamed `tenant_id` → `client_id` to match the docs' "Client" domain language.
- **Institution isolation** (default business filter, overridable by authorized cross-institution roles): a default repository filter on `institution_id`, overridable via Casbin for roles like Client Director, Regional Manager, Group Academic Head, Finance Controller.

The JWT / TenantContext carries **both** `client_id` (resolved from the subdomain at request start) and a **selected** `institution_id` (set by the in-app institution switcher after login).

**Rationale:** A working POC proved the Supabase + Casbin + RLS stack composes. RLS-only (without the repo) was rejected because it couples business logic to Postgres and breaks §12 migration-readiness for zero extra benefit over hybrid. The repository is the §12 contract; RLS is the *current deployment's* hardening layer — if we later move to separate-schema/DB, we drop RLS policies and swap the repository implementation; business logic is untouched. The two-level split maps cleanly onto the architecture's distinction between a hard security boundary (client) and a default business filter (institution).

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| App-level repositories only (no RLS) | A single repository method that forgets to inject `client_id` = a data leak; the docs call client isolation a *legal* risk. Defensible as "ship faster, RLS later" but accepts accidental-leak risk until RLS lands. |
| RLS only (no repository abstraction) | Couples business logic to Postgres + shared-tables; migrating to separate-schema/DB (§11 future path) means rewriting all queries; breaks §12/§19 rule 6. |
| Both client_id + institution_id enforced in RLS | Institution isolation isn't actually a hard boundary (cross-institution access is a documented capability for Client Director etc.), so RLS would need bypass logic for those roles — complexity that fights the model. |

---

### D2 — ID strategy for C-01 entities

**Decision:** **UUID v4** for primary keys of Client, Institution, OrgUnit, InstitutionType, and all lifecycle/event entities. C-12 (Code & Identifier Engine) is reserved for human-readable, institution-scoped business codes (Student ID, Employee ID, receipt numbers) and is **not** used for internal platform-entity PKs.

**Rationale:** Globally unique, Supabase-native (matches the POC), migration-ready (no sequence collisions when moving to separate-schema/DB per §12), no central coordination needed. Keeping C-12 off C-01 PKs preserves C-01's documented **zero-dependency** property — C-12 is institution-scoped (needs an Institution from C-01), so a circular dependency would arise if Client/Institution/OrgUnit IDs depended on C-12.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| UUID v7 (time-ordered) | Newer; needs uuidv7 support in Postgres/Supabase (extension or app-side generation). Time-sortability is nice-to-have, not a C-01 requirement. Deferred to a future revisit if pagination/indexing benchmarks show value. |
| C-12-generated codes for all entities | Wrong fit: C-12 is institution-scoped and human-readable; Client *is* the scoper of institutions; InstitutionType is platform-level. Also creates the C-01 ↔ C-12 circular dependency. |
| Autoincrement serial | Leaks tenant counts (guessable IDs), collides on DB migration (sequence reset), breaks §12. Excluded from consideration. |

---

### D3 — Subdomain slug rules + mutability

**Decision:** The subdomain identifies the **Client** (per architecture §5.3), never the institution.

- **Format:** lowercase, 3–63 chars, `[a-z0-9-]`, must start and end alphanumeric.
- **Uniqueness:** globally unique across all clients.
- **Reserved names:** platform labels blocked (`www`, `api`, `admin`, `app`, `mail`, `auth`, `platform`, `super`, etc.).
- **Collision at creation:** reject and suggest alternatives — no auto-suffix (avoids ambiguity).
- **Mutability:** **immutable after creation.** The display name may change freely (supports rebranding without changing the URL); the slug never does.
- **Multi-institution clients:** the subdomain is the client portal; after login the user picks/switches institution via an **in-app institution switcher**. No per-institution subdomains.

**Rationale:** Matches the documented model (§5.3) exactly and keeps routing a single lookup (subdomain → client). Immutability eliminates redirect chains, stale links, a historical-slug table, and the phishing/tenant-isolation risk of reusing a freed slug. In-app switcher cleanly handles the multi-institution case without per-institution DNS/CNAME overhead.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Slug = client + optional institution path slug (`/i/oakwood`) | Adds institution-slug uniqueness within client, extra routing/validation, and a redirect strategy when slugs change — complexity not justified for the C-01 use case. |
| Per-institution subdomains | Contradicts §5.3 (subdomain identifies the client); routing now maps subdomain → institution → client (extra hop); a chain/trust client has no single portal subdomain; cross-institution admin roles have no natural entry point. |
| Mutable slug with permanent redirect table | Adds a historical-slug table + lookup on every unmatched subdomain, orphaned-slug cleanup policy, possible redirect chains, and collision risk on reuse. |
| Mutable slug, no redirect | Old links break; an old slug can route to a *different* client if reassigned — tenant-isolation and phishing risk. Rejected. |

---

### D4 — Client entity field schema

**Decision:** C-01's Client carries only **identity + legal-identity + contact + lifecycle + address-FK**. Intrinsic fields (C-01 owned):

| Field | Type | Notes |
|---|---|---|
| `id` | UUID v4 (PK) | per D2 |
| `slug` | string | immutable, globally unique (per D3) |
| `display_name` | string | mutable |
| `legal_name` | string | legal entity name |
| `legal_entity_type` | enum (configurable) | e.g. Sole Proprietor / Partnership / Pvt Ltd / Trust / Society |
| `tax_registration_number` | string (optional) | regional legal identity (e.g. GSTIN, TIN) |
| `primary_contact_email` | string | |
| `primary_contact_phone` | string | |
| `billing_contact_email` | string | |
| `address_id` | UUID v4 (FK → C-13) | physical/legal address owned by C-13 |
| `current_lifecycle_status` | enum (FK → state machine) | per D8 |
| `created_at` / `updated_at` / `archived_at` | timestamp | audit timestamps |

**Delegated elsewhere:** timezone, locale, `logo_url`, `brand_color`, `theme` → **C-08 Configuration Framework** at Client scope (inheriting Institution → Module). Subscription state → C-07. Billing/contract/payment → C-23. No commercial metadata on C-01's Client.

**Rationale:** Keeps C-01 pure identity/lifecycle; respects C-08 as the single config framework; branding/theme changes never require schema migrations.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| tz/locale intrinsic columns; branding in C-08 | Mild C-08 boundary blur; schema migration to add/change those two; the config-lookup cost on the hot path is negligible with caching. |
| All of tz/locale/branding as intrinsic columns | Branding changes (logos, colors, seasonal themes) require schema changes; maximally blurs C-08; least flexible. |

---

### D5 — Institution entity field schema

**Decision:** C-01's Institution carries **identity + type-FK + contact + address-FK + lifecycle**. Intrinsic fields (C-01 owned):

| Field | Type | Notes |
|---|---|---|
| `id` | UUID v4 (PK) | per D2 |
| `client_id` | UUID v4 (FK → Client) | the RLS tenant column (per D1) |
| `institution_type_id` | UUID v4 (FK → InstitutionType) | immutable after creation (per D7) |
| `display_name` | string | mutable |
| `legal_name` | string (optional) | |
| `code` | string (optional) | within-client unique short code for switcher/reports |
| `primary_contact_email` / `primary_contact_phone` | string | |
| `address_id` | UUID v4 (FK → C-13) | |
| `current_lifecycle_status` | enum (FK → state machine) | per D9 |
| `established_year` | integer (optional) | |
| `affiliation_number` / `affiliation_board` | string (optional) | regional legal identity for official documents |
| `created_at` / `updated_at` / `archived_at` | timestamp | |

**Delegated elsewhere:** timezone, locale, currency, branding, `academic_year_start`, `grading_scale` → **C-08** at Institution scope (inheriting from Client, overriding where set). No per-institution subdomain (per D3). Academic structure (Grade/Class/Subject mapping, AcademicYear, Term) → C-05.

**Rationale:** Parallel boundary to D4 — C-01 stays identity/lifecycle; all tunable behavior lives in C-08 config; academic structure is C-05's domain (see D10).

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| tz/locale/currency intrinsic; branding+academic in C-08 | Currency is read by C-23 billing; tz/locale are foundational — but C-08 caching keeps the config-lookup cost negligible, and intrinsic columns blur the C-08 boundary and need migrations. |
| All config fields intrinsic | Schema migrations for any branding/grading-scale change; rejects C-08's role; maximally rigid. |

---

### D6 — OrgUnit schema, hierarchy model, and restructuring rules

**Decision:**

**Hierarchy model:** Adjacency list (`parent_id` self-FK on OrgUnit, nullable = root) + Postgres **recursive CTE** (`WITH RECURSIVE`) for subtree/ancestor queries. `OrgUnitHierarchy` is the live parent-child relation via `parent_id` — no separate closure table.

**Intrinsic fields (C-01 owned):**

| Field | Type | Notes |
|---|---|---|
| `id` | UUID v4 (PK) | |
| `client_id` | UUID v4 (FK → Client) | RLS tenant column (per D1) |
| `institution_id` | UUID v4 (FK → Institution) | default repo filter (per D1) |
| `parent_id` | UUID v4 (FK → OrgUnit, nullable) | nullable = root |
| `name` | string | |
| `type` | enum (configurable, driven by InstitutionType template) | Department / Faculty / Grade / Division / Section / Class / Program / Batch / Course |
| `sort_order` | integer | |
| `code` | string (optional) | within-institution unique |
| `current_lifecycle_status` | enum | active / inactive / archived |
| `created_at` / `updated_at` / `archived_at` | timestamp | |

**Restructuring rules:**
- **Deletion:** archive-only (soft-delete), reactivation allowed — consistent with institutions and the docs' "never delete" principle; prevents orphaned downstream data (classes, attendance, etc.).
- **Move (parent change):** allowed, **audited**, **cycle-prevented** (cannot move a node under its own descendant); the whole subtree moves with the node.
- **Type:** **immutable after creation** — to "change" type, archive the node and create a new one (avoids breaking downstream invariants that depend on the node's type).

**Rationale:** School org structures are shallow (Grade→Class→Section, ~4–6 levels); adjacency list + recursive CTE is the simplest, most migration-friendly model, with trivial inserts/moves. Archive-only preserves audit integrity and downstream referential safety. Type immutability avoids the cascade-invalidations that come with in-place type changes.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Closure table (`OrgUnitClosure`) | Extra table; every insert/move rewrites closure rows for the moved subtree; more storage + write complexity. Justified only for deep or frequently-queried trees — overkill for shallow school structures. |
| Materialized path (path string) | Rewrites path of moved subtree + descendants on every move; harder FK enforcement; path-length limits; less standard. |
| Hard-delete when empty; freely mutable type | Weakest audit integrity; risk of orphaned downstream data; type-change cascades break invariants; not aligned with docs' archive-only principle. |

---

### D7 — InstitutionType + default OrgUnit template format

**Decision:**

**InstitutionType intrinsic fields (C-01 owned):**

| Field | Type | Notes |
|---|---|---|
| `id` | UUID v4 (PK) | |
| `name` | string | School / College / University / Coaching Institute / … |
| `code` | string | unique short code |
| `is_system` | boolean | system-defined vs configurable |
| `default_org_unit_template` | JSONB | nested tree of `{ org_unit_type, sort_order, children: [...] }` |
| `created_at` / `updated_at` | timestamp | |

**Template encoding:** a **JSONB column** `default_org_unit_template` on InstitutionType storing a nested tree of `{ org_unit_type, sort_order, children: [...] }`. At institution creation, the template is **materialized** into actual OrgUnit rows stamped with the new institution's `client_id` + `institution_id`. Validation logic ensures referenced OrgUnit types are valid and the tree is acyclic.

**Semantics:** InstitutionType's **only** job is to supply the default OrgUnit template at institution creation time. It does **not** drive runtime module behavior — Attendance, Fees, Homework, Exams operate identically regardless of type. InstitutionType on an Institution is **immutable after creation** (setup-time only); to "change" type, archive the institution and create a new one.

**Rationale:** JSONB matches the docs' "configurable, not hardcoded" rule (C-01 §4 rule 3) — admins add new InstitutionTypes + templates via API without code changes. Templates are read once at institution creation and then never queried, so a normalized table would add overhead without payoff.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Normalized `OrgUnitTemplate` + `OrgUnitTemplateNode` tables | Extra tables and joins; FK-enforced but templates are read once then never queried, so normalization overhead doesn't pay off; larger migration surface. |
| Hardcoded templates in code/seed files | Contradicts C-01 §4 rule 3; every new InstitutionType requires a code change and redeploy; clients/admins cannot add types without engineering. |

---

### D8 — Client lifecycle state-machine

**Decision:** States: `Prospective`, `Active`, `Suspended`, `Archived`, `Terminated`.

**Allowed arcs:**
- `Prospective → Active` (contract signed + onboarding complete)
- `Prospective → Archived` (lead dropped)
- `Active → Suspended` (payment failure / policy violation / admin action)
- `Suspended → Active` (resolved + admin approval)
- `Active → Archived` (voluntary exit / contract end)
- `Archived → Active` (re-activation: contract renewed + admin approval)
- `Suspended → Archived` (escalation after grace)
- `Active → Terminated`, `Suspended → Terminated`, `Archived → Terminated` (permanent legal/financial closure)

**Terminal state:** `Terminated` is **terminal** — no return.
**Re-activatable state:** `Archived` is the only inactive-but-re-activatable state.

All transitions require a **reason + admin/platform approval** and are **audited via C-11** (ClientId tagged) and recorded in a `ClientLifecycleEvent` history table (`state`, `entered_at`, `reason`, `actor`).

**Semantics:**
- `Suspended` = hard temporary halt (payment/legal driven).
- `Archived` = dormant, re-activatable.
- `Terminated` = permanent legal/financial closure.

**Rationale:** Standard SaaS lifecycle with Terminated as a true terminal state. Aligns with the docs' explicit re-activation principle (C-01 §4 rule 6, c-01 doc §7) — Archived → Active is allowed.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Terminated → Prospective (re-onboard same client_id) | Re-using the same Client record for a new contract blurs audit history and billing continuity; usual practice is a new Client record on re-onboarding. |
| No Archived re-activation (stricter) | Contradicts the docs' explicit re-activation principle; loses client continuity; forces a new subdomain slug on return. |

---

### D9 — Institution lifecycle state-machine + Client coupling

**Decision:** States: `Onboarding`, `Active`, `Inactive`, `Archived`. **No `Terminated`** for institutions (that's Client-level only).

**Allowed arcs:**
- `Onboarding → Active` (go-live: setup complete + admin approval)
- `Onboarding → Archived` (onboarding abandoned, never went live)
- `Active → Inactive` (pause: term break / seasonal closure / admin pause)
- `Inactive → Active` (resume + admin approval)
- `Active → Archived` (permanent closure, data retained)
- `Inactive → Archived` (escalation: inactive becomes permanent)
- `Archived → Active` (re-activation, per docs)

**Client-state coupling:** an Institution can only be **operationally** Active if its Client is Active. If the Client goes Suspended/Archived/Terminated, the Institution's access is **gated at runtime (effective state)** **without cascading state changes** onto the Institution row — each institution's own lifecycle position is preserved, so a briefly-suspended client doesn't lose each institution's state.

All transitions audited via C-11 (ClientId + InstitutionId tagged) and recorded in an `InstitutionLifecycleEvent` history table.

**Suspended vs Inactive semantics:** Client `Suspended` = hard temporary halt, payment/legal driven. Institution `Inactive` = soft operational pause (term break, seasonal closure, admin pause). Different triggers, different levels.

**Rationale:** Runtime gating (effective state) preserves institution lifecycle integrity during transient client suspensions; cascade-state-changes would mutate institution state on client events (mass state churn on large clients) and require remembering each institution's pre-suspension state to restore it.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Cascade state changes on Client suspension | Mutates Institution state on Client events (mass churn); must remember pre-suspension state to restore; race conditions; against the docs' preserve-lifecycle principle. |
| No Archived re-activation (stricter) | Contradicts docs' re-activation principle; loses institution continuity and its OrgUnit/academic-structure setup; forces re-onboarding. |

---

### D10 — OrgUnit (C-01) ↔ Academic Structure (C-05) boundary

**Decision:**

- **C-01 owns the structural/administrative container**, **including** Grade/Class/Section/Program/Batch as OrgUnit types (per the InstitutionType template). Pure structure: `id`, `client_id`, `institution_id`, `parent_id`, `type`, `name`, `code`, `sort_order`, `lifecycle` — **no academic metadata**.
- **C-05 owns the academic layer on top:** `AcademicYear`, `Term`, `Subject`, and the academic assignments — `Subject → OrgUnit` (which subjects are taught in Grade 10), `AcademicYear → Institution`, class-subject mapping, homeroom-teacher assignment, grading periods.

**Interface contract:** C-05 entities hold FKs to C-01 OrgUnits (and Institution). **C-01 has NO FK to C-05** — this preserves C-01's zero-dependency property. C-01 never knows about academic years or subjects.

A "class" used by Attendance/Exams = an **OrgUnit** (structural container) + its **C-05 academic metadata** for the current academic year.

**POC reconciliation:** the POC's `classes.homeroom_teacher_id` moves **out** of the C-01 OrgUnit into **C-05** (academic assignment) or **C-02 RoleAssignment** scoped to OrgUnit + AcademicYear — it is **not** an intrinsic C-01 OrgUnit field. C-01 OrgUnit stays pure structure.

**Rationale:** Honors the c-01 doc, which explicitly lists Grade/Class/Section/Program/Batch as OrgUnit types in the InstitutionType template and states "C-01 owns OrgUnit + OrgUnitHierarchy." Preserves C-01's zero-dependency invariant (no FK to C-05).

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| C-05 owns Grade/Class/Section; C-01 only Dept/Faculty | Contradicts the c-01 doc (lists Grade/Class/Section/Program/Batch as OrgUnit types); moves template ownership from C-01 to C-05; breaks stated C-01 entity ownership; forces a redesign of the InstitutionType concept (D7). |
| Overlapping ownership with a sync mapping | Duplicate source of truth, sync complexity, ambiguity about which is authoritative; violates the docs' "single source of truth" principle applied to C-01. |

---

### D11 — C-01 write-operation permission matrix (first cut)

**Decision:** Tiered delegation matrix. (First cut — C-04 refines precise role definitions; Casbin policies encode it.)

| Role | Scope | C-01 write permissions |
|---|---|---|
| **Platform Owner** (SaaS provider side) | All | ALL C-01 operations — create/suspend/archive/terminate Client, manage InstitutionTypes, everything, as higher authority. |
| **Client Director** (client's top admin) | Own client only | Create institution, activate/inactive/archive institution, reinstate institution, update Client + Institution identity, manage OrgUnits. **Cannot** create/suspend/terminate the Client itself (request to Platform). |
| **Institution Admin / Principal** | Own institution only | Update institution identity, create/move/archive/reactivate OrgUnits. **Cannot** create/suspend/archive the institution itself (request to Client Director). |
| **Cross-institution roles** (Regional Manager, Group Academic Head, Finance Controller) | Across institutions within a client | **READ-only** oversight on C-01; no C-01 write operations. |

All writes audited via C-11 with actor identity. Casbin RBAC+ABAC (from the POC) enforces this matrix at the API layer; RLS enforces `client_id` isolation at the DB layer as the backstop.

**Rationale:** Tiered delegation gives clients self-service over their own institutions and OrgUnits (low platform support load) while keeping cross-tenant boundary changes (Client lifecycle, ownership transfer) under Platform control.

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Platform-centralized (stricter) | Platform-side bottleneck for institution lifecycle; slower for multi-institution clients; less self-service; more support load on the SaaS provider. |
| Broad client self-service (looser) | Maximum autonomy, minimal platform control; risk of a Client Director archiving institutions without platform oversight; depends on a high-trust model and strong audit. |

---

### D12 — Institution ownership transfer process

**Decision:** Platform-approved **full operational transfer** with **immutable audit**.

**Workflow:**
1. Request initiated.
2. Both source & destination clients consent (legal/contractual).
3. **Platform Owner approves** (cross-tenant boundary change — neither source nor destination can self-serve).
4. Execute in a **single transaction** → verify isolation.
5. Record an `OwnershipTransferEvent`.

**Approver:** Platform Owner **only**.

**Data handling:**
- **Operational data** (the Institution row, its OrgUnits, C-05 academic structure, student records, user-institution assignments for that institution) gets `client_id` updated A→B in **one transaction**.
- **Audit events (C-11) are immutable** — they keep the ClientId they were recorded with (historical truth).

**`OwnershipTransferEvent` captures:** `from_client`, `to_client`, `institution`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason`.

**Users:** users whose **only** institution is the transferred one are migrated to Client B; users with other Client-A institutions stay in Client A and lose the transferred institution (C-02 coordination point).

**Billing:** C-07/C-23 move the institution's subscription to Client B's invoice effective next billing cycle.

**Rationale:** A cross-tenant boundary change must be Platform-approved (neither side can self-serve a boundary move). One-transaction operational transfer preserves continuity; immutable audit preserves historical truth. Matches the docs' reference to "an approved migration process" (C-01 §4 rule 7).

**Alternatives rejected:**
| Alternative | Reason for rejection |
|---|---|
| Split at transfer point (watermark) | Every historical query needs watermark logic; reports straddle two clients; the institution's "current state" is under B but history split across two tenants; rarely worth the cost. |
| No transfer; archive + recreate | Contradicts the docs (C-01 §4 rule 7 explicitly references an approved migration process); loses the institution's OrgUnit/academic-structure setup and historical continuity; forces full re-onboarding. |

---

## 3. Consequences

**Positive:**
- Unblocks the three 🥇/🥈 missing artifacts: C-01 technical spec, API contracts, database schema — each can now be authored against an unambiguous decision set.
- The POC's three-layer stack (Supabase AuthN / Casbin AuthZ / Postgres RLS) is preserved and extended; nothing in the POC is invalidated.
- Migration-readiness (§12) is fully respected: repositories are the storage-agnostic contract; RLS is a deployment-local hardening layer that can be dropped on a future separate-schema/DB move.
- Two-level isolation (`client_id` hard, `institution_id` soft) maps cleanly onto the architecture's distinction between a legal boundary and a business filter.
- C-01's zero-dependency property is preserved (no FK to C-05; UUIDs instead of C-12 codes).
- Audit integrity preserved across all lifecycle transitions and ownership transfers (immutable C-11 events; history tables per entity).

**Negative / costs:**
- Two isolation layers to build and maintain from day one (repositories + RLS) — more upfront setup than app-level only.
- JSONB template validation logic (D7) is application-side — no DB-level FK enforcement inside the JSON; must be covered by tests.
- Runtime effective-state gating (D9) adds a small per-request check (institution's Client must be Active for the institution to be operationally Active).
- Ownership transfer (D12) is a single-transaction cross-table update — must be carefully tested for partial-failure rollback across OrgUnits, C-05 academic structure, student records, and user-institution assignments.

**Risks:**
- A future requirement for "historical data stays with the seller" on ownership transfer would force a watermark model (D12 alternative) — not chosen now.
- If the team later wants time-ordered IDs for pagination/indexing benchmarks, D2's UUID v4 can be revisited (UUID v7 is a drop-in candidate).

---

## 4. Model

### 4.1 Entity hierarchy (C-01 owned entities, in bold)

```
[PlatformOwner] – owns the SaaS, billed-to nobody
   │ 1:N
[Client]*  – contract signer, bill recipient
   │  lifecycle: Prospective→Active→Suspended→Archived→Terminated (Terminated terminal)
   │  1:N              │ subscribed-to
[Institution]*          [C-07 Subscription] (Client-level, per-module add-ons)
   │  lifecycle: Onboarding→Active→Inactive→Archived (no Terminated)
   │  has-one           │ runtime-gated by Client state (effective state, no cascade)
[InstitutionType]──► default OrgUnit template (JSONB, setup-time only, NOT a runtime driver)
   │ 1:N
[OrgUnit]* →→ [OrgUnitHierarchy] (adjacency list via parent_id; recursive CTE for subtrees)
                 │ lifecycle: active/inactive/archived (archive-only, no hard delete)
                 │ type immutable; move = audited + cycle-prevented + subtree moves

* = C-01 owned entity (single source of truth — no other module may redefine)

[Client]   ◄── C-02 Users belong-to-client-first
           ◄── C-03 Auth resolves client via subdomain, per-client IdP
           ◄── C-04 Authorization layers: Platform→Client→Institution→OrgUnit→…
           ◄── C-07 Subscription gates modules at Client level
           ◄── C-23 Billing issues one invoice per Client, itemized per-Institution
           ◄── C-11 Audit tags every event with ClientId + InstitutionId (immutable)
           ◄── C-08 Config inherits Platform→Client→Institution→Module
           ◄── C-13 Address owns the institution's physical address (C-01 holds FK)

[OrgUnit]  ◄── C-05 Academic Structure holds FKs to OrgUnit (AcademicYear, Term, Subject,
              class-subject mapping, homeroom-teacher). C-01 has NO FK to C-05.
```

### 4.2 Request flow — three-layer defense in depth + repository contract

```
   ┌──────────────────────────────────────────────────────────────────┐
   │ LAYER 1 — AuthN (Supabase)               "Who are you?"          │
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
   │  never passes client_id, never writes SQL, never knows RLS.      │
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

### 4.3 Lifecycle state machines

```
Client:        Prospective ──► Active ──► Suspended ──► Archived ──► Terminated (TERMINAL)
                  │              │            │              │
                  └──────────────┘            └──────────────┘
                  (dropped)                  (escalation)
                  Archived ◄─────────────────┘
                  Archived ──► Active (re-activation, with approval)

Institution:   Onboarding ──► Active ──► Inactive ──► Archived
                  │            │            │              │
                  └────────────┘            └──────────────┘
                  (abandoned)              (escalation)
                                            Archived ──► Active (re-activation)

Effective state: Institution is operationally Active ONLY if Client is Active.
                 Client Suspended/Archived/Terminated → Institution access gated at runtime,
                 Institution row's own state is NOT mutated (no cascade).
```

---

## 5. Constraints

Non-negotiable constraints this ADR imposes on C-01 implementation:

1. **Repository-first.** Business logic talks only to tenant-aware repositories. No direct SQL in routes/services. No reliance on RLS as the primary filter. (D1)
2. **`client_id` on every tenant-scoped table.** RLS policy on `client_id` is mandatory for every table that holds tenant data. (D1)
3. **UUID v4 PKs for all C-01 entities.** No autoincrement, no C-12 codes for these PKs. (D2)
4. **Slug immutability.** Client subdomain slug is set once at creation and never changes. Display name may change. (D3)
5. **No per-institution subdomains.** Multi-institution navigation is via the in-app switcher only. (D3)
6. **C-01 purity.** Client/Institution/OrgUnit carry identity + lifecycle only. tz/locale/currency/branding/academic-config live in C-08. (D4, D5)
7. **OrgUnit archive-only.** No hard delete for OrgUnits. Type immutable after creation. Moves are audited + cycle-prevented. (D6)
8. **InstitutionType is setup-time only.** Immutable on an Institution after creation. JSONB template, configurable via API (not code). Not a runtime driver. (D7)
9. **Terminated is terminal.** Client `Terminated` has no exit arcs. `Archived` is the only re-activatable inactive state (Client and Institution). (D8, D9)
10. **No cascade on Client suspension.** Institution lifecycle state is preserved during transient Client suspensions; gating is runtime/effective, not persisted. (D9)
11. **C-01 has no FK to C-05.** OrgUnit stays pure structure; academic metadata lives in C-05 with FKs to OrgUnit. (D10)
12. **`homeroom_teacher_id` does not live on OrgUnit.** It belongs to C-05 (academic assignment) or C-02 RoleAssignment scoped to OrgUnit + AcademicYear. (D10)
13. **Cross-tenant write operations require Platform Owner approval.** Client create/suspend/terminate and Institution ownership transfer are Platform-gated. (D11, D12)
14. **Audit events are immutable.** C-11 events keep the ClientId they were recorded with, even across ownership transfers. (D12)

---

## 6. Alternatives Considered (consolidated)

| # | Decision | Primary alternative considered | Reason rejected |
|---|---|---|---|
| D1 | Hybrid (repo + RLS) | RLS only (no repo) | Breaks §12 migration-readiness; couples logic to Postgres. |
| D2 | UUID v4 | Autoincrement serial | Leaks tenant counts; collides on DB migration; breaks §12. |
| D3 | Slug = client, immutable | Per-institution subdomains | Contradicts §5.3; extra routing hop; no portal subdomain for chains. |
| D4 | Identity+lifecycle; config in C-08 | All config intrinsic columns | Branding changes need migrations; rejects C-08; maximally rigid. |
| D5 | Identity+lifecycle; config in C-08 | All config intrinsic columns | Same as D4. |
| D6 | Adjacency list + recursive CTE | Closure table | Overkill for shallow school structures; extra write complexity. |
| D7 | JSONB template column | Hardcoded templates in code | Contradicts C-01 §4 rule 3 ("configurable, not hardcoded"). |
| D8 | Terminated terminal | Terminated → Prospective (re-onboard same id) | Blurs audit/billing continuity; usual practice is a new Client record. |
| D9 | Runtime effective-state gating | Cascade state changes on Client suspension | Mass state churn; must restore pre-suspension state; race conditions. |
| D10 | C-01 structure; C-05 academic layer | C-05 owns Grade/Class; C-01 only Dept/Faculty | Contradicts c-01 doc; breaks C-01 entity ownership; redesigns D7. |
| D11 | Tiered delegation | Platform-centralized (stricter) | Platform bottleneck for institution lifecycle; less self-service. |
| D12 | Full transfer; immutable audit | Split at transfer point (watermark) | Every historical query needs watermark logic; reports straddle clients. |

---

## 7. Future Evolution

Under what conditions would this ADR be revisited?

- **D1 (isolation):** If the platform migrates to separate-schema or separate-database (§11 future path), RLS policies are dropped and a new repository implementation is written; business logic is untouched. RLS may also be added as a hardening layer on a future deployment that initially shipped app-level only.
- **D2 (IDs):** If pagination/indexing benchmarks show value in time-ordered IDs, UUID v4 can be swapped for UUID v7 — drop-in, no schema change.
- **D3 (slug):** If a client legally requires the URL itself to change on rebrand, revisit the immutability rule and add a historical-slug redirect table. Custom domains (e.g., `attendance.schoola.com`) remain a documented future fallback over subdomains.
- **D6 (hierarchy):** If school structures grow deep or subtree queries become hot, revisit adjacency-list vs closure-table (the repository contract makes this an implementation swap).
- **D8 (Client lifecycle):** If a regulatory requirement forces "terminated client's historical data must remain queryable under the original client," revisit D12's watermark alternative for the terminated case.
- **D12 (ownership transfer):** If a client legally demands historical operational data stay with the seller on transfer, revisit the watermark alternative (currently rejected).
- **Temporal/client_id history (Q10):** Do NOT pre-build row-history tracking (temporal tables / per-row client_id history) now. The full-transfer model (D12) + immutable C-11 audit log already cover provenance. Revisit only if a concrete near-term requirement for per-row ownership history emerges — that would be a D12 redesign, not a toggle. No temporal/history tables are built in Phase 1.
- **General:** Each decision is independently reversible without rewriting the others — the decision set is cohesive but not tightly coupled.

---

## 8. Spec-Resolution Decisions (Q1–Q10)

The following 10 implementation questions were surfaced during spec-impact analysis and resolved to fully unblock the C-01 technical spec, API contracts, and database schema. They are decisional input to those artifacts, recorded here so the ADR is the single complete input fed to sdd-stack.

| # | Question | Resolution |
|---|---|---|
| Q1 | RLS on the `client` table itself (it defines the tenant — no `client_id` column) | **Self-visible.** A Client Director can read their own client row. RLS policy: `id = current_client_id`. |
| Q2 | Storage of "configurable" enums (`legal_entity_type`, OrgUnit `type`, InstitutionType name) | **Lookup tables** (id + name, FK-referenced). Adding a new type = a data insert, no code/deploy. Honors D7's "configurable, not hardcoded" rule. |
| Q3 | Approval record storage for lifecycle transitions | **Separate `Approval` table** — one row per approval: `requested_by`, `approved_by`, `status`, `timestamps`. Supports pending-approval state and the request→approve flow in D8/D9. |
| Q4 | Async events on lifecycle changes / ownership transfer | **C-11 audit only** (synchronous, internal). No message broker for C-01. Consumers wire in directly or poll. Async events deferred until a cross-capability event bus requirement materializes. |
| Q5 | API base URL shape — subdomain-resolved vs client-in-path | **Subdomain-resolved.** `POST /api/v1/institutions` with client implicit from subdomain (per D3). Supersedes the c-01-explained illustrative example (`POST /api/clients/{slug}/institutions`). The explainer doc must get a "superseded" note pointing to the API contracts doc. Platform-Owner-only endpoints live under a platform-scoped base. |
| Q6 | OrgUnit cycle-prevention enforcement location | **App-side** (the repository checks before update). DB schema must NOT add a duplicating trigger. Matches the repository-first principle (D1). |
| Q7 | OrgUnit move audit storage | **C-11 only** — generic audit event `action="org_unit_moved"`, `payload={from_parent, to_parent, moved_by, ...}`. No dedicated `org_unit_move_event` table. |
| Q8 | Lifecycle-event history table partitioning in Phase 1 | **Defer.** Phase 1 = no partitioning. Revisit when volume matters (monthly partitioning on `entered_at` is the candidate). |
| Q9 | Slug-collision "suggestions" behavior | **Return "taken" with no suggestions.** No auto-suffix, no near-match algorithm. Caller must propose a new slug. |
| Q10 | Pre-build temporal/client_id row-history tracking | **Do not pre-build.** Revisit-only (see §7 above). Full-transfer (D12) + immutable C-11 audit covers provenance. |

---

> **ADR Status:** This ADR records the implementation-level decisions for C-01. It does **not** replace the C-01 technical spec, API contracts, or database schema (the 🥇/🥈 artifacts to be authored next) — it is the decisional input those artifacts will be built against.
