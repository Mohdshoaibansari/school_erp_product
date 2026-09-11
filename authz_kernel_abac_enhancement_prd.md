# PRD --- AuthZ Kernel ABAC Enhancement

**Product:** Multi-Tenant School ERP\
**Capability:** C-04 Authorization / AuthZ Kernel\
**Enhancement:** Business-Domain Attribute-Based Authorization (ABAC)\
**Status:** Proposed / Ready for Design Discussion\
**Architecture:** Modular Monolith, FastAPI, SQLAlchemy 2.x,
PostgreSQL/Supabase, Casbin\
**Scope:** AuthZ Kernel only. Business-module implementation is
explicitly out of scope for this phase.

------------------------------------------------------------------------

## 1. Executive Summary

The School ERP already has a centralized Authorization capability based
on roles, permissions, and scopes. The next enhancement is to extend the
AuthZ Kernel so that it can evaluate **business-domain authorization
attributes** in addition to generic identity, role, tenant, and
institution context.

The goal is not to move Teacher, Student, Parent, Homework, Academic, or
other business logic into the AuthZ Kernel.

Instead:

-   The Kernel owns the authorization framework and decision process.
-   Casbin remains the policy evaluation engine.
-   Authentication/middleware provides generic subject context.
-   Business modules will eventually provide domain-specific facts
    required for an authorization decision.
-   RLS remains the database-level isolation mechanism.
-   Domain relationships remain owned by their respective business
    domains.

Example:

> `Teacher T001` has `homework.create` permission, but may create
> homework only when the requested class/subject is within the teacher's
> permitted academic relationship.

The AuthZ Kernel must provide the mechanism to evaluate this without
storing teacher assignments as Casbin policies.

------------------------------------------------------------------------

# 2. Background

The current platform architecture defines C-04 Authorization as a Kernel
capability. It owns:

-   Permission
-   Role
-   RoleAssignment
-   Scope
-   Policy
-   TemporaryRole

The project specification explicitly defines Authorization as RBAC +
ABAC, with authorization layers including Platform, Client, Institution,
Org Unit, Grade/Program, Class/Batch, Subject/Course, and Context.

The current system also has:

-   Authentication-derived request context
-   `client_id`
-   `institution_id`
-   user identity
-   roles
-   user tier / platform-owner context
-   Casbin-based authorization
-   PostgreSQL RLS for database isolation

The academic model already contains domain relationships such as:

-   `section.homeroom_teacher_id`
-   `teacher_assignment`
-   `student_enrollment`

These relationships are business-domain data and must remain the source
of truth.

------------------------------------------------------------------------

# 3. Problem Statement

Current role/permission/scope authorization can answer questions such
as:

``` text
Does Teacher have homework.create?
Does this user have institution scope?
Does this request belong to the user's client?
```

It cannot, by itself, answer contextual business questions such as:

``` text
Is this teacher assigned to the requested section?
Is this teacher assigned to the requested subject?
Is this teacher the homeroom/class teacher?
Is this student accessing their own attendance?
Is this parent accessing attendance of their own child?
Did this teacher create this homework?
```

These decisions require business-domain attributes and relationships.

The enhancement must provide a generic mechanism for incorporating these
facts into Casbin evaluation without coupling the AuthZ Kernel to
business-module persistence models.

------------------------------------------------------------------------

# 4. Goals

## 4.1 Primary Goals

1.  Extend the AuthZ Kernel from generic RBAC/scope checks to contextual
    ABAC.
2.  Keep Casbin as the centralized authorization decision engine.
3.  Support request-specific business attributes.
4.  Allow business modules to contribute authorization facts without
    becoming part of the Kernel.
5.  Preserve the existing `TenantContext` and authentication flow.
6.  Preserve existing permission and scope semantics.
7.  Support users with multiple roles.
8.  Support relationships involving multiple resources, such as:
    -   Teacher → multiple Sections
    -   Teacher → multiple Subjects
    -   Student → own identity
    -   Parent → multiple Students
9.  Keep business-domain data outside Casbin policy storage.
10. Keep PostgreSQL RLS as defense-in-depth for database isolation.
11. Provide explainable authorization decisions for debugging and audit.
12. Avoid premature implementation of a generic rules engine inside
    AuthZ.

## 4.2 Secondary Goals

