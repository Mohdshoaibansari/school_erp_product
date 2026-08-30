# Design — AuthZ Kernel ABAC Enforcement & Platform Owner Security Fix

> **Change:** `fix-c04-authz-abac-enforcement`
> **Capability:** C-04 Authorization / AuthZ Kernel
> **Phase:** sdd-stack design
> **Traceability:** Design decisions (D1–D12) trace to the delta spec requirements `REQ-AUTHZ-FIX-ABAC-01`, `REQ-AUTHZ-FIX-PO-01`, `REQ-AUTHZ-FIX-REG-01`, `REQ-AUTHZ-FIX-PID-01`, `REQ-AUTHZ-FIX-TEST-01..03` and proposal §2 (P0/P1), §4 (PO product requirement), §5 (DoD), §6 (required tests), §8 (deliverables).
> **Decisional inputs:** `proposal.md`, delta spec `specs/authorization/spec.md`, scout report (`bb606037_pi-sdd-scout_0_output.md`), base implementation `add-c04-authz-abac-enhancement` design.md.
> **Status:** Design phase — ready for tasks breakdown.

---

## 0. Scope and Boundary

This change **corrects and completes** the shipped ABAC-enhancement implementation (`add-c04-authz-abac-enhancement`, on `main`, must not be discarded). It touches **only** the AuthZ Kernel wiring, the Platform Owner permission surface, and the AuthZ test suite. No teacher/student/parent/homework/attendance business rule is implemented; no business ORM model is imported into the Kernel; no RLS policy is changed; no Kafka/event bus/rule engine/DB bypass is introduced.

**In scope:** real Casbin-boundary ABAC enforcement (attribute `false`/`missing` → DENY proven inside the matcher), removal of the unconditional Platform Owner ALLOW (both locations), Platform Owner permission seeding via migration, production conditional-policy registration wiring, policy-identification improvement, and regression/security tests.

**Out of scope (explicit):** business-module conditional policies (Phase 7), runtime policy reload, dynamic DB policy table, RLS changes, `authorize_many()` batch execution, multi-role attribute-resolution optimization (designed deferral, D10).

**Verified current state (scout + design-phase reads, not re-verified here):**
- Casbin **1.43.0** sync; enforcer built in `backend/kernel/app_factory.py` `_create_casbin_enforcer` (L161–218) from `kernel/authz/casbin_model.conf`; populated only in-memory via `add_policy` / `add_role_for_user`.
- `match_attrs` registered at `app_factory.py:189` **before** all policy loops; same in every test harness.
- The matcher **already** ends with `&& match_attrs(r.sub, p.attrs)`; policy def is `p = sub, obj, act, scope, attrs` (5 fields). The enforcement path exists but is **unproven at the raw boundary** and **bypassed for Platform Owners**.
- PO unconditional ALLOW exists in **two places**: `authorization_service.py:100–105` (Step 1 of `authorize()`) and `dependencies.py` `_check_impl_legacy` (the `# Platform owner bypass (D28)` block, ~L219–222).
- PO JWT (minted by `kernel/auth/services/service.py:113–144`) carries **only** `sub` + `is_platform_owner` — **no `roles` claim, no `client_id`**. Middleware (`kernel/middleware.py`) skips role lookup for PO → production `TenantContext.roles == []` for PO. Any pipeline PO evaluation therefore needs an effective role label (D5).
- Production `role_permission` rows for `platform_owner`: only the 8 `config.*` perms (migration 009), all with scope `'institution'` (the 016 server_default). No `client.*` rows. The D11 wildcard `("platform_owner","*","*","any","")` exists **only in test fixtures**.
- Platform routes (`backend/business/tenant_institution/routes/platform.py`) reference `client.create/read/update/transfer_ownership/transition_lifecycle` and `institution_type.read/create/update`; `client.create` **has no permission row anywhere**; `institution_type.read` (004) / `create`,`update` (016) exist. One route (`approve_ownership_transfer`) has **no** `require_permission` at all (only `require_platform_owner`).
- `_extract_policy_id` (`authorization_service.py:204–213`) derives `sub:obj:act:scope` **without** `attrs` and **without** scope filtering; audit-only.
- `manifest.register_authorization_policies` is `pass`; `register_conditional_policy` + the `_conditional` catalog are used **only in tests**.
- `tests/test_authz_abac.py` `test_failed_abac` (L354–362) is a **vacuous stub** (no `authorize()` call, no assertion) — and it calls `_setup_base_policies`, which adds a non-conditional policy that would defeat the intended ABAC check.
- `tests/conftest.py:253` overrides `get_enforcer` with `_AllowAllEnforcer()` for app-level tests; the modern `require_permission` path resolves `svc = get_authorization_service()` and calls `svc.authorize(request)` — the service holds the **real** enforcer — so the override is inert on the modern path (it only affects the legacy fallback). App-level tests that must control the pipeline use their own service/enforcer wiring.

---

## 1. Architecture Overview — Before / After

### 1.1 Before (declared-but-unproven ABAC + unconditional PO ALLOW)

```
AuthorizationService.authorize(request)
  1. is_platform_owner or "platform_owner" in roles  →  ALLOW   ← unconditional bypass (2x)
  2. no roles                     → DENY(NO_ROLES)
  3. required attrs (catalog)     → union across roles
  4. resolve attrs (providers)    → fail-closed UNRESOLVED_ATTRIBUTE
  5. Casbin loop per role         → match_attrs(d) evaluated in matcher, but:
       • attr=false / attr=missing DENY never proven at the enforcer boundary
       • test_failed_abac is a vacuous stub
       • conditional policies exist only in tests (production hook = pass)
  6. classify denial              → reason codes
  7. audit
```

Problems:
1. **PO bypass short-circuits step 1 in two code paths** — a Platform Owner is ALLOWed on *any* resource/action (student, homework, fee, …) before RBAC/scope/ABAC/Casbin run. The legacy fallback path keeps the same hole.
2. Production PO has **no platform-level Casbin permissions** (only `config.*`), so removing the bypass alone would break the platform surface unless permissions are seeded.
3. Production PO has **no role label** in `TenantContext.roles` (JWT holds none) — the pipeline's no-roles check and the per-role Casbin loop can't evaluate a PO without an effective role.
4. ABAC enforcement is **unproven at the raw boundary**: no test calls `enforcer.enforce()` directly with `attribute=false` / `attribute=missing`; the one DENY-style test is vacuous; `match_attrs` truthiness accepts the string `"false"` (a latent ALLOW bug).
5. `_extract_policy_id` collides for conditional policies sharing `role:resource:action:scope` and can name a policy whose scope did **not** match.

