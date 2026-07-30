# C-08 Configuration Framework — Spec Delta

## ADDED Requirements

### Requirement: ConfigurationKey Registry

The system MUST provide a centralized registry of named, typed configuration keys. Every key has a unique name, a declared type, a non-null default value, an optional merge strategy, a category, an optional module namespace, a description, and a deprecation flag.

#### Scenario: Platform Owner creates a new key
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` with `key="attendance.markingCutoffTime"`, `type="string"`, `default_value="10:00 AM"`, `category="Business Rules"`, `module="attendance"`, `description="..."`
- **THEN** the system creates the key, returns 201 with the key representation, and writes a `configuration_audit` row with `action="key_created"`

#### Scenario: Key creation fails without a default
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` with `default_value=null` or omits `default_value`
- **THEN** the system returns 400 with a clear error message

#### Scenario: Key type is one of the allowed values
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` with `type` not in `["string", "number", "boolean", "json", "date"]`
- **THEN** the system returns 400

#### Scenario: List keys paginated and filterable
- **WHEN** any authenticated user GETs `/api/v1/config/keys?category=Business%20Rules&module=attendance&page=1&page_size=20`
- **THEN** the system returns a paginated list of keys matching the filters, including `id`, `key`, `type`, `default_value`, `merge_strategy`, `category`, `module`, `description`, `is_feature_toggle`, `is_deprecated`, `deprecated_at`, `replacement_key`, `allowed_values`, `created_at`, `updated_at`

#### Scenario: Soft-delete a key
- **WHEN** a Platform Owner PATCHes `/api/v1/config/keys/{id}` with `is_deprecated=true` and `replacement_key="attendance.cutoffTime"`
- **THEN** the system sets `is_deprecated=true`, `deprecated_at=now()`, blocks new value overrides for this key, and writes a `configuration_audit` row with `action="key_deprecated"`

#### Scenario: Hard delete is not supported
- **WHEN** a Platform Owner DELETEs `/api/v1/config/keys/{id}`
- **THEN** the system returns 405 Method Not Allowed (soft delete only via PATCH)

#### Scenario: Deprecated key auto-hides after 90 days
- **WHEN** a key has `is_deprecated=true` AND `deprecated_at < now() - interval '90 days'`
- **THEN** the key is excluded from the default list response at `/api/v1/config/keys` but remains in the database and is still readable via `GET /api/v1/config/keys/{id}`

### Requirement: ConfigurationValue Overrides

The system MUST allow configuration values to be overridden at Platform, Client, or Institution scope. The Platform-scope default lives on the key's `default_value` field (no separate value row). Client- and Institution-scope overrides are stored as separate rows.

#### Scenario: Institute Admin sets an Institution-scope override
- **WHEN** an Institute Admin POSTs `/api/v1/config/values` with `key_id=<X>`, `scope_type="institution"`, `scope_id=<their own institution>`, `value="11:00 AM"`
- **THEN** the system creates a `configuration_value` row, patches the in-memory cache in the primary instance, emits a PostgreSQL NOTIFY on `config_changes`, and writes a `configuration_audit` row with `action="value_created"`

#### Scenario: Client Director sets a Client-scope override
- **WHEN** a Client Director POSTs `/api/v1/config/values` with `key_id=<X>`, `scope_type="client"`, `scope_id=<their own client>`, `value="MM/DD/YYYY"`
- **THEN** the system creates the override, returns 201, and writes an audit row

#### Scenario: Cross-tenant write is rejected
- **WHEN** a Client Director at Client A POSTs `/api/v1/config/values` with `scope_type="institution"`, `scope_id=<institution of Client B>`
- **THEN** the system returns 403

#### Scenario: Duplicate value rejected
- **WHEN** any user POSTs `/api/v1/config/values` with the same `key_id`, `scope_type`, and `scope_id` as an existing row
- **THEN** the system returns 409 Conflict

#### Scenario: Write to deprecated key is rejected
- **WHEN** any user POSTs `/api/v1/config/values` for a key where `is_deprecated=true`
- **THEN** the system returns 409

#### Scenario: Delete clears the override
- **WHEN** any user DELETEs `/api/v1/config/values/{id}` for a row in their scope
- **THEN** the system removes the row, patches the in-memory cache, emits NOTIFY, and writes an audit row with `action="value_deleted"`

#### Scenario: List values filtered by scope
- **WHEN** a Client Director GETs `/api/v1/config/values?scope_type=client`
- **THEN** the system returns only Client-scope value rows where `scope_id=<their own client>` and Client-scope Institution-scope rows where `institution.client_id=<their client>`

#### Scenario: Platform Owner sees all values
- **WHEN** a Platform Owner GETs `/api/v1/config/values`
- **THEN** the system returns all value rows across all clients and institutions

### Requirement: Scope Inheritance

The system MUST resolve a configuration key by walking the scope chain Institution → Client → Platform, returning the first match. If no override exists at any scope, the key's `default_value` is returned.

#### Scenario: Institution override takes precedence
- **WHEN** `attendance.markingCutoffTime` has Platform default `"10:00 AM"`, Client override `"11:00 AM"`, and Institution override `"12:00 PM"`
- **THEN** `config.get("attendance.markingCutoffTime", institution_id=<inst X>)` returns `"12:00 PM"`

#### Scenario: Falls back to Client override
- **WHEN** `attendance.markingCutoffTime` has Platform default `"10:00 AM"` and Client override `"11:00 AM"`, with no Institution override
- **THEN** `config.get("attendance.markingCutoffTime", institution_id=<inst X>, client_id=<client Y>)` returns `"11:00 AM"`

#### Scenario: Falls back to Platform default
- **WHEN** `attendance.markingCutoffTime` has Platform default `"10:00 AM"` and no Client or Institution override
- **THEN** `config.get("attendance.markingCutoffTime", institution_id=<inst X>, client_id=<client Y>)` returns `"10:00 AM"`

#### Scenario: Unknown key raises error
- **WHEN** `config.get("nonexistent.key", institution_id=<inst X>)` is called for a key not in the registry
- **THEN** the system raises a `KeyError` or `ConfigurationKeyNotFound` exception

### Requirement: Merge Strategies

The system MUST support three merge strategies: `replace` (default, full replacement), `append_lists` (lists unioned with set semantics), and `deep_merge` (JSON objects deep-merged per RFC 7396, lists replaced). Scalars MUST always use `replace` regardless of the declared merge strategy.

#### Scenario: Replace strategy replaces fully
- **WHEN** `attendance.statuses` has `merge_strategy="replace"`, Platform default `["present", "absent"]`, and Institution override `["present", "absent", "half_day"]`
- **THEN** the resolved value is `["present", "absent", "half_day"]` (replacement, not union)

#### Scenario: Append lists strategy unions
- **WHEN** `attendance.statuses` has `merge_strategy="append_lists"`, Platform default `["present", "absent"]`, and Institution override `["half_day"]`
- **THEN** the resolved value is `["present", "absent", "half_day"]` (union, order preserved from parent)

#### Scenario: Deep merge strategy merges objects
- **WHEN** `display.theme` has `merge_strategy="deep_merge"`, Platform default `{"primary": "blue", "secondary": "white"}`, and Institution override `{"primary": "green"}`
- **THEN** the resolved value is `{"primary": "green", "secondary": "white"}` (deep merge, lists replaced not merged)

#### Scenario: Scalars always replace
- **WHEN** `fee.lateFeePercentage` has `merge_strategy="append_lists"` (incorrectly applied to a scalar) and Institution override `1.5`
- **THEN** the resolved value is `1.5` (replacement, not append)

### Requirement: Resolution API

The system MUST expose a programmatic `config.get(key, institution_id=None, client_id=None)` function that returns the resolved value for the given scope, working in any execution context (request, background job, migration, test).

#### Scenario: config.get works in a FastAPI request
- **WHEN** a route handler calls `config.get("attendance.markingCutoffTime", institution_id=ctx.institution_id)`
- **THEN** the system returns the resolved value, served from the in-memory dict without a database query

#### Scenario: config.get works in a background job
- **WHEN** a Celery/RQ/arq job calls `config.get("fee.lateFeePercentage", institution_id=job.institution_id, client_id=job.client_id)` outside of a FastAPI request
- **THEN** the system returns the resolved value

#### Scenario: Resolve debug endpoint
- **WHEN** any user POSTs `/api/v1/config/resolve` with `key="attendance.markingCutoffTime"`, `scope_type="institution"`, `scope_id=<inst X>`
- **THEN** the system returns `{"key": "attendance.markingCutoffTime", "resolved_value": "...", "source_scope": "institution:<inst X> | client:<client Y> | platform:default"}`

#### Scenario: Resolve quick-lookup
- **WHEN** any user GETs `/api/v1/config/resolve/attendance.markingCutoffTime?institution_id=<inst X>&client_id=<client Y>`
- **THEN** the system returns the resolved value plus the source scope

### Requirement: In-Memory Cache and Hot Reload

The system MUST load all ConfigurationKey and ConfigurationValue rows into an in-memory dict on application startup. Reads MUST be served from the in-memory dict. On any UPDATE, the in-memory dict MUST be patched in the primary instance immediately and other instances MUST refresh via PostgreSQL NOTIFY/LISTEN within 5 seconds.

#### Scenario: Startup loads all keys and values
- **WHEN** the application starts up
- **THEN** the system loads every row from `configuration_key` and `configuration_value` into in-memory dicts, and `config.get(...)` is ready to serve values

#### Scenario: Single-instance update propagates instantly
- **WHEN** a user PATCHes `/api/v1/config/values/{id}` in a single-instance deployment
- **THEN** the in-memory dict is patched before the response is returned, and `config.get(...)` returns the new value on the next call

#### Scenario: Multi-instance update propagates within 5s
- **WHEN** a user PATCHes `/api/v1/config/values/{id}` in instance A of a multi-instance deployment
- **THEN** instance A patches its in-memory dict and emits a NOTIFY on `config_changes`; instance B (LISTENing) reloads its in-memory dict from the database within 5 seconds

#### Scenario: NOTIFY trigger fires on UPDATE
- **WHEN** any row in `configuration_key` or `configuration_value` is INSERTed, UPDATEd, or DELETEd
- **THEN** a PostgreSQL trigger emits a NOTIFY on the `config_changes` channel with the action type and row id

### Requirement: Configuration Audit Log

The system MUST record every key create/update/deprecate and every value create/update/delete in the `configuration_audit` table. Audit rows MUST be append-only (no UPDATE or DELETE). Audit MUST record who/what/when but MUST NOT store before/after values.

#### Scenario: Audit row on key creation
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` and the key is created
- **THEN** a `configuration_audit` row is written with `action="key_created"`, `actor_user_id=<PO id>`, `actor_role="platform_owner"`, `timestamp=now()`

