# PRD — Authorization Consolidation (C-04 Single Source of Truth)

> **Capability:** C-04 Authorization (consolidation)
> **Capability layer / phase:** Kernel · Critical · Phase 1 (consolidation) + Phase 3 (ABAC wiring)
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-09
> **Decisional source of truth:** `docs/architecture/analysis-authorization-consolidation.md`, `docs/architecture/adr-c04-authorization-implementation.md` (D5, D7, D12, D19, D21, D26, D27, D28)
> **Companion docs:** `docs/prd/c-04-authorization.md` (original C-04 PRD), `docs/prd/c-01-tenant-institution.md` (D11 matrix), `openspec/changes/archive/2026-07-14-add-c04-authorization/specs/authorization/spec.md` (C-04 spec)
> **Scope note:** This is a **product** requirements document. It consolidates C-01's hardcoded authorization policies into C-04's DB-driven system, removes the parallel implementation, and wires up ABAC enforcement that was specified but never implemented. Decisions are referenced by ID (e.g., "per D7") rather than re-specified here.

---

## 1. Problem

The School ERP platform has **two parallel authorization systems** that feed into the same Casbin enforcer:

| System | Source | Roles covered | Status |
|---|---|---|---|
| **C-01** (`business/tenant_institution/policies.py`) | Hardcoded D11 matrix | `platform_owner`, `client_director`, `institution_admin`, `cross_institution`, regional/oversight roles | Temporary — implemented July 8 as stopgap until C-04 was built |
| **C-04** (`role_permission` DB table) | DB-driven, loaded at startup | `Admin`, `Principal`, `HOD`, `Teacher`, `Staff`, `Student`, `Parent` (C-02 roles) | Permanent — implemented July 14 |

C-04 was supposed to absorb C-01's policies (per C-01 spec: "C-04 encodes the D11 matrix as Casbin RBAC+ABAC policies"). It never did. C-01's hardcoded policies remain in production, creating three concrete problems:

1. **Action name mismatches:** C-01 uses `"transition"`, routes use `"transition_lifecycle"`. C-01 uses `"update_identity"`, routes use `"update"`. The CD role works through C-01's hardcoded policy with action `"transition"`, but the route checks action `"transition_lifecycle"` — they don't match, so the CD gets 403 on `POST /api/v1/institutions/{id}/transition`.

2. **Two sources of truth for permissions:** Adding a new permission requires editing Python code (C-01) OR a DB table (C-04). Developers don't know which to use. Inconsistencies accumulate.

3. **ABAC is broken:** The C-04 spec (D7, D19) requires `require_permission` to accept object attributes (`client_id`, `institution_id`) from the calling endpoint. The implementation doesn't accept these parameters — it builds the object from `ctx`, making the ABAC scope check always pass (sub.client_id == obj.client_id because both come from the same context). RLS is the only real tenant isolation backstop.

**Goal:** Eliminate the parallel system. All authorization policies come from C-04's `role_permission` DB table. `require_permission` accepts object attributes so ABAC scope enforcement works as designed. RLS remains as the defense-in-depth backstop.

---

## 2. Goals & Non-goals

### 2.1 In scope — this feature owns

