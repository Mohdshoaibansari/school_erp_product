# PRD — AuthZ Kernel ABAC Enhancement

> **Capability:** C-04 Authorization / AuthZ Kernel
> **Capability layer / phase:** Kernel · Enhancement · Phase 1 (ABAC contract + Casbin integration)
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-08-24
> **Decisional source of truth:** `openspec/changes/add-c04-authz-abac-enhancement/proposal.md`
> **Companion docs:** `docs/prd/c-04-authorization-consolidation.md` (consolidation PRD), `docs/prd/c-04-authorization.md` (original C-04 PRD), `docs/architecture/adr-c04-authorization-implementation.md` (C-04 ADR)
> **Scope note:** This is a **product** requirements document. It extends the AuthZ Kernel from generic RBAC/scope checks to contextual RBAC+ABAC by introducing a Kernel-owned `AuthorizationAttributeProvider` contract. Business-module implementation (Teacher, Student, Parent providers) is explicitly out of scope. Decisions are referenced by section number from the source proposal rather than re-specified here.

---

## 1. Problem

The School ERP's C-04 Authorization capability currently evaluates **role + permission + scope** via Casbin. This answers questions such as:

- Does this user have `homework.create` permission?
- Does this user have institution scope?
- Does this request belong to the user's client?

It **cannot** answer contextual business questions such as:

- Is this teacher assigned to the requested section?
- Is this teacher assigned to the requested subject?
- Is this teacher the homeroom/class teacher?
- Is this student accessing their own attendance?
- Is this parent accessing attendance of their own child?
- Did this teacher create this homework?

These decisions require **business-domain attributes and relationships** — data that lives in business modules (teacher assignments, student enrollments, parent-child relationships), not in the AuthZ Kernel.

The current architecture has no mechanism to incorporate business-domain facts into Casbin evaluation without either (a) hardcoding business logic into the Kernel (destroying modular boundaries) or (b) duplicating business relationships as Casbin policies (creating a stale replica).

**Goal:** Extend the AuthZ Kernel so it can evaluate business-domain authorization attributes alongside roles, permissions, and scopes — while keeping the Kernel business-agnostic and preserving modular-monolith dependency direction.

---

## 2. Goals & Non-goals

### 2.1 In scope — this feature owns

| Concern | Per (proposal §) | Notes |
|---|---|---|
| **Authorization request/decision contract** | §8, §21, §31 Phase 1 | Define `AuthorizationRequest` (subject, resource, action, context, attributes) and `AuthorizationDecision` (allowed, reason, policy_id) as Kernel-owned types. |
| **Attribute provider contract** | §9, §10, §31 Phase 2 | Define `AuthorizationAttributeProvider` — a Kernel-owned interface that business modules implement. Providers receive subject/resource/context and return domain attributes. Registration and resolution semantics included. |
| **Casbin integration with attributes** | §13, §31 Phase 3 | Extend the Casbin adapter/model to consume subject + resource + action + scope + attributes, while preserving current authorization behavior. |
| **Multi-role evaluation** | §14, §31 Phase 4 | Evaluate all effective roles for a user, not just the first. A valid permission from any applicable role may satisfy RBAC, subject to scope and ABAC conditions. |
| **Structured decision and error model** | §21, §31 Phase 5 | Standardize ALLOW/DENY with reason codes and policy IDs. Internal diagnostic information for debugging and audit. |
| **Synthetic-attribute testing** | §31 Phase 6 | Validate the AuthZ engine independently using test providers and fake attributes before any business module integration. |
| **Authorization pipeline standardization** | §22 | Standardize the 12-step pipeline from authentication through RLS. |
| **Observability and audit context** | §28 | Authorization decisions must be traceable with correlation ID, user, client, institution, action, resource, roles, scope, policy, decision, and reason. |

### 2.2 Out of scope — owned by other capabilities or deferred

