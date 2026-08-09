# Design — C-04 Authorization Consolidation (Single Source of Truth)

> **Change:** `consolidate-c04-authorization-single-source`
> **Traceability.** Design decisions trace to PRD AC IDs (AC-1..AC-22) and proposal items.
> **Status:** Design phase — ready for tasks breakdown.

---

## 1. Architecture Diagram — Before / After

### 1.1 Before (Two Parallel Systems)

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROUTES                                  │
│                                                                 │
│  C-01 routes (client_portal.py, platform.py)                    │
│    require_permission("institution", "transition_lifecycle")    │
│    ✗ No obj_client_id / obj_institution_id passed               │
│                                                                 │
│  C-02 routes (users.py, profiles.py, roles.py, identifiers.py) │
│    require_permission("user", "read")                           │
│    ✗ No obj_client_id / obj_institution_id passed               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   require_permission()                          │
│                                                                 │
│  sub = ctx  (role, client_id, institution_id)                   │
│  obj = ctx  (name, client_id, institution_id)  ← ALWAYS SAME   │
│  enforce(sub, obj, action) → always passes (sub==obj)           │
│  ✗ ABAC broken — cross-tenant check never fires                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Casbin Enforcer (one instance)                  │
│                                                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │ C-01 policies.py    │  │ C-04 role_permission DB table    │  │
│  │ Hardcoded D11 matrix│  │ Loaded at startup by             │  │
│  │ platform_owner *.*  │  │ policy_loader.py                 │  │
│  │ client_director ... │  │ Admin, Principal, HOD, Teacher,  │  │
│  │ institution_admin ..│  │ Staff, Student, Parent           │  │
│  │ cross_institution . │  │                                  │  │
│  │ ✗ Wrong action names│  │ ✗ No C-01 roles                  │  │
│  │   "transition" vs   │  │ ✗ No scope column                │  │
│  │   "transition_life..│  │ ✗ Hardcoded "institution" scope  │  │
│  └─────────────────────┘  └──────────────────────────────────┘  │
│          TWO sources of truth                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RLS (defense-in-depth)                       │
│  app.current_client_id, app.current_institution_id              │
│  Only backstop — Casbin already passed                          │
└─────────────────────────────────────────────────────────────────┘
```

**Problems visible in this diagram:**
1. Two policy sources (C-01 code + C-04 DB) feed the same enforcer
2. `require_permission` builds obj from ctx → sub.client_id == obj.client_id always → ABAC never blocks
3. C-01 uses action `"transition"`, routes use `"transition_lifecycle"` → CD gets 403

### 1.2 After (Single Source of Truth)

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROUTES                                  │
│                                                                 │
│  C-01 routes (client_portal.py, platform.py)                    │
│    # Pre-fetch resource → get its client_id, institution_id     │
│    institution = svc.get_institution(ctx, institution_id)       │
│    require_permission("institution", "transition_lifecycle",    │
│        obj_client_id=institution.client_id,                     │
│        obj_institution_id=institution.id)                       │
│                                                                 │
│  C-02 routes (users.py, profiles.py, roles.py, identifiers.py) │
│    user = svc.get_user(ctx, user_id)                            │
│    require_permission("user", "read",                           │
│        obj_client_id=user.client_id,                            │
│        obj_institution_id=user.institution_id)                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   require_permission()                          │
│                                                                 │
│  sub = ctx  (role, client_id, institution_id)                   │
│  obj = {name, client_id, institution_id}  ← FROM PARAMETERS    │
│    obj_client_id defaults to ctx.client_id if not passed        │
│    obj_institution_id defaults to ctx.institution_id            │
│  enforce(sub, obj, action)                                      │
│  ✓ ABAC actually enforces cross-tenant / cross-institution      │
│                                                                 │
│  platform_owner bypass (code) — early return, no Casbin check   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Casbin Enforcer (one instance)                  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ C-04 role_permission DB table — SOLE SOURCE OF TRUTH      │ │
│  │                                                            │ │
│  │ Loaded at startup by policy_loader.py (reads scope column) │ │
│  │                                                            │ │
│  │ C-01 roles now in DB:                                      │ │
│  │   client_director  → 15 permissions, scope=tenant          │ │
│  │   institution_admin → 9 permissions, scope=institution     │ │
│  │   cross_institution → 3 permissions, scope=tenant          │ │
│  │                                                            │ │
│  │ C-02 roles (unchanged):                                    │ │
│  │   Admin, Principal, HOD, Teacher, Staff, Student, Parent   │ │
│  │   scope=institution (default)                              │ │
│  │                                                            │ │
│  │ Policy tuple: (role, resource, action, scope)              │ │
│  │   scope from role_permission.scope column                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  C-01 policies.py  → DELETED                                    │
│  C-01 casbin_model.conf → DELETED                               │
│  C-01 register_casbin_policies → REMOVED                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RLS (defense-in-depth)                       │
│  app.current_client_id, app.current_institution_id              │
│  Still active — unchanged, catches any Casbin bypass            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Migration SQL — Alembic Migration `016_c04_authorization_consolidation.py`

One big-bang Alembic migration handles all schema + data changes.

### 2.1 Add `scope` column to `role_permission`

```sql
ALTER TABLE role_permission
ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'institution';
```

**Rationale:** Default `'institution'` is correct for all existing C-02 role_permissions (Admin, Principal, HOD, Teacher, Staff, Student, Parent all operate at institution scope). No backfill UPDATE needed — the DEFAULT handles it.

### 2.2 Insert 9 missing permissions

```sql
INSERT INTO permission (id, name, description, resource, action)
VALUES
  (gen_random_uuid(), 'institution.archive',   'Archive an institution',     'institution',      'archive'),
  (gen_random_uuid(), 'institution.list',      'List institutions',          'institution',      'list'),
  (gen_random_uuid(), 'org_unit.archive',      'Archive an org unit',        'org_unit',          'archive'),
  (gen_random_uuid(), 'org_unit.reactivate',   'Reactivate an org unit',     'org_unit',          'reactivate'),
  (gen_random_uuid(), 'org_unit.reorder',      'Reorder org units',          'org_unit',          'reorder'),
  (gen_random_uuid(), 'institution_type.create','Create institution types',  'institution_type',  'create'),
  (gen_random_uuid(), 'institution_type.update','Update institution types',  'institution_type',  'update'),
  (gen_random_uuid(), 'user_profile.create',   'Create user profile',        'user_profile',      'create'),
  (gen_random_uuid(), 'user.delete',           'Delete a user',              'user',              'delete')
