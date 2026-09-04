# C-06 — Relationship Management Framework
## Product Requirements Document (PRD)

**Status:** Implementation Ready  
**Capability:** C-06  
**Layer:** Kernel  
**Criticality:** Critical  
**Phase:** Phase 1  
**Scope:** Institution-agnostic

---

## 1. Purpose

C-06 provides the centralized relationship model for relationships between people in the School ERP.

It owns the fact that two `Person` records are related, the type of that relationship, and optional responsibilities attached to that relationship.

Business modules must consume C-06 instead of creating independent parent/guardian/contact relationship models.

Examples include:

- Mother ↔ Child
- Father ↔ Child
- Guardian ↔ Child
- Sibling ↔ Sibling
- Foster Parent ↔ Child
- Grandparent ↔ Child
- Primary Guardian responsibility
- Financial Responsible responsibility
- Emergency Contact responsibility
- Pickup Authorized responsibility

C-06 is a relationship framework, not a Student or Parent module.

---

## 2. Architectural Position

```text
C-02 Identity
    Person
      |
      v
C-06 Relationship Management
    Relationship
      |
      +-- RelationshipType
      |
      +-- ContactRoleAssignment
              |
              +-- ContactRole
      |
      v
Business Modules
    Student
    Parent
    Employee
    Communication
    Fees
    Attendance
    Transport
    Health
    Exams
    Events
```

### Core rule

> C-06 owns relationships between people. Business modules consume those relationships and must not create parallel relationship mappings.

C-06 references `Person`; it does not own Person identity.

---

## 3. Problem Statement

Without a centralized relationship capability, modules tend to create separate mappings such as:

```text
Student.parent_id
Student.guardian_id
Student.emergency_contact_id
Fee.financial_responsible_id
Communication.parent_id
Transport.pickup_person_id
```

This causes duplicated data, conflicting definitions, poor historical support, difficulty representing complex families, and duplicated authorization and recipient-resolution logic.

C-06 provides one authoritative relationship model.

---

## 4. Goals

C-06 must:

1. Model relationships between `Person` records.
2. Support directional and symmetric relationship types.
3. Support inverse relationship types.
4. Prevent duplicate relationships between the same two people.
5. Support configurable RelationshipTypes.
6. Support multiple responsibilities on one relationship.
7. Support independent temporal validity for responsibilities.
8. Preserve historical data.
9. Support future-effective relationships and responsibilities.
10. Provide reliable service/API operations for consuming modules.
11. Respect tenant and institution boundaries.
12. Enforce domain integrity at both service and database levels.

### Non-goals

C-06 does not own:

- Person identity
- User accounts
- Authentication
- Authorization decisions
- Student records
- Parent business profiles
- Employee records
- Enrollment
- Fees
- Communication
- Addresses
- Documents
- Payroll
- Transport workflows

Those belong to other capabilities.

---

# 5. Core Domain Model

## 5.1 Person

`Person` is owned by C-02.

A Person represents a real-world human and may exist without a User account.

Examples:

- Parent without portal access
- Emergency contact without an account
- Child
- Grandparent
- Pickup-authorized person

C-06 must never require a User to establish a relationship.

---

## 5.2 Relationship

A `Relationship` connects exactly two different Persons.

```text
Person A ---- Relationship ---- Person B
                    |
              RelationshipType
```

A Relationship is directional.

Example:

```text
Fatima → Mother → Ahmed
```

Its inverse perspective is derived:

```text
Ahmed → Child → Fatima
```

Only one physical Relationship row exists.

### No canonical RelationshipType

C-06 does not define a canonical direction or canonical RelationshipType.

A valid relationship may be created from either perspective. The supplied type is retained; inverse perspective is derived through the inverse RelationshipType.

---

# 6. RelationshipType

`RelationshipType` defines the semantic classification of a Relationship.

Examples:

```text
Mother
Child
Father
Guardian
Sibling
Grandparent
Foster Parent
Step Parent
```

## 6.1 Data-driven

RelationshipTypes are data-driven, not hard-coded enums.

## 6.2 Platform-managed

RelationshipTypes are platform-managed globally. Institutions consume the platform-defined types.

Institution-specific customization is outside Phase 1.