### 1.2 After (verified ABAC + PO through the normal pipeline)

```
AuthorizationService.authorize(request)
  1. (removed)                     ← no PO short-circuit
  2. effective roles               → PO normalized to ("platform_owner",) [D5]
  3. no roles                      → DENY(NO_ROLES)
  4. required attrs (catalog)      → union across roles [D10: unchanged, deferred]
  5. resolve attrs (providers)     → fail-closed; provider exception → UNRESOLVED_ATTRIBUTE [D2/D3]
  6. Casbin loop per role          → raw-boundary PROVEN: attr=true ALLOW, false/missing DENY [D1/D2]
  7. classify denial               → reason codes (never grants)
  8. audit                         → policy_id now includes attrs + scope-accurate [D9]

Platform Owner (production):
  - JWT is_platform_owner  →  TenantContext.is_platform_owner (unchanged, RLS defense-in-depth)
  - subject roles          → ("platform_owner",) derived at the authz boundary [D5]
  - grants                 → role_permission rows seeded by migration [D6]:
        client.create/read/update/transfer_ownership/transition_lifecycle,
        institution_type.read/create/update, config.* — all scope "any"
  - access to institute operational resources (student, teacher, attendance, homework, fee, …)
    → DENY MISSING_PERMISSION (no rows, no wildcard, no hierarchy in production)

Production registration:
  manifest.register_authorization_policies → iterates a declared conditional-policy
  list calling register_conditional_policy (mechanism wired, list empty today) [D8]
```

The enforcer remains the **sole granter**. Denial classification, audit, attribute resolution, and RLS all stay on the existing side rails.

---

## 2. Architecture Decisions

### D1 — `match_attrs` strict-boolean semantics (REQ-AUTHZ-FIX-ABAC-01; P0; task D-A)

**Decision: tighten `match_attrs` from Python truthiness to strict boolean identity.**

`backend/kernel/authz/services/authorization_service.py` (L41–55):

```python
def match_attrs(sub: dict, attrs: str) -> bool:
    if not attrs or attrs in ("*", ""):
        return True                       # no attribute condition — unchanged
    return all(sub.get(a) is True for a in attrs.split(","))
```

Semantics table:

| Subject value for required attr `a` | `bool(v)` (before) | `v is True` (after) | Result |
|---|---|---|---|
| `True` (real bool from a provider) | ALLOW | ALLOW | ALLOW |
| `False` | DENY | DENY | DENY |
| key absent (`.get` → `None`) | DENY (`bool(None)`) | DENY (`None is True`) | DENY — fail-closed |
| `None` | DENY | DENY | DENY |
| `""` empty string | DENY | DENY | DENY |
| string `"false"` | **ALLOW** (truthy) | DENY | **bug fixed** |
| string `"true"`, int `1`, numpy bool | ALLOW | DENY | fail-closed on non-bool |
| `0` | DENY | DENY | DENY |

**Why strict `is True` (not `bool()`):** the only behavior that changes is ambiguous *truthy-non-bool* values, which previously ALLOWed. Strictness makes the matcher fail closed on everything that is not a genuine provider-returned boolean. Providers are server-side, Kernel-contract code (never client input — D6 of the base design), so requiring real `bool` returns is an enforceable contract. Cost: a provider returning `1`/`"true"`/`numpy.bool_` now DENies — that is the desired fail-closed direction, documented in the provider contract docstring.

**Interpretation note (spec wording):** the delta spec says every named attribute must be "present and truthy". This design interprets "truthy" as **strict boolean `True`** — the safe tightening requested by the source brief. If reviewers prefer literal Python truthiness, the change is a one-word revert in `match_attrs`; that is not recommended (string `"false"` would re-open an ALLOW vector).

**Scope of change:** one line in `match_attrs` + provider-contract docstring. The matcher (`casbin_model.conf`) is untouched. All existing providers return real bools (`IsSelfAttributeProvider`, test synthetics), and all `attrs=""` RBAC policies are unaffected — no existing green test flips (verified against the test inventory in §6).

### D2 — Raw enforcer-boundary ABAC tests (REQ-AUTHZ-FIX-ABAC-01, REQ-AUTHZ-FIX-TEST-01; P0; task D-A)

**Decision: add a dedicated test class that calls `enforcer.enforce()` directly — no `AuthorizationService` — at the Casbin boundary.**

New class `TestRawEnforcerBoundary` in `backend/tests/test_authz_abac.py` (reusing `_build_enforcer()` which registers `match_attrs`):

```python
def _po_boundary_enforcer(self):
    e = _build_enforcer()
    e.add_role_for_user("Teacher", "Teacher")
    e.add_policy("Teacher", "homework", "create", "institution", "is_subject_teacher")
    e.add_policy("Teacher", "homework", "read",    "institution", "")   # no-attr control
    return e

def test_attr_true_allows(self):
    sub = {"role": "Teacher", "client_id": CID, "institution_id": IID, "is_subject_teacher": True}
    obj = {"name": "homework", "client_id": CID, "institution_id": IID}
    assert self._po_boundary_enforcer().enforce(sub, obj, "create") is True

def test_attr_false_denies(self):
    ... "is_subject_teacher": False ...  assert enforce(...) is False   # Casbin-level DENY

def test_attr_missing_denies(self):
    ... sub WITHOUT the "is_subject_teacher" key ... assert enforce(...) is False

def test_no_attr_falls_back_to_rbac_scope(self):
    ... sub with no domain attrs, attrs="" policy, matching scope → True
```

**Why `missing → DENY` holds at the boundary:** `match_attrs(r.sub, p.attrs)` is the last conjunct of the matcher. With `p.attrs == "is_subject_teacher"` and the key absent, `sub.get("is_subject_teacher")` returns `None`; `None is True` is `False` → the matcher evaluates `False` → `enforce()` returns `False`. There is no Python pre-check on this path — the denial is produced **inside Casbin**, which is exactly what the requirement asks to prove (`attribute=false/missing → DENY directly, no Python pre-check involved`).

**Why the raw boundary matters:** all existing DENY assertions run through `authorize()` and observe the denial only via `decision.reason` — a change that made `match_attrs` a no-op (or an always-true stub) would flip them to ALLOW, except the vacuous stub which could never catch it. Direct `enforce()` assertions pin the matcher behavior itself, so a regression in the Casbin path (function not registered, attrs dropped, model changed) fails loudly.

