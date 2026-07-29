# Proposal: C-08 Configuration Framework

## Why

The School ERP platform must support many independent customer organizations (Clients) each operating one or more institutions (schools/colleges). The behavior of every business module — Attendance, Fees, Homework, Exams, Communication, etc. — is inherently configurable: an attendance cutoff time, a late-fee percentage, a grading scale, a date format, a notification channel preference, an enable/disable feature toggle. Without a centralized configuration framework, every setting ends up hardcoded in code, every override ends up in a module-specific `config` JSONB column, and every change requires a code deploy + application restart. The platform cannot scale to multiple tenants with different policies under that model.

C-08 is the **runtime configuration nervous system** of the platform. It owns a single, central key-value store with **typed values**, **scope inheritance** (Platform → Client → Institution → Module), **lightweight audit**, and **in-memory resolution with hot reload**. Per the platform non-negotiable rules, "configuration requires no code changes" (Rule 11) and "modules read, don't own." C-08 is the implementation of that contract.

Per the platform dependency map (`docs/platform-capabilities/platform-capabilities-v3.md` §4), C-01b (Tenant & Institution Domain) was sequenced to depend on C-08. C-08 was originally sequenced at P2 in Phase 1, immediately after C-01, but was deferred. It is being built now to unblock C-05 (Academic Structure), C-06 (Relationship Management), and every business module's configurable behavior. Building C-08 now is a hard prerequisite for the remaining Phase 1 capabilities and for any business module that needs configurable per-tenant behavior (e.g., Attendance's `attendance.statuses`, which differs by institution — one school has 2 statuses, another has 4).

## What Changes

- **NEW capability `configuration`** — A kernel capability that owns the centralized configuration framework. Introduces the `ConfigurationKey` registry, the `ConfigurationValue` override store, the `ConfigurationAudit` change log, the `config.get(key, institution_id=..., client_id=...)` resolution API, the in-memory cache with PostgreSQL NOTIFY-based hot reload, and the 12-endpoint REST surface under `/api/v1/config/`. Lives at `backend/kernel/config/`. No business module, no admin UI in Phase 1 (use Swagger).

- **NEW Alembic migration `009_c08_configuration.py`** — Creates 3 tables (`configuration_key`, `configuration_value`, `configuration_audit`) with RLS on `configuration_value`, seeds 15 keys across 5 categories, and inserts 8 new permissions + 13 role-permission mappings into the C-04 `permission` and `role_permission` tables.

- **NEW kernel manifest registration** — `ConfigurationManifest` registered in `backend/kernel/manifest.py`. Wires routes, on-startup cache load, NOTIFY LISTEN handler.

- **NEW endpoints under `/api/v1/config/`** — 12 endpoints total: 5 key CRUD (PO-only for write), 4 value CRUD (role-scoped), 1 audit read, 2 resolve debug.

- **MODIFIED `backend/kernel/manifest.py`** — Add `ConfigurationManifest` to the kernel manifests list. No other C-01/C-02/C-03/C-04 code change.

- **NEW tests in `tests/test_c08_configuration.py`** — ~25 unit + integration tests covering key CRUD, value CRUD, scope inheritance, all 3 merge strategies (`replace`, `append_lists`, `deep_merge`), audit, deprecation, in-memory cache, NOTIFY propagation, RLS, permission enforcement, scope checks.

- **NEW 4 flow documents in `school_erp_flow/c08/`** — Key creation, value override, merge semantics, audit + deprecation. Plus an index file.

- **No changes to existing module code (Fees, Homework, Tenant Institution)** — Phase 1 ships the framework but does NOT migrate any existing module to consume C-08. The 15 seed keys are placeholders demonstrating the capability. Migrating Fees and Homework to `config.get()` calls is a Phase 2 effort.

- **No changes to C-01, C-02, C-03, C-04 code** — Only the C-08 migration inserts rows into C-04's tables; no C-04 code change. C-04's `on_startup` auto-loads the new rows at next app restart.

