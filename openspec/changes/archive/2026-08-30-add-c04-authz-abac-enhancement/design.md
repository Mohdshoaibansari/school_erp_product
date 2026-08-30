# Design — C-04 AuthZ Kernel ABAC Enhancement

> **Change:** `add-c04-authz-abac-enhancement`
> **Capability:** C-04 Authorization / AuthZ Kernel
> **Phase:** sdd-stack design
> **Traceability:** Design decisions trace to the delta spec requirements (`REQ-AUTHZ-ABAC-01..07`, `REQ-AUTHZ-ABAC-M01..M05`) and PRD acceptance criteria (`AC-1..AC-48`).
> **Decisional inputs:** `proposal.md` (36 sections), `docs/prd/c04-authz-abac-enhancement.md` (§8 — 11 resolved decisions Q1–Q11), `docs/prd/c04-authz-abac-enhancement-impact.md` (§4 code impact map, §8 residual gaps).
> **Status:** Design phase — ready for tasks breakdown.

---

## 0. Scope and Boundary

This design covers **the AuthZ Kernel only**. It defines the Kernel-side contract that future business modules (Teacher, Student, Parent, Homework, Attendance — Phase 7) will implement. No business ORM model is imported into the Kernel; the dependency direction is strictly:

```
Business Module  ──►  AuthZ Kernel Contract      (allowed)
AuthZ Kernel     ──►  Business Module            (forbidden)
```

**In scope:** authorization types, `AuthorizationAttributeProvider` contract + `ProviderRegistry`, `AuthorizationService.authorize()` pipeline, structured reason codes, Casbin model extension for domain attributes, multi-role evaluation, generalized `is_self`, policy loader extension for conditional policies, observability.

**Out of scope (explicit):** any Teacher/Student/Parent/Homework/Attendance/Academic provider implementation (Phase 7), batch `authorize_many()` execution (designed only), dynamic DB policy table, runtime policy reload, permission CRUD, fine-grained scopes.

**Reference implementation read for grounding:**
- `backend/kernel/authz/dependencies.py` — `require_permission()`/`check_permission()`/`_check_impl()` use `roles[0]`, raise `HTTPException(403)` inline, hardcode an `owner_id` self-access bypass.
- `backend/kernel/authz/casbin_model.conf` — 4-field `p = sub, obj, act, scope`, matcher `g(r.sub.role, p.sub)` + `client_id`/`institution_id` scope.
- `backend/kernel/authz/services/policy_loader.py` — loads `(role, resource, action, scope)` from `role_permission`, maintains in-memory `_permission_map`.
- `backend/kernel/authz/manifest.py` — `register_casbin_policies` + `on_startup` hooks.
- `backend/kernel/authz/models/permission.py` — `Permission` / `RolePermission` ORM (unchanged).
- `backend/kernel/tenant_context.py` — `TenantContext` (client_id, institution_id, user_id, is_platform_owner, user_tier, roles).

---

## 1. Architecture Overview — Before / After

### 1.1 Before (generic RBAC + scope only)

```
Route (sync)
  ├─ Depends(require_permission("homework", "create"))      # or inline check_permission()
  └─ _check_impl(ctx, enforcer, ...):
        sub = {"role": roles[0], client_id, institution_id}  # ← ONLY FIRST ROLE
        obj = {"name", client_id, institution_id}
        owner_id == user_id  →  bypass (hardcoded self-access)
        enforcer.enforce(sub, obj, action)  → bool
        deny  →  raise HTTPException(403, "Permission denied")   # no reason code
```

Problems:
1. `roles[0]` — multi-role users (HOD+Teacher, Principal+Teacher) are reduced to one role.
2. No structured decision — denial is an opaque `403 "Permission denied"`.
3. No domain attributes — Casbin only sees `client_id`/`institution_id`; cannot answer "is this teacher assigned to this section?".
4. Self-access is a hardcoded special case, not a generic attribute.

### 1.2 After (RBAC + scope + domain-attribute ABAC)

```
Route (sync or async)
  ├─ Depends(require_permission(resource, action, ...))     # thin adapter (async dependency)
  └─ inline await check_permission(...)                      # thin adapter (async helper)

AuthorizationService.authorize(AuthorizationRequest)          # NEW pipeline (async)
  1. platform_owner bypass                        → ALLOW (unchanged)
  2. no roles                                     → DENY MISSING_PERMISSION
  3. determine required attrs (policy catalog)    → union over matching conditional policies
  4. resolve required attrs via ProviderRegistry  → request-scoped cache, fail-closed
  5. Casbin: loop per role (all roles)            → ANY role allow = ALLOW
  6. classify denial reason (catalog + attr map)  → structured reason code
  7. emit audit record                            → correlation_id, roles, scope, policy_id, reason
  → AuthorizationDecision(allowed, reason, policy_id)

Casbin model (extended)
  p = sub, obj, act, scope, attrs                 # attrs = required boolean attribute names
  matcher += match_attrs(r.sub, p.attrs)          # Kernel-registered custom function
```

The enforcer remains the **sole granter**. The Python-side reason discriminator runs **only on DENY** to label *why*; it never grants access.

---

## 2. Architecture Decisions

### D1 — Authorization types (REQ-AUTHZ-ABAC-01, AC-1..AC-5)

New module `backend/kernel/authz/models/authorization_types.py` defines five Kernel-owned types. All are plain `@dataclass` (frozen where possible) with no ORM dependencies.