| Concern | Owned by / Phase | Notes |
|---|---|---|
| **Teacher authorization provider** | Future (Phase 7) | `TeacherAuthorizationAttributeProvider` — evaluates `is_class_teacher`, `is_subject_teacher`, etc. Designed separately after Kernel contract is finalized. |
| **Student authorization provider** | Future (Phase 7) | Evaluates `is_self` and similar student-domain attributes. |
| **Parent authorization provider** | Future (Phase 7) | Evaluates `is_parent_of_resource` and similar relationship attributes. |
| **Homework resource context** | Future (Phase 7) | Business module supplies resource-specific information for homework authorization. |
| **Academic domain attribute providers** | Future (Phase 7) | Section, subject, enrollment attributes. |
| **Attendance domain attribute providers** | Future (Phase 7) | Attendance-specific authorization attributes. |
| **Dynamic ABAC policy table** | Deferred | A `Policy` table for runtime-defined ABAC rules (per C-04 consolidation PRD §2.2). |
| **Permission CRUD API** | Deferred (C-04 Phase 2) | Runtime permission management. |
| **Runtime policy reload** | Deferred (C-04 Phase 2) | App restart required to pick up policy changes. |
| **Configurable roles UI** | Deferred (C-04 Phase 2) | Admin UI for role/permission management. |
| **Fine-grained scopes** | Deferred (C-04 Phase 2) | OrgUnit, Grade, Class scopes require C-05 Academic Structure. |
| **TemporaryRole table** | Deferred (C-04 Phase 2) | Time-bound role assignments. |
| **Kafka / external messaging** | Never | No external event bus for authorization. |
| **Generic rules engine** | Never | No new rules engine inside AuthZ. |

### 2.3 Explicit non-goals

- No Teacher, Student, Parent, Homework, Attendance, or Academic business logic inside the AuthZ Kernel.
- No `teacher_assignment`, `student_enrollment`, or `parent_student_relationship` moved into AuthZ.
- No individual teacher-to-class relationships stored as Casbin policies.
- No replacement of PostgreSQL RLS (remains defense-in-depth).
- No replacement of authentication flow.
- No direct querying of arbitrary business tables by the Kernel.
- No business module depending on another business module's ORM models.
- No redesign of existing module architecture unless required by this enhancement.
- No Kafka or external messaging system introduction.
- No new generic rules engine.

---

## 3. Users / Personas

| Persona | Role | Impact of this feature |
|---|---|---|
| **Teacher** | Institution user | Gains contextual authorization: homework creation restricted to assigned sections/subjects. Currently has permission but no business-context enforcement. |
| **Student** | Institution user | Gains self-only access control: can read own attendance but not others'. Currently relies solely on RLS. |
| **Parent** | Institution user (guardian) | Gains child-scoped access: can read own child's attendance. Relationship modeling deferred to C-06. |
| **Institution Admin** | Institution lead | No direct change. Authorization decisions become more granular and explainable. |
| **Platform Owner** | SaaS operator | No change. Code bypass retained. |
| **Backend Developer** | Builds business modules | Implements `AuthorizationAttributeProvider` for their domain. Clear contract; no need to understand Casbin internals. Must not import other modules' ORM models. |
| **DB Admin** | Manages policies | No change to policy management. ABAC conditions are code-driven through providers, not DB-driven policies. |

---

## 4. User Journeys

### 4.1 Teacher creates homework for assigned section (ALLOW)

**Scenario:** Teacher T001 creates homework for Section 4A, Mathematics.

1. Teacher authenticates → JWT carries `user_id=U001`, `role=Teacher`, `client_id=C001`, `institution_id=I001`.
2. Teacher calls `POST /api/v1/homework` with `section_id=4A`, `subject_id=Mathematics`.
3. Business module builds `ResourceContext` (resource_type=homework, section_id=4A, subject_id=Mathematics, academic_year_id=AY2026).
4. Business module calls `authorization_service.authorize(subject, action="homework.create", resource)`.
5. AuthZ Kernel resolves generic context (roles, scope, tenant).
6. AuthZ Kernel determines required domain attributes and invokes `TeacherAuthorizationAttributeProvider`.
7. Provider evaluates: T001 is assigned to Section 4A + Mathematics for AY2026 → returns `{is_subject_teacher: true}`.
8. Casbin evaluates: Teacher + homework.create + institution scope + `is_subject_teacher=true` → **ALLOW**.
9. Homework is created. RLS enforces tenant isolation at DB level.

### 4.2 Teacher attempts homework for unassigned section (DENY)

**Scenario:** Teacher T001 attempts homework for Section 5A, Mathematics.

