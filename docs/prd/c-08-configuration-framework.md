# PRD — C-08 Configuration Framework

> **Capability:** C-08 Configuration Framework
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-07-05
> **Decisional source of truth:** This PRD. All 16 decisions (D1–D16) were locked in a grill-me session on 2026-07-05.
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-08; `docs/platform-capabilities/c-08-configuration-framework-explained.md`; `docs/architecture/architecture-v1.md`; `docs/architecture/adr-platform-software-architecture.md`; `docs/requirements/functional-requirements.md` §1.8
> **Scope note:** This is a **product** requirements document. It is deliberately free of implementation detail (DB column types, API shapes, RLS policy text, Casbin rule syntax). Those belong in the spec/design phase, sourced from this PRD. Decisions are referenced by ID (e.g., "per D1") rather than re-specified in implementation.

---

## 1. Problem

The School ERP platform must support many independent customer organizations (Clients) each operating one or more institutions (schools/colleges). The behavior of every business module — Attendance, Fees, Homework, Exams, Communication, etc. — is inherently configurable: an attendance cutoff time, a late-fee percentage, a grading scale, a date format, a notification channel preference, an enable/disable feature toggle. Without a centralized configuration framework, every setting ends up hardcoded in code, every override ends up in a module-specific `config` JSONB column, and every change requires a code deploy + application restart. The platform cannot scale to multiple tenants with different policies under that model.

C-08 is the **runtime configuration nervous system** of the platform. It owns a single, central key-value store with **typed values**, **scope inheritance** (Platform → Client → Institution → Module), **lightweight audit**, and **in-memory resolution with hot reload**. Every other capability and module reads configuration from C-08 instead of hardcoding values. Per architecture-v1 §3 and the platform non-negotiable rules, "configuration requires no code changes" and "modules read, don't own." C-08 is the implementation of that contract.

Per the platform dependency map, C-01b (Tenant & Institution Domain) depends on C-08 — C-08 was originally sequenced at P2 in Phase 1, immediately after C-01. It is being built now to unblock C-05 (Academic Structure), C-06 (Relationship Management), and every business module's configurable behavior.

---

## 2. Goals & Non-goals

### 2.1 In scope — C-08 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **ConfigurationKey** (typed, named setting registry) | D3, D8, D9, D12 | A registry of every key that exists on the platform: name, type, default, merge_strategy, category, module namespace, deprecation status. Platform-Owner-managed. |
| **ConfigurationValue** (scope-bound override) | D3, D4, D5, D7, D10 | An override of a key's value at a specific scope (Platform / Client / Institution). The default value lives on the key, not in a Platform-scope value row. |
| **ConfigurationScope** (Platform → Client → Institution → Module) | D1, D14 | A 4-level inheritance chain. **Module scope is deferred to Phase 2** (per D14). Phase 1 implements Platform + Client + Institution only. |
| **FeatureToggle** (boolean key with is_feature_toggle=true) | D3, D8 | A subtype of ConfigurationKey for module on/off switches. Reuses the same table — no separate entity. |
| **ConfigurationAudit** (lightweight change log) | D3, D6 | Who/what/when for every key create/update/delete and every value create/update/delete. No before/after values stored. |
| **Scope inheritance + merge semantics** | D1, D2 | Resolution walks: institution → client → platform. Returns first match. Lists/JSONs use strict replace by default; opt-in `append_lists` / `deep_merge` per key. |
| **In-memory resolution cache with hot reload** | D5, D7 | All keys + values loaded into an in-memory dict on app startup. On UPDATE, the in-memory dict is patched immediately in the primary instance. Other instances refresh via PostgreSQL NOTIFY/LISTEN (≤5s lag). |
| **Scope-based edit authorization** (3-tier by role) | D4, D15 | Platform Owner owns Platform scope + the key registry. Client Director owns Client scope + their institutions. Institute Admin owns their own Institution scope. Teacher/Student read-only. |
| **C-04-integrated permission model** (centralized RBAC) | D15 | All C-08 permissions go through the existing Casbin enforcer. 8 new permissions added in the C-08 migration. C-04 stays the single source of truth (Non-Negotiable Rule 3). |
| **Soft-delete + deprecation** | D13 | Keys are soft-deleted via `is_deprecated=true`. New overrides blocked; reads continue to work. Auto-hide from UI after 90 days. Hard delete is NOT supported. |
| **Default-required key registration** | D9 | Every ConfigurationKey MUST have a non-null default_value at the platform level. No key can exist without a default. Modules can always trust `config.get(key)` returns a value. |
| **Type-only validation at write** | D8 | C-08 validates that a value matches the declared type (string, number, boolean, json, date). Business constraints (HH:MM format, enum of allowed values, regex) are validated by the CONSUMING module, not C-08. |
| **Resolution API with explicit scope kwargs** | D10 | `config.get('key', institution_id=..., client_id=...)` — function takes the key and the resolution context. Works in any context (request, background job, migration). TenantContext is NOT required. |
| **Phase 1 seed catalog (15 keys)** | D12 | 15 keys across 5 categories seeded in Alembic migration `009_c08_configuration.py`: Business Rules (4), Display (3), Academic (3), Notifications (2), Homework (2), Platform (1). |
| **Full REST surface** (~12 endpoints under `/api/v1/config/`) | D11 | Key CRUD (PO) + Value CRUD (role-scoped) + Audit (read) + Resolve (debug). |
| **Tenant isolation via RLS** | D1, D4 | RLS policies on `configuration_value` filter by `client_id` / `institution_id` consistent with existing patterns. Platform-scope values are tenant-agnostic. |
| **Manifest registration** | D16 | `backend/kernel/manifest.py` includes C-08 in the kernel manifest list. App factory wires it. |
| **Flow documents** | D16 | 4 flow documents in `school_erp_flow/c08/` showing end-to-end journeys. |