ON CONFLICT (name) DO NOTHING;
```

**Post-condition:** `permission` table has 35 rows (26 existing + 9 new).

### 2.3 Migrate C-01 roles to `role_permission`

```sql
-- client_director: 15 permissions, scope=tenant
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

-- institution_admin: 9 permissions, scope=institution
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

-- cross_institution: 3 permissions, scope=tenant
INSERT INTO role_permission (id, role_id, permission_id, scope)
SELECT gen_random_uuid(), r.id, p.id, 'tenant'
FROM role r, permission p
WHERE r.name = 'cross_institution'
  AND p.name IN ('client.read', 'institution.read', 'org_unit.read')
ON CONFLICT (role_id, permission_id) DO NOTHING;
```

### 2.4 Downgrade

```sql
-- Remove scope column
ALTER TABLE role_permission DROP COLUMN IF EXISTS scope;

-- Remove C-01 role-permission mappings
DELETE FROM role_permission
WHERE role_id IN (SELECT id FROM role WHERE name IN ('client_director', 'institution_admin', 'cross_institution'));

-- Remove 9 missing permissions
DELETE FROM permission WHERE name IN (
  'institution.archive', 'institution.list',
  'org_unit.archive', 'org_unit.reactivate', 'org_unit.reorder',
  'institution_type.create', 'institution_type.update',
  'user_profile.create', 'user.delete'
);
```

### 2.5 Post-migration verification query

```sql
-- Verify total permissions = 35
SELECT COUNT(*) FROM permission;  -- expect 35

-- Verify C-01 roles have correct scopes
SELECT r.name AS role, COUNT(*) AS perm_count,
       MIN(rp.scope) AS scope
FROM role_permission rp
JOIN role r ON r.id = rp.role_id
WHERE r.name IN ('client_director', 'institution_admin', 'cross_institution')
GROUP BY r.name;
-- expect:
--   client_director   | 15 | tenant
--   institution_admin |  9 | institution
--   cross_institution |  3 | tenant

