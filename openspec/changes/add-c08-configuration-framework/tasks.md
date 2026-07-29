# C-08 Configuration Framework — Implementation Tasks

## 1. Migration: Schema, Seed Data, RLS, NOTIFY Trigger

- [x] 1.1 Create migration file `backend/migrations/versions/009_c08_configuration.py` with revision chain pointing to `008_nullable_institution_id`
- [x] 1.2 Add `upgrade()` creating 3 tables: `configuration_key`, `configuration_value`, `configuration_audit` with all columns per PRD §5
- [x] 1.3 Add `downgrade()` that drops the 3 tables in reverse FK order
- [x] 1.4 Add `upgrade()` step to insert 8 rows into C-04 `permission` table: `config.key.create`, `config.key.update`, `config.key.deprecate`, `config.key.list`, `config.value.create`, `config.value.update`, `config.value.delete`, `config.audit.read` (with `ON CONFLICT DO NOTHING`)
- [x] 1.5 Add `upgrade()` step to insert ~13 rows into C-04 `role_permission` table: PlatformOwner → all 8, ClientDirector → 5 (config.value.{create,update,delete}, config.key.list, config.audit.read), InstituteAdmin → 5 (same as CD)
- [x] 1.6 Add `upgrade()` step to seed 15 keys into `configuration_key` covering 5 categories: 4 Business Rules (attendance.markingCutoffTime, attendance.statuses [json+append_lists+default=['present','absent']], fee.lateFeePercentage, leave.autoApproveUnderDays), 3 Display (display.dateFormat, display.timezone, display.language), 3 Academic (academic.gradingScale, academic.passPercentage, academic.termStructure), 2 Notifications (notification.attendanceAbsenceAlert, notification.defaultChannel), 2 Homework (homework.allowLateSubmission, homework.maxAttachmentsPerAssignment), 1 Platform (platform.maxFileUploadMB)
- [x] 1.7 Add `upgrade()` step to write 15 `configuration_audit` rows (one per seed key) with `action='key_created'`, `actor_user_id=NULL`, `actor_role='system'`
- [x] 1.8 Add RLS policy on `configuration_value` filtering by `client_id` (always) and `institution_id` (when populated), with Platform Owner bypass consistent with migration 007
- [x] 1.9 Add PostgreSQL trigger function + trigger on `configuration_value` (INSERT/UPDATE/DELETE) emitting NOTIFY on `config_changes` channel with action type and row id
- [x] 1.10 Add PostgreSQL trigger function + trigger on `configuration_key` (INSERT/UPDATE/DELETE) emitting NOTIFY on `config_changes` channel
- [x] 1.11 Verify migration applies cleanly on fresh DB: `alembic upgrade head` exits 0, `SELECT COUNT(*) FROM configuration_key` returns 15, `SELECT COUNT(*) FROM configuration_audit WHERE actor_user_id IS NULL` returns 15
- [x] 1.12 Verify migration applies cleanly on existing cloud Supabase DB: connect via psql, run `alembic upgrade head`, run same verification queries
- [x] 1.13 Verify `alembic downgrade -1` cleanly drops all 3 tables, the 8 permissions, and the 13 role-permission mappings

## 2. Kernel Module Scaffold

- [x] 2.1 Create `backend/kernel/config/__init__.py` (empty package init)
- [x] 2.2 Create `backend/kernel/config/manifest.py` with `ConfigurationManifest` class implementing `ModuleManifest` Protocol: `register_routes(app)`, `register_casbin_policies(enforcer)`, `on_startup()`, `on_shutdown()`
- [x] 2.3 Create `backend/kernel/config/models/__init__.py` (empty init)
- [x] 2.4 Create `backend/kernel/config/repos/__init__.py` (empty init)
- [x] 2.5 Create `backend/kernel/config/services/__init__.py` (empty init)
- [x] 2.6 Create `backend/kernel/config/routes/__init__.py` (empty init)
- [x] 2.7 Create `backend/kernel/config/dependencies.py` with `get_configuration_service` and `require_config_scope` (service-layer scope guard)

## 3. ORM Models