### 2.2 Out of scope — owned by other capabilities or deferred to Phase 2

| Concern | Owned by / Phase | Per | Notes |
|---|---|---|---|
| **Module-scope overrides** | C-08 Phase 2 | D1, D14 | A 4th scope level (Module) where overrides can be at a per-module-instance level. Deferred. In Phase 1, the `module` column on ConfigurationKey is a NAMESPACE/CATEGORY only, not a runtime scope. |
| **Admin UI for editing config** | Future (Phase 2) | D16 | Phase 1 uses Swagger UI to edit config. A proper admin UI (with key list, value editor, scope selector, audit viewer) is a separate build. |
| **Encrypted at-rest for sensitive values** | Future (Phase 2+) | — | Some config values (API keys, secrets) may need encryption. Phase 1 stores all values in plain JSONB. The `type=json` could carry a secret, but it's not encrypted. |
| **Per-key constraint validation (regex, min/max, enum)** | C-08 Phase 2 | D8 | Phase 1 supports type-only validation + an optional `allowed_values` JSONB array as hint. Future: full constraint system enforced at write. |
| **Multi-region config replication** | Future (Phase 3+) | — | Single-region in-memory cache; multi-region uses NOTIFY in same region. |
| **Configuration export/import** | Future (Phase 2) | — | Bulk copy config from one institution to another. Useful for chains. |
| **Configuration history/rollback UI** | Future (Phase 2) | D6 | Light audit captures who/what/when only. No before/after values means no UI rollback. A heavier audit (with diffs) is a future enhancement. |
| **Dynamic config (computed values, expressions)** | Future | — | Phase 1 values are static literals. No expressions, no function references, no env-var interpolation. |
| **Environment variables** | DevOps | — | DB connection strings, app secrets, etc. are env vars, not C-08 keys. C-08 is for runtime-configurable behavior. |
| **User preferences (theme, language)** | C-02 | — | Per-user display preferences are user-level, not platform-level. C-02 owns `UserPreference`. |
| **Module-specific business logic** | Business Modules | — | C-08 stores the *value*; modules implement the *behavior*. |
| **Hard delete of keys/values** | Never | D13 | Soft delete only. No hard delete API. |

### 2.3 Explicit non-goals for Phase 1

- No Module scope (per D14).
- No admin UI (per D16).
- No before/after audit values (per D6).
- No encryption at rest (Phase 2).
- No hard delete (per D13).
- No expression/computed values.
- No env-var interpolation in C-08 values.

---

## 3. Users / Personas

C-08 has four primary actors. Their precise role definitions and Casbin encoding are owned by C-04; C-08 only defines what each persona can do against C-08 entities.