## 6.3 Immutable definition

The semantic definition of a RelationshipType is immutable after creation:

- `code`
- `name`
- inverse RelationshipType
- `is_symmetric`

Changing the meaning requires creating a new type.

## 6.4 Symmetric types

A type may be symmetric.

Example:

```text
Sibling
```

For a symmetric type:

```text
A → Sibling → B
```

is equivalent to:

```text
B → Sibling → A
```

Only one physical Relationship exists. Person IDs must be deterministically normalized for symmetric relationships.

## 6.5 Non-symmetric types

Every non-symmetric RelationshipType must have an inverse RelationshipType.

Example:

```text
Mother ↔ Child
Father ↔ Child
Guardian ↔ Child
```

Inverse types are created as a pair in one operation.

There is no `RelationshipTypePair` entity.

Each RelationshipType directly references its inverse.

---

# 7. ContactRole

A `ContactRole` represents a responsibility attached to a specific Relationship.

Examples:

- Primary Guardian
- Guardian
- Financial Responsible
- Emergency Contact
- Pickup Authorized

ContactRole is distinct from RelationshipType.

Example:

```text
Fatima → Mother → Ahmed
    + PrimaryGuardian
    + FinancialResponsible
    + EmergencyContact
    + PickupAuthorized
```

## 7.1 Data-driven

ContactRoles are platform-managed entities, not hard-coded enums.

## 7.2 Relationship-specific

A ContactRole is not a global Person property.

For example:

```text
Fatima → Mother → Ahmed
    FinancialResponsible

Fatima → Mother → Sara
    PrimaryGuardian
```

## 7.3 Compatibility

The platform defines which ContactRoles are valid for each RelationshipType.

Compatibility is an explicit allow-list.

If a role is not explicitly allowed, it is denied by default.

---

# 8. ContactRoleAssignment

`ContactRoleAssignment` attaches a ContactRole to a Relationship.

```text
Relationship
    |
    +-- ContactRoleAssignment
            |
            +-- ContactRole
```

Role-specific validity belongs to the assignment.

A Relationship may have zero or more assignments.

Multiple different roles may be effective simultaneously.

There is no cross-role exclusivity.

---

# 9. Relationship Identity and Uniqueness

## 9.1 Self relationship

A Person cannot be related to themselves:

```text
person_a_id != person_b_id
```

## 9.2 Unordered person pair

For physical uniqueness:

```text
(A, B) == (B, A)
```

Therefore the inverse perspective cannot create a second physical Relationship.

## 9.3 Temporal uniqueness

For the same pair of Persons, overlapping Relationship validity periods are prohibited.

At any point in time, a pair may have at most one effective RelationshipType.

Invalid:

```text
Mother
2026-01-01 → 2026-12-31

Guardian
2026-06-01 → NULL
```

If the relationship type genuinely changes, create separate temporal records:

```text
Guardian
2026-01-01 → 2026-06-30

Mother
2026-07-01 → NULL
```

---

# 10. Relationship Temporal Model

Relationships use:

```text
valid_from
valid_to
```

## Rules

- `valid_from` is mandatory.
- `valid_to` is optional.
- `valid_to` is inclusive.
- `valid_to < valid_from` is invalid.
- `valid_from == valid_to` is valid for one calendar day.
- Future-effective relationships are supported.
- Historical relationships are preserved.
- No separate status field is stored.

### Derived status

```text
Future:
today < valid_from

Effective:
valid_from <= today
AND (valid_to IS NULL OR today <= valid_to)

Historical:
valid_to IS NOT NULL
AND today > valid_to
```

---

# 11. Relationship Date Editing

Relationship validity dates are editable subject to all integrity rules.

If a date change would cause an existing ContactRoleAssignment to fall outside the new Relationship validity:

> Reject the Relationship change.

The administrator must explicitly adjust affected ContactRoleAssignments first.

The system must never silently truncate or delete roles.

If a Relationship is extended and all existing roles remain valid, the extension is allowed.

---

# 12. ContactRole Temporal Model

ContactRoleAssignments have their own:

```text
valid_from
valid_to
```

## 12.1 Containment

A role assignment must be completely contained within its parent Relationship.

