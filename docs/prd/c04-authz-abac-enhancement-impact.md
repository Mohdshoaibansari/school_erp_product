# Impact Classification — C-04 AuthZ Kernel ABAC Enhancement

> **Phase:** sdd-stack-impact-classification
> **Change:** C-04 AuthZ Kernel ABAC Enhancement
> **Change ID:** `add-c04-authz-abac-enhancement`
> **Decisional source of truth:** `openspec/changes/add-c04-authz-abac-enhancement/proposal.md`
> **PRD:** `docs/prd/c04-authz-abac-enhancement.md`
> **Baseline classified against:** `openspec/specs/` (archived main specs for all built capabilities)
> **Date:** 2026-08-28
> **Method:** Shallow targeted scan of every spec under `openspec/specs/` against the ABAC enhancement PRD (48 acceptance criteria) + existing backend code in `backend/kernel/authz/`.

---

## 1. Summary — Affected OpenSpec Domains

The ABAC enhancement produces delta specs under `openspec/changes/add-c04-authz-abac-enhancement/specs/<domain>/spec.md`. The following `<domain>` folders will carry deltas:

| # | OpenSpec domain | Severity | Impact classes | One-line reason |
|---|---|---|---|---|
| 1 | `authorization` | **High** | Added + Modified | Core of the enhancement: new types (AuthorizationRequest/Decision/SubjectContext/ResourceContext/AuthorizationAttributes), new contract (AuthorizationAttributeProvider), Casbin model extension for domain attributes, multi-role evaluation fix, structured reason codes, observability. |
| 2 | `auth-infrastructure` | **Low** | Modified (minimal) | RLS session variables unchanged; authorization pipeline standardization (§22) documents the step ordering but does not change RLS plumbing. No behavioral delta required. |
| 3 | `authentication` | **Low** | None | Authentication flow (login/activate/OTP) is unchanged. Pipeline step 1 (authenticate) is a precondition, not a modification. No delta required. |
| 4 | `frontend-shell` | **Low** | None | REQ-SHELL-07 (backend-authoritative authorization with friendly 403) is already the contract. Structured reason codes are internal (AC-20); the frontend continues to render a generic friendly 403. No delta required. |

**Domains confirmed NOT affected** (scanned, no delta needed):
- `academic-structure` — provides domain data (teacher assignments, enrollments) that future attribute providers will consume, but the ABAC enhancement does not modify academic-structure requirements.
- `identity-user-management` — user/role/account model unchanged. The ABAC enhancement consumes roles from `TenantContext` (existing) and does not modify user management.
- `client-user-bootstrap` — bootstrap flow unchanged.
- `tenant-institution` — tenant/institution model unchanged. Scope evaluation is preserved (AC-36).
- `configuration` / `configuration-framework` — no new config keys introduced by this enhancement.
- `fees` / `homework` — business modules that will consume the ABAC contract in Phase 7; no changes in this enhancement.
- `platform-owner-separation` / `platform-owner-followups` — Platform Owner bypass is retained unchanged (AC-12, existing code).
- `person` (if exists) — person model unaffected.

---

## 2. Per-Domain Classification

### 2.1 `authorization` — High · Added + Modified

**Source spec:** `openspec/specs/authorization/spec.md` (contains base C-04 spec + C-05 academic-structure permission additions + person-model revamp note)

**Existing code analyzed:**
- `backend/kernel/authz/dependencies.py` — `require_permission()` and `check_permission()` with `obj_client_id`, `obj_institution_id`, `owner_id` parameters
- `backend/kernel/authz/casbin_model.conf` — RBAC + ABAC model with subject/object `client_id`/`institution_id` attributes
- `backend/kernel/authz/services/policy_loader.py` — loads `role_permission` from DB, pushes to Casbin enforcer
- `backend/kernel/authz/models/permission.py` — `Permission` and `RolePermission` ORM models
- `backend/kernel/authz/manifest.py` — module manifest with startup/policy registration hooks