-   Make ABAC extensible for future business modules.
-   Avoid loading unnecessary business-domain data.
-   Support efficient authorization checks for collection relationships.
-   Maintain modular dependency direction.
-   Keep the Kernel independent from Teacher, Student, Parent, Homework,
    Attendance, and other modules.

------------------------------------------------------------------------

# 5. Non-Goals

This enhancement MUST NOT:

1.  Implement Teacher business logic.
2.  Implement Student business logic.
3.  Implement Parent/Guardian relationship management.
4.  Implement Homework authorization rules specifically inside the
    Kernel.
5.  Move `teacher_assignment` into AuthZ.
6.  Move `student_enrollment` into AuthZ.
7.  Store individual teacher-to-class relationships as Casbin policies.
8.  Replace PostgreSQL RLS.
9.  Replace authentication.
10. Introduce Kafka or an external messaging system.
11. Build a new generic rules engine.
12. Make AuthZ directly query arbitrary business tables.
13. Make every business module depend on another business module's ORM
    models.
14. Redesign the existing module architecture unless required by this
    enhancement.

------------------------------------------------------------------------

# 6. Architectural Principles

## 6.1 Authentication ≠ Authorization

Authentication establishes:

> Who is the caller?

Authorization establishes:

> Is this caller allowed to perform this operation against this resource
> in this context?

------------------------------------------------------------------------

## 6.2 Permission ≠ Business Relationship

Example:

``` text
homework.create
```

means:

> The user's role is allowed to create homework.

It does NOT mean:

> The teacher may create homework for every class.

The second decision requires business context.

------------------------------------------------------------------------

## 6.3 Business Data ≠ Authorization Policy Data

The following remain business-domain source-of-truth data:

``` text
teacher_assignment
student_enrollment
section.homeroom_teacher_id
parent_student_relationship
```

Casbin must not become a replica of these relationships.

------------------------------------------------------------------------

## 6.4 RLS ≠ Complete Business Authorization

RLS protects database boundaries.

Typical responsibility:

``` text
client_id
institution_id
```

depending on the existing policy.

RLS must not become the primary location for complex business rules such
as:

``` text
Teacher is assigned to Section 1A.
```

Business relationships are evaluated at the authorization/application
layer.

------------------------------------------------------------------------

## 6.5 Kernel Must Remain Business-Agnostic

The AuthZ Kernel may understand concepts such as:

``` text
subject
resource
action
scope
attribute
policy
authorization decision
```

It must NOT understand:

``` text
TeacherAssignment ORM model
Homework ORM model
StudentEnrollment ORM model
ParentChild ORM model
```

------------------------------------------------------------------------

# 7. Target Authorization Model

The target model is:

``` text
                    HTTP Request
                         |
                         v
                Authentication Context
                         |
                         v
                   TenantContext
                         |
                         v
                   Business Module
                         |
              Build Resource Context
                         |
                         v
                   Authorization
                         |
              +----------+----------+
              |                     |
       Generic Context       Domain Attributes
              |                     |
              |              Business Provider
              |                     |
              +----------+----------+
                         |
                         v
                       Casbin
                         |
                 RBAC + ABAC
                         |
                    ALLOW/DENY
                         |
                         v
                   Application
                         |
                         v
                  PostgreSQL RLS
```

------------------------------------------------------------------------

# 8. Authorization Context Model

The AuthZ Kernel should conceptually evaluate an `AuthorizationRequest`.

``` python
AuthorizationRequest(
    subject=...,
    resource=...,
    action=...,
    context=...,
    attributes=...
)
```

## 8.1 Subject

Generic identity/security information:

``` text
user_id
roles
client_id
institution_id
user_tier
platform_owner status
```

The current request context remains the primary source.

------------------------------------------------------------------------

## 8.2 Resource

The business operation supplies resource-specific information.

Example:

``` text
resource_type = homework
resource_id = HW001
client_id = C001
institution_id = I001
section_id = S1A
subject_id = MATH
academic_year_id = AY2026
```

------------------------------------------------------------------------

## 8.3 Action

Examples:

``` text
create
read
update
delete
publish
approve
submit
grade
mark
```

The existing permission model remains the primary capability gate.

------------------------------------------------------------------------

## 8.4 Context

Generic execution context:

``` text
client
institution
academic year
current date/time
request metadata where required
```

The Kernel owns generic context handling.

------------------------------------------------------------------------

## 8.5 Domain Attributes

Domain attributes are facts required to evaluate contextual policies.

