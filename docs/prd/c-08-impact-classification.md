# Impact Classification — C-08 Configuration Framework

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-08 — Configuration Framework
> **Decisional inputs:** `docs/prd/c-08-configuration-framework.md` (PRD), grill-me session (16 locked decisions, D1–D16, 2026-07-05)
> **Verification:** `openspec/specs/tenant-institution/spec.md` exists (C-01). `openspec/specs/identity-user-management/spec.md` exists (C-02). `openspec/specs/authentication/spec.md` exists (C-03). No `authorization` or `configuration` spec exists yet. `openspec/specs/platform-owner-separation/spec.md` and `platform-owner-followups/spec.md` exist (Phase 1.5).
> **Capability layer:** **Kernel** (lives in `backend/kernel/config/`, not `backend/business/`)

---

## Classification

- Domain status: **NEW** (C-08 has no existing OpenSpec spec)
- Delta type: **ADDED** (new domain) + **MODIFIED** (C-04 behavioral contract: C-08 inserts 8 permission rows + 3 role-permission mappings into C-04's tables; no C-01/C-02/C-03 endpoint changes)
- Cross-cutting: **PARTIAL** — C-08 adds rows to C-04's tables but does NOT retrofit C-01/C-02/C-03 endpoints (C-04 already retrofitted them). The seed catalog references 15 keys, but Phase 1 does NOT migrate any existing module to consume config — that's a Phase 2 concern (modules migrate from hardcoded values to `config.get()` calls).
- Recommended OpenSpec domain name: `configuration`
- Recommended OpenSpec change name: `add-c08-configuration-framework`

---

## Reasoning

### C-08 is a NEW domain (ADDED)

The `openspec/specs/` directory contains `tenant-institution/`, `identity-user-management/`, `authentication/`, `authorization` (does NOT yet exist — C-04 was a kernel capability that didn't produce a live spec under that name; its behavior was folded into the C-01/C-02 spec via MODIFIED deltas), `platform-owner-separation/`, and `platform-owner-followups/`. There is no `configuration` spec. C-08's primary delta type is ADDED — a brand-new kernel domain introducing `ConfigurationKey`, `ConfigurationValue`, `ConfigurationAudit` entities, the `config.get(...)` resolution API, the in-memory cache with NOTIFY-based invalidation, and the 12-endpoint REST surface.

### C-08 MODIFIES C-04's behavioral contract (rows-only, no endpoint changes)

C-04's spec (whether as a standalone spec or as MODIFIED deltas to C-01/C-02) defines the C-04 `permission` and `role_permission` tables as the central authorization catalog. C-08 extends this catalog:

- **8 new `permission` rows** — `config.key.create`, `config.key.update`, `config.key.deprecate`, `config.key.list`, `config.value.create`, `config.value.update`, `config.value.delete`, `config.audit.read`. Inserted by C-08's migration `009_c08_configuration.py` with `ON CONFLICT DO NOTHING`.
- **~13 new `role_permission` rows** — mapping PlatformOwner to all 8, ClientDirector to `config.value.{create,update,delete}` + `config.key.list` + `config.audit.read`, InstituteAdmin to `config.value.{create,update,delete}` + `config.key.list` + `config.audit.read`. Inserted by the same migration.

This is a **data-level change to C-04's tables**, not a behavioral change. C-04's `on_startup` auto-loads the new rows at next app restart — **no C-04 code change needed**. No C-04 endpoint is added or modified. No C-04 policy in code is added (all policies are DB-driven, loaded at startup).

The C-04 impact is therefore a **MODIFIED delta to the `authorization` domain** describing "C-04 tables now contain 8 + ~13 additional rows for C-08." The C-08 PRD calls this out (D15) and the spec/design phase must include this as a MODIFIED requirement in the `authorization` domain.

### C-08 does NOT modify C-01's behavioral contract

C-01's spec (archived) defines the C-01 entities (client, institution, org_unit, institution_type) and their lifecycles. C-08 does not change any C-01 endpoint, permission, or behavior. C-08 only **consumes** C-01's `client` and `institution` tables as FK targets in `configuration_value.scope_id`. This is a read-only consumer relationship, not a behavioral change to C-01. **No MODIFIED deltas to C-01.**

### C-08 does NOT modify C-02's behavioral contract

C-02's spec (archived) defines the `app_user` table and user lifecycle. C-08 does not change any C-02 endpoint, permission, or behavior. C-08 only **consumes** C-02's `app_user` table for `configuration_audit.actor_user_id` and `configuration_value.updated_by` FKs. **No MODIFIED deltas to C-02.**

### C-08 does NOT modify C-03's behavioral contract

C-03's spec (archived) defines authentication. C-08 does not change any C-03 endpoint or behavior. C-08 routes use the same JWT auth + TenantContext that all other modules use. **No MODIFIED deltas to C-03.**

### C-08 does NOT modify Platform Owner Separation's contract

C-08 follows the existing Platform Owner pattern: Platform Owner acts via the platform-owner JWT path (no `Host` header, custom HS256 JWT with `is_platform_owner: true` claim). No new platform-owner-specific code; C-08 routes use the existing `require_platform_owner` dependency (or its C-08 analog gated on the `config.*` permissions). **No MODIFIED deltas to platform-owner-separation.**

### Why cross-cutting is PARTIAL (not full)

C-08 adds to C-04's tables but does NOT retrofit existing module endpoints. C-08 also has no required consumer-of-C-08 behavior in Phase 1: the 15 seed keys are seeded but not yet consumed by Fees/Homework. (The seed `homework.allowLateSubmission` and `homework.maxAttachmentsPerAssignment` will be wired up in a future Homework module update, but that is OUT of Phase 1 scope per D16.) The MODIFIED delta to C-04 is minimal — rows-only, no code change. This is **partial** cross-cutting: C-08 is not a fan-out retrofit like C-04 was.

---

## ADDED requirements (high-level — C-08's new domain)

These are the requirement areas that will become requirements/scenarios in `specs/configuration/spec.md` during prd-to-sdd. Each maps to PRD §6 (FR-01 through FR-47) and grill-me decisions D1–D16.

### ConfigurationKey registry

- **`configuration_key` table** — registry of every key that exists on the platform. Columns: `id` (UUID PK), `key` (TEXT UNIQUE NOT NULL), `type` (ENUM: string|number|boolean|json|date), `default_value` (JSONB NOT NULL — required per D9), `merge_strategy` (TEXT default 'replace' per D2; values: replace|append_lists|deep_merge), `category` (ENUM: Business Rules|Display|Academic|Notifications|Feature Toggles|Platform|Integrations per D12), `module` (TEXT nullable — namespace only, not a runtime scope per D14), `description` (TEXT NOT NULL), `is_feature_toggle` (BOOLEAN default false), `is_deprecated` (BOOLEAN default false), `deprecated_at` (TIMESTAMPTZ nullable — drives 90-day auto-hide per D13), `replacement_key` (TEXT nullable — set when deprecated per D13), `allowed_values` (JSONB nullable — hint only per D8), `created_at` + `updated_at`. No RLS (global registry, all roles can read per D11/D15). (FR-01 to FR-08, D3, D8, D9, D13)
- **Key CRUD endpoints** — 5 endpoints under `/api/v1/config/keys`: POST (PO creates key), GET (list, paginated, filterable by category/module/is_deprecated/is_feature_toggle), GET/{id}, PATCH/{id} (PO updates metadata, default, deprecates), DELETE/{id} (PO soft-deletes, sets `is_deprecated=true`). All endpoints use `require_permission('config.key.*', ...)` from C-04. (FR-01, FR-06, FR-07, FR-08, FR-45, D4, D11, D15)
- **Default value required** — POST returns 400 if `default_value` is missing or null. (FR-02, D9)
- **Type-only write validation** — POST/PATCH validates the value's JSON type matches the declared `type` column. JSON values must parse as valid JSON. Business constraints (HH:MM, enum, regex) are NOT enforced at write; modules enforce them at read. (FR-13, D8)

### ConfigurationValue overrides

- **`configuration_value` table** — overrides of a key at a specific scope. Columns: `id` (UUID PK), `key_id` (UUID FK → configuration_key), `scope_type` (ENUM: platform|client|institution — `module` is deferred to Phase 2 per D14), `scope_id` (UUID nullable — FK to client or institution; NULL for platform scope since platform defaults live on the key, not in a value row), `client_id` (UUID FK → client — always populated, drives RLS), `institution_id` (UUID FK → institution nullable — populated for `scope_type=institution`), `value` (JSONB NOT NULL), `created_at` + `updated_at`, `updated_by` (UUID NOT NULL — FK → app_user). RLS policies filter by `client_id` / `institution_id` per the migration-007 pattern. UNIQUE constraint on (`key_id`, `scope_type`, `scope_id`). (FR-09, FR-10, FR-11, FR-12, FR-14, D3, D4, D5, D42, D43)
- **Value CRUD endpoints** — 4 endpoints under `/api/v1/config/values`: POST (any role in scope sets override), GET (list for my scope, filterable by scope_type, key_id, scope_id), PATCH/{id} (update), DELETE/{id} (clear override, fall back to parent). All endpoints use `require_permission('config.value.*', ...)` + scope check in the service layer. (FR-09 to FR-14, FR-45, D4, D11, D15)
- **Role-scope enforcement** — Platform Owner can write at any scope; Client Director can write at Client scope (own client) and Institution scope (own client's institutions); Institute Admin can write at Institution scope (own institution only). Cross-tenant writes are 403'd. The permission check in C-04 is the first gate; the service layer does a second scope check (FR-38) to prevent Client Director from accidentally targeting another client's institution if their permission somehow allows it. (FR-10, FR-12, FR-38, D4, D15)
- **Platform-scope values are NOT separate rows** — The platform default lives on the key's `default_value` field. There is no `configuration_value` row with `scope_type='platform'`. The Platform Owner's "set platform default" is a PATCH on the key, not a POST on values. (D3, D9, D43)

### ConfigurationAudit (lightweight)

- **`configuration_audit` table** — append-only change log. Columns: `id` (UUID PK), `key_id` (UUID FK → configuration_key), `scope_type` (ENUM nullable), `scope_id` (UUID nullable), `action` (ENUM: key_created|key_updated|key_deprecated|value_created|value_updated|value_deleted), `actor_user_id` (UUID nullable — NULL for system actions like seed), `actor_role` (TEXT nullable — snapshot of role at action time), `timestamp` (TIMESTAMPTZ default now()). No before/after values stored (per D6). Append-only — no UPDATE/DELETE. (FR-30 to FR-33, D6)
- **Audit endpoint** — `GET /api/v1/config/audit?key=&scope_type=&scope_id=&action=&actor_user_id=&from=&to=` with role-scope filtering. (FR-34, D11, D15)

### Scope inheritance + merge semantics

- **Resolution walk** — `institution → client → platform`. Returns the first match. (FR-15, D1, D5)
- **Merge strategies** — `replace` (default) replaces completely; `append_lists` unions list values with set semantics (preserving order); `deep_merge` deep-merges objects per RFC 7396 (lists replaced). Scalars always replace regardless of `merge_strategy`. (FR-16 to FR-19, D2)
- **Default fallback** — When no override exists at any scope, return the key's `default_value`. (FR-20, D9)

### Resolution API (`kernel/config.py`)

- **`config.get(key, institution_id=None, client_id=None)`** — Programmatic function. Returns the resolved value for the given scope. Works in any context (FastAPI request, background job, migration, test). TenantContext is NOT required. (FR-21, FR-22, D10)
- **`POST /api/v1/config/resolve`** — Debug endpoint. Returns the resolved value AND its source (which scope provided it). (FR-23, D11)
- **`GET /api/v1/config/resolve/{key}?institution_id=&client_id=`** — Quick-lookup debug endpoint. (FR-24, D11)

### In-memory cache + NOTIFY-based hot reload

- **Startup load** — On app startup, load all `ConfigurationKey` rows + all `ConfigurationValue` rows into in-memory dicts. Keys dict keyed by `key` (TEXT). Values dict keyed by `(scope_type, scope_id, key_id)`. (FR-25, D5)
- **In-memory resolution** — `config.get(...)` is served from the in-memory dict, no DB hit. (FR-26, D5)
- **In-process patch on UPDATE** — When the primary app instance handles a value/key UPDATE, it patches its in-memory dict immediately. (FR-27, D5, D7)
- **NOTIFY/LISTEN for multi-instance** — Every UPDATE emits a `NOTIFY config_changes '...'` on PostgreSQL. Other instances LISTEN on this channel and reload their in-memory dicts on receipt. Multi-instance lag ≤5s. (FR-28, FR-29, D7)
- **PostgreSQL trigger** — A `BEFORE UPDATE` trigger on `configuration_value` (and possibly on `configuration_key`) emits the NOTIFY. Alternatively, the application code emits NOTIFY explicitly in the service layer. The spec/design phase picks one.

### Authorization (C-04 integration)

- **8 new C-04 permissions** — `config.key.create`, `config.key.update`, `config.key.deprecate`, `config.key.list`, `config.value.create`, `config.value.update`, `config.value.delete`, `config.audit.read`. Inserted by migration `009_c08_configuration.py` with `ON CONFLICT DO NOTHING`. (FR-35, D15)
- **3 new role-permission mappings** — PlatformOwner → all 8; ClientDirector → `config.value.{create,update,delete}` + `config.key.list` + `config.audit.read`; InstituteAdmin → same as ClientDirector. (FR-36, D4, D15)
- **`require_permission` from C-04** — Every C-08 endpoint uses the existing `require_permission(...)` dependency from `backend/kernel/authz/dependencies.py`. C-08 does NOT implement its own permission system. (FR-37, D15)
- **Service-layer scope check** — In addition to the C-04 permission check, the C-08 service layer enforces scope: a Client Director cannot write at another client's institution even if their permission allows the action. The check reads `current_user.client_id` / `institution_id` from TenantContext and rejects mismatched writes with 403. (FR-38, D4)

### Seed catalog (15 keys)

- **Migration seeds 15 keys** — Across 5 categories. 4 Business Rules (attendance.markingCutoffTime, attendance.statuses [json+append_lists+default=['present','absent']], fee.lateFeePercentage, leave.autoApproveUnderDays), 3 Display (display.dateFormat, display.timezone, display.language), 3 Academic (academic.gradingScale, academic.passPercentage, academic.termStructure), 2 Notifications (notification.attendanceAbsenceAlert, notification.defaultChannel), 2 Homework (homework.allowLateSubmission, homework.maxAttachmentsPerAssignment), 1 Platform (platform.maxFileUploadMB). (FR-39, FR-40, D12)
- **Migration also seeds audit** — Each seed key gets a `configuration_audit` row with `action=key_created`, `actor_user_id=NULL` (system action), `actor_role='system'`. (FR-41, D6)
- **Migration also seeds C-04 rows** — 8 permissions + ~13 role-permission mappings (see Authorization section above). (FR-41, D15)

### Tenant isolation

- **RLS on `configuration_value`** — Policy filters by `client_id` (always populated) and `institution_id` (when populated), consistent with the migration-007 pattern. (FR-42, D1, D4)
- **Platform Owner RLS bypass** — Platform Owner queries against `configuration_value` bypass the RLS policy, consistent with the migration-007 pattern. (FR-43, D43)
- **`configuration_key` is global** — No RLS. All roles can read all keys (subject to `config.key.list` permission). (FR-44, D11, D15)

### Soft delete + deprecation

- **Soft delete only** — DELETE on a key is a PATCH `is_deprecated=true` + `replacement_key`. The key stays in the registry. Reads continue to work. New overrides blocked (returns 409). (FR-07, D13)
- **90-day auto-hide** — `GET /api/v1/config/keys` filters out keys where `is_deprecated=true AND deprecated_at < now() - interval '90 days'`. The row remains in the DB. (FR-08, D13)
- **No renames** — Deprecate old key, create new key. Modules migrate in a coordinated release. (D13)

### REST API surface

- **12 endpoints under `/api/v1/config/`** — 5 key endpoints + 4 value endpoints + 1 audit endpoint + 2 resolve endpoints. All have OpenAPI `summary` fields. All use `require_permission(...)` from C-04. (FR-45, FR-46, FR-47, D11)

### Kernel manifest + module registration

- **`backend/kernel/config/manifest.py`** — New `ConfigurationManifest` class. Registers routes (`register_routes(app)`), registers C-04 policies (empty — all in DB), registers on_startup hook that loads the in-memory dict from DB, registers LISTEN on `config_changes` channel. (D16)
- **`backend/kernel/manifest.py`** — Updated to include `ConfigurationManifest` in the kernel manifests list. The app factory wires it before serving. (D16)
- **No business-side manifest** — C-08 is a kernel capability; there is no `backend/business/configuration/` directory. All code lives in `backend/kernel/config/`.

---

## MODIFIED requirements (C-04 — rows-only, no endpoint changes)

C-04's spec (whether as a standalone spec or as MODIFIED deltas to C-01/C-02) defines the `permission` and `role_permission` tables. C-08's migration `009_c08_configuration.py` inserts new rows into these tables:

- **8 new `permission` rows** — `config.key.create` (PO), `config.key.update` (PO), `config.key.deprecate` (PO), `config.key.list` (all roles), `config.value.create` (PO/CD/InstAdmin scope-checked), `config.value.update` (PO/CD/InstAdmin scope-checked), `config.value.delete` (PO/CD/InstAdmin scope-checked), `config.audit.read` (all roles, scope-checked). (FR-35, D15)
- **~13 new `role_permission` rows** — PlatformOwner → all 8; ClientDirector → 5 (config.value.{create,update,delete} + config.key.list + config.audit.read); InstituteAdmin → 5 (same as ClientDirector, scope-checked at institution level). (FR-36, D4, D15)

### Impact on C-04

- C-04's `permission` table grows from 26 + business-module-permissions to 26 + business-module-permissions + 8 = 34 + business-module-permissions.
- C-04's `role_permission` table grows correspondingly.
- C-04's `on_startup` auto-loads new rows at next app restart — **no C-04 code change**.
- C-04 endpoints are unchanged.
- C-04 tests are unaffected (new rows don't break existing role mappings).
- The Casbin enforcer singleton (from C-04) loads all permissions at startup; the new `config.*` permissions become enforceable as soon as the enforcer reloads.

### C-04 manifest registration

C-08's manifest does NOT register new Casbin policies in code (its `register_casbin_policies(enforcer)` is empty). All C-08 policies live in the DB, loaded by C-04 at startup. This matches the pattern established by Fees and Homework (D15 / D8 of those modules).

---

## NOT MODIFIED: other domains

| Domain | Status | Reason |
|---|---|---|
| **C-01** (tenant-institution) | No change | Consumed via FK to `client` and `institution` for `scope_id`. No endpoint changes. No permission changes. |
| **C-02** (identity-user-management) | No change | Consumed via FK to `app_user` for `actor_user_id` and `updated_by`. No endpoint changes. |
| **C-03** (authentication) | No change | Consumed via JWT authentication + TenantContext. No endpoint changes. |
| **C-11** (audit) | No change | C-08 has its own `configuration_audit` table (lightweight). C-11 is the broader async audit pipeline; C-08 does not emit C-11 events in Phase 1 (the `configuration_audit` table is the audit surface for C-08). Future: a C-08 high-level event might emit a C-11 event, but Phase 1 doesn't require it. |
| **C-05** (academic structure) | No change | Not yet built. When C-05 lands, it will consume C-08 (e.g., `academic.gradingScale` will be read by C-05's grade calculation), but that's a Phase 2 concern. |
| **C-06** (relationship management) | No change | Not yet built. Same future-consumer story. |
| **C-07** (subscription management) | No change | Not yet built. |
| **C-09** (notification framework) | No change | Not yet built. When it lands, it will consume C-08 (e.g., `notification.defaultChannel` will be read by C-09's dispatch logic), but that's a Phase 2 concern. |
| **C-12** (code & identifier generation) | No change | Not yet built. Independent of C-08. |
| **Platform Owner Separation** | No change | C-08 follows the existing Platform Owner pattern (custom HS256 JWT, `is_platform_owner` claim, `require_platform_owner` for key-registry endpoints). No new platform-owner code. |
| **Fees** (business module) | No change | The seed `fee.lateFeePercentage` key is present but NOT consumed by Fees in Phase 1. The Fees module continues to use its hardcoded value. Migrating Fees to consume C-08 is a Phase 2 effort. |
| **Homework** (business module) | No change | The seed `homework.allowLateSubmission` and `homework.maxAttachmentsPerAssignment` keys are present but NOT consumed by Homework in Phase 1. Homework continues to use hardcoded values. Migrating Homework to consume C-08 is a Phase 2 effort. |

---

## Test fixture impact

`tests/conftest.py` `app` fixture:
- Add `from kernel.config.manifest import manifest as config_manifest`
- Update `create_app(kernel_manifests=[..., config_manifest])` — but C-08 is a kernel manifest, so it goes into the kernel manifests list, not the business manifests list.
- The `AlwaysAllowEnforcer` override (from C-04) already handles new permissions automatically.

Tests needing C-08 in scope:
- `tests/test_c08_configuration.py` — new file. ~25 tests covering: key CRUD, value CRUD, scope inheritance, all 3 merge strategies, audit, deprecation, in-memory cache, NOTIFY propagation, RLS, permission enforcement, scope checks.
- Existing 300+ tests should not require changes. C-08 has no behavioral effect on existing modules (no module consumes C-08 in Phase 1).

---

## Import-linter impact

- `backend/kernel/config/` imports from `kernel/` (TenantAwareRepositoryBase, TenantContext, require_permission, AuditEmitter, db, middleware) — **allowed** (kernel → kernel, same layer per A3).
- `backend/kernel/config/` imports from `kernel/authz/` (require_permission, Casbin enforcer) — **allowed** (kernel → kernel).
- `backend/kernel/config/` imports from `backend/migrations/` — **not typical**; the seed data lives in the migration, not the manifest. The manifest only reads the in-memory dict at startup, not the seed data.
- No `backend/kernel/config/` → `business/` imports (kernel does not depend on business per A3).
- No `backend/kernel/config/` → `shared/` imports.
- No cycles introduced.
- Existing contracts (A3, A4) should pass without modification.

---

## Cross-cutting concerns

- **First kernel-level module to insert into C-04's tables** — C-08 is a kernel module that owns its own config domain but extends C-04's permission catalog. The pattern is "C-04 owns the *framework* (Casbin enforcer, require_permission dependency, role_permission table); kernel modules can extend the framework's data." This is a deliberate design from A11 (kernel → ∅ + business → kernel) and from C-04's "centralized RBAC" rule (Rule 3).
- **C-11 audit is NOT used by C-08 in Phase 1** — C-08 has its own `configuration_audit` table. The reasoning: C-11's audit pipeline is currently basic-sync-only (per the `audit.py` AuditEmitter Protocol); C-08's audit is fundamentally about a single resource (a config value) and benefits from being co-located with the data. Future: when C-11's full async pipeline lands, C-08 may emit C-11 events for high-level config changes, but the granular audit stays in C-08's own table.
- **In-memory cache + NOTIFY is new infrastructure** — No existing module uses PostgreSQL NOTIFY/LISTEN. C-08 introduces this pattern. The implementation uses `psycopg2.AsyncConnection` for LISTEN (or SQLAlchemy's `event.listen` for raw connection access). The migration creates a trigger function + trigger on `configuration_value` and `configuration_key` to emit NOTIFY on UPDATE/INSERT/DELETE.
- **Config is read-only in Phase 1 for consumers** — The seed catalog is present, but NO existing module (Fees, Homework) is migrated to consume C-08. This is intentional: Phase 1 ships the framework; Phase 2 migrates modules one-by-one. The D16 decision explicitly says "NO admin UI in Phase 1" — the parallel is "NO consumer migration in Phase 1."
- **Module scope deferred to Phase 2** — The `module` column on ConfigurationKey is a namespace only. The C-08 `scope_type` ENUM has 3 values (platform, client, institution), not 4. When Module scope is added in Phase 2, a new ENUM value is added via migration. This is a deliberate forward-compatible design.
- **Attendance module is not built yet** — The seed catalog includes `attendance.*` keys. These are placeholders demonstrating the C-08 capability. When the Attendance module is built (future), it will consume these keys.

---

## Summary of files added/modified

### NEW files (C-08)

| File | Purpose |
|---|---|
| `backend/kernel/config/__init__.py` | Package init |
| `backend/kernel/config/manifest.py` | `ConfigurationManifest` class |
| `backend/kernel/config/models/configuration_models.py` | ORM: `ConfigurationKey`, `ConfigurationValue`, `ConfigurationAudit` |
| `backend/kernel/config/repos/configuration_repo.py` | Repository (inherits `TenantAwareRepositoryBase`) |
| `backend/kernel/config/services/configuration_service.py` | Business logic: CRUD, resolution, cache, NOTIFY |
| `backend/kernel/config/routes/keys.py` | Key CRUD endpoints (5) |
| `backend/kernel/config/routes/values.py` | Value CRUD endpoints (4) |
| `backend/kernel/config/routes/audit.py` | Audit endpoint (1) |
| `backend/kernel/config/routes/resolve.py` | Resolve debug endpoints (2) |
| `backend/kernel/config/dependencies.py` | `get_configuration_service`, `require_config_scope` |
| `backend/kernel/config/resolver.py` | In-memory dict + `config.get(...)` API |
| `backend/kernel/config/notifier.py` | PostgreSQL NOTIFY emit + LISTEN handler |
| `backend/migrations/versions/009_c08_configuration.py` | Migration: 3 tables + 15 seed keys + 8 C-04 permissions + 13 role-permission mappings + RLS policies + NOTIFY trigger |
| `backend/tests/test_c08_configuration.py` | ~25 unit/integration tests |
| `school_erp_flow/c08/_c08_flow_01_key_creation.md` | Flow doc: PO creates a key, sets default |
| `school_erp_flow/c08/_c08_flow_02_value_override.md` | Flow doc: CD/Admin overrides for their scope; resolution |
| `school_erp_flow/c08/_c08_flow_03_merge_semantics.md` | Flow doc: `append_lists` example with `attendance.statuses` |
| `school_erp_flow/c08/_c08_flow_04_audit_and_deprecation.md` | Flow doc: audit log + deprecate-old/create-new |
| `school_erp_flow/c08/_c08_flow_index.md` | Index referencing all 4 flows |

### MODIFIED files

| File | Change |
|---|---|
| `backend/kernel/manifest.py` | Add `ConfigurationManifest` to the kernel manifests list |
| `backend/main.py` | (No change — kernel manifests auto-wire) |
| `docs/platform-capabilities/platform-capabilities-v3.md` | No change (C-08 already documented) |
| `openspec/specs/authorization/spec.md` (if it exists) | Add MODIFIED delta: "C-04's permission table now contains 8 new config.* rows + 13 new role-permission rows for C-08" |

### NOT modified

- `backend/business/*` (Fees, Homework, Tenant Institution)
- `backend/kernel/auth/*` (authentication)
- `backend/kernel/user/*` (identity)
- `backend/kernel/authz/*` (authorization — only the migration inserts new rows; no code change)
- `backend/kernel/middleware.py` (no change)
- `backend/kernel/tenant_context.py` (no change)
- `backend/kernel/repo_base.py` (no change)
- `backend/kernel/audit.py` (no change)
- `tests/conftest.py` (no change — `AlwaysAllowEnforcer` handles new permissions automatically)
- Any frontend file (no UI in Phase 1)

---

> **End of Impact Classification**  
> **Version:** 1.0  
> **Date:** 2026-07-05  
> **Decisions referenced:** D1–D16 (from PRD)  
> **Status:** Ready for prd-to-sdd phase (proposal.md → spec.md → design.md → tasks.md → verify.md → archive)