```text
relationship.valid_from <= role.valid_from
```

and, when the Relationship has an end:

```text
role.valid_to IS NOT NULL
AND role.valid_to <= relationship.valid_to
```

If the Relationship has no end, the role may also have no end.

## 12.2 Independent start

A role may begin after the Relationship begins.

```text
Relationship:
2026-10-01 → NULL

FinancialResponsible:
2026-11-01 → NULL
```

Valid.

## 12.3 Independent end

A role may end before the Relationship ends.

```text
Relationship:
2026-01-01 → NULL

FinancialResponsible:
2026-01-01 → 2026-06-30
```

Valid.

## 12.4 Multiple periods

The same ContactRole may have multiple non-contiguous periods.

Valid:

```text
FinancialResponsible
2026-01-01 → 2026-06-30

FinancialResponsible
2026-09-01 → NULL
```

## 12.5 Overlap

Same `Relationship + ContactRole` periods may not overlap.

Because `valid_to` is inclusive:

```text
2026-01-01 → 2026-06-30
2026-07-01 → NULL
```

is valid.

```text
2026-01-01 → 2026-06-30
2026-06-30 → NULL
```

is invalid.

---

# 13. ContactRole Removal and Reintroduction

Ending a ContactRoleAssignment preserves history.

For a current assignment:

```text
2026-01-01 → NULL
```

ending it requires an explicit `valid_to`.

It must not be hard-deleted.

A role may later be reintroduced as a new non-overlapping validity period.

---

# 14. RelationshipType Changes

An existing Relationship may change its RelationshipType.

The new type must be validated against all existing ContactRoleAssignments.

If any current/historical/future assignment becomes incompatible:

- reject the change
- identify the incompatible assignments
- require explicit reconciliation
- never silently delete roles

The semantic definitions of RelationshipTypes themselves remain immutable.

---

# 15. Institution and Tenant Boundaries

C-06 must respect the platform tenancy model.

Relationships must not be exposed across unauthorized tenant/institution boundaries.

C-06 must use existing tenant/institution context, RLS, and C-04 authorization.

Cross-institution relationships are not implicitly allowed.

If cross-institution linking is introduced later, it requires explicit platform configuration and authorization.

---

# 16. Authorization

C-06 integrates with C-04 and does not implement a parallel authorization system.

C-06 may provide domain facts such as:

- Person participates in Relationship
- RelationshipType
- effective ContactRole
- PrimaryGuardian
- FinancialResponsible
- EmergencyContact
- PickupAuthorized

C-06 supplies facts; C-04/Casbin remains the final policy decision-maker.

---

# 17. Service Layer

Consumers should use services rather than directly manipulating ORM entities.

Recommended responsibilities:

```text
RelationshipService
    create_relationship()
    get_relationship()
    update_relationship()
    end_relationship()
    change_relationship_type()
    list_relationships()
    get_inverse_view()
    resolve_related_persons()

RelationshipTypeService
    create_inverse_pair()
    get_type()
    list_types()
    validate_contact_role()

ContactRoleService
    list_roles()
    list_compatible_roles()

ContactRoleAssignmentService
    add_role()
    update_role_period()
    end_role()
    list_effective_roles()
    list_historical_roles()
```

Exact names may follow existing project conventions.

---

# 18. Create Relationship

Inputs:

```text
person_a_id
person_b_id
relationship_type_id
valid_from
valid_to?
```

Optional initial roles:

```text
contact_role_assignments
```

Validation:

- Persons exist.
- Persons are within allowed scope.
- Persons are different.
- RelationshipType exists.
- Dates are valid.
- No overlapping Relationship exists for the pair.
- Symmetric relationship normalization is applied.
- ContactRoles are compatible.
- Role periods are contained within the Relationship.
- Same-role periods do not overlap.

The operation must be transactional.

---

# 19. Retrieve and Resolve Relationships

The service must support:

- direct Relationship view
- inverse perspective
- effective relationships
- future relationships
- historical relationships
- effective ContactRoles
- historical ContactRoles
- related Person resolution
- filtering by RelationshipType
- filtering by ContactRole

For an effective date `D`:

```text
valid_from <= D
AND (valid_to IS NULL OR D <= valid_to)
```

---

