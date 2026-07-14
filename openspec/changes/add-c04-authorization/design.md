# Design — C-04 Authorization

> **Traceability.** Design decisions trace to grill-me decision IDs (D1–D33) and PRD AC IDs (AC-1..AC-24). The design follows C-01/C-02/C-03's established patterns (ModuleManifest Protocol A5, hybrid Depends+contextvar A6, TenantAwareRepositoryBase A6, single Alembic env A7).

## 1. Module Structure

```
backend/kernel/authz/
├── __init__.py
├── manifest.py              # AuthorizationManifest (A5 hooks)
├── casbin_model.conf         # Casbin model (relocated from C-01, D14)
├── models/
│   ├── __init__.py
│   ├── permission.py         # Permission + RolePermission ORM models
├── dependencies.py           # get_enforcer(), require_permission()
├── services/
│   ├── __init__.py
│   ├── policy_loader.py      # on_startup DB read + register_casbin_policies
├── conftest.py              # Test fixtures (real Casbin enforcer with seed data)
```

## 2. Database Schema

Migration: `004_c04_authorization.py`.

### 2.1 permission table

```sql
CREATE TABLE permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No RLS (global data, shared across all clients)
```

**Seed data (26 rows):** C-01 resources: `client.read`, `client.update`, `client.transfer_ownership`, `client.transition_lifecycle`, `institution.read`, `institution.create`, `institution.update`, `institution.transition_lifecycle`, `org_unit.read`, `org_unit.create`, `org_unit.update`, `org_unit.delete`, `org_unit.move`, `institution_type.read`. C-02 resources: `user.read`, `user.create`, `user.update`, `user.suspend`, `user_profile.read`, `user_profile.update`, `role_assignment.read`, `role_assignment.create`, `role_assignment.delete`, `user_identifier.read`, `user_identifier.create`, `user_identifier.delete`.

### 2.2 role_permission table

```sql
CREATE TABLE role_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES role(id),     -- FK to C-02's role table
    permission_id UUID NOT NULL REFERENCES permission(id),
    UNIQUE(role_id, permission_id)
);
-- No RLS (global data)
```

**Seed data (~40 rows):** The mapping per C-02 role uses a SQL join:
```sql
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id FROM role r, permission p
WHERE r.name = 'Admin' AND p.name IN (
    'institution.read', 'org_unit.read', 'org_unit.create', 'org_unit.update',
    'org_unit.delete', 'org_unit.move', 'institution_type.read',
    'user.read', 'user.create', 'user.update', 'user.suspend',
    'user_profile.read', 'role_assignment.read', 'role_assignment.create',
    'role_assignment.delete', 'user_identifier.read', 'user_identifier.create',
    'user_identifier.delete'
);
-- Similar blocks for Principal, HOD, Teacher, Staff, Student, Parent
```

### 2.3 platform_owner role row

```sql
INSERT INTO role (id, name) VALUES (gen_random_uuid(), 'platform_owner')
ON CONFLICT (name) DO NOTHING;
```

## 3. Casbin Model and Enforcer

### 3.1 Model relocatio

C-01's `business/tenant_institution/casbin_model.conf` moves to `kernel/authz/casbin_model.conf`. The model content is unchanged. C-01's `register_casbin_policies(enforcer)` hook continues to add D11 policies — only the model path changes.

### 3.2 App factory enforcer creation

In `kernel/app_factory.py`, `create_app()`:

```python
import casbin
from pathlib import Path

def create_app(manifests: list) -> FastAPI:
    # ... existing setup ...

    # Create Casbin enforcer from centralized model (D10, D29)
    casbin_model_path = Path(__file__).parent / "authz" / "casbin_model.conf"
    enforcer = casbin.Enforcer(str(casbin_model_path))

    # Call register_casbin_policies on each manifest (dependency order)
    for manifest in manifests:
        if hasattr(manifest, "register_casbin_policies"):
            manifest.register_casbin_policies(enforcer)

    # Store enforcer singleton
    set_enforcer(enforcer)
    # ...
```

### 3.3 Policy registration hooks