1. Same authentication and request flow as §4.1.
2. Provider evaluates: T001 is NOT assigned to Section 5A → returns `{is_subject_teacher: false}`.
3. Casbin evaluates: Teacher + homework.create + institution scope + required ABAC condition fails → **DENY**.
4. `AuthorizationDecision(allowed=False, reason="ATTRIBUTE_CONDITION_FAILED")`.
5. Request returns 403. No homework created.

### 4.3 Student reads own attendance (ALLOW)

**Scenario:** Student S001 reads attendance for `student_id=S001`.

1. Student authenticates → role=Student.
2. Business module builds resource context with `student_id=S001`.
3. Provider evaluates: authenticated student matches resource student → returns `{is_self: true}`.
4. Casbin evaluates: Student + attendance.read + `is_self=true` → **ALLOW**.

### 4.4 Student attempts to read another student's attendance (DENY)

**Scenario:** Student S001 reads attendance for `student_id=S002`.

1. Provider evaluates: authenticated student does NOT match resource student → returns `{is_self: false}`.
2. Casbin evaluates: Student + attendance.read + `is_self=false` → **DENY**.
3. `AuthorizationDecision(allowed=False, reason="NOT_SELF")`.

### 4.5 Parent reads child's attendance (ALLOW)

**Scenario:** Parent P001 reads attendance for student S002 (their child).

1. Parent authenticates → role=Parent.
2. Provider evaluates: P001 is parent of S002 → returns `{is_parent_of_resource: true}`.
3. Casbin evaluates: Parent + attendance.read + `is_parent_of_resource=true` → **ALLOW**.
4. The parent-child relationship itself remains owned by the appropriate business/domain capability (C-06).

### 4.6 Multi-role user (HOD + Teacher)

**Scenario:** A user with both HOD and Teacher roles creates homework.

1. User authenticates → roles=[HOD, Teacher].
2. AuthZ Kernel evaluates all effective roles.
3. A valid permission from any applicable role may satisfy RBAC, subject to scope and ABAC conditions.
4. System does NOT reduce to only the first role.

---

## 5. Acceptance Criteria

### 5.1 Authorization contract

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-1 | `AuthorizationRequest` type exists with subject, resource, action, context, and attributes fields | §8, §31 Phase 1 |
| AC-2 | `AuthorizationDecision` type exists with allowed (bool), reason (string), and policy_id fields | §21, §31 Phase 5 |
| AC-3 | `SubjectContext` carries generic identity/security information: user_id, roles, client_id, institution_id, user_tier, platform_owner status | §8.1 |
| AC-4 | `ResourceContext` carries resource-specific information supplied by the business operation: resource_type, resource_id, client_id, institution_id, plus domain-specific fields | §8.2 |
| AC-5 | `AuthorizationAttributes` carries domain attributes as key-value pairs (e.g., `is_class_teacher`, `is_subject_teacher`, `is_self`, `is_parent_of_resource`, `is_owner`, `is_assigned_to_resource`) | §8.5 |

### 5.2 Attribute provider contract

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-6 | A Kernel-owned `AuthorizationAttributeProvider` interface exists with registration and resolution semantics | §9, §31 Phase 2 |
| AC-7 | Providers receive authorization subject, resource, and context and return only the attributes required for evaluation | §9 |
| AC-8 | Providers do NOT make the final authorization decision — Casbin remains responsible for policy evaluation | §10 |
| AC-9 | The Kernel does NOT import any business ORM models (Teacher, Student, Parent, Homework, etc.) | §6.5, §34 |
| AC-10 | Business modules implement the provider contract; the Kernel defines the interface | §23, §34 |

### 5.3 Casbin integration

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-11 | Casbin evaluates subject + resource + action + scope + attributes together | §13, §31 Phase 3 |
| AC-12 | Existing RBAC and scope behavior remains unchanged (backward compatible) | §29.3 |
| AC-13 | Casbin does NOT directly query business repositories | §13 |
| AC-14 | Casbin does NOT import business ORM models | §13 |

### 5.4 Multi-role evaluation

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-15 | All effective roles for a user are evaluated, not just the first role | §14, §31 Phase 4 |
| AC-16 | A valid permission from any applicable effective role may satisfy RBAC, subject to scope and ABAC conditions | §14 |
| AC-17 | Users with role combinations (e.g., HOD+Teacher, Principal+Teacher) are correctly authorized | §14 |