-- Verify existing C-02 roles still have institution scope
SELECT r.name AS role, COUNT(*) AS perm_count
FROM role_permission rp
JOIN role r ON r.id = rp.role_id
WHERE r.name IN ('Admin','Principal','HOD','Teacher','Staff','Student','Parent')
GROUP BY r.name;
-- expect same counts as before, all scope=institution (from DEFAULT)
```

---

## 3. `require_permission` Signature Change

### 3.1 Current signature

```python
def require_permission(
    resource: str,
    action: str,
    *,
    owner_id: uuid.UUID | None = None,
):
```

### 3.2 New signature

```python
def require_permission(
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
):
```

### 3.3 Inner `_enforce` changes

```python
def _enforce(
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
):
    # ... existing enforcer check + platform_owner bypass (unchanged) ...

    roles = ctx.roles or []
    if ctx.is_platform_owner or "platform_owner" in roles:
        return  # unchanged

    if not roles:
        raise HTTPException(status_code=403, ...)

    sub = {
        "role": roles[0],
        "client_id": str(ctx.client_id) if ctx.client_id else "",
        "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
    }

    # NEW: Build object from parameters, fall back to ctx
    obj = {
        "name": resource,
        "client_id": str(obj_client_id) if obj_client_id
                     else (str(ctx.client_id) if ctx.client_id else ""),
        "institution_id": str(obj_institution_id) if obj_institution_id
                           else (str(ctx.institution_id) if ctx.institution_id else ""),
    }

    # Step 1: Casbin (unchanged call)
    if not enforcer.enforce(sub, obj, action):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Step 2: Ownership check (unchanged)
    if owner_id is not None and ctx.user_id and str(ctx.user_id) != str(owner_id):
        admin_obj = {"name": resource, "client_id": "", "institution_id": ""}
        if not enforcer.enforce(sub, admin_obj, action):
            raise HTTPException(status_code=403, detail="You can only access your own resource")
```

### 3.4 Backward compatibility

- Existing callers `require_permission("user", "read")` → `obj_client_id=None`, `obj_institution_id=None` → defaults to ctx values → **same behavior as before**.
- New callers pass explicit resource attributes → ABAC actually enforces.

---

## 4. `policy_loader.py` Changes

### 4.1 Current behavior (hardcoded `"institution"` scope)

```python
def register_policies_from_map(enforcer):
    for role_name, permissions in _permission_map.items():
        enforcer.add_role_for_user(role_name, role_name)
        for resource, action in permissions:
            enforcer.add_policy(role_name, resource, action, "institution")  # ← HARDCODED
```

### 4.2 New behavior (scope from DB)

```python
def load_permission_map() -> None:
    """Read role_permission rows including scope column."""
    global _permission_map
    session = _get_session()
    try:
        rows = session.execute(text("""
            SELECT r.name AS role_name, p.resource, p.action, rp.scope
            FROM role_permission rp
            JOIN role r ON r.id = rp.role_id
            JOIN permission p ON p.id = rp.permission_id
            ORDER BY r.name, p.resource, p.action
        """)).fetchall()

        _permission_map.clear()
        for role_name, resource, action, scope in rows:
            _permission_map.setdefault(role_name, []).append((resource, action, scope))

        logger.info(
            "C-04 policy loader: loaded %d role-permission mappings across %d roles",
            len(rows), len(_permission_map),
        )
    finally:
        session.close()


def register_policies_from_map(enforcer: Any) -> None:
    """Push policies into enforcer — scope from DB, not hardcoded."""
    for role_name, permissions in _permission_map.items():
        enforcer.add_role_for_user(role_name, role_name)
        for resource, action, scope in permissions:
            enforcer.add_policy(role_name, resource, action, scope)  # ← FROM DB

    logger.info(
        "C-04 policy loader: registered %d role mappings into enforcer",
        len(_permission_map),
    )


def get_permission_map() -> dict[str, list[tuple[str, str, str]]]:
    """Return current in-memory map (test helper). Signature changes: 3-tuple."""
    return dict(_permission_map)