**Key findings from code analysis:**
1. **Multi-role evaluation uses only `roles[0]`** — `_check_impl()` at line ~68 builds `sub = {"role": roles[0], ...}`. Only the first role is evaluated. PRD AC-15 requires all effective roles to be evaluated.
2. **No `AuthorizationRequest`/`AuthorizationDecision` types exist** — authorization is done inline via `require_permission()` which raises HTTP 403 directly. No structured decision object.
3. **No `AuthorizationAttributeProvider` contract** — the current ABAC is limited to `client_id`/`institution_id` scope checks and `owner_id` self-access. No mechanism for business modules to contribute domain attributes.
4. **No structured reason codes** — denial always returns `HTTPException(403, detail="Permission denied")` with no distinction between missing permission, invalid scope, tenant mismatch, etc.
5. **Casbin model has ABAC-ready matchers** but only for `client_id`/`institution_id` scope. No domain attribute support.
6. **Self-access bypass is hardcoded** — `owner_id` check in `_check_impl()` is a special case, not a generic attribute mechanism.

#### ADDED
- **Authorization request/decision contract** — `AuthorizationRequest`, `AuthorizationDecision`, `SubjectContext`, `ResourceContext`, `AuthorizationAttributes` types (AC-1 through AC-5, PRD §8, proposal §8/§21/§31 Phase 1).
- **Attribute provider contract** — `AuthorizationAttributeProvider` interface with registration and resolution semantics (AC-6 through AC-10, PRD §9/§10, proposal §9/§10/§31 Phase 2). Providers receive subject/resource/context and return domain attributes. Kernel does NOT import business ORM models.
- **Structured reason codes** — enum with `MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED` (AC-18 through AC-20, PRD §21, proposal §21/§31 Phase 5).
- **Authorization pipeline standardization** — 12-step pipeline from authentication through RLS (AC-22, PRD §22, proposal §22).
- **Observability and audit context** — decision traceability with correlation_id, user_id, client_id, institution_id, action, resource_type, resource_id, roles, scope, policy_id, decision, reason (AC-32 through AC-33, PRD §28, proposal §28).
- **Security invariants** — fail-closed (AC-21), no client-supplied trust (AC-22), no cross-client attribute resolution (AC-23), institution boundary (AC-24), RLS defense-in-depth (AC-25).
- **Performance requirements** — lightweight checks, request-specific resolution, per-request caching, batch checks, no network calls, no Kafka (AC-26 through AC-31, PRD §27, proposal §27).
- **Multiple assignment support** — providers evaluate requested resource against relationship set, not singular attributes (AC-34 through AC-35, PRD §11, proposal §11).
- **Policy model for conditional rules** — policies support "when" conditions on domain attributes (AC-38 through AC-39, PRD §16, proposal §16).
- **Synthetic-attribute testing** — test-only providers validate the engine without business module implementation (AC-46 through AC-48, PRD §35, proposal §35 Phase 6).
- **Testing requirements** — unit tests (AC-43), security tests (AC-44), regression tests (AC-45).

#### MODIFIED
- **`require_permission` dependency** — currently raises HTTP 403 directly. Will be extended to build an `AuthorizationRequest`, invoke the new authorization pipeline (resolve attributes → evaluate all roles → Casbin), and return an `AuthorizationDecision`. The existing `obj_client_id`/`obj_institution_id`/`owner_id` parameters are preserved for backward compatibility but the internal implementation changes. **Supersedes** the existing `require_permission` requirement. (AC-1 through AC-5, AC-11, AC-15, AC-18.)
- **Casbin model** — currently matches on `sub.role` (singular), `obj.name`, `act`, and scope (`client_id`/`institution_id`). Will be extended to also match on domain attributes. The existing RBAC + scope behavior must remain unchanged (AC-12, AC-45). **Supersedes** the existing Casbin model matchers. (AC-11, AC-13, AC-14.)
- **Multi-role evaluation** — currently `_check_impl()` uses `roles[0]` only. Will evaluate all effective roles; a valid permission from any role satisfies RBAC subject to scope and ABAC conditions. **Supersedes** the existing single-role evaluation behavior. (AC-15 through AC-17.)
- **Policy loader** — currently loads `(role, resource, action, scope)` tuples. May need extension to support attribute-conditional policies (design-phase decision on how policies declare required attributes). (AC-38, AC-39.)
- **Ownership enforcement** — the current hardcoded `owner_id` self-access bypass in `_check_impl()` is a special case of ABAC (`is_self` attribute). The new attribute provider mechanism generalizes this. The `owner_id` parameter may be preserved for backward compatibility or replaced by a provider. **Design-phase decision.** (AC-5, proposal §8.5.)

