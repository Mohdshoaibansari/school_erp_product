# Delta Spec — Authorization (ABAC Enhancement)

> **Change:** `add-c04-authz-abac-enhancement`
> **Domain:** authorization
> **Delta type:** ADDED + MODIFIED + REMOVED
> **Base spec:** `openspec/specs/authorization/spec.md`
> **Source PRD:** `docs/prd/c04-authz-abac-enhancement.md`
> **Source proposal:** `openspec/changes/add-c04-authz-abac-enhancement/proposal.md`

---

## ADDED Requirements

### REQ-AUTHZ-ABAC-01: Authorization Request/Decision Contract

The AuthZ Kernel SHALL define a Kernel-owned `AuthorizationRequest` contract composed of a `SubjectContext`, a `ResourceContext`, an action, and `AuthorizationAttributes`. `SubjectContext` SHALL carry generic identity/security facts (`user_id`, `roles`, `client_id`, `institution_id`, `user_tier`, `platform_owner` status). `ResourceContext` SHALL carry resource-specific facts supplied by the business operation (`resource_type`, `resource_id`, `client_id`, `institution_id`, plus domain-specific fields). `AuthorizationAttributes` SHALL carry domain attributes as key-value pairs (e.g., `is_class_teacher`, `is_subject_teacher`, `is_self`, `is_parent_of_resource`, `is_owner`, `is_assigned_to_resource`). The Kernel SHALL also define an `AuthorizationDecision` result carrying `allowed` (bool), `reason` (structured code), and `policy_id`.

Per PRD §8 (Phase 1), AC-1 through AC-5.

#### Scenario: Request composes subject, resource, action, attributes
- **WHEN** a business module submits an authorization request
- **THEN** the request SHALL carry a `SubjectContext`, a `ResourceContext`, an action, and `AuthorizationAttributes`

#### Scenario: Decision carries allowed, reason, policy_id
- **WHEN** an authorization request is evaluated
- **THEN** the returned `AuthorizationDecision` SHALL carry `allowed`, `reason`, and `policy_id`

---

### REQ-AUTHZ-ABAC-02: AuthorizationAttributeProvider Contract

The AuthZ Kernel SHALL own an `AuthorizationAttributeProvider` interface (in `kernel/authz/`) that business modules implement. Providers SHALL expose an async `resolve()` and SHALL return only the attributes required for evaluation — facts, NOT authorization decisions; Casbin remains the sole decision-maker. The Kernel SHALL determine required attributes from the policies being evaluated (lazy/request-driven resolution), and a `ProviderRegistry` SHALL map required attributes to one or more providers (multiple providers MAY contribute to a single request; execution SHALL be deterministic). Providers SHALL register at application startup, SHALL be stateless with injected dependencies, and SHALL NOT store request-scoped state. Resolved attributes SHALL be cached for the lifetime of one authorization request. When no attributes are required, the Kernel SHALL fall back to pure RBAC+scope evaluation without invoking any provider.

Per PRD §8 (Q1–Q4, Q11), AC-6 through AC-10, AC-26 through AC-28, AC-34 through AC-35.

#### Scenario: Provider returns facts, not decisions
- **WHEN** a provider resolves domain facts for a request
- **THEN** it SHALL return attribute values only, NOT an allow/deny decision

#### Scenario: Providers are async and request-driven
- **WHEN** a required attribute is determined by the policies being evaluated
- **THEN** the Kernel SHALL invoke the matching provider's async `resolve()` for only that attribute

#### Scenario: Pure-RBAC fallback when no attributes required
- **WHEN** a request's policies declare no required attributes
- **THEN** the Kernel SHALL evaluate RBAC+scope directly without invoking providers

---

### REQ-AUTHZ-ABAC-03: Structured Reason Codes

The Kernel SHALL define a stable `AuthorizationReasonCode` enum with at least: `MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED`. Reason codes SHALL be machine-readable and SHALL be safe for internal logs and controlled API responses; sensitive policy/attribute internals SHALL NOT be exposed to clients.

Per PRD §8 (Q5), AC-18 through AC-20.

#### Scenario: Reason code enum is complete
- **WHEN** the reason-code enum is inspected
- **THEN** it SHALL contain the nine codes listed above

#### Scenario: Denial carries a structured reason
- **WHEN** an authorization request is denied
- **THEN** the decision SHALL carry a machine-readable reason code rather than a free-form message

---

### REQ-AUTHZ-ABAC-04: Authorization Pipeline + Restrictive Ordering

The Kernel SHALL standardize an authorization pipeline ordered: authentication → tenant validation → permission/RBAC → scope → ABAC. ABAC SHALL be restrictive: it SHALL only further restrict a permission already granted by RBAC and SHALL NEVER grant a permission denied by RBAC. Missing or failed required attributes SHALL result in DENY. The pipeline SHALL be designed to support `authorize_many()` (batch), but batch authorization SHALL NOT be implemented in this enhancement; any future batch path SHALL avoid N+1 provider/database queries.