```

### 4.3 Key change summary

| Aspect | Before | After |
|---|---|---|
| `load_permission_map` SELECT | 3 columns (role_name, resource, action) | 4 columns (+ scope) |
| `_permission_map` value type | `list[tuple[str, str]]` | `list[tuple[str, str, str]]` |
| `register_policies_from_map` | `add_policy(role, res, act, "institution")` | `add_policy(role, res, act, scope)` |
| `get_permission_map` return type | `dict[str, list[tuple[str, str]]]` | `dict[str, list[tuple[str, str, str]]]` |

---

## 5. Route Change Patterns

### 5.1 Pattern: Single-resource endpoints (GET/PUT/DELETE by ID)

Pre-fetch the resource, pass its attributes.

```python
# BEFORE
@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: uuid.UUID,
    _authz: None = Depends(require_permission("institution", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: ...,
):
    result = svc.get_institution(ctx, institution_id)
    ...

# AFTER
@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: ...,
):
    # Pre-fetch for ABAC object attributes
    result = svc.get_institution(ctx, institution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Institution not found")
    _authz: None = Depends(require_permission(
        "institution", "read",
        obj_client_id=result.client_id,
        obj_institution_id=result.id,
    ))
    return result
```

**Wait — this pattern doesn't work with FastAPI's Depends.** FastAPI resolves `Depends` at function signature time, not inside the function body. The correct pattern is:

```python
# AFTER (correct pattern)
@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: uuid.UUID,
    _authz: None = Depends(require_permission("institution", "read")),
    # ↑ Still uses Depends — but now we need a different approach
):
```

### 5.2 Correct pattern: Two-phase enforcement

Since FastAPI resolves `Depends` before the function body runs, we cannot pass resource-derived attributes to `require_permission` as a `Depends` parameter. Instead, use one of two approaches:

**Approach A: Inline enforcement (recommended for single-resource endpoints)**

```python
@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: ... = Depends(get_tenant_institution_service),
    enforcer: ... = Depends(get_enforcer),
):
    result = svc.get_institution(ctx, institution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Inline ABAC check with resource-derived attributes
    from kernel.authz.dependencies import check_permission
    check_permission(ctx, enforcer, "institution", "read",
                     obj_client_id=result.client_id,
                     obj_institution_id=result.id)
    return result
```

**Approach B: Use a factory that accepts a resolver function**

```python
def require_permission_with_resolver(
    resource: str,
    action: str,
    resolver: Callable[[TenantContext, Any], tuple[uuid.UUID | None, uuid.UUID | None]],
):
    """Factory that pre-fetches resource for ABAC."""
    def _enforce(
        ctx: TenantContext = Depends(get_tenant_context),
        enforcer: ... = Depends(get_enforcer),
    ):
        obj_client_id, obj_institution_id = resolver(ctx, enforcer)
        # ... enforce ...
    return _enforce
```

**Approach C (chosen for this design): Default-to-ctx + explicit override where needed**

The simplest approach: `require_permission` gains `obj_client_id` / `obj_institution_id` keyword params that default to `None` (→ fall back to ctx). For **list endpoints** and **create endpoints**, callers pass ctx values explicitly or omit them (same behavior). For **single-resource endpoints**, callers pass the resource's attributes.

But the FastAPI `Depends` issue remains. The solution: **convert single-resource endpoints to use a two-step pattern** where:
1. `Depends(require_permission(...))` runs first with ctx defaults (pre-check)
2. A second inline check runs after resource fetch with actual attributes

**Actually, the simplest correct solution:** For single-resource endpoints where ABAC matters, remove the `Depends` and call the check inline after fetching the resource. The `require_permission` function becomes a reusable callable.

### 5.3 Final chosen approach: Extract `check_permission` callable

```python
# kernel/authz/dependencies.py — NEW public function

def check_permission(
    ctx: TenantContext,
    enforcer: Any,
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> None:
    """Inline permission check — call after fetching resource.

    Same logic as require_permission but callable directly.
    Raises HTTPException(403) on denial.
    """
    roles = ctx.roles or []

    if ctx.is_platform_owner or "platform_owner" in roles:
        return

    if not roles:
        raise HTTPException(status_code=403, detail="Permission denied — no roles assigned")

    sub = {
        "role": roles[0],
        "client_id": str(ctx.client_id) if ctx.client_id else "",
        "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
    }
    obj = {
        "name": resource,
        "client_id": str(obj_client_id) if obj_client_id
                     else (str(ctx.client_id) if ctx.client_id else ""),
        "institution_id": str(obj_institution_id) if obj_institution_id
                           else (str(ctx.institution_id) if ctx.institution_id else ""),
    }

    if not enforcer.enforce(sub, obj, action):
        raise HTTPException(status_code=403, detail="Permission denied")

    if owner_id is not None and ctx.user_id and str(ctx.user_id) != str(owner_id):
        admin_obj = {"name": resource, "client_id": "", "institution_id": ""}
        if not enforcer.enforce(sub, admin_obj, action):
            raise HTTPException(status_code=403, detail="You can only access your own resource")
```

### 5.4 Route change patterns — summary table

| Endpoint pattern | Authz approach | obj_client_id | obj_institution_id |
|---|---|---|---|
| `POST /institutions` (create) | `Depends(require_permission(...))` | `ctx.client_id` (optimistic) | `ctx.institution_id` (optimistic) |
| `GET /institutions` (list) | `Depends(require_permission(...))` | `ctx.client_id` | *(omitted)* |
| `GET /institutions/{id}` (get) | Inline `check_permission` after fetch | `inst.client_id` | `inst.id` |
| `PATCH /institutions/{id}` (update) | Inline `check_permission` after fetch | `inst.client_id` | `inst.id` |
| `POST /institutions/{id}/transition` | Inline `check_permission` after fetch | `inst.client_id` | `inst.id` |
| `POST /institutions/{id}/archive` | Inline `check_permission` after fetch | `inst.client_id` | `inst.id` |
| `GET /clients/{id}` (platform) | `Depends(require_permission(...))` | `ctx.client_id` | *(omitted)* |
| `POST /users` (create) | `Depends(require_permission(...))` | `ctx.client_id` (optimistic) | `ctx.institution_id` (optimistic) |
| `GET /users/{id}` (get) | Inline `check_permission` after fetch | `user.client_id` | `user.institution_id` |
| `PATCH /users/{id}` (update) | Inline `check_permission` after fetch | `user.client_id` | `user.institution_id` |
| `DELETE /users/{id}` | Inline `check_permission` after fetch | `user.client_id` | `user.institution_id` |
| `GET /user-profiles/{id}` | Inline `check_permission` after fetch | `profile.client_id` | `profile.institution_id` |
| `POST /role-assignments` (create) | `Depends(require_permission(...))` | `ctx.client_id` (optimistic) | `ctx.institution_id` (optimistic) |
| `DELETE /role-assignments/{id}` | Inline `check_permission` after fetch | `ra.client_id` | `ra.institution_id` |
| Lookup endpoints (`/lookups/*`) | `Depends(require_permission(...))` | `ctx.client_id` | *(omitted)* |

### 5.5 Affected files — complete list

**C-01 routes (business/tenant_institution/routes/):**
- `client_portal.py` — ~16 require_permission calls
- `platform.py` — ~11 require_permission calls
- `client_users.py` — any additional routes

**C-02 routes (kernel/user/routes/):**
- `users.py` — 6 require_permission calls
- `profiles.py` — 3 require_permission calls
- `roles.py` — 3 require_permission calls
- `identifiers.py` — 3 require_permission calls
- `lookups.py` — 5 require_permission calls

**Other modules (update obj_client_id/obj_institution_id where applicable):**
- `kernel/config/routes/values.py` — 5 calls
- `kernel/config/routes/keys.py` — 5 calls
- `kernel/config/routes/resolve.py` — 2 calls
- `kernel/config/routes/audit.py` — 1 call
- `business/fees/routes/fee_assignments.py` — 5 calls
- `business/fees/routes/fee_types.py` — 5 calls
- `business/fees/routes/payments.py` — 2 calls
- `business/homework/routes/homework_routes.py` — 6 calls

---

## 6. C-01 Cleanup

### 6.1 Files to delete

| File | Reason |
|---|---|
| `backend/business/tenant_institution/policies.py` | All D11 policies migrated to role_permission table (D14, AC-1) |
| `backend/business/tenant_institution/casbin_model.conf` | Duplicate of kernel/authz/casbin_model.conf (D14, AC-2) |

### 6.2 Manifest change — `backend/business/tenant_institution/manifest.py`

**Before:**
```python
def register_casbin_policies(self, enforcer) -> None:
    from business.tenant_institution.policies import register_policies
    register_policies(enforcer)
```

**After:**
```python
def register_casbin_policies(self, enforcer) -> None:
    # C-04 is sole owner of policy registration (D14, AC-4).
    # All D11 policies migrated to role_permission DB table.
    pass
```

### 6.3 Test file updates

| File | Change |
|---|---|
| `tests/test_c04_authz.py` | Remove `from business.tenant_institution.policies import register_policies`. Update `_build_test_enforcer` to not use C-01 policies. Update `_register_c04_test_policies` to include C-01 roles with correct scopes. |
| `tests/test_casbin_permissions.py` | Remove `c01_manifest.register_casbin_policies(e)` calls. Update tests to use only C-04 DB-loaded policies. |
| `tests/conftest.py` | Remove any C-01 policy import references. |

### 6.4 Import cleanup

Search for and remove all imports of:
- `from business.tenant_institution.policies import ...`
- `from business.tenant_institution import policies`
- References to `PERMISSION_POLICIES`, `ROLE_HIERARCHY`, `build_enforcer` from C-01

---

## 7. Migration Strategy — Big-Bang

### 7.1 Rationale

Big-bang (one migration + one code change) is chosen because:
- The alternative (gradual migration with feature flags) adds complexity for a change that touches every route
- The migration is backward-compatible (DEFAULT 'institution' handles existing rows)
- The code change is mechanical (add parameters to existing calls)
- Testing catches issues before deploy

### 7.2 Deployment sequence

1. **Apply migration 016** to the database
   - Adds `scope` column with DEFAULT 'institution' (instant, no table rewrite)
   - Inserts 9 new permissions (ON CONFLICT DO NOTHING — idempotent)
   - Inserts C-01 role-permission mappings (ON CONFLICT DO NOTHING — idempotent)
2. **Deploy code** in same release:
   - `policy_loader.py` reads scope from DB
   - `require_permission` gains new parameters
   - Routes pass object attributes
   - C-01 files deleted
3. **Restart app** (required — Phase 1 has no runtime policy reload per D11)
4. **Run smoke tests** on staging:
   - CD can transition institution (was broken → now works)
   - Admin can read users (unchanged)
   - Cross-tenant access blocked at Casbin layer (new)
   - Platform owner bypass works (unchanged)

### 7.3 Rollback

If migration 016 fails:
- Downgrade drops `scope` column, deletes C-01 role-permission rows, deletes 9 permissions
- Code rollback: redeploy previous version (C-01 policies.py still exists in git history)

If code fails (migration succeeded):
- Redeploy previous code version
- The `scope` column is ignored by old code (old `policy_loader.py` hardcodes `"institution"`)
- C-01 policies still load from `policies.py` (file not deleted yet in old code)
- System returns to pre-consolidation state

### 7.4 Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Migration SQL has typo in permission names | Low | CD/admin roles broken | Test migration in staging; post-migration verification query |
| `policy_loader.py` scope column read fails | Low | All roles get institution scope (default) | Fallback: hardcoded "institution" in except block |
| Route update misses an endpoint | Medium | That endpoint uses ctx defaults (ABAC passes) | Grep for all `require_permission` calls; lint test |
| `check_permission` import missing | Low | ImportError on startup | Test all endpoints in CI |
| Performance: pre-fetch adds extra DB query | Low | Negligible for single-resource | Already fetching in most routes (e.g., `svc.get_institution`) |

---

## 8. Tradeoffs and Open Issues

### 8.1 Tradeoffs

| Decision | Alternative | Why chosen | Cost |
|---|---|---|---|
| **Big-bang migration** | Gradual with feature flags | Simpler; migration is backward-compatible | Higher deploy risk |
| **Scope on `role_permission`** (not `permission`) | Scope on `permission` table | Same permission can have different scopes per role (e.g., `institution.read` is `tenant` for CD but `institution` for Admin) | More rows; scope can't be inferred from permission alone |
| **Inline `check_permission`** | FastAPI `Depends` everywhere | FastAPI `Depends` can't use function-body results; inline is correct | Slightly more verbose routes |
| **Platform owner code bypass** | DB entry for platform_owner | D27/D28 decision; platform_owner has `*.*` which is dangerous in DB | Platform owner is code-coupled, not data-driven |
| **Default to ctx when obj attrs omitted** | Require explicit attrs | Backward compat; no need to update all routes at once | Silent pass-through for callers that forget |
| **`check_permission` + `require_permission` coexist** | Single API | `require_permission` for Depends pattern (create/list/lookup), `check_permission` for inline (single-resource) | Two APIs for same concern |

### 8.2 Open issues

| # | Issue | Status | Resolution |
|---|---|---|---|
| 1 | **`check_permission` vs `require_permission` naming** | Open | Consider renaming `require_permission` to `require_permission_dep` and `check_permission` to `require_permission` for consistency. Or keep as-is and document. |
| 2 | **List endpoints: what `obj_institution_id` to pass?** | Resolved | Omit for list endpoints (pass only `obj_client_id=ctx.client_id`). The Casbin matcher handles empty string as "no institution check" when scope is `tenant`. |
| 3 | **Do C-01 roles exist in `role` table?** | Needs verification | Migration 001 seeds C-01 roles. Migration 004 seeds `platform_owner`. Verify `client_director`, `institution_admin`, `cross_institution` rows exist before running migration 016. |
| 4 | **Role hierarchy — does it matter?** | Open | C-01's `ROLE_HIERARCHY` (platform_owner inherits client_director, etc.) was registered via `enforcer.add_role_for_user`. After consolidation, this hierarchy is lost unless we seed `role_hierarchy` entries in DB or add them in policy_loader. **Decision needed:** add role hierarchy rows to `role_permission` or add a `role_hierarchy` table? For now, platform_owner bypass is code-based so hierarchy is moot for platform_owner. For cross_institution roles (regional_manager → cross_institution), the hierarchy matters. |
| 5 | **Performance: extra DB query per single-resource endpoint** | Accepted | Each inline `check_permission` call doesn't add a query — the resource was already fetched. The Casbin enforcement is in-memory. |
| 6 | **C-02 routes ownership enforcement** | Unchanged | The `owner_id` parameter on `require_permission` still works. The ABAC change doesn't affect ownership logic. |

---

## 9. Casbin Model — No Change

The Casbin model at `kernel/authz/casbin_model.conf` is **unchanged**. It already supports the `(role, resource, action, scope)` policy tuple with the correct matcher:

```
m = g(r.sub.role, p.sub)
  && (p.obj == "*" || p.obj == r.obj.name)
  && (p.act == "*" || p.act == r.act)
  && (p.scope == "any"
      || (p.scope == "tenant" && r.sub.client_id == r.obj.client_id)
      || (p.scope == "institution"
          && r.sub.client_id == r.obj.client_id
          && r.sub.institution_id == r.obj.institution_id))
```

The only change is that policies are now loaded with the correct scope from DB instead of hardcoded `"institution"`.

---

## 10. Summary of All File Changes

| File | Action | Description |
|---|---|---|
| `backend/migrations/versions/016_c04_authorization_consolidation.py` | **CREATE** | Alembic migration: scope column, 9 permissions, C-01 role mappings |
| `backend/kernel/authz/dependencies.py` | **MODIFY** | Add `obj_client_id`, `obj_institution_id` params to `require_permission`. Add `check_permission` public function. |
| `backend/kernel/authz/services/policy_loader.py` | **MODIFY** | SELECT scope column, pass scope to `add_policy`, update type hints |
| `backend/business/tenant_institution/manifest.py` | **MODIFY** | Remove `register_casbin_policies` body (make no-op) |
| `backend/business/tenant_institution/policies.py` | **DELETE** | D11 matrix migrated to DB |
| `backend/business/tenant_institution/casbin_model.conf` | **DELETE** | Duplicate model removed |
| `backend/business/tenant_institution/routes/client_portal.py` | **MODIFY** | Pass obj attrs to require_permission / use check_permission inline |
| `backend/business/tenant_institution/routes/platform.py` | **MODIFY** | Pass obj attrs to require_permission |
| `backend/kernel/user/routes/users.py` | **MODIFY** | Pass obj attrs / use check_permission inline |
| `backend/kernel/user/routes/profiles.py` | **MODIFY** | Pass obj attrs / use check_permission inline |
| `backend/kernel/user/routes/roles.py` | **MODIFY** | Pass obj attrs / use check_permission inline |
| `backend/kernel/user/routes/identifiers.py` | **MODIFY** | Pass obj attrs / use check_permission inline |
| `backend/kernel/user/routes/lookups.py` | **MODIFY** | Pass obj_client_id=ctx.client_id |
| `backend/kernel/config/routes/*.py` | **MODIFY** | Pass obj_client_id=ctx.client_id where applicable |
| `backend/business/fees/routes/*.py` | **MODIFY** | Pass obj attrs where applicable |
| `backend/business/homework/routes/homework_routes.py` | **MODIFY** | Pass obj attrs where applicable |
| `tests/test_c04_authz.py` | **MODIFY** | Remove C-01 policy imports, update enforcer builder, add ABAC tests |
| `tests/test_casbin_permissions.py` | **MODIFY** | Remove C-01 policy registration, update to DB-only policies |