#### REMOVED
- **Single-role evaluation behavior** — the `roles[0]` pattern is replaced by all-roles evaluation. Not a requirement removal per se, but the behavioral contract changes.

---

### 2.2 `auth-infrastructure` — Low · Modified (minimal)

**Source spec:** `openspec/specs/auth-infrastructure/spec.md`

#### MODIFIED (minimal)
- **RLS session variables** — the ABAC enhancement does not add new RLS session variables. The existing `app.current_user_id`, `app.current_client_id`, `app.is_platform_owner` are unchanged. The authorization pipeline standardization (PRD §22, step 12) documents that persistence happens under RLS, but this is already the behavior.
- **No behavioral change** — the auth-infrastructure spec covers Supabase client, RLS session variables, and conftest RLS bypass. None of these are modified by the ABAC enhancement.
- **Likely no delta spec required.** The pipeline documentation is in the authorization domain, not auth-infrastructure.

---

### 2.3 `authentication` — Low · No delta

**Source spec:** `openspec/specs/authentication/spec.md`

- The authentication flow (login, activate, OTP, password reset/change, logout, silent token refresh) is unchanged.
- Pipeline step 1 (authenticate request) is a precondition owned by C-03, not modified by this enhancement.
- The `TenantContext` resolution (middleware) is unchanged.
- **No delta spec required.**

---

### 2.4 `frontend-shell` — Low · No delta

**Source spec:** `openspec/specs/frontend-shell/spec.md`

- REQ-SHELL-07 (backend-authoritative authorization with friendly 403) already states: "the backend (Casbin RBAC+ABAC) remains authoritative on every request" and "the app SHALL render a friendly permission-denied message, never a raw error."
- The structured reason codes (AC-18 through AC-20) are for internal logs and controlled API responses (AC-20: "sensitive policy internals are not unnecessarily exposed to clients"). The frontend continues to render a generic friendly 403.
- Role-filtered navigation (REQ-SHELL-03, REQ-SHELL-10) is derived from JWT roles, not from ABAC attributes. Unchanged.
- **No delta spec required.** If the design phase decides to surface specific reason codes in the 403 response body for better UX, a frontend delta would be needed — but the PRD explicitly scopes reason codes as internal.

---

## 3. Cross-Cutting Concerns (span multiple domains)

| Cross-cutting concern | Domains touched | PRD ref | Notes |
|---|---|---|---|
| **Authorization pipeline standardization** | authorization (primary), authentication (step 1), auth-infrastructure (step 12 RLS) | §22, AC-22 | The 12-step pipeline is documented in the authorization delta. Steps 1 and 12 are owned by other domains but are not modified — they are referenced as preconditions/postconditions. |
| **Backward compatibility** | authorization | AC-12, AC-45 | Existing RBAC + scope behavior must remain unchanged. The `require_permission` signature is preserved (or extended with optional parameters). Existing callers must not break. |
| **Dependency direction invariant** | authorization | AC-40, AC-41, PRD §23 | `Business Module → AuthZ Kernel Contract`, never reverse. The Kernel defines interfaces; business modules implement them. This is an architectural constraint, not a code change. |
| **Subscription interaction** | authorization | AC-42, PRD §25 | Five concerns remain distinct: Subscription, Permission, Scope, ABAC, RLS. Documented in the authorization delta. |

---

