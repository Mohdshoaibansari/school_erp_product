# Tasks — C-04 Authorization Consolidation (Single Source of Truth)

> **Change:** `consolidate-c04-authorization-single-source`
> **Status:** Ready for implementation
> **Estimated total:** 23 tasks across 5 phases

---

## Phase 0 — Schema Migration (3 tasks)

### Task 0.1: Create Alembic migration `016_c04_authorization_consolidation.py`

**File:** `backend/migrations/versions/016_c04_authorization_consolidation.py`

**Change:**
Create new Alembic migration file with revision `016_c04_authorization_consolidation`, `down_revision = "015_user_account_parent_table"`. The migration performs three operations:

1. **Add `scope` column** to `role_permission`:
   ```sql
   ALTER TABLE role_permission ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'institution';
   ```
   The DEFAULT handles backfill for existing C-02 role_permissions (Admin, Principal, HOD, Teacher, Staff, Student, Parent all operate at institution scope).

2. **Insert 9 missing permissions** into the `permission` table (ON CONFLICT DO NOTHING):
   - `institution.archive` — Archive an institution
   - `institution.list` — List institutions
   - `org_unit.archive` — Archive an org unit
   - `org_unit.reactivate` — Reactivate an org unit
   - `org_unit.reorder` — Reorder org units
   - `institution_type.create` — Create institution types
   - `institution_type.update` — Update institution types
   - `user_profile.create` — Create user profile
   - `user.delete` — Delete a user

3. **Migrate C-01 roles** to `role_permission`:
   - `client_director` → 15 permissions (institution.*, client.*, org_unit.*) with scope `'tenant'`
   - `institution_admin` → 9 permissions (institution.read/update, org_unit.*) with scope `'institution'`
   - `cross_institution` → 3 permissions (client.read, institution.read, org_unit.read) with scope `'tenant'`

Include a `downgrade()` that: drops the `scope` column, deletes C-01 role-permission rows, deletes the 9 new permissions.

**Verify:**
```bash
cd backend && python -m alembic upgrade head && python -c "
import os; from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'))
with engine.connect() as c:
    assert c.execute(text('SELECT COUNT(*) FROM permission')).scalar() >= 35, 'Expected >= 35 permissions'
    assert c.execute(text(\"SELECT COUNT(*) FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name='client_director'\")).scalar() == 15
    assert c.execute(text(\"SELECT COUNT(*) FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name='institution_admin'\")).scalar() == 9
    assert c.execute(text(\"SELECT COUNT(*) FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name='cross_institution'\")).scalar() == 3
    assert c.execute(text(\"SELECT DISTINCT rp.scope FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name='client_director'\")).scalar() == 'tenant'
print('ALL CHECKS PASSED')
"
```

---

### Task 0.2: Verify scope column on existing C-02 role_permissions

**File:** N/A (post-migration verification)

**Change:**
After applying migration 016, verify all existing C-02 role_permissions have `scope = 'institution'` from the DEFAULT. Run a verification query against the database.

**Verify:**
```bash
cd backend && python -c "
import os; from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'))
with engine.connect() as c:
    rows = c.execute(text(\"SELECT r.name, rp.scope, COUNT(*) FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name IN ('Admin','Principal','HOD','Teacher','Staff','Student','Parent') GROUP BY r.name, rp.scope\")).fetchall()
    for r in rows:
        assert r[1] == 'institution', f'{r[0]} has scope {r[1]}, expected institution'
    print('All C-02 roles have institution scope:', rows)
"
```

---

### Task 0.3: Verify migration downgrade

**File:** N/A (post-migration verification)

**Change:**
Test that `alembic downgrade -1` correctly removes the `scope` column, C-01 role-permission rows, and the 9 new permissions. Then re-upgrade.

**Verify:**
```bash
cd backend && python -m alembic downgrade -1 && python -c "
import os; from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'))
with engine.connect() as c:
    assert c.execute(text(\"SELECT COUNT(*) FROM role_permission rp JOIN role r ON r.id=rp.role_id WHERE r.name IN ('client_director','institution_admin','cross_institution')\")).scalar() == 0
    assert c.execute(text(\"SELECT COUNT(*) FROM permission WHERE name IN ('institution.archive','institution.list','org_unit.archive','org_unit.reactivate','org_unit.reorder','institution_type.create','institution_type.update','user_profile.create','user.delete')\")).scalar() == 0
print('Downgrade OK')
" && python -m alembic upgrade head && echo "Re-upgrade OK"
```

---