Examples:

``` text
is_class_teacher
is_subject_teacher
is_self
is_parent_of_resource
is_owner
is_assigned_to_resource
```

These are NOT necessarily persistent fields.

They can be derived for the specific authorization request.

------------------------------------------------------------------------

# 9. Attribute Provider Concept

The AuthZ Kernel should define a generic contract for resolving
authorization-relevant domain attributes.

Conceptually:

``` text
AuthorizationAttributeProvider
```

A provider receives the authorization subject/resource/context and
returns only the attributes required for evaluation.

Example:

``` text
TeacherAuthorizationAttributeProvider
```

could evaluate:

``` text
teacher_id = T001
section_id = S1A
subject_id = MATH
academic_year_id = AY2026
```

and return:

``` json
{
  "is_class_teacher": true,
  "is_subject_teacher": true
}
```

The provider does not make the final authorization decision.

Casbin remains responsible for policy evaluation.

------------------------------------------------------------------------

# 10. Provider Responsibility

A domain provider answers:

> What business facts are true for this authorization request?

It does NOT answer:

> Is access allowed?

Example:

``` text
Teacher Provider
        |
        v
Is T001 assigned to Section 1A?
        |
        v
is_subject_teacher = true
```

Casbin then evaluates:

``` text
Teacher
+
homework.create
+
institution scope
+
is_subject_teacher = true
```

------------------------------------------------------------------------

# 11. Multiple Assignments

The system MUST support users with multiple relationships.

Example:

``` text
Teacher T001

Class Teacher:
    1A
    2B

Subject Teacher:
    3A + Mathematics
    4A + Mathematics
    4B + Physics
```

The provider must evaluate the requested resource against the
relationship set.

It must NOT assume:

``` text
teacher.class_id
teacher.subject_id
```

as singular attributes.

------------------------------------------------------------------------

# 12. Request-Specific Attribute Resolution

The system should avoid loading every relationship belonging to a user.

Bad approach:

``` text
Every request
    |
    +-- load all teacher assignments
    +-- load all student enrollments
    +-- load all parent relationships
    +-- load all other domain data
```

Preferred approach:

``` text
Authorization request
        |
        v
Determine required attributes
        |
        v
Resolve only relevant domain facts
        |
        v
Casbin
```

Example:

``` text
Teacher T001
Homework:
    Section = 4A
    Subject = Mathematics

Provider checks only:
    T001 + 4A + Mathematics + AY2026
```

------------------------------------------------------------------------

# 13. Casbin Responsibilities

Casbin remains responsible for:

1.  Role-based permission evaluation.
2.  Scope evaluation.
3.  Attribute-based conditions.
4.  Final ALLOW/DENY decision.
5.  Centralized policy evaluation.
6.  Policy consistency across modules.

Casbin should not:

-   query business repositories directly;
-   import business ORM models;
-   own Teacher assignments;
-   own Student enrollment;
-   maintain a duplicate relationship database.

------------------------------------------------------------------------

# 14. Multi-Role Support

The authorization system MUST evaluate all effective roles.

A user may have:

``` text
Principal
Teacher
```

or:

``` text
HOD
Teacher
```

or other combinations.

The system MUST NOT reduce multiple roles to only the first role.

Authorization should effectively evaluate:

``` text
roles[]
+
permission
+
scope
+
attributes
```

A valid permission from any applicable effective role may satisfy the
RBAC portion, subject to scope and ABAC conditions.

------------------------------------------------------------------------

# 15. Scope Model

Existing generic scopes remain conceptually:

``` text
platform
tenant/client
institution
org unit
grade/program
class/batch
subject/course
context
```

The enhancement must not unnecessarily replace these with a new scope
model.

ABAC should complement scope.

Example:

``` text
Role:
    Teacher

Permission:
    homework.create

Scope:
    institution

ABAC:
    teacher is assigned to target section/subject
```

------------------------------------------------------------------------

# 16. Policy Model

The existing Authorization specification defines a formal Policy entity
for conditional rules.

The enhanced design should support policies conceptually such as:

``` text
Teacher may create homework
when:
    is_subject_teacher == true
```

or:

``` text
Teacher may update homework
when:
    is_owner == true
```

or:

``` text
Student may read attendance
when:
    is_self == true
```

or:

``` text
Parent may read attendance
when:
    is_parent_of_resource == true
```

The policy system must remain generic.