## 4. Existing Code Impact Map

The following backend files are directly affected by the ABAC enhancement:

| File | Current behavior | Impact |
|---|---|---|
| `backend/kernel/authz/dependencies.py` | `require_permission()` builds Casbin subject from `roles[0]`, raises HTTP 403 on denial | **High** — must be extended to: (a) evaluate all roles, (b) resolve domain attributes via providers, (c) return structured `AuthorizationDecision`, (d) use reason codes |
| `backend/kernel/authz/casbin_model.conf` | Matchers: `g(r.sub.role, p.sub)` + scope checks on `client_id`/`institution_id` | **High** — must be extended to match on domain attributes in addition to existing RBAC + scope |
| `backend/kernel/authz/services/policy_loader.py` | Loads `(role, resource, action, scope)` from `role_permission` | **Medium** — may need extension for attribute-conditional policies (design decision) |
| `backend/kernel/authz/models/permission.py` | `Permission` and `RolePermission` ORM models | **Low** — no schema change expected; attribute providers are code-driven, not DB-driven |
| `backend/kernel/authz/manifest.py` | Startup hooks for policy loading | **Low** — may need to register attribute providers at startup (design decision) |

**New files expected** (not yet created — design phase determines exact structure):
- `backend/kernel/authz/services/authorization_service.py` — the new authorization pipeline
- `backend/kernel/authz/models/authorization_types.py` — `AuthorizationRequest`, `AuthorizationDecision`, `SubjectContext`, `ResourceContext`, `AuthorizationAttributes`
- `backend/kernel/authz/services/attribute_provider.py` — `AuthorizationAttributeProvider` ABC + registry
- `backend/kernel/authz/models/reason_codes.py` — `AuthorizationReasonCode` enum

---

## 5. Open Questions (from PRD §8)

These are product-level questions that affect the spec delta's final shape:

| # | Question | Impact on spec delta | Recommendation |
|---|----------|---------------------|----------------|
| Q1 | Should `AuthorizationAttributeProvider` be async? | Affects interface signature | Yes — providers will query business tables |
| Q2 | How are required attributes determined for a request? | Affects pipeline step 7 | Providers declare what they supply; Kernel invokes all registered providers for the resource type |
| Q3 | Should the Kernel support multiple providers per resource type? | Affects provider registration semantics | Yes — each provider contributes a subset of attributes |
| Q4 | What is the provider lifecycle? | Affects module integration pattern | Startup registration via module manifest |
| Q5 | Should reason codes be an enum or free-form strings? | Affects the reason code type | Enum for consistency and testability |
| Q6 | How does ABAC interact with existing `require_permission`? | Affects migration path | Extend, not replace — `require_permission` becomes a thin wrapper |
| Q7 | Should the Kernel provide a "no-op" default provider? | Affects backward compatibility | Yes — missing provider → empty attributes → pure RBAC |

**Recommendation:** These questions should be resolved in the design phase. The spec delta states the requirements with the recommended approach noted; the design phase confirms or adjusts.

---

## 6. Added / Modified / Removed — Consolidated

### ADDED (new requirements introduced by the enhancement)
1. `AuthorizationRequest` type — subject, resource, action, context, attributes (AC-1).
2. `AuthorizationDecision` type — allowed, reason, policy_id (AC-2).
3. `SubjectContext` — user_id, roles, client_id, institution_id, user_tier, platform_owner (AC-3).
4. `ResourceContext` — resource_type, resource_id, client_id, institution_id, domain fields (AC-4).
5. `AuthorizationAttributes` — domain attributes as key-value pairs (AC-5).
6. `AuthorizationAttributeProvider` interface — registration and resolution semantics (AC-6 through AC-10).
7. Structured reason codes enum (AC-18 through AC-20).
8. Authorization pipeline standardization — 12-step pipeline (AC-22, §22).
9. Observability and audit context (AC-32 through AC-33).
10. Security invariants — fail-closed, no client-supplied trust, no cross-client, institution boundary, RLS defense-in-depth (AC-21 through AC-25).
11. Performance requirements — lightweight, request-specific, cached, batch, no network, no Kafka (AC-26 through AC-31).
12. Multiple assignment support (AC-34 through AC-35).
13. Policy model for conditional rules (AC-38 through AC-39).
14. Synthetic-attribute testing (AC-46 through AC-48).
15. Testing requirements — unit, security, regression (AC-43 through AC-45).

