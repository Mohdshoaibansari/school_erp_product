# Delta Spec — Authorization (ABAC Enhancement)

> **Change:** `add-c04-authz-abac-enhancement`
> **Domain:** authorization
> **Delta type:** ADDED + MODIFIED + REMOVED
> **Base spec:** `openspec/specs/authorization/spec.md` (base C-04 spec from `2026-07-14-add-c04-authorization` + C-05 academic-structure permissions + person-model revamp note)
> **Source PRD:** `docs/prd/c04-authz-abac-enhancement.md`
> **Source proposal:** `openspec/changes/add-c04-authz-abac-enhancement/proposal.md`
> **Impact classification:** `docs/prd/c04-authz-abac-enhancement-impact.md` (authorization only)

---

## ADDED Requirements

### Requirement: Authorization Request/Decision Contract

The AuthZ Kernel SHALL define the authorization contract types: `AuthorizationRequest` (subject, resource, action, context, attributes), `SubjectContext` (user_id, roles, client_id, institution_id, user_tier, platform_owner), `ResourceContext` (resource_type, resource_id, client_id, institution_id, plus domain-specific fields), `AuthorizationAttributes` (key-value domain facts), and `AuthorizationDecision` (allowed, reason, policy_id). `AuthorizationRequest` SHALL be the single input to the authorization pipeline and `AuthorizationDecision` SHALL be its structured result, returned by the authorization service rather than raising HTTP exceptions directly. Subject/context values SHALL be derived from trusted server-side context, never client-supplied parameters.

Per AC-1, AC-2, AC-3, AC-4, AC-5; PRD §6.6; proposal §8/§21/§31 Phase 1/5.

#### Scenario: Request carries the full contract
- **WHEN** an authorization check is initiated
- **THEN** `AuthorizationRequest` SHALL hold `subject`, `resource`, `action`, `context`, and `attributes`
- **AND** identity/security values SHALL come from the authentication context (JWT + TenantContext), never from client-supplied parameters

#### Scenario: Decision is structured, not an exception
- **WHEN** authorization completes
- **THEN** the service SHALL return an `AuthorizationDecision` with `allowed`, `reason`, and `policy_id`
- **AND** ALLOW SHALL set `allowed=True`; DENY SHALL set `allowed=False` with a reason code

---

### Requirement: AuthorizationAttributeProvider Contract

The AuthZ Kernel SHALL define a Kernel-owned `AuthorizationAttributeProvider` interface that business modules implement. Providers SHALL receive the subject, resource, and context, and SHALL return only domain facts (`AuthorizationAttributes`) — never a final allow/deny decision (Casbin remains the decider). Resolution SHALL be lazy/request-driven: policies declare the attributes they require, and the Kernel SHALL resolve only required attributes. A `ProviderRegistry` SHALL map required attributes to providers; multiple providers MAY contribute attributes to one request and execution SHALL be deterministic. Providers SHALL be application-scoped, stateless, with dependencies injected at startup registration. Resolved attributes SHALL be cached for the lifetime of one authorization request. A request that requires no attributes SHALL evaluate with pure RBAC + scope (backward compatible). The Kernel SHALL NOT import business ORM models.

Per AC-6, AC-7, AC-8, AC-9, AC-10; PRD §8 (Q1–Q4, Q7, Decision 8, Decision 11); proposal §9/§10/§23/§31 Phase 2.

#### Scenario: Provider returns facts, not decisions
- **WHEN** a provider resolves attributes
- **THEN** it SHALL return domain facts (e.g., `is_subject_teacher=True`)
- **AND** Casbin SHALL make the final allow/deny decision

#### Scenario: Lazy, request-driven, cached resolution
- **WHEN** a request arrives
- **THEN** the Kernel SHALL resolve only the attributes the applicable policies require
- **AND** resolved values SHALL be cached and reused for the lifetime of that request

#### Scenario: Startup registration, stateless, deterministic
- **WHEN** a business module starts
- **THEN** it SHALL register its providers at startup via the module manifest, stateless with injected dependencies
- **AND** when multiple providers contribute to one request, execution SHALL be deterministic