### 5.5 Decision and error model

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-18 | `AuthorizationDecision` includes structured reason codes | §21, §31 Phase 5 |
| AC-19 | Reason codes include at minimum: `MISSING_PERMISSION`, `INVALID_SCOPE`, `TENANT_ACCESS_DENIED`, `INSTITUTION_ACCESS_DENIED`, `ATTRIBUTE_CONDITION_FAILED`, `NOT_ASSIGNED_TO_RESOURCE`, `NOT_SELF`, `NOT_PARENT_OF_RESOURCE`, `POLICY_DENIED` | §21 |
| AC-20 | Reason codes are safe for internal logs and controlled API responses; sensitive policy internals are not unnecessarily exposed to clients | §21 |

### 5.6 Security requirements

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-21 | **Fail closed**: if required authorization attributes cannot be resolved, the decision is DENY — missing attributes are never interpreted as permission | §26.1 |
| AC-22 | **No client-supplied trust**: the client cannot declare domain attributes (e.g., `is_class_teacher: true`) and have the Kernel trust them; attributes must be derived from trusted server-side sources | §26.2 |
| AC-23 | **No cross-client attribute resolution**: a provider must never resolve business relationships outside the authenticated client boundary | §26.3 |
| AC-24 | **Institution boundary**: where institution scope is required, the authorization context ensures the resource belongs to an institution the subject can access | §26.4 |
| AC-25 | **RLS defense-in-depth**: authorization success does not disable or bypass PostgreSQL RLS | §26.5 |

### 5.7 Performance requirements

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-26 | Authorization checks are lightweight enough for normal API request paths | §27 |
| AC-27 | Providers avoid loading unnecessary relationship collections (request-specific resolution, not full-collection load) | §12, §27 |
| AC-28 | Repeated attribute lookups within a single request are reusable/cached | §27 |
| AC-29 | Implementation supports batch/collection relationship checks where appropriate | §27 |
| AC-30 | No network call between modules in the modular-monolith architecture | §27 |
| AC-31 | No Kafka or external event bus introduced | §27 |

### 5.8 Observability and audit

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-32 | Authorization decisions are traceable with: correlation_id, user_id, client_id, institution_id, action, resource_type, resource_id, roles, scope, policy_id, decision, reason | §28 |
| AC-33 | Domain attribute values are logged carefully to avoid unnecessary sensitive-data exposure | §28 |

### 5.9 Multiple assignments

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-34 | Users with multiple relationships (e.g., teacher assigned to multiple sections and subjects) are correctly supported | §11 |
| AC-35 | Providers evaluate the requested resource against the relationship set — they do NOT assume singular attributes like `teacher.class_id` | §11 |

### 5.10 Scope model

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-36 | Existing generic scopes (platform, tenant/client, institution, org unit, grade/program, class/batch, subject/course, context) are preserved | §15 |
| AC-37 | ABAC complements scope — it does not replace it | §15 |

### 5.11 Policy model

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-38 | The policy system supports conditional rules such as "Teacher may create homework when is_subject_teacher == true" | §16 |
| AC-39 | The policy system remains generic: business modules define which facts are available; the Kernel defines how policies consume them | §16 |

### 5.12 Dependency direction

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-40 | Dependency direction is `Business Module → AuthZ Kernel Contract`, never `AuthZ Kernel → Business Module` | §23 |
| AC-41 | The Kernel defines interfaces/contracts; business modules implement them | §23 |

### 5.13 Subscription interaction

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-42 | The five concerns remain distinct: Subscription (capability available?), Permission (role has capability?), Scope (where can role operate?), ABAC (under what business conditions?), RLS (what DB rows accessible?) | §25 |

### 5.14 Testing

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-43 | Unit tests cover: single role, multiple roles, missing permission, tenant scope, institution scope, successful ABAC, failed ABAC, missing required attribute, multiple assignments, conflicting assignments | §29.1 |
| AC-44 | Security tests verify: Client A → Client B = DENY, Institution A → Institution B = DENY, Teacher assigned to 1A → 1A = ALLOW, Teacher assigned to 1A → 1B = DENY, Student S1 → S1 attendance = ALLOW, Student S1 → S2 attendance = DENY | §29.2 |
| AC-45 | Regression tests confirm existing RBAC and scope behavior is unchanged | §29.3 |