| Persona | Who they are | Scope | C-08 reach (per D4, D15) |
|---|---|---|---|
| **Platform Owner** | The SaaS provider operating the platform. | All tenants + the platform itself. | **ALL** C-08 operations: create/update/deprecate keys (the key registry), set Platform-scope values, view all values across all tenants, read all audit. |
| **Client Director** | The client's top administrator (e.g., trust director, chain owner). | Own client only. | Set Client-scope values for their own client. Set Institution-scope values for any institution in their client. **Cannot** create or modify keys (registry is PO-only). |
| **Institution Admin / Principal** | The institution's top in-building administrator. | Own institution only. | Set Institution-scope values for their own institution. **Cannot** create or modify keys. **Cannot** set Client-scope values. |
| **Module Developer** (technical persona) | The engineer who builds a business module. | Code-level integration. | Calls `config.get('key', institution_id=..., client_id=...)` in their module code. Read-only API surface for runtime consumption. Registers new keys via the API (as Platform Owner acting on behalf of the platform). |
| **Teacher / Student** | End-user roles. | Own institution. | Read-only. (No C-08 endpoints that need write access for these roles.) |

All writes are audited via C-08's own `configuration_audit` table with actor identity. The Platform Owner acts via the standard Platform Owner JWT path (no `Host` header needed); Client Director and Institute Admin act via their tenant-scoped JWT with `Host: <slug>.localhost` (per C-03 + C-04 conventions).

---

## 4. User Journeys

| # | Persona | Journey | Key PRD refs |
|---|---|---|---|
| **J1** | Platform Owner | **Seed a new configuration key.** PO opens Swagger, POSTs `/api/v1/config/keys` with `key=attendance.markingCutoffTime`, `type=string`, `default=10:00 AM`, `category=Business Rules`, `module=attendance`. Audit row created. From this moment every institution that doesn't override gets `10:00 AM`. | D3, D8, D9, D11, D12, D15 |
| **J2** | Institute Admin | **Override a value for their institution.** Admin logs in, POSTs `/api/v1/config/values` with `key=attendance.markingCutoffTime`, `scope=institution`, `scope_id=<my institution>`, `value=11:00 AM`. In-memory dict patched in primary instance; NOTIFY wakes other instances. Resolution for that institution now returns `11:00 AM`; other institutions still get `10:00 AM`. | D3, D4, D5, D7, D10, D11, D15 |
| **J3** | Client Director | **Set a Client-scope value that all their institutions inherit.** CD POSTs `key=display.dateFormat`, `scope=client`, `scope_id=<my client>`, `value=MM/DD/YYYY`. Every institution in the client now resolves to that date format unless an institution overrides. | D1, D3, D4, D7, D10, D11 |
| **J4** | Module Developer (in code) | **Read config from a business module.** In a route handler, call `config.get('attendance.statuses', institution_id=...)`. Returns the resolved list for the user's institution. For `attendance.statuses` (merge_strategy=append_lists), if Platform default is `['present', 'absent']` and the institution overrides with `['half_day']`, the resolved list is `['present', 'absent', 'half_day']`. | D2, D5, D8, D10 |
| **J5** | Platform Owner | **Deprecate an old key, create a new one.** PO PATCHes `attendance.markingCutoffTime` with `is_deprecated=true`, `replacement_key=attendance.cutoffTime`. New overrides blocked. Reads still work for 90 days while modules migrate. After 90 days the key auto-hides from Swagger list. | D13 |
| **J6** | Platform Owner | **Debug resolution.** PO POSTs `/api/v1/config/resolve` with `key=attendance.statuses`, `scope=institution`, `scope_id=<inst X>`. Response shows the resolved value AND the source (`institution:<inst X>`, or `client:<client Y>`, or `platform:default`). Helps diagnose "why isn't this institution getting the value I expect?" | D11 |
| **J7** | Any user | **List overrides for my scope.** A Client Director calls `GET /api/v1/config/values?scope_type=client`. Sees only their client's values. An Institute Admin calls `GET /api/v1/config/values?scope_type=institution`. Sees only their institution's values. Platform Owner sees all. | D4, D11, D15 |
| **J8** | Platform Owner | **Read audit log.** PO calls `GET /api/v1/config/audit?key=attendance.markingCutoffTime`. Sees who created the key, who set which overrides, when, at which scope. No before/after values (per D6). | D6, D11 |