- [x] 3.1 Create `backend/kernel/config/models/configuration_models.py`
- [x] 3.2 Define `ConfigurationKey` ORM model with all columns from PRD §5.1 using SQLAlchemy 2.0 typed `Mapped[...]` style
- [x] 3.3 Define `ConfigurationValue` ORM model with all columns from PRD §5.2, FKs to `configuration_key`, `client`, `institution`, `app_user`; UNIQUE constraint on (`key_id`, `scope_type`, `scope_id`)
- [x] 3.4 Define `ConfigurationAudit` ORM model with all columns from PRD §5.3, FK to `configuration_key`
- [x] 3.5 Define ENUM types for `configuration_type`, `configuration_scope_type`, `configuration_category`, `configuration_audit_action` (use SQLAlchemy `Enum` with `name=...`)
- [x] 3.6 Verify models import cleanly: `from kernel.config.models.configuration_models import ConfigurationKey, ConfigurationValue, ConfigurationAudit` works

## 4. Repository Layer

- [x] 4.1 Create `backend/kernel/config/repos/configuration_repo.py` with `ConfigurationRepository` class inheriting `TenantAwareRepositoryBase`
- [x] 4.2 Implement `list_keys(filters: KeyFilters) -> list[ConfigurationKey]` with pagination, filtering by category/module/is_deprecated/is_feature_toggle, and 90-day auto-hide
- [x] 4.3 Implement `get_key(key_id) -> ConfigurationKey | None` and `get_key_by_name(key_name) -> ConfigurationKey | None`
- [x] 4.4 Implement `create_key(payload, actor_user_id) -> ConfigurationKey` (validates default_value presence, type match)
- [x] 4.5 Implement `update_key(key_id, payload, actor_user_id) -> ConfigurationKey` (metadata, default_value, deprecation fields)
- [x] 4.6 Implement `soft_delete_key(key_id, replacement_key, actor_user_id) -> ConfigurationKey` (sets is_deprecated=true, deprecated_at=now())
- [x] 4.7 Implement `list_values(filters: ValueFilters) -> list[ConfigurationValue]` with RLS-aware filtering
- [x] 4.8 Implement `get_value(key_id, scope_type, scope_id) -> ConfigurationValue | None` and `get_value_by_id(value_id) -> ConfigurationValue | None`
- [x] 4.9 Implement `create_value(payload, actor_user_id) -> ConfigurationValue` (validates type match, rejects deprecated keys, enforces unique constraint)
- [x] 4.10 Implement `update_value(value_id, payload, actor_user_id) -> ConfigurationValue`
- [x] 4.11 Implement `delete_value(value_id, actor_user_id) -> None`
- [x] 4.12 Implement `list_audit(filters: AuditFilters) -> list[ConfigurationAudit]` with RLS-aware filtering
- [x] 4.13 Implement `write_audit_row(key_id, scope_type, scope_id, action, actor_user_id, actor_role) -> None`

## 5. Service Layer

- [x] 5.1 Create `backend/kernel/config/services/configuration_service.py` with `ConfigurationService` class
- [x] 5.2 Inject `db: AsyncSession`, `repo: ConfigurationRepository`, `cache: ConfigurationCache`, `notifier: ConfigurationNotifier`
- [x] 5.3 Implement `create_key(...)` → repo.create_key, cache.add_key, notifier.notify, write_audit_row
- [x] 5.4 Implement `update_key(...)` → repo.update_key, cache.update_key, notifier.notify, write_audit_row
- [x] 5.5 Implement `soft_delete_key(...)` → repo.soft_delete_key, cache.update_key, notifier.notify, write_audit_row
- [x] 5.6 Implement `create_value(...)` with role-scope check: rejects if `current_user.client_id != payload.client_id` (or institution mismatch)
- [x] 5.7 Implement `update_value(...)` and `delete_value(...)` with similar role-scope check
- [x] 5.8 Implement `resolve(key, institution_id, client_id) -> tuple[value, source_scope]` — uses cache, walks institution → client → platform, applies merge_strategy
- [x] 5.9 Implement `get_resolved_with_source(key, institution_id, client_id) -> dict` for the resolve debug endpoint

## 6. In-Memory Cache and Resolver