- **No admin UI in Phase 1** — Per decision D16. Swagger UI is the only editing surface.

## Capabilities

### New Capabilities
- `configuration`: The C-08 Configuration Framework — centralized key-value store with scope inheritance (Platform → Client → Institution → Module), typed values, lightweight audit, and in-memory resolution with hot reload. New file: `openspec/changes/add-c08-configuration-framework/specs/configuration/spec.md`.

### Modified Capabilities
- _None._ The C-08 migration inserts 8 new `permission` rows and ~13 new `role_permission` rows into C-04's tables, but C-04 has no live OpenSpec spec (its behavior is folded into the `tenant-institution` spec via MODIFIED deltas, and the C-04 architecture decisions are documented in `docs/architecture/adr-c04-authorization-implementation.md`). The new rows are data, not a behavioral change. No spec-level modification is required.

## Impact

### Code (NEW)

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
| `backend/kernel/config/dependencies.py` | `get_configuration_service`, scope guards |
| `backend/kernel/config/resolver.py` | In-memory dict + `config.get(...)` API |
| `backend/kernel/config/notifier.py` | PostgreSQL NOTIFY emit + LISTEN handler |
| `backend/migrations/versions/009_c08_configuration.py` | Migration: 3 tables + 15 seed keys + 8 C-04 permissions + 13 role-permission mappings + RLS policies + NOTIFY trigger |
| `backend/tests/test_c08_configuration.py` | ~25 unit/integration tests |
| `school_erp_flow/c08/_c08_flow_01_key_creation.md` | Flow doc |
| `school_erp_flow/c08/_c08_flow_02_value_override.md` | Flow doc |
| `school_erp_flow/c08/_c08_flow_03_merge_semantics.md` | Flow doc |
| `school_erp_flow/c08/_c08_flow_04_audit_and_deprecation.md` | Flow doc |
| `school_erp_flow/c08/_c08_flow_index.md` | Index |

### Code (MODIFIED)

| File | Change |
|---|---|
| `backend/kernel/manifest.py` | Add `ConfigurationManifest` to the kernel manifests list |

### Not Modified

- `backend/business/*` (Fees, Homework, Tenant Institution)
- `backend/kernel/auth/*` (authentication)
- `backend/kernel/user/*` (identity)
- `backend/kernel/authz/*` (authorization — only the migration inserts new rows; no code change)
- `backend/kernel/middleware.py`, `tenant_context.py`, `repo_base.py`, `audit.py` (no change)
- `tests/conftest.py` (no change — `AlwaysAllowEnforcer` from C-04 handles new permissions automatically)
- Any frontend file (no UI in Phase 1)

### APIs

- 12 NEW REST endpoints under `/api/v1/config/` (see above).
- 1 NEW programmatic API: `config.get(key, institution_id=None, client_id=None)`.

### Database

- 3 NEW tables: `configuration_key`, `configuration_value`, `configuration_audit`.
- 2 NEW RLS policies on `configuration_value` (client + institution filters, with Platform Owner bypass).
- 1 NEW PostgreSQL NOTIFY trigger on `configuration_value` and `configuration_key`.
- 15 NEW rows in `configuration_key` (seeds).
- 8 NEW rows in `permission` (C-04).
- ~13 NEW rows in `role_permission` (C-04).

### Dependencies

- C-01 (Tenant & Institution) — upstream; `configuration_value.scope_id` FKs to `client` and `institution`.
- C-02 (Identity & User) — upstream; `configuration_audit.actor_user_id` and `configuration_value.updated_by` FKs to `app_user`.
- C-03 (Authentication) — upstream; routes use JWT + TenantContext.
- C-04 (Authorization) — upstream; C-08 extends C-04's permission catalog.
- PostgreSQL NOTIFY/LISTEN — new infrastructure dependency (no other module uses this).
- All business modules — downstream (future consumer; not in Phase 1).

### Tests

- NEW `tests/test_c08_configuration.py` (~25 tests).
- No change to existing 300+ tests (C-08 has no behavioral effect on existing modules in Phase 1).
