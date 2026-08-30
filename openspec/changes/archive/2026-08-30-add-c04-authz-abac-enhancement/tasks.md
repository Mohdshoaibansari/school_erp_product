# Tasks — C-04 AuthZ Kernel ABAC Enhancement

> **Change:** `add-c04-authz-abac-enhancement`
> **Capability:** C-04 Authorization / AuthZ Kernel
> **Status:** Ready for implementation (tasks only — completion is verified during apply)
> **Estimated total:** 28 tasks across 9 task groups

These tasks implement the delta spec `specs/authorization/spec.md` (REQ-AUTHZ-ABAC-01..07, M01..M05) and the design decisions D1–D14. Every task lists the requirement(s) it satisfies and the exact evidence a reviewer uses to confirm completion.

**Conventions**
- All commands run from `backend/` with the project venv active (`backend/.venv`). `python` = the venv interpreter.
- "Evidence" is checkable by a reviewer: a passing test, a file-import assertion, a grep that returns the expected result, or a Casbin ALLOW/DENY probe.
- Kernel boundary (AC-9, AC-14, AC-40, AC-41): `kernel/authz/` imports **no** `business/` symbol and **no** Teacher/Student/Parent/Homework ORM model. Enforced by Task 9.5.
- Do **not** implement batch `authorize_many()` (D14) — design the seam only.

---

## Group 1 — Authorization Contract Types (D1, D2)

### Task 1.1: Create Kernel-owned authorization types

**File:** `backend/kernel/authz/models/authorization_types.py` (new)

**Requirements:** REQ-AUTHZ-ABAC-01 (contract), D1, D13 (`AuthorizationAudit` dataclass)

**Change:**
Define five Kernel-owned `@dataclass` types with **no ORM imports**:
- `SubjectContext` (frozen): `user_id: str | None`, `roles: tuple[str, ...]`, `client_id`, `institution_id`, `user_tier`, `is_platform_owner`; plus a `from_tenant_context(ctx: TenantContext) -> SubjectContext` constructor that maps `TenantContext` fields (roles list → tuple).
- `ResourceContext` (frozen): `resource_type: str`, `resource_id: str | uuid.UUID | None`, `client_id`, `institution_id`, `data: Mapping[str, Any]` (generic domain-field extension point).
- `AuthorizationAttributes` (mutable): `values: dict[str, Any]`, `resolved_by: dict[str, str]` (attr→provider), `unresolved: set[str]` (fail-closed bookkeeping).
- `AuthorizationRequest` (frozen): `subject`, `resource`, `action: str`, `attributes: AuthorizationAttributes` (defaulted).
- `AuthorizationDecision` (frozen): `allowed: bool`, `reason: AuthorizationReasonCode`, `policy_id: str | None`, `audit: AuthorizationAudit | None`.
- `AuthorizationAudit` (frozen): `correlation_id`, `user_id`, `client_id`, `institution_id`, `action`, `resource_type`, `resource_id`, `roles`, `scope`, `policy_id`, `decision`, `reason` (D13 field set).

Note: `AuthorizationReasonCode` is imported from `reason_codes.py` (Task 1.2). To avoid a circular import, `reason_codes.py` must not import `authorization_types.py`; `AuthorizationDecision.reason` references the enum by type annotation only (use `TYPE_CHECKING` if needed).

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.models.authorization_types import SubjectContext, ResourceContext, AuthorizationAttributes, AuthorizationRequest, AuthorizationDecision, AuthorizationAudit
from kernel.tenant_context import TenantContext
import uuid, inspect
ctx = TenantContext(client_id=uuid.uuid4(), institution_id=None, user_id='u1', roles=['Teacher','HOD'], is_platform_owner=False)
s = SubjectContext.from_tenant_context(ctx)
assert s.roles == ('Teacher','HOD') and s.user_id == 'u1'
r = ResourceContext(resource_type='homework', resource_id='HW1', client_id=s.client_id, institution_id=None, data={'section_id':'4A'})
req = AuthorizationRequest(subject=s, resource=r, action='create')
assert req.attributes.values == {} and req.attributes.unresolved == set()
assert inspect.isclass(AuthorizationAudit) and 'correlation_id' in AuthorizationAudit.__dataclass_fields__
print('types OK')
"
```

---

### Task 1.2: Create structured reason-code enum

**File:** `backend/kernel/authz/models/reason_codes.py` (new)

**Requirements:** REQ-AUTHZ-ABAC-03 (reason codes), D2

**Change:**
Define `AuthorizationReasonCode` as a `str`-backed `enum.Enum` with the nine required codes **plus** two Kernel-internal refinements:
`MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED`, `NO_ROLES`, `UNRESOLVED_ATTRIBUTE`.

Also define the Kernel-owned static map `_ATTRIBUTE_DENY_REASON` (false-attribute → specific code) exactly as D2:
`is_self → NOT_SELF`, `is_parent_of_resource → NOT_PARENT_OF_RESOURCE`, `is_assigned_to_resource → NOT_ASSIGNED_TO_RESOURCE`, `is_class_teacher → NOT_ASSIGNED_TO_RESOURCE`, `is_subject_teacher → NOT_ASSIGNED_TO_RESOURCE`, default `ATTRIBUTE_CONDITION_FAILED`.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.models.reason_codes import AuthorizationReasonCode, _ATTRIBUTE_DENY_REASON
required = {'MISSING_PERMISSION','INVALID_SCOPE','TENANT_ACCESS_DENIED','INSTITUTION_ACCESS_DENIED','ATTRIBUTE_CONDITION_FAILED','NOT_ASSIGNED_TO_RESOURCE','NOT_SELF','NOT_PARENT_OF_RESOURCE','POLICY_DENIED'}
assert required <= {m.name for m in AuthorizationReasonCode}
assert {m.name for m in AuthorizationReasonCode} >= required | {'NO_ROLES','UNRESOLVED_ATTRIBUTE'}
assert _ATTRIBUTE_DENY_REASON['is_self'] is AuthorizationReasonCode.NOT_SELF
assert _ATTRIBUTE_DENY_REASON['is_subject_teacher'] is AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE
print('reason codes OK')
"
```