# 20. Emergency Contacts

Emergency Contact is a **ContactRole**, not a RelationshipType.

A non-parent person may hold this role.

Emergency contacts may require priority ordering.

The relationship framework must support priority-ordered emergency contacts without redefining EmergencyContact as a RelationshipType.

---

# 21. Financial Responsibility

Financial Responsible is a ContactRole.

It is not a property of Person, Parent, Student, or RelationshipType.

Example:

```text
Fatima → Mother → Ahmed
    FinancialResponsible

Fatima → Mother → Sara
    [not FinancialResponsible]
```

Fees must resolve financial responsibility through C-06 rather than maintaining a competing relationship mapping.

---

# 22. Parent and Student Integration

C-06 does not create Student or Parent records.

To find Ahmed's parents:

1. Student module identifies Ahmed's Person.
2. C-06 resolves relationships involving Ahmed.
3. C-06 returns related Persons and relationship metadata.
4. Parent module determines whether those Persons have Parent business profiles.
5. C-02 separately determines User/account state.

C-06 must not assume every related Person is:

- a Parent
- a User
- a portal user
- a Parent business profile

---

# 23. Logical Data Model

## relationship_type

```text
id
code
name
inverse_relationship_type_id
is_symmetric
created_at
```

Rules:

- code unique
- semantic fields immutable
- non-symmetric type requires inverse
- inverse relationship must be reciprocal

## contact_role

```text
id
code
name
created_at
```

Rules:

- code unique
- platform managed

## relationship_type_contact_role

```text
relationship_type_id
contact_role_id
```

Constraint:

```text
UNIQUE(relationship_type_id, contact_role_id)
```

## relationship

```text
id
person_a_id
person_b_id
relationship_type_id
valid_from
valid_to
created_at
updated_at
```

Constraints:

```text
person_a_id != person_b_id
valid_from IS NOT NULL
valid_to IS NULL OR valid_to >= valid_from
```

Physical uniqueness must treat `(A,B)` and `(B,A)` as the same pair.

## contact_role_assignment

```text
id
relationship_id
contact_role_id
valid_from
valid_to
created_at
updated_at
```

Constraints:

```text
valid_from IS NOT NULL
valid_to IS NULL OR valid_to >= valid_from
```

Containment and temporal overlap constraints also apply.

---

# 24. Database Integrity

Do not rely solely on API/service validation.

Use PostgreSQL constraints wherever practical:

- CHECK constraints
- foreign keys
- unique indexes
- exclusion constraints
- NOT NULL constraints

Temporal non-overlap should preferably be database-enforced using PostgreSQL range/exclusion mechanisms where practical.

This is particularly important for concurrent writes.

---

# 25. Concurrency

The system must prevent concurrent requests from creating invalid duplicates.

Example:

```text
Request A:
A → Mother → B

Request B:
B → Child → A
```

Both must not independently succeed for overlapping validity periods.

Database-level integrity must protect against race conditions.

Database errors should be translated into stable domain errors.

---

# 26. Error Categories

Recommended domain errors:

```text
PERSON_NOT_FOUND
PERSON_SCOPE_VIOLATION
SELF_RELATIONSHIP_NOT_ALLOWED
RELATIONSHIP_TYPE_NOT_FOUND
INVALID_RELATIONSHIP_TYPE
INVERSE_RELATIONSHIP_TYPE_INVALID
RELATIONSHIP_DATE_INVALID
RELATIONSHIP_OVERLAP
RELATIONSHIP_NOT_FOUND
CONTACT_ROLE_NOT_FOUND
CONTACT_ROLE_NOT_ALLOWED
CONTACT_ROLE_DATE_INVALID
CONTACT_ROLE_OUTSIDE_RELATIONSHIP
CONTACT_ROLE_OVERLAP
RELATIONSHIP_TYPE_CHANGE_REQUIRES_RECONCILIATION
```

Use existing project error conventions.

---

# 27. Auditability

Relationship mutations must integrate with the platform audit capability.

At minimum, preserve events for:

- Relationship creation
- RelationshipType change
- Relationship validity changes
- ContactRole addition
- ContactRole validity changes
- ContactRole ending

Historical records must not be destroyed merely because they become ineffective.

