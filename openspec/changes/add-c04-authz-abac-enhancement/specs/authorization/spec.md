# Delta Spec — Authorization (ADDED + MODIFIED)

> **Change:** `add-c04-authz-abac-enhancement`
> **Domain:** authorization
> **Delta type:** ADDED + MODIFIED
> **Base spec:** `openspec/specs/authorization/spec.md` (contains base C-04 spec from `2026-07-14-add-c04-authorization` + C-05 academic-structure permission additions from `add-c05-academic-structure` + person-model revamp note from `add-c02-identity-person-model-revamp`)
> **Source PRD:** `docs/prd/c04-authz-abac-enhancement.md` (48 acceptance criteria)
> **Source proposal:** `openspec/changes/add-c04-authz-abac-enhancement/proposal.md`
> **Impact classification:** `docs/prd/c04-authz-abac-enhancement-impact.md`

---

## ADDED Requirements

### REQ-AUTHZ-ABAC-01: Authorization Request Contract

The AuthZ Kernel SHALL define an `AuthorizationRequest` type that encapsulates the full authorization context. The request SHALL contain: `subject` (SubjectContext), `resource` (ResourceContext), `action` (string), `context` (generic execution context), and `attributes` (AuthorizationAttributes). The `AuthorizationRequest` SHALL be the single input to the authorization pipeline. Per AC-1, AC-3, AC-4, AC-5; PRD §8; proposal §8/§31 Phase 1.

#### Scenario: AuthorizationRequest contains all required fields
- **WHEN** an authorization check is initiated
- **THEN** the `AuthorizationRequest` SHALL contain a `subject` field of type `SubjectContext`
- **AND** a `resource` field of type `ResourceContext`
- **AND** an `action` field of type `string`
- **AND** a `context` field for generic execution context
- **AND** an `attributes` field of type `AuthorizationAttributes`

#### Scenario: SubjectContext carries generic identity information
- **WHEN** a `SubjectContext` is constructed from an authenticated request
- **THEN** it SHALL contain `user_id` (UUID), `roles` (list of strings), `client_id` (UUID), `institution_id` (UUID), `user_tier` (string), and `is_platform_owner` (bool)
- **AND** these values SHALL be derived from the authentication context (JWT + TenantContext), never from client-supplied parameters

#### Scenario: ResourceContext carries resource-specific information
- **WHEN** a `ResourceContext` is constructed by a business module
- **THEN** it SHALL contain `resource_type` (string), `resource_id` (UUID or None), `client_id` (UUID), `institution_id` (UUID)
- **AND** MAY contain additional domain-specific fields (e.g., `section_id`, `subject_id`, `student_id`)

#### Scenario: AuthorizationAttributes carries domain attributes
- **WHEN** domain attributes are resolved by attribute providers
- **THEN** the `AuthorizationAttributes` SHALL contain key-value pairs such as `is_class_teacher` (bool), `is_subject_teacher` (bool), `is_self` (bool), `is_parent_of_resource` (bool), `is_owner` (bool), `is_assigned_to_resource` (bool)
- **AND** attribute values SHALL be derived from trusted server-side sources only

---

### REQ-AUTHZ-ABAC-02: Authorization Decision Contract

The AuthZ Kernel SHALL define an `AuthorizationDecision` type that represents the structured result of an authorization check. The decision SHALL contain: `allowed` (bool), `reason` (AuthorizationReasonCode enum), and `policy_id` (string or None). The decision SHALL be returned by the authorization service instead of raising HTTP exceptions directly. Per AC-2, AC-18, AC-19, AC-20; PRD §21; proposal §21/§31 Phase 5.

#### Scenario: Successful authorization returns ALLOW decision
- **WHEN** Casbin evaluates a request and all conditions pass
- **THEN** the `AuthorizationDecision` SHALL have `allowed=True`
- **AND** `reason` SHALL be `AuthorizationReasonCode.ALLOWED`
- **AND** `policy_id` SHALL reference the matching Casbin policy

#### Scenario: Failed authorization returns DENY decision with reason
- **WHEN** Casbin evaluates a request and a condition fails
- **THEN** the `AuthorizationDecision` SHALL have `allowed=False`
- **AND** `reason` SHALL be one of the defined reason codes
- **AND** `policy_id` SHALL reference the evaluated policy (or None if no policy matched)

#### Scenario: Reason codes cover all denial categories
- **WHEN** a denial occurs
- **THEN** the `reason` SHALL be one of: `MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED`
- **AND** reason codes SHALL be an enum (not free-form strings) for consistency and testability

#### Scenario: Reason codes are safe for controlled API responses
- **WHEN** a denial reason is included in an API response
- **THEN** it SHALL NOT expose sensitive policy internals (e.g., Casbin model details, internal policy IDs beyond what is safe)
- **AND** the reason code SHALL be suitable for internal logs and controlled API responses

