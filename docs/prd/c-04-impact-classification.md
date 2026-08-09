# Impact Classification — C-04 Authorization Consolidation

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-04 — Authorization (consolidation with C-01)
> **Decisional inputs:** `docs/prd/c-04-authorization-consolidation.md` (PRD), `docs/architecture/analysis-authorization-consolidation.md` (analysis), `docs/prd/c-04-authorization.md` (original C-04 PRD), `docs/prd/c-01-tenant-institution.md` (D11 matrix)
> **Verification:** `openspec list --specs` returns existing C-04 archived spec at `openspec/changes/archive/2026-07-14-add-c04-authorization/specs/authorization/spec.md`. C-01 archived spec at `openspec/changes/archive/2026-07-08-add-c01-tenant-institution/specs/tenant-institution/spec.md`.

---

## Classification

- **Domain status:** EXISTING (C-04) — modifications to existing capability
- **Delta type:** MODIFIED (C-04 authorization, C-01 tenant-institution)
- **Cross-cutting:** YES — affects 3 modules (C-01, C-04, C-02 user routes), 1 spec (authorization), schema (role_permission table), all routes using require_permission
- **Recommended OpenSpec change name:** `consolidate-c04-authorization-single-source`

## Reasoning

This change consolidates two parallel authorization systems into one:
1. C-01's hardcoded D11 permission matrix in `business/tenant_institution/policies.py`
2. C-04's DB-driven `role_permission` table

After consolidation:
- All authorization policies live in C-04's `role_permission` table
- `require_permission` accepts object attributes (client_id, institution_id) for ABAC enforcement
- C-01's `policies.py` and `casbin_model.conf` are deleted
- C-01's `register_casbin_policies` hook is removed

This touches:
- **C-04 Authorization** — MODIFIED. `require_permission` signature change, `policy_loader` reads scope from DB, migration adds scope column + missing permissions + C-01 role mappings.
- **C-01 Tenant & Institution** — MODIFIED. `policies.py` deleted, `casbin_model.conf` deleted, manifest's `register_casbin_policies` removed.
- **C-02 Identity & User Management** — MODIFIED. All routes that use `require_permission` need to pass object attributes (for ABAC).

## ADDED requirements (high-level)

### C-04 — authorization