## Phase 1 — Policy Loader + `require_permission` Changes (4 tasks)

### Task 1.1: Update `policy_loader.py` to read scope from DB

**File:** `backend/kernel/authz/services/policy_loader.py`

**Change:**
1. Update `load_permission_map()` — change SELECT to include `rp.scope`:
   ```sql
   SELECT r.name AS role_name, p.resource, p.action, rp.scope
   FROM role_permission rp
   JOIN role r ON r.id = rp.role_id
   JOIN permission p ON p.id = rp.permission_id
   ORDER BY r.name, p.resource, p.action
   ```
2. Update `_permission_map` type from `dict[str, list[tuple[str, str]]]` to `dict[str, list[tuple[str, str, str]]]`
3. Update the loop to unpack 4 columns: `role_name, resource, action, scope`
4. Update `register_policies_from_map()` — change `add_policy(role_name, resource, action, "institution")` to `add_policy(role_name, resource, action, scope)` (scope from DB, not hardcoded)
5. Update `get_permission_map()` return type to `dict[str, list[tuple[str, str, str]]]`

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.policy_loader import load_permission_map, get_permission_map
load_permission_map()
m = get_permission_map()
for role, perms in m.items():
    for p in perms:
        assert len(p) == 3, f'{role}: expected 3-tuple, got {p}'
        assert p[2] in ('any', 'tenant', 'institution'), f'{role}: invalid scope {p[2]}'
print('Policy loader OK:', {k: len(v) for k, v in m.items()})
"
```

---

### Task 1.2: Add `check_permission` callable to `dependencies.py`

**File:** `backend/kernel/authz/dependencies.py`

**Change:**
Add a new public function `check_permission()` that performs the same logic as `require_permission`'s inner `_enforce` but is callable directly (for use in route handlers that need inline ABAC after fetching a resource). Signature:

```python
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
```

Logic is identical to `_enforce` inner function: platform_owner bypass, role validation, build sub from ctx, build obj from params (defaulting to ctx), Casbin enforce, ownership check. Raises `HTTPException(403)` on denial.

**Verify:**
```bash
cd backend && python -c "from kernel.authz.dependencies import check_permission; print('Import OK')"
```

---

### Task 1.3: Update `require_permission` to accept object attributes

**File:** `backend/kernel/authz/dependencies.py`

**Change:**
1. Add `obj_client_id: uuid.UUID | None = None` and `obj_institution_id: uuid.UUID | None = None` keyword parameters to `require_permission`
2. Update inner `_enforce` to build the Casbin object from these parameters instead of from ctx:
   ```python
   obj = {
       "name": resource,
       "client_id": str(obj_client_id) if obj_client_id
                    else (str(ctx.client_id) if ctx.client_id else ""),
       "institution_id": str(obj_institution_id) if obj_institution_id
                          else (str(ctx.institution_id) if ctx.institution_id else ""),
   }
   ```
3. Backward compatibility: when `obj_client_id=None` and `obj_institution_id=None`, fall back to `ctx` values (existing callers continue to work without changes)
4. Update the docstring to document the new parameters

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.dependencies import require_permission
import inspect
sig = inspect.signature(require_permission)
params = list(sig.parameters.keys())
assert 'obj_client_id' in params, f'Missing obj_client_id, params: {params}'
assert 'obj_institution_id' in params, f'Missing obj_institution_id, params: {params}'
assert sig.parameters['obj_client_id'].default is None
assert sig.parameters['obj_institution_id'].default is None
print('Signature OK:', params)
"
```

---

### Task 1.4: Update `kernel/authz/manifest.py` to import `check_permission`

**File:** `backend/kernel/authz/manifest.py`