---

### REQ-AUTHZ-ABAC-03: Attribute Provider Contract

The AuthZ Kernel SHALL define an `AuthorizationAttributeProvider` abstract interface that business modules implement. The provider SHALL receive the authorization subject (`SubjectContext`), resource (`ResourceContext`), and context, and return only the attributes required for evaluation (`AuthorizationAttributes`). The Kernel SHALL NOT import any business ORM models (Teacher, Student, Parent, Homework, etc.). Business modules implement the provider contract; the Kernel defines the interface. Per AC-6, AC-7, AC-8, AC-9, AC-10; PRD §9/§10/§23/§34; proposal §9/§10/§23/§31 Phase 2.

#### Scenario: Provider interface is Kernel-owned
- **WHEN** the `AuthorizationAttributeProvider` interface is defined
- **THEN** it SHALL be defined in the `kernel/authz/` package
- **AND** business modules SHALL import and implement this interface
- **AND** the Kernel SHALL NOT import from `business/` packages

#### Scenario: Provider receives subject, resource, and context
- **WHEN** a provider's `resolve_attributes()` method is called
- **THEN** it SHALL receive `subject` (SubjectContext), `resource` (ResourceContext), and execution context
- **AND** it SHALL return an `AuthorizationAttributes` instance with the resolved domain attributes

#### Scenario: Provider does NOT make the final authorization decision
- **WHEN** a provider resolves attributes
- **THEN** it SHALL return only domain facts (e.g., `is_subject_teacher=True`)
- **AND** it SHALL NOT determine whether access is allowed
- **AND** Casbin SHALL remain responsible for the final policy evaluation

#### Scenario: Provider registration at startup
- **WHEN** a business module starts up
- **THEN** it SHALL register its `AuthorizationAttributeProvider` implementation with the AuthZ Kernel
- **AND** registration SHALL happen at startup via the module manifest pattern (consistent with existing Casbin policy registration)
- **AND** the Kernel SHALL maintain a registry of providers keyed by resource type

#### Scenario: Multiple providers per resource type
- **WHEN** an authorization request arrives for a resource type that has multiple registered providers
- **THEN** the Kernel SHALL invoke all registered providers for that resource type
- **AND** each provider SHALL contribute its subset of attributes
- **AND** the combined attributes SHALL be passed to Casbin

#### Scenario: No provider registered for resource type (backward compatibility)
- **WHEN** an authorization request arrives for a resource type with no registered attribute provider
- **THEN** the Kernel SHALL proceed with empty domain attributes
- **AND** the authorization SHALL evaluate using pure RBAC + scope (existing behavior)
- **AND** no error SHALL be raised due to missing provider

#### Scenario: Provider is async
- **WHEN** a provider needs to query business tables to resolve attributes
- **THEN** the provider interface SHALL support async resolution (providers may use `await` for database queries)
- **AND** the authorization service SHALL `await` the provider's response

#### Scenario: Lazy/request-driven attribute resolution
- **WHEN** an authorization request arrives
- **THEN** the Kernel SHALL determine which attributes are required by the applicable policies
- **AND** the Kernel SHALL resolve ONLY those required attributes (not all possible attributes)
- **AND** resolved attributes SHALL be cached for the lifetime of the authorization request
- **AND** repeated lookups within the same request SHALL reuse cached values

#### Scenario: ProviderRegistry maps required attributes to providers
- **WHEN** the Kernel determines that a specific attribute (e.g., `is_subject_teacher`) is required
- **THEN** the `ProviderRegistry` SHALL identify which provider(s) can supply that attribute
- **AND** multiple providers MAY contribute attributes to one authorization request
- **AND** provider execution SHALL be deterministic

#### Scenario: Providers are stateless with injected dependencies
- **WHEN** a provider is registered at startup
- **THEN** it SHALL be application-scoped (not request-scoped)
- **AND** it SHALL be stateless — no request-specific state stored inside the provider
- **AND** dependencies (repositories, services) SHALL be injected via the constructor
- **AND** the provider SHALL NOT store request-specific data between calls

#### Scenario: Batch authorization architecture (deferred)
- **WHEN** the authorization architecture is designed
- **THEN** it SHALL support a future `authorize_many()` method
- **AND** `authorize_many()` SHALL NOT be implemented in the first iteration
- **AND** the architecture SHALL avoid N+1 provider/database queries in future batch implementations

---

### REQ-AUTHZ-ABAC-04: Casbin Integration with Domain Attributes

The Casbin enforcer SHALL evaluate subject + resource + action + scope + domain attributes together in a single enforcement call. The existing RBAC and scope behavior SHALL remain unchanged (backward compatible). Casbin SHALL NOT directly query business repositories. Casbin SHALL NOT import business ORM models. Per AC-11, AC-12, AC-13, AC-14; PRD §13; proposal §13/§31 Phase 3.