```python
@dataclass(frozen=True)
class SubjectContext:
    user_id: str | None
    roles: tuple[str, ...]
    client_id: uuid.UUID | None
    institution_id: uuid.UUID | None
    user_tier: str | None
    is_platform_owner: bool

@dataclass(frozen=True)
class ResourceContext:
    resource_type: str                      # e.g. "homework"
    resource_id: str | uuid.UUID | None     # e.g. "HW001"
    client_id: uuid.UUID | None
    institution_id: uuid.UUID | None
    data: Mapping[str, Any]                 # domain fields: section_id, subject_id, owner_id, ...

@dataclass
class AuthorizationAttributes:
    values: dict[str, Any]                  # resolved domain attributes
    # provenance + fail-closed bookkeeping (D5/D6)
    resolved_by: dict[str, str]             # attr name -> provider name
    unresolved: set[str]                    # required-but-unresolved (fail-closed)

@dataclass(frozen=True)
class AuthorizationRequest:
    subject: SubjectContext
    resource: ResourceContext
    action: str
    attributes: AuthorizationAttributes = field(default_factory=AuthorizationAttributes)

@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: AuthorizationReasonCode
    policy_id: str | None = None
    audit: AuthorizationAudit | None = None  # D13
```

**Decision.** `SubjectContext` is derived from `TenantContext` (a `from_tenant_context()` constructor). `ResourceContext.data` is the generic extension point for domain-specific fields — this is how business modules supply `section_id`, `subject_id`, `academic_year_id`, `student_id`, `owner_id` without the Kernel importing their models. `AuthorizationAttributes` lives on the request and is populated during the pipeline (the proposal's "request composed of subject + resource + action + attributes" is realized by the service filling `request.attributes`).

**Tradeoff.** `ResourceContext.data` is untyped (`Mapping[str, Any]`) to keep the Kernel generic; the cost is that attribute names are stringly-typed and validated at the provider boundary (a provider that can't interpret a field fails closed). Typed per-resource contexts were rejected because they would import business concepts into the Kernel.

### D2 — Structured reason code enum (REQ-AUTHZ-ABAC-03, AC-18..AC-20)

New module `backend/kernel/authz/models/reason_codes.py` defines `AuthorizationReasonCode` as a `str`-backed `enum.Enum` (stable, machine-readable values).

The nine required codes plus two Kernel-internal refinements:

| Code | Meaning | Produced when |
|---|---|---|
| `MISSING_PERMISSION` | No role has the `(resource, action)` permission | RBAC deny, no matching policy |
| `INVALID_SCOPE` | Permission exists but no scope matches (fallback) | scope mismatch not otherwise classified |
| `TENANT_ACCESS_DENIED` | `sub.client_id != obj.client_id` | tenant scope violated |
| `INSTITUTION_ACCESS_DENIED` | client matches, institution differs | institution scope violated |
| `ATTRIBUTE_CONDITION_FAILED` | Required attribute resolved but false (generic) | default attribute-failure code |
| `NOT_ASSIGNED_TO_RESOURCE` | `is_assigned_to_resource`/`is_class_teacher`/`is_subject_teacher` resolved false | teacher-style attribute failed |
| `NOT_SELF` | `is_self` resolved false | self-access attribute failed |
| `NOT_PARENT_OF_RESOURCE` | `is_parent_of_resource` resolved false | parent relationship attribute failed |
| `POLICY_DENIED` | Explicit deny or unmatched (fallback) | defensive fallback |
| `NO_ROLES` | Subject has zero effective roles | pre-RBAC (Kernel internal) |
| `UNRESOLVED_ATTRIBUTE` | Required attribute has no provider / provider errored | fail-closed (D6) |

**Decision.** Reason codes are an enum (PRD Q5), safe for internal logs and controlled API responses. The 403 response body carries **only** the machine-readable code plus a generic message; policy internals and attribute values are never echoed to clients (AC-20). `NO_ROLES` and `UNRESOLVED_ATTRIBUTE` are additive refinements above the required nine (spec says "at least").

**Attribute→reason mapping.** To keep providers decision-agnostic (they return facts, never reasons — AC-8), the Kernel owns a small static map from false attribute name → specific reason code:

```python
_ATTRIBUTE_DENY_REASON = {
    "is_self": AuthorizationReasonCode.NOT_SELF,
    "is_parent_of_resource": AuthorizationReasonCode.NOT_PARENT_OF_RESOURCE,
    "is_assigned_to_resource": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
    "is_class_teacher": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
    "is_subject_teacher": AuthorizationReasonCode.NOT_ASSIGNED_TO_RESOURCE,
}
# default: ATTRIBUTE_CONDITION_FAILED
```

This makes every one of the nine required codes reachable without business logic in the Kernel.

### D3 — `AuthorizationAttributeProvider` contract (REQ-AUTHZ-ABAC-02, AC-6..AC-10)

New module `backend/kernel/authz/services/attribute_provider.py` defines the Kernel-owned abstract contract:

```python
class AuthorizationAttributeProvider(ABC):
    name: str                                          # stable provider identifier
    resource_types: frozenset[str]                     # "*" = any resource type
    attributes: frozenset[str]                         # attribute names it can resolve

    @abstractmethod
    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]:
        """Return ONLY the facts this provider owns. Never an allow/deny decision."""
```

**Decision.**
- **Async** `resolve()` (PRD Q1): providers may perform async repository/DB reads; Casbin evaluation itself remains synchronous and in-memory.
- Providers return a **subset** of their declared `attributes` (facts only, never a decision — AC-8).
- Providers are **stateless with injected dependencies** (PRD Q4): no request-scoped state stored on the provider instance; request-specific data flows through the `AuthorizationRequest` argument.
- Providers are **boundary-trusted server-side code** (AC-22): they are registered in-process, not callable from client input. The Kernel never trusts client-supplied attribute values (D6).

**Backward-compat guard (AC-9, AC-14):** the contract lives in `kernel/authz/` and imports nothing from `business/`. The Kernel `__init__`/service modules never import Teacher/Student/Parent/Homework ORM models.

### D4 — `ProviderRegistry` + required-attribute determination (REQ-AUTHZ-ABAC-02, AC-6..AC-10, AC-26..AC-28, AC-34..AC-35)

`ProviderRegistry` maps `(resource_type, attribute_name) → provider`:

```python
class ProviderRegistry:
    def register(self, provider: AuthorizationAttributeProvider) -> None: ...
    def providers_for(self, resource_type: str, attribute: str) -> AuthorizationAttributeProvider | None: ...
    def resolve_attributes(self, request, required: set[str]) -> AuthorizationAttributes: ...
```

**Decision — required-attribute determination is lazy/request-driven (PRD Q2, Q11).**
- The Kernel maintains a **policy catalog** (D9) of conditional policies `(role, resource, action, scope, required_attrs)`.
- For a request, the required set = **union** of `required_attrs` across all catalog entries matching any of the subject's roles × `(resource, action)`.
- If the required set is empty → **pure RBAC+scope fallback**; no provider is invoked (AC — "Pure-RBAC fallback").
- Each required attribute is resolved by the provider registered for `(resource_type, attribute)`. A provider registered for `resource_types="*"` serves all resource types.

**Multiple providers (PRD Q3).** Multiple providers may contribute to one request (e.g., one resolves `is_subject_teacher`, another resolves `is_self`). Execution order is **deterministic**: providers are ordered by registration order, then by `provider.name` (stable across runs). Registry registration is idempotent and rejects duplicate `(resource_type, attribute)` claims with a startup error (fail-fast).

**Multiple assignments (AC-34..AC-35).** Providers receive the full request (subject + resource + action) and evaluate the relationship **set** internally — e.g., "is T001 assigned to (section=4A, subject=Mathematics, ay=2026)?" — not a singular `teacher.class_id`. The contract deliberately returns booleans for *this* request's resource, not collection membership lists.

### D5 — Request-scoped attribute caching (AC-28)

**Decision.** Resolved attributes are cached for the **lifetime of one authorization request** (`authorize()` invocation). The cache is a plain dict threaded through the pipeline — never stored on the provider (providers are stateless, PRD Q4) and never shared across requests.

- Within one `authorize()` call, a repeated `(resource_type, attribute)` resolution hits the cache instead of re-invoking the provider.
- Across requests there is **no** caching: attributes are request-specific (AC-27) and must reflect current state; cross-request caching would risk stale authorization data.
- For the future `authorize_many()` batch path (D14), the same cache spans the batch so a given `(resource_type, attribute)` is resolved once and reused across all entries.

**Rationale.** Per-request caching satisfies AC-28 (repeated lookups reusable) and AC-27 (don't load unnecessary collections) without the staleness and invalidation complexity of app-level attribute caches.

### D6 — `AuthorizationService.authorize()` pipeline (REQ-AUTHZ-ABAC-04, AC-21..AC-25)

New module `backend/kernel/authz/services/authorization_service.py` owns the single decision pipeline:

```python
async def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
    # 1. Platform Owner bypass (D28) — unchanged
    if request.subject.is_platform_owner or "platform_owner" in request.subject.roles:
        return ALLOW(reason=ALLOWED)

    # 2. No roles
    if not request.subject.roles:
        return DENY(NO_ROLES)

    # 3. Determine required attributes from the policy catalog
    required = self._catalog.required_attributes(request.subject.roles, request.resource.resource_type, request.action)

    # 4. Resolve required attributes (fail-closed)
    if required:
        request.attributes = await self._registry.resolve_attributes(request, required)
        if request.attributes.unresolved:
            return DENY(UNRESOLVED_ATTRIBUTE)          # AC-21 fail-closed

    # 5. Casbin — evaluate ALL roles (D7), attributes injected into sub
    allow, policy_id = self._enforce(request)

    if allow:
        return ALLOW(reason=ALLOWED, policy_id=policy_id)

    # 6. Classify the denial reason (D2) — runs ONLY on DENY
    reason = self._classify_denial(request)

    # 7. Emit audit record (D13)
    return DENY(reason=reason)
```

**Restrictive ordering (AC — "Restrictive ordering").** The order is fixed: permission/RBAC → scope → ABAC. ABAC **never** grants what RBAC denies: attributes are resolved *after* the catalog confirms a matching `(role, resource, action)` permission exists, and the Casbin matcher requires `g(r.sub.role, p.sub)` (RBAC) *and* scope *and* `match_attrs` (ABAC) to all hold for a single policy. A user with no matching permission is denied with `MISSING_PERMISSION` before any attribute is resolved.

**Fail-closed (AC-21).** Any required attribute with no registered provider, or a provider that raises, is recorded in `attributes.unresolved` → `DENY(UNRESOLVED_ATTRIBUTE)`. Missing attributes are never interpreted as permission.

**No client-supplied trust (AC-22).** The pipeline builds `SubjectContext`/`ResourceContext` **only** from server-side sources (`TenantContext` from middleware; resource data supplied by the business module's own service layer, not the request body). Client-sent `is_class_teacher: true` fields are ignored — they are not routed into `AuthorizationAttributes`.

**Cross-client / institution boundary (AC-23, AC-24).** `subject.client_id`/`institution_id` come from `TenantContext`; `resource.client_id`/`institution_id` come from the fetched resource. The Casbin scope matcher enforces equality. Providers are contractually required to resolve relationships only within `subject.client_id`; the Kernel passes the authenticated context and never widens it.

**RLS defense-in-depth (AC-25).** Authorization success performs no RLS changes; persistence continues under existing RLS session variables (`app.current_client_id`, `app.current_institution_id`, `app.current_user_id`).

**Sync fallback note.** When `required` is empty (every current production caller), step 4 is a no-op and step 5 runs Casbin synchronously — no async I/O, no provider overhead. Async work (provider `resolve`) occurs only when a conditional policy actually requires attributes.

### D7 — Multi-role evaluation (REQ-AUTHZ-ABAC-M03, AC-15..AC-17; resolves gap #1)

**Decision: loop `enforcer.enforce()` per role in Python — pass `roles[]` into the model is NOT used.**

```python
def _enforce(self, request) -> tuple[bool, str | None]:
    sub_base = {
        "client_id": str(request.subject.client_id or ""),
        "institution_id": str(request.subject.institution_id or ""),
    }
    sub_base.update(request.attributes.values)   # resolved domain attributes
    for role in request.subject.roles:
        sub = {**sub_base, "role": role}
        allowed, policy_id = self._enforcer_enforce(sub, request.resource, request.action)
        if allowed:
            return True, policy_id
    return False, None
```

**Rationale (gap #1 resolution).**
- The current model uses `g(r.sub.role, p.sub)` with a **singular** `r.sub.role`. Looping keeps that matcher untouched — each role is individually resolved through `g`, preserving role hierarchy (the `add_role_for_user` self-links and any future hierarchy edges).
- "A valid permission from any applicable effective role may satisfy RBAC" (AC-16) maps directly to "ANY role allows".
- `roles[]`-in-the-model would require rewriting the `g` matcher to a list form (`p.sub in r.sub.roles` or a custom function), which loses/duplicates hierarchy semantics and changes the model's RBAC section — higher regression risk against AC-12/AC-45.
- Cost: `len(roles)` enforce calls (typically 1–3). Casbin `enforce` is in-memory and negligible (AC-26). Attribute resolution happens **once before the loop** (attributes are role-independent), so no N× provider calls.

**Reason-code interaction.** The loop returns `allow/policy_id` only. On full denial, `_classify_denial()` (D6 step 6) uses the catalog (D9) to produce the precise reason — see D9.

### D8 — Casbin model extension for domain attributes (REQ-AUTHZ-ABAC-M02, AC-11..AC-14; resolves gap #2)

**Decision: extend the model with a 5th policy field `attrs` and a Kernel-registered custom matcher function `match_attrs` — a "model matcher" approach, not built-in ABAC (`r.sub.*`) and not Python pre-filtering as the decision mechanism.**

**Proposed `casbin_model.conf`:**

```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act, scope, attrs

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub.role, p.sub) && (p.obj == "*" || p.obj == r.obj.name) && (p.act == "*" || p.act == r.act) && (p.scope == "any" || (p.scope == "tenant" && r.sub.client_id == r.obj.client_id) || (p.scope == "institution" && r.sub.client_id == r.obj.client_id && r.sub.institution_id == r.obj.institution_id)) && match_attrs(r.sub, p.attrs)
```

`match_attrs` is registered at enforcer creation:

```python
def match_attrs(sub: dict, attrs: str) -> bool:
    if not attrs or attrs in ("*", ""):
        return True                       # no attribute condition
    return all(bool(sub.get(a)) for a in attrs.split(","))
```

`attrs` is a comma-separated list of **required boolean attribute names** (e.g., `"is_subject_teacher"`, `"is_self"`). The attribute condition is "all named attributes must be truthy" — which covers every PRD example (`… when is_subject_teacher == true`, `… when is_self == true`, `… when is_parent_of_resource == true`).

**Why model matcher (not built-in ABAC, not Python pre-filter).**
- **Built-in ABAC (`r.sub.*`)** would require each attribute name to be hardcoded in the matcher at authoring time — not generic; the PRD requires policies to declare arbitrary attribute names (AC-39).
- **Python pre-filter as the decision mechanism** would split the decision across Python + Casbin, violating "Casbin remains the single centralized decision engine" (§13). Python pre-filtering is used **only** for reason labeling (D9), never to grant.
- The custom function keeps the matcher **generic** (any attribute name) without a full rules engine (non-goal §5.11): `match_attrs` is a truthiness lookup, not an expression DSL, no `eval`, no arbitrary code.

**Migration (atomic).** Existing policies are registered with 4 args (`add_policy(role, res, act, scope)`). The 5-field `[policy_definition]` requires 5 args. The policy loader (D9) and every test helper (`_register_c01_policies`, `_register_c04_test_policies` in `test_c04_authz.py`, and `test_casbin_permissions.py`) must be updated in the same change to pass `""` as the 5th arg for non-conditional policies. This is a **model migration risk** — see §6.

### D9 — Policy loader extension + policy catalog (REQ-AUTHZ-ABAC-M04, AC-38..AC-39; resolves gap #4)

**Decision: code-driven conditional policies + an in-memory policy catalog. No new DB schema for attribute conditions.**

The existing `_permission_map` (role → `[(resource, action, scope)]`) is evolved into a **policy catalog** that is the single in-memory source feeding **both** the Casbin enforcer **and** the reason discriminator:

```python
# non-conditional (from role_permission DB, unchanged source)
_non_conditional: dict[str, list[tuple[str, str, str]]]            # role -> [(res, act, scope)]
# conditional (code-driven, this enhancement)
_conditional: dict[str, list[tuple[str, str, str, str]]]           # role -> [(res, act, scope, "attr1,attr2")]
```

New Kernel APIs:

```python
def register_conditional_policy(enforcer, role, resource, action, scope, required_attrs: Sequence[str]) -> None:
    """Declare a code-driven conditional policy. Adds to catalog AND enforcer."""
    enforcer.add_policy(role, resource, action, scope, ",".join(required_attrs))
    _conditional.setdefault(role, []).append((resource, action, scope, ",".join(required_attrs)))

def required_attributes(roles, resource, action) -> set[str]: ...
def has_permission(roles, resource, action) -> bool: ...           # non-conditional OR conditional
def matching_scopes(roles, resource, action, sub_client, sub_inst, obj_client, obj_inst) -> list[str]: ...
```

**Registration path.** The manifest gains a hook `register_authorization_policies(enforcer)` (invoked after the DB loader in `app_factory._create_casbin_enforcer`). Business modules (Phase 7) will implement this hook to declare their conditional policies; in this iteration, only **synthetic/test providers** and the **built-in `is_self` policy** (D10) use it. The DB loader (`register_policies_from_map`) is updated to register 5-arg policies with `""` attrs and to populate `_non_conditional`.

**Why code-driven, not DB (gap #4 resolution).** The PRD explicitly defers the dynamic ABAC `Policy` table (§2.2, "DB Admin: no change … ABAC conditions are code-driven through providers"). The existing `permission`/`role_permission` tables are unchanged (impact classification §4: "Low — no schema change"). Introducing a DB schema for conditions now would (a) widen scope, (b) duplicate the conditional-policy source, and (c) require runtime reload (deferred). Code-driven registration keeps conditions versioned with code, testable via synthetic providers, and reversible; a DB policy schema remains a Phase-7/deferred concern.

**Reason discriminator (runs only on DENY).** `_classify_denial()` consults the catalog to label the denial:

1. If **no** role has `(resource, action)` in either catalog → `MISSING_PERMISSION`.
2. Else if no matching scope among the roles that hold the permission:
   - `sub.client_id != obj.client_id` → `TENANT_ACCESS_DENIED`
   - client matches, `sub.institution_id != obj.institution_id` → `INSTITUTION_ACCESS_DENIED`
   - otherwise → `INVALID_SCOPE`
3. Else (permission + scope matched, but Casbin denied) → an attribute condition failed; use the D2 false-attribute map → `NOT_SELF` / `NOT_ASSIGNED_TO_RESOURCE` / `NOT_PARENT_OF_RESOURCE` / `ATTRIBUTE_CONDITION_FAILED`.
4. Defensive fallback → `POLICY_DENIED`.

**Single-source guarantee.** The catalog and the enforcer are populated by the **same** loader/registration code from the **same** source (DB query for non-conditional; code call for conditional). This keeps them in sync by construction, so the catalog-based reason labels cannot drift from what Casbin actually evaluated. The discriminator is **not** a second grant path — Casbin's `enforce()` remains the sole authority; the catalog only annotates a Casbin denial.

### D10 — Generalized `is_self` + `owner_id` backward compatibility (REQ-AUTHZ-ABAC-M05, AC-5; resolves gap #3)

**Decision: ship a built-in `is_self` provider (Kernel-owned, not a business module) and route `owner_id` through it.**

```python
class IsSelfAttributeProvider(AuthorizationAttributeProvider):
    name = "authz.is_self"
    resource_types = frozenset({"*"})
    attributes = frozenset({"is_self"})

    async def resolve(self, request) -> dict[str, Any]:
        owner_id = request.resource.data.get("owner_id") or request.resource.data.get("user_id")
        subject_id = request.subject.user_id
        return {"is_self": bool(owner_id and subject_id and str(subject_id) == str(owner_id))}
```

- The Kernel registers `IsSelfAttributeProvider` at startup (D12), plus a built-in conditional policy: `(role="*", resource="*", action="*", scope="any", attrs="is_self")` is **not** registered — because self-access must be gated by the *permission* too. Instead, self-access becomes a normal ABAC condition declared by business modules in Phase 7 (e.g., `(Student, attendance, read, institution, "is_self")`).
- The `owner_id`/`user_id` field is supplied via `ResourceContext.data` (D1). The hardcoded `if owner_id and user_id match: return` block in `_check_impl()` is **removed** and replaced by `is_self` evaluation inside Casbin.

**`owner_id` backward compatibility (gap #3 resolution).**
- `require_permission(..., owner_id=...)` and `check_permission(..., owner_id=...)` keep their signatures. The adapters map `owner_id` → `ResourceContext.data["owner_id"]`.
- **Verified:** `owner_id` has **zero production callers** today (only `dependencies.py` defines it; no route passes it — see §5). Therefore the semantic shift from "unconditional self-access bypass" to "`is_self` attribute evaluated by Casbin *alongside* the permission" has **no production impact**.
- For any future caller, the correct pattern is: pass `owner_id` **and** declare the conditional permission policy; `is_self=true` then gates access. This is the intended PRD §19 shape (`Student + attendance.read + is_self` → ALLOW) rather than the old identity-only bypass.

### D11 — `require_permission` / `check_permission` as thin async adapters (REQ-AUTHZ-ABAC-M01, AC — "Extend, not replace")

**Decision: extend, not replace (PRD Q6). Both entry points become thin adapters over `AuthorizationService`; signatures are preserved; Platform Owner bypass is retained.**

```python
def require_permission(resource, action, *, obj_client_id=None, obj_institution_id=None, owner_id=None):
    async def _enforce(ctx = Depends(get_tenant_context), enforcer = Depends(get_enforcer)):
        svc = get_authorization_service()
        request = _build_request(ctx, resource, action, obj_client_id, obj_institution_id, owner_id)
        decision = await svc.authorize(request)
        if not decision.allowed:
            raise _to_http_403(decision)      # structured 403 carrying reason.code
    return _enforce

async def check_permission(ctx, enforcer, resource, action, *, obj_client_id=None, obj_institution_id=None, owner_id=None):
    ...
```

- `_build_request` derives `SubjectContext` from `TenantContext` and `ResourceContext` from the explicit object attributes (falling back to ctx values, preserving current behavior — AC-12).
- On denial, `_to_http_403` raises `HTTPException(403, detail={"code": decision.reason.value, "message": "Permission denied"})` — a **structured** 403 (REQ-AUTHZ-ABAC-M01 scenario "Structured 403 on denial") that exposes the code, not policy internals.
- **Platform Owner bypass retained** (unchanged early return in `authorize()` step 1) — AC — "Platform Owner bypass retained".

**Async migration note.** `require_permission` becomes an **async** FastAPI dependency; `Depends(require_permission(...))` call sites need **no change** (FastAPI resolves async dependencies transparently). `check_permission` becomes `async def`; its existing ~10 **sync** route call sites (`client_portal.py` ×8, `identifiers.py` ×1, `roles.py` ×1) must be migrated to `async def` + `await check_permission(...)` in the tasks phase. This is the minimal, mechanical consequence of the resolved async-provider decision (Q1). Alternatives (sync bridge via `asyncio.run()` in a threadpool) were rejected: fragile across sync/async route contexts and inconsistent with the async contract. Since no conditional policy is registered for existing production routes in this iteration, those migrated routes perform no async provider I/O — the pipeline runs the synchronous Casbin path.

### D12 — Provider lifecycle: startup registration (PRD Q4, AC — application-scoped)

**Decision: application-scoped, startup registration via the module manifest.**

- New manifest hook `register_attribute_providers(registry: ProviderRegistry) -> None` (optional, default no-op), invoked by `app_factory` **before** `_create_casbin_enforcer` completes the service wiring.
- The C-04 manifest registers the built-in `IsSelfAttributeProvider` (D10).
- Providers are constructed once at startup with injected dependencies and held by the registry for the app lifetime (stateless — no per-request mutation).
- Registration is **deterministic** (D4): registration order + name ordering; duplicate `(resource_type, attribute)` claims raise at startup (fail-fast).

**Tradeoff (startup vs dynamic).** Startup registration gives deterministic wiring, fail-fast on misconfiguration, and no runtime race on registry mutation. Dynamic per-request registration was rejected: it would re-introduce nondeterminism and complicate the request-scoped cache. Phase-7 business modules register their providers in their own manifest `register_attribute_providers`.

### D13 — Observability / audit context (REQ-AUTHZ-ABAC-06, AC-32..AC-33)

`AuthorizationAudit` dataclass (populated on every decision, attached to `AuthorizationDecision.audit`) captures: `correlation_id`, `user_id`, `client_id`, `institution_id`, `action`, `resource_type`, `resource_id`, `roles`, `scope`, `policy_id`, `decision`, `reason`.

- Emitted via `logger.info`/`logger.warning` on the `kernel.authz` logger at a level appropriate to volume (AC — "Observability overhead").
- **Attribute value redaction (AC-33):** the audit log records the *set of resolved attribute names* (for traceability) but **omits** or redacts values by default; the `AuthorizationAttributes` provenance (`resolved_by`) is logged, raw values are not. A future redaction allowlist can be added per attribute.
- `correlation_id` is threaded from request context (fallback: generated UUID).

### D14 — Batch `authorize_many()` — designed, NOT implemented (AC-29)

**Decision: design the seam, do not implement.** The pipeline is factored so a future `authorize_many(requests) -> list[AuthorizationDecision]` can:

1. Compute the union of required attributes across all requests in one pass.
2. Resolve each distinct `(resource_type, attribute)` **once** (batch-wide cache, reuse D5 cache across entries) — this is the explicit N+1 avoidance the PRD mandates.
3. Group enforcement by role/subject where possible to reuse Casbin policy lookups.

No batch API, no batch caching, no batch tests are shipped in this iteration.

---

## 3. Proposed Casbin Model (before → after)

| Aspect | Before | After |
|---|---|---|
| `[policy_definition]` | `p = sub, obj, act, scope` (4) | `p = sub, obj, act, scope, attrs` (5) |
| `[matchers]` RBAC | `g(r.sub.role, p.sub)` | unchanged |
| `[matchers]` resource/action | `p.obj/act == "*" or == r.*` | unchanged |
| `[matchers]` scope | `any/tenant/institution` on client/institution | unchanged |
| `[matchers]` attributes | — | `&& match_attrs(r.sub, p.attrs)` |
| subject | `{role, client_id, institution_id}` | `{role, client_id, institution_id, **resolved_attrs}` |
| role evaluation | `roles[0]` (Python) | loop per role (Python) |

---

## 4. File Impact Map

### New files

| File | Content |
|---|---|
| `backend/kernel/authz/models/authorization_types.py` | `SubjectContext`, `ResourceContext`, `AuthorizationAttributes`, `AuthorizationRequest`, `AuthorizationDecision`, `AuthorizationAudit` (D1, D13) |
| `backend/kernel/authz/models/reason_codes.py` | `AuthorizationReasonCode` enum + `_ATTRIBUTE_DENY_REASON` map (D2) |
| `backend/kernel/authz/services/attribute_provider.py` | `AuthorizationAttributeProvider` ABC, `ProviderRegistry`, `IsSelfAttributeProvider` (D3, D4, D10) |
| `backend/kernel/authz/services/authorization_service.py` | `AuthorizationService`, `match_attrs` custom Casbin function, policy catalog, reason discriminator (D6, D8, D9) |

### Modified files

| File | Change |
|---|---|
| `backend/kernel/authz/casbin_model.conf` | 5-field `p`, add `match_attrs` to matcher (D8) |
| `backend/kernel/authz/dependencies.py` | `require_permission`/`check_permission` become thin async adapters; remove `roles[0]` and hardcoded `owner_id` bypass; structured 403 (D11, D7, D10) |
| `backend/kernel/authz/services/policy_loader.py` | register 5-arg policies; populate `_non_conditional` catalog; add `register_conditional_policy` + catalog query helpers (D9) |
| `backend/kernel/authz/manifest.py` | add `register_attribute_providers` hook; register `IsSelfAttributeProvider`; wire `AuthorizationService` (D12) |
| `backend/kernel/app_factory.py` | invoke `register_attribute_providers`; register `match_attrs`; build+store `AuthorizationService` singleton (D8, D12) |
| `backend/business/tenant_institution/routes/client_portal.py` | 8 `check_permission` call sites → `async def` + `await` (D11) |
| `backend/kernel/user/routes/identifiers.py` | 1 `check_permission` call site → async (D11) |
| `backend/kernel/user/routes/roles.py` | 1 `check_permission` call site → async (D11) |

### Unchanged (explicitly)

`models/permission.py` (no schema change), `TenantContext`, authentication, auth-infrastructure/RLS, frontend-shell.

---

## 5. Residual Gap Resolutions (impact classification §8)

| # | Gap | Resolution |
|---|---|---|
| 1 | Casbin model extension for multi-role (loop per role vs `roles[]`) | **Loop per role** (D7). Preserves `g` hierarchy, keeps model RBAC section untouched, minimal regression risk; attributes resolved once before the loop. |
| 2 | Attribute-conditional policy format (model matchers vs built-in ABAC vs Python pre-filter) | **Model matcher + custom `match_attrs`** (D8). Generic over arbitrary attribute names, Casbin remains the sole decision engine; Python only labels denial reasons (D9). |
| 3 | `owner_id` backward compatibility | **Preserve signature; generalize to `is_self`** (D10). `owner_id` → `ResourceContext.data["owner_id"]`; built-in `IsSelfAttributeProvider` resolves `is_self`. Zero production callers → zero impact. |
| 4 | Config/DB policy schema for attribute conditions vs code-driven | **Code-driven** (D9). No DB schema; conditions declared via `register_conditional_policy` + manifest hook. Dynamic DB policy table remains deferred. |

The PRD's open questions Q1–Q7 are already resolved in PRD §8; this design implements them as follows: Q1 → async `resolve()` (D3); Q2 → lazy/request-driven determination (D4); Q3 → multiple providers, deterministic order (D4); Q4 → startup registration, stateless (D12); Q5 → enum (D2); Q6 → extend not replace, restrictive ordering (D6, D11); Q7 → implicit fail-closed, no no-op default provider (D6).

---

## 6. Tradeoffs

| Decision | Alternative | Why chosen | Cost |
|---|---|---|---|
| Loop `enforce()` per role (D7) | `roles[]` into model | Preserves `g` hierarchy + RBAC matcher; minimal regression risk | `len(roles)` enforce calls (negligible) |
| Model matcher `match_attrs` (D8) | Built-in ABAC `r.sub.*`; Python pre-filter | Generic attribute names; Casbin stays sole decision engine | 5-field policy arity migration; custom function to register |
| Custom function vs condition DSL | `eval()` / rules engine | No arbitrary code; truthiness lookup only; avoids "generic rules engine" non-goal | Limited to "all-required-attrs-truthy" conditions (sufficient for PRD examples) |
| Code-driven conditional policies (D9) | DB policy table | Matches PRD deferral; versioned with code; no schema/runtime reload | Requires redeploy to change conditions (acceptable; runtime reload deferred) |
| Catalog-based reason labeling (D9) | Casbin explain/staged probes | Cheap in-memory; precise codes; no second grant path | Catalog must stay in sync with enforcer (guaranteed by single source) |
| Request-scoped cache (D5) | App-level cache | No staleness/invalidation; satisfies AC-27/28 | Re-resolves per request (by design) |
| Startup provider registration (D12) | Dynamic registration | Deterministic, fail-fast, no race | No runtime provider hot-swap |
| Async entry points (D11) | Sync bridge (`asyncio.run`) | Matches async contract (Q1); future-proof | ~10 sync route call sites migrate to async |
| `is_self` via Casbin (D10) | Keep hardcoded bypass | First-class ABAC, removes special case | `is_self` now also requires the permission (intended; zero current callers) |
| Structured reason codes (D2) | Free-form strings | Testable, machine-readable, controlled API surface | Enum must stay stable (additive only) |

---

## 7. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Casbin model migration (5-field `p`)** | 4-arg policies break if any registration path is missed | Update loader + all test helpers atomically; regression suite (AC-45); startup smoke check that `get_all_policies()` is non-empty and 5-tuples |
| **Fail-closed surprises** | Missing/unregistered provider → unexpected 403 | Explicit `UNRESOLVED_ATTRIBUTE` code + audit log distinguishes it from `ATTRIBUTE_CONDITION_FAILED`; synthetic tests assert fail-closed (D6) |
| **Cross-tenant leakage** | Provider resolves outside `client_id` | Contract passes authenticated context; scope matcher still enforces client/institution; RLS remains defense-in-depth (AC-25); security tests (client A→B DENY) |
| **N+1 queries** | Per-request provider lookups multiply | Request-scoped cache (D5); batch seam designed for single-resolution (D14); providers resolve only required attributes (AC-27) |
| **Reason-label drift** | Catalog label ≠ actual Casbin denial cause | Single source: loader/registration feeds both catalog and enforcer; labels never grant (D9) |
| **`require_permission` backward compat** | Existing callers break | Signatures preserved; `obj_*` fallback to ctx unchanged; Platform Owner bypass retained; regression tests (AC-12/AC-45) |
| **Async route migration** | Sync→async conversion of ~10 handlers | Mechanical, low-risk; those routes register no conditional policies in this iteration so no async provider I/O is added; covered by existing route tests |
| **Over-engineering** | Building framework before business need | Synthetic providers (Phase 6) validate contract; no DB schema, no rules engine, no batch impl |

---

## 8. Verification Hooks

All requirements are validated by testable hooks. Existing test conventions live in `backend/tests/test_c04_authz.py` and `backend/tests/test_casbin_permissions.py`.

### 8.1 Unit tests (AC-43)

| Hook | Requirement |
|---|---|
| Single role allow/deny | RBAC unchanged (AC-12, AC-45) |
| Multiple roles: `[HOD, Teacher]` where only `Teacher` has the permission → ALLOW | AC-15..AC-17, REQ-AUTHZ-ABAC-M03 |
| Missing permission → `MISSING_PERMISSION` | REQ-AUTHZ-ABAC-04 |
| Tenant scope mismatch → `TENANT_ACCESS_DENIED`; institution mismatch → `INSTITUTION_ACCESS_DENIED` | AC-44, D9 |
| Successful ABAC: synthetic provider returns `is_subject_teacher=true` → Casbin ALLOW | AC-46, REQ-AUTHZ-ABAC-07 |
| Failed ABAC: `is_subject_teacher=false` → DENY `NOT_ASSIGNED_TO_RESOURCE` | AC-47, D2 |
| Missing required attribute (no provider) → DENY `UNRESOLVED_ATTRIBUTE` (fail-closed) | AC-21, D6 |
| Multiple assignments (provider checks set membership, not singular) | AC-34..AC-35 |
| Conflicting assignments (assigned to 1A, requested 1B → false) | AC-43, D4 |
| Pure-RBAC fallback when no attributes required → provider not invoked | REQ-AUTHZ-ABAC-02, D4 |

### 8.2 Security tests (AC-44)

| Hook | Requirement |
|---|---|
| Client A → Client B resource = DENY `TENANT_ACCESS_DENIED` | AC-23, D9 |
| Institution A → Institution B = DENY `INSTITUTION_ACCESS_DENIED` | AC-24, D9 |
| Teacher assigned to 1A → 1A = ALLOW; → 1B = DENY | AC-44, D4 |
| Student S1 → S1 attendance = ALLOW; S1 → S2 = DENY `NOT_SELF` | AC-44, D10 |
| Client-supplied `is_class_teacher: true` in body is ignored (attribute resolved server-side) | AC-22, D6 |

### 8.3 Regression tests (AC-45)

- Existing `test_c04_authz.py` and `test_casbin_permissions.py` pass unchanged after the loader/model migration (5-arg policies with `""` attrs).
- Platform Owner bypass still returns before the pipeline.
- `require_permission`/`check_permission` still raise 403 on denial (now with structured `code`), still allow on grant.

### 8.4 Synthetic-attribute demonstration (AC-46..AC-48)

A test-only provider (e.g., `SyntheticTeacherProvider` returning `is_subject_teacher` from a fixed map keyed by `resource.data["section_id"]`) plus a test-registered conditional policy `(Teacher, homework, create, institution, "is_subject_teacher")` demonstrates ALLOW/DENY with **no** Teacher/Homework/Academic/Student business code in the Kernel — proving the contract shape before Phase 7.

### 8.5 Dependency-direction check (AC-9, AC-14, AC-40, AC-41)

A static check (import analysis / grep) asserts `kernel/authz/` imports no `business/` symbol and no Teacher/Student/Parent/Homework ORM model; and that `business/` modules import only from `kernel/authz/` (contract direction).

---

## 9. Open Questions / Deferred Decisions

| # | Item | Status |
|---|---|---|
| 1 | Dynamic DB `Policy` table for runtime ABAC rules | Deferred (Phase 2 / Phase 7) — code-driven only this iteration |
| 2 | Runtime policy reload | Deferred (app restart required) |
| 3 | Attribute value redaction allowlist (per-attribute) | Deferred — default is omit/redact values (D13) |
| 4 | Business-module provider implementations (Teacher/Student/Parent/Homework/Attendance) | Out of scope (Phase 7) |
| 5 | `authorize_many()` batch execution | Designed (D14), not implemented |
| 6 | ADR for C-04 ABAC enhancement (AGENTS.md §7) | Flagged by impact §8.5 — parent should create `docs/architecture/adr-c04-authz-abac-enhancement.md` before/alongside apply; this design is the technical decisional input for it |

---

> **End of design.** This document is the technical design input to the tasks phase. It does not modify specs or implement code.