---

## Group 2 — Attribute Provider Contract + Registry (D3, D4, D5)

### Task 2.1: Create `AuthorizationAttributeProvider` ABC

**File:** `backend/kernel/authz/services/attribute_provider.py` (new)

**Requirements:** REQ-AUTHZ-ABAC-02 (provider contract), D3

**Change:**
Define the Kernel-owned abstract contract (imports **nothing** from `business/`):
```python
class AuthorizationAttributeProvider(ABC):
    name: str
    resource_types: frozenset[str]          # "*" = any resource type
    attributes: frozenset[str]
    @abstractmethod
    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]: ...
```
`resolve()` must be `async` and return only facts (a subset of `attributes`), never an allow/deny decision.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.attribute_provider import AuthorizationAttributeProvider
import inspect
assert inspect.isabstract(AuthorizationAttributeProvider)
assert 'resolve' in AuthorizationAttributeProvider.__abstractmethods__
assert inspect.iscoroutinefunction(AuthorizationAttributeProvider.resolve)
assert 'name' in AuthorizationAttributeProvider.__annotations__
print('provider ABC OK')
"
```

---

### Task 2.2: Create `ProviderRegistry` with deterministic ordering

**File:** `backend/kernel/authz/services/attribute_provider.py`

**Requirements:** REQ-AUTHZ-ABAC-02 (multiple providers, deterministic), D4

**Change:**
Add `ProviderRegistry` with:
- `register(provider)` — idempotent; **rejects** a duplicate `(resource_type, attribute)` claim with a startup error (fail-fast). Providers are held for the app lifetime and remain stateless.
- `providers_for(resource_type, attribute) -> AuthorizationAttributeProvider | None`.
- Deterministic execution order: registration order, then `provider.name` (stable across runs).

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.attribute_provider import ProviderRegistry, AuthorizationAttributeProvider
from kernel.authz.models.authorization_types import AuthorizationRequest
import asyncio
class P(AuthorizationAttributeProvider):
    name='p'; resource_types=frozenset({'*'}); attributes=frozenset({'a'})
    async def resolve(self, request): return {'a': True}
r = ProviderRegistry()
r.register(P())
assert r.providers_for('homework','a') is not None
try:
    r.register(P()); assert False, 'expected duplicate error'
except Exception:
    pass
print('registry OK')
"
```

---

### Task 2.3: Implement request-scoped caching + fail-closed `resolve_attributes`

**File:** `backend/kernel/authz/services/attribute_provider.py`

**Requirements:** REQ-AUTHZ-ABAC-02 (lazy/request-driven, pure-RBAC fallback), REQ-AUTHZ-ABAC-05 (fail-closed), D5

**Change:**
Implement `resolve_attributes(request, required: set[str]) -> AuthorizationAttributes`:
- For each required attribute, resolve via the provider registered for `(resource_type, attribute)`.
- Cache resolved values on the `AuthorizationAttributes`/pipeline dict for the **lifetime of one `authorize()` call** (no cross-request caching). A repeated `(resource_type, attribute)` hits the cache, not the provider.
- If an attribute has **no registered provider**, or a provider raises, record it in `attributes.unresolved` (fail-closed) — never treat it as permission.
- When `required` is empty, return an empty `AuthorizationAttributes` **without** invoking any provider (pure-RBAC fallback).

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.attribute_provider import ProviderRegistry, AuthorizationAttributeProvider
from kernel.authz.models.authorization_types import AuthorizationRequest, SubjectContext, ResourceContext
import asyncio
calls = {'n': 0}
class P(AuthorizationAttributeProvider):
    name='p'; resource_types=frozenset({'*'}); attributes=frozenset({'x'})
    async def resolve(self, request): calls['n'] += 1; return {'x': True}