#### Scenario: Casbin evaluates RBAC + scope + attributes together
- **WHEN** `enforcer.enforce()` is called with a subject, object, action, and domain attributes
- **THEN** Casbin SHALL check: (a) role-based permission, (b) scope (client/institution), (c) domain attribute conditions
- **AND** all three must pass for the enforcement to return `True`

#### Scenario: Existing RBAC behavior is unchanged
- **WHEN** a request arrives with no domain attributes (pure RBAC scenario)
- **THEN** Casbin SHALL evaluate using the existing role + permission + scope model
- **AND** the result SHALL be identical to the pre-enhancement behavior
- **AND** no regression SHALL occur in existing role-permission mappings

#### Scenario: Casbin does NOT query business repositories
- **WHEN** Casbin evaluates a policy
- **THEN** it SHALL NOT execute SQL queries against business tables
- **AND** all domain attributes SHALL be pre-resolved by attribute providers before Casbin evaluation

#### Scenario: Casbin does NOT import business ORM models
- **WHEN** the Casbin model configuration and enforcement code are inspected
- **THEN** there SHALL be no imports from `business/` packages
- **AND** the Casbin model SHALL reference only generic attribute names (e.g., `r.obj.is_subject_teacher`), not business entity classes

---

### REQ-AUTHZ-ABAC-05: Multi-Role Evaluation

The AuthZ Kernel SHALL evaluate ALL effective roles for a user, not just the first role. A valid permission from any applicable effective role MAY satisfy RBAC, subject to scope and ABAC conditions. Users with role combinations (e.g., HOD+Teacher, Principal+Teacher) SHALL be correctly authorized. Per AC-15, AC-16, AC-17; PRD §14; proposal §14/§31 Phase 4.

#### Scenario: Single role evaluation (baseline)
- **WHEN** a user with a single role (e.g., `Teacher`) makes an authorized request
- **THEN** the Kernel SHALL evaluate the single role against the policy
- **AND** the result SHALL be the same as the current behavior

#### Scenario: Multiple roles — any valid role satisfies RBAC
- **WHEN** a user with roles `[HOD, Teacher]` makes a request where `HOD` has the required permission but `Teacher` does not
- **THEN** the Kernel SHALL evaluate both roles
- **AND** the `HOD` permission SHALL satisfy the RBAC check
- **AND** the request SHALL proceed to scope and ABAC evaluation

#### Scenario: Multiple roles — all roles lack permission
- **WHEN** a user with roles `[Student, Parent]` makes a request where neither role has the required permission
- **THEN** the Kernel SHALL evaluate both roles
- **AND** neither SHALL satisfy the RBAC check
- **AND** the decision SHALL be `DENY` with reason `MISSING_PERMISSION`

#### Scenario: Multiple roles — scope and ABAC apply per-policy
- **WHEN** a user with roles `[HOD, Teacher]` has `homework.create` via `Teacher` role but the ABAC condition `is_subject_teacher` fails
- **THEN** the `Teacher` role's policy SHALL be evaluated with its ABAC conditions
- **AND** if the `HOD` role also has `homework.create` with different ABAC conditions, those SHALL be evaluated independently
- **AND** a valid permission from any role that passes all conditions (RBAC + scope + ABAC) SHALL result in ALLOW

#### Scenario: Principal + Teacher combination
- **WHEN** a user with roles `[Principal, Teacher]` makes a request
- **THEN** both roles SHALL be evaluated
- **AND** the most permissive valid combination SHALL apply (any role that grants access with passing scope + ABAC)

---

### REQ-AUTHZ-ABAC-06: Security Invariants

The AuthZ Kernel SHALL enforce the following security invariants: (a) fail-closed — if required attributes cannot be resolved, the decision is DENY; (b) no client-supplied trust — the client cannot declare domain attributes; (c) no cross-client attribute resolution — providers must not resolve relationships outside the authenticated client boundary; (d) institution boundary — the resource must belong to an accessible institution; (e) RLS defense-in-depth — authorization success does not disable PostgreSQL RLS. Per AC-21, AC-22, AC-23, AC-24, AC-25; PRD §26; proposal §26.

#### Scenario: Missing required attribute results in DENY (fail-closed)
- **WHEN** an authorization request requires the `is_subject_teacher` attribute
- **AND** the registered provider fails to resolve it (raises an exception or returns None)
- **THEN** the decision SHALL be `DENY` with reason `ATTRIBUTE_CONDITION_FAILED`
- **AND** the system SHALL NOT interpret missing attributes as permission