| Concern | Per | Notes |
|---|---|---|
| **Migrate C-01 hardcoded policies to C-04 DB** | D11, D26 | All `client_director`, `institution_admin`, `cross_institution` policies move from `policies.py` to `role_permission` table. |
| **Add `scope` column to `role_permission`** | D26 | Scope values: `any` (no tenant check), `tenant` (own-client), `institution` (own-institution). Maps directly to Casbin policy. |
| **Add missing permissions to C-04 catalog** | D18 | `institution.archive`, `institution.list`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`, `institution_type.create`, `institution_type.update`, `user_profile.create`, `user.delete` — present in routes or C-01 but missing from C-04. |
| **Fix `require_permission` to accept object attributes** | D7, D19 | Add `obj_client_id` and `obj_institution_id` parameters. Endpoints pass resource attributes. Casbin ABAC scope check actually enforces. |
| **Remove C-01 `policies.py`** | D14 | Delete `business/tenant_institution/policies.py` and `business/tenant_institution/casbin_model.conf`. C-01 manifest's `register_casbin_policies` becomes empty/removed. |
| **Keep platform_owner code bypass** | D27, D28 | `require_permission` retains early-return for `is_platform_owner`. No DB entry for platform_owner. |
| **Update C-01 manifest** | D14 | Remove `register_casbin_policies` hook (or make it a no-op). C-04 is sole owner of policy registration. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Notes |
|---|---|---|
| ABAC Policy engine (full D21) | Phase 3 | Phase 3 adds `Policy` table and dynamic ABAC rules. Phase 1 wires up the static ABAC check via `require_permission` parameters. |
| Permission CRUD API | Phase 2 (D23) | Deferred. Phase 1 still uses seed data. |
| Runtime policy reload (`reload_policies()`) | Phase 2 (D11) | Deferred. App restart required to pick up policy changes. |
| Configurable roles UI | Phase 2 (D23) | Deferred. |
| Fine-grained scopes (OrgUnit, Grade, Class) | Phase 2 (D6) | Requires C-05 Academic Structure. |
| TemporaryRole table | Phase 2 (D21) | Deferred. |
| C-02 role migration (Admin, Teacher, etc.) | Already done | C-04 migration 004 seeded C-02 roles. No change needed. |
| RLS policies | Existing | RLS remains as defense-in-depth backstop. Not changed by this PRD. |

### 2.3 Explicit non-goals

- No new permission types beyond the 26 in the C-04 catalog + 9 missing ones
- No change to RLS policies
- No change to login/authentication flow (C-03)
- No change to the Casbin model file (`kernel/authz/casbin_model.conf`)

---

## 3. Users / Personas

| Persona | Role | Impact of this feature |
|---|---|---|
| **Platform Owner** | SaaS operator | No change. Code bypass retained. |
| **Client Director** | Client lead | Gains: `institution.transition_lifecycle` (was broken due to action name mismatch). ABAC now actually enforces cross-tenant block (currently only RLS). |
| **Institution Admin** | Institution lead | No change to behavior. Now sourced from DB instead of hardcoded code. |
| **Teacher/Student/Parent** | Institution users | No change. C-04 DB-driven already. |
| **Backend Developer** | Adds new endpoints | One source of truth for permissions. `require_permission(resource, action, obj_client_id, obj_institution_id)` is the standard pattern. |
| **DB Admin** | Manages roles/permissions | All role-permission mappings are in the DB. Edit `role_permission` table to grant/revoke. No code change needed. |

---

## 4. User Journey

### 4.1 CD transitions an institution (currently broken, fixed by this PRD)

**Before:**
1. CD authenticates → JWT carries `role=client_director`
2. Middleware looks up `role_assignment` → finds `client_director` role → sets `ctx.roles=["client_director"]` (with D12 fix)
3. CD calls `POST /api/v1/institutions/{id}/transition`
4. Route calls `require_permission("institution", "transition_lifecycle")`
5. Casbin checks: is there a policy `("client_director", "institution", "transition_lifecycle", ...)`? **No** — C-01 registered `("client_director", "institution", "transition", "tenant")` (wrong action name). C-04 DB has no entry for `client_director`.
6. Casbin returns false → **403 Forbidden** ❌

**After (D11 + ABAC wiring):**
1. CD authenticates → JWT carries `role=client_director`
2. Middleware looks up `role_assignment` → finds `client_director` role → sets `ctx.roles=["client_director"]`
3. CD calls `POST /api/v1/institutions/{id}/transition` (with institution_id in URL)
4. Route resolves the institution to get its `client_id` → calls `require_permission("institution", "transition_lifecycle", obj_client_id=institution.client_id, obj_institution_id=institution.id)`
5. Casbin checks: is there a policy `("client_director", "institution", "transition_lifecycle", "tenant")`? **Yes** — loaded from `role_permission` table.
6. Casbin checks scope: `sub.client_id (A) == obj.client_id (A)` ✅ → allowed
7. Action proceeds → **200 OK** ✅

### 4.2 Cross-tenant block (currently only RLS, now also Casbin)

**Before (D7/D19 spec gap):**
1. CD-A (client_id=A) calls `GET /api/v1/institutions/{id}` where institution belongs to client_id=B
2. Route calls `require_permission("institution", "read")` — no object attributes
3. Casbin checks: `sub.client_id (A) == obj.client_id (A)` (both from ctx) → ✅ passes
4. Route proceeds → service returns institution from client B (BUG: leaked data)
5. RLS at the service/repo layer blocks the actual data fetch — but the route handler still ran

**After (D7/D19 wired up):**
1. CD-A (client_id=A) calls `GET /api/v1/institutions/{id}`
2. Route resolves institution, gets its `client_id=B`
3. Route calls `require_permission("institution", "read", obj_client_id=B, obj_institution_id=inst.id)`
4. Casbin checks: `sub.client_id (A) == obj.client_id (B)` → ❌ fails
5. Casbin returns false → **403 Forbidden** ✅ (blocked BEFORE service runs)
6. No data leak at the route level. RLS still blocks at the DB level as backstop.

### 4.3 New permission granted to a role (DB-only, no code change)

**Before:**
1. Developer wants to add a new permission for CD
2. Edits `business/tenant_institution/policies.py` → adds `("client_director", "institution", "new_action", "tenant")`
3. Commits, pushes, waits for deploy
4. App restarts → policy loader reads updated policies from Python file

**After:**
1. DBA wants to add a new permission for CD
2. Runs SQL: `INSERT INTO permission (id, name, resource, action) VALUES (...)` + `INSERT INTO role_permission (id, role_id, permission_id) VALUES (...)`
3. App restarts → policy loader reads from DB
4. No code change, no deploy needed (only restart)

---

## 5. Acceptance Criteria

### 5.1 Consolidation

| ID | Criterion | Per |
|----|-----------|-----|
| AC-1 | `business/tenant_institution/policies.py` no longer exists | D14 |
| AC-2 | `business/tenant_institution/casbin_model.conf` no longer exists | D14 |
| AC-3 | All C-01 policies are in the `role_permission` table | D11, D26 |
| AC-4 | C-01 manifest's `register_casbin_policies` is removed or empty | D14 |
| AC-5 | App starts with the same enforcer policies as before (verified by running all existing auth tests) | D11 |

### 5.2 Permission catalog

| ID | Criterion | Per |
|----|-----------|-----|
| AC-6 | `role_permission` table has a `scope` column with values `any`/`tenant`/`institution` | D26 |
| AC-7 | All 9 missing permissions are in the `permission` table: `institution.archive`, `institution.list`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`, `institution_type.create`, `institution_type.update`, `user_profile.create`, `user.delete` | D18 |
| AC-8 | `client_director` has role-permission mappings for all C-01 policies (transition, archive, update_identity, org_unit.*, etc.) with `tenant` scope | D11 |
| AC-9 | `institution_admin` has role-permission mappings for all C-01 policies with `institution` scope | D11 |
| AC-10 | `cross_institution` has read-only mappings for client/institution/org_unit with `tenant` scope | D11 |

