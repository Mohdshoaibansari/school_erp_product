# Tasks — AuthZ Kernel ABAC Enforcement & Platform Owner Security Fix

> **Change:** `fix-c04-authz-abac-enforcement`
> **Capability:** C-04 Authorization / AuthZ Kernel
> **Phase:** sdd-stack tasks (tasks only — completion is verified during apply)
> **Status:** Ready for implementation
> **Estimated total:** 22 tasks across 12 task groups (+ 1 auxiliary archive-time action)

These tasks implement the delta spec `specs/authorization/spec.md` (`REQ-AUTHZ-FIX-ABAC-01`, `REQ-AUTHZ-FIX-PO-01`, `REQ-AUTHZ-FIX-REG-01`, `REQ-AUTHZ-FIX-PID-01`, `REQ-AUTHZ-FIX-TEST-01..03`) and the design decisions D1–D12. Every task lists the requirement(s) it satisfies and the exact evidence a reviewer uses to confirm completion (test name + assertion, migration name, file + function).

**Conventions**
- All commands run from `backend/` with the project venv active (`backend/.venv`). `python` = the venv interpreter.
- "Evidence" is checkable: a passing test name, a file/function signature assertion, a grep that returns the expected result, an Alembic migration id, or a Casbin ALLOW/DENY probe.
- Kernel boundary invariant (repeat of the base change AC-9/AC-14): `kernel/authz/` imports **no** `business/` symbol and **no** Teacher/Student/Parent/Homework/Attendance ORM model. Enforced in Group 12.
- **No RLS changes.** No `kernel/db.py` session-var edit, no RLS policy edit. If a discovered regression requires one, stop and log it as a risk (R-noted) — do not silently expand scope.
- Backward compat hard constraints (do not break): `require_permission` callers unchanged (no signature change in this change); `AuthorizationDecision` shape unchanged; `.routes` call sites (`obj_client_id`/`obj_institution_id` fallback) unchanged; `casbin_model.conf` unchanged.

**Design-decision mapping used by the groups below** (design `design.md` decision letters are retained; the group numbering follows the task-breakdown mandate):

| Task Group | Design decision | Delta requirements |
|---|---|---|
| Group 1 | D1 (`match_attrs` strict) | ABAC-01 |
| Group 2 | D2 (raw boundary tests) | ABAC-01, TEST-01 |
| Group 3 | D3 (stub fix + pipeline regression) | ABAC-01, TEST-01 |
| Group 4 | D4a (service Step-1 removal) + D5 (service-side normalization) | PO-01 |
| Group 5 | D4b (legacy removal) + D5 (legacy normalization) | PO-01 |
| Group 6 | D6 (PO permissions migration) | PO-01 |
| Group 7 | D8 (production registration) | REG-01 |
| Group 8 | D9 (policy identity) | PID-01 |
| Group 9 | D7 + D12-inventory (PO security tests + app-level updates) | TEST-02 |
| Group 10 | D3 (provider-failure fail-closed) | TEST-03 |
| Group 11 | D2/TEST-01 case 4 (scope regression) | TEST-01 |
| Group 12 | D12 (full-suite + boundary static checks) | all |
| Aux | D11 (archive-time spec amendment) | PO-01 (spec consistency) |

---

## Group 1 — `match_attrs` strict-boolean semantics (D1)

### Task 1.1: Tighten `match_attrs` to strict boolean identity + provider contract doc

**File:** `backend/kernel/authz/services/authorization_service.py` (function `match_attrs`, ~L41–55)

**Requirements:** REQ-AUTHZ-FIX-ABAC-01

**Change:**
Change the matcher helper from Python truthiness to strict boolean identity:

```python
def match_attrs(sub: dict, attrs: str) -> bool:
    if not attrs or attrs in ("*", ""):
        return True
    return all(sub.get(a) is True for a in attrs.split(","))
```