#### Scenario: Client-supplied attributes are NOT trusted
- **WHEN** a client sends `{"is_class_teacher": true}` in the request body or headers
- **THEN** the Kernel SHALL NOT use this value for authorization
- **AND** domain attributes SHALL be resolved exclusively by server-side attribute providers
- **AND** any client-supplied attribute values SHALL be ignored

#### Scenario: Provider respects client boundary
- **WHEN** an attribute provider resolves business relationships
- **THEN** it SHALL scope queries to the authenticated user's `client_id`
- **AND** it SHALL NOT resolve relationships across client boundaries
- **AND** a provider that attempts cross-client resolution SHALL be considered a bug

#### Scenario: Institution boundary enforced
- **WHEN** an authorization request requires institution scope
- **AND** the resource belongs to institution B but the subject has access to institution A only
- **THEN** the decision SHALL be `DENY` with reason `INSTITUTION_ACCESS_DENIED`

#### Scenario: RLS remains active after authorization success
- **WHEN** an authorization check returns ALLOW
- **THEN** PostgreSQL RLS policies SHALL still be enforced on the database query
- **AND** the authorization success SHALL NOT disable or bypass RLS
- **AND** RLS remains defense-in-depth

---

### REQ-AUTHZ-ABAC-07: Performance Requirements

Authorization checks SHALL be lightweight enough for normal API request paths. Providers SHALL avoid loading unnecessary relationship collections. Repeated attribute lookups within a single request SHALL be reusable/cached. The implementation SHALL support batch/collection relationship checks where appropriate. No network call between modules in the modular-monolith architecture. No Kafka or external event bus introduced. Per AC-26, AC-27, AC-28, AC-29, AC-30, AC-31; PRD §27; proposal §27.

#### Scenario: Authorization check completes within API request budget
- **WHEN** an authorization check is performed as part of a normal API request
- **THEN** the total authorization time (attribute resolution + Casbin evaluation) SHALL be lightweight enough to not noticeably impact API response times
- **AND** the check SHALL complete within the existing request timeout

#### Scenario: Provider resolves only relevant attributes
- **WHEN** a provider is invoked for a homework authorization request
- **THEN** it SHALL query only the specific relationship (e.g., "is teacher T001 assigned to section 4A + Mathematics?")
- **AND** it SHALL NOT load all teacher assignments for the user

#### Scenario: Repeated lookups are cached within a request
- **WHEN** multiple authorization checks within the same request require the same attribute (e.g., `is_subject_teacher` for the same teacher + section)
- **THEN** the attribute value SHALL be resolved once and reused
- **AND** the provider SHALL NOT re-query the database for the same attribute within the same request

#### Scenario: No network calls between modules
- **WHEN** an attribute provider resolves domain attributes
- **THEN** it SHALL use in-process database queries (SQLAlchemy)
- **AND** it SHALL NOT make HTTP calls, RPC calls, or any network calls to other modules

#### Scenario: No external messaging introduced
- **WHEN** the authorization system is inspected
- **THEN** there SHALL be no Kafka producers, consumers, or external event bus connections
- **AND** authorization SHALL be synchronous within the request lifecycle

---

### REQ-AUTHZ-ABAC-08: Observability and Audit Context

Authorization decisions SHALL be traceable with structured log context. The log context SHALL include: correlation_id, user_id, client_id, institution_id, action, resource_type, resource_id, roles, scope, policy_id, decision, and reason. Domain attribute values SHALL be logged carefully to avoid unnecessary sensitive-data exposure. Per AC-32, AC-33; PRD §28; proposal §28.

#### Scenario: ALLOW decision is logged with full context
- **WHEN** an authorization check returns ALLOW
- **THEN** the log entry SHALL include: correlation_id, user_id, client_id, institution_id, action, resource_type, resource_id, roles, scope, policy_id, decision="ALLOW", reason="ALLOWED"

#### Scenario: DENY decision is logged with full context
- **WHEN** an authorization check returns DENY
- **THEN** the log entry SHALL include: correlation_id, user_id, client_id, institution_id, action, resource_type, resource_id, roles, scope, policy_id, decision="DENY", reason=<reason_code>

#### Scenario: Attribute values are logged carefully
- **WHEN** domain attributes are included in log context
- **THEN** boolean attributes (e.g., `is_subject_teacher=True`) SHALL be logged
- **AND** sensitive data (e.g., raw student IDs, relationship details) SHALL NOT be logged unnecessarily
- **AND** the log level for successful authorizations SHALL be DEBUG
- **AND** the log level for denied authorizations SHALL be WARNING

---

### REQ-AUTHZ-ABAC-09: Multiple Assignment Support

The authorization system SHALL support users with multiple relationships (e.g., teacher assigned to multiple sections and subjects). Providers SHALL evaluate the requested resource against the relationship set — they SHALL NOT assume singular attributes like `teacher.class_id`. Per AC-34, AC-35; PRD §11; proposal §11.