### D3 — `test_failed_abac` stub fixed + pipeline regression coverage (REQ-AUTHZ-FIX-ABAC-01, REQ-AUTHZ-FIX-TEST-01; P0; task D-A)

**Decision: replace the vacuous stub with a real pipeline assertion; do NOT remove it.** The stub's docstring documents an intended behavior (false `is_subject_teacher` → `NOT_ASSIGNED_TO_RESOURCE`) that no other pipeline test asserts with that exact shape; fixing it is cheaper than deleting + re-documenting.

New body of `test_failed_abac` (mirrors `test_synthetic_deny_with_conditional_policy` / `test_conflicting_assignments` shape — **no** non-conditional fallback policy, which would defeat the ABAC check):

```python
def test_failed_abac(self):
    """is_subject_teacher=false → DENY NOT_ASSIGNED_TO_RESOURCE (real assertion)."""
    e = _build_enforcer()
    e.add_role_for_user("Teacher", "Teacher")
    pl._conditional.clear(); pl._non_conditional.clear()
    pl._conditional["Teacher"] = [("homework", "create", "institution", "is_subject_teacher")]

    r = ProviderRegistry(); r.register(SyntheticTeacherProvider())
    svc = _build_service(enforcer=e, registry=r)

    req = _make_request(resource=_make_resource(data={"section_id": "5A"}))  # 5A → False
    decision = asyncio.run(svc.authorize(req))
    assert decision.allowed is False
    assert decision.reason == AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE
```

**Regression-case matrix for REQ-AUTHZ-FIX-TEST-01** (five required cases; existing coverage retained, one new case):

| # | Case | Test (file) | Status |
|---|---|---|---|
| 1 | attribute=true + required-attr policy → ALLOW | `test_synthetic_allow_with_conditional_policy`, `test_successful_abac` | exists |
| 2 | attribute=false + required-attr policy → DENY | `test_synthetic_deny_with_conditional_policy`, `test_teacher_assigned_to_1a_deny_1b`, fixed `test_failed_abac` | exists + fixed |
| 3 | attribute=missing → fail-closed DENY | `test_missing_required_attribute_fail_closed` (no provider → `UNRESOLVED_ATTRIBUTE`), NEW raw-boundary `test_attr_missing_denies` (key absent inside Casbin) | exists + new |
| 4 | no attribute requirement → RBAC/scope only | `test_pure_rbac_fallback` (provider not invoked), NEW raw-boundary `test_no_attr_falls_back_to_rbac_scope` | exists + new |
| 5 | ABAC never bypasses RBAC (attr=true, permission absent → DENY) | **NEW** `test_abac_never_bypasses_rbac` (§6) | new |

**Provider-failure fail-closed (REQ-AUTHZ-FIX-TEST-03):** NEW `test_provider_exception_fails_closed` — register a provider whose `resolve()` raises `RuntimeError`, request with a conditional policy requiring its attribute → `authorize()` returns DENY `UNRESOLVED_ATTRIBUTE` (verified: `ProviderRegistry.resolve_attributes` catches and records into `unresolved` at `attribute_provider.py:174–179`; the pipeline returns `UNRESOLVED_ATTRIBUTE` at `authorization_service.py:126–132`). Never ALLOW.

### D4 — Platform Owner bypass removed in both locations (REQ-AUTHZ-FIX-PO-01; P0; task D-B)

**Decision: delete the unconditional ALLOW in the service Step 1 and the legacy fallback block.**

1. `backend/kernel/authz/services/authorization_service.py` — delete the Step 1 block (L98–107). `authorize()` then starts at the no-roles check. The docstring pipeline list is updated (Step 1 removed).
2. `backend/kernel/authz/dependencies.py` `_check_impl_legacy` — delete the `# Platform owner bypass (D28)` block (return before role validation). The legacy fallback then evaluates PO through the same Casbin loop as everyone else.