Business modules define which business facts are available; the Kernel
defines how policies consume them.

------------------------------------------------------------------------

# 17. Example --- Teacher Homework Authorization

## Request

``` text
Teacher T001
Create Homework
Section = 4A
Subject = Mathematics
Academic Year = 2026-27
```

## Generic context

``` text
user_id = U001
role = Teacher
client_id = C001
institution_id = I001
```

## Permission

``` text
homework.create
```

## Domain facts

``` text
is_class_teacher = false
is_subject_teacher = true
```

## Casbin decision

``` text
Teacher
+
homework.create
+
institution scope
+
is_subject_teacher
=
ALLOW
```

------------------------------------------------------------------------

# 18. Example --- Unauthorized Teacher

Teacher T001 attempts:

``` text
Section = 5A
Subject = Mathematics
```

Provider returns:

``` text
is_class_teacher = false
is_subject_teacher = false
```

Casbin:

``` text
homework.create
+
Teacher
+
institution
+
required ABAC condition
```

Result:

``` text
DENY
```

------------------------------------------------------------------------

# 19. Example --- Student SELF

Subject:

``` text
student_id = S001
```

Resource:

``` text
attendance.student_id = S001
```

Domain attribute:

``` text
is_self = true
```

Casbin:

``` text
Student
+
attendance.read
+
is_self
=
ALLOW
```

For:

``` text
attendance.student_id = S002
```

the attribute becomes:

``` text
is_self = false
```

and access is denied.

------------------------------------------------------------------------

# 20. Example --- Parent → Child

Subject:

``` text
parent_id = P001
```

Resource:

``` text
student_id = S002
```

Domain provider determines:

``` text
is_parent_of_resource = true
```

Casbin evaluates the policy.

The relationship itself remains owned by the appropriate business/domain
capability.

------------------------------------------------------------------------

# 21. Authorization Decision Response

The Kernel should provide a structured decision.

Conceptually:

``` python
AuthorizationDecision(
    allowed=True,
    reason="ALLOWED",
    policy_id="...",
)
```

For denial:

``` python
AuthorizationDecision(
    allowed=False,
    reason="NOT_ASSIGNED_TO_RESOURCE",
    policy_id="..."
)
```

Potential reason codes:

``` text
MISSING_PERMISSION
INVALID_SCOPE
TENANT_ACCESS_DENIED
INSTITUTION_ACCESS_DENIED
ATTRIBUTE_CONDITION_FAILED
NOT_ASSIGNED_TO_RESOURCE
NOT_SELF
NOT_PARENT_OF_RESOURCE
POLICY_DENIED
```

Reason codes should be safe for internal logs and controlled API
responses.

Sensitive policy internals must not be unnecessarily exposed to clients.

------------------------------------------------------------------------

# 22. Authorization Pipeline

The Kernel should standardize the following conceptual pipeline:

``` text
1. Authenticate request
2. Build TenantContext
3. Identify subject
4. Identify action
5. Identify target resource
6. Resolve generic scope/context
7. Determine required domain attributes
8. Resolve domain attributes
9. Invoke Casbin
10. Return structured decision
11. Continue business operation if ALLOW
12. Execute persistence under PostgreSQL RLS
```

------------------------------------------------------------------------

# 23. Dependency Direction

The dependency direction MUST remain:

``` text
Business Module
        |
        v
AuthZ Kernel Contract
```

and never:

``` text
AuthZ Kernel
        |
        v
Teacher Module
```

The Kernel must define interfaces/contracts.

Business modules may implement those contracts.

This preserves modular-monolith boundaries.

------------------------------------------------------------------------

# 24. Business Module Boundary

This PRD does NOT define the internal architecture of:

``` text
Teacher
Student
Parent
Homework
Academic
Attendance
```

Those modules will be designed separately.

This enhancement only defines the **Kernel-side contract** required for
those future modules to participate in ABAC.

------------------------------------------------------------------------

# 25. Subscription Interaction

Subscription is a separate concern.

The following are distinct:

``` text
Subscription:
    Is the capability available to this client?

Permission:
    Does this role have the capability?

Scope:
    Where can the role operate?

ABAC:
    Under what business conditions can it operate?

RLS:
    What database rows can be physically accessed?
```

The final authorization architecture should support these concerns
without merging them into one data model.

------------------------------------------------------------------------

# 26. Security Requirements

## 26.1 Fail Closed