#### Scenario: Teacher assigned to multiple sections
- **WHEN** teacher T001 is assigned to sections 1A, 2B, 3A+Mathematics, 4A+Mathematics, 4B+Physics
- **AND** T001 requests to create homework for section 3A + Mathematics
- **THEN** the provider SHALL check the specific relationship (T001 → 3A + Mathematics)
- **AND** SHALL return `is_subject_teacher=True` for this specific combination

#### Scenario: Teacher NOT assigned to requested section
- **WHEN** teacher T001 is assigned to sections 1A, 2B, 3A+Mathematics
- **AND** T001 requests to create homework for section 5A + Mathematics
- **THEN** the provider SHALL check the specific relationship (T001 → 5A + Mathematics)
- **AND** SHALL return `is_subject_teacher=False`

#### Scenario: Provider does NOT assume singular attributes
- **WHEN** a provider resolves attributes for a teacher
- **THEN** it SHALL NOT assume `teacher.class_id` or `teacher.subject_id` as singular fields
- **AND** it SHALL query the relationship set (e.g., `teacher_assignment` table) for the specific resource combination

---

### REQ-AUTHZ-ABAC-10: Scope Model Preservation

Existing generic scopes (platform, tenant/client, institution, org unit, grade/program, class/batch, subject/course, context) SHALL be preserved. ABAC SHALL complement scope — it SHALL NOT replace it. Per AC-36, AC-37; PRD §15; proposal §15.

#### Scenario: Existing scope semantics are unchanged
- **WHEN** a policy with `scope = 'institution'` is evaluated
- **THEN** Casbin SHALL check `sub.client_id == obj.client_id AND sub.institution_id == obj.institution_id`
- **AND** this behavior SHALL be identical to the pre-enhancement behavior

#### Scenario: ABAC adds conditions on top of scope
- **WHEN** a policy requires both `institution` scope and `is_subject_teacher == true`
- **THEN** the scope check SHALL pass first (client + institution match)
- **AND** the ABAC condition SHALL be evaluated second (domain attribute check)
- **AND** both must pass for ALLOW

#### Scenario: ABAC does not replace scope
- **WHEN** a request has valid ABAC attributes but fails scope
- **THEN** the decision SHALL be `DENY` with reason `INVALID_SCOPE` or `INSTITUTION_ACCESS_DENIED`
- **AND** ABAC attributes SHALL NOT override scope failures

---

### REQ-AUTHZ-ABAC-11: Policy Model for Conditional Rules

The policy system SHALL support conditional rules such as "Teacher may create homework when `is_subject_teacher == true`". The policy system SHALL remain generic: business modules define which facts are available; the Kernel defines how policies consume them. Per AC-38, AC-39; PRD §16; proposal §16.

#### Scenario: Policy with ABAC condition
- **WHEN** a policy is defined as `(Teacher, homework.create, institution, is_subject_teacher == true)`
- **AND** a Teacher requests `homework.create` with `is_subject_teacher=True`
- **THEN** Casbin SHALL evaluate the policy and return ALLOW

#### Scenario: Policy with ABAC condition — attribute fails
- **WHEN** a policy is defined as `(Teacher, homework.create, institution, is_subject_teacher == true)`
- **AND** a Teacher requests `homework.create` with `is_subject_teacher=False`
- **THEN** Casbin SHALL evaluate the policy and return DENY
- **AND** the reason SHALL be `ATTRIBUTE_CONDITION_FAILED`

#### Scenario: Policy without ABAC condition (backward compatible)
- **WHEN** a policy is defined without ABAC conditions (existing RBAC-only policy)
- **AND** a user with the matching role requests the action
- **THEN** Casbin SHALL evaluate using RBAC + scope only (existing behavior)

#### Scenario: Business modules define available facts
- **WHEN** a business module registers an attribute provider
- **THEN** the provider declares which attributes it can supply (e.g., `is_subject_teacher`, `is_class_teacher`)
- **AND** the Kernel does NOT need to know the business meaning of these attributes
- **AND** the Kernel only needs to pass them to Casbin for policy evaluation

---

### REQ-AUTHZ-ABAC-12: Dependency Direction

Dependency direction SHALL remain `Business Module → AuthZ Kernel Contract`, never `AuthZ Kernel → Business Module`. The Kernel SHALL define interfaces/contracts; business modules SHALL implement them. Per AC-40, AC-41; PRD §23; proposal §23.

#### Scenario: Kernel defines the provider interface
- **WHEN** the `AuthorizationAttributeProvider` interface is defined
- **THEN** it SHALL be defined in `kernel/authz/`
- **AND** business modules SHALL import this interface to implement it