- **Scope column on `role_permission`** — `role_permission.scope` column with values `any`/`tenant`/`institution`. Maps directly to Casbin policy scope. (ADR D26)
- **Missing permissions in catalog** — Add `institution.archive`, `institution.list`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`, `institution_type.create`, `institution_type.update`, `user_profile.create`, `user.delete`. Present in routes or C-01 but missing from C-04. (ADR D18)
- **C-01 roles in `role_permission`** — `client_director`, `institution_admin`, `cross_institution` get role-permission mappings with appropriate scopes (`tenant`/`institution`). (ADR D11)
- **`require_permission` accepts object attributes** — New params `obj_client_id`, `obj_institution_id`. Casbin object built from params, not from ctx. ABAC scope check actually enforces. (ADR D7, D19)
- **Platform owner code bypass retained** — `require_permission` returns early for `is_platform_owner`. No DB entry for platform_owner. (ADR D27, D28)

### C-01 — tenant-institution (cleanup)

- **Delete `policies.py`** — `business/tenant_institution/policies.py` no longer exists. All policies migrated to C-04 DB. (ADR D14)
- **Delete duplicate `casbin_model.conf`** — `business/tenant_institution/casbin_model.conf` no longer exists. Model only at `kernel/authz/casbin_model.conf`. (ADR D14)
- **Remove C-01 `register_casbin_policies` hook** — C-01 manifest no longer registers policies. C-04 is sole owner. (ADR D14)

## MODIFIED behavior

- **`require_permission` signature** — Adds `obj_client_id: uuid.UUID | None = None` and `obj_institution_id: uuid.UUID | None = None` keyword params. Existing callers work unchanged (backward compatible). New callers pass object attributes for ABAC enforcement.
- **C-01 routes** — All C-01 routes that use `require_permission` need to pass `obj_client_id`/`obj_institution_id` (after pre-fetching the resource). ~15 routes affected.
- **C-02 routes** — All C-02 routes that use `require_permission` need to pass `obj_client_id`/`obj_institution_id`. ~12 routes affected.
- **Policy registration order** — C-01 manifest no longer registers policies. C-04 manifest registers all policies. No more two-step registration.
- **CD transition_lifecycle bug fixed** — CD role can now transition institutions (action name match between route and DB).

## REMOVED behavior

- **C-01 hardcoded policies** — `PERMISSION_POLICIES` and `ROLE_HIERARCHY` in `policies.py` removed. All coverage migrated to `role_permission` table.
- **C-01 Casbin model** — Duplicate `casbin_model.conf` removed. Only `kernel/authz/casbin_model.conf` remains.
- **C-01 `register_policies` function** — Removed from `policies.py`. C-04's `register_policies_from_map` is the sole registration path.
- **C-01 `build_enforcer` function** — Dead function removed. Tests that used it now use C-04's `build_enforcer`.

## Boundary relationships (NOT modifications)

| Relationship | Direction | Other capability | Why NOT a modification |
|---|---|---|---|
| New permissions added to `permission` table | C-04 → C-08 Config | C-08 config (if permission reads are cached) | Permission table is read at startup, not config-driven. No C-08 change needed. |
| Scope column on `role_permission` | C-04 → C-04 | Self | Same domain, same table. |
| `obj_client_id`/`obj_institution_id` params on `require_permission` | C-04 → all modules | C-01, C-02, C-08, fees, homework | All modules are callers of `require_permission`. They update their calls but the dependency is the same. No C-04 spec change to those modules' own requirements. |
| Platform owner bypass retained | C-04 → C-01 | C-01 platform routes | Platform owner can call all endpoints — no behavior change, just code organization. |
| RLS backstop | C-04 → C-04 | Self | RLS policies unchanged. C-04's Casbin is now a stronger layer; RLS remains as defense-in-depth. |

## Artifacts affected

| Artifact | Action |
|---|---|
| `docs/prd/c-04-authorization-consolidation.md` | Done (PRD source) |
| `docs/architecture/analysis-authorization-consolidation.md` | Done (analysis source) |
| `docs/prd/c-04-impact-classification.md` | This document |
| `openspec/changes/consolidate-c04-authorization-single-source/specs/authorization/spec.md` | MODIFIED delta (D7, D19, D26, D27 — ABAC wiring + scope) |
| `openspec/changes/consolidate-c04-authorization-single-source/specs/tenant-institution/spec.md` | MODIFIED delta (D14 — remove policies.py) |
| `openspec/changes/consolidate-c04-authorization-single-source/specs/identity-user-management/spec.md` | MODIFIED delta (route changes for ABAC) |
| `openspec/changes/consolidate-c04-authorization-single-source/design.md` | NEW — design doc |
| `openspec/changes/consolidate-c04-authorization-single-source/tasks.md` | NEW — task list |
| `openspec/changes/consolidate-c04-authorization-single-source/verify.md` | NEW — verification |
| `backend/kernel/authz/dependencies.py` | MODIFIED — `require_permission` signature change |
| `backend/kernel/authz/services/policy_loader.py` | MODIFIED — read scope from `role_permission.scope` |
| `backend/kernel/authz/manifest.py` | MODIFIED — register scope-aware policies |
| `backend/business/tenant_institution/policies.py` | DELETED |
| `backend/business/tenant_institution/casbin_model.conf` | DELETED |
| `backend/business/tenant_institution/manifest.py` | MODIFIED — remove `register_casbin_policies` |
| `backend/business/tenant_institution/routes/client_portal.py` | MODIFIED — pass object attributes |
| `backend/business/tenant_institution/routes/platform.py` | MODIFIED — pass object attributes |
| `backend/kernel/user/routes/users.py` | MODIFIED — pass object attributes |
| `backend/kernel/user/routes/profiles.py` | MODIFIED — pass object attributes |
| `backend/kernel/user/routes/identifiers.py` | MODIFIED — pass object attributes |
| `backend/kernel/user/routes/roles.py` | MODIFIED — pass object attributes |
| `backend/kernel/user/routes/lookups.py` | MODIFIED — pass object attributes |
| `backend/business/fees/routes/*.py` | MODIFIED — pass object attributes |
| `backend/business/homework/routes/*.py` | MODIFIED — pass object attributes |
| `backend/migrations/versions/016_c04_authorization_consolidation.py` | NEW — add scope column, missing permissions, migrate C-01 roles |
| `backend/tests/test_c04_authorization.py` | MODIFIED — test new ABAC behavior |
| `backend/tests/test_c01_tenant_institution.py` | MODIFIED — remove references to C-01 policies |
| `backend/tests/test_c02_user.py` | MODIFIED — test object attributes |