If required authorization attributes cannot be resolved:

``` text
DENY
```

The system must never interpret missing attributes as permission.

------------------------------------------------------------------------

## 26.2 No Client-Supplied Trust

The client must not be allowed to declare:

``` json
{
  "is_class_teacher": true
}
```

and have the Kernel trust it.

Domain attributes must be derived from trusted server-side sources.

------------------------------------------------------------------------

## 26.3 No Cross-Client Attribute Resolution

A provider must never resolve business relationships outside the
authenticated client boundary.

------------------------------------------------------------------------

## 26.4 Institution Boundary

Where institution scope is required, the authorization context must
ensure the resource belongs to an institution the subject can access.

------------------------------------------------------------------------

## 26.5 RLS Defense-in-Depth

Authorization success must not disable or bypass PostgreSQL RLS.

------------------------------------------------------------------------

# 27. Performance Requirements

1.  Authorization checks should be lightweight enough for normal API
    request paths.
2.  Providers must avoid loading unnecessary relationship collections.
3.  Repeated attribute lookups within a single request should be
    reusable/cached.
4.  The implementation should support batch/collection relationship
    checks where appropriate.
5.  No network call should be required between modules in the current
    modular-monolith architecture.
6.  Do not introduce Kafka or an external event bus for this feature.

------------------------------------------------------------------------

# 28. Observability and Audit

Authorization decisions should be traceable.

At minimum, internal logs/audit context should capture:

``` text
correlation_id
user_id
client_id
institution_id
action
resource_type
resource_id
roles
scope
policy_id
decision
reason
```

Domain attribute values should be logged carefully to avoid unnecessary
sensitive-data exposure.

------------------------------------------------------------------------

# 29. Testing Requirements

## 29.1 Unit Tests

Test:

-   single role;
-   multiple roles;
-   missing permission;
-   tenant scope;
-   institution scope;
-   successful ABAC;
-   failed ABAC;
-   missing required attribute;
-   multiple assignments;
-   conflicting assignments;
-   expired/invalid contextual access where applicable.

## 29.2 Security Tests

Must verify:

``` text
Client A → Client B = DENY
Institution A → Institution B = DENY
Teacher assigned to 1A → 1A = ALLOW
Teacher assigned to 1A → 1B = DENY
Student S1 → S1 attendance = ALLOW
Student S1 → S2 attendance = DENY
```

## 29.3 Regression Tests

Existing RBAC and scope behavior must remain unchanged.

------------------------------------------------------------------------

# 30. Acceptance Criteria

The enhancement is complete when:

-   [ ] Existing AuthZ APIs continue working.
-   [ ] Existing permission model remains backward compatible.
-   [ ] Multiple roles are evaluated correctly.
-   [ ] Authorization supports request-specific resource attributes.
-   [ ] AuthZ supports domain attribute providers through a Kernel-owned
    contract.
-   [ ] Casbin can evaluate business attributes.
-   [ ] Business ORM models are not imported into AuthZ Kernel.
-   [ ] Casbin does not directly query business repositories.
-   [ ] Missing attributes fail closed.
-   [ ] Domain attributes cannot be trusted from client input.
-   [ ] Multiple teacher assignments are supported.
-   [ ] Authorization decisions are explainable internally.
-   [ ] RLS remains active.
-   [ ] No external messaging system is introduced.
-   [ ] Unit and integration security tests cover the new behavior.

------------------------------------------------------------------------

# 31. Recommended Implementation Phases

## Phase 1 --- Authorization Contract

Implement/define:

``` text
AuthorizationRequest
AuthorizationDecision
SubjectContext
ResourceContext
AuthorizationAttributes
```

without implementing business modules.

------------------------------------------------------------------------

## Phase 2 --- Attribute Provider Contract

Define a Kernel-owned interface:

``` text
AuthorizationAttributeProvider
```

with registration/resolution semantics.

No Teacher/Student implementation is required yet.

------------------------------------------------------------------------

## Phase 3 --- Casbin Integration

Extend the existing Casbin adapter/model to consume:

``` text
subject
resource
action
scope
attributes
```

while preserving current authorization behavior.

------------------------------------------------------------------------

## Phase 4 --- Multiple Role Evaluation

Correctly support:

``` text
roles[]
```

instead of treating only one role as the effective role.

------------------------------------------------------------------------

## Phase 5 --- Decision and Error Model