Consequences, by construction of the pipeline:
- **No path grants a PO without a matching policy.** Grant comes only from `role_permission` rows → non-conditional policies → Casbin `g(r.sub.role, p.sub) && scope && match_attrs`.
- `is_platform_owner` in `SubjectContext` and the RLS session var `app.is_platform_owner` (migration 007 `platform_owner_client_access`, `kernel/db.py:59–61`) are **unchanged** — they are defense-in-depth (TenantContext membership + DB row wall), not an authorization grant. The `require_platform_owner` route guard is **kept as-is**: it gates *platform membership*, it is not an authz bypass (the fix spec's boundary relationship "PO routes now rely on configured permissions, not a bypass" refers to the `require_permission` layer).
- Audit: PO decisions now carry a real `policy_id` when allowed and a real reason code when denied; no more bare `ALLOWED` with `policy_id=None`.

### D5 — Platform Owner effective role label (REQ-AUTHZ-FIX-PO-01; P0; task D-B)

**Decision: derive the PO's effective role label at the authz boundary — not in middleware, not in the pipeline core.**

Production PO JWTs carry no `roles` claim and middleware skips role lookup for PO (`kernel/middleware.py` "Role lookup for normal users (not platform owner...)"). Without a label, the no-roles check DENies everything and the per-role Casbin loop `g(r.sub.role, p.sub)` can never match `p.sub == "platform_owner"`. 

`backend/kernel/authz/models/authorization_types.py` `SubjectContext.from_tenant_context` (L38):

```python
@classmethod
def from_tenant_context(cls, ctx: Any) -> SubjectContext:
    roles = tuple(ctx.roles or [])
    if ctx.is_platform_owner and "platform_owner" not in roles:
        # PO JWT carries no roles claim (kernel.auth C-03); derive the existing
        # "platform_owner" DB role so configured role_permission rows
        # (client.*, config.*) match via Casbin g(). Role derivation, NOT a
        # bypass: grants still come only from role_permission rows, evaluated
        # by the full pipeline (permission → scope → ABAC → Casbin).
        roles = ("platform_owner",) + roles
    return cls(user_id=ctx.user_id, roles=roles, ...)
```

And in the legacy fallback `_check_impl_legacy`, after `roles = ctx.roles or []`:

```python
if ctx.is_platform_owner and "platform_owner" not in roles:
    roles = ["platform_owner"] + roles
```

Rationale and tradeoffs:
- **Chosen: authz-boundary normalization** (single production construction point `dependencies.py:81` + the legacy fallback). Contained to the authorization layer ("the fix is at the authorization layer only" — proposal §4), zero impact on other `TenantContext.roles` consumers, no middleware behavior change.
- Rejected alternatives: middleware injection of `"platform_owner"` into `ctx.roles` (widens the change to every roles consumer and muddies TenantContext semantics); pipeline-core special case in `authorize()` Step 2 (splits effective-role logic across the service and forces threading through `_enforce`/`_classify_denial`).
- The role name `"platform_owner"` already exists as a DB `role` row (migration 004) and is the key under which all PO `role_permission` rows are seeded (009 and the new migration, D6) — the normalization is therefore consistent with the existing permission matrix, not a new concept.

### D6 — Platform Owner platform-permission migration (REQ-AUTHZ-FIX-PO-01; P0; task D-B critical decision)

**Decision: seed explicit `role_permission` rows for `platform_owner` (option (a) — product-aligned; keeps the platform surface working). No wildcard, no hierarchy — every permission is explicit and grounded in the platform routes + the D11 matrix (ADR C-01 D11: PO = "ALL C-01 operations — create/suspend/archive/terminate Client, manage InstitutionTypes, everything, as higher authority").**

New Alembic migration `backend/migrations/versions/0XX_fix_c04_abac_po_permissions.py` (revision chained after 016 — see tasks phase for the exact head):

```python
_PO_PLATFORM_PERMS = [
    "client.create",                      # NEW permission row; POST /api/v1/platform/clients
    "client.read",                        # GET  /api/v1/platform/clients[/{id}]
    "client.update",                      # PATCH /api/v1/platform/clients/{id}
    "client.transfer_ownership",          # POST /api/v1/platform/ownership-transfers
    "client.transition_lifecycle",        # POST /api/v1/platform/clients/{id}/transition
    "institution_type.read",              # GET  /api/v1/platform/institution-types[/{id}]
    "institution_type.create",            # POST /api/v1/platform/institution-types
    "institution_type.update",            # PATCH /api/v1/platform/institution-types/{id}
    # config.* (8, seeded in 009) — scope corrected to 'any' below
]

def upgrade():
    # 1. client.create — no permission row exists today
    op.execute(
        "INSERT INTO permission (id, name, description, resource, action) "
        "VALUES (gen_random_uuid(), 'client.create', "
        "'Create a client (platform-level)', 'client', 'create') "
        "ON CONFLICT (name) DO NOTHING"
    )
    # 2. Seed platform_owner rows at scope 'any' (explicit perms only)
    for perm in _PO_PLATFORM_PERMS:
        op.execute(
            "INSERT INTO role_permission (id, role_id, permission_id, scope) "
            "SELECT gen_random_uuid(), r.id, p.id, 'any' "
            "FROM role r, permission p "
            "WHERE r.name = 'platform_owner' AND p.name = :perm "
            "ON CONFLICT (role_id, permission_id) DO NOTHING",
            {"perm": perm},
        )
    # 3. Re-seat ALL platform_owner rows (incl. config.* from 009) to scope 'any'
    op.execute(
        "UPDATE role_permission SET scope = 'any' "
        "WHERE role_id = (SELECT id FROM role WHERE name = 'platform_owner')"
    )

def downgrade():
    op.execute(
        "DELETE FROM role_permission WHERE role_id = "
        "(SELECT id FROM role WHERE name = 'platform_owner') "
        "AND permission_id IN (SELECT id FROM permission "
        "WHERE name IN ('client.create','client.read','client.update',"
        "'client.transfer_ownership','client.transition_lifecycle',"
        "'institution_type.read','institution_type.create','institution_type.update'))"
    )
    op.execute("DELETE FROM permission WHERE name = 'client.create'")
    # restore 009-era scope ('institution') for the config.* platform_owner rows
    op.execute(
        "UPDATE role_permission SET scope = 'institution' WHERE role_id = "
        "(SELECT id FROM role WHERE name = 'platform_owner')"
    )
```

**Design rationale:**
- **Exact surfaces.** The seeded names are exactly the `require_permission` resources/actions on the platform router (read during design: `platform.py` `client create/read/update/transition_lifecycle/transfer_ownership` + `institution_type read/create/update`). `institution_type.*` and `client.create` are grounded in the D11 matrix ("manage InstitutionTypes", "create Client"). **No `platform.*` family is invented; no wildcard is used.** If the platform capability owner wants a stricter matrix later, the migration is one file to trim.
- **Scope `'any'` for all PO rows** (including re-seating the 009 config.* rows from the accidental `'institution'` default): PO is a platform-level identity with `client_id=None`/`institution_id=None` on both sub and obj (routes pass `obj_client_id=None` → ctx fallback → empty). `'institution'` scope would "pass" today only via the fragile `"" == ""` vacuous equality; `'any'` encodes the intended semantics per `casbin_model.conf` ("any — no tenant check (Platform-level / cross-tenant operations)") and matches the D11 fixture's PO scope. Platform-wide config ops (`config.*`) are platform-level by nature.
- **No hierarchy.** Production registers only self-links (`policy_loader.py:88`); the D11 g-hierarchy (`platform_owner → client_director/...`) exists only in test fixtures and is **not** seeded — PO grants stay exactly the seeded rows. This is what makes "PO cannot auto-access institute operational resources" hold in production.
- **`approve_ownership_transfer`** (`platform.py`, the only platform route with no `require_permission`) — leave its `require_platform_owner`-only guard in place for this change (it never relied on a bypass); recommended follow-up: add `require_permission("client", "transfer_ownership", obj_client_id=None)` for guard parity (P2, optional, no behavior change to the fix).

Deployment sequence (§5): migration must land with or before the code in the same release; restart required (startup policy load). Old code + new migration: no behavior change (bypass still active); new code + old DB: PO platform access breaks → do not deploy code before the migration.

### D7 — Platform Owner security tests (REQ-AUTHZ-FIX-TEST-02; P0; task D-B)

**Decision: new `TestPlatformOwnerSecurity` class in `backend/tests/test_authz_abac.py` using a production-shape PO matrix (self-link only, explicit perms — no wildcard, no D11 hierarchy), plus updated legacy app-level tests.**

New shared helper (module-level in `test_authz_abac.py`, reused by raw-boundary and pipeline PO tests):

```python
def _register_prod_po_policies(e):
    """Production-shape Platform Owner matrix (D6): explicit perms, no wildcard/hierarchy.

    Mirrors the migration seeds exactly: (resource, action) tuples at scope 'any'.
    """
    e.add_role_for_user("platform_owner", "platform_owner")
    for resource, action in [
        ("client", "create"), ("client", "read"), ("client", "update"),
        ("client", "transfer_ownership"), ("client", "transition_lifecycle"),
        ("institution_type", "read"), ("institution_type", "create"),
        ("institution_type", "update"),
    ]:
        e.add_policy("platform_owner", resource, action, "any", "")
```

Tests (pipeline via `AuthorizationService` + provider registry, plus one raw enforcer assert):

| Scenario | Assertion |
|---|---|
| PO + `client.read` on a client/platform resource → ALLOW through the normal pipeline | `decision.allowed is True`, `reason == ALLOWED`, `policy_id` non-null and 5-part |
| PO raw enforcer boundary: `platform_owner` + `client.read (any)` on cross-client obj → True | `enforcer.enforce(...) is True` (scope `any` = no tenant check) |
| PO → `student`/`teacher`/`attendance`/`homework` resource → DENY (no rows) | `allowed is False`, `reason == MISSING_PERMISSION` |
| PO → `user.create` / `institution.read` → DENY (exist for other roles, not PO) | `reason == MISSING_PERMISSION` |
| PO built from `TenantContext` via `from_tenant_context` (roles=[]) gets `("platform_owner",)` | D5 normalization asserted directly |
| PO more than one role (e.g. `["platform_owner","client_director"]`) — no double-grant, pipeline unchanged | allowed only via a matching policy |

App-level legacy tests updated (they asserted the removed bypass):
- `backend/tests/test_c04_authz.py` `test_platform_owner_bypass_user_create` / `test_platform_owner_bypass_institution_read` (L395–410) → renamed `test_platform_owner_denied_unconfigured_user_create` / `..._institution_read`, asserting **403**. Deterministic in both service states: service wired → PO has no `user.create`/`institution.read` rows → `MISSING_PERMISSION` 403; service None → legacy fallback with `roles=["platform_owner"]` → no policy → 403.
- `backend/tests/test_fees.py:633` `test_platform_owner_bypasses_all` → renamed `test_platform_owner_denied_operational_resource`, asserting **403** on POST `/api/v1/fee-types` (fee-type creation is an institute operational resource; PO has no `fee.*` rows).
- `backend/tests/test_authz_abac.py` `test_platform_owner_bypass` (L440) — pipeline test asserting bypass ALLOW → replaced by the D7 ALLOW/DENY matrix (removed; its positive case is covered by `PO + client.read → ALLOW`).

### D8 — Production conditional-policy registration (REQ-AUTHZ-FIX-REG-01; P0; task D-C)

**Decision: wire `manifest.register_authorization_policies` to a declared, explicit conditional-policy list; keep it minimal — no rules engine, no business rules in the Kernel.**

`backend/kernel/authz/manifest.py` (L48–54):

```python
# Declared production conditional policies: (role, resource, action, scope, required_attrs).
# The Kernel ships NO business conditional policies (self-access must stay gated by an
# explicit permission + attrs policy declared by the owning business module in Phase 7).
# Populate this list (or implement register_authorization_policies in a business manifest)
# when the first real ABAC rule lands — the mechanism below is the production path.
_PRODUCTION_CONDITIONAL_POLICIES: list[tuple[str, str, str, str, Sequence[str]]] = []

def register_authorization_policies(self, enforcer: Any) -> None:
    from kernel.authz.services.policy_loader import register_conditional_policy
    for role, resource, action, scope, required_attrs in _PRODUCTION_CONDITIONAL_POLICIES:
        register_conditional_policy(enforcer, role, resource, action, scope, required_attrs)
    logger.debug("[AUTHZ] Registered %d production conditional policies", len(_PRODUCTION_CONDITIONAL_POLICIES))
```

- The factory already invokes this hook for every manifest after the DB loader (`app_factory.py:193–199`) — no factory change needed.
- `register_conditional_policy` is exercised today **only in tests**; this change makes the production registration path real (empty but wired), so a Phase-7 business module's first conditional policy works with zero kernel changes.
- "match_attrs exercised in production" is satisfied at the **function level** (registered at startup, `app_factory.py:189`) and proven at the **boundary level** by the new raw-enforcer tests; runtime *evaluation* of a conditional policy happens once the first business module declares one (explicitly out of scope here — no invented business rule).
- Verification test (REQ-AUTHZ-FIX-REG-01 scenarios): in `test_authz_abac.py`, patch `AuthorizationManifest._PRODUCTION_CONDITIONAL_POLICIES` with one entry, run `manifest.register_authorization_policies(e)` on a fresh enforcer → assert the 5-arg policy is in `e.get_all_policies()` and `policy_loader._conditional` holds the entry; then assert `register_casbin_policies`/DB loader path is unchanged (non-conditional policies still registered with `""` attrs).

### D9 — Policy identification includes `attrs` + scope filter (REQ-AUTHZ-FIX-PID-01; P1; task D-D)

**Decision: `_extract_policy_id` returns a 5-part id `role:resource:action:scope:attrs`, filters candidates on scope (mirroring the matcher), and verifies the attribute condition before identifying the policy. Audit-only — it never grants (it is called only after `enforce()` returned True).**

`backend/kernel/authz/services/authorization_service.py` (L204–213):

```python
def _extract_policy_id(self, sub: dict, obj: dict, action: str) -> str | None:
    """Extract the matching policy ID for audit purposes (best-effort, never grants)."""
    try:
        policies = self._enforcer.get_filtered_policy(0, sub.get("role", ""))
        for p in policies:
            if len(p) < 5:
                continue
            if p[1] != "*" and p[1] != obj.get("name"):
                continue
            if p[2] != "*" and p[2] != action:
                continue
            # Scope filter — mirrors casbin_model.conf matcher semantics
            if not self._policy_scope_matches(p[3], sub, obj):
                continue
            # Only identify a policy whose attribute condition actually holds
            if not match_attrs(sub, p[4]):
                continue
            return f"{p[0]}:{p[1]}:{p[2]}:{p[3]}:{p[4]}"
    except Exception:
        pass
    return None

@staticmethod
def _policy_scope_matches(scope: str, sub: dict, obj: dict) -> bool:
    if scope == "any":
        return True
    if scope == "tenant":
        return str(sub.get("client_id", "")) == str(obj.get("client_id", ""))
    if scope == "institution":
        return (str(sub.get("client_id", "")) == str(obj.get("client_id", ""))
                and str(sub.get("institution_id", "")) == str(obj.get("institution_id", "")))
    return False
```

- **Why attrs + match_attrs verification:** `_enforce` calls this only after `enforce()` was True, so at least one policy fully matched; iterating with name/action/scope/attrs checks guarantees the *first* passing policy is a policy that genuinely matched — and two conditional policies differing only in attrs now yield distinct ids (`...:institution:is_subject_teacher` vs `...:institution:is_class_teacher`).
- **Scope filter** removes the prior "may name a non-matching scope" inaccuracy (a `tenant`-scope policy can no longer be reported when an `institution`-scope one matched).
- No persistent policy-ID system exists (confirmed) and none is introduced — ids remain derived strings for `AuthorizationAudit.policy_id`; `AuthorizationDecision` shape is unchanged.
- Tests (REQ-AUTHZ-FIX-PID-01): two conditional policies `(Teacher, homework, create, institution, "is_subject_teacher")` and `(..., "is_class_teacher")`; ALLOW each in turn → `policy_id` ends with the respective attrs field and the two ids differ; and an enforcement without the helper (`enforce()` bool) is unaffected by the helper (identification never influences the decision — structural, since the helper is post-hoc).

### D10 — Multi-role attribute resolution — deferred (P1; task D-E)

**Decision: do NOT change `required_attributes`. Document as future optimization.**

`policy_loader.required_attributes` (L130–143) unions required attrs across **all** subject roles for the matching `(resource, action)` in the conditional catalog. Behavior analysis:
- **Correctness:** the union is a superset of what any single role needs; attributes are resolved once and injected into every role's subject dict before the per-role Casbin loop (`authorization_service.py:165–202`). A role whose policy doesn't reference the extra attribute is unaffected by its presence in `sub`.
- **Not a bug, but conservative:** if role A contributes `attrX` and subject roles are `[A, B]` where only B's policy applies, `attrX` is still resolved — an extra provider call, and a **fail-closed bias** if `attrX` has no provider (the request DENies with `UNRESOLVED_ATTRIBUTE` even though B's policy would have allowed). In production today the conditional catalog is empty (D8), so this is latent.
- **Decision:** defer to Phase 7 when real conditional policies exist and the resolution set can be scoped per-role (e.g., resolve the union of attrs across *only* the roles that hold a matching policy, or resolve per-role and cache). Changing now would touch resolution semantics without a production conditional policy to validate against — violates "P1 recommended only if a clean solution exists without destabilizing". Recorded as a future-optimization note in the docstring + this design.