Per PRD §8 (Q6), §22, §8 "Batch Authorization", AC-29.

#### Scenario: Restrictive ordering is enforced
- **WHEN** a user lacks the required permission (RBAC denies)
- **THEN** ABAC SHALL NOT be able to grant access
- **AND** the decision SHALL be DENY with `MISSING_PERMISSION`

#### Scenario: ABAC further restricts an RBAC grant
- **WHEN** a user has the permission but a required attribute condition fails
- **THEN** the decision SHALL be DENY with the corresponding attribute reason code

---

### REQ-AUTHZ-ABAC-05: Security Invariants

The Kernel SHALL enforce: (1) **fail-closed** — if a required attribute cannot be resolved, the decision SHALL be DENY; (2) **no client-supplied trust** — domain attributes SHALL be derived only from trusted server-side sources, never from client input; (3) **no cross-client attribute resolution** — providers SHALL NOT resolve relationships outside the authenticated client boundary; (4) **institution boundary** — where institution scope is required, the resource SHALL belong to an institution the subject can access; (5) **RLS defense-in-depth** — authorization success SHALL NOT disable or bypass PostgreSQL RLS.

Per PRD §8 (Q7, Q9, Q10), AC-21 through AC-25.

#### Scenario: Missing attribute fails closed
- **WHEN** a required attribute cannot be resolved for a request
- **THEN** the decision SHALL be DENY (never treated as permission)

#### Scenario: Client-supplied attributes are not trusted
- **WHEN** a client submits a domain attribute (e.g., `is_class_teacher: true`)
- **THEN** the Kernel SHALL ignore it and resolve the attribute from server-side providers

---

### REQ-AUTHZ-ABAC-06: Observability and Audit Context

Every authorization decision SHALL be traceable with structured context: `correlation_id`, `user_id`, `client_id`, `institution_id`, `action`, `resource_type`, `resource_id`, `roles`, `scope`, `policy_id`, `decision`, and `reason`. Domain attribute values SHALL be logged carefully to avoid unnecessary sensitive-data exposure.

Per PRD §28, AC-32 through AC-33.

#### Scenario: Decision is fully traceable
- **WHEN** an authorization decision is produced
- **THEN** it SHALL carry the structured context fields listed above

#### Scenario: Sensitive attribute values are handled carefully
- **WHEN** domain attribute values are logged
- **THEN** sensitive values SHALL be omitted or redacted to avoid unnecessary exposure

---

### REQ-AUTHZ-ABAC-07: Testing and Synthetic-Attribute Validation

The Kernel SHALL be validated with unit tests (single role, multiple roles, missing permission, tenant scope, institution scope, successful ABAC, failed ABAC, missing required attribute, multiple/conflicting assignments), security tests (cross-client DENY, cross-institution DENY, self-access ALLOW/DENY), and regression tests confirming existing RBAC+scope behavior is unchanged. A test-only provider implementation SHALL demonstrate ALLOW and DENY (e.g., `is_subject_teacher=true/false`) with no Teacher, Homework, Academic, Student, or other business implementation embedded in the Kernel.

Per PRD §29, §35, AC-43 through AC-48.

#### Scenario: Synthetic ALLOW is demonstrated
- **WHEN** a test-only provider supplies `is_subject_teacher=true` for a permitted teacher
- **THEN** Casbin SHALL return ALLOW without any business module in the Kernel

#### Scenario: Synthetic DENY is demonstrated
- **WHEN** a test-only provider supplies `is_subject_teacher=false`
- **THEN** Casbin SHALL return DENY without any business module in the Kernel

---

## MODIFIED Requirements

### REQ-AUTHZ-ABAC-M01: `require_permission` Dependency — Extend to Pipeline

The `require_permission` dependency SHALL build an `AuthorizationRequest` (subject from `TenantContext` roles, resource from the provided object attributes, action), resolve required domain attributes via registered providers, evaluate ALL effective roles, invoke Casbin, and return an `AuthorizationDecision` instead of raising HTTP 403 directly. On denial it SHALL raise a structured 403 carrying the reason code. Existing `obj_client_id` / `obj_institution_id` / `owner_id` parameters SHALL be preserved for backward compatibility, and the Platform Owner bypass SHALL be retained.

**Supersedes** the archived "`require_permission` FastAPI Dependency" requirement — the dependency now composes the new pipeline and returns a structured decision rather than raising HTTP 403 inline.

Per PRD §8 (Q6), AC-1 through AC-5, AC-11, AC-15, AC-18.

#### Scenario: Dependency composes the new pipeline
- **WHEN** `require_permission(resource, action, ...)` is invoked
- **THEN** it SHALL build an `AuthorizationRequest`, resolve attributes, invoke Casbin, and return an `AuthorizationDecision`