#### Scenario: Kernel does NOT import business modules
- **WHEN** the `kernel/authz/` package is inspected
- **THEN** there SHALL be no imports from `business/teacher/`, `business/student/`, `business/homework/`, or any other business package
- **AND** the dependency graph SHALL remain acyclic

#### Scenario: Business modules implement the contract
- **WHEN** a business module (e.g., teacher module) needs to participate in ABAC
- **THEN** it SHALL implement `AuthorizationAttributeProvider` for its domain
- **AND** it SHALL register the provider via the module manifest
- **AND** the Kernel SHALL invoke the provider without knowing its implementation details

---

### REQ-AUTHZ-ABAC-13: Subscription Interaction

The five authorization concerns SHALL remain distinct: Subscription (capability available?), Permission (role has capability?), Scope (where can role operate?), ABAC (under what business conditions?), RLS (what DB rows accessible?). Per AC-42; PRD §25; proposal §25.

#### Scenario: Five concerns are evaluated independently
- **WHEN** an authorization check is performed
- **THEN** the evaluation SHALL consider: (1) Subscription — is the capability available to this client? (2) Permission — does the user's role have the capability? (3) Scope — where can the role operate? (4) ABAC — under what business conditions? (5) RLS — what DB rows are physically accessible?
- **AND** these concerns SHALL NOT be merged into a single data model

#### Scenario: ABAC complements, does not replace, other concerns
- **WHEN** a user has valid permission, scope, and subscription
- **AND** the ABAC condition fails
- **THEN** the decision SHALL be DENY
- **AND** the denial reason SHALL indicate the ABAC failure, not a permission or scope failure

---

### REQ-AUTHZ-ABAC-14: Authorization Pipeline Standardization

The AuthZ Kernel SHALL standardize the 12-step authorization pipeline: (1) Authenticate request, (2) Build TenantContext, (3) Identify subject, (4) Identify action, (5) Identify target resource, (6) Resolve generic scope/context, (7) Determine required domain attributes, (8) Resolve domain attributes, (9) Invoke Casbin, (10) Return structured decision, (11) Continue business operation if ALLOW, (12) Execute persistence under PostgreSQL RLS. Per PRD §22; proposal §22.

#### Scenario: Pipeline executes steps in order
- **WHEN** an authorized API request is processed
- **THEN** the pipeline SHALL execute steps 1–12 in order
- **AND** each step SHALL complete before the next begins
- **AND** if any step fails (e.g., step 8 attribute resolution fails), the pipeline SHALL short-circuit to step 10 with a DENY decision

#### Scenario: Steps 1–2 are owned by authentication/middleware
- **WHEN** the pipeline executes
- **THEN** steps 1 (authenticate) and 2 (build TenantContext) SHALL be completed by the authentication middleware before the authorization pipeline begins
- **AND** the authorization pipeline SHALL receive the authenticated context as input

#### Scenario: Steps 4–5 are owned by business modules
- **WHEN** the pipeline executes
- **THEN** steps 4 (identify action) and 5 (identify target resource) SHALL be determined by the business module
- **AND** the business module SHALL construct the `ResourceContext` with the action and resource details

#### Scenario: Steps 6–10 are owned by the AuthZ Kernel
- **WHEN** the pipeline executes
- **THEN** steps 6 (resolve scope), 7 (determine attributes), 8 (resolve attributes), 9 (invoke Casbin), and 10 (return decision) SHALL be executed by the AuthZ Kernel
- **AND** the Kernel SHALL invoke registered attribute providers for step 8

---

### REQ-AUTHZ-ABAC-15: Synthetic-Attribute Testing

The AuthZ Kernel SHALL be validated independently using test providers and fake attributes before any business module integration. A test-only implementation SHALL demonstrate: Teacher T001 with `homework.create` + Section 1A + Mathematics + `is_subject_teacher=true` → Casbin ALLOW. A test-only implementation SHALL demonstrate: Teacher T001 with `homework.create` + Section 5A + Mathematics + `is_subject_teacher=false` → Casbin DENY. These demonstrations SHALL work without any Teacher, Homework, Academic, or Student business implementation embedded in the AuthZ Kernel. Per AC-46, AC-47, AC-48; PRD §35; proposal §35 Phase 6.

#### Scenario: Synthetic ALLOW — teacher assigned to requested section
- **WHEN** a test provider returns `is_subject_teacher=True` for teacher T001 + section 1A + Mathematics
- **AND** the authorization request is `(subject=Teacher T001, action=homework.create, resource={section_id=1A, subject_id=Mathematics})`
- **THEN** Casbin SHALL evaluate and return ALLOW
- **AND** the test SHALL pass without any real Teacher or Homework business module