Do not introduce a separate C-06 audit framework if a platform-wide audit capability exists.

---

# 28. Security Requirements

C-06 must:

1. Enforce tenant/institution boundaries.
2. Respect RLS.
3. Respect C-04 authorization.
4. Avoid trusting caller-supplied tenant context where secure server context exists.
5. Validate both Person endpoints.
6. Prevent unauthorized enumeration.
7. Avoid unnecessary sensitive data in logs.

---

# 29. Performance

Common access patterns include:

- Person → all relationships
- Person → effective relationships
- Person → related Persons
- Person → RelationshipType
- Person → effective ContactRoles
- Relationship → ContactRoles

Recommended initial indexes:

```text
relationship(person_a_id)
relationship(person_b_id)
relationship(relationship_type_id)
relationship(valid_from)
relationship(valid_to)

contact_role_assignment(relationship_id)
contact_role_assignment(contact_role_id)
contact_role_assignment(valid_from)
contact_role_assignment(valid_to)
```

Composite indexes should be added based on actual query plans.

---

# 30. API Design

Conceptual API surface:

```text
GET    /relationship-types
GET    /contact-roles
GET    /people/{person_id}/relationships
POST   /people/{person_id}/relationships
GET    /relationships/{relationship_id}
PATCH  /relationships/{relationship_id}
POST   /relationships/{relationship_id}/contact-roles
PATCH  /contact-role-assignments/{assignment_id}
```

Exact route naming must follow existing API conventions.

APIs requiring historical/future resolution should support an explicit effective date.

---

# 31. Transaction Boundaries

Mutations must be transactional.

### Inverse RelationshipType pair

```text
BEGIN
    create type A
    create type B
    link A.inverse = B
    link B.inverse = A
COMMIT
```

Any failure rolls back the complete pair.

### Relationship with initial roles

```text
BEGIN
    create Relationship
    validate roles
    create ContactRoleAssignments
COMMIT
```

Any failure rolls back the complete operation.

---

# 32. Example Scenarios

### Mother with multiple responsibilities

```text
Fatima → Mother → Ahmed

PrimaryGuardian
FinancialResponsible
EmergencyContact
PickupAuthorized
```

All may be effective simultaneously.

### Parent without login

```text
Person: Fatima
User: none

Fatima → Mother → Ahmed
```

Valid.

### Non-parent emergency contact

```text
Person: Ali

Ali → Other/Guardian → Ahmed
EmergencyContact
```

Ali does not need a Parent profile or User account.

### Responsibility changes

```text
FinancialResponsible
2026-01-01 → 2026-06-30

FinancialResponsible
2026-09-01 → NULL
```

Valid.

### Relationship type changes

```text
Guardian
2026-01-01 → 2026-06-30

Mother
2026-07-01 → NULL
```

Two Relationship records.

### Future relationship

```text
Guardian
2027-04-01 → NULL
```

Future before April 1, 2027.

### Future responsibility

```text
Relationship:
Mother
2026-10-01 → NULL

FinancialResponsible:
2026-11-01 → NULL
```

Valid.

### Invalid role containment

```text
Relationship:
2026-01-01 → 2026-12-31

Role:
2026-03-01 → 2027-01-31
```

Rejected.

### Invalid relationship overlap

```text
Mother
2026-01-01 → 2026-12-31

Guardian
2026-06-01 → NULL
```

Rejected.

### Symmetric sibling

```text
A → Sibling → B
```

and:

```text
B → Sibling → A
```

resolve to the same physical Relationship.

---

# 33. Acceptance Criteria

## Relationship

- [ ] Connects exactly two Persons.
- [ ] Does not require a User.
- [ ] Rejects self-relationships.
- [ ] Requires RelationshipType.
- [ ] Prevents duplicate unordered Person pairs for overlapping periods.
- [ ] Supports historical relationships.
- [ ] Supports future relationships.
- [ ] Requires valid_from.
- [ ] Allows nullable valid_to.
- [ ] Treats valid_to as inclusive.
- [ ] Allows valid_from == valid_to.
- [ ] Derives status from dates.
- [ ] Derives inverse without a second row.

## RelationshipType