- [x] 6.1 Create `backend/kernel/config/resolver.py` with `ConfigurationCache` class (singleton)
- [x] 6.2 Implement `load_all(db: AsyncSession)` that loads all `ConfigurationKey` and `ConfigurationValue` rows into in-memory dicts
- [x] 6.3 Implement `add_key(key)`, `update_key(key)`, `remove_key(key_id)` (cache patching methods)
- [x] 6.4 Implement `add_value(value)`, `update_value(value)`, `remove_value(value_id)`
- [x] 6.5 Implement `get_key_by_name(name) -> ConfigurationKey | None`
- [x] 6.6 Implement `get_value(key_id, scope_type, scope_id) -> ConfigurationValue | None` (looks up the in-memory dict)
- [x] 6.7 Implement `config.get(name, institution_id=None, client_id=None) -> Any` — top-level API; walks institution → client → platform; applies merge_strategy; returns resolved value
- [x] 6.8 Implement `apply_merge(parent_value, child_value, merge_strategy, value_type) -> Any` — handles replace, append_lists (set union, preserving order), deep_merge (RFC 7396), and "scalars always replace"
- [x] 6.9 Add `from kernel.config.resolver import config` as the public API entry point (a module-level singleton instance)
- [x] 6.10 Verify startup loads in < 500ms for 15 keys + 0 values (the seed-only case) using a timing log

## 7. NOTIFY/LISTEN Notifier

- [x] 7.1 Create `backend/kernel/config/notifier.py` with `ConfigurationNotifier` class
- [x] 7.2 Implement `notify(action: str, key_id: UUID, value_id: UUID | None) -> None` — runs `NOTIFY config_changes, '...'` SQL on the current connection
- [x] 7.3 Implement `start_listener(db: AsyncSession)` — opens a dedicated raw psycopg2 connection (via `psycopg2.connect` for the LISTEN), runs `LISTEN config_changes`, spawns an asyncio task that polls `notifies()` and calls `cache.reload_key_or_value(action, key_id, value_id)` on receipt
- [x] 7.4 Implement `stop_listener()` — cancels the asyncio task, closes the dedicated connection
- [x] 7.5 Wire `start_listener` in the manifest's `on_startup`; wire `stop_listener` in `on_shutdown`
- [x] 7.6 Verify single-instance: PATCH a value, immediately `config.get` returns new value
- [x] 7.7 Verify multi-instance behavior (manually, by running two app instances locally): PATCH in instance A, instance B reloads within 5s

## 8. Routes — Key CRUD (PO-only for write)

- [x] 8.1 Create `backend/kernel/config/routes/keys.py` with APIRouter
- [x] 8.2 Implement `POST /api/v1/config/keys` — gated on `require_permission('config.key', 'create')`, validates payload (default_value present, type in allowed list), returns 201
- [x] 8.3 Implement `GET /api/v1/config/keys` — gated on `require_permission('config.key', 'list')`, accepts query params (category, module, is_deprecated, is_feature_toggle, include_deprecated, page, page_size), returns paginated list
- [x] 8.4 Implement `GET /api/v1/config/keys/{id}` — gated on `require_permission('config.key', 'list')`, returns single key or 404
- [x] 8.5 Implement `PATCH /api/v1/config/keys/{id}` — gated on `require_permission('config.key', 'update')`, accepts partial payload (metadata, default_value, is_deprecated, replacement_key), returns 200
- [x] 8.6 Implement `DELETE /api/v1/config/keys/{id}` — gated on `require_permission('config.key', 'deprecate')`, BUT returns 405 Method Not Allowed (soft delete only via PATCH)
- [x] 8.7 Add OpenAPI `summary=` field to every endpoint

## 9. Routes — Value CRUD (role-scoped)

- [x] 9.1 Create `backend/kernel/config/routes/values.py` with APIRouter
- [x] 9.2 Implement `POST /api/v1/config/values` — gated on `require_permission('config.value', 'create')`, calls service which does role-scope check (rejects cross-tenant/cross-institution), returns 201
- [x] 9.3 Implement `GET /api/v1/config/values` — gated on `require_permission('config.value', 'list')` (or `config.audit.read`?), accepts filters (key_id, scope_type, scope_id, page, page_size), returns paginated list scoped to caller's role
- [x] 9.4 Implement `PATCH /api/v1/config/values/{id}` — gated on `require_permission('config.value', 'update')`, calls service which does role-scope check
- [x] 9.5 Implement `DELETE /api/v1/config/values/{id}` — gated on `require_permission('config.value', 'delete')`, calls service which does role-scope check
- [x] 9.6 Add OpenAPI `summary=` field to every endpoint