Standardize:

``` text
ALLOW
DENY
reason
policy_id
```

and internal diagnostic information.

------------------------------------------------------------------------

## Phase 6 --- Test the Kernel with Synthetic Attributes

Before integrating business modules, use test providers/fake attributes.

Example:

``` text
is_class_teacher = true
is_subject_teacher = false
```

This validates the AuthZ engine independently.

------------------------------------------------------------------------

## Phase 7 --- Business Module Integration

This phase is explicitly outside this PRD.

Later:

``` text
Teacher → Teacher Authorization Provider
Student → Student Authorization Provider
Parent → Parent Authorization Provider
Homework → Resource Context
```

will be designed separately.

------------------------------------------------------------------------

# 32. Example Target API

The exact Python API should be decided during technical design, but the
conceptual API should resemble:

``` python
decision = await authorization_service.authorize(
    subject=subject_context,
    action="homework.create",
    resource=resource_context,
)
```

Internally:

``` text
AuthorizationService
    |
    +-- resolve generic context
    |
    +-- resolve required attributes
    |
    +-- invoke Casbin
    |
    +-- return AuthorizationDecision
```

Business modules should not interact directly with the Casbin enforcer.

------------------------------------------------------------------------

# 33. Architectural Decision

The recommended architecture is:

``` text
                  AUTHZ KERNEL
                       |
        +--------------+--------------+
        |                             |
     Casbin                  Provider Contract
        |                             |
        |                   +---------+---------+
        |                   |         |         |
        |                Teacher   Student   Parent
        |                Provider  Provider  Provider
        |                   |         |         |
        |                   v         v         v
        |                Business Domain Data
        |
        v
 ALLOW / DENY
```

The Kernel owns:

``` text
authorization request
authorization decision
policy evaluation
Casbin integration
provider contract
scope evaluation
error model
observability
```

Business modules own:

``` text
business relationships
domain facts
domain data
attribute provider implementation
```

------------------------------------------------------------------------

# 34. Important Design Constraint

Do NOT implement the following:

``` text
AuthZ Kernel
    |
    +-- TeacherRepository
    +-- StudentRepository
    +-- HomeworkRepository
    +-- ParentRepository
```

This would destroy the intended modular architecture.

Instead:

``` text
AuthZ Kernel
    |
    +-- AuthorizationAttributeProvider interface
```

and business modules implement the contract.

------------------------------------------------------------------------

# 35. Definition of Done

The AuthZ Kernel enhancement is considered ready for business-module
adoption when a test-only implementation can demonstrate:

``` text
Subject:
    Teacher T001

Permission:
    homework.create

Resource:
    Section 1A
    Mathematics

Attributes:
    is_class_teacher = true
    is_subject_teacher = true

Casbin:
    ALLOW
```

and:

``` text
Subject:
    Teacher T001

Permission:
    homework.create

Resource:
    Section 5A
    Mathematics

Attributes:
    is_class_teacher = false
    is_subject_teacher = false

Casbin:
    DENY
```

without any Teacher, Homework, Academic, or Student business
implementation being embedded in the AuthZ Kernel.

------------------------------------------------------------------------

# 36. Final Architectural Outcome

The target separation is:

``` text
Authentication
    ↓
Who is the user?

TenantContext
    ↓
Generic identity + tenant/institution context

Business Module
    ↓
What resource is being accessed?

Attribute Provider
    ↓
What business facts are true?

Casbin
    ↓
Given identity + permission + scope + attributes,
is access allowed?

PostgreSQL RLS
    ↓
Can the database physically expose/write the row?
```

This preserves the project's Platform-First and Kernel-first
architecture while giving C-04 the ABAC capability originally intended
by the platform specification.

------------------------------------------------------------------------

## References within the project

The implementation should remain aligned with:

-   `01-prd.md` --- Product and phased requirements
-   `03-architecture.md` --- Overall architecture
-   `06-auth-spec.md` --- Authentication and authorization
-   `07-multi-tenant-spec.md` --- Tenant/context isolation
-   `18-domain-driven-design.md` --- Bounded contexts and dependency
    direction
-   C-04 Authorization specification
-   Existing AuthZ implementation and migration history

This PRD intentionally defines the **AuthZ Kernel enhancement only**.
Teacher, Student, Parent, Academic, Homework, Attendance, and other
business-module authorization providers should be specified after the
Kernel contract is finalized.
