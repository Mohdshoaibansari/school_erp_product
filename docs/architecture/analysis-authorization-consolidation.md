# Authorization Consolidation Analysis

> **Date:** 2026-08-09
> **Objective:** Eliminate parallel authorization systems. All authZ should come from C-04 kernel module.
> **Status:** Analysis — pending review

---

## 1. Current State — Two Parallel Systems

### System A: C-01 Hardcoded Policies (`business/tenant_institution/policies.py`)

C-01 was implemented on July 8 as a stopgap until C-04 was built. It hardcoded the D11 permission matrix directly into Casbin policies at startup.

**Source:** `backend/business/tenant_institution/policies.py` — `PERMISSION_POLICIES` list + `ROLE_HIERARCHY`

**Roles covered:** `platform_owner`, `client_director`, `institution_admin`, `cross_institution`, `regional_manager`, `group_academic_head`, `finance_controller`

**Policies registered via:** C-01 manifest `register_casbin_policies(enforcer)` hook → `register_policies(enforcer)` in `policies.py`

### System B: C-04 DB-Driven Policies (`kernel/authz/services/policy_loader.py`)

C-04 was implemented on July 14. It loads permissions from the `role_permission` DB table at startup and pushes them into the same Casbin enforcer.

**Source:** `role_permission` table (seeded by migration 004)

**Roles covered:** `Admin`, `Principal`, `HOD`, `Teacher`, `Staff`, `Student`, `Parent` (C-02 roles only)

**Policies registered via:** C-04 manifest `register_casbin_policies(enforcer)` hook → `register_policies_from_map(enforcer)` in `policy_loader.py`

### Both feed the SAME enforcer

At startup, the app factory iterates manifests in dependency order:
1. C-01 `register_casbin_policies(enforcer)` → pushes hardcoded D11 matrix
2. C-04 `register_casbin_policies(enforcer)` → pushes DB-loaded C-02 role permissions

Both sets of policies coexist in one Casbin enforcer. A `client_director` role gets policies from C-01. An `Admin` role gets policies from C-04.

---

## 2. ABAC Status — Deferred (D21)

The C-04 PRD explicitly states:

> "**No ABAC policy engine** — the Casbin model supports ABAC but Phase 1 does not define ABAC policies. Ownership checks are handled at the app level, not in Casbin (D12)."
>
> "`Policy` ABAC rules | Phase 3 | Deferred. The Casbin model is ABAC-ready but Phase 1 uses RBAC only for permission resolution (D21)."

The Casbin model (`kernel/authz/casbin_model.conf`) has ABAC matchers:
```
m = g(r.sub.role, p.sub) && (p.obj == "*" || p.obj == r.obj.name) 
    && (p.act == "*" || p.act == r.act) 
    && (p.scope == "any" || (p.scope == "tenant" && r.sub.client_id == r.obj.client_id) 
    || (p.scope == "institution" && r.sub.client_id == r.obj.client_id 
        && r.sub.institution_id == r.obj.institution_id))
```

But the current `require_permission` implementation builds both subject AND object from the same `TenantContext`, making the ABAC scope check always pass (sub.client_id == obj.client_id because both come from ctx). RLS is the only real tenant isolation backstop.

**Conclusion:** ABAC is correctly deferred. The Casbin model is ABAC-ready for Phase 3. Phase 1 relies on RLS for tenant isolation. This analysis focuses on RBAC consolidation only.

---

## 3. Action Name Mismatches

C-01 and C-04 use different action names for the same operations:

| Resource | C-01 action | C-04 action | Route uses | Match? |
|---|---|---|---|---|
| `institution` | `transition` | `transition_lifecycle` | `transition_lifecycle` | ❌ C-01 wrong |
| `institution` | `update_identity` | `update` | `update` | ❌ C-01 extra |
| `institution` | `archive` | *(not in C-04)* | `transition_lifecycle` | ❌ C-01 extra |
| `institution` | `read` | `read` | `read` | ✅ |
| `institution` | `create` | `create` | `create` | ✅ |
| `client` | `update_identity` | `update` | `update` | ❌ C-01 extra |
| `client` | `read` | `read` | `read` | ✅ |
| `org_unit` | `archive` | *(not in C-04)* | *(not used)* | ⚠️ C-01 only |
| `org_unit` | `reactivate` | *(not in C-04)* | *(not used)* | ⚠️ C-01 only |
| `org_unit` | `update_identity` | `update` | `update` | ❌ C-01 extra |
| `org_unit` | `reorder` | *(not in C-04)* | *(not used)* | ⚠️ C-01 only |