#### Scenario: Structured 403 on denial
- **WHEN** an authorization request is denied
- **THEN** the dependency SHALL raise a 403 carrying the structured reason code

#### Scenario: Platform Owner bypass retained
- **WHEN** a Platform Owner invokes `require_permission`
- **THEN** the dependency SHALL return without running the pipeline

---

### REQ-AUTHZ-ABAC-M02: Casbin Model — Extend for Domain Attributes

The Casbin model SHALL be extended to evaluate subject + resource + action + scope + domain attributes together. Existing RBAC matchers and scope checks (`client_id` / `institution_id`) SHALL remain unchanged; attribute conditions SHALL be additive. Casbin SHALL NOT directly query business repositories or import business ORM models.

**Supersedes** the archived "Casbin Enforcer Singleton" requirement's model-matcher behavior — the model now consumes domain attributes in addition to role, resource, action, and scope.

Per AC-11 through AC-14.

#### Scenario: Attributes evaluated alongside RBAC+scope
- **WHEN** Casbin evaluates a request carrying domain attributes
- **THEN** it SHALL evaluate role, permission, scope, and attribute conditions together

#### Scenario: Existing scope matchers unchanged
- **WHEN** a request is evaluated with existing RBAC+scope policies
- **THEN** `client_id` and `institution_id` scope checks SHALL behave exactly as before

---

### REQ-AUTHZ-ABAC-M03: Multi-Role Evaluation

The authorization implementation SHALL evaluate ALL effective roles rather than only `roles[0]`. A valid permission from any applicable effective role SHALL satisfy RBAC, subject to scope and ABAC conditions.

**Supersedes** the single-role (`roles[0]`) evaluation behavior.

Per AC-15 through AC-17.

#### Scenario: All roles are evaluated
- **WHEN** a user with roles `[HOD, Teacher]` requests an action
- **THEN** the Kernel SHALL evaluate both roles, not only the first

#### Scenario: Any valid role satisfies RBAC
- **WHEN** a user's first role lacks a permission but a later role has it
- **THEN** the Kernel SHALL NOT deny based solely on the first role

---

### REQ-AUTHZ-ABAC-M04: Policy Loader — Extend for Conditional Policies

The policy loader SHALL support attribute-conditional policies (policies declare the attributes they require for evaluation). Existing non-conditional `(role, resource, action, scope)` tuples SHALL remain unchanged.

**Supersedes** the archived "C-04 Policy Registration" requirement — the loader now also handles policies that declare required attributes.

Per PRD §8 (Q11), AC-38 through AC-39.

#### Scenario: Conditional policy declares required attributes
- **WHEN** a policy expresses a condition such as "Teacher may create homework when `is_subject_teacher == true`"
- **THEN** the loader SHALL record the required attribute (`is_subject_teacher`) for that policy

#### Scenario: Non-conditional policies unchanged
- **WHEN** a policy has no attribute condition
- **THEN** its `(role, resource, action, scope)` tuple SHALL be loaded exactly as before

---

### REQ-AUTHZ-ABAC-M05: Ownership Enforcement — Generalize to `is_self`

The hardcoded `owner_id` self-access bypass SHALL generalize to an `is_self` attribute resolved via the attribute provider mechanism. The `owner_id` parameter SHALL be preserved for backward compatibility.

**Supersedes** the archived "Ownership Enforcement (App-Level)" requirement — self-access becomes a first-class ABAC attribute rather than a hardcoded special case.

Per AC-5, proposal §8.5.

#### Scenario: Self-access resolved as an attribute
- **WHEN** a user accesses their own resource
- **THEN** the `is_self` attribute SHALL be resolved true via the provider mechanism and evaluated by Casbin

#### Scenario: Non-self access denied
- **WHEN** a user accesses another user's resource without admin-level scope
- **THEN** `is_self` SHALL be false and the decision SHALL be DENY

---

## REMOVED Requirements

### Single-Role Evaluation Behavior (removed)

The prior behavior of building the Casbin subject from `roles[0]` only — evaluating a single effective role — SHALL be removed and replaced by all-roles evaluation.

Per AC-15.

---

## Boundary Relationships

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| Attribute provider contract | Business Module → AuthZ Kernel | Teacher/Student/Parent (Phase 7) | Kernel defines interface; modules implement |
| Pipeline step 1 (authenticate) | C-04 → C-03 | authentication | Precondition, unchanged |
| Pipeline step 12 (RLS) | C-04 → auth-infrastructure | RLS session variables | Postcondition, unchanged |
| Platform Owner bypass retained | C-04 → platform-owner-separation | platform owner routes | No change |
| Scope model preserved | C-04 → C-05 | academic-structure | Existing scope semantics unchanged |
| Reason codes internal | C-04 → frontend-shell | friendly 403 | Frontend renders generic 403 |
| Dependency direction invariant | Business Module → Kernel | all business modules | `Business Module → AuthZ Kernel Contract`, never reverse |