### MODIFIED (existing requirements that change)
1. `require_permission` dependency — extends to use new authorization pipeline with attribute resolution and structured decisions (AC-1 through AC-5, AC-11, AC-15, AC-18).
2. Casbin model — extends to match on domain attributes alongside existing RBAC + scope (AC-11 through AC-14).
3. Multi-role evaluation — changes from `roles[0]` to all-roles evaluation (AC-15 through AC-17).
4. Policy loader — may extend for attribute-conditional policies (AC-38, AC-39; design decision).
5. Ownership enforcement — `owner_id` self-access bypass generalizes to attribute provider mechanism (AC-5; design decision).

### REMOVED (requirements dropped)
1. Single-role evaluation behavior — replaced by all-roles evaluation (AC-15).

### CROSS-CUTTING (spans multiple domains)
1. Authorization pipeline standardization — authorization (primary) + authentication (step 1 reference) + auth-infrastructure (step 12 RLS reference).
2. Backward compatibility invariant — all existing callers of `require_permission` must continue to work.
3. Dependency direction invariant — `Business Module → AuthZ Kernel Contract`, never reverse.

---

## 7. Affected OpenSpec Domains — Final List (for delta spec folders)

Delta specs will be produced under `openspec/changes/add-c04-authz-abac-enhancement/specs/<domain>/spec.md` for:

| Domain | Impact severity | Confidence | Delta required? |
|---|---|---|---|
| `authorization` | **High** | High | **Yes** — primary delta spec |
| `auth-infrastructure` | Low | High | **No** — no behavioral change |
| `authentication` | Low | High | **No** — no behavioral change |
| `frontend-shell` | Low | High | **No** — no behavioral change |

**Definitely affected (delta required):** `authorization`.
**Not affected (no delta):** all other domains scanned.

---

## 8. Residual Gaps & Narrowest Useful Next Rerun

### Residual gaps (flagged for the design phase)
1. **PRD Q1–Q7 unresolved** — seven open product questions (see §5). The spec delta states requirements with recommended approaches; the design phase confirms or adjusts. Q2 (how required attributes are determined) and Q6 (how ABAC interacts with `require_permission`) are the most consequential.
2. **Casbin model extension strategy** — the current model uses `r.sub.role` (singular). Multi-role evaluation (AC-15) requires evaluating all roles. Two approaches: (a) loop `enforcer.enforce()` per role in Python, or (b) extend the Casbin model to accept `roles[]`. Design decision.
3. **Attribute-conditional policy format** — how does a Casbin policy express "Teacher may create homework when `is_subject_teacher == true`"? Options: (a) extend the Casbin model with attribute matchers, (b) use Casbin's built-in ABAC (`r.sub.*` / `r.obj.*` matchers), (c) pre-filter in Python before Casbin. Design decision.
4. **`owner_id` backward compatibility** — the current self-access bypass is a special case. The design phase decides whether to preserve `owner_id` as a convenience parameter or replace it entirely with an `is_self` attribute provider.
5. **No ADR for C-04 ABAC enhancement** — the PRD and proposal are the decisional sources. If an ADR is needed per AGENTS.md §7, it should be created before the design phase.

### Narrowest useful next rerun
- A **code-level scan** of `backend/kernel/authz/` to produce a file-level implementation impact map for the design/tasks phases. This is **optional** and belongs to the design or current-state-exploration phase.

---

> **End of impact classification.** This document is the input to the proposal/spec/design phases. The primary delta spec is `authorization`. Open questions Q1–Q7 should be resolved in the design phase; the spec delta states requirements with recommended approaches.