r = ProviderRegistry(); r.register(P())
req = AuthorizationRequest(subject=SubjectContext(user_id='u',roles=('T',),client_id=None,institution_id=None,user_tier=None,is_platform_owner=False), resource=ResourceContext(resource_type='hw',resource_id='1',client_id=None,institution_id=None,data={}), action='create')
attrs = asyncio.run(r.resolve_attributes(req, {'x','x'}))
assert attrs.values['x'] is True and calls['n'] == 1, 'expected request-scoped cache'
# fail-closed: no provider for 'missing'
attrs2 = asyncio.run(r.resolve_attributes(req, {'missing'}))
assert 'missing' in attrs2.unresolved
# pure-RBAC fallback
attrs3 = asyncio.run(r.resolve_attributes(req, set()))
assert attrs3.values == {} and calls['n'] == 1
print('resolve_attributes OK')
"
```

---

## Group 3 — Casbin Model Extension + `match_attrs` (D8)

> **Atomicity note:** Tasks 3.1–3.3 form a single atomic unit (design §6 "Casbin model migration"). The 5-field `p` model, `match_attrs` registration, and the 5-arg test-helper updates must land together, or app startup / tests break.

### Task 3.1: Extend `casbin_model.conf` to 5-field policy + attribute matcher

**File:** `backend/kernel/authz/casbin_model.conf`

**Requirements:** REQ-AUTHZ-ABAC-M02 (model extension), D8

**Change:**
Change `[policy_definition]` from `p = sub, obj, act, scope` to `p = sub, obj, act, scope, attrs`. Leave `[request_definition]`, `[role_definition]`, `[policy_effect]` unchanged. Extend the matcher by appending `&& match_attrs(r.sub, p.attrs)`. The RBAC (`g(r.sub.role, p.sub)`), resource/action, and scope clauses stay **byte-for-byte identical** to today.

**Verify:**
```bash
cd backend && python -c "
import os, kernel.authz
p = os.path.join(os.path.dirname(kernel.authz.__file__), 'casbin_model.conf')
txt = open(p).read()
assert 'p = sub, obj, act, scope, attrs' in txt
assert 'match_attrs(r.sub, p.attrs)' in txt
assert 'g(r.sub.role, p.sub)' in txt
print('model file OK')
"
```

---

### Task 3.2: Define `match_attrs` and register it at enforcer creation

**Files:**
- `backend/kernel/authz/services/authorization_service.py` (new — this task adds `match_attrs` only; `AuthorizationService` is added in Group 5)
- `backend/kernel/app_factory.py`

**Requirements:** REQ-AUTHZ-ABAC-M02, D8

**Change:**
Define the custom Casbin function (truthiness lookup, **no** `eval`, **no** rules engine):
```python
def match_attrs(sub: dict, attrs: str) -> bool:
    if not attrs or attrs in ("*", ""):
        return True
    return all(bool(sub.get(a)) for a in attrs.split(","))
```
Register it on the enforcer in `_create_casbin_enforcer` immediately after `casbin.Enforcer(model_path)` via `enforcer.add_function("match_attrs", match_attrs)`. (Confirmed: Casbin passes `r.sub` to `match_attrs` as a `dict`, so `sub.get(a)` is correct.)

**Verify:**
```bash
cd backend && python -c "
import casbin, os, kernel.authz
from kernel.authz.services.authorization_service import match_attrs
p = os.path.join(os.path.dirname(kernel.authz.__file__), 'casbin_model.conf')
e = casbin.Enforcer(p)
e.add_function('match_attrs', match_attrs)
assert match_attrs({'a':True}, 'a') is True
assert match_attrs({'a':False}, 'a') is False
assert match_attrs({}, '') is True
print('match_attrs OK')
"
```

---

### Task 3.3: Migrate test enforcer builders to 5-arg policies + register `match_attrs`

**Files:**
- `backend/tests/test_c04_authz.py` (`_register_c01_policies`, `_register_c04_test_policies`, `_build_test_enforcer`)
- `backend/tests/test_casbin_permissions.py` (`register_policies`, `enforcer` fixture, `casbin_model_path`-based enforcer builders)

**Requirements:** REQ-AUTHZ-ABAC-M02 (scope matchers unchanged — regression), D8 migration

**Change:**
Every `enforcer.add_policy(role, resource, action, scope)` in these helpers becomes `add_policy(role, resource, action, scope, "")` (5-arg). Every enforcer built directly from `casbin_model.conf` registers `match_attrs` via `add_function`. No test assertion values change — only the policy arity + function registration.

**Verify:**
```bash
cd backend && python -m pytest tests/test_casbin_permissions.py tests/test_c04_authz.py -q 2>&1 | tail -20
```

---

## Group 4 — Policy Loader + Conditional Policies + Catalog (D9)

### Task 4.1: Migrate policy loader to 5-arg policies + non-conditional catalog

**File:** `backend/kernel/authz/services/policy_loader.py`

**Requirements:** REQ-AUTHZ-ABAC-M04 (non-conditional tuples unchanged), D9

**Change:**
Evolve the module state to hold two catalogs:
- `_non_conditional: dict[str, list[tuple[str, str, str]]]` — role → `[(resource, action, scope)]` (populated from the DB query, unchanged SQL).
- `_conditional: dict[str, list[tuple[str, str, str, str]]]` — role → `[(resource, action, scope, attrs)]` (added in Task 4.2).
Update `register_policies_from_map` to `enforcer.add_policy(role_name, resource, action, scope, "")` (5-arg) and populate `_non_conditional`.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services import policy_loader as pl
pl._non_conditional.clear()
pl._non_conditional['Teacher'] = [('homework','create','institution')]
import casbin, os, kernel.authz
from kernel.authz.services.authorization_service import match_attrs
p = os.path.join(os.path.dirname(kernel.authz.__file__), 'casbin_model.conf')
e = casbin.Enforcer(p); e.add_function('match_attrs', match_attrs)
pl.register_policies_from_map.__globals__['_permission_map'] = pl._non_conditional
# direct probe of 5-arg registration shape
e.add_policy('Teacher','homework','create','institution','')
assert len(e.get_policy()[0]) == 5
print('loader 5-arg OK')
"
```