**Change:**
No change needed — `check_permission` is a module-level function in `dependencies.py`, not exported via manifest. The manifest continues to load policies via `policy_loader`. Verify that the manifest's `on_startup` and `register_casbin_policies` hooks still work after the `policy_loader` changes from Task 1.1.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.manifest import manifest
print('Manifest name:', manifest.name)
print('register_casbin_policies:', hasattr(manifest, 'register_casbin_policies'))
"
```

---

## Phase 2 — Route Updates (9 tasks)

### Task 2.1: Update C-01 institution routes — `client_portal.py`

**File:** `backend/business/tenant_institution/routes/client_portal.py`

**Change:**
Update all ~11 `require_permission` calls to pass `obj_client_id` and `obj_institution_id`. Two patterns:

**Pattern A — Create/list endpoints (no resource fetch needed):** Use `Depends(require_permission(...))` with explicit ctx values:
- `POST /institutions` (create): pass `obj_client_id=ctx.client_id` (optimistic)
- `GET /institutions` (list): pass `obj_client_id=ctx.client_id` only

**Pattern B — Single-resource endpoints (pre-fetch required):** Convert to inline `check_permission` after fetching the resource:
- `GET /institutions/{id}` (read): fetch institution first, then `check_permission(ctx, enforcer, "institution", "read", obj_client_id=inst.client_id, obj_institution_id=inst.id)`
- `PUT /institutions/{id}` (update): same pattern
- `POST /institutions/{id}/transition` (transition_lifecycle): same pattern
- `POST /institutions/{id}/archive` (archive): same pattern
- `GET /org-units/{id}` (read): fetch org unit, pass `obj_client_id=ou.client_id, obj_institution_id=ou.institution_id`
- `PUT /org-units/{id}` (update): same pattern
- `DELETE /org-units/{id}` (delete): same pattern
- `POST /org-units/{id}/move` (move): same pattern
- `POST /org-units/{id}/archive` (archive): same pattern
- `POST /org-units/{id}/reactivate` (reactivate): same pattern

For Pattern B endpoints, remove the `_authz` Depends parameter and add inline check after the service call. Add `enforcer: Any = Depends(get_enforcer)` to the function signature.

**Verify:**
```bash
cd backend && python -c "
import ast, sys
with open('business/tenant_institution/routes/client_portal.py') as f:
    tree = ast.parse(f.read())