**Root cause:** C-01 was designed independently with its own action naming convention. C-04 used a different convention (`resource.action_lifecycle`). Routes use C-04 names.

---

## 4. Permission Gaps

### 4.1 Actions in C-01 but NOT in C-04 permission catalog

These C-01 policies have no corresponding row in the C-04 `permission` table:

| C-01 policy | C-04 permission | Status |
|---|---|---|
| `institution.update_identity` | `institution.update` | Name mismatch — should map |
| `institution.archive` | *(none)* | Missing from C-04 |
| `institution.transition` | `institution.transition_lifecycle` | Name mismatch — should map |
| `client.update_identity` | `client.update` | Name mismatch — should map |
| `org_unit.update_identity` | `org_unit.update` | Name mismatch — should map |
| `org_unit.archive` | *(none)* | Missing from C-04 |
| `org_unit.reactivate` | *(none)* | Missing from C-04 |
| `org_unit.reorder` | *(none)* | Missing from C-04 |

### 4.2 Actions in routes but NOT in C-04 permission catalog

| Route action | C-04 permission | Status |
|---|---|---|
| `institution_type.create` | *(none)* | Missing from C-04 spec |
| `institution_type.update` | *(none)* | Missing from C-04 spec |
| `user_profile.create` | *(none)* | Missing from C-04 spec (routes use it) |
| `user.delete` | *(none)* | Missing from C-04 spec (routes use it) |

### 4.3 Roles in C-01 but NOT in C-04 role_permission mapping

| C-01 role | In C-04 `role_permission`? | Source of permissions |
|---|---|---|
| `platform_owner` | ❌ (by design — D27) | C-01 wildcard `*.*` at `any` scope |
| `client_director` | ❌ | C-01 hardcoded policies only |
| `institution_admin` | ❌ | C-01 hardcoded policies only |
| `cross_institution` | ❌ | C-01 hardcoded policies only |
| `regional_manager` | ❌ | C-01 role hierarchy only |
| `group_academic_head` | ❌ | C-01 role hierarchy only |
| `finance_controller` | ❌ | C-01 role hierarchy only |

### 4.4 Roles in C-04 but NOT in C-01

| C-04 role | In C-01? | Source of permissions |
|---|---|---|
| `Admin` | ❌ | C-04 `role_permission` only |
| `Principal` | ❌ | C-04 `role_permission` only |
| `HOD` | ❌ | C-04 `role_permission` only |
| `Teacher` | ❌ | C-04 `role_permission` only |
| `Staff` | ❌ | C-04 `role_permission` only |
| `Student` | ❌ | C-04 `role_permission` only |
| `Parent` | ❌ | C-04 `role_permission` only |

---

## 5. `require_permission` Signature Gap

### Spec says (C-04 spec line 94):
```python
require_permission(resource, action, client_id, institution_id, owner_id)
```
Object attributes (`client_id`, `institution_id`) passed explicitly by the calling endpoint (D7, D19).

### Implementation:
```python
require_permission(resource, action, *, owner_id=None)
```
No `client_id` or `institution_id` parameters. Object built from `ctx` (same as subject).

### Impact:
- ABAC scope checks always pass (sub.client_id == obj.client_id from same ctx)
- Phase 1 RBAC works (role check is independent of object attributes)
- RLS is the only tenant isolation backstop

### Decision (D21):
ABAC is deferred to Phase 3. The `require_permission` signature gap is acceptable for Phase 1 RBAC. The parameters should be added when ABAC is implemented.

---

## 6. Dead Files

| File | Status |
|---|---|
| `business/tenant_institution/casbin_model.conf` | Dead copy — identical to `kernel/authz/casbin_model.conf`. Nothing references it. Can be deleted. |
| `business/tenant_institution/policies.py` `build_enforcer()` | Dead function — not called anywhere. Can be removed. |

---

## 7. Consolidation Plan

### Goal
All authorization policies come from C-04's `role_permission` DB table. C-01's `policies.py` is removed. One system, one source of truth.

### Step 1: Add missing permissions to C-04 `permission` table

Add these rows (via new migration):

| name | resource | action |
|---|---|---|
| `institution.list` | institution | list |
| `institution.archive` | institution | archive |
| `org_unit.archive` | org_unit | archive |
| `org_unit.reactivate` | org_unit | reactivate |
| `org_unit.reorder` | org_unit | reorder |
| `institution_type.create` | institution_type | create |
| `institution_type.update` | institution_type | update |
| `user_profile.create` | user_profile | create |
| `user.delete` | user | delete |

### Step 2: Map C-01 roles to C-04 `role_permission` table

Add role-permission mappings for `client_director`, `institution_admin`, `cross_institution`:

**client_director** (tenant scope):
- `institution.create`, `institution.read`, `institution.update`, `institution.transition_lifecycle`, `institution.archive`
- `client.read`, `client.update`
- `org_unit.create`, `org_unit.read`, `org_unit.update`, `org_unit.move`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`

**institution_admin** (institution scope):
- `institution.read`, `institution.update`
- `org_unit.create`, `org_unit.read`, `org_unit.update`, `org_unit.move`, `org_unit.archive`, `org_unit.reactivate`, `org_unit.reorder`

**cross_institution** (tenant scope, read-only):
- `client.read`, `institution.read`, `org_unit.read`

### Step 3: Update `policy_loader.py` to register scope

C-04's `register_policies_from_map` currently registers all policies with `"institution"` scope. C-01 uses `"tenant"` and `"any"` scopes. The loader needs to support scope per role-permission mapping.

Options:
- **A:** Add a `scope` column to `role_permission` table
- **B:** Derive scope from role name (e.g., `client_director` → `tenant`, `platform_owner` → `any`)
- **C:** Add a `scope` column to the `permission` table (scope is per-permission, not per-role)

Recommended: **A** — `scope` on `role_permission` (most flexible, matches Casbin model).

### Step 4: Update action names in routes

Align all routes to use C-04 action names:
- `institution.transition` → `institution.transition_lifecycle` (already correct in routes)
- `institution.update_identity` → `institution.update` (already correct in routes)
- `client.update_identity` → `client.update` (already correct in routes)
- `org_unit.update_identity` → `org_unit.update` (already correct in routes)

**No route changes needed** — routes already use C-04 names. C-01 policies need to be removed (they use different names).

### Step 5: Handle `platform_owner` wildcard

`platform_owner` uses `*.*` at `any` scope in C-01. Options:
- **A:** Keep as a special case in `require_permission` (check `is_platform_owner` before Casbin)
- **B:** Add `platform_owner` to `role_permission` with `*.*` at `any` scope
- **C:** Keep C-01's `platform_owner` policy only (don't migrate to DB)

Recommended: **A** — `require_permission` already has a platform_owner bypass. Keep it explicit in code.

### Step 6: Remove C-01 `policies.py`

After all C-01 policies are migrated to C-04 `role_permission`:
- Delete `business/tenant_institution/policies.py`
- Delete `business/tenant_institution/casbin_model.conf`
- Remove `register_casbin_policies` from C-01 manifest
- Remove role hierarchy (handled by Casbin `g` policies in DB or by platform_owner bypass)

### Step 7: Update C-01 manifest

C-01 manifest's `register_casbin_policies` hook becomes empty (or removed). C-04 is the sole owner of policy registration.

---

## 8. Migration Strategy

### Phase 1 (immediate — unblock current testing)
1. Add missing permissions to DB (SQL insert)
2. Add `client_director` + `institution_admin` role-permission mappings to DB
3. Restart app — policies load from DB
4. C-01 hardcoded policies still active (harmless duplicate with same effect)

### Phase 2 (consolidation)
1. Add `scope` column to `role_permission` table
2. Update `policy_loader.py` to read scope from DB
3. Migrate all C-01 roles to `role_permission` with correct scopes
4. Remove C-01 `policies.py` and `casbin_model.conf`
5. Remove C-01 `register_casbin_policies` hook

### Phase 3 (ABAC — future)
1. Add `client_id`/`institution_id` parameters to `require_permission`
2. Routes pass object attributes explicitly
3. ABAC scope checks enforced in Casbin (not just RLS)

---

## 9. Risks and Open Questions

| # | Question | Impact |
|---|---|---|
| 1 | Should `scope` be on `role_permission` or `permission` table? | Schema design |
| 2 | Should `platform_owner` wildcard be in DB or code? | Maintainability |
| 3 | Should C-01 role hierarchy (`g` policies) be in DB or code? | Role inheritance |
| 4 | What happens to C-01's `cross_institution` read-only scope? | Needs scope support |
| 5 | Are there other modules (fees, homework) that register Casbin policies? | Scope of change |

**Answer:** No. Fees and homework manifests have empty `register_casbin_policies` hooks. Only C-01 and C-04 register policies.

---

## 10. Recommendation

**Immediate fix (unblock testing):** Run SQL to add `client_director` permissions to `role_permission` table. This makes the CD role work through C-04's system. C-01's hardcoded policies become harmless duplicates.

**Consolidation (next sprint):** Add `scope` column to `role_permission`, migrate all C-01 roles, remove `policies.py`. One system, one source of truth.

**ABAC (future phase):** Add object attributes to `require_permission`, enforce scope in Casbin instead of RLS.