### D11 — Spec-consistency: stale "PO bypass SHALL stay" lines (REQ-AUTHZ-FIX-PO-01; P0-adjacent)

**Decision: this change's delta spec supersedes the archived bypass-retention wording. The main specs still containing "the PO `require_permission` bypass ... SHALL STAY" — `openspec/specs/platform-owner-separation/spec.md` (L91–93, D28) and `openspec/specs/client-user-bootstrap/spec.md` (L230–233, D8) — are NOT edited during this change (this change's delta domain is `authorization` only). The archive step and/or a follow-up delta MUST amend those two lines**, otherwise main specs contradict the new behavior. Flagged as an explicit archive-time action; task phase must record it.

### D12 — Test-impact inventory (cross-cutting; P0)

**Decision: enumerate and classify every existing test touching the removed behavior so the apply phase has a complete, deterministic list.** (Full enumeration in §6.) Classes: (a) unaffected — D11-fixture enforcer tests that never exercise the pipeline; (b) updated — app-level PO bypass assertions (D7); (c) new — raw-boundary, PO security, provider-failure, RBAC-never-bypassed, registration, policy-id tests; (d) the fixed stub.

---

## 3. Casbin Model — UNCHANGED

`backend/kernel/authz/casbin_model.conf` is **not modified**. The matcher already executes `match_attrs(r.sub, p.attrs)`:

```
m = g(r.sub.role, p.sub) && (p.obj == "*" || p.obj == r.obj.name) && (p.act == "*" || p.act == r.act)
    && (p.scope == "any" || (p.scope == "tenant" && r.sub.client_id == r.obj.client_id)
        || (p.scope == "institution" && r.sub.client_id == r.obj.client_id && r.sub.institution_id == r.obj.institution_id))
    && match_attrs(r.sub, p.attrs)
```

| Aspect | Before | After |
|---|---|---|
| `[policy_definition]` | `p = sub, obj, act, scope, attrs` (5) | unchanged |
| matcher ABAC clause | `&& match_attrs(r.sub, p.attrs)` | unchanged |
| `match_attrs` body | `bool(sub.get(a))` truthiness | **strict `sub.get(a) is True`** (D1) |
| non-conditional policy load | 5-arg with `""` attrs | unchanged |
| conditional policy load | test-only (`register_conditional_policy`) | + production path wired (D8) |
| subject | `{role, client_id, institution_id, **resolved_attrs}` | unchanged (+ PO role normalization upstream, D5) |

The 5-field arity migration risk from the base change is already resolved on `main` (loader + all harnesses pass 5 args) — nothing to redo here.

---

## 4. Migration Detail

New migration `backend/migrations/versions/<rev>_fix_c04_abac_po_permissions.py` (exact revision id decided at tasks phase via `alembic revision` against the current head).

**Idempotency:** all inserts use `ON CONFLICT ... DO NOTHING`; the scope `UPDATE` is idempotent; downgrade is reverse-ordered.

**Post-migration verification query (documented in the migration docstring):**

```sql
SELECT r.name AS role, p.name AS permission, rp.scope
FROM role_permission rp
JOIN role r ON r.id = rp.role_id
JOIN permission p ON p.id = rp.permission_id
WHERE r.name = 'platform_owner'
ORDER BY p.name;
-- expect: client.* 5, institution_type.* 3, config.* 8 — all scope 'any'
```

**Deployment / rollback sequence:**
1. Apply migration (adds `client.create` permission, 8 new PO rows, re-seats PO scope to `any`). Old code + new DB: PO still bypasses — no behavior change.
2. Deploy code in the same release (bypass removal + normalization + registration wiring). Restart required (startup policy load).
3. Rollback code first, then `downgrade()` (removes PO rows for client./institution_type., deletes `client.create`, restores config.* PO scope to `'institution'`).

**Risk note:** a PO session that was active across the code deploy keeps its old JWT (no roles claim) — harmless: normalization derives the label at request time; no token re-issue needed.

---

## 5. File Impact Map

### New files

| File | Content |
|---|---|
| `backend/migrations/versions/<rev>_fix_c04_abac_po_permissions.py` | `client.create` permission + PO platform `role_permission` seeds (scope `any`) + config.* scope re-seat (D6) |
| `openspec/changes/fix-c04-authz-abac-enforcement/design.md` | this file |

### Modified files