---

### Task 4.2: Add `register_conditional_policy` + conditional catalog

**File:** `backend/kernel/authz/services/policy_loader.py`

**Requirements:** REQ-AUTHZ-ABAC-M04 (conditional policies declare required attributes), D9

**Change:**
Add:
```python
def register_conditional_policy(enforcer, role, resource, action, scope, required_attrs: Sequence[str]) -> None:
    enforcer.add_policy(role, resource, action, scope, ",".join(required_attrs))
    _conditional.setdefault(role, []).append((resource, action, scope, ",".join(required_attrs)))
```
This is **code-driven** (no DB schema change; `permission`/`role_permission` tables unchanged).

**Verify:**
```bash
cd backend && python -c "
import casbin, os, kernel.authz
from kernel.authz.services import policy_loader as pl
from kernel.authz.services.authorization_service import match_attrs
p = os.path.join(os.path.dirname(kernel.authz.__file__), 'casbin_model.conf')
e = casbin.Enforcer(p); e.add_function('match_attrs', match_attrs)
pl._conditional.clear()
pl.register_conditional_policy(e, 'Teacher', 'homework', 'create', 'institution', ['is_subject_teacher'])
assert ('homework','create','institution','is_subject_teacher') in pl._conditional['Teacher']
assert e.get_policy()[-1] == ['Teacher','homework','create','institution','is_subject_teacher']
print('conditional policy OK')
"
```

---

### Task 4.3: Add catalog query helpers (required attrs, permission, scopes)

**File:** `backend/kernel/authz/services/policy_loader.py`

**Requirements:** REQ-AUTHZ-ABAC-02 (lazy required-attribute determination), REQ-AUTHZ-ABAC-M04, D9

**Change:**
Add the catalog query helpers used by `AuthorizationService`:
- `required_attributes(roles, resource, action) -> set[str]` — union of `attrs` over all conditional entries matching any role × `(resource, action)`.
- `has_permission(roles, resource, action) -> bool` — true if any role has `(resource, action)` in either catalog.
- `matching_scopes(roles, resource, action, sub_client, sub_inst, obj_client, obj_inst) -> list[str]` — the scopes (from `_non_conditional` + `_conditional`) that match the permission and whose tenant/institution constraints hold. (Feeds the reason discriminator; **never** grants.)

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services import policy_loader as pl
pl._conditional.clear(); pl._non_conditional.clear()
pl._non_conditional['Teacher'] = [('homework','read','institution')]
pl._conditional['Teacher'] = [('homework','create','institution','is_subject_teacher')]
pl._conditional['HOD'] = [('homework','create','institution','is_class_teacher')]
assert pl.required_attributes(['Teacher','HOD'],'homework','create') == {'is_subject_teacher','is_class_teacher'}
assert pl.has_permission(['Teacher'],'homework','create') is True
assert pl.has_permission(['Teacher'],'homework','delete') is False
print('catalog helpers OK')
"
```

---

### Task 4.4: Add manifest policy-registration hook + startup smoke check

**Files:**
- `backend/kernel/authz/manifest.py`
- `backend/kernel/app_factory.py`

**Requirements:** REQ-AUTHZ-ABAC-M04, D9 (registration path), D12 (wiring)

**Change:**
Add a hook `register_authorization_policies(enforcer)` to the C-04 manifest, invoked by `_create_casbin_enforcer` after the DB loader runs. In this iteration the hook is a placeholder that future business modules (Phase 7) will extend via their own manifests; the C-04 manifest's hook calls `register_policies_from_map(enforcer)` (existing behavior preserved) so the DB-loaded non-conditional policies continue to flow into the enforcer.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.manifest import manifest
import inspect
assert hasattr(manifest, 'register_casbin_policies')
print('manifest hook OK')
"
```
Plus a startup smoke check that the app-built enforcer is non-empty and 5-tuples:
```bash
cd backend && python -c "
import os, kernel.authz
from kernel.authz.services.policy_loader import register_policies_from_map, load_permission_map
# (run with DATABASE_URL available) — policies must be 5-tuples after migration
from kernel.app_factory import _create_casbin_enforcer
print('smoke: run full app enforcer build in Task 9.6')
"
```