## 10. Routes — Audit and Resolve

- [x] 10.1 Create `backend/kernel/config/routes/audit.py` with APIRouter
- [x] 10.2 Implement `GET /api/v1/config/audit` — gated on `require_permission('config.audit', 'read')`, accepts filters (key, scope_type, scope_id, action, actor_user_id, from, to, page, page_size), returns paginated list scoped to caller's role
- [x] 10.3 Add OpenAPI `summary=` field
- [x] 10.4 Create `backend/kernel/config/routes/resolve.py` with APIRouter
- [x] 10.5 Implement `POST /api/v1/config/resolve` — gated on `require_permission('config.key', 'list')`, accepts `{key, scope_type, scope_id}`, returns `{key, resolved_value, source_scope}`
- [x] 10.6 Implement `GET /api/v1/config/resolve/{key}` — gated on `require_permission('config.key', 'list')`, accepts `?institution_id=&client_id=`, returns `{key, resolved_value, source_scope}`
- [x] 10.7 Add OpenAPI `summary=` field to both

## 11. Manifest Wiring and Kernel Registration

- [x] 11.1 Open `backend/kernel/manifest.py`, add `from kernel.config.manifest import manifest as config_manifest`
- [x] 11.2 Add `config_manifest` to the `KERNEL_MANIFESTS` list (or equivalent) so the app factory wires it
- [x] 11.3 Verify the app factory creates the app, calls `config_manifest.register_routes(app)`, calls `config_manifest.on_startup()`, and the 12 routes are reachable at `/api/v1/config/*`
- [x] 11.4 Verify Swagger at `/docs` lists all 12 endpoints with `summary` fields and the Bearer Authorize button works

## 12. Tests — Unit and Integration (~25 tests)

- [x] 12.1 Create `backend/tests/test_c08_configuration.py`
- [x] 12.2 Test: `test_create_key_succeeds_with_valid_payload` — PO creates a key, audit row written
- [x] 12.3 Test: `test_create_key_fails_without_default_value` — POST without default_value returns 400
- [x] 12.4 Test: `test_create_key_fails_with_invalid_type` — POST with type='enum' returns 400
- [x] 12.5 Test: `test_list_keys_paginated_and_filtered` — GET with filters returns correct subset
- [x] 12.6 Test: `test_soft_delete_key_blocks_new_values` — PATCH is_deprecated=true, then POST /values returns 409
- [x] 12.7 Test: `test_90_day_auto_hide` — manually set deprecated_at to 100 days ago, GET /keys excludes it
- [x] 12.8 Test: `test_institute_admin_creates_institution_value` — Admin POSTs value for own institution, succeeds
- [x] 12.9 Test: `test_cross_institution_value_rejected` — Admin POSTs value for another institution, 403
- [x] 12.10 Test: `test_client_director_creates_client_value` — CD POSTs Client-scope value, succeeds
- [x] 12.11 Test: `test_cross_client_value_rejected` — CD at Client A POSTs Client-scope value for Client B, 403
- [x] 12.12 Test: `test_duplicate_value_returns_409` — POST same (key_id, scope_type, scope_id) twice
- [x] 12.13 Test: `test_scope_institution_takes_precedence` — Platform default, Client override, Institution override → returns Institution
- [x] 12.14 Test: `test_scope_client_fallback` — Platform default, Client override, no Institution → returns Client
- [x] 12.15 Test: `test_scope_platform_fallback` — only default → returns default
- [x] 12.16 Test: `test_merge_strategy_replace` — list value with replace → child list fully replaces parent
- [x] 12.17 Test: `test_merge_strategy_append_lists` — list value with append_lists → child list unioned with parent
- [x] 12.18 Test: `test_merge_strategy_deep_merge` — JSON object with deep_merge → objects merged per RFC 7396
- [x] 12.19 Test: `test_scalar_always_replaces` — string with merge_strategy='append_lists' → still replaces
- [x] 12.20 Test: `test_in_memory_cache_serves_get` — `config.get(...)` returns in < 1ms (timing assertion)
- [x] 12.21 Test: `test_notify_listener_reloads_on_update` — PATCH a value, fire NOTIFY manually, verify cache reloads
- [x] 12.22 Test: `test_audit_written_on_every_change` — every create/update/delete writes an audit row
- [x] 12.23 Test: `test_audit_endpoint_filters_correctly` — GET /audit?key=X returns only X's audit
- [x] 12.24 Test: `test_unauthenticated_request_returns_401` — no Bearer token
- [x] 12.25 Test: `test_teacher_cannot_create_key` — Teacher POST /keys returns 403
- [x] 12.26 Test: `test_resolve_debug_endpoint_returns_source` — POST /resolve returns the source scope label
- [x] 12.27 Test: `test_rls_blocks_cross_client_value_read` — direct SQL from a Client-scoped role returns only own client's values
- [x] 12.28 Test: `test_rls_bypassed_for_platform_owner` — direct SQL from PO role returns all values
- [x] 12.29 Run the full test suite: `cd backend && uv run pytest -x` — verify 300 existing + ~25 new = ~325 tests pass
- [x] 12.30 Verify no regression: existing 300 tests still pass; C-08 has no behavioral effect on existing modules in Phase 1