### 5.15 Definition of done

| ID | Criterion | Per (proposal §) |
|----|-----------|------------------|
| AC-46 | A test-only implementation demonstrates: Teacher T001 with `homework.create` + Section 1A + Mathematics + `is_subject_teacher=true` → Casbin ALLOW | §35 |
| AC-47 | A test-only implementation demonstrates: Teacher T001 with `homework.create` + Section 5A + Mathematics + `is_subject_teacher=false` → Casbin DENY | §35 |
| AC-48 | The above demonstrations work without any Teacher, Homework, Academic, or Student business implementation embedded in the AuthZ Kernel | §35 |

---

## 6. Architecture (conceptual — product shape only)

> Implementation detail (Python types, Casbin model configuration, API shapes) belongs in the spec/design phase. This section captures only the product-relevant shape.

### 6.1 Target authorization flow

```
                    HTTP Request
                         │
                         ▼
                Authentication Context
                         │
                         ▼
                   TenantContext
                         │
                         ▼
                   Business Module
                         │
              Build Resource Context
                         │
                         ▼
                   Authorization
                         │
              ┌──────────┴──────────┐
              │                     │
       Generic Context       Domain Attributes
              │                     │
              │              Business Provider
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
                       Casbin
                         │
                   RBAC + ABAC
                         │
                    ALLOW / DENY
                         │
                         ▼
                   Application
                         │
                         ▼
                  PostgreSQL RLS
```

### 6.2 Kernel ownership boundary

The AuthZ Kernel owns:
- Authorization request and decision types
- Policy evaluation (Casbin integration)
- Provider contract (interface definition)
- Scope evaluation
- Error model and reason codes
- Observability and audit context

Business modules own:
- Business relationships (teacher_assignment, student_enrollment, etc.)
- Domain facts (is_class_teacher, is_subject_teacher, is_self, etc.)
- Domain data (teacher, student, parent, homework persistence)
- Attribute provider implementations

### 6.3 Dependency direction

```
Business Module
        │
        ▼
AuthZ Kernel Contract
```

Never:

```
AuthZ Kernel
        │
        ▼
Teacher Module
```

### 6.4 Architectural decomposition

```
                  AUTHZ KERNEL
                       │
        ┌──────────────┴──────────────┐
        │                             │
     Casbin                  Provider Contract
        │                             │
        │                   ┌─────────┴─────────┐
        │                   │         │         │
        │                Teacher   Student   Parent
        │                Provider  Provider  Provider
        │                   │         │         │
        │                   ▼         ▼         ▼
        │                Business Domain Data
        │
        ▼
 ALLOW / DENY
```

### 6.5 Target authorization pipeline

| Step | Concern | Owner |
|------|---------|-------|
| 1 | Authenticate request | Authentication (C-03) |
| 2 | Build TenantContext | Middleware |
| 3 | Identify subject (user_id, roles, client_id, institution_id, user_tier, platform_owner) | Middleware |
| 4 | Identify action | Business module |
| 5 | Identify target resource | Business module |
| 6 | Resolve generic scope/context | AuthZ Kernel |
| 7 | Determine required domain attributes | AuthZ Kernel |
| 8 | Resolve domain attributes | Attribute Provider (business module) |
| 9 | Invoke Casbin | AuthZ Kernel |
| 10 | Return structured decision | AuthZ Kernel |
| 11 | Continue business operation if ALLOW | Business module |
| 12 | Execute persistence under PostgreSQL RLS | Database |

### 6.6 Conceptual API

```python
decision = await authorization_service.authorize(
    subject=subject_context,
    action="homework.create",
    resource=resource_context,
)
```

Internally, the `AuthorizationService`:
1. Resolves generic context
2. Resolves required attributes (via registered providers)
3. Invokes Casbin
4. Returns `AuthorizationDecision`

Business modules do not interact directly with the Casbin enforcer.