The existing `register_casbin_policies(enforcer)` hooks on C-01, C-02, C-03 manifests remain unchanged in signature. C-01's hook calls `register_policies(enforcer)` from its `policies.py`. C-02's hook is empty. C-03's hook is empty. C-04's hook adds permission-based policies.

C-04's hook:

```python
# kernel/authz/services/policy_loader.py

_role_permission_map: dict[str, list[tuple[str, str]]] = {}  # role_name → [(resource, action)]

def load_permission_map(session):
    """Read role_permission from DB into in-memory map (called by on_startup)."""
    rows = session.execute(text("""
        SELECT r.name AS role_name, p.resource, p.action
        FROM role_permission rp
        JOIN role r ON r.id = rp.role_id
        JOIN permission p ON p.id = rp.permission_id
    """)).fetchall()
    _role_permission_map.clear()
    for role_name, resource, action in rows:
        _role_permission_map.setdefault(role_name, []).append((resource, action))

def register_casbin_policies(enforcer):
    """Add C-04 permission-based policies to the enforcer (D24)."""
    for role_name, perms in _role_permission_map.items():
        for resource, action in perms:
            enforcer.add_policy(role_name, resource, action, "institution")
        # Add role grouping for Casbin hierarchy
        enforcer.add_grouping_policy(role_name, f"{role_name}_casbin_label")
```

## 4. require_permission Dependency

### 4.1 Signature

```python
# kernel/authz/dependencies.py

from fastapi import Depends, HTTPException
from kernel.tenant_context import TenantContext, get_tenant_context

def require_permission(
    resource: str,
    action: str,
    *,
    client_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
):
    """FastAPI dependency enforcing role+scope+ownership authorization.

    Two-step enforcement (D12):
    1. Casbin: role + resource + action + scope (tenant/institution/any)
    2. App-level: ownership check (if owner_id provided)
    """
    def enforce(
        ctx: TenantContext = Depends(get_tenant_context),
        enforcer = Depends(get_enforcer),
    ):
        role = ctx.roles[0] if ctx.roles else ""

        # Build Casbin subject and object
        sub = {
            "role": role,
            "client_id": str(ctx.client_id) if ctx.client_id else "",
            "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
        }
        obj = {
            "name": resource,
            "client_id": str(client_id) if client_id else "",
            "institution_id": str(institution_id) if institution_id else "",
        }

        # Step 1: Casbin role + scope check
        if not enforcer.enforce(sub, obj, action):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {resource}.{action} requires role with appropriate scope",
            )

        # Step 2: Ownership check (D22)
        if owner_id and ctx.user_id and str(owner_id) != str(ctx.user_id):
            # Check if user has admin scope (can act on behalf of others)
            admin_obj = dict(obj)
            admin_obj["name"] = f"{resource}.admin_bypass"
            if not enforcer.enforce(sub, admin_obj, action):
                raise HTTPException(
                    status_code=403,
                    detail="You can only access your own resource",
                )

    return Depends(enforce)
```

### 4.2 Endpoint usage example

```python
# C-01 example
@router.post("/institutions", status_code=201)
def create_institution(
    dto: InstitutionCreateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
    _: None = Depends(require_permission(
        "institution", "create",
        client_id=dto.client_id,
        institution_id=dto.institution_id,
    )),
):
    ...

# C-02 example with ownership
@router.get("/users/{user_id}")
def get_user(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
    _: None = Depends(require_permission(
        "user", "read",
        client_id=ctx.client_id,
        institution_id=ctx.institution_id,
        owner_id=user_id,  # ownership check
    )),
):
    ...
```

## 5. Manifest and Dependencies

### 5.1 AuthorizationManifest (A5)

```python
# kernel/authz/manifest.py

class AuthorizationManifest(ManifestBase):
    name = "authorization"

    def register_routes(self, app):
        pass  # No C-04 endpoints in Phase 1

    async def on_startup(self):
        """Read role_permission from DB into in-memory map (D24)."""
        from kernel.authz.services.policy_loader import load_permission_map
        from kernel.auth.dependencies import get_db_session_factory
        session_factory = get_db_session_factory()
        with session_factory() as session:
            load_permission_map(session)

    def register_casbin_policies(self, enforcer):
        """Add C-04 permission-based policies (D24)."""
        from kernel.authz.services.policy_loader import register_casbin_policies
        register_casbin_policies(enforcer)
```