#### Scenario: No required attributes — backward compatible
- **WHEN** a request's applicable policies require no domain attributes
- **THEN** the Kernel SHALL proceed with empty attributes and evaluate pure RBAC + scope

---

### Requirement: Structured Reason Codes

The AuthZ Kernel SHALL define an `AuthorizationReasonCode` enum with: `MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED`. Reason codes SHALL be stable machine-readable values used for internal logs and controlled API responses. Sensitive policy internals SHALL NOT be unnecessarily exposed to clients.

Per AC-18, AC-19, AC-20; PRD §8 (Q5); proposal §21/§31 Phase 5.

#### Scenario: Denial carries a stable, safe enum reason
- **WHEN** a decision is DENY
- **THEN** `reason` SHALL be one of the defined enum values, not a free-form string
- **AND** the reason SHALL be safe for internal diagnostics without exposing sensitive policy/attribute internals

---

### Requirement: Authorization Pipeline + Restrictive Ordering

The AuthZ Kernel SHALL evaluate authorization as a pipeline: authentication → tenant validation → permission/RBAC → scope → ABAC. The pipeline SHALL be restrictive — ABAC SHALL NOT grant a permission that RBAC denies, and a required attribute that is missing or fails SHALL produce DENY. The architecture SHALL be designed to support a future `authorize_many()` batch method that avoids N+1 provider/database queries; batch authorization SHALL NOT be implemented in this iteration.

Per AC-22, AC-42; PRD §8 (Q6, Decision 11, Batch Authorization); proposal §22.

#### Scenario: RBAC gate precedes scope and ABAC
- **WHEN** a user lacks the required permission for an action
- **THEN** the decision SHALL be DENY with `MISSING_PERMISSION`
- **AND** scope and ABAC SHALL NOT override that denial

#### Scenario: Batch authorization is designed-for, not implemented
- **WHEN** the authorization architecture is reviewed
- **THEN** it SHALL support a future `authorize_many()` without N+1 queries
- **AND** no batch method SHALL ship in this iteration

---

### Requirement: Security Invariants

The AuthZ Kernel SHALL enforce: fail-closed (a required attribute that cannot be resolved SHALL produce DENY, never permission); no client-supplied attribute trust (attributes SHALL come only from server-side providers); no cross-client attribute resolution (providers SHALL stay within the authenticated client boundary); institution boundary (institution-scoped requests SHALL verify the resource belongs to an accessible institution); and RLS defense-in-depth (authorization success SHALL NOT bypass PostgreSQL RLS).

Per AC-21, AC-22, AC-23, AC-24, AC-25; PRD §8 (Decision 9, Decision 10); proposal §26.

#### Scenario: Missing required attribute fails closed
- **WHEN** a required attribute cannot be resolved
- **THEN** the decision SHALL be DENY
- **AND** missing attributes SHALL NOT be interpreted as permission

#### Scenario: Client-declared attributes are ignored
- **WHEN** a client supplies domain attributes (e.g., `is_class_teacher=true`)
- **THEN** the Kernel SHALL ignore them and resolve attributes exclusively from providers

#### Scenario: Cross-client/institution isolation and RLS backstop
- **WHEN** a provider resolves relationships
- **THEN** it SHALL scope to the authenticated `client_id`
- **AND** an institution-scoped request for an inaccessible institution SHALL DENY with `INSTITUTION_ACCESS_DENIED`
- **AND** on ALLOW, PostgreSQL RLS SHALL still enforce row-level isolation

---

### Requirement: Observability and Audit Context

Authorization decisions SHALL be traceable with structured log context: `correlation_id`, `user_id`, `client_id`, `institution_id`, `action`, `resource_type`, `resource_id`, `roles`, `scope`, `policy_id`, `decision`, and `reason`. Domain attribute values SHALL be logged carefully to avoid unnecessary sensitive-data exposure.

Per AC-32, AC-33; PRD §28; proposal §28.

#### Scenario: ALLOW and DENY are both traceable
- **WHEN** a decision is made
- **THEN** the log entry SHALL include the full context listed above, with `decision` and `reason`
- **AND** sensitive relationship/identity detail SHALL NOT be logged unnecessarily