---

## Group 5 — `AuthorizationService` Pipeline (D6, D7, D14)

### Task 5.1: Implement `authorize()` pipeline with restrictive ordering

**File:** `backend/kernel/authz/services/authorization_service.py`

**Requirements:** REQ-AUTHZ-ABAC-04 (pipeline + restrictive ordering), REQ-AUTHZ-ABAC-05 (fail-closed, no client-supplied trust, cross-client/institution boundary, RLS defense-in-depth), D6

**Change:**
Implement `AuthorizationService.authorize(request) -> AuthorizationDecision` in the exact order of D6:
1. Platform Owner bypass (`is_platform_owner` or `"platform_owner" in roles`) → ALLOW (reason `ALLOWED`).
2. No roles → DENY(`NO_ROLES`).
3. Determine `required` from the catalog (`required_attributes`).
4. If `required` non-empty, `resolve_attributes`; if `attributes.unresolved` → DENY(`UNRESOLVED_ATTRIBUTE`).
5. `_enforce(request)` (Casbin, all roles — Task 5.2).
6. On ALLOW → return `ALLOWED` with `policy_id`. On DENY → `_classify_denial` (Task 5.3).
7. Emit audit record (Task 8.1) on every decision.

ABAC is **restrictive**: a user with no matching permission is denied `MISSING_PERMISSION` **before** any provider is invoked. ABAC never grants what RBAC denies. The subject/resource contexts are built only from server-side sources; client-sent attribute fields are never routed into `AuthorizationAttributes`. Authorization success performs **no** RLS change (RLS remains defense-in-depth).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "pipeline" 2>&1 | tail -20
```

---

### Task 5.2: Implement multi-role `_enforce` (loop per role)

**File:** `backend/kernel/authz/services/authorization_service.py`

**Requirements:** REQ-AUTHZ-ABAC-M03 (all roles, any valid role satisfies RBAC), D7; REMOVED single-role (`roles[0]`) behavior

**Change:**
Implement `_enforce(request) -> tuple[bool, str | None]` that loops `enforcer.enforce()` per role (attributes injected into the subject once, before the loop) and returns on the **first** ALLOW. This replaces the `roles[0]` behavior removed from `dependencies.py` (Task 6.1). Do **not** pass `roles[]` into the model — keep the `g(r.sub.role, p.sub)` matcher untouched.

**Verify:**
```bash
cd backend && python -c "
# multi-role: HOD lacks homework.create, Teacher has it -> ALLOW
import casbin, os, kernel.authz
from kernel.authz.services.authorization_service import match_attrs
p = os.path.join(os.path.dirname(kernel.authz.__file__), 'casbin_model.conf')
e = casbin.Enforcer(p); e.add_function('match_attrs', match_attrs)
e.add_role_for_user('Teacher','Teacher'); e.add_role_for_user('HOD','HOD')
e.add_policy('Teacher','homework','create','institution','')
sub = {'role':'HOD','client_id':'c1','institution_id':'i1'}
print('roles[0]=HOD alone denied:', e.enforce(sub, {'name':'homework','client_id':'c1','institution_id':'i1'}, 'create'))
sub['role']='Teacher'
print('roles[0]=Teacher allowed:', e.enforce(sub, {'name':'homework','client_id':'c1','institution_id':'i1'}, 'create'))
"
```

---

### Task 5.3: Implement reason discriminator `_classify_denial`

**File:** `backend/kernel/authz/services/authorization_service.py`

**Requirements:** REQ-AUTHZ-ABAC-03, REQ-AUTHZ-ABAC-04, D9

**Change:**
Implement `_classify_denial(request) -> AuthorizationReasonCode` following D9 order (runs **only on DENY**; never grants):
1. No role has `(resource, action)` in either catalog → `MISSING_PERMISSION`.
2. Else no matching scope → `TENANT_ACCESS_DENIED` / `INSTITUTION_ACCESS_DENIED` / `INVALID_SCOPE` per D9.
3. Else an attribute condition failed → `_ATTRIBUTE_DENY_REASON` lookup (default `ATTRIBUTE_CONDITION_FAILED`).
4. Defensive fallback → `POLICY_DENIED`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "reason" 2>&1 | tail -20
```