#### Scenario: Synthetic DENY — teacher NOT assigned to requested section
- **WHEN** a test provider returns `is_subject_teacher=False` for teacher T001 + section 5A + Mathematics
- **AND** the authorization request is `(subject=Teacher T001, action=homework.create, resource={section_id=5A, subject_id=Mathematics})`
- **THEN** Casbin SHALL evaluate and return DENY
- **AND** the reason SHALL be `ATTRIBUTE_CONDITION_FAILED`
- **AND** the test SHALL pass without any real Teacher or Homework business module

#### Scenario: Test providers are isolated from production
- **WHEN** synthetic-attribute tests run
- **THEN** they SHALL use test-only attribute providers that return hardcoded or fixture-based attributes
- **AND** these providers SHALL NOT be registered in the production provider registry
- **AND** the tests SHALL validate the authorization engine independently of business module implementations

---

### REQ-AUTHZ-ABAC-16: Testing Requirements

The authorization test suite SHALL cover: unit tests for single role, multiple roles, missing permission, tenant scope, institution scope, successful ABAC, failed ABAC, missing required attribute, multiple assignments, conflicting assignments. Security tests SHALL verify: Client A → Client B = DENY, Institution A → Institution B = DENY, Teacher assigned to 1A → 1A = ALLOW, Teacher assigned to 1A → 1B = DENY, Student S1 → S1 attendance = ALLOW, Student S1 → S2 attendance = DENY. Regression tests SHALL confirm existing RBAC and scope behavior is unchanged. Per AC-43, AC-44, AC-45; PRD §29; proposal §29.

#### Scenario: Unit tests cover all authorization scenarios
- **WHEN** the authorization test suite runs
- **THEN** it SHALL include tests for: single role ALLOW, single role DENY, multiple roles ALLOW (any valid), multiple roles DENY (none valid), missing permission, tenant scope pass, tenant scope fail, institution scope pass, institution scope fail, ABAC condition pass, ABAC condition fail, missing required attribute (fail-closed), multiple assignments (correct section), multiple assignments (wrong section), conflicting assignments

#### Scenario: Security tests verify cross-tenant and cross-institution isolation
- **WHEN** security tests run
- **THEN** they SHALL verify: Client A user accessing Client B resource = DENY, Institution A user accessing Institution B resource = DENY

#### Scenario: Security tests verify domain-specific ABAC
- **WHEN** security tests run
- **THEN** they SHALL verify: Teacher assigned to section 1A accessing section 1A = ALLOW, Teacher assigned to section 1A accessing section 1B = DENY, Student S1 accessing S1 attendance = ALLOW, Student S1 accessing S2 attendance = DENY

#### Scenario: Regression tests confirm backward compatibility
- **WHEN** regression tests run
- **THEN** all existing RBAC and scope tests SHALL pass unchanged
- **AND** no existing authorization behavior SHALL be broken by the ABAC enhancement

---

## MODIFIED Requirements

### REQ-AUTHZ-MOD-01: `require_permission` Dependency (Modified — ABAC pipeline)

The `require_permission` FastAPI dependency SHALL be extended to use the new authorization pipeline. It SHALL build an `AuthorizationRequest` from the subject context, resource, and action; resolve domain attributes via registered providers; evaluate all effective roles; invoke Casbin with RBAC + scope + attributes; and return an `AuthorizationDecision`. The existing `obj_client_id`, `obj_institution_id`, and `owner_id` parameters SHALL be preserved for backward compatibility. The dependency SHALL raise HTTP 403 with a structured detail message including the reason code when the decision is DENY. **Supersedes** the existing `require_permission` requirement in the base spec. Per AC-1 through AC-5, AC-11, AC-15, AC-18; PRD §6.6; proposal §32.

#### Scenario: Existing callers continue to work (backward compatibility)
- **WHEN** an existing endpoint uses `require_permission("institution", "read", obj_client_id=ctx.client_id)`
- **THEN** the dependency SHALL work identically to the pre-enhancement behavior
- **AND** the authorization SHALL succeed or fail based on RBAC + scope (no ABAC attributes needed)

#### Scenario: New callers can pass resource context for ABAC
- **WHEN** a business module calls `require_permission("homework", "create", resource_context=ResourceContext(...))`
- **THEN** the dependency SHALL build an `AuthorizationRequest` including the resource context
- **AND** registered attribute providers for the resource type SHALL be invoked
- **AND** Casbin SHALL evaluate RBAC + scope + domain attributes

#### Scenario: All effective roles are evaluated
- **WHEN** `require_permission` is called for a user with roles `[HOD, Teacher]`
- **THEN** the dependency SHALL evaluate both roles against the policy
- **AND** a valid permission from any role SHALL satisfy the RBAC check
- **AND** the current behavior of using only `roles[0]` SHALL be replaced

#### Scenario: Structured 403 response with reason code
- **WHEN** the authorization decision is DENY
- **THEN** the HTTP 403 response detail SHALL include the reason code (e.g., `"Permission denied: ATTRIBUTE_CONDITION_FAILED"`)
- **AND** the reason code SHALL be one of the defined `AuthorizationReasonCode` enum values