---

### Requirement: Testing and Synthetic-Attribute Validation

The authorization test suite SHALL cover unit, security, and regression scenarios: single role, multiple roles, missing permission, tenant scope, institution scope, successful ABAC, failed ABAC, missing required attribute, multiple assignments, cross-tenant/cross-institution denial, and unchanged RBAC+scope behavior. A test-only provider SHALL demonstrate ALLOW (`is_subject_teacher=True`) and DENY (`is_subject_teacher=False`) for a teacher homework scenario without any Teacher, Homework, Academic, or Student business implementation inside the Kernel.

Per AC-43, AC-44, AC-45, AC-46, AC-47, AC-48; PRD §29/§35; proposal §29/§35 Phase 6.

#### Scenario: Unit, security, and regression coverage
- **WHEN** the suite runs
- **THEN** it SHALL cover the scenarios above
- **AND** existing RBAC and scope tests SHALL pass unchanged

#### Scenario: Synthetic ALLOW / DENY without business modules
- **WHEN** a test-only provider returns `is_subject_teacher=True` for the requested section
- **THEN** Casbin SHALL return ALLOW
- **AND** when it returns `is_subject_teacher=False`, Casbin SHALL return DENY with `ATTRIBUTE_CONDITION_FAILED`
- **AND** no business module SHALL be embedded in the Kernel for these tests

---

## MODIFIED Requirements

### Requirement: `require_permission` Dependency (Modified — ABAC pipeline)

The `require_permission` FastAPI dependency SHALL build an `AuthorizationRequest` from subject context, resource, and action; resolve required domain attributes via registered providers; evaluate ALL effective roles; invoke Casbin with RBAC + scope + attributes; and return an `AuthorizationDecision`. On DENY it SHALL raise HTTP 403 with a structured detail carrying the reason code. The `obj_client_id`, `obj_institution_id`, and `owner_id` parameters SHALL be preserved for backward compatibility. The Platform Owner bypass SHALL be retained unchanged. **Supersedes** the archived spec's "`require_permission` FastAPI Dependency" requirement.

Per AC-1, AC-11, AC-15, AC-18; PRD §8 (Q6); proposal §32.

#### Scenario: Existing callers continue to work
- **WHEN** an existing endpoint calls `require_permission("institution", "read", obj_client_id=...)`
- **THEN** authorization SHALL succeed or fail on RBAC + scope, with no ABAC attributes required

#### Scenario: All roles and attributes flow through the pipeline
- **WHEN** a caller passes a resource context for an ABAC-aware action
- **THEN** the dependency SHALL resolve required attributes via providers, evaluate all effective roles through Casbin, and raise a structured 403 carrying the reason code on DENY

#### Scenario: Platform Owner bypass retained
- **WHEN** a Platform Owner calls `require_permission`
- **THEN** the dependency SHALL return without Casbin enforcement, identical to prior behavior

---

### Requirement: Casbin Model (Modified — domain attribute matchers)

The Casbin model SHALL be extended to match domain attributes alongside the existing RBAC + scope matchers. Existing RBAC and scope matching SHALL remain unchanged. The model SHALL evaluate all effective roles (not a singular `sub.role`), and a required attribute absent from the object SHALL fail closed. **Supersedes** the archived spec's "Casbin Enforcer Singleton" requirement with respect to its model matchers.

Per AC-11, AC-12, AC-13, AC-14, AC-15; PRD §13/§14; proposal §13.

#### Scenario: Existing RBAC + scope matchers preserved
- **WHEN** a policy without ABAC conditions is evaluated
- **THEN** role grouping, resource/action, and scope matching SHALL behave exactly as before

#### Scenario: Domain attributes evaluated, business-agnostic
- **WHEN** a policy declares an attribute condition (e.g., `is_subject_teacher == true`)
- **THEN** Casbin SHALL evaluate it against the resolved attribute on the object
- **AND** a missing required attribute SHALL DENY (fail closed)
- **AND** Casbin SHALL reference only generic attribute names, never querying or importing business modules

---

### Requirement: Multi-Role Evaluation (Modified — all effective roles)