- [ ] Data-driven.
- [ ] Platform-managed.
- [ ] Semantic definition immutable.
- [ ] Explicit symmetric flag.
- [ ] Non-symmetric type has inverse.
- [ ] Inverse pair created transactionally.
- [ ] No RelationshipTypePair entity.

## ContactRole

- [ ] Data-driven.
- [ ] Platform-managed.
- [ ] Relationship-specific.
- [ ] Multiple roles can coexist.
- [ ] Compatibility uses explicit allow-list.
- [ ] Unconfigured compatibility is denied.
- [ ] ContactRole is not RelationshipType.

## ContactRoleAssignment

- [ ] Relationship may have zero roles.
- [ ] Role dates are independent.
- [ ] Role start may differ from Relationship start.
- [ ] Role end may differ from Relationship end.
- [ ] Role validity is contained within Relationship validity.
- [ ] Same role may have multiple non-contiguous periods.
- [ ] Same-role periods cannot overlap.
- [ ] Historical assignments are preserved.
- [ ] Ending a role does not hard-delete history.

## RelationshipType changes

- [ ] Existing RelationshipType may be changed.
- [ ] New compatibility is validated.
- [ ] Incompatible assignments cause rejection.
- [ ] Incompatible roles are never silently deleted.

## Relationship date changes

- [ ] Changes that invalidate child roles are rejected.
- [ ] Valid extensions are allowed.
- [ ] No automatic role truncation.
- [ ] No automatic role deletion.

## Security

- [ ] Tenant/institution boundaries enforced.
- [ ] RLS respected.
- [ ] C-04 authorization used.
- [ ] No parallel authorization engine.

## Concurrency

- [ ] Concurrent duplicate relationships cannot bypass uniqueness.
- [ ] Temporal overlap is database-protected where practical.
- [ ] Integrity errors map to stable domain errors.

---

# 34. Testing Strategy

## Unit tests

Test:

- valid Relationship creation
- missing Person
- self Relationship
- duplicate pair
- overlapping Relationship
- future Relationship
- historical Relationship
- same-day validity
- invalid dates
- inverse resolution
- symmetric normalization
- RelationshipType compatibility
- ContactRole compatibility
- multiple simultaneous roles
- role containment
- role overlap
- non-contiguous role periods
- RelationshipType changes
- parent-date-change validation

## Integration tests

Test:

- API/service/database interaction
- RLS
- authorization
- tenant isolation
- transaction rollback
- inverse pair creation
- relationship plus initial roles

## Database/concurrency tests

Test concurrent attempts to create:

```text
A → Mother → B
B → Child → A
```

and overlapping relationships.

The database must prevent invalid states.

---

# 35. Implementation Guidance

Recommended backend boundary:

```text
app/
├── kernel/
│   ├── identity/
│   ├── authorization/
│   └── relationships/
│       ├── models/
│       ├── repositories/
│       ├── services/
│       ├── schemas/
│       ├── routes/
│       ├── exceptions/
│       └── tests/
└── modules/
    ├── student/
    ├── parent/
    ├── employee/
    ├── attendance/
    └── ...
```

Align with the existing backend architecture.

Technology:

- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL / Supabase
- Existing RLS strategy
- Existing C-04 authorization
- Existing error and audit architecture

Do not introduce another ORM or authorization engine.

---

# 36. Migration Strategy

If legacy relationship mappings exist:

1. Identify existing parent/guardian/contact mappings.
2. Resolve endpoints to Person records.
3. Map legacy semantics to RelationshipTypes.
4. Map responsibilities to ContactRoles.
5. Preserve known historical dates.
6. Deduplicate equivalent relationships.
7. Detect conflicting periods.
8. Flag ambiguous records for reconciliation.
9. Preserve legacy information where possible.
10. Make migration explicit and auditable.

Do not silently discard relationship data.

---

# 37. Business Module Integration

### Student

Uses C-06 to resolve parents and guardians.

### Parent

Uses C-06 to discover related children.

### Fees

Uses FinancialResponsible.

### Communication

Uses C-06 for relationship-based recipient resolution.

### Transport

Uses PickupAuthorized.

### Attendance

Uses C-06 for parent/guardian notification resolution.

### Health