### 5.3 ABAC wiring

| ID | Criterion | Per |
|----|-----------|-----|
| AC-11 | `require_permission` accepts `obj_client_id` and `obj_institution_id` keyword parameters | D7, D19 |
| AC-12 | `require_permission` builds Casbin object with the passed object attributes, not from `ctx` | D7, D19 |
| AC-13 | CD-A (client_id=A) calling `require_permission("institution", "read", obj_client_id=B)` gets 403 | D7 |
| AC-14 | CD-A calling `require_permission("institution", "read", obj_client_id=A)` gets 200 | D7 |
| AC-15 | Cross-institution block works at the Casbin layer (not just RLS) | D7, D12 |

### 5.4 Platform owner

| ID | Criterion | Per |
|----|-----------|-----|
| AC-16 | `require_permission` retains early-return for `ctx.is_platform_owner` | D27, D28 |
| AC-17 | `platform_owner` has NO entry in `role_permission` table (bypass is in code) | D27 |
| AC-18 | Platform Owner can call any endpoint without 403 | D27, D28 |

### 5.5 Backward compatibility

| ID | Criterion | Per |
|----|-----------|-----|
| AC-19 | All existing C-04 tests pass (C-02 role permissions unchanged) | D26 |
| AC-20 | All existing C-01 tests pass (or are updated to reflect the consolidation) | D11 |
| AC-21 | Journey flow tests (01, 02, 09) complete end-to-end | D11 |
| AC-22 | RLS policies remain unchanged (defense in depth) | D5 |