Authorization SHALL evaluate ALL effective roles for a user, not only `roles[0]`. A valid permission from any effective role MAY satisfy RBAC, subject to that role's scope and ABAC conditions. **Supersedes** the single-role (`roles[0]`) evaluation behavior.

Per AC-15, AC-16, AC-17; PRD §14; proposal §14/§31 Phase 4.

#### Scenario: Any valid role satisfies RBAC
- **WHEN** a user has roles `[HOD, Teacher]` and only `HOD` grants the permission
- **THEN** the `HOD` role SHALL satisfy RBAC and the request SHALL proceed to scope and ABAC

#### Scenario: No role satisfies — or conditions differ per role
- **WHEN** none of the user's roles grants the required permission
- **THEN** the decision SHALL DENY with `MISSING_PERMISSION`
- **AND** when multiple roles grant the same permission, each role's scope and ABAC SHALL be evaluated independently; any fully-passing role SHALL ALLOW

---

### Requirement: Policy Loader (Modified — attribute-conditional policies)

The policy loader SHALL be extended to load attribute-conditional policies, where a policy declares the domain attributes it requires. Existing `(role, resource, action, scope)` tuples SHALL load unchanged for non-conditional policies. The loader SHALL remain generic — it SHALL NOT need to understand the business meaning of declared attributes. **Supersedes** the archived spec's "C-04 Policy Registration" requirement where attribute conditions are introduced.

Per AC-38, AC-39; PRD §16; proposal §16.

#### Scenario: Non-conditional policies load unchanged
- **WHEN** the loader reads `role_permission` rows without conditions
- **THEN** policies SHALL load as `(role, resource, action, scope)` exactly as before

#### Scenario: Conditional policies declare required attributes
- **WHEN** a policy carries an attribute condition
- **THEN** the loader SHALL register it with the declared required attributes, enabling lazy resolution

---

### Requirement: Ownership Enforcement (Modified — generalized `is_self` attribute)

The app-level ownership enforcement (`owner_id` self-access) SHALL generalize to an `is_self` domain attribute supplied by a provider, with Casbin evaluating the `NOT_SELF` reason when self-access fails. The `owner_id` parameter SHALL be preserved for backward compatibility. **Supersedes** the archived spec's "Ownership Enforcement (App-Level)" requirement with respect to the hardcoded bypass.

Per AC-5; PRD §8.5; proposal §8.5; impact §2.1.

#### Scenario: Self-access via `is_self` attribute
- **WHEN** a user accesses their own resource
- **THEN** the provider SHALL supply `is_self=True` and the decision SHALL ALLOW (subject to RBAC + scope)

#### Scenario: Non-self access denied, `owner_id` compatible
- **WHEN** a user accesses another user's resource and the provider supplies `is_self=False`
- **THEN** the decision SHALL DENY with `NOT_SELF`
- **AND** an existing caller passing `owner_id` SHALL keep equivalent self-access behavior

---

## REMOVED Requirements

### Requirement: Single-Role (`roles[0]`) Evaluation (Removed)

The behavior of evaluating only the first effective role (`roles[0]`) SHALL be removed, replaced by all-roles evaluation (see "Multi-Role Evaluation").

---

## Boundary Relationships

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| Attribute provider contract | Business modules → AuthZ Kernel | C-05, C-06, Teacher/Student/Parent/Homework/Attendance (Phase 7) | Business modules implement the Kernel-owned interface; Kernel never imports business modules |
| Pipeline step 1 (authenticate) | AuthZ Kernel ← Authentication | C-03 | Precondition; authentication flow unchanged |
| Pipeline step 12 (persist under RLS) | AuthZ Kernel → Database | auth-infrastructure / PostgreSQL RLS | RLS remains defense-in-depth; success does not bypass it |
| `require_permission` signature | AuthZ Kernel → all modules | C-01, C-02, C-05, fees, homework | Existing callers preserved; new callers may pass resource context |
| Platform Owner bypass retained | AuthZ Kernel → C-01 | platform-owner-separation | No behavior change |
| Permission table / policy loader | AuthZ Kernel → C-08 | configuration | No new permission rows; attribute conditions are code-driven, not DB-driven |