No-attribute / `*` / `""` handling is unchanged. This closes the string-`"false"` ALLOW vector and makes all non-`True` values (including `False`, `None`, missing key, `""`, `1`, `"true"`, `numpy.bool_`) fail closed. Add an explicit provider-contract docstring note on `AuthorizationAttributeProvider.resolve` (`backend/kernel/authz/services/attribute_provider.py`): providers MUST return genuine Python `bool`; any non-`True` value is treated as a denial. Update the `match_attrs` docstring with the semantics table.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.services.authorization_service import match_attrs
assert match_attrs({'is_subject_teacher': True}, 'is_subject_teacher') is True
assert match_attrs({'is_subject_teacher': 'false'}, 'is_subject_teacher') is False, 'string false MUST be denied'
assert match_attrs({'is_subject_teacher': 'true'}, 'is_subject_teacher') is False, 'string true fail-closed'
assert match_attrs({'is_subject_teacher': 1}, 'is_subject_teacher') is False, 'int fail-closed'
assert match_attrs({'is_subject_teacher': False}, 'is_subject_teacher') is False
assert match_attrs({}, 'is_subject_teacher') is False, 'missing fail-closed'
assert match_attrs({}, '') is True and match_attrs({}, '*') is True
print('match_attrs strict OK')
"
```
Pluss the existing green suite must not flip (all providers return real bools):
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q 2>&1 | tail -5
```

---

## Group 2 — Raw enforcer-boundary ABAC tests (D2)

### Task 2.1: Add `TestRawEnforcerBoundary` calling `enforcer.enforce()` directly

**File:** `backend/tests/test_authz_abac.py` (new class `TestRawEnforcerBoundary`; reuse module-level `_build_enforcer()` which already calls `add_function("match_attrs", ...)`)

**Requirements:** REQ-AUTHZ-FIX-ABAC-01, REQ-AUTHZ-FIX-TEST-01

