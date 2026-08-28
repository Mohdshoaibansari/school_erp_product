# Delta Spec — Authorization (ABAC Enforcement & Platform Owner Security Fix)

> **Change:** `fix-c04-authz-abac-enforcement`
> **Domain:** authorization
> **Delta type:** MODIFIED + ADDED
> **Base spec:** `openspec/specs/authorization/spec.md`
> **Prior delta (behavioral baseline this fix corrects):** `openspec/changes/add-c04-authz-abac-enhancement/specs/authorization/spec.md`
> **Source proposal:** `openspec/changes/fix-c04-authz-abac-enforcement/proposal.md`
> **Impact classification:** MODIFIED (correction of already-shipped `add-c04-authz-abac-enhancement` behavior) + ADDED (new regression/security tests)

The AuthZ Kernel's ABAC-enhancement implementation is retained; this change completes
real enforcement (the `match_attrs` path already exists in the matcher and now gets
proven), removes the unconditional Platform Owner ALLOW, wires production
conditional-policy registration, and improves policy identification. No other domain
is touched. The Kernel remains business-domain agnostic; no business ORM/model
references appear in any requirement.

---

## MODIFIED Requirements

### REQ-AUTHZ-FIX-ABAC-01: ABAC Enforcement Verification (matcher + raw boundary)

The authorization Casbin matcher SHALL evaluate the 5th policy field `attrs` via the
custom `match_attrs` function (`g(r.sub.role, p.sub) && ... && match_attrs(r.sub, p.attrs)`),
which SHALL return `true` for empty `attrs`, `*`, or `""` (no attribute condition) and
SHALL otherwise require every named requested attribute to be present and truthy on the
subject. The implementation SHALL provide **raw-enforcer-boundary** tests proving that,
inside Casbin itself, `attribute=false` → DENY and `attribute=missing` → DENY when the
matched policy declares that required attribute. The vacuous `test_failed_abac` stub
(no `authorize()` call, no assertion) SHALL be replaced with a real assertion.

**Supersedes** REQ-AUTHZ-ABAC-M02 ("Casbin Model — Extend for Domain Attributes") and
the ABAC-DENY test coverage in REQ-AUTHZ-ABAC-07 from `add-c04-authz-abac-enhancement`:
the matcher behavior itself is unchanged and now moves from "declared" to "verified at
the raw enforcer boundary", and the stub DENY test becomes a real one.

Per proposal §2 (P0), §5 acceptance criteria (matcher evaluates `p.attrs`; attr=false →
DENY; attr=missing → DENY), §6 required test 1–4.

#### Scenario: Empty/no attribute condition is satisfied
- **WHEN** a policy has an empty `attrs` field and all other matcher clauses hold
- **THEN** `match_attrs` SHALL return `true` and the decision SHALL proceed to normal RBAC+scope evaluation

#### Scenario: Required attribute false denies at the raw boundary
- **WHEN** a policy declares a required attribute (e.g., `attrs = is_subject_teacher`) and `enforcer.enforce()` is invoked with that attribute absent or `false` on the subject
- **THEN** Casbin SHALL return DENY directly (no Python pre-check involved)

#### Scenario: Required attribute missing denies at the raw boundary
- **WHEN** a policy declares a required attribute and `enforcer.enforce()` is invoked with the attribute omitted from the subject
- **THEN** Casbin SHALL return DENY directly

#### Scenario: Failed ABAC stub is replaced by a real assertion
- **WHEN** the former `test_failed_abac` runs
- **THEN** it SHALL invoke the pipeline with `is_subject_teacher=false` and SHALL assert the decision is DENY with a non-`ALLOWED` reason (it SHALL NO LONGER pass vacuously)

---

### REQ-AUTHZ-FIX-PO-01: Platform Owner Evaluated Through the Normal Pipeline