### 5.2 Dependencies injection (A6)

```python
# kernel/authz/dependencies.py

_enforcer: casbin.Enforcer | None = None

def set_enforcer(enforcer: casbin.Enforcer):
    global _enforcer
    _enforcer = enforcer

def get_enforcer() -> casbin.Enforcer:
    return _enforcer    # singleton, set by app factory
```

## 6. Startup Sequence

1. Alembic migration 004 applied: `permission` + `role_permission` tables created, 26 permissions + ~40 role_permission rows seeded, `platform_owner` row added to `role` table
2. `create_app()` called with manifests [C-01, C-02, C-03, C-04] in dependency order
3. C-04's `on_startup` runs: reads `role_permission` from DB into in-memory `_role_permission_map`
4. App factory creates Casbin enforcer from `kernel/authz/casbin_model.conf`
5. Factory iterates manifests, calls `register_casbin_policies(enforcer)`:
   - C-01: adds D11 policies (`*.*` for platform_owner, tenant/institution scopes, etc.)
   - C-02: empty
   - C-03: empty
   - C-04: adds permission policies (`Teacher, user, read, institution`, etc.)
6. Factory calls `set_enforcer(enforcer)`
7. Enforcer ready. `get_enforcer()` returns the singleton

## 7. Testing Strategy

### 7.1 C-04 unit tests: Casbin enforcement

Build the real Casbin enforcer with the real model and seed policies, then assert for each role-permission-scope combination.

```python
# tests/test_c04_authorization.py

def test_enforcer_teacher_has_user_read():
    enforcer = casbin.Enforcer("kernel/authz/casbin_model.conf")
    register_all_policies(enforcer, seed_data)  # adds policies from seed

    sub = {"role": "Teacher", "client_id": "c1", "institution_id": "i1"}
    obj = {"name": "user", "client_id": "c1", "institution_id": "i1"}

    assert enforcer.enforce(sub, obj, "read") == True
    assert enforcer.enforce(sub, obj, "create") == False

def test_enforcer_teacher_cross_institution_denied():
    enforcer = casbin.Enforcer("kernel/authz/casbin_model.conf")
    register_all_policies(enforcer, seed_data)

    sub = {"role": "Teacher", "client_id": "c1", "institution_id": "i1"}
    obj = {"name": "user", "client_id": "c1", "institution_id": "i2"}  # different institution

    assert enforcer.enforce(sub, obj, "read") == False  # institution scope check fails
```

### 7.2 C-04 integration tests: require_permission dependency

Test the dependency with a mocked TenantContext.

```python
def test_require_permission_grants_to_authorized_role(app):
    enforcer = casbin.Enforcer("kernel/authz/casbin_model.conf")
    register_all_policies(enforcer, seed_data)
    set_enforcer(enforcer)

    ctx = TenantContext(
        client_id=uuid.UUID("c1"), institution_id=uuid.UUID("i1"),
        roles=["Admin"], user_id="admin-1",
    )
    with app.dependency_overrides as overrides:
        overrides[get_tenant_context] = lambda: ctx
        # Call require_permission indirectly via a test endpoint or directly
        dep = require_permission("user", "create", client_id=ctx.client_id, institution_id=ctx.institution_id)
        # Should not raise
```

### 7.3 C-01/C-02 retrofit tests

Tests need:
1. Seed `role` + `permission` + `role_permission` data in test fixtures, OR
2. `app.dependency_overrides[get_enforcer] = lambda: PermissiveEnforcer()`

Seeding is preferred — it validates the real authorization path.

## 8. Import-Linter

No new contracts. Existing A3 (`kernel → ∅`) covers `kernel/authz/`. A4 (acyclic) covers the dependency chain C-04 → C-02 → C-01a.

## 9. Config

No new environment variables needed. The Casbin model path is baked into the repo (`kernel/authz/casbin_model.conf`). No external config for Phase 1.