---

### Task 5.4: Design the `authorize_many()` batch seam (NOT implemented)

**File:** `backend/kernel/authz/services/authorization_service.py` (docstring/comment + signature only)

**Requirements:** REQ-AUTHZ-ABAC-04 (batch designed, not implemented), D14

**Change:**
Add a documented seam (e.g., a commented `# async def authorize_many(self, requests) -> list[AuthorizationDecision]:` or an `__init_subclass__`-free TODO block) capturing D14's contract: compute the union of required attributes across all requests in one pass; resolve each distinct `(resource_type, attribute)` once (batch-wide cache); group enforcement by subject. **No** batch API, cache, or tests are shipped.

**Verify:**
```bash
cd backend && grep -n "authorize_many" kernel/authz/services/authorization_service.py && ! grep -n "async def authorize_many" kernel/authz/services/authorization_service.py
```

---

## Group 6 — `require_permission` / `check_permission` Rewrite (D11)

### Task 6.1: Rewrite both entry points as thin async adapters over `AuthorizationService`

**File:** `backend/kernel/authz/dependencies.py`

**Requirements:** REQ-AUTHZ-ABAC-M01 (extend to pipeline, structured 403, Platform Owner bypass retained), D11, D7 (remove `roles[0]`), D10 (remove hardcoded `owner_id` bypass)

**Change:**
- `require_permission(resource, action, *, obj_client_id=None, obj_institution_id=None, owner_id=None)` becomes an **async** FastAPI dependency: build an `AuthorizationRequest` (subject from `TenantContext`, resource from explicit object attrs with ctx fallback), `await svc.authorize(request)`, and on denial raise a **structured** 403.
- `check_permission(ctx, enforcer, resource, action, *, ...)` becomes `async def`; same thin-adapter logic, returns `None` on allow, raises structured 403 on deny.
- Remove `_check_impl`'s `roles[0]` subject construction and the hardcoded `owner_id` self-access bypass (replaced by the `is_self` attribute — Task 7.1).
- Structured 403: `HTTPException(403, detail={"code": decision.reason.value, "message": "Permission denied"})` — exposes the code, never policy internals.
- Platform Owner bypass is **retained** (early return in `authorize()` step 1); no `obj_*` signature change.

**Verify:**
```bash
cd backend && python -c "
import inspect
from kernel.authz.dependencies import require_permission, check_permission
sig = inspect.signature(check_permission)
assert 'obj_client_id' in sig.parameters and 'owner_id' in sig.parameters
assert inspect.iscoroutinefunction(check_permission), 'check_permission must be async'
print('deps signature OK')
"
```

---

### Task 6.2: Migrate all inline `check_permission` call sites to `async`/`await`

**Files:** `backend/business/tenant_institution/routes/client_portal.py` (8 sites), `backend/kernel/user/routes/identifiers.py` (1), `backend/kernel/user/routes/roles.py` (1), `backend/kernel/user/routes/users.py` (4)

**Requirements:** REQ-AUTHZ-ABAC-M01, D11 (async migration)

**Change:**
Convert every handler that calls `check_permission(...)` inline to `async def` and `await check_permission(...)`. The 14 sites are:
- `client_portal.py`: institution read / update / transition_lifecycle (×2: transition + go-live) / org_unit move / archive / reactivate / reorder.
- `identifiers.py`: `delete_identifier`.
- `roles.py`: `delete_role_assignment`.
- `users.py`: `get_user`, `update_user`, `delete_user`, `transition_user_lifecycle`.

Note: the design's file impact map (§2) omitted `users.py`; those 4 sites are included here because `check_permission` is now async. No conditional policies are registered for these production routes in this iteration, so no async provider I/O is added — the pipeline runs the synchronous Casbin path.

**Verify:**
```bash
cd backend && python -c "
import ast
for f in ['business/tenant_institution/routes/client_portal.py','kernel/user/routes/identifiers.py','kernel/user/routes/roles.py','kernel/user/routes/users.py']:
    src = open(f).read()
    assert 'await check_permission(' in src, f
    # every async-def handler containing check_permission must await it
    tree = ast.parse(src)
    print(f, 'has await check_permission:', src.count('await check_permission('))
"
```

---

## Group 7 — Ownership Generalization to `is_self` (D10)

### Task 7.1: Add built-in `IsSelfAttributeProvider` and register it at startup

**Files:**
- `backend/kernel/authz/services/attribute_provider.py`
- `backend/kernel/authz/manifest.py` (new `register_attribute_providers` hook)

**Requirements:** REQ-AUTHZ-ABAC-M05 (owner_id → is_self), D10, D12

