# Proposal — Authorization Consolidation (C-04 Single Source of Truth)

## Why

The School ERP has **two parallel authorization systems** feeding the same Casbin enforcer. C-01's hardcoded D11 permission matrix in `business/tenant_institution/policies.py` was a stopgap (July 8) until C-04's DB-driven `role_permission` table was built (July 14). C-04 was supposed to absorb C-01's policies — it never did.

This creates three concrete bugs:
1. **Action name mismatches** — C-01 uses `"transition"`, routes use `"transition_lifecycle"`. CD gets 403 on institution transition.
2. **Two sources of truth** — Developers edit Python code (C-01) OR a DB table (C-04) for permissions. Inconsistencies accumulate.
3. **ABAC is broken** — `require_permission` builds the Casbin object from `ctx`, so `sub.client_id == obj.client_id` always passes. Cross-tenant enforcement exists only at the RLS backstop.

**Goal:** Eliminate the parallel system. All policies come from C-04's `role_permission` table. `require_permission` accepts object attributes for real ABAC enforcement. RLS remains as defense-in-depth.

## What Changes

- **MODIFIED: `role_permission` table** — Add `scope` column (`any`/`tenant`/`institution`) mapping directly to Casbin policy scope. Default `institution` for existing C-02 role_permissions.
- **MODIFIED: `permission` table** — Add 9 missing permissions: `institution.archive`, `institution.list`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`, `institution_type.create`, `institution_type.update`, `user_profile.create`, `user.delete`.
- **MODIFIED: `role_permission` data** — Migrate C-01 roles (`client_director`, `institution_admin`, `cross_institution`) to `role_permission` with appropriate scopes (`tenant`/`institution`).
- **MODIFIED: `require_permission` signature** — Add `obj_client_id: uuid.UUID | None = None` and `obj_institution_id: uuid.UUID | None = None` keyword params. Casbin object built from params, not from ctx. ABAC scope check actually enforces.
- **MODIFIED: `policy_loader`** — Read `scope` from `role_permission.scope` column when building Casbin policies at startup.
- **MODIFIED: All C-01 routes** — Pass `obj_client_id`/`obj_institution_id` to `require_permission` (pre-fetch resource to get its client_id/institution_id).
- **MODIFIED: All C-02 routes** — Same ABAC parameter wiring.
- **MODIFIED: C-01 manifest** — Remove `register_casbin_policies` hook. C-04 is sole owner.
- **REMOVED: `business/tenant_institution/policies.py`** — All D11 policies migrated to DB.
- **REMOVED: `business/tenant_institution/casbin_model.conf`** — Duplicate model removed. Only `kernel/authz/casbin_model.conf` remains.
- **KEPT: Platform owner code bypass** — `require_permission` retains early-return for `is_platform_owner`. No DB entry for platform_owner (per D27, D28).

## Capabilities

### Modified Capabilities

- **`authorization` (MODIFIED)** — `require_permission` gains object-attribute params. `policy_loader` reads scope from DB. Migration adds scope column, missing permissions, C-01 role mappings. Platform owner bypass retained.
- **`tenant-institution` (MODIFIED)** — `policies.py` deleted. `casbin_model.conf` deleted. `register_casbin_policies` removed from manifest. All C-01 routes pass object attributes to `require_permission`.
- **`identity-user-management` (MODIFIED)** — All C-02 routes pass object attributes to `require_permission` for ABAC enforcement.

## Impact

- **Schema change:** `ALTER TABLE role_permission ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'institution'`
- **New migration:** `016_c04_authorization_consolidation.py` — scope column, 9 missing permissions, C-01 role migration
- **Modified code:** `backend/kernel/authz/dependencies.py` — `require_permission` signature change
- **Modified code:** `backend/kernel/authz/services/policy_loader.py` — read scope from DB
- **Modified code:** `backend/kernel/authz/manifest.py` — register scope-aware policies
- **Modified code:** All C-01 route files (~15 endpoints) — pass object attributes
- **Modified code:** All C-02 route files (~12 endpoints) — pass object attributes
- **Removed code:** `backend/business/tenant_institution/policies.py`
- **Removed code:** `backend/business/tenant_institution/casbin_model.conf`
- **Modified code:** `backend/business/tenant_institution/manifest.py` — remove `register_casbin_policies`
- **Risk:** Big-bang migration. If the migration has a bug, the app starts with incorrect policies. Mitigation: test in staging first.