The unconditional Platform Owner ALLOW SHALL be removed in BOTH locations:
`authorization_service.py` Step 1 (returns ALLOW before Casbin) and the legacy
fallback in `dependencies.py` (returns when the service singleton is `None`). A
Platform Owner SHALL flow through the normal pipeline: Permission → Scope → ABAC →
Casbin. PO access to platform/client data SHALL be granted only by explicit configured
permissions (`client.*`, `config.*`). A Platform Owner SHALL NOT automatically access
institute operational resources (student, teacher, attendance, homework, etc.) merely
by virtue of holding the role. No hardcoded business-resource list and no invented
permissions SHALL be introduced into the Kernel.

**Supersedes** the PO-bypass retention in REQ-AUTHZ-ABAC-M01 ("`require_permission`
Dependency — Extend to Pipeline") and the archived "Platform Owner Bypass — Retained"
requirement: the bypass behavior is removed rather than retained.

Per proposal §4 (PO Product Requirement), §5 (PO no longer unconditional; evaluated via
normal mechanism; cannot auto-access institute operational resources; existing
client/platform access continues per configured permissions).

#### Scenario: Platform Owner no longer bypasses unconditionally
- **WHEN** a Platform Owner requests any resource/action and has no configured permission for it
- **THEN** the decision SHALL be DENY (no `if is_platform_owner: return ALLOW`)

#### Scenario: Platform Owner granted access via configured permission
- **WHEN** a Platform Owner holds a configured permission such as `client.read` or `config.*` for the requested platform/client resource
- **THEN** the decision SHALL be ALLOW through the normal Permission → Scope → ABAC → Casbin pipeline

#### Scenario: Platform Owner denied institute operational resources
- **WHEN** a Platform Owner requests an institute operational resource (e.g., student, teacher, attendance, homework) without a corresponding configured permission
- **THEN** the decision SHALL be DENY

---

### REQ-AUTHZ-FIX-REG-01: Production Conditional-Policy Registration

The production manifest hook `register_authorization_policies` (currently `pass`)
SHALL be wired so that conditional policies declared via
`policy_loader.register_conditional_policy(...)` (role, resource, action, scope,
required-attribute list) are registered at application startup alongside the
DB-loaded non-conditional policies. The exact registration mechanism (which
production module declares which conditional policies, and how they reach the hook)
SHALL be finalized in the design phase. Non-conditional DB policies SHALL continue to
register unchanged.

**Supersedes** the registration aspect of REQ-AUTHZ-ABAC-M04 ("Policy Loader — Extend
for Conditional Policies") from `add-c04-authz-abac-enhancement`: conditional policies
move from test-only to a production startup registration path.

Per proposal §2 (P0, "ABAC must never bypass RBAC" enforcement in production), §5.

#### Scenario: Conditional policies register at startup
- **WHEN** the application starts and `register_authorization_policies` runs
- **THEN** every conditional policy declared via `register_conditional_policy` SHALL be present in the enforcer alongside the DB-loaded non-conditional policies

#### Scenario: Non-conditional DB policies unchanged
- **WHEN** the production manifest hook runs
- **THEN** `register_casbin_policies` / DB-loaded non-conditional policies SHALL be registered exactly as before

---

### REQ-AUTHZ-FIX-PID-01: Policy Identification Includes `attrs` (P1)

`_extract_policy_id` SHALL include the `attrs` field (5th policy element) when deriving
the reported policy id, so that multiple conditional policies sharing an identical
`role:resource:action:scope` signature but differing in required attributes produce
distinct policy ids. Identification SHALL remain best-effort and audit-only; it SHALL
never grant or deny.

**Supersedes** the prior `_extract_policy_id` behavior (deriving
`sub:obj:act:scope` from `p[0]:p[1]:p[2]:p[3]` without `attrs`) introduced by
`add-c04-authz-abac-enhancement`.

Per proposal §2 (P1), §8 Deliverable E (policy identification fixed).

#### Scenario: Conditional policies with identical signature yield distinct ids
- **WHEN** two conditional policies for the same role/resource/action/scope differ only by required attributes
- **THEN** `_extract_policy_id` SHALL return distinct ids that include each policy's `attrs` field

#### Scenario: Identification never affects the decision
- **WHEN** `_extract_policy_id` runs for audit
- **THEN** its result SHALL NOT influence the ALLOW/DENY outcome

---

## ADDED Requirements

### REQ-AUTHZ-FIX-TEST-01: ABAC Enforcement Regression Tests

The Kernel SHALL ship ABAC enforcement regression tests covering the raw enforcement
boundary and the pipeline, demonstrating the five required cases:
1. attribute=true with a required-attr policy → ALLOW;
2. attribute=false with a required-attr policy → DENY;
3. attribute=missing with a required-attr policy → DENY (fail-closed);
4. no attribute requirement → normal RBAC/scope evaluation (ALLOW when permitted);
5. ABAC must not bypass RBAC → attribute=true with permission absent → DENY.

Tests SHALL use a test-only provider and in-memory policies; no business module SHALL
be imported into the Kernel or its tests.

Per proposal §6 "ABAC regression (raw enforcement boundary + pipeline)" tests 1–5, §5.

#### Scenario: Attribute=true allows
- **WHEN** a permitted request carries a required attribute resolved `true`
- **THEN** the decision SHALL be ALLOW

#### Scenario: Attribute=false denies
- **WHEN** a permitted request carries a required attribute resolved `false`
- **THEN** the decision SHALL be DENY

#### Scenario: Attribute=missing fails closed
- **WHEN** a permitted request's required attribute cannot be resolved
- **THEN** the decision SHALL be DENY

#### Scenario: No attribute requirement follows RBAC/scope
- **WHEN** a request has no attribute condition and the RBAC/scope checks pass
- **THEN** the decision SHALL be ALLOW

#### Scenario: ABAC never bypasses RBAC
- **WHEN** an attribute resolves `true` but the requesting role lacks the permission
- **THEN** the decision SHALL be DENY

---

### REQ-AUTHZ-FIX-TEST-02: Platform Owner Security Tests

The Kernel SHALL ship Platform Owner security regression tests proving:
- PO + `client.read` (or a configured platform/client permission) on a platform/client
  resource → ALLOW, granted through the normal pipeline;
- PO on an institute operational resource (student / teacher / attendance / homework)
  → DENY absent a configured permission.

Reference `client.*` and `config.*` permissions only as they exist; the tests SHALL NOT
invent new permissions.

Per proposal §6 "Platform Owner security" tests.

#### Scenario: PO allowed on client resource via configured permission
- **WHEN** a Platform Owner requests a platform/client resource with `client.read`
- **THEN** the decision SHALL be ALLOW through the normal pipeline

#### Scenario: PO denied institute operational resources
- **WHEN** a Platform Owner requests a student/teacher/attendance/homework resource without a configured permission
- **THEN** the decision SHALL be DENY

---

### REQ-AUTHZ-FIX-TEST-03: Provider-Failure Fail-Closed Test

The Kernel SHALL ship a test proving that when an attribute provider raises an
exception during resolution, the authorization decision SHALL be DENY (fail-closed) and
SHALL NOT be treated as a grant.

Per proposal §2 (P0 fail-closed), §6 "Provider failure", §5 (provider failures fail closed).

#### Scenario: Provider exception denies
- **WHEN** a required attribute's provider raises an exception
- **THEN** the decision SHALL be DENY with a fail-closed reason, never ALLOW

---

## Boundary Relationships

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| Attribute-provider contract | Business Module → AuthZ Kernel | Teacher/Student/Parent | Kernel defines interface; modules implement (unchanged) |
| Pipeline step 1 (authenticate) | C-04 → C-03 | authentication | Precondition, unchanged |
| Pipeline step 12 (RLS) | C-04 → auth-infrastructure | RLS session variables | Postcondition, unchanged; RLS policies NOT modified by this fix |
| Platform Owner routing | C-04 → platform-owner-separation | platform owner routes | PO routes now rely on configured permissions, not a bypass |
| Scope model preserved | C-04 → C-05 | academic-structure | `any`/`tenant`/`institution` semantics unchanged |
| Dependency direction invariant | Business Module → Kernel | all business modules | `Business Module → AuthZ Kernel Contract`, never reverse |