**Change:**
Add the Kernel-owned (not business-module) provider:
```python
class IsSelfAttributeProvider(AuthorizationAttributeProvider):
    name = "authz.is_self"
    resource_types = frozenset({"*"})
    attributes = frozenset({"is_self"})
    async def resolve(self, request):
        owner_id = request.resource.data.get("owner_id") or request.resource.data.get("user_id")
        return {"is_self": bool(owner_id and request.subject.user_id and str(request.subject.user_id) == str(owner_id))}
```
Add a manifest hook `register_attribute_providers(registry)` (optional, default no-op) and register `IsSelfAttributeProvider` in the C-04 manifest. `app_factory` invokes the hook before the service wiring completes.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.attribute_provider import IsSelfAttributeProvider
from kernel.authz.models.authorization_types import AuthorizationRequest, SubjectContext, ResourceContext
import asyncio
p = IsSelfAttributeProvider()
req = AuthorizationRequest(subject=SubjectContext(user_id='u1',roles=('Student',),client_id=None,institution_id=None,user_tier=None,is_platform_owner=False), resource=ResourceContext(resource_type='attendance',resource_id='a1',client_id=None,institution_id=None,data={'owner_id':'u1'}), action='read')
assert asyncio.run(p.resolve(req)) == {'is_self': True}
req2 = AuthorizationRequest(subject=SubjectContext(user_id='u2',roles=('Student',),client_id=None,institution_id=None,user_tier=None,is_platform_owner=False), resource=ResourceContext(resource_type='attendance',resource_id='a1',client_id=None,institution_id=None,data={'owner_id':'u1'}), action='read')
assert asyncio.run(p.resolve(req2)) == {'is_self': False}
print('is_self provider OK')
"
```

---

### Task 7.2: Route `owner_id` through `ResourceContext.data` (backward compat)

**File:** `backend/kernel/authz/dependencies.py`

**Requirements:** REQ-AUTHZ-ABAC-M05 (owner_id preserved, semantics generalized), D10

**Change:**
In the `_build_request` helper, map the `owner_id` keyword argument to `ResourceContext.data["owner_id"]`. Keep the `owner_id` parameter in both entry-point signatures (zero production callers today). Document that self-access is now gated by Casbin via `is_self` **alongside** the permission, not by an identity-only bypass.

**Verify:**
```bash
cd backend && python -c "
import inspect
from kernel.authz.dependencies import require_permission
assert 'owner_id' in inspect.signature(require_permission).parameters
print('owner_id backward compat OK')
"
```

---

## Group 8 — Observability (D13)

### Task 8.1: Emit structured decision audit + redact attribute values

**Files:**
- `backend/kernel/authz/services/authorization_service.py`

**Requirements:** REQ-AUTHZ-ABAC-06 (observability + audit context), D13

**Change:**
Populate `AuthorizationAudit` on every decision with the D13 field set (`correlation_id`, `user_id`, `client_id`, `institution_id`, `action`, `resource_type`, `resource_id`, `roles`, `scope`, `policy_id`, `decision`, `reason`) and attach it to `AuthorizationDecision.audit`. Emit via the `kernel.authz` logger (`info` for allow, `warning` for deny). **Redact** domain attribute values: log the set of resolved attribute names + `resolved_by` provenance, but omit/redact raw values by default. Thread `correlation_id` from request context (fallback: generated UUID).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "audit" 2>&1 | tail -20
```

---

## Group 9 — Tests (D14 seam only; REQ-AUTHZ-ABAC-07)

### Task 9.1: Add synthetic-attribute provider fixture (no business code)

**File:** `backend/tests/test_authz_abac.py` (new)

**Requirements:** REQ-AUTHZ-ABAC-07 (synthetic ALLOW/DENY), AC-46..AC-48

**Change:**
Add a test-only `SyntheticTeacherProvider` that returns `is_subject_teacher` from a fixed map keyed by `request.resource.data["section_id"]`, plus a test-registered conditional policy `(Teacher, homework, create, institution, "is_subject_teacher")`. No Teacher/Homework/Academic/Student business implementation is imported into the Kernel.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "synthetic" 2>&1 | tail -20
```

---

### Task 9.2: Add pipeline unit tests

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-ABAC-07, REQ-AUTHZ-ABAC-04, AC-43

**Change:**
Add unit tests covering: single role allow/deny; multiple roles `[HOD, Teacher]` where only `Teacher` holds the permission → ALLOW; missing permission → `MISSING_PERMISSION`; tenant scope mismatch → `TENANT_ACCESS_DENIED`; institution mismatch → `INSTITUTION_ACCESS_DENIED`; successful ABAC (`is_subject_teacher=true` → ALLOW); failed ABAC (`is_subject_teacher=false` → DENY `NOT_ASSIGNED_TO_RESOURCE`); missing required attribute (no provider) → DENY `UNRESOLVED_ATTRIBUTE`; multiple/conflicting assignments; pure-RBAC fallback (provider not invoked when no attrs required).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "unit" 2>&1 | tail -30
```