#### Scenario: Audit row on value update
- **WHEN** any user PATCHes `/api/v1/config/values/{id}`
- **THEN** a `configuration_audit` row is written with `action="value_updated"`, `key_id=<X>`, `scope_type=<Y>`, `scope_id=<Z>`, `actor_user_id=<user id>`, `actor_role=<role>`

#### Scenario: Audit read endpoint
- **WHEN** any user GETs `/api/v1/config/audit?key=attendance.markingCutoffTime&from=2026-07-01&to=2026-07-31`
- **THEN** the system returns all audit rows matching the filter, scoped to the user's role (PO sees all, CD sees own client, Admin sees own institution)

#### Scenario: Audit rows are immutable
- **WHEN** any user attempts to UPDATE or DELETE a row in `configuration_audit`
- **THEN** the database rejects the operation (no UPDATE/DELETE grant, or trigger raises)

### Requirement: Authorization via C-04

The system MUST enforce all C-08 operations through the existing C-04 Casbin enforcer. C-08 MUST register 8 new permissions and 3 new role-permission mappings in C-04's tables. C-08 MUST NOT implement its own permission system.

#### Scenario: Unauthenticated request is rejected
- **WHEN** an unauthenticated user requests any `/api/v1/config/*` endpoint
- **THEN** the system returns 401