#### Scenario: Platform Owner bypass is retained
- **WHEN** a Platform Owner calls `require_permission` for any resource and action
- **THEN** the dependency SHALL return silently (no 403) before Casbin enforcement runs
- **AND** this behavior SHALL be identical to the pre-enhancement behavior

---

### REQ-AUTHZ-MOD-02: Casbin Model (Modified — domain attribute matchers)

The Casbin model at `kernel/authz/casbin_model.conf` SHALL be extended to support domain attribute matching in addition to the existing RBAC + scope matchers. The model SHALL accept domain attributes on the object (e.g., `r.obj.is_subject_teacher`) and match them against policy conditions. The existing RBAC + scope matchers SHALL remain unchanged. **Supersedes** the existing Casbin model matchers. Per AC-11, AC-12, AC-13, AC-14; PRD §13; proposal §13.

#### Scenario: Existing RBAC + scope matcher is preserved
- **WHEN** a policy is evaluated without ABAC conditions
- **THEN** the matcher SHALL evaluate: `g(r.sub.role, p.sub) && (p.obj == "*" || p.obj == r.obj.name) && (p.act == "*" || p.act == r.act) && scope_check`
- **AND** this SHALL be identical to the pre-enhancement matcher behavior

#### Scenario: ABAC attribute matcher is added
- **WHEN** a policy includes ABAC conditions (e.g., `is_subject_teacher == true`)
- **THEN** the matcher SHALL also evaluate the attribute condition against `r.obj.is_subject_teacher`
- **AND** the attribute value SHALL come from the resolved domain attributes (pre-populated on the Casbin object)

#### Scenario: Missing attributes in object default to fail-closed
- **WHEN** a policy requires `is_subject_teacher == true` but the object does not have this attribute
- **THEN** the matcher SHALL treat the missing attribute as a failure
- **AND** the enforcement SHALL return `False` (DENY)

---

### REQ-AUTHZ-MOD-03: Policy Loader (Modified — attribute-conditional policies)

The policy loader SHALL be extended to support attribute-conditional policies in addition to the existing `(role, resource, action, scope)` tuples. The loader SHALL read attribute conditions from the policy definition (or configuration) and register them with the Casbin enforcer. The existing policy loading behavior SHALL remain unchanged for policies without ABAC conditions. **Supersedes** the existing policy loader requirement. Per AC-38, AC-39; PRD §16; proposal §16.

#### Scenario: Existing policies load unchanged
- **WHEN** the app starts and the policy loader reads `role_permission` rows
- **THEN** policies without ABAC conditions SHALL be loaded as `(role_name, resource, action, scope)` tuples
- **AND** this behavior SHALL be identical to the pre-enhancement policy loader

#### Scenario: Attribute-conditional policies are loaded
- **WHEN** a policy definition includes ABAC conditions (e.g., `is_subject_teacher == true`)
- **THEN** the policy loader SHALL register the policy with the attribute condition
- **AND** Casbin SHALL evaluate the condition during enforcement

#### Scenario: Policy format supports generic attribute conditions
- **WHEN** a policy is defined with an ABAC condition
- **THEN** the condition SHALL reference generic attribute names (e.g., `is_subject_teacher`, `is_self`, `is_class_teacher`)
- **AND** the Kernel SHALL NOT need to understand the business meaning of these attributes
- **AND** business modules SHALL define which attributes are available via their providers

---

## Boundary Relationships

| Relationship | Direction | Other capability | Nature |
|---|---|---|---|
| Attribute provider contract | Business modules → AuthZ Kernel | C-05 Academic Structure, C-06 Relationships, Teacher/Student/Parent modules | Business modules implement the Kernel-owned interface; no Kernel dependency on business modules |
| Authorization pipeline step 1 | AuthZ Kernel → Authentication (C-03) | C-03 Authentication | Authentication is a precondition; the Kernel receives the authenticated context |
| Authorization pipeline step 12 | AuthZ Kernel → Database (RLS) | PostgreSQL RLS | RLS remains defense-in-depth; authorization success does not bypass RLS |
| `require_permission` signature | AuthZ Kernel → All modules | C-01, C-02, C-05, fees, homework, all business modules | Existing callers preserved; new callers can pass resource context for ABAC |
| Platform Owner bypass retained | AuthZ Kernel → C-01 | C-01 Platform Owner | No behavior change |
| Casbin model extension | AuthZ Kernel → Self | Internal | Model file changes; existing policies remain valid |
| Permission table unchanged | AuthZ Kernel → C-08 Configuration | C-08 | No new permissions added by this enhancement; attribute providers are code-driven, not DB-driven |