**Change:**
Add a helper and four tests that invoke **the Casbin enforcer boundary directly** — no `AuthorizationService`, no Python pre-check — proving the matcher path itself:
- `_po_boundary_enforcer()` → `_build_enforcer()`, add roles `Teacher`/`Teacher`, add `("Teacher","homework","create","institution","is_subject_teacher")` and the no-attr control `("Teacher","homework","read","institution","")`.
- `test_attr_true_allows` — sub `{"role":"Teacher","client_id":CID,"institution_id":IID,"is_subject_teacher":True}`, obj `{"name":"homework",...}` → `assert enforcer.enforce(sub, obj, "create") is True`.
- `test_attr_false_denies` — same sub with `"is_subject_teacher": False` → `assert ... is False` (Casbin-level DENY, no Python pre-check).
- `test_attr_missing_denies` — sub **without** the `is_subject_teacher` key → `assert ... is False` (`None is True` → matcher false).
- `test_no_attr_falls_back_to_rbac_scope` — no domain attrs, the `attrs=""` policy, matching institution scope → `assert ... is True`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "TestRawEnforcerBoundary" 2>&1 | tail -12
```
Expected: `4 passed`. Each assertion named above pins the matcher clause; a regression that drops/neuters `match_attrs` fails loudly here.

---

## Group 3 — Fix the vacuous `test_failed_abac` stub + pipeline ABAC regression (D3)

### Task 3.1: Replace the vacuous stub with a real pipeline assertion

**File:** `backend/tests/test_authz_abac.py` (method `test_failed_abac`, ~L372)

**Requirements:** REQ-AUTHZ-FIX-ABAC-01, REQ-AUTHZ-FIX-TEST-01

**Change:**
Rewrite `test_failed_abac` to invoke the real pipeline with `is_subject_teacher=false`. Follow the `test_synthetic_deny_with_conditional_policy` shape — **do not** call `_setup_base_policies` (the non-conditional fallback would defeat the ABAC check). New body: build enforcer, register conditional policy `pl._conditional["Teacher"] = [("homework","create","institution","is_subject_teacher")]`, build service with `SyntheticTeacherProvider`, request section_id `"5A"` (→ `False`), `decision = asyncio.run(svc.authorize(req))`, then `assert decision.allowed is False` and `assert decision.reason == AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "test_failed_abac" 2>&1 | tail -8
```
Evidence that it is no longer vacuous: grep shows an explicit `authorize(` call and a real `assert` on `allowed is False` / a reason code inside the test body.

### Task 3.2: Add `test_abac_never_bypasses_rbac`

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-FIX-TEST-01 (case 5)

**Change:**
Add a pipeline test proving ABAC never grants what RBAC denies: a required attribute resolves `true` (`SyntheticTeacherProvider` returns `is_subject_teacher=True`) but the requesting role has **no** permission for the `(resource, action)` → `assert decision.allowed is False` and `assert decision.reason == AuthorizationReasonCode.MISSING_PERMISSION`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "test_abac_never_bypasses_rbac" 2>&1 | tail -8
```

---

## Group 4 — Remove PO Step-1 bypass in `authorization_service` + service-side role normalization (D4a/D5)

### Task 4.1: Remove the Step-1 Platform Owner short-circuit from `authorize()`

**File:** `backend/kernel/authz/services/authorization_service.py` (`authorize`, ~L98–107)

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change:**
Delete the Step-1 block that returns `ALLOWED` when `request.subject.is_platform_owner or "platform_owner" in request.subject.roles` **before** the no-roles check. `authorize()` now begins at the no-roles check (DENY `NO_ROLES`). Update the docstring pipeline list (Step 1 removed) to state PO flows Permission → Scope → ABAC → Casbin.

**Verify (static):**
```bash
cd backend && ! grep -nE "is_platform_owner.*LLOW|Platform owner bypass" kernel/authz/services/authorization_service.py \
  && echo "no PO short-circuit in service"
```

### Task 4.2: Derive the PO effective role label in `SubjectContext.from_tenant_context`

**File:** `backend/kernel/authz/models/authorization_types.py` (`SubjectContext.from_tenant_context`, ~L38)

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change:**
When `ctx.is_platform_owner` and `"platform_owner" not in roles`, prepend `("platform_owner",)` to the derived roles tuple. Comment explains this is role derivation (NOT a grant): grants still come only from `role_permission` rows evaluated by the full pipeline.

**Verify:**
```bash
cd backend && python -c "
from kernel.authz.models.authorization_types import SubjectContext
from kernel.tenant_context import TenantContext
import uuid
ctx = TenantContext(client_id=uuid.uuid4(), institution_id=None, user_id='po1', roles=[], is_platform_owner=True)
s = SubjectContext.from_tenant_context(ctx)
assert s.roles == ('platform_owner',), s.roles
ctx2 = TenantContext(client_id=uuid.uuid4(), institution_id=None, user_id='u', roles=['Teacher'], is_platform_owner=False)
assert SubjectContext.from_tenant_context(ctx2).roles == ('Teacher',)
print('PO role normalization OK')
"
```

---

## Group 5 — Remove legacy PO bypass in `dependencies` + legacy-side normalization (D4b/D5)

### Task 5.1: Remove the legacy PO bypass block and add PO normalization in `_check_impl_legacy`

**File:** `backend/kernel/authz/dependencies.py` (`_check_impl_legacy`, ~L209–231)

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change:**
Delete the `# Platform owner bypass (D28)` early-return block (returns before role validation on `ctx.is_platform_owner`). Then, after `roles = ctx.roles or []`, append the PO normalization: `if ctx.is_platform_owner and "platform_owner" not in roles: roles = ["platform_owner"] + roles`. The legacy fallback now evaluates PO through the same Casbin loop as everyone else.

**Verify (static):**
```bash
cd backend && ! grep -n "Platform owner bypass (D28)" kernel/authz/dependencies.py \
  && echo "legacy PO bypass removed"
```

### Task 5.2: App-level proof that the legacy path evaluates PO through the pipeline

**File:** `backend/tests/test_c04_authz.py` (updated in Group 9) — behavioral evidence for the group

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change (covered by Group 9 Task 9.2):** the renamed app-level PO tests (`test_platform_owner_denied_unconfigured_user_create`, `test_platform_owner_denied_unconfigured_institution_read`) run with the service singleton `None` (legacy fallback) and must return **403** — proof the legacy path no longer grants on bypass alone. No separate code change here; this task documents the cross-group evidence dependency.

**Verify (after 9.2):**
```bash
cd backend && python -m pytest tests/test_c04_authz.py -q -k "platform_owner" 2>&1 | tail -8
```

---

## Group 6 — Seed `platform_owner` platform permissions (D6)

### Task 6.1: Create Alembic migration `023_fix_c04_abac_po_permissions.py`

**File:** `backend/migrations/versions/023_fix_c04_abac_po_permissions.py` (new; `revision = "023_fix_c04_abac_po_permissions"`, `down_revision = "022_person_model_revamp"` — the current head; design said "chained after 016", tasks phase resolves the exact head at apply via `alembic revision`)

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change:**
Mirror D6 SQL exactly:
1. Insert `permission` row `client.create` (resource `client`, action `create`) `ON CONFLICT (name) DO NOTHING`.
2. Seed `role_permission` rows at scope `'any'` for `platform_owner` for the explicit surface: `client.create/read/update/transfer_ownership/transition_lifecycle`, `institution_type.read/create/update` (`ON CONFLICT (role_id, permission_id) DO NOTHING`).
3. Re-seat **all** `platform_owner` `role_permission` rows (including the 8 `config.*` from migration 009, which were seeded at the 016 server-default `'institution'`) to `scope='any'`.
4. `downgrade()`: delete the `client.*`/`institution_type.*` PO rows, delete the `client.create` permission, restore `config.*` PO rows to scope `'institution'`.

Include the post-migration verification query in the docstring. **No wildcard, no g-hierarchy** — only the explicit rows above.

**Verify:**
```bash
cd backend && python -m alembic upgrade head && python -c "
import os; from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get('DATABASE_URL','postgresql://postgres:postgres@127.0.0.1:54322/postgres'))
with engine.connect() as c:
    rows = c.execute(text(\"\"\"
        SELECT p.name, rp.scope FROM role_permission rp
        JOIN role r ON r.id=rp.role_id JOIN permission p ON p.id=rp.permission_id
        WHERE r.name='platform_owner' ORDER BY p.name\"\"\")).fetchall()
    names = {r[0] for r in rows}; scopes = {r[1] for r in rows}
    assert {'client.create','client.read','institution_type.read'} <= names, names
    assert all(n in ('client.create','client.read','client.update','client.transfer_ownership','client.transition_lifecycle','institution_type.read','institution_type.create','institution_type.update','config.read','config.write') or n.startswith('config.') for n in names)
    assert scopes == {'any'}, scopes
print('PO rows OK:', len(rows), 'rows, scope any')
" && python -m alembic downgrade -1 && python -m alembic upgrade head && echo "downgrade/re-upgrade OK"
```

### Task 6.2: DB-level test asserting the Platform Owner holds `client.read`

**File:** `backend/tests/test_authz_abac.py` (or a migration-data integration test)

**Requirements:** REQ-AUTHZ-FIX-PO-01

**Change:**
Add a test that queries the seeded matrix (join `role_permission`/`role`/`permission`) and asserts `platform_owner` holds `client.read`. Success depends on the test harness executing Alembic migrations against its DB (verify harness in Task 12); if the harness does not run migrations, annotate and rely on the Task 6.1 verification query instead (see Risk R2).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "po_has_client_read" 2>&1 | tail -8
```

---

## Group 7 — Wire production conditional-policy registration (D8)

### Task 7.1: Make `register_authorization_policies` real in the manifest

**File:** `backend/kernel/authz/manifest.py` (`register_authorization_policies`, currently `pass` at ~L52)

**Requirements:** REQ-AUTHZ-FIX-REG-01

**Change:**
Replace the `pass` body with a wired list-driven registration:
- module-level `_PRODUCTION_CONDITIONAL_POLICIES: list[tuple[str,str,str,str,Sequence[str]]] = []` (explicitly empty today — the Kernel ships NO business conditional policy).
- `register_authorization_policies(self, enforcer)` iterates that list calling `policy_loader.register_conditional_policy(enforcer, role, resource, action, scope, required_attrs)` and `logger.debug(...)` with the count.
- Confirm no factory change is needed: `app_factory._create_casbin_enforcer` already invokes `manifest.register_authorization_policies(enforcer)` after the DB loader (L198–199).

**Verify (static + import):**
```bash
cd backend && ! grep -nE "register_authorization_policies\(self, enforcer.*\n.*pass" kernel/authz/manifest.py \
  && python -c "from kernel.authz.manifest import manifest; print('manifest import OK')"
```

### Task 7.2: Add `test_production_conditional_policy_registration`

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-FIX-REG-01

**Change:**
Patch `AuthorizationManifest._PRODUCTION_CONDITIONAL_POLICIES` with one entry (e.g. `("Teacher","homework","create","institution",["is_subject_teacher"])`) on a fresh enforcer, run `manifest.register_authorization_policies(e)`, and assert:
- the 5-arg policy tuple appears in `e.get_all_policies()`; and
- `policy_loader._conditional["Teacher"]` holds the `(resource, action, scope, attrs_str)` entry; and
- the non-conditional/DB path is unchanged (a `register_policies_from_map`-style policy still lands with `""` attrs).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "production_conditional_policy_registration" 2>&1 | tail -8
```

---

## Group 8 — Policy identification includes `attrs` + scope filter (D9)

### Task 8.1: Update `_extract_policy_id` to a 5-part, matcher-mirror id

**File:** `backend/kernel/authz/services/authorization_service.py` (`_extract_policy_id`, ~L204, and new helper `_policy_scope_matches`)

**Requirements:** REQ-AUTHZ-FIX-PID-01

**Change:**
Rewrite to: iterate `get_filtered_policy(0, sub.get("role",""))`; skip `len(p) < 5`; skip unless `p[1]` matches `obj["name"]` and `p[2]` matches `action` (with `*` wildcard); skip unless `_policy_scope_matches(p[3], sub, obj)` (any→True; tenant→client equality; institution→client+institution equality); skip unless `match_attrs(sub, p[4])`; return `f"{p[0]}:{p[1]}:{p[2]}:{p[3]}:{p[4]}"`. Keep it post-hoc/audit-only (invoked only after `enforce()` returned True), wrapped in try/except returning `None`. `AuthorizationDecision` shape is unchanged.

**Verify (static):**
```bash
cd backend && python -c "
import inspect
from kernel.authz.services.authorization_service import AuthorizationService
src = inspect.getsource(AuthorizationService._extract_policy_id)
assert ':p[3]}:{p[4]}' in src or 'p[4]' in src, 'attrs must be part of the id'
assert 'match_attrs(sub, p[4])' in src, 'must verify the attr condition'
print('extract_policy_id includes attrs + attr verification')
"
```

### Task 8.2: Add policy-id tests

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-FIX-PID-01

**Change:**
- `test_extract_policy_id_includes_attrs` — register two conditional policies `(Teacher, homework, create, institution, "is_subject_teacher")` and `(Teacher, homework, create, institution, "is_class_teacher")`; ALLOW each in turn; assert the reported `policy_id` ends with the respective attrs field and the two ids **differ**.
- `test_extract_policy_id_scope_filtered` — matching `tenant`-scope vs non-matching `institution`-scope policy; the helper reports the matching scope's id, never a non-matching one.
- Structural "identification never grants": `_extract_policy_id` is only called post-ALLOW; assert existing allow/deny outcomes are unchanged (covered by full suite in Group 12).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "extract_policy_id" 2>&1 | tail -8
```

---

## Group 9 — Platform Owner security tests (D7) + app-level test updates (D12 inventory)

### Task 9.1: Add `_register_prod_po_policies` helper + `TestPlatformOwnerSecurity`

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-FIX-TEST-02

**Change:**
Add module-level helper `_register_prod_po_policies(e)` that builds the production-shape PO matrix (self-link only, explicit perms at scope `any`, **no** wildcard, **no** D11 g-hierarchy — mirrors the Task 6.1 seeds exactly). Add class `TestPlatformOwnerSecurity`:

| Test | Assertion |
|---|---|
| `test_po_client_read_allows` (pipeline) | PO + `client.read` on client/platform resource → `allowed is True`, `reason == ALLOWED`, `policy_id` non-null and 5-part |
| `test_po_raw_enforcer_client_read` | `platform_owner` + `client.read ("any")` on cross-client obj → `enforcer.enforce(...) is True` (scope `any` = no tenant check) |
| `test_po_denied_operational_resources` (parametrized) | PO → `student`/`teacher`/`attendance`/`homework` → `allowed is False`, `reason == MISSING_PERMISSION` |
| `test_po_denied_unconfigured_permissions` | PO → `user.create` / `institution.read` (exist for other roles, not PO) → `reason == MISSING_PERMISSION` |
| `test_po_subject_normalization` | `from_tenant_context` with `is_platform_owner=True`, `roles=[]` → `("platform_owner",)` (D5 direct assert) |
| `test_po_multi_role_no_double_grant` | PO with `["platform_owner","client_director"]` → allowed only via a matching policy, never a second grant |

Remove the old `test_platform_owner_bypass` (L440) pipeline test from `test_authz_abac.py` — its positive case is covered by `test_po_client_read_allows`.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "TestPlatformOwnerSecurity" 2>&1 | tail -12
```
Expected: all D7 matrix tests pass (ALLOW via configured perm; DENY on student/teacher/attendance/homework/unconfigured).

### Task 9.2: Update app-level PO bypass tests to 403 (rename + invert assertion)

**Files:**
- `backend/tests/test_c04_authz.py` — `test_platform_owner_bypass_user_create` (L395) and `test_platform_owner_bypass_institution_read` (L403) → rename `test_platform_owner_denied_unconfigured_user_create` / `..._institution_read`, assert **403**.
- `backend/tests/test_fees.py` — `test_platform_owner_bypasses_all` (L633) → rename `test_platform_owner_denied_operational_resource`, assert **403** on POST `/api/v1/fee-types`.

**Requirements:** REQ-AUTHZ-FIX-TEST-02, REQ-AUTHZ-FIX-PO-01

**Change:**
Invert the assertions. Deterministic in both service states per D7: service wired → PO has no `user.create`/`institution.read`/`fee.*` rows → `MISSING_PERMISSION` 403; service `None` → legacy fallback with `roles=["platform_owner"]` → no policy → 403. Keep the D11-fixture enforcer-level tests (`test_platform_owner_bypasses_all_c01` etc., `test_c04_authz.py:256–273`) **unchanged** and annotated as legacy-D11-fixture (they exercise model semantics, never the pipeline).

**Verify:**
```bash
cd backend && python -m pytest tests/test_c04_authz.py tests/test_fees.py -q -k "platform_owner" 2>&1 | tail -10
```

---

## Group 10 — Provider-failure fail-closed test (D3 / REQ-AUTHZ-FIX-TEST-03)

### Task 10.1: Add `test_provider_exception_fails_closed`

**File:** `backend/tests/test_authz_abac.py`

**Requirements:** REQ-AUTHZ-FIX-TEST-03

**Change:**
Register a test-only provider whose `resolve()` raises `RuntimeError`; issue a request whose conditional policy requires that provider's attribute; verify `decision.allowed is False` and `decision.reason == AuthorizationReasonCode.UNRESOLVED_ATTRIBUTE` (registry already catches and records into `unresolved`; the pipeline returns `UNRESOLVED_ATTRIBUTE`). Assert it is **never** ALLOW. No provider contract change needed (fail-closed already in `ProviderRegistry.resolve_attributes`).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "test_provider_exception_fails_closed" 2>&1 | tail -8
```

---

## Group 11 — Scope regression tests (REQ-AUTHZ-FIX-TEST-01 case 4)

### Task 11.1: Confirm existing scope tests still pass unchanged

**Files:** `backend/tests/test_authz_abac.py` (security scope tests), `backend/tests/test_casbin_permissions.py`

**Requirements:** REQ-AUTHZ-FIX-TEST-01 (case 4), REQ-AUTHZ-FIX-ABAC-01

**Change:**
No new code — assert the pre-existing scope invariants still hold under the strict `match_attrs` after all groups 1–10 land: Client A→A ALLOW / A→B DENY (`TENANT_ACCESS_DENIED`) and Institution A→A ALLOW / A→B DENY (`INSTITUTION_ACCESS_DENIED`); no-attribute request follows pure RBAC/scope (provider not invoked).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py tests/test_casbin_permissions.py -q \
  -k "tenant or institution or security or pure_rbac" 2>&1 | tail -8
```

---

## Group 12 — Test suite verification + kernel boundary static checks (D12)

### Task 12.1: Extend `TestKernelBoundary` static checks for the removed bypass

**File:** `backend/tests/test_authz_abac.py` (class `TestKernelBoundary`, ~L621)

**Requirements:** all (Kernel boundary + PO-01 static guard)

**Change:**
Extend the existing static class to additionally assert: (a) no `business.*` imports / no business ORM names in `kernel/authz/` (retained); (b) no `is_platform_owner ... return allow` / `Platform owner bypass` pattern remains in `authorization_service.py` **and** `dependencies.py` (static guard against reintroducing the bypass).

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py -q -k "TestKernelBoundary" 2>&1 | tail -8
```

### Task 12.2: Run the full backend test suite

**File:** N/A

**Requirements:** REQ-AUTHZ-FIX-TEST-01..03, all MODIFIED reqs

**Change:**
Run the full backend suite plus an AuthZ-focused run. Confirm all AuthZ tests pass and no regressions elsewhere (fees, C-04, platform, lifecycle, RLS). Confirm the harness applies migrations to its test DB (Risk R2) so the app-level PO tests + Task 6.2 DB test run against the new seeds.

**Verify:**
```bash
cd backend && python -m pytest tests/test_authz_abac.py tests/test_c04_authz.py tests/test_casbin_permissions.py tests/test_fees.py -q 2>&1 | tail -12
cd backend && python -m pytest tests/ -q 2>&1 | tail -15
```

---

## Auxiliary (archive-time action — NOT part of the apply-phase code delta) — D11

### Task A.1: Amend the archived "PO bypass SHALL STAY" spec lines at archive time

**Files (archive-time, not this change's code delta):** `openspec/specs/platform-owner-separation/spec.md` (~L91–93, D28) and `openspec/specs/client-user-bootstrap/spec.md` (~L230–233, D8)

**Requirements:** REQ-AUTHZ-FIX-PO-01 (spec consistency)

**Change:**
At the archive step (or a follow-up delta), rewrite the historical "the PO `require_permission` bypass ... SHALL STAY" lines to state PO is now evaluated through the normal pipeline via configured `role_permission` rows (per this fix), so `main` specs do not contradict the shipped behavior. **Do not edit these files during apply** — this change's spec delta is scoped to the `authorization` domain. Flag for the archive phase.

**Verify:**
```bash
cd .. # repo root
grep -rn "SHALL STAY" openspec/specs/platform-owner-separation/spec.md openspec/specs/client-user-bootstrap/spec.md \
  && echo "confirm archive-time lines still present (pending archive amendment)"
```

---

## Summary

| Group | Design | Tasks | Key Deliverable |
|---|---|---|---|
| 1 — `match_attrs` strict | D1 | 1 | strict `is True`; string `"false"` denied |
| 2 — Raw enforcer boundary | D2 | 1 (4 tests) | `TestRawEnforcerBoundary` (attr true/false/missing/no-attr) |
| 3 — Stub fix + pipeline ABAC | D3 | 2 | real `test_failed_abac`; `test_abac_never_bypasses_rbac` |
| 4 — Service PO bypass | D4a/D5 | 2 | Step-1 removed; PO role normalization |
| 5 — Legacy PO bypass | D4b/D5 | 2 | legacy block removed + normalization |
| 6 — PO permission migration | D6 | 2 | `023_fix_c04_abac_po_permissions` (merge/up/down verified); PO `client.read` DB test |
| 7 — Production registration | D8 | 2 | wired `register_authorization_policies` + startup test |
| 8 — Policy identity | D9 | 2 | 5-part `policy_id` + scope filter + tests |
| 9 — PO security tests | D7/D12 | 2 | `TestPlatformOwnerSecurity`; app-level 403 updates |
| 10 — Provider-failure | D3 | 1 | `test_provider_exception_fails_closed` |
| 11 — Scope regression | D2/TEST-01 | 1 | Client/Inst A→A/A→B still hold |
| 12 — Full-suite + boundary | D12 | 2 | `TestKernelBoundary` guard; full suite green |
| Aux — archive spec amendment | D11 | 1 | archive-time spec fix (not apply) |
| **Total** | | **22** | |

### Dependency Order

```
Group 1 (match_attrs strict) ─► Group 2 (raw boundary tests, pins Group 1)
Group 3 (stub + RBAC-never-bypass) ─► (independent of Groups 4–8)
Groups 4 + 5 (remove both PO bypasses + normalization) ─► Groups 6 (seeds) + 9 (PO security + app-level tests)
Group 6 (migration) is the precondition for the Group 9 app-level 403/DB tests in any service-wired state
Group 7 (registration) and Group 8 (policy id) are independent of Groups 4–6
Group 9 depends on Groups 4, 5, 6 (bypass removed, seeds present, normalization active)
Group 10 (provider fail-closed) independent; Group 11 (scope regression) validates Group 1 on existing tests
Group 12 (full suite + boundary static) runs last and gates closure
Aux (archive amendment) is archive-time, after apply
```

### Implementation notes / guardrails
- Kernel is business-agnostic: all new tests use test-only providers + in-memory policies; no business module is imported (enforced by Task 12.1).
- No RLS change; no `casbin_model.conf` change; no `require_permission` signature change; `AuthorizationDecision` shape unchanged (constraints, per AGENTS.md §8 config/module + task brief).
- Migration head at apply time must be confirmed via `alembic heads`; the design's "after 016" is superseded by the actual current head `022_person_model_revamp` (note in Task 6.1).