---

## 6. Architecture

### 6.1 Current state (before)

```
┌─────────────────────────────────────────────────────────┐
│                    ROUTES                               │
│  require_permission("institution", "transition_lifecycle") │
│    ↓ no object attributes passed                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              require_permission                          │
│  sub = ctx (role, client_id, institution_id)             │
│  obj = ctx (name, client_id, institution_id)  ← WRONG    │
│  enforce(sub, obj, action) → always passes (same ctx)   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                Casbin Enforcer (single)                  │
│  C-01 policies: hardcoded in policies.py                │
│  C-04 policies: loaded from role_permission DB table    │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Target state (after)

```
┌─────────────────────────────────────────────────────────┐
│                    ROUTES                               │
│  # Lookup resource, get its client_id and institution_id  │
│  institution = repo.get(institution_id)                 │
│  require_permission("institution", "transition_lifecycle",│
│      obj_client_id=institution.client_id,                │
│      obj_institution_id=institution.id)                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              require_permission                          │
│  sub = ctx (role, client_id, institution_id)             │
│  obj = {"name": resource,                                │
│         "client_id": obj_client_id,        ← FROM URL    │
│         "institution_id": obj_institution_id}           │
│  enforce(sub, obj, action) → checks role + scope match  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                Casbin Enforcer (single)                  │
│  ALL policies from role_permission DB table (one source) │
│  No code-based policies (C-01 policies.py removed)      │
│  platform_owner bypass in require_permission (code)     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                RLS (defense in depth)                    │
│  app.current_client_id, app.current_institution_id,     │
│  app.current_user_id filter every tenant-scoped query    │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Schema change

```sql
-- Add scope column to role_permission
ALTER TABLE role_permission ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'institution';

-- Backfill scope for existing C-02 role_permissions
UPDATE role_permission SET scope = 'institution' WHERE scope IS NULL OR scope = '';

-- Add missing permissions
INSERT INTO permission (id, name, resource, action, description) VALUES
  (gen_random_uuid(), 'institution.archive', 'institution', 'archive', 'Archive an institution'),
  (gen_random_uuid(), 'institution.list', 'institution', 'list', 'List institutions'),
  (gen_random_uuid(), 'org_unit.archive', 'org_unit', 'archive', 'Archive an org unit'),
  (gen_random_uuid(), 'org_unit.reactivate', 'org_unit', 'reactivate', 'Reactivate an org unit'),
  (gen_random_uuid(), 'org_unit.reorder', 'org_unit', 'reorder', 'Reorder org units'),
  (gen_repository_uuid(), 'institution_type.create', 'institution_type', 'create', 'Create institution types'),
  (gen_random_uuid(), 'institution_type.update', 'institution_type', 'update', 'Update institution types'),
  (gen_random_uuid(), 'user_profile.create', 'user_profile', 'create', 'Create user profile'),
  (gen_random_uuid(), 'user.delete', 'user', 'delete', 'Delete a user')
ON CONFLICT (name) DO NOTHING;
```

### 6.4 Role migration