Uses C-06 for authorized guardian/contact resolution.

No consumer module may maintain a duplicate relationship table for the same business fact.

---

# 38. Observability

Recommended structured events:

```text
relationship.created
relationship.updated
relationship.ended
relationship.type_changed
relationship.contact_role_added
relationship.contact_role_updated
relationship.contact_role_ended
relationship.validation_failed
```

Do not log unnecessary personal data.

Recommended metrics:

- relationship creation failures
- temporal conflict failures
- authorization denials
- role compatibility failures
- relationship resolution latency

---

# 39. Future Extensions

Outside Phase 1:

- institution-specific RelationshipType customization
- institution-specific ContactRole customization
- cross-institution relationship linking
- advanced family graph queries
- household entities
- custody/legal-document modeling
- family groups
- relationship evidence documents
- approval workflows
- automated relationship inference
- AI-assisted relationship extraction

The Phase 1 model must not prevent these extensions.

---

# 40. Non-Negotiable Invariants

```text
1. Relationship endpoints are Persons, never Users.

2. A Relationship connects exactly two different Persons.

3. One physical Relationship represents both perspectives.

4. Inverse relationships are derived.

5. RelationshipType is mandatory.

6. RelationshipTypes are data-driven and platform-managed.

7. Symmetry is explicit.

8. Every non-symmetric RelationshipType has an inverse.

9. No RelationshipTypePair entity exists.

10. One Person pair cannot have overlapping Relationship periods.

11. Relationship history is preserved.

12. Future Relationships are supported.

13. Relationship validity is date-derived.

14. ContactRoles are separate from RelationshipTypes.

15. A Relationship may have zero or many ContactRoles.

16. Multiple different ContactRoles may be simultaneously effective.

17. ContactRole compatibility is explicit allow-list based.

18. ContactRoleAssignments have independent validity.

19. ContactRole validity must be contained within Relationship validity.

20. The same ContactRole may have multiple non-overlapping periods.

21. ContactRole periods may not overlap.

22. Historical ContactRoleAssignments are preserved.

23. Parent validity changes may not silently mutate child assignments.

24. RelationshipType changes require ContactRole reconciliation when needed.

25. Tenant/institution boundaries must always be respected.

26. C-06 does not own authentication or authorization decisions.

27. Business modules consume C-06 rather than duplicating relationship data.
```

---

# 41. Definition of Done

C-06 is complete only when:

- [ ] Domain model implemented.
- [ ] SQLAlchemy models implemented.
- [ ] Alembic migrations implemented.
- [ ] Database integrity constraints implemented.
- [ ] Temporal overlap protection implemented.
- [ ] RelationshipType inverse/symmetric behavior implemented.
- [ ] ContactRole compatibility implemented.
- [ ] ContactRole temporal behavior implemented.
- [ ] RelationshipType changes validated.
- [ ] Relationship date changes protect child assignments.
- [ ] Service layer implemented.
- [ ] API layer implemented.
- [ ] Authorization integration implemented.
- [ ] RLS/tenant boundaries verified.
- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] Database constraint tests pass.
- [ ] Concurrency tests pass for critical invariants.
- [ ] API documentation complete.
- [ ] Audit integration complete.
- [ ] No consuming business module maintains a duplicate relationship model.
- [ ] Migration/reconciliation strategy documented if legacy data exists.

---

# 42. Final Architectural Decision

C-06 establishes a **person-to-person relationship graph with typed, temporal relationships and relationship-specific responsibilities**.

The model is:

```text
                    RelationshipType
                         |
                         v
Person A -----> Relationship <----- Person B
                         |
                         v
               ContactRoleAssignment
                         |
                         v
                    ContactRole
```

The responsibilities are deliberately separated:

```text
WHO ARE THEY?
    Person

HOW ARE THEY RELATED?
    Relationship
        +
    RelationshipType

WHAT RESPONSIBILITIES EXIST?
    ContactRoleAssignment
        +
    ContactRole
```

C-06 is therefore the **single source of truth for person-to-person relationships across the ERP**.

Business modules must consume this capability rather than independently modeling the same relationship facts.

---

# 43. Implementation Decisions

> **Source:** Grill session 2026-09-03
> **Impact Classification:** `docs/prd/c-06-impact-classification.md`