#### Scenario: Teacher cannot create a key
- **WHEN** a Teacher POSTs `/api/v1/config/keys`
- **THEN** the system returns 403 (the Teacher role does not have `config.key.create`)

#### Scenario: Institute Admin can override values in own institution
- **WHEN** an Institute Admin POSTs `/api/v1/config/values` with `scope_type="institution"`, `scope_id=<their own institution>`
- **THEN** the system accepts the request and creates the value

#### Scenario: Institute Admin cannot create keys
- **WHEN** an Institute Admin POSTs `/api/v1/config/keys`
- **THEN** the system returns 403 (key registry is Platform-Owner-only)

#### Scenario: Client Director can set Client and Institution values
- **WHEN** a Client Director POSTs `/api/v1/config/values` with `scope_type="client"` (own client) or `scope_type="institution"` (own client's institution)
- **THEN** the system accepts the request

#### Scenario: Platform Owner can do anything
- **WHEN** a Platform Owner requests any `/api/v1/config/*` endpoint
- **THEN** the system accepts the request (subject to payload validation)

### Requirement: Tenant Isolation via RLS

The system MUST enforce tenant isolation on `configuration_value` via PostgreSQL Row-Level Security, consistent with the migration-007 pattern. Platform-scope values are stored on the key (not in `configuration_value`), so Platform Owner queries bypass RLS for global visibility. `configuration_key` is global (no RLS) since the registry is read by all roles.

#### Scenario: RLS blocks cross-client value reads
- **WHEN** a Client Director at Client A queries `SELECT * FROM configuration_value` directly via SQL
- **THEN** only rows where `client_id=<Client A>` are returned

#### Scenario: RLS blocks cross-institution value reads
- **WHEN** an Institute Admin at Institution X queries `SELECT * FROM configuration_value` directly via SQL
- **THEN** only rows where `institution_id=<Institution X>` are returned

#### Scenario: Platform Owner bypasses RLS
- **WHEN** a Platform Owner queries `SELECT * FROM configuration_value` directly via SQL
- **THEN** all rows are returned (RLS bypass)

#### Scenario: ConfigurationKey is global
- **WHEN** any authenticated user queries `SELECT * FROM configuration_key`
- **THEN** all rows are returned (no RLS on the registry)

### Requirement: Seed Catalog of 15 Keys

The system MUST seed 15 configuration keys across 5 categories via Alembic migration `009_c08_configuration.py`. The `attendance.statuses` key MUST be seeded with `type="json"`, `merge_strategy="append_lists"`, `default_value=["present", "absent"]`, `category="Business Rules"`, `module="attendance"`. The migration MUST also seed the 8 C-04 permissions and ~13 role-permission mappings.

#### Scenario: Migration seeds the 15 keys
- **WHEN** the migration `009_c08_configuration.py` is applied to a fresh database
- **THEN** `SELECT COUNT(*) FROM configuration_key` returns 15

#### Scenario: Migration seeds audit rows for each key
- **WHEN** the migration applies the 15 seed keys
- **THEN** 15 `configuration_audit` rows are written with `action="key_created"`, `actor_user_id=NULL`, `actor_role="system"`

#### Scenario: Migration seeds C-04 permissions
- **WHEN** the migration applies
- **THEN** 8 new rows exist in `permission` (`config.key.create`, `config.key.update`, `config.key.deprecate`, `config.key.list`, `config.value.create`, `config.value.update`, `config.value.delete`, `config.audit.read`)

#### Scenario: Migration seeds role-permission mappings
- **WHEN** the migration applies
- **THEN** the `role_permission` table has new rows for PlatformOwner (all 8), ClientDirector (5), and InstituteAdmin (5)

### Requirement: Module Scope Deferred to Phase 2

The system MUST NOT support a Module scope for configuration overrides in Phase 1. The `module` column on `ConfigurationKey` is a namespace/category only, not a runtime scope. The `scope_type` ENUM in `configuration_value` has exactly three values: `platform`, `client`, `institution`.

#### Scenario: Module scope is rejected
- **WHEN** any user POSTs `/api/v1/config/values` with `scope_type="module"`
- **THEN** the system returns 400 (invalid scope_type)

#### Scenario: Module is a namespace
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` with `module="attendance"`
- **THEN** the key is stored with `module="attendance"` for namespace filtering, but resolution is unaffected (the `module` column plays no role in scope inheritance)

### Requirement: Type-Only Validation at Write

The system MUST validate at write time that the value matches the declared type. Business constraints (HH:MM, enum of allowed values, regex) MUST NOT be enforced at write time. The optional `allowed_values` field on `ConfigurationKey` is a hint only and is not enforced.

#### Scenario: Wrong type at write is rejected
- **WHEN** a user POSTs `/api/v1/config/values` for a key with `type="number"` and provides a string value
- **THEN** the system returns 400

#### Scenario: JSON value must parse
- **WHEN** a user POSTs `/api/v1/config/values` for a key with `type="json"` and provides an invalid JSON string
- **THEN** the system returns 400

#### Scenario: Business constraint is module's responsibility
- **WHEN** a user sets `attendance.markingCutoffTime` to `"banana"`
- **THEN** the C-08 system accepts the value (it is a string) and the Attendance module is responsible for parsing and rejecting malformed values at read time

### Requirement: Default Value Required at Key Creation

Every `ConfigurationKey` MUST have a non-null `default_value` at the platform level. Creation MUST fail with 400 if `default_value` is missing or null.

#### Scenario: Key creation with no default fails
- **WHEN** a Platform Owner POSTs `/api/v1/config/keys` with `default_value=null`
- **THEN** the system returns 400

#### Scenario: Default always resolves
- **WHEN** `config.get(key, ...)` is called and no override exists at any scope
- **THEN** the system returns the key's `default_value`

### Requirement: Soft Delete and Deprecation

The system MUST support soft deletion of configuration keys via `is_deprecated=true`. New value overrides on deprecated keys MUST be rejected (409). Existing overrides MUST continue to be readable. After 90 days from `deprecated_at`, deprecated keys MUST auto-hide from the default list response but remain in the database.

#### Scenario: PATCH soft-deletes a key
- **WHEN** a Platform Owner PATCHes `/api/v1/config/keys/{id}` with `is_deprecated=true`, `replacement_key="attendance.cutoffTime"`
- **THEN** the key is marked deprecated; new value POSTs return 409; existing value reads continue; `GET /api/v1/config/keys/{id}` still returns the key

#### Scenario: Hard delete is not supported
- **WHEN** a Platform Owner DELETEs `/api/v1/config/keys/{id}`
- **THEN** the system returns 405 (soft delete only)

#### Scenario: 90-day auto-hide
- **WHEN** a key has `is_deprecated=true` and `deprecated_at < now() - 90 days`
- **THEN** the key is excluded from `GET /api/v1/config/keys` (default response) but is returned if the `?include_deprecated=true` query parameter is set

### Requirement: REST API Surface Under /api/v1/config/

The system MUST expose 12 endpoints under `/api/v1/config/`, all of which require a Bearer token and use the existing `require_permission` dependency from C-04. Every endpoint MUST have an OpenAPI `summary` field.

#### Scenario: All 12 endpoints are registered
- **WHEN** the application starts and the ConfigurationManifest is loaded
- **THEN** the following routes are reachable: `POST /api/v1/config/keys`, `GET /api/v1/config/keys`, `GET /api/v1/config/keys/{id}`, `PATCH /api/v1/config/keys/{id}`, `DELETE /api/v1/config/keys/{id}`, `POST /api/v1/config/values`, `GET /api/v1/config/values`, `PATCH /api/v1/config/values/{id}`, `DELETE /api/v1/config/values/{id}`, `GET /api/v1/config/audit`, `POST /api/v1/config/resolve`, `GET /api/v1/config/resolve/{key}`

#### Scenario: Every endpoint has an OpenAPI summary
- **WHEN** a user navigates to `/docs`
- **THEN** every C-08 endpoint is listed with a `summary` field describing its purpose

### Requirement: Kernel Manifest Registration

The `ConfigurationManifest` MUST be registered in `backend/kernel/manifest.py` so that the app factory wires its routes, on-startup cache load, and NOTIFY LISTEN handler.

#### Scenario: Manifest wires the router
- **WHEN** the application starts
- **THEN** the ConfigurationManifest's `register_routes(app)` is called and all 12 routes are registered with the FastAPI app

#### Scenario: Manifest loads cache on startup
- **WHEN** the application starts
- **THEN** the ConfigurationManifest's `on_startup` hook loads all keys and values into the in-memory dict, and `config.get(...)` is ready

#### Scenario: Manifest subscribes to NOTIFY
- **WHEN** the application starts
- **THEN** the ConfigurationManifest's NOTIFY listener subscribes to the `config_changes` channel on the database connection