---

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Provider performance** — attribute resolution adds a lookup step per authorization check | Latency increase on every authorized API call | Request-specific resolution (§12): providers check only the relevant relationship, not full collections. Per-request caching of repeated lookups (AC-28). No network calls in modular monolith (AC-30). |
| **Missing provider registration** — a business module forgets to register its attribute provider | Fail-closed: missing attributes → DENY (AC-21). Users get 403 unexpectedly. | Clear provider contract documentation. Synthetic-attribute testing (Phase 6) validates the engine independently. |
| **Attribute trust boundary** — a bug allows client-supplied attributes to be trusted | Security breach: client declares `is_class_teacher=true` | Kernel enforces server-side-only attribute resolution (AC-22). Providers are server-side code, not request parameters. Security tests verify this (AC-44). |
| **Cross-client attribute leakage** — a provider resolves relationships across client boundaries | Data leak across tenants | Provider contract enforces client boundary (AC-23). RLS remains as defense-in-depth (AC-25). |
| **Multi-role complexity** — evaluating all roles increases policy surface area | More Casbin policies to evaluate; potential for conflicting ALLOW/DENY across roles | Casbin handles multi-role evaluation. Any valid permission from any role satisfies RBAC (AC-16). Scope and ABAC conditions still apply per-policy. |
| **Casbin model changes** — extending Casbin to consume attributes may require model file changes | Regression risk on existing RBAC behavior | Backward compatibility is an explicit acceptance criterion (AC-12, AC-45). Phase 6 validates with synthetic attributes before business integration. |
| **Over-engineering** — building a generic framework before any business module needs it | Wasted effort if the contract doesn't match real provider needs | Phase 6 uses synthetic/test providers to validate the contract shape. Phase 7 (business integration) is separate and will stress-test the contract. |
| **Observability overhead** — logging every authorization decision with full context | Log volume increase | Log authorization decisions at appropriate level. Sensitive attribute values logged carefully (AC-33). |

---

## 8. Product Decisions

All open questions have been resolved. Decisions recorded below.

| # | Question | Decision |
|---|----------|----------|
| Q1 | **Should the `AuthorizationAttributeProvider` contract support async providers?** | **Yes — async.** AuthorizationService is async. Attribute providers expose async `resolve()`. Providers may perform async DB/repository operations. Casbin evaluation remains synchronous. |
| Q2 | **How are required attributes determined for a given authorization request?** | **Lazy/request-driven resolution.** Policies declare the attributes they require. AuthorizationService determines the required attributes. Resolve only attributes required by the authorization evaluation. Cache resolved attributes for the lifetime of one authorization request. |
| Q3 | **Should the Kernel support multiple providers per resource type?** | **Yes — multiple providers supported.** ProviderRegistry maps required attributes to providers. Multiple providers may contribute attributes to one authorization request. Provider execution must be deterministic. |
| Q4 | **What is the provider lifecycle?** | **Application-scoped, startup registration.** Providers are registered during application startup. Providers should be stateless. Dependencies are injected. Request-specific state must not be stored inside providers. |
| Q5 | **Should reason codes be an enum or free-form strings?** | **Enum.** Use stable machine-readable enum/string codes. Free-form reason strings are not the primary API contract. Optional detailed diagnostic information may exist internally. Sensitive policy/attribute details must not automatically be exposed to clients. |
| Q6 | **How does ABAC interact with the existing `require_permission` decorator?** | **Extend, not replace.** Authorization pipeline: Authentication → Tenant validation → Permission/RBAC → Scope → ABAC. Authorization is restrictive — ABAC cannot grant a permission denied by RBAC. Missing or failed required attributes result in DENY. |
| Q7 | **Should the Kernel provide a "no-op" default provider that returns empty attributes?** | **Implicit yes (fail-closed).** Failure to resolve a required authorization attribute results in DENY. Client-supplied authorization attributes are never trusted. Missing provider → missing attributes → DENY. |

### Additional Decisions (8–11)

| # | Topic | Decision |
|---|-------|----------|
| 8 | **Business boundary** | AuthZ Kernel must never import Teacher, Student, Parent, Homework, Attendance, Academic, or other business ORM models. Business modules implement the attribute-provider contracts. Casbin must never directly query business repositories. Business relationships remain owned by their respective business modules. |
| 9 | **Fail closed** | Failure to resolve a required authorization attribute results in DENY. Client-supplied authorization attributes are never trusted. |
| 10 | **RLS** | AuthZ does not replace PostgreSQL RLS. Successful authorization does not bypass RLS. |
| 11 | **Policy requirements** | Policies declare the attributes they require. AuthorizationService determines the required attributes. ProviderRegistry resolves those attributes. Providers supply facts; Casbin makes the final authorization decision. |