## 43.1 Tenant Scoping

Relationships use `client_id` for tenant isolation via RLS. No `institution_id` on Relationship tables. Institution context is derived from Person when needed.

## 43.2 Seeded Data

### Default RelationshipTypes

| Code | Name | Inverse | Is Symmetric |
|---|---|---|---|
| `mother` | Mother | `child` | false |
| `child` | Child | `mother` | false |
| `father` | Father | `child` | false |
| `guardian` | Guardian | `child` | false |
| `sibling` | Sibling | `sibling` | true |
| `grandparent` | Grandparent | `grandchild` | false |
| `grandchild` | Grandchild | `grandparent` | false |
| `foster_parent` | Foster Parent | `foster_child` | false |
| `foster_child` | Foster Child | `foster_parent` | false |
| `step_parent` | Step Parent | `step_child` | false |
| `step_child` | Step Child | `step_parent` | false |

### Default ContactRoles

| Code | Name |
|---|---|
| `primary_guardian` | Primary Guardian |
| `guardian` | Guardian |
| `financial_responsible` | Financial Responsible |
| `emergency_contact` | Emergency Contact |
| `pickup_authorized` | Pickup Authorized |

### Default Compatibility Matrix

| RelationshipType | Allowed ContactRoles |
|---|---|
| `mother` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `father` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `guardian` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `grandparent` | guardian, emergency_contact, pickup_authorized |
| `foster_parent` | primary_guardian, guardian, financial_responsible, emergency_contact, pickup_authorized |
| `step_parent` | guardian, emergency_contact, pickup_authorized |
| `sibling` | emergency_contact |
| `child` | (none — inverse perspective) |
| `grandchild` | (none — inverse perspective) |
| `foster_child` | (none — inverse perspective) |
| `step_child` | (none — inverse perspective) |

## 43.3 Symmetric Normalization

For symmetric relationships (e.g., Sibling), Person IDs are normalized:

```text
person_a_id = LEAST(person_a_id, person_b_id)
person_b_id = GREATEST(person_a_id, person_b_id)
```

A `normalized_pair` column stores the concatenation for unique constraint enforcement.

## 43.4 Temporal Overlap Enforcement

Temporal overlap validation is enforced at the **application level**, not PostgreSQL exclusion constraints. The service validates no overlapping Relationship periods exist for the same Person pair before creation/update.

## 43.5 Status Computation

Relationship status is computed dynamically from dates (no `status` column):

```text
Future:      today < valid_from
Effective:   valid_from <= today AND (valid_to IS NULL OR today <= valid_to)
Historical:  valid_to IS NOT NULL AND today > valid_to
```

## 43.6 Containment Enforcement

ContactRoleAssignment validity must be contained within parent Relationship validity. This is enforced at the **service level**:

- `role.valid_from >= relationship.valid_from`
- If `relationship.valid_to` is not null, then `role.valid_to` must be not null and `role.valid_to <= relationship.valid_to`

## 43.7 RelationshipType Change Validation

When changing a RelationshipType on an existing Relationship:
1. Get all ContactRoleAssignments for the Relationship
2. Check each role against the new RelationshipType's compatibility list
3. If any role is incompatible, reject the change and list the incompatible roles
4. Never silently delete roles

## 43.8 Inverse RelationshipType Generation

The API accepts a single RelationshipType for creation. The service **auto-generates** the inverse type in the same transaction. No separate API call needed.

## 43.9 Module Boundary

The module is located at `backend/kernel/relationship/` (singular, matching existing conventions).

## 43.10 Audit Integration

C-06 integrates with the existing `AuditEmitter` interface. Events emitted:

- `relationship.created`
- `relationship.updated`
- `relationship.ended`
- `relationship.type_changed`
- `relationship.contact_role_added`
- `relationship.contact_role_updated`
- `relationship.contact_role_ended`

## 43.11 Deferred Items

The following are deferred to future enhancements:

- Priority ordering for EmergencyContact
- Institution-specific RelationshipType customization
- Institution-specific ContactRole customization
- Cross-institution relationship linking
- Advanced family graph queries
- Household entities
- Custody/legal-document modeling
- Approval workflows