## 13. Flow Documentation

- [x] 13.1 Create `school_erp_flow/c08/_c08_flow_index.md` referencing all 4 flows
- [x] 13.2 Create `school_erp_flow/c08/_c08_flow_01_key_creation.md` — PO creates a key via Swagger, sets default, sees it in the list
- [x] 13.3 Create `school_erp_flow/c08/_c08_flow_02_value_override.md` — Institute Admin overrides `attendance.markingCutoffTime` for their institution, resolution returns the new value
- [x] 13.4 Create `school_erp_flow/c08/_c08_flow_03_merge_semantics.md` — Institution appends `half_day` to `attendance.statuses`, resolution returns the union `['present', 'absent', 'half_day']`
- [x] 13.5 Create `school_erp_flow/c08/_c08_flow_04_audit_and_deprecation.md` — PO deprecates an old key, creates a new one, audit log shows the chain

## 14. End-to-End Smoke Test

- [x] 14.1 Start the backend: `cd backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000` — verify no errors
- [x] 14.2 Open Swagger at `http://127.0.0.1:8000/docs` — verify all 12 C-08 endpoints are listed with summaries
- [x] 14.3 Login as Platform Owner (`admin@school-erp.com` / `Shoby@123`) — verify Bearer token in Authorize
- [x] 14.4 Create a key: `POST /api/v1/config/keys` with `key=test.smoke`, `type=string`, `default_value="hello"` — verify 201
- [x] 14.5 List keys: `GET /api/v1/config/keys` — verify the new key is in the list
- [x] 14.6 Resolve the key: `GET /api/v1/config/resolve/test.smoke` — verify response is `{"key": "test.smoke", "resolved_value": "hello", "source_scope": "platform:default"}`
- [x] 14.7 Login as Client Director (`shoby.ansari586@gmail.com` / `Admin@123`) with `Host: meerutpublic.localhost`
- [x] 14.8 Create a Client-scope value: `POST /api/v1/config/values` with `key_id=<test.smoke's id>`, `scope_type=client`, `scope_id=<client id>`, `value="world"` — verify 201
- [x] 14.9 Resolve again: `GET /api/v1/config/resolve/test.smoke?client_id=<client id>` — verify response is `{"resolved_value": "world", "source_scope": "client:<client id>"}`
- [x] 14.10 Read audit: `GET /api/v1/config/audit?key=test.smoke` — verify 2 audit rows (key_created, value_created)
- [x] 14.11 Deprecate the key: `PATCH /api/v1/config/keys/{id}` with `is_deprecated=true`, `replacement_key=test.smoke2` — verify 200
- [x] 14.12 Try to create a new value for the deprecated key — verify 409
- [x] 14.13 Clean up: PATCH the test key to remove is_deprecated; DELETE the test value; ignore the test key (it will be a soft-deprecated noop after the smoke test)