### Batch Authorization

- Design the architecture to support `authorize_many()`.
- Do not implement batch authorization in the first iteration.
- Future batch authorization must avoid N+1 provider/database queries.

---

## 9. Sequencing & Dependencies

| Dependency | Direction | Notes |
|---|---|---|
| **C-04 Authorization Consolidation** | Predecessor — must be complete | The consolidation PRD unifies all policies into C-04's DB-driven system and fixes ABAC wiring. This enhancement builds on that unified foundation. |
| **C-04 Authorization (original)** | Predecessor — already archived | The base C-04 capability (Permission, Role, RoleAssignment, Scope, Policy, TemporaryRole) is already built. |
| **C-05 Academic Structure** | Consumer — provides domain data | Teacher assignments, student enrollments, section/subject data. The ABAC enhancement defines the contract; C-05 data is what providers will query. |
| **C-06 Relationship Management** | Future consumer | Parent-child relationships. The parent attribute provider will use C-06 data. |
| **Student/Employee Domain Split** | Future consumer | Student and employee domain entities. Student/employee attribute providers will reference these. |
| **Business modules (Teacher, Student, Parent, Homework, Attendance)** | Future consumers (Phase 7) | Each implements `AuthorizationAttributeProvider` for their domain. Explicitly out of scope for this PRD. |

### Implementation phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **Phase 1** | Authorization Contract | `AuthorizationRequest`, `AuthorizationDecision`, `SubjectContext`, `ResourceContext`, `AuthorizationAttributes` types — no business module implementation |
| **Phase 2** | Attribute Provider Contract | `AuthorizationAttributeProvider` interface with registration/resolution semantics — no Teacher/Student implementation required |
| **Phase 3** | Casbin Integration | Extend Casbin adapter/model to consume subject + resource + action + scope + attributes while preserving current behavior |
| **Phase 4** | Multiple Role Evaluation | Correctly support `roles[]` evaluation instead of treating only one role as effective |
| **Phase 5** | Decision and Error Model | Standardize ALLOW/DENY with reason codes, policy IDs, and internal diagnostics |
| **Phase 6** | Synthetic-Attribute Testing | Validate the AuthZ engine with test providers/fake attributes before business integration |
| **Phase 7** | Business Module Integration | **Out of scope for this PRD.** Teacher, Student, Parent, Homework, Attendance providers designed separately. |

---

## 10. Success Criteria

| ID | Success Measure | How Verified |
|----|-----------------|--------------|
| SC-1 | The AuthZ Kernel can evaluate domain attributes alongside roles, permissions, and scopes | AC-1 through AC-5; Phase 6 synthetic tests |
| SC-2 | Business modules can contribute authorization facts through a Kernel-owned contract without the Kernel importing business models | AC-6 through AC-10; dependency analysis |
| SC-3 | Casbin evaluates RBAC+ABAC together as a single decision | AC-11 through AC-14; integration tests |
| SC-4 | Multiple roles are correctly evaluated | AC-15 through AC-17; multi-role test scenarios |
| SC-5 | Authorization decisions are explainable with structured reason codes | AC-18 through AC-20; decision logging verification |
| SC-6 | Security invariants hold: fail-closed, no client-supplied trust, no cross-client leakage, institution boundary, RLS defense-in-depth | AC-21 through AC-25; security test suite |
| SC-7 | Performance is acceptable for normal API request paths | AC-26 through AC-31; performance benchmarks |
| SC-8 | A test-only implementation demonstrates ALLOW and DENY for teacher homework scenarios without any business implementation in the Kernel | AC-46 through AC-48; Phase 6 synthetic tests |
| SC-9 | Existing RBAC and scope behavior is unchanged | AC-12, AC-45; regression test suite |
| SC-10 | The Kernel remains business-agnostic — no business ORM models imported | AC-9, AC-14; dependency analysis |

---

> **End of PRD.** This document is the product requirements input to the sdd-stack lifecycle. Per AGENTS.md §2, the source proposal is the decisional input; this PRD derives from it and does not re-specify decisions. Open questions requiring product decisions are listed in §8. Business module implementation (Phase 7) is explicitly out of scope and should be specified after the Kernel contract is finalized.