---

### Task 9.3: Add security tests

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-ABAC-05 (security invariants), AC-44

**Change:**
Add security tests: Client A → Client B resource → DENY `TENANT_ACCESS_DENIED`; Institution A → Institution B → DENY `INSTITUTION_ACCESS_DENIED`; teacher assigned to 1A → 1A ALLOW, → 1B DENY; student S1 → S1 attendance ALLOW, S1 → S2 DENY `NOT_SELF`; client-supplied `is_class_teacher: true` in the body is **ignored** (attribute resolved server-side).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "security" 2>&1 | tail -30
```

---

### Task 9.4: Run regression tests (existing RBAC/scope unchanged)

**Files:** `backend/tests/test_c04_authz.py`, `backend/tests/test_casbin_permissions.py`

**Requirements:** REQ-AUTHZ-ABAC-M02 (scope matchers unchanged), AC-45

**Change:**
Confirm existing `test_c04_authz.py` and `test_casbin_permissions.py` pass unchanged (beyond the Task 3.3 arity/registration migration). Platform Owner bypass still returns before the pipeline; `require_permission`/`check_permission` still deny with 403 (now structured `code`) and still allow on grant.

**Verify:**
```bash
cd backend && python -m pytest tests/test_c04_authz.py tests/test_casbin_permissions.py -v 2>&1 | tail -40
```

---

### Task 9.5: Add dependency-direction static check

**File:** `backend/tests/test_authz_abac.py` (or a `tests/test_authz_kernel_boundary.py`)

**Requirements:** AC-9, AC-14, AC-40, AC-41 (Kernel boundary)

**Change:**
Add a static check (import analysis / grep over `kernel/authz/`) asserting: `kernel/authz/` imports no `business/` symbol and no Teacher/Student/Parent/Homework ORM model; `business/` modules import only from `kernel/authz/` (contract direction).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "boundary" 2>&1 | tail -20
```

---

### Task 9.6: Run the full backend test suite

**File:** N/A

**Requirements:** AC-43..AC-45 (full validation)

**Change:**
Run the full backend test suite and confirm no regressions. Confirm the app-built enforcer (via `_create_casbin_enforcer`) is non-empty with 5-tuple policies (model-migration smoke check, design §6).

**Verify:**
```bash
cd backend && python -m pytest tests/ -q 2>&1 | tail -30
```

---

## Summary

| Group | Tasks | Key Deliverable |
|---|---|---|
| 1 — Contract types | 2 | `authorization_types.py`, `reason_codes.py` (REQ-AUTHZ-ABAC-01, 03) |
| 2 — Provider contract + registry | 3 | `attribute_provider.py` ABC + `ProviderRegistry` + fail-closed cache (REQ-AUTHZ-ABAC-02, 05) |
| 3 — Casbin model + `match_attrs` | 3 | 5-field `p`, `match_attrs` registration, test-helper migration (REQ-AUTHZ-ABAC-M02) |
| 4 — Policy loader + conditional policies | 4 | 5-arg loader, `register_conditional_policy`, catalog helpers, manifest hook (REQ-AUTHZ-ABAC-M04) |
| 5 — `AuthorizationService` pipeline | 4 | `authorize()` restrictive pipeline, multi-role loop, reason discriminator, batch seam (REQ-AUTHZ-ABAC-04, M03) |
| 6 — `require_permission` rewrite | 2 | thin async adapters + structured 403 + async route migration (REQ-AUTHZ-ABAC-M01) |
| 7 — Ownership generalization | 2 | `IsSelfAttributeProvider` + `owner_id` → `is_self` (REQ-AUTHZ-ABAC-M05) |
| 8 — Observability | 1 | structured audit + redaction (REQ-AUTHZ-ABAC-06) |
| 9 — Tests | 6 | synthetic/unit/security/regression/boundary/full-suite (REQ-AUTHZ-ABAC-07) |
| **Total** | **28** | |

### Dependency Order

```
Group 1 (types) ─► Group 2 (providers) ─► Group 3 (model + match_attrs, atomic)
                                          └─► Group 4 (loader, atomic with 3)
Group 1+2+3+4 ─► Group 5 (pipeline) ─► Group 6 (adapters) ─► Group 7 (is_self) ─► Group 8 (observability)
Group 5+6+7+8 ─► Group 9 (tests)
```

- Groups 3 and 4 are **atomic** with respect to app startup (5-field model + `match_attrs` registration + 5-arg loader + test-helper migration land together).
- Group 5 depends on the catalog helpers from Group 4.
- Group 6 depends on `AuthorizationService` (Group 5).
- Group 7 (`is_self`) depends on the provider contract (Group 2) and the adapter mapping (Group 6).