# Verify no bare require_permission('...', '...') without obj_client_id in function defs
print('client_portal.py: AST parse OK')
" && grep -c "check_permission\|obj_client_id" backend/business/tenant_institution/routes/client_portal.py
```

---

### Task 2.2: Update C-01 platform routes — `platform.py`

**File:** `backend/business/tenant_institution/routes/platform.py`

**Change:**
Update all ~11 `require_permission` calls. Key routes:
- `POST /clients` (create): `require_permission("client", "create", obj_client_id=ctx.client_id)`
- `GET /clients/{id}` (read): inline `check_permission` after fetching client, `obj_client_id=client.id`
- `PUT /clients/{id}` (update): inline `check_permission`, `obj_client_id=client.id`
- `POST /clients/{id}/transition` (transition_lifecycle): inline `check_permission`, `obj_client_id=client.id`
- `GET /institution-types` (list): `require_permission("institution_type", "read", obj_client_id=ctx.client_id)`
- `POST /institution-types` (create): `require_permission("institution_type", "create", obj_client_id=ctx.client_id)`
- `GET /institution-types/{id}` (read): inline `check_permission`, `obj_client_id=ctx.client_id`
- `PUT /institution-types/{id}` (update): inline `check_permission`, `obj_client_id=ctx.client_id`
- `POST /clients/{id}/transfer-ownership` (transfer_ownership): inline `check_permission`, `obj_client_id=client.id`

**Verify:**
```bash
cd backend && python -c "import ast; ast.parse(open('business/tenant_institution/routes/platform.py').read()); print('platform.py: AST parse OK')"
```

---

### Task 2.3: Update C-02 user routes — `users.py`

**File:** `backend/kernel/user/routes/users.py`

**Change:**
Update all 6 `require_permission` calls:
- `POST /users` (create): `require_permission("user", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- `GET /users` (list): `require_permission("user", "read", obj_client_id=ctx.client_id)`
- `GET /users/{id}` (read): inline `check_permission` after fetch, `obj_client_id=user.client_id, obj_institution_id=user.institution_id`
- `PUT /users/{id}` (update): inline `check_permission`
- `DELETE /users/{id}` (delete): inline `check_permission`
- `POST /users/{id}/suspend` (suspend): inline `check_permission`

**Verify:**
```bash
cd backend && python -c "import ast; ast.parse(open('kernel/user/routes/users.py').read()); print('users.py: AST parse OK')"
```

---

### Task 2.4: Update C-02 profile/role/identifier routes

**Files:**
- `backend/kernel/user/routes/profiles.py`
- `backend/kernel/user/routes/roles.py`
- `backend/kernel/user/routes/identifiers.py`

**Change:**

**profiles.py** (3 calls):
- `POST /user-profiles` (create): `require_permission("user_profile", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- `GET /user-profiles/{id}` (read): inline `check_permission` after fetch, `obj_client_id=profile.client_id, obj_institution_id=profile.institution_id`
- `PUT /user-profiles/{id}` (update): inline `check_permission`

**roles.py** (3 calls):
- `POST /role-assignments` (create): `require_permission("role_assignment", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- `GET /role-assignments` (list): `require_permission("role_assignment", "read", obj_client_id=ctx.client_id)`
- `DELETE /role-assignments/{id}` (delete): inline `check_permission` after fetch, `obj_client_id=ra.client_id, obj_institution_id=ra.institution_id`

**identifiers.py** (3 calls):
- `POST /user-identifiers` (create): `require_permission("user_identifier", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- `GET /user-identifiers/{id}` (read): inline `check_permission`, `obj_client_id=ident.client_id, obj_institution_id=ident.institution_id`
- `DELETE /user-identifiers/{id}` (delete): inline `check_permission`

**Verify:**
```bash
cd backend && for f in kernel/user/routes/profiles.py kernel/user/routes/roles.py kernel/user/routes/identifiers.py; do python -c "import ast; ast.parse(open('$f').read()); print('$f: AST OK')"; done
```

---

### Task 2.5: Update C-02 lookup routes — `lookups.py`

**File:** `backend/kernel/user/routes/lookups.py`

**Change:**
Update all 5 `require_permission` calls. All are list/lookup endpoints — pass `obj_client_id=ctx.client_id` only:
- `GET /lookups/user-categories` → `require_permission("user", "read", obj_client_id=ctx.client_id)`
- `GET /lookups/roles` → `require_permission("role_assignment", "read", obj_client_id=ctx.client_id)`
- `GET /lookups/institutions` → `require_permission("institution", "read", obj_client_id=ctx.client_id)`
- `GET /lookups/org-units` → `require_permission("org_unit", "read", obj_client_id=ctx.client_id)`
- `GET /lookups/clients` → `require_permission("client", "read", obj_client_id=ctx.client_id)`

**Verify:**
```bash
cd backend && python -c "import ast; ast.parse(open('kernel/user/routes/lookups.py').read()); print('lookups.py: AST OK')"
```

---

### Task 2.6: Update fees routes — `fee_assignments.py`, `fee_types.py`, `payments.py`

**Files:**
- `backend/business/fees/routes/fee_assignments.py`
- `backend/business/fees/routes/fee_types.py`
- `backend/business/fees/routes/payments.py`

**Change:**

**fee_assignments.py** (5 calls):
- Create: `require_permission("fee_assignment", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- List: `require_permission("fee_assignment", "read", obj_client_id=ctx.client_id)`
- Get by ID: inline `check_permission` after fetch
- Update: inline `check_permission`
- Waive: inline `check_permission`

**fee_types.py** (5 calls):
- Create: `require_permission("fee", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- List: `require_permission("fee", "read", obj_client_id=ctx.client_id)`
- Get by ID: inline `check_permission`
- Update: inline `check_permission`
- Delete: inline `check_permission`

**payments.py** (2 calls):
- Create: `require_permission("payment", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- List: `require_permission("payment", "read", obj_client_id=ctx.client_id)`

**Verify:**
```bash
cd backend && for f in business/fees/routes/fee_assignments.py business/fees/routes/fee_types.py business/fees/routes/payments.py; do python -c "import ast; ast.parse(open('$f').read()); print('$f: AST OK')"; done
```

---

### Task 2.7: Update homework routes — `homework_routes.py`

**File:** `backend/business/homework/routes/homework_routes.py`

**Change:**
Update all ~12 `require_permission` calls:
- Create homework: `require_permission("homework", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- List homework: `require_permission("homework", "read", obj_client_id=ctx.client_id)`
- Get homework by ID: inline `check_permission` after fetch
- Update homework: inline `check_permission`
- Delete homework: inline `check_permission`
- Close homework: inline `check_permission`
- Submit: `require_permission("submission", "create", obj_client_id=ctx.client_id, obj_institution_id=ctx.institution_id)`
- Get submission: inline `check_permission`
- Create grade: inline `check_permission`
- Get grade: inline `check_permission`
- Update grade: inline `check_permission`

**Verify:**
```bash
cd backend && python -c "import ast; ast.parse(open('business/homework/routes/homework_routes.py').read()); print('homework_routes.py: AST OK')"
```

---

### Task 2.8: Update config routes — `values.py`, `keys.py`, `resolve.py`, `audit.py`

**Files:**
- `backend/kernel/config/routes/values.py`
- `backend/kernel/config/routes/keys.py`
- `backend/kernel/config/routes/resolve.py`
- `backend/kernel/config/routes/audit.py`

**Change:**
All config endpoints are list/create/update/delete patterns. Pass `obj_client_id=ctx.client_id` where applicable. Config is global (no RLS), so no `obj_institution_id` needed for most. Update each `require_permission` call:

- `values.py` (5 calls): add `obj_client_id=ctx.client_id` to all
- `keys.py` (5 calls): add `obj_client_id=ctx.client_id` to all
- `resolve.py` (2 calls): add `obj_client_id=ctx.client_id` to all
- `audit.py` (1 call): add `obj_client_id=ctx.client_id`

**Verify:**
```bash
cd backend && for f in kernel/config/routes/values.py kernel/config/routes/keys.py kernel/config/routes/resolve.py kernel/config/routes/audit.py; do python -c "import ast; ast.parse(open('$f').read()); print('$f: AST OK')"; done
```

---

### Task 2.9: Verify no bare `require_permission` calls remain without `obj_client_id`

**File:** N/A (grep verification)

**Change:**
After all Phase 2 route updates, verify that every `require_permission` call in route files includes `obj_client_id`. This ensures no endpoint was missed.

**Verify:**
```bash
cd backend && grep -rn "require_permission(" --include="*.py" business/ kernel/ | grep -v ".venv" | grep -v "__pycache__" | grep -v "test_" | grep -v "def require_permission" | grep -v "check_permission" | grep -v "obj_client_id" || echo "ALL require_permission calls include obj_client_id"
```

---

## Phase 3 — C-01 Cleanup (4 tasks)

### Task 3.1: Delete `policies.py`

**File:** `backend/business/tenant_institution/policies.py`

**Change:**
Delete the file. All D11 policies are now in the `role_permission` DB table (migrated in Phase 0). No file should exist at this path after the change.

**Verify:**
```bash
test ! -f backend/business/tenant_institution/policies.py && echo "policies.py deleted OK" || echo "FAIL: policies.py still exists"
```

---

### Task 3.2: Delete `casbin_model.conf`

**File:** `backend/business/tenant_institution/casbin_model.conf`

**Change:**
Delete the file. The only Casbin model file remains at `backend/kernel/authz/casbin_model.conf`.

**Verify:**
```bash
test ! -f backend/business/tenant_institution/casbin_model.conf && echo "casbin_model.conf deleted OK" || echo "FAIL: casbin_model.conf still exists"
test -f backend/kernel/authz/casbin_model.conf && echo "Central model OK" || echo "FAIL: central model missing"
```

---

### Task 3.3: Remove `register_casbin_policies` from C-01 manifest

**File:** `backend/business/tenant_institution/manifest.py`

**Change:**
Remove the `register_casbin_policies` method body (or make it a no-op). C-04 is the sole owner of policy registration. The method should become:

```python
def register_casbin_policies(self, enforcer) -> None:
    # C-04 is sole owner of policy registration (D14, AC-4).
    # All D11 policies migrated to role_permission DB table.
    pass
```

Remove the import of `register_policies` from `policies`.

**Verify:**
```bash
cd backend && python -c "
from business.tenant_institution.manifest import manifest
import inspect
src = inspect.getsource(manifest.register_casbin_policies)
assert 'register_policies' not in src, 'Still imports register_policies'
assert 'pass' in src or len(src.strip().split(chr(10))) <= 4, 'Body should be empty/pass'
print('Manifest OK: register_casbin_policies is a no-op')
"
```

---

### Task 3.4: Remove all imports of `policies.py` from test files

**Files:**
- `backend/tests/test_c04_authz.py`
- `backend/tests/test_casbin_permissions.py`
- `backend/tests/test_fees.py`

**Change:**
Remove all imports from `business.tenant_institution.policies` (e.g., `register_policies`, `make_subject`, `make_resource`, `casbin_model_path`, `PERMISSION_POLICIES`, `ROLE_HIERARCHY`, `build_enforcer`). Update test helpers to use C-04 DB-loaded policies or inline test fixtures instead of C-01 hardcoded policies.

For `test_c04_authz.py`:
- Remove `from business.tenant_institution.policies import register_policies`
- Update `_build_test_enforcer()` to not call `register_policies(e)`. Instead, register C-01 role policies inline using the same scope-aware pattern (with tenant/institution scopes).
- Update `_register_c04_test_policies()` to include C-01 roles (client_director, institution_admin, cross_institution) with correct scopes.

For `test_casbin_permissions.py`:
- Remove all imports from `business.tenant_institution.policies`
- Remove `c01_manifest.register_casbin_policies(e)` calls
- Rewrite tests to use C-04 DB-style policy registration (test helper that seeds C-01 roles inline)
- The D11 matrix tests should still pass with the same assertions — only the policy source changes

For `test_fees.py`:
- Remove `from business.tenant_institution.policies import register_policies`
- Update enforcer fixture to use C-04-style policy registration

**Verify:**
```bash
cd backend && grep -rn "from business.tenant_institution.policies\|from business.tenant_institution import policies" --include="*.py" | grep -v ".venv" | grep -v "__pycache__" || echo "No remaining imports of policies.py"
```

---

## Phase 4 — Testing (3 tasks)

### Task 4.1: Update `test_c04_authz.py` with ABAC object-attribute tests

**File:** `backend/tests/test_c04_authz.py`

**Change:**
Add new test cases for ABAC enforcement with object attributes:

1. **Cross-tenant block test:** CD (client_id=A) calling `require_permission("institution", "read", obj_client_id=B)` → 403
2. **Same-tenant pass test:** CD (client_id=A) calling `require_permission("institution", "read", obj_client_id=A)` → 200
3. **Cross-institution block test:** Admin (institution_id=X) calling `require_permission("user", "read", obj_institution_id=Y)` → 403
4. **check_permission callable test:** Test that `check_permission(ctx, enforcer, ...)` works inline
5. **Backward compat test:** `require_permission("user", "read")` without obj attrs → falls back to ctx → 200

Update `_build_test_enforcer` to not use C-01 policies (post-cleanup). Register C-01 roles with correct scopes in `_register_c04_test_policies`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_c04_authz.py -v 2>&1 | tail -30
```

---

### Task 4.2: Run full test suite

**File:** N/A

**Change:**
Run all existing tests to verify backward compatibility. All existing tests must pass after the consolidation. Focus on:
- `test_c04_authz.py` — C-04 authorization tests (updated in Task 4.1)
- `test_casbin_permissions.py` — D11 matrix tests (updated in Task 3.4)
- `test_c02_user.py` — C-02 user tests (should pass with updated routes)
- `test_fees.py` — Fees tests (updated in Task 3.4)
- `test_lifecycle.py` — Institution lifecycle tests
- `test_org_unit_hierarchy.py` — Org unit tests
- `test_api.py` — API integration tests
- `test_rls.py` — RLS tests (unchanged, should still pass)

**Verify:**
```bash
cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -50
```

---

### Task 4.3: Journey flow verification

**File:** N/A

**Change:**
Verify the three key user journeys from the PRD work end-to-end:

1. **CD transitions an institution** (was broken → now works): CD calls `POST /api/v1/institutions/{id}/transition` → 200 (not 403)
2. **Cross-tenant block at Casbin layer**: CD-A calls `GET /api/v1/institutions/{id}` where institution belongs to client-B → 403 (not just RLS)
3. **Platform owner bypass**: PO calls any endpoint → 200 (code bypass retained)

These may need to be tested manually against a running app or via integration test fixtures.

**Verify:**
```bash
cd backend && python -m pytest tests/test_lifecycle.py tests/test_c04_authz.py tests/test_casbin_permissions.py -v -k "transition or platform_owner or cross" 2>&1 | tail -20
```

---

## Summary

| Phase | Tasks | Files Changed | Key Deliverable |
|---|---|---|---|
| Phase 0 | 3 | 1 (migration) | Scope column + 9 permissions + C-01 role mappings in DB |
| Phase 1 | 4 | 2 (dependencies.py, policy_loader.py) | `check_permission` + `require_permission` with obj attrs + scope-aware policy loader |
| Phase 2 | 9 | ~16 route files | All routes pass `obj_client_id`/`obj_institution_id` for ABAC |
| Phase 3 | 4 | 4 (delete 2 files, update 1 manifest, update 3 test files) | C-01 `policies.py` + `casbin_model.conf` removed, manifest no-op |
| Phase 4 | 3 | 1 (test_c04_authz.py) | ABAC tests + full suite pass + journey verification |
| **Total** | **23** | **~24 files** | Single source of truth for authorization |

### Dependency Order

```
Phase 0 (migration) → Phase 1 (policy loader + deps) → Phase 2 (routes) → Phase 3 (cleanup) → Phase 4 (testing)
```

Within each phase, tasks can be done in the listed order. Phase 3 depends on Phase 2 (routes must be updated before removing policies.py). Phase 4 depends on Phase 3 (tests must reference the new patterns).