| File | Change |
|---|---|
| `backend/kernel/authz/services/authorization_service.py` | remove Step-1 PO bypass (D4); tighten `match_attrs` to strict boolean (D1); `_extract_policy_id` → 5-part id + scope filter + attrs verification, add `_policy_scope_matches` (D9); provider-contract docstring |
| `backend/kernel/authz/models/authorization_types.py` | `SubjectContext.from_tenant_context` PO role-label normalization (D5) |
| `backend/kernel/authz/dependencies.py` | remove legacy PO bypass in `_check_impl_legacy`; add the same PO role normalization there (D4/D5) |
| `backend/kernel/authz/manifest.py` | `_PRODUCTION_CONDITIONAL_POLICIES` list + wired `register_authorization_policies` (D8) |
| `backend/kernel/authz/services/policy_loader.py` | docstring note on multi-role union deferral (D10) — no code change |
| `backend/tests/test_authz_abac.py` | `TestRawEnforcerBoundary` (D2); fixed `test_failed_abac` (D3); `test_abac_never_bypasses_rbac`, `test_provider_exception_fails_closed` (D3); `_register_prod_po_policies` + `TestPlatformOwnerSecurity` (D7); remove old `test_platform_owner_bypass`; registration + policy-id tests (D8/D9) |
| `backend/tests/test_c04_authz.py` | app-level PO bypass tests → 403 expectations with new names (D7/D12) |
| `backend/tests/test_fees.py` | `test_platform_owner_bypasses_all` → 403 expectation, renamed (D7/D12) |

### Unchanged (explicitly)

`casbin_model.conf`, `kernel/tenant_context.py`, `kernel/middleware.py`, `kernel/db.py` (RLS session vars), migrations 001–021 and all RLS policies, `authorization_types` remainder, `attribute_provider.py` (registry fail-closed already correct), `policy_loader` registration semantics, `require_permission`/`check_permission` signatures + `_build_request` backward-compat (`owner_id` path), route call sites (`obj_client_id=None` fallback preserved), `AuthorizationDecision` shape, frontend-shell, all business modules and their manifests.

---

## 6. Verification Hooks / Test Plan

All requirements map to executable tests. Conventions follow `backend/tests/test_authz_abac.py` (synthetic providers, in-memory policies, no business imports).

### 6.1 REQ-AUTHZ-FIX-ABAC-01 — matcher + raw boundary
| Hook | Test |
|---|---|
| matcher evaluates `p.attrs`; empty/`*`/`""` → true | raw `test_no_attr_falls_back_to_rbac_scope` + all existing `attrs=""` RBAC tests (regression) |
| attr=true → ALLOW | raw `test_attr_true_allows` |
| attr=false → DENY at the raw boundary (no Python pre-check) | raw `test_attr_false_denies` |
| attr=missing → DENY at the raw boundary (`None is True` → matcher false) | raw `test_attr_missing_denies` |
| stub replaced by a real assertion | fixed `test_failed_abac` (§D3) — invokes the pipeline with `is_subject_teacher=false`, asserts DENY `NOT_ASSIGNED_TO_RESOURCE` |

### 6.2 REQ-AUTHZ-FIX-PO-01 — PO through normal pipeline
| Hook | Test |
|---|---|
| no unconditional ALLOW (both code paths removed) | grep-based static guard: Step-1 block and legacy block absent (can extend the existing kernel-boundary static tests, §6.5) |
| PO + `client.read` platform resource → ALLOW | `TestPlatformOwnerSecurity::test_po_client_read_allows` (pipeline, prod-shape matrix) |
| PO → student/teacher/attendance/homework → DENY | `test_po_denied_operational_resources` (parametrized resource list) |
| PO → `user.create`/`institution.read` → DENY | `test_po_denied_unconfigured_permissions` |
| PO role normalization | `test_po_subject_normalization` (from_tenant_context with empty roles) |
| app-level behavior | updated `test_c04_authz` 403 tests + renamed `test_fees` 403 test |

### 6.3 REQ-AUTHZ-FIX-REG-01 — production conditional-policy registration
| Hook | Test |
|---|---|
| declared conditional policies land in the enforcer at startup | `test_production_conditional_policy_registration` (patch `_PRODUCTION_CONDITIONAL_POLICIES` with one entry; assert policy 5-tuple in `get_all_policies()` and `_conditional` catalog populated) |
| non-conditional DB policies unchanged | same test asserts `register_policies_from_map` path still adds `""`-attrs 5-arg policies |

### 6.4 REQ-AUTHZ-FIX-PID-01 — policy identification
| Hook | Test |
|---|---|
| same-signature conditional policies → distinct ids | `test_extract_policy_id_includes_attrs` (two attrs variants; ids differ; each ends with its attrs field) |
| scope-accurate id | `test_extract_policy_id_scope_filtered` (matching `tenant` vs non-matching `institution` policy; helper reports the matching one) |
| never influences the decision | structural: helper is invoked only after `enforce()` True; existing allow/deny tests unchanged |

### 6.5 REQ-AUTHZ-FIX-TEST-01..03 — regression/security/fail-closed + boundary invariants
- Five-case matrix (§D3 table).
- `test_provider_exception_fails_closed` (provider raises → `UNRESOLVED_ATTRIBUTE`, never ALLOW).
- Extend `TestKernelBoundary` static checks (existing, `test_authz_abac.py:480+`): still assert no `business.*` imports / no business ORM names in `kernel/authz/`; add an assertion that no `is_platform_owner: return allow`/`Platform owner bypass` pattern remains in `authorization_service.py` + `dependencies.py`.

### 6.6 Existing test inventory — classification for the apply phase
| Test | File:L | Fate |
|---|---|---|
| `test_platform_owner_bypasses_all_c01` / `bypasses_user_create` / `bypasses_institution_read` (12.6, enforcer-level, D11 **fixture**) | `test_c04_authz.py:256–273` | **keep** (fixture wildcard path, model-semantics tests, never exercises pipeline) — annotate as legacy-D11-fixture |
| `test_platform_owner_bypass_user_create` / `bypass_institution_read` (app-level) | `test_c04_authz.py:395–410` | **update** → 403, renamed (D7) |
| `test_platform_owner_bypasses_all` | `test_fees.py:633` | **update** → 403, renamed (D7) |
| `test_platform_owner_bypass` | `test_authz_abac.py:440` | **replace** with D7 matrix (positive case covered by `client.read → ALLOW`) |
| `test_failed_abac` stub | `test_authz_abac.py:354–362` | **fix** (D3) |
| `TestPlatformOwnerMatrix` (fixture wildcard: create/suspend/terminate/manage/approve) | `test_casbin_permissions.py:104–115` | **keep** (fixture semantics; wildcard stays in fixture) — superseded by production-shape PO tests; optional follow-up: migrate fixture to the explicit matrix |
| `test_platform_owner_*` app tests via `platform_client` fixture (conftest AllowAll enforcer) | `test_api.py`, `test_lifecycle.py`, `test_client_user_bootstrap.py` | **keep** — `client-user-bootstrap` PO endpoints use `require_platform_owner` only; platform PO routes evaluate via the real DB-loaded enforcer which, post-migration, carries the explicit PO policies → still granted. Verify the test harness applies migrations to the test DB (else PO app tests 403 — see Risks R6). |