---

## 5. Entities & Data Model

### 5.1 ConfigurationKey

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `key` | TEXT UNIQUE NOT NULL | Dotted namespace, e.g., `attendance.markingCutoffTime`. |
| `type` | ENUM NOT NULL | One of: `string`, `number`, `boolean`, `json`, `date`. |
| `default_value` | JSONB NOT NULL | The platform-level default. **Required** (per D9). |
| `merge_strategy` | TEXT NOT NULL DEFAULT 'replace' | One of: `replace`, `append_lists`, `deep_merge` (per D2). |
| `category` | ENUM NOT NULL | One of: `Business Rules`, `Display`, `Academic`, `Notifications`, `Feature Toggles`, `Platform`, `Integrations`. |
| `module` | TEXT NULLABLE | Namespace, not a runtime scope (per D14). E.g., `attendance`, `fees`, `homework`. |
| `description` | TEXT NOT NULL | Human-readable explanation. |
| `is_feature_toggle` | BOOLEAN NOT NULL DEFAULT FALSE | If true, the value is a boolean used as an on/off switch. |
| `is_deprecated` | BOOLEAN NOT NULL DEFAULT FALSE | Soft-delete flag (per D13). |
| `deprecated_at` | TIMESTAMPTZ NULLABLE | Set when `is_deprecated` flips to true. Auto-hide after 90 days. |
| `replacement_key` | TEXT NULLABLE | If deprecated, points to the new key (per D13). |
| `allowed_values` | JSONB NULLABLE | Optional hint (per D8). NOT enforced at write. |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |

### 5.2 ConfigurationValue

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `key_id` | UUID FK → configuration_key | The key being overridden. |
| `scope_type` | ENUM NOT NULL | One of: `platform`, `client`, `institution`. (Module scope deferred — per D14.) |
| `scope_id` | UUID NULLABLE | FK to `client` or `institution`. NULL for `platform` scope (platform values are tenant-agnostic and stored on the key's `default_value` — there is no need for a separate Platform-scope value row). |
| `client_id` | UUID FK → client | Tenant isolation (RLS). Always populated. |
| `institution_id` | UUID FK → institution NULLABLE | Tenant isolation (RLS). Populated for `scope_type=institution`. |
| `value` | JSONB NOT NULL | The override value. |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |
| `updated_by` | UUID NOT NULL | User ID who last modified. |

**Uniqueness:** (`key_id`, `scope_type`, `scope_id`) UNIQUE. At most one override per (key, scope, scope_id).

### 5.3 ConfigurationAudit

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | — |
| `key_id` | UUID FK → configuration_key | — |
| `scope_type` | ENUM NULLABLE | `platform`, `client`, `institution`, or NULL for key-registry events. |
| `scope_id` | UUID NULLABLE | — |
| `action` | ENUM NOT NULL | One of: `key_created`, `key_updated`, `key_deprecated`, `value_created`, `value_updated`, `value_deleted`. |
| `actor_user_id` | UUID NULLABLE | NULL if system action (e.g., seeded by migration). |
| `actor_role` | TEXT NULLABLE | Snapshot of the role at time of action. |
| `timestamp` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |

**No before/after values stored** (per D6). Lightweight, fast, and storage-cheap.

---

## 6. Functional Requirements

Each requirement references the locked decision(s) it derives from.

### 6.1 Configuration Key Registry

| ID | Requirement | Per |
|---|---|---|
| FR-01 | The system MUST support CRUD on the ConfigurationKey registry. Create/Update/Delete are Platform-Owner-only. | D4, D11, D15 |
| FR-02 | Every ConfigurationKey MUST have a non-null `default_value` at the platform level. Creation fails with 400 if missing. | D9 |
| FR-03 | `merge_strategy` defaults to `replace` and accepts `replace`, `append_lists`, `deep_merge`. | D2 |
| FR-04 | `type` MUST be one of `string`, `number`, `boolean`, `json`, `date`. | D8 |
| FR-05 | `category` MUST be one of the 7 enum values. | D12 |
| FR-06 | The system MUST support listing keys with pagination + filters (`category`, `module`, `is_deprecated`, `is_feature_toggle`). | D11 |
| FR-07 | The system MUST support soft-deletion: PATCH `is_deprecated=true` + `replacement_key`. Hard delete is NOT exposed. | D11, D13 |
| FR-08 | After 90 days from `deprecated_at`, deprecated keys MUST auto-hide from the list endpoint (filtered out by default). The row remains in the DB. | D13 |

### 6.2 Configuration Value CRUD

| ID | Requirement | Per |
|---|---|---|
| FR-09 | The system MUST support CRUD on ConfigurationValue overrides. | D11 |
| FR-10 | POST/PATCH/DELETE on values MUST enforce role-and-scope checks: Platform Owner can write at any scope; Client Director can write at Client scope (own client) and Institution scope (own client's institutions); Institute Admin can write at Institution scope (own institution only). | D4, D15 |
| FR-11 | At most one value row per (`key_id`, `scope_type`, `scope_id`). Duplicate POSTs return 409. | §5.2 |
| FR-12 | GET on values MUST filter by the caller's effective scope: Platform Owner sees all; Client Director sees own client; Institute Admin sees own institution. | D4, D11 |
| FR-13 | The system MUST validate at write time that the value matches the declared type. Scalars must be of the correct primitive type. JSON values must parse as valid JSON. | D8 |
| FR-14 | The system MUST support clearing an override (DELETE), causing the resolution to fall back to the parent scope. | D11 |

### 6.3 Scope Inheritance & Merge Semantics

| ID | Requirement | Per |
|---|---|---|
| FR-15 | Resolution walks: institution → client → platform. Returns the first match. | D1, D5 |
| FR-16 | For `merge_strategy=replace` (default), the child value completely replaces the parent. | D2 |
| FR-17 | For `merge_strategy=append_lists`, list values are unioned (set semantics, preserving order). Object values are deep-merged. | D2 |
| FR-18 | For `merge_strategy=deep_merge`, JSON values are merged per RFC 7396 (objects deep-merged, lists replaced). | D2 |
| FR-19 | Scalars (string, number, boolean, date) ALWAYS use replace regardless of `merge_strategy`. | D2 |
| FR-20 | When no override exists at any scope, the resolution MUST return the key's `default_value`. | D9 |

### 6.4 Resolution API

| ID | Requirement | Per |
|---|---|---|
| FR-21 | The system MUST expose a programmatic `config.get(key, institution_id=None, client_id=None)` function that returns the resolved value for the given scope. | D10 |
| FR-22 | `config.get` MUST work in any context: FastAPI request, background job, migration, test. It MUST NOT depend on TenantContext. | D10 |
| FR-23 | The system MUST expose a debug endpoint `POST /api/v1/config/resolve` that returns the resolved value AND its source (which scope provided it). | D11 |
| FR-24 | The system MUST expose a debug endpoint `GET /api/v1/config/resolve/{key}?institution_id=&client_id=` for quick lookups. | D11 |

### 6.5 In-Memory Cache & Hot Reload

| ID | Requirement | Per |
|---|---|---|
| FR-25 | On app startup, the system MUST load all ConfigurationKey rows and all ConfigurationValue rows into in-memory dicts keyed by `(scope_type, scope_id, key_id)`. | D5 |
| FR-26 | `config.get` MUST be served from the in-memory dict, not from a DB query. | D5 |
| FR-27 | On any UPDATE to ConfigurationKey or ConfigurationValue, the system MUST patch the in-memory dict in the primary instance immediately. | D5, D7 |
| FR-28 | The system MUST emit a PostgreSQL NOTIFY on the channel `config_changes` after every UPDATE. Other instances MUST LISTEN on this channel and reload their in-memory dicts on receipt. | D7 |
| FR-29 | Single-instance deployments MUST see instant propagation (no NOTIFY needed). Multi-instance deployments MUST propagate within ≤5 seconds. | D7 |

### 6.6 Audit

| ID | Requirement | Per |
|---|---|---|
| FR-30 | The system MUST write a `configuration_audit` row for every key create/update/deprecate and every value create/update/delete. | D6 |
| FR-31 | Each audit row MUST record: `key_id`, `scope_type`, `scope_id`, `action`, `actor_user_id`, `actor_role`, `timestamp`. | D6 |
| FR-32 | The system MUST NOT store before/after values in the audit row. | D6 |
| FR-33 | Audit rows are append-only — no UPDATE or DELETE on `configuration_audit`. | D6 |
| FR-34 | The system MUST expose `GET /api/v1/config/audit?key=&scope_type=&scope_id=&action=&actor_user_id=&from=&to=` with role-scope filtering. | D11 |

### 6.7 Authorization (C-04 Integration)

| ID | Requirement | Per |
|---|---|---|
| FR-35 | The C-08 migration MUST insert 8 new permissions into the C-04 `permission` table: `config.key.create`, `config.key.update`, `config.key.deprecate`, `config.key.list`, `config.value.create`, `config.value.update`, `config.value.delete`, `config.audit.read`. | D15 |
| FR-36 | The C-08 migration MUST insert role-permission mappings: PlatformOwner gets all 8; ClientDirector gets `config.value.{create,update,delete}` + `config.key.list` + `config.audit.read`; InstituteAdmin gets `config.value.{create,update,delete}` (institution scope) + `config.key.list` + `config.audit.read`. | D4, D15 |
| FR-37 | Every C-08 endpoint MUST use the existing `require_permission(...)` dependency from `backend/kernel/authz/dependencies.py`. C-08 MUST NOT implement its own permission system. | D15 |
| FR-38 | Scope checks (institution_id/client_id) MUST be enforced in the service layer in addition to the role check. A Client Director cannot write at another client's institution even if they somehow have the `config.value.create` permission. | D4 |

### 6.8 Seed Catalog

| ID | Requirement | Per |
|---|---|---|
| FR-39 | The Alembic migration `009_c08_configuration.py` MUST seed 15 keys across 5 categories: 4 Business Rules, 3 Display, 3 Academic, 2 Notifications, 2 Homework, 1 Platform. | D12 |
| FR-40 | The `attendance.statuses` key MUST be seeded with `type=json`, `merge_strategy=append_lists`, `default=['present', 'absent']`, `category=Business Rules`, `module=attendance`. | D12 |
| FR-41 | The migration MUST also insert the 8 C-04 permissions + role-permission mappings from FR-35/FR-36. | D15 |

### 6.9 Tenant Isolation

| ID | Requirement | Per |
|---|---|---|
| FR-42 | `configuration_value` MUST have an RLS policy that filters by `client_id` (and `institution_id` when populated), consistent with the existing RLS pattern from migration 007. | D1, D4 |
| FR-43 | Platform-scope values are NOT stored as rows (the platform default lives on the key's `default_value` field). Platform Owner is not subject to RLS on `configuration_value` (consistent with Platform Owner bypass patterns). | D1 |
| FR-44 | `configuration_key` is global (no RLS); all roles can read all keys (subject to `config.key.list` permission). | D11, D15 |

### 6.10 REST API Surface

| ID | Requirement | Per |
|---|---|---|
| FR-45 | The system MUST expose the 12 endpoints listed in §2.1 (D11) under `/api/v1/config/`. | D11 |
| FR-46 | Every endpoint MUST have an OpenAPI `summary` field. | §6 conventions |
| FR-47 | The C-08 router MUST be registered via the kernel manifest and served behind the same auth/middleware chain as all other modules. | D16 |

---

## 7. Out-of-Scope (Phase 1) — Detailed

Per D14, D16, and §2.2, the following are explicitly OUT of Phase 1:

- **Module-scope overrides** — a 4th scope level. Deferred to Phase 2. The `module` column on ConfigurationKey is a namespace only.
- **Admin UI** — a proper web UI for editing config. Phase 1 uses Swagger. A frontend page is a separate build.
- **Before/after audit values** — D6 says light audit. No diffs stored. No rollback UI.
- **Encrypted at-rest** — secrets are stored in plain JSONB. Phase 2+ would add encryption.
- **Hard delete** — soft delete only (D13).
- **Computed/expression values** — values are static literals.
- **Env-var interpolation** — values are not interpolated from env vars at read time.
- **Per-key regex/min/max/enum enforcement** — type-only validation (D8).
- **Multi-region replication** — single-region in-memory cache.
- **Config export/import** — bulk copy between institutions.
- **Dynamic config reload via file watcher** — only DB-driven reload.

---

## 8. Dependencies

| Capability | Dependency Type | Rationale |
|---|---|---|
| **C-01** Tenant & Institution | Required (upstream) | C-08 `ConfigurationValue.scope_id` FKs to `client` and `institution` from C-01. RLS uses C-01's `client_id` / `institution_id` columns. |
| **C-02** Identity & User | Required (upstream) | `configuration_audit.actor_user_id` FKs to `app_user`. `configuration_value.updated_by` FKs to `app_user`. |
| **C-03** Authentication | Required (upstream) | C-08 routes use the existing JWT auth + TenantContext from C-03. Platform Owner JWT path applies. |
| **C-04** Authorization | Required (upstream) | C-08 permissions live in C-04's `permission` table. C-08 routes use C-04's `require_permission` dependency. Casbin enforcer is loaded at startup. |
| **C-11** Audit & Observability | Indirect | C-08 has its own `configuration_audit` table (lightweight). C-11's full audit pipeline (async, queryable, retention-leveled) is Phase 2 work; Phase 1 emits C-11 events for high-level config actions (PO creates a key, etc.) but the granular audit is in C-08's own table. |
| **PostgreSQL NOTIFY/LISTEN** | Infrastructure | Required for the multi-instance cache invalidation (D7). |
| **All business modules** | Downstream (consumer) | Modules read config from C-08 instead of hardcoding. Phase 1: no module integration required (the seed catalog is enough to demonstrate). Phase 2: each module migrates from hardcoded values to `config.get()` calls. |

---

## 9. Acceptance Criteria

Phase 1 is "done" when ALL of the following are true:

### 9.1 Database & Migration

- [ ] Migration `009_c08_configuration.py` exists and applies cleanly on a fresh DB and on the existing cloud Supabase DB.
- [ ] After applying the migration, `SELECT COUNT(*) FROM configuration_key` returns 15.
- [ ] After applying the migration, `SELECT COUNT(*) FROM configuration_audit WHERE actor_user_id IS NULL` returns 15 (the 15 seed keys, system-actor).
- [ ] The migration also inserts 8 permissions into C-04's `permission` table + 3 role-permission mappings (PlatformOwner, ClientDirector, InstituteAdmin).

### 9.2 API

- [ ] All 12 endpoints under `/api/v1/config/` are reachable via Swagger at `http://127.0.0.1:8000/docs`.
- [ ] All endpoints have OpenAPI `summary` fields.
- [ ] Swagger "Authorize" works (Bearer token from Platform Owner login or tenant-scoped login).

### 9.3 Functional

- [ ] Platform Owner can create a new key via `POST /api/v1/config/keys` and see it appear in `GET /api/v1/config/keys`.
- [ ] Platform Owner can set a Platform-scope default by setting `default_value` on a key (no Platform-scope value row needed).
- [ ] Client Director can create a Client-scope value via `POST /api/v1/config/values` with `scope_type=client`.
- [ ] Institute Admin can create an Institution-scope value via `POST /api/v1/config/values` with `scope_type=institution` for their own institution only.
- [ ] Institute Admin attempting to create a value for ANOTHER institution receives 403.
- [ ] Client Director attempting to create a value for ANOTHER client's institution receives 403.
- [ ] `config.get('attendance.markingCutoffTime', institution_id=inst_A)` returns the Institution value if set, else the Client value if set, else the key's `default_value`.
- [ ] `config.get('attendance.statuses', institution_id=inst_A)` with `merge_strategy=append_lists` returns the union of [Platform default, Client override, Institution override] for list values.
- [ ] Updating a value via `PATCH /api/v1/config/values/{id}` patches the in-memory dict AND emits a NOTIFY.
- [ ] `GET /api/v1/config/resolve/{key}?institution_id=...` returns the resolved value plus the source (which scope provided it).
- [ ] `GET /api/v1/config/audit?key=attendance.markingCutoffTime` returns audit rows including the create event + every value change.

### 9.4 Authorization

- [ ] Every C-08 endpoint is protected by `require_permission(...)`. Unauthenticated requests get 401.
- [ ] Authenticated users without the right permission get 403.
- [ ] A Teacher (no C-08 permissions) cannot write to any endpoint; reads work if they have `config.key.list`.
- [ ] A Platform Owner can access ALL endpoints, including key-registry CRUD.
- [ ] A Client Director cannot create/update/delete keys (key-registry is PO-only).

### 9.5 Deprecation

- [ ] `PATCH /api/v1/config/keys/{id}` with `is_deprecated=true` and `replacement_key` succeeds; the key remains readable.
- [ ] Attempting to create a new value for a deprecated key returns 409.
- [ ] After 90 days (tested by manually setting `deprecated_at` to a past date), the deprecated key is hidden from the default list response.

### 9.6 Performance

- [ ] `config.get(...)` returns in < 1ms (in-memory dict lookup).
- [ ] App startup loads all config in < 500ms for a DB with 15 keys and 0 value overrides (i.e., the seed-only case).

### 9.7 Tests

- [ ] ≥25 unit + integration tests pass.
- [ ] Tests cover: key CRUD, value CRUD, scope inheritance, all 3 merge strategies, audit, deprecation, in-memory cache, NOTIFY propagation, RLS, permission enforcement, scope checks.
- [ ] No regression: existing 300 tests still pass.

### 9.8 Documentation

- [ ] 4 flow documents in `school_erp_flow/c08/`:
  - `_c08_flow_01_key_creation.md` — PO creates a key, sets default.
  - `_c08_flow_02_value_override.md` — CD/Admin overrides for their scope; resolution.
  - `_c08_flow_03_merge_semantics.md` — append_lists example with attendance.statuses.
  - `_c08_flow_04_audit_and_deprecation.md` — audit log + deprecate-old/create-new.
- [ ] An index file `_c08_flow_index.md` referencing all 4 flows.

---

## 10. Open Questions

**None.** All 16 decisions (D1–D16) were locked in the grill-me session on 2026-07-05. The PRD is ready for impact classification → proposal/spec/design/tasks.

If new questions arise during the SDD flow (e.g., while drafting the design or applying the implementation), they will be added back here with their resolution.

---

## 11. References

### 11.1 Platform & Architecture

- `docs/platform-capabilities/platform-capabilities-v3.md` §C-08 (lines 655-700) — formal C-08 definition
- `docs/platform-capabilities/c-08-configuration-framework-explained.md` — design explainer with 7 examples
- `docs/platform-capabilities/platform-capabilities-v3.md` §4 (Dependency Map, lines 1717-1764) — C-08 is Level 1
- `docs/platform-capabilities/platform-capabilities-v3.md` §5.1 (Phase 1 Sequencing, lines 1768-1790) — C-08 is P2
- `docs/platform-capabilities/platform-capabilities-v3.md` §7 (Non-Negotiable Rules, lines 1866-1900) — Rule 11: "Configuration requires no code changes"
- `docs/architecture/architecture-v1.md` §3 (Platform-First Evaluation)
- `docs/architecture/adr-platform-software-architecture.md` — modular monolith, kernel split

### 11.2 Existing Capabilities (Upstream Dependencies)

- `docs/specs/tenant-institution/spec.md` — C-01 spec (institution lifecycle, RLS patterns)
- `docs/specs/platform-owner-separation/spec.md` — Platform Owner JWT path
- `openspec/specs/tenant-institution/spec.md` — live C-01 spec
- `openspec/specs/platform-owner-separation/spec.md` — live Platform Owner spec
- `openspec/specs/platform-owner-followups/spec.md` — Platform Owner followups

### 11.3 Existing Implementation Patterns to Follow

- `backend/kernel/authz/` — Casbin enforcer, permissions, `require_permission` dependency
- `backend/kernel/user/` — kernel module pattern (manifest, routes, services, repos, models, dependencies)
- `backend/kernel/middleware.py` — JWT verification, TenantContext, platform owner detection
- `backend/kernel/audit.py` — `AuditEmitter` protocol
- `backend/kernel/repo_base.py` — `TenantAwareRepositoryBase` (for tenant isolation)
- `backend/migrations/versions/007_platform_owner_rls.py` — RLS pattern for platform-owner bypass
- `backend/migrations/versions/008_nullable_institution_id.py` — recent migration example

### 11.4 Templates

- `docs/reference/document-template.md` — PRD template
- `docs/prd/fees-module.md` — example business-module PRD
- `docs/prd/homework-module.md` — example business-module PRD
- `docs/prd/c-01-tenant-institution.md` — example kernel PRD

---

> **End of PRD**  
> **Version:** 1.0  
> **Date:** 2026-07-05  
> **Decisions:** 16 locked (D1–D16)  
> **Status:** Ready for SDD flow (impact classification → proposal → spec → design → tasks → apply → verify → archive)