```sql
-- Migrate client_director permissions
INSERT INTO role_permission (id, role_id, permission_id, scope)
SELECT gen_random_uuid(), r.id, p.id, 'tenant'
FROM role r, permission p
WHERE r.name = 'client_director'
  AND p.name IN (
    'institution.create', 'institution.read', 'institution.update',
    'institution.transition_lifecycle', 'institution.archive', 'institution.list',
    'client.read', 'client.update',
    'org_unit.create', 'org_unit.read', 'org_unit.update', 'org_unit.move',
    'org_unit.archive', 'org_unit.reactivate', 'org_unit.reorder'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Migrate institution_admin permissions
INSERT INTO role_permission (id, role_id, permission_id, scope)
SELECT gen_random_uuid(), r.id, p.id, 'institution'
FROM role r, permission p
WHERE r.name = 'institution_admin'
  AND p.name IN (
    'institution.read', 'institution.update',
    'org_unit.create', 'org_unit.read', 'org_unit.update', 'org_unit.move',
    'org_unit.archive', 'org_unit.reactivate', 'org_unit.reorder'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Migrate cross_institution permissions
INSERT INTO role_permission (id, role_id, permission_id, scope)
SELECT gen_random_uuid(), r.id, p.id, 'tenant'
FROM role r, permission p
WHERE r.name = 'cross_institution'
  AND p.name IN ('client.read', 'institution.read', 'org_unit.read')
ON CONFLICT (role_id, permission_id) DO NOTHING;
```

---

## 7. Migration Strategy

This is a **big-bang migration** (per user decision):

1. **Single Alembic migration** that:
   - Adds `scope` column to `role_permission`
   - Inserts 9 missing permissions
   - Migrates C-01 roles (client_director, institution_admin, cross_institution) to `role_permission`
   - Backfills scope for existing C-02 role_permissions

2. **Code change in same change**:
   - Update `require_permission` signature: add `obj_client_id`, `obj_institution_id` params
   - Update `policy_loader.py` to read scope from `role_permission.scope`
   - Update all C-01 and C-02 routes to pass object attributes
   - Delete `business/tenant_institution/policies.py`
   - Delete `business/tenant_institution/casbin_model.conf`
   - Remove `register_casbin_policies` from C-01 manifest

3. **Test** all existing tests pass + new ABAC tests pass

4. **Deploy** — requires app restart (no runtime reload in Phase 1 per D11)

**Risk:** If the migration has a bug, the app starts with incorrect policies. Mitigation: test the migration in a staging environment first.

---

## 8. Out-of-Scope (Explicit)

- No change to RLS policies
- No change to Casbin model file (already ABAC-ready)
- No change to login/auth flow
- No new permission types beyond the 35 total (26 existing + 9 new)
- No runtime policy reload (D11 deferred)
- No configurable roles UI (D23 deferred)
- No TemporaryRole table (D21 deferred)
- No fine-grained scopes like OrgUnit/Grade/Class (D6 deferred)
- No `Policy` table for dynamic ABAC (D21 deferred to Phase 3)

---

## 9. Open Questions

| # | Question | Impact |
|---|---|---|
| 1 | Should `obj_client_id`/`obj_institution_id` be required or optional parameters on `require_permission`? | API ergonomics. Optional with sensible default (use `ctx.client_id` for backward compat) is safer. |
| 2 | For list endpoints where no specific resource ID is available, what object attributes are passed? | D19 says "list endpoints may pass only the client scope (no institution_id)". The route passes `ctx.client_id` as `obj_client_id` and empty string for `obj_institution_id`. |
| 3 | Should the `cross_institution` role have a separate name or be a flag on existing roles? | If separate, it's a new role in the `role` table. If flag, it's an attribute. Currently C-01 has it as a separate role. |
| 4 | What happens if the `role` table doesn't have `client_director` or `institution_admin` rows? | The migration should INSERT them if missing. Or assume they exist (they were seeded by C-01 migration 011). |

---

## 10. Consequences

### Positive

- One source of truth for permissions (C-04 DB table)
- ABAC actually enforces cross-tenant blocks at the Casbin layer
- No code changes needed to grant/revoke permissions
- Eliminates the action name mismatch bug (C-01's `"transition"` vs C-04's `"transition_lifecycle"`)
- All C-01 roles get proper DB-driven policies

### Negative

- Every route must be updated to pass object attributes to `require_permission` (~15-20 routes)
- Backward compatibility: routes that don't pass object attributes will get permissive ABAC (object attrs default to ctx → always passes)
- Big-bang migration is risky — if it fails, all authorization breaks
- Requires careful testing of every role × resource × scope combination