---

## 7. Tradeoffs

| Decision | Alternative | Why chosen | Cost |
|---|---|---|---|
| Strict `is True` match_attrs (D1) | Keep `bool()` truthiness | Kills string-`"false"` ALLOW vector; fail-closed on any non-bool | Providers must return real bools (documented contract); numpy/int values fail closed |
| PO role normalization at the authz boundary (D5) | Middleware injection; pipeline special case | Contained to authz layer; single production construction point; zero effect on other roles consumers | Two call sites to keep in sync (service factory + legacy fallback) |
| Explicit PO permission migration incl. `client.create` + `institution_type.*` (D6) | Only the 4 client.* perms; leave seeds untouched (breaking) | Grounded in actual platform routes + ADR D11; keeps "existing platform/client access continues to work per configured permissions" (DoD) | 9 new PO rows; one new permission row (`client.create`) |
| Scope `'any'` for PO rows, incl. re-seat of config.* (D6) | Leave `'institution'` (vacuous `""==""` pass) | Semantically correct (platform-level ops); removes fragile empty-equality dependency | PO config rows change scope (only platform_owner rows; verified no other consumer relies on their `'institution'` scope) |
| Keep D11 wildcard fixtures, add production-shape fixtures (D7/D12) | Rewrite all D11 fixture tests | Minimal churn; legacy fixture tests still validate model semantics; production truth carried by the new tests | Two PO fixture shapes coexist (legacy vs prod) — annotated, with optional follow-up to migrate |
| Wire registration hook with an empty declared list (D8) | Register a Kernel-owned conditional policy | No invented business rule can alter production semantics; mechanism fully exercised by tests | match_attrs runtime evaluation of a conditional policy begins only with Phase 7 (acceptable — precondition now in place) |
| `_extract_policy_id` full matcher-mirror filter (D9) | Just append `:attrs` | Ids name an actually-matched policy; distinct attrs variants; scope-accurate | Slightly more code in audit helper (still post-hoc, never grants) |
| Defer multi-role resolution optimization (D10) | Per-role required-attr sets now | No production conditional policies to validate against; correctness unaffected today | Latent fail-closed bias documented for Phase 7 |

---

## 8. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **PO platform surface broken if migration/code skew** | Platform routes 403 for PO | Same-release deployment; migration-first sequence (§4); post-migration verification query; test DB executes migrations (verify harness) |
| R2 | **PO app-level tests depend on DB seeds** | PO platform app tests fail if test DB lacks the new rows | Confirm alembic migrations run in the test harness; the 403-flip tests are deterministic in either service state (D7) |
| R3 | **Strictness regression** (providers returning non-bool) | Unexpected 403s | Provider contract docstring; `is_self` + all synthetic providers already return bools; raw-boundary tests pin semantics |
| R4 | **Stale specs** ("PO bypass SHALL STAY" in `platform-owner-separation` / `client-user-bootstrap`) | Spec/prod contradiction; reviewers confused | Archive-time action + follow-up delta (D11); design flags it now |
| R5 | **Legacy D11 fixture encodes the removed wildcard** | Future readers may believe production PO retains `*.*` | Production-shape fixtures + tests carry the truth; legacy fixture annotate d; optional follow-up migration of the fixture |
| R6 | **`_AllowAllEnforcer` override illusion** (inert on the modern path) | App tests may silently not exercise real policy | Noted; PO app tests re-verified against the real DB-loaded enforcer; no change to the override in this fix |
| R7 | **Empty-id scope vacuity elsewhere** (non-PO `tenant`/`institution` with `""` ids) | Vacuous passes for other roles in odd contexts | Pre-existing, out of scope; PO rows moved to `any` so the fix doesn't *add* vacuous cases; noted for a future scope-hardening pass |
| R8 | **Policy-id helper cost** | Trivial (post-hoc, filtered policy list) | Bounded by role's policy count; wrapped in try/except as before |
| R9 | **Test-surface churn from 403 flips** | Widened diff | Inventory in §6.6 is exhaustive per scout + reads; run full suite in apply phase |

---

## 9. Residual Gaps Resolved

| Gap (proposal §2/§8) | Resolution |
|---|---|
| Matcher references `match_attrs` but enforcement unproven | Raw-boundary tests (D2) + strict semantics (D1) |
| `test_failed_abac` vacuous | Real assertion (D3) |
| PO unconditional ALLOW (2 paths) | Removed (D4); grants via seeded explicit perms (D6); effective role label (D5); security tests (D7) |
| Production registration hooks `pass` | Wired declared-list registration (D8) |
| `_extract_policy_id` collides, scope-blind | 5-part id + matcher-mirror filter (D9) |
| Multi-role attr union conservative | Deferred, documented (D10) |
| `client.create` permission missing while a route requires it | New permission row + PO seed (D6) |
| Main specs say "PO bypass SHALL STAY" | Superseded by this delta; archive-time spec amendment needed (D11) |

---

## 10. Open Questions / Deferred

| # | Item | Status |
|---|---|---|
| 1 | Spec wording "truthy" vs strict `is True` implementation | Resolved to strict (D1); if reviewers insist on literal truthiness, one-line revert — not recommended |
| 2 | Stricter PO write matrix (e.g., split `client.create` out of PO scope; add `client.suspend/terminate` family) | Deferred to the platform capability owner; migration is a single file to trim |
| 3 | `approve_ownership_transfer` guard parity (`require_permission("client","transfer_ownership")`) | Deferred (P2, recommended follow-up) |
| 4 | Migrate legacy D11 wildcard fixtures to the production-shape matrix | Deferred (optional follow-up; fixtures annotated) |
| 5 | Multi-role required-attr scoping (per-role resolution) | Deferred to Phase 7 (D10) |
| 6 | Spec amendment for `platform-owner-separation` / `client-user-bootstrap` bypass lines | Archive-time action for THIS change (D11) |

---

> **End of design.** This document is the technical design input to the tasks phase. It does not modify specs or implement code.