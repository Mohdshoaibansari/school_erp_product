# C-08 Configuration Framework — Design

## Context

The School ERP platform has been built sequentially through C-01 (Tenant & Institution), C-02 (Identity & User), C-03 (Authentication), C-04 (Authorization), and two business modules (Fees, Homework). Per the platform capability roadmap, C-08 (Configuration Framework) was sequenced at P2 in Phase 1, immediately after C-01, but was deferred during the original build. It is now being built to unblock the remaining Phase 1 capabilities (C-05 Academic Structure, C-06 Relationship Management, C-09 Notification Framework) and any future business module that needs configurable per-tenant behavior (e.g., Attendance's `attendance.statuses`, where one school uses 2 statuses and another uses 4).

Currently, every configurable value in the platform is hardcoded:
- `attendance.markingCutoffTime` → would be `"10:00 AM"` in code
- `fee.lateFeePercentage` → would be `2` in code
- `display.dateFormat` → would be `"DD/MM/YYYY"` in code
- `homework.maxAttachmentsPerAssignment` → would be `5` in code

This means every change requires a code deploy, an application restart, and a migration. Multi-tenant SaaS cannot scale under this model — different schools have different policies, and the platform cannot be a platform if every tenant gets the same behavior.

C-08 introduces a runtime configuration framework that the entire platform reads from. The design below explains the technical approach.

## Goals / Non-Goals

**Goals:**
- Centralize all runtime-configurable behavior in a single key-value store
- Support 4-level scope inheritance (Platform → Client → Institution → Module) with Module scope deferred to Phase 2
- Resolve values from memory in < 1ms (in-process dict, no DB hit on read)
- Propagate changes to running app instances within 5 seconds (NOTIFY/LISTEN)
- Audit every change (who/what/when, no before/after values)
- Enforce authorization through the existing C-04 Casbin enforcer (no new permission system)
- Provide a programmatic `config.get(key, institution_id=..., client_id=...)` API that works in any context
- Enforce tenant isolation via PostgreSQL RLS (defense-in-depth on top of the in-memory cache)
- Ship 15 seed keys demonstrating the capability across 5 categories
- Match the existing kernel module pattern (manifest, routes, services, repos, models, dependencies)

**Non-Goals:**
- Module-scope overrides (Phase 2)
- Admin UI (Phase 2; use Swagger in Phase 1)
- Before/after audit values (deferred; light audit only)
- Encrypted at-rest for sensitive values (Phase 2+)
- Hard delete of keys/values (never; soft delete only)
- Computed/expression values (static literals only)
- Multi-region replication (single-region only in Phase 1)
- Config export/import (Phase 2)
- Migrating existing modules (Fees, Homework) to consume C-08 (Phase 2; the seed keys are placeholders)

## Decisions

### Decision 1: In-memory dict keyed by (scope_type, scope_id, key_id) for resolution

**Choice:** Load all `ConfigurationKey` rows + all `ConfigurationValue` rows into in-memory dicts at app startup. `config.get(...)` walks `institution → client → platform` in the dict and returns the first match.

**Rationale:** The platform already has a hot path for every API request (every route reads from a database or service). Adding a DB roundtrip to every `config.get(...)` call (which happens 5-10 times per request) would add unacceptable latency. An in-memory dict provides O(1) lookups. The total memory cost is negligible (15-100 keys, ~1000s of value rows max).

**Alternatives considered:**
- **DB read per call** — simple, correct, but adds 5-10 roundtrips per request. Rejected.
- **Redis cache** — adds Redis as a hard infrastructure dependency. Rejected for Phase 1.
- **Per-request resolved snapshot in middleware** — a `ResolvedConfig` object built once per request. Cleaner module-side code, but loses the ability to use `config.get(...)` outside a request context (background jobs, migrations). Rejected.

**Trade-off:** In-memory cache must be kept in sync with the DB. This is handled via PostgreSQL NOTIFY/LISTEN (see Decision 2).

### Decision 2: PostgreSQL NOTIFY/LISTEN for multi-instance cache invalidation

**Choice:** Every UPDATE on `configuration_value` or `configuration_key` triggers a PostgreSQL NOTIFY on the `config_changes` channel. Other app instances LISTEN on this channel and reload their in-memory dict on receipt.

**Rationale:** PostgreSQL is already a hard dependency. NOTIFY/LISTEN is built into the database, requires no additional infrastructure (no Redis, no message broker), and provides sub-second propagation. Single-instance deployments get instant updates (the primary patches the dict before responding). Multi-instance deployments get ≤5s lag on follower instances.

**Alternatives considered:**
- **Redis pub/sub** — fast and well-understood, but adds Redis as a hard dependency. Rejected for Phase 1.
- **Periodic polling (every N seconds)** — simpler but adds latency and unnecessary DB load. Rejected.
- **Read-on-every-call** — defeats the purpose of in-memory caching. Rejected.

**Trade-off:** Multi-instance deployments may serve stale values for up to 5s after an UPDATE. Acceptable for a configuration framework (no business logic depends on millisecond-freshness).

### Decision 3: Per-key `merge_strategy` field (replace, append_lists, deep_merge) instead of type-based semantics

**Choice:** Each `ConfigurationKey` declares its own `merge_strategy`. Default is `replace`. Optional values are `append_lists` (lists unioned) and `deep_merge` (JSON objects deep-merged per RFC 7396, lists replaced). Scalars (string, number, boolean, date) ALWAYS use replace regardless of the declared strategy.

**Rationale:** Different keys have different merge needs. `attendance.statuses` (a list) wants union semantics — adding `half_day` should not require re-listing `present` and `absent`. `display.dateFormat` (a string) wants replace semantics. Putting the strategy on the key (not the type) lets each key opt into the right behavior. The "scalars always replace" rule prevents surprising behavior when someone declares `merge_strategy="append_lists"` on a string key.

**Alternatives considered:**
- **Always replace (uniform)** — simplest, but every override is a full copy. Risk of accidental removal of platform defaults. Rejected.
- **Always merge by type** — uniform but inflexible. Can't remove a platform default from a list. Rejected.
- **Per-type strategies** — e.g., strings replace, lists append. Forces every list key to use append (some may want replace). Rejected.

**Trade-off:** Keys must be designed with their merge strategy in mind. Documented in the PRD's `merge_strategy` field per seed key.

### Decision 4: Dedicated `configuration_key` + `configuration_value` + `configuration_audit` tables (no JSONB on existing tables)

**Choice:** Three new tables in a new schema. `configuration_key` is the registry (metadata, types, defaults, merge strategy, deprecation). `configuration_value` is the override store (key + scope + value, with FKs to client/institution for tenant isolation). `configuration_audit` is the change log.

**Rationale:** A central registry is essential for discoverability (what keys exist?), type safety (C-08 validates that values match the declared type), and avoiding typo-driven bugs (a misspelled `markingCutOffTime` silently returns NULL forever with a JSONB column; with a registry, the typo is a 400). Separate value and audit tables make the resolution path (key → value) and the audit path (key + value → audit) independent and queryable.

**Alternatives considered:**
- **JSONB on `client` and `institution` tables** — no new tables, but no central registry, no type validation, no feature_toggle category, hard to audit centrally. "Config sprawl" risk. Rejected.
- **Hybrid (registry table + JSONB on scope tables)** — complex queries across multiple JSONB columns, RLS per scope table. Rejected.

**Trade-off:** Three new tables. Small storage cost. Worth it for the central registry.

### Decision 5: Lightweight audit (who/what/when, no before/after)

**Choice:** The `configuration_audit` table records `key_id`, `scope_type`, `scope_id`, `action`, `actor_user_id`, `actor_role`, `timestamp`. No `old_value` or `new_value` is stored.

**Rationale:** A configuration framework's primary audit need is "who changed what and when?" — not "what did it change from and to?" The latter is recoverable by re-reading the current state; the former is not. Light audit is fast, cheap, and sufficient for compliance. If a real rollback need arises, a future enhancement can add a heavier audit table.

**Alternatives considered:**
- **Heavy audit (old_value + new_value)** — useful for rollback UI, but doubles the storage cost and complicates the schema. Deferred.
- **No audit (logs only)** — log lines are not queryable, easy to lose. Rejected.

**Trade-off:** No rollback UI in Phase 1. A future "revert to N days ago" feature would need a heavier audit.

### Decision 6: 8 new C-04 permissions registered in C-08's migration, with role-permission mappings

**Choice:** The C-08 migration `009_c08_configuration.py` inserts 8 rows into C-04's `permission` table and ~13 rows into `role_permission`. C-08's manifest does NOT register Casbin policies in code.

**Rationale:** Per platform Non-Negotiable Rule 3, "no module implements its own permission system." C-04 owns the permission framework. C-08 extends the framework's data. This matches the pattern established by Fees and Homework (which also insert rows into C-04's tables). The pattern is well-tested: C-04's `on_startup` auto-loads the new rows at next app restart, the Casbin enforcer singleton picks them up, and `require_permission(...)` enforces them.

**Alternatives considered:**
- **C-08-internal permission checks** — would violate Rule 3 and create drift risk. Rejected.
- **Hardcoded role checks in routes** — cheapest, but loses the ability to delegate config to a new role without code change. Rejected.

**Trade-off:** The C-08 migration must be applied AFTER the C-04 migration. Migration ordering is enforced by Alembic's revision chain.

### Decision 7: Platform-scope values are NOT separate rows

**Choice:** The Platform-level default value lives on the `ConfigurationKey.default_value` field. There is no `configuration_value` row with `scope_type='platform'`. The Platform Owner's "set platform default" is a PATCH on the key, not a POST on values.

**Rationale:** The platform default is a property of the key (it determines what an institution with no override gets). Storing it on the key simplifies the resolution walk (no need to look up a Platform-scope value row) and makes the seed migration natural (one INSERT per key, with the default embedded). It also makes the "default is required" rule (D9) trivially enforceable at the schema level.

**Alternatives considered:**
- **Platform-scope value rows** — symmetric with Client/Institution scopes, but introduces a redundant representation (the default is on the key AND in a value row). Confusing. Rejected.

**Trade-off:** The `scope_type` ENUM has only 3 values (platform, client, institution), not 4. The Platform Owner never writes to `/api/v1/config/values` for the platform default — they PATCH the key.

### Decision 8: Module scope is a namespace, not a runtime scope (Phase 2)

**Choice:** The `module` column on `ConfigurationKey` is a TEXT field for namespace/category filtering. It is NOT a runtime scope. The `scope_type` ENUM has exactly 3 values (platform, client, institution).

**Rationale:** Per the platform dependency map, C-08 is Level 1 (no dependencies). Module scope would require a `module_instance` table that C-08 doesn't own (it would belong to C-07 Subscription Management or a future module-registry capability). Building Module scope now would create a premature dependency. The `module` column as namespace is forward-compatible: when Module scope is added in Phase 2, a migration adds a 4th ENUM value and a new resolution path.

**Alternatives considered:**
- **Build Module scope in Phase 1** — would require inventing a `module_instance` table now. Premature. Rejected.

**Trade-off:** A future "Attendance module override at Whitefield school" use case must wait for Phase 2. Phase 1's `attendance.*` keys are institution-scoped (or platform-default).

### Decision 9: Type-only validation at write; business constraints at consume

**Choice:** C-08 validates that the value's JSON type matches the declared `type` (string/number/boolean/json/date). C-08 does NOT validate HH:MM format, regex, min/max, or enums of allowed values. The consuming module is responsible for these checks.

**Rationale:** C-08 doesn't know the semantics of `attendance.markingCutoffTime` — it only knows it's a string. The Attendance module knows it must parse as `HH:MM`. Putting format validation in C-08 would require a constraint system that C-08 would have to maintain forever. Putting it in the consuming module keeps each module's validation local and discoverable. The optional `allowed_values` JSONB on the key is a hint only (UI suggestions) and is not enforced.

**Alternatives considered:**
- **Centralized constraint validation** — every key declares regex, min, max, enum. C-08 enforces at write. More strict, but centralizes validation logic that varies per module. Rejected for Phase 1.

**Trade-off:** A misformatted `attendance.markingCutoffTime` will pass C-08's write check and fail at read time. The module's error handling must be defensive. (Trade-off is acceptable; it matches the existing pattern of "platform validates structure, modules validate semantics.")

### Decision 10: `config.get(key, institution_id=None, client_id=None)` — explicit scope kwargs

**Choice:** The programmatic API takes the key and the resolution context as explicit kwargs. No `TenantContext` dependency.

**Rationale:** `config.get(...)` must work in any context: FastAPI request, background job (Celery/RQ/arq), migration script, test. Some of these have no `TenantContext` (background jobs run with explicit IDs from the job payload). Making the API take explicit kwargs removes the implicit context dependency. It also makes the function trivial to mock in tests.

**Alternatives considered:**
- **`config.get(key)` reading from `TenantContext`** — concise at call site, but breaks outside request scope. Rejected.
- **FastAPI dependency injection (`ResolvedConfig`)** — clean, but adds DI boilerplate. Loses the ability to use `config.get(...)` outside a request. Rejected.

**Trade-off:** Call sites are slightly more verbose (`config.get(key, institution_id=inst)` instead of `config.get(key)`). Acceptable; explicit > implicit.

### Decision 11: Soft delete via PATCH (not DELETE) on keys; 90-day auto-hide

**Choice:** DELETE on `/api/v1/config/keys/{id}` returns 405. Soft delete is via PATCH `is_deprecated=true` + `replacement_key`. Deprecated keys auto-hide from the list response after 90 days but remain in the DB.

**Rationale:** Hard-deleting a key would orphan all its value rows (FK constraint) and break any module still reading it. Soft delete is non-destructive: the key is marked deprecated, new overrides are blocked (409), but existing reads continue to work. The 90-day window gives modules time to migrate. After 90 days, the key auto-hides from the default list (but is still accessible via `?include_deprecated=true` and via direct GET).

**Alternatives considered:**
- **Hard delete (CASCADE)** — clean but destructive. A typo on a critical key would break all tenants immediately. Rejected.
- **No deprecation, just leave dead keys** — registry fills with stale keys over time. Rejected.

**Trade-off:** Deprecated keys accumulate in the DB forever. Acceptable; the storage cost is negligible.

### Decision 12: 15 seed keys demonstrating all 5 categories and 2 merge strategies

**Choice:** The migration seeds 15 keys: 4 Business Rules, 3 Display, 3 Academic, 2 Notifications, 2 Homework, 1 Platform. `attendance.statuses` is seeded with `merge_strategy="append_lists"` and `default=["present","absent"]` to demonstrate the list-union semantics.

**Rationale:** A seed catalog of 15 keys covers all 5 categories, all 5 value types (string, number, boolean, json, date), both merge strategies (replace for most, append_lists for `attendance.statuses`), and the full module namespace (attendance, fees, homework, display, academic, notification, platform). The seed catalog is enough to demonstrate the system end-to-end without depending on any business module.

**Alternatives considered:**
- **Empty seed (modules register their own)** — requires every module to have a registration step. Keys appear gradually. No central audit. Rejected.
- **3 keys only (minimal demonstrator)** — too thin to validate the architecture across types and categories. Rejected.

**Trade-off:** The seed includes 2 homework keys that are not yet consumed by the Homework module. This is intentional: Phase 1 ships the framework; Phase 2 migrates Homework. The keys are placeholders showing how the system works.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Multi-instance cache stale for up to 5s** | Acceptable for a configuration framework. Document in the API guide that "configuration changes may take up to 5 seconds to propagate to all instances." If tighter propagation is needed, future work can move to Redis pub/sub. |
| **NOTIFY trigger failure silently drops updates** | The trigger is `BEFORE UPDATE`, so a failure would fail the UPDATE itself. The application code wraps the UPDATE in a transaction; if the trigger raises, the transaction rolls back. There is no silent drop. |
| **In-memory dict grows unbounded** | Negligible — at 100 clients × 100 institutions × 100 keys, the dict is ~1M entries, ~hundreds of MB. Acceptable. If memory becomes an issue, the dict can be split by client and lazy-loaded. |
| **8 new C-04 permissions create a large migration** | The migration is `009_c08_configuration.py`. The permissions are inserted with `ON CONFLICT DO NOTHING`, so re-running the migration is safe. |
| **Deprecated keys auto-hide after 90 days but no UI exists to surface the 90-day warning** | Phase 1 has no UI, so the 90-day auto-hide is a behavior visible in Swagger. Phase 2 admin UI will surface the deprecation status with a clear visual. |
| **No "revert to N days ago" capability because audit is light** | Documented. Phase 1 does not support rollback. Future enhancement: a heavier audit table with old_value/new_value. |
| **`config.get(...)` outside a request must pass institution_id/client_id explicitly** | The function signature requires them as kwargs. This is enforced at the call site, not the type system. A code review checklist should include "every `config.get(...)` call passes institution_id or client_id." |
| **Module scope is deferred, but seed keys have `module="attendance"` etc.** | The `module` column is a namespace filter, not a scope. UI in Phase 2 will use it to group keys by module. The seed keys demonstrate the namespace without creating a Phase 1 Module scope. |
| **No consumer migration in Phase 1 means the seed keys are unused at runtime** | Intentional. The seed catalog is enough to demonstrate the system. Phase 2 migrates Fees and Homework to consume `config.get(...)`. The PRD explicitly excludes consumer migration from Phase 1. |

## Migration Plan

### Phase 0: Pre-implementation
1. Review this design with stakeholders.
2. Confirm the 8 C-04 permissions and ~13 role-permission mappings with C-04 maintainer.
3. Confirm the 15 seed keys with product owner.

### Phase 1: Implementation
1. Create the migration `009_c08_configuration.py`. Run on a fresh DB and on the existing cloud Supabase DB. Verify with `SELECT COUNT(*) FROM configuration_key` returning 15.
2. Create the kernel module `backend/kernel/config/`. Implement the resolver, the service, the routes, the manifest.
3. Wire the manifest in `backend/kernel/manifest.py`. Restart the backend. Verify Swagger lists the 12 endpoints.
4. Write ~25 tests in `tests/test_c08_configuration.py`. Run the full test suite. Verify 325+ tests pass.
5. Write 4 flow documents in `school_erp_flow/c08/`.

### Phase 2: Rollout
1. Deploy the migration to staging.
2. Deploy the backend code to staging.
3. Smoke test: PO creates a key, sets a default; CD overrides at Client scope; Admin overrides at Institution scope; resolve returns the right value; audit log shows the chain; deprecated key blocks new overrides.
4. Deploy to production.
5. **No module migration in this rollout.** Fees and Homework continue to use hardcoded values. The seed keys are placeholders.

### Rollback Strategy
- **Code rollback:** Revert the manifest, the routes, the services, the resolver. The migration can stay (its tables are inert if not queried).
- **Data rollback:** If the migration itself must be rolled back: `alembic downgrade -1`. This drops the 3 C-08 tables, removes the 8 C-04 permissions, removes the 13 role-permission mappings. **NOTE:** Downgrading the migration deletes the seed catalog. Re-upgrading re-seeds it.

## Open Questions

None. All 16 PRD decisions (D1–D16) are locked, and this design captures the technical approach for each. Any new questions that arise during implementation (e.g., specific Casbin enforcer details) will be resolved in the tasks.md and during code review.
