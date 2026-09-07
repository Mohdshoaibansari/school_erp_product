# C-13 Address Management — Product Requirements Document

**Status:** Requirements baseline complete  
**Phase:** Phase 1 — Address Management  
**Product:** Multi-Tenant School ERP  
**Module:** C-13  
**Date:** 2026-09-05

## 1. Purpose

C-13 provides a centralized, reusable Address Management capability for the School ERP.

It supports addresses belonging to ERP entities such as Persons and Institutions, and future entities such as Students and Employees, while keeping entity lifecycle and business ownership with the consuming domains.

C-13 is a kernel/platform capability. It owns address data, address assignments, address types, postal reference data, validation, temporal rules, and integrity. It does not own Person, Student, Employee, or Institution lifecycle.

## 2. Phase 1 Scope

### Included

- Address management
- Address-to-entity assignment
- Address types
- AddressType ↔ EntityType compatibility
- Temporal address assignments
- Address history
- Address correction
- Address deletion
- Country, State, City reference data
- Geographic hierarchy validation
- Tenant/institution scope enforcement
- C-04 authorization integration
- Application/database integrity

### Explicitly Deferred

- Latitude/longitude
- GPS
- Geocoding/reverse geocoding
- Maps
- Distance calculations
- Geographic zones
- Route/location optimization
- Physical `Location` entity
- Pickup/drop-point management
- Geographic intelligence

C-13 Phase 1 is an Address capability, not a Location/geospatial capability.

## 3. Architectural Principles

### 3.1 Entity-owned Address

An Address belongs to exactly one ERP entity. Two entities with identical postal information have separate Address records. Address is not a globally shared physical-location object.

### 3.2 Generic internal capability

C-13 uses a generic polymorphic association so multiple ERP entity types can consume the capability.

Conceptually:

```text
Entity
  |
  | AddressAssignment
  |
Address
```

The polymorphic mechanism must never become a security or tenant-isolation bypass.

### 3.3 Domain ownership

C-13 does not own:

- Person lifecycle
- Institution lifecycle
- Student lifecycle
- Employee lifecycle

The owning domain remains authoritative for the target entity.

### 3.4 Scope

C-13 does not duplicate tenant/institution ownership on Address or AddressAssignment. Scope is derived from the target entity.

### 3.5 Authorization

C-04 remains the sole authorization decision-maker. C-13 may resolve entity facts and scope, but must not implement an independent authorization engine.

C-13 must integrate with the existing FastAPI authentication middleware and C-04/Casbin authorization flow.

## 4. Core Domain Model

Conceptually:

```text
EntityType
    |
    | AddressType compatibility
    v
AddressType

Entity
    |
    | AddressAssignment
    v
Address
```

AddressAssignment conceptually contains:

```text
entity_type
entity_id
address_id
address_type_id
valid_from
valid_to
```

Address contains:

```text
address_line_1
address_line_2
landmark
locality
postal_code
city_id
state_id
country_id
```

## 5. EntityType

EntityType is a controlled registry of entity types that may participate in C-13.

### Ownership and registration

EntityTypes are module-owned and registered through database migration/seed mechanisms.

Examples:

```text
C-01 Institution -> INSTITUTION
C-02 Identity    -> PERSON
Future Employee  -> EMPLOYEE
```

Rules:

- Registration is deterministic and idempotent.
- Application startup must not create EntityTypes.
- Platform administrators cannot create arbitrary EntityTypes.
- The owning module controls registration.

### Identity

Each EntityType has:

- immutable globally unique `code`
- immutable human-readable `name`

Both are immutable after registration.

### Deletion

An EntityType may technically be deleted only if it has never been referenced by an AddressAssignment.

However:

- No runtime/admin deletion API exists.
- Deletion is migration-only.
- Once referenced, it is permanently protected.
- Removing a module must not automatically delete a referenced EntityType.

### Scope invariant

Every addressable entity in this School ERP has tenant/institution scope. C-13 does not support unscoped/platform-level addressable entities.

## 6. AddressType

AddressType defines the semantic purpose of an address.

Examples:

```text
RESIDENTIAL
PERMANENT
CORRESPONDENCE
OFFICE
EMERGENCY
```

### Ownership

AddressTypes are platform-managed, data-driven, and not enums or institution-managed.

### Identity

Each AddressType has:

- immutable globally unique `code`
- unique editable display `name`

Policies and integrations should use `code`, not display name.

### Lifecycle

AddressType has no active/inactive/retired lifecycle. It remains usable subject to current compatibility configuration.

### Deletion

An AddressType may be hard-deleted only if it has never been used by an AddressAssignment.

“Used” means ever referenced, including references that were subsequently hard-deleted.

Thus, once used, an AddressType is permanently protected.

### Compatibility

Compatibility is an explicit platform-managed allow-list.

Rules:

- Unconfigured compatibility = denied.
- Consuming modules cannot independently redefine compatibility.
- Compatibility is current-state configuration only.
- No compatibility versioning or temporal model.
- Removing compatibility is blocked while assignments exist that depend on it.
- Existing assignments must not be silently invalidated by compatibility changes.

## 7. Address Model

### Fields

| Field | Required | Maximum | Notes |
|---|---:|---:|---|
| `address_line_1` | Yes | 500 | Primary address line |
| `address_line_2` | No | 500 | Additional details |
| `locality` | No | 100 | Free text |
| `landmark` | No | 100 | Free text |
| `postal_code` | No | 20 | No country-specific validation in Phase 1 |
| `city_id` | Yes | — | Normalized reference |
| `state_id` | Yes | — | Normalized reference |
| `country_id` | Yes | — | Normalized reference |

### Primary address

There is no generic `is_primary` field. Consumers use explicit AddressType semantics.

### Custom labels

C-13 does not provide a generic custom address label. AddressType provides the semantic meaning.

## 8. Geographic Reference Data

C-13 owns:

```text
Country
  └── State
       └── City
```

### Administration

Geographic data is seed/migration managed only.

There are no runtime CRUD APIs for Country, State, or City. Platform administrators cannot edit them through the application. Corrections/additions require controlled migration/seed changes.

### Codes

Every geographic record has a stable machine-readable code.

- Country code: globally unique, immutable.
- State code: unique within Country, immutable.
- City code: unique within State, immutable.

Names may be changed through migration/seed.

### Deletion

Country/State/City may be hard-deleted through migration only when no dependent Address records exist.

### Hierarchy

The selected City, State, and Country must belong to the same hierarchy.

For example, an Address cannot combine a City belonging to Uttar Pradesh with a State of Maharashtra.

### Locality

Locality is free text, not a normalized entity.

## 9. AddressAssignment

AddressAssignment associates an entity with an Address, AddressType, and validity period.

### Multiple addresses

An entity may have multiple addresses and multiple AddressTypes simultaneously.

### Effective uniqueness

An entity may have only one effective AddressAssignment for a given AddressType at any point in time.

### AddressType immutability

AddressType cannot be changed on an existing AddressAssignment. A type change requires ending/removing the old assignment as appropriate and creating a new assignment.

### Validity

- `valid_from` is mandatory.
- `valid_to` is optional.
- `valid_to` is inclusive.
- `valid_to < valid_from` is invalid.
- `valid_from == valid_to` is valid.
- Future-effective assignments are supported.
- Historical assignments are supported.
- No overlapping periods for the same entity + AddressType.
- Only one effective assignment for a given entity + AddressType.

Conceptual states:

```text
Future:
today < valid_from

Effective:
valid_from <= today
and
(valid_to IS NULL OR today <= valid_to)

Historical:
valid_to IS NOT NULL
and today > valid_to
```

### Date editing

Validity dates may be edited even while an assignment is Effective, subject to all temporal invariants.

## 10. Address Change Semantics

### Business change

When the entity actually moves:

```text
end old assignment
create new Address
create new assignment
```

This is one atomic operation.

The old address remains historically meaningful.

An Address record is never reused. If an entity later returns to the same postal address, a new Address record is created.

### Data correction

If an Effective Address was entered incorrectly, a controlled correction operation may mutate the Address in place.

Example:

```text
Banglore -> Bangalore
```

Correction:

- has a separate authorization permission
- is audited
- records before/after values where supported by the audit framework
- is transactional
- must not change the historical business meaning

Future address data can be edited normally. Effective address data cannot be modified through ordinary update; correction is a distinct operation.

## 11. Address Deletion

AddressAssignment may be hard-deleted.

Deleting an AddressAssignment automatically deletes its owned Address in the same transaction.

No orphan Address records are allowed.

There is no independent business operation for deleting an Address.

The business authorization concept is:

```text
address.delete
```

representing the atomic deletion of assignment plus owned Address.

## 12. Input Validation and Normalization

Application/API validation must enforce field-length limits and reject over-length input. Input must never be silently truncated. Database constraints provide a second protection layer.

### Whitespace

All address text inputs follow one cross-cutting rule:

> Trim leading and trailing whitespace only.

Applies to:

- address_line_1
- address_line_2
- locality
- landmark
- postal_code

Example:

```text
"  MG Road  " -> "MG Road"
```

Internal whitespace, capitalization, and punctuation are preserved.

### Empty values

For optional fields:

```text
missing -> NULL
null    -> NULL
"   "   -> NULL
```

For required fields:

```text
missing -> validation error
null    -> validation error
"   "   -> validation error
```

No empty-string/NULL dual representation for absent optional values.

## 13. Multi-Tenancy and Scope

### Scope derivation

C-13 does not store `client_id` or `institution_id` on Address or AddressAssignment merely for ownership.

The target entity is authoritative for scope.

### Natural scope

```text
Institution
  -> Client scoped

Person / Student / Employee
  -> Institution scoped
```

The target entity's natural scope determines the authorization boundary.

### Cross-scope access

C-13 must not hard-code role assumptions such as “Client Director can access all institutions.”

Instead:

1. Resolve the target entity.
2. Resolve authoritative scope facts.
3. Build/augment authorization context.
4. Let C-04/Casbin make the final decision.
5. Execute only when authorized.

## 14. Authorization

Authentication is handled by the existing FastAPI middleware. C-13 must not duplicate token validation.

C-04/Casbin remains the sole policy decision-maker.

C-13 must integrate with the existing:

```text
SubjectContext
ResourceContext
RBAC
ABAC
ProviderRegistry
Casbin
```

Business/entity providers supply facts; they do not make authorization decisions.

At minimum, authorization concepts equivalent to:

```text
address.create
address.update
address.delete
address.correct
```

are required.

`address.correct` is separate because it permits controlled modification of historically relevant data.

Exact resource/action mapping is deferred to implementation design.

## 15. Transactions

The following operations must be transactional:

### Create

```text
Address
+
AddressAssignment
```

### Replace

```text
end old assignment
+
create new Address
+
create new assignment
```

### Delete

```text
delete AddressAssignment
+
delete owned Address
```

### Correct

Address correction and its audit information must be atomic.

## 16. Integrity Requirements

At minimum:

- Address belongs to exactly one entity.
- Address cannot be assigned to multiple entities.
- EntityType must be registered.
- AddressType must exist.
- AddressType/EntityType compatibility must be explicitly allowed.
- City/State/Country hierarchy must be valid.
- `valid_from <= valid_to` when `valid_to` exists.
- Assignment periods for the same entity + AddressType cannot overlap.
- At most one effective assignment exists for entity + AddressType.
- Address deletion cannot leave an orphan Address.
- Target entity scope is authoritative.
- Polymorphic association cannot bypass authorization or tenant isolation.

## 17. Audit and History

Normal address changes preserve historical assignment periods.

Hard deletion is an explicit destructive administrative operation and should integrate with the ERP's general audit framework.

Effective-address correction requires dedicated authorization and auditability.

Audit should capture, where supported:

```text
who
when
what changed
before value
after value
```

Exact shared audit implementation is deferred to implementation design.

## 18. Module Boundaries

### C-13 owns

- Address
- AddressAssignment
- AddressType
- AddressType compatibility
- C-13 EntityType integration
- Country
- State
- City
- Address validation
- Temporal address rules
- Correction semantics
- Deletion semantics
- Address ownership/integrity
- Address application/service capability

### C-13 does not own

**C-01**
- Client
- Institution
- OrgUnit
- Institution lifecycle

**C-02**
- User
- Person
- Identity lifecycle
- Authentication

**Future Student module**
- Student lifecycle
- Enrollment
- Academic student semantics

**Future Employee module**
- Employee lifecycle
- Employment
- HR/payroll

## 19. API Design — Deferred

The final HTTP API structure is intentionally deferred to the implementation grill-me session with the coding agent.

Possible approaches include:

```text
Generic:
POST /addresses/assignments
```

or entity-specific APIs such as:

```text
/persons/{person_id}/addresses
/institutions/{institution_id}/addresses
/students/{student_id}/addresses
/employees/{employee_id}/addresses
```

This PRD does not lock the final route shape or route ownership.

Regardless of the eventual API choice, implementation must preserve:

- generic C-13 domain/service capability
- existing FastAPI authentication middleware
- centralized C-04/Casbin authorization
- tenant/institution isolation
- all C-13 business invariants

The API decision must not cause duplication of C-13 business rules.

## 20. Non-Functional Requirements

The implementation should provide:

- strong tenant isolation
- database-level referential integrity
- application-level validation
- transactional consistency
- idempotent reference-data seeds/migrations
- no silent truncation
- no orphan Address records
- predictable temporal behavior
- clear validation errors
- testable service boundaries
- compatibility with existing FastAPI + C-04/Casbin architecture
- compatibility with PostgreSQL/Supabase RLS strategy

## 21. Testing Requirements

### Address validation

- required fields
- maximum lengths
- over-length rejection
- whitespace trimming
- whitespace-only optional values
- whitespace-only required values
- NULL normalization

### Geographic integrity

- valid hierarchy
- invalid City/State
- invalid State/Country
- missing required geography
- code uniqueness/scoping

### AddressType

- valid type
- invalid type
- allowed compatibility
- denied compatibility
- deletion protection after use
- compatibility removal restrictions

### EntityType

- registered type
- unregistered type
- immutable code/name
- migration-only deletion
- deletion protection after use

### Temporal behavior

- future assignment
- effective assignment
- historical assignment
- same-day assignment
- invalid date range
- overlapping periods
- adjacent periods
- one-effective-address rule
- editing effective dates

### Replacement

- old assignment ends correctly
- new Address created
- new assignment created
- rollback on failure

### Deletion

- assignment deleted
- owned Address deleted
- no orphan
- authorization failure

### Correction

- authorized correction
- unauthorized correction
- before/after audit
- effective address correction
- rollback on failure

### Multi-tenancy

- same-institution access
- cross-institution denial where policy denies
- cross-client denial where policy denies
- valid cross-scope access where policy permits
- polymorphic entity cannot bypass scope

### Authorization

- authentication middleware integration
- Casbin allow/deny
- RBAC
- ABAC
- resource scope facts
- correction permission
- delete permission

## 22. Deferred Implementation Decisions

These are intentionally left to the coding-agent implementation grill-me session:

1. Exact HTTP API structure and route ownership.
2. Endpoint naming.
3. Request/response schemas.
4. Pagination/filtering conventions.
5. SQLAlchemy model/relationship implementation.
6. Exact table and column naming.
7. Exact PostgreSQL constraint/index implementation.
8. Exact RLS implementation.
9. Exact C-04 resource/action policy mapping.
10. Audit framework integration.
11. Repository/service class structure.
12. Error-code taxonomy.
13. Migration organization.
14. Geographic seed dataset implementation.
15. Concurrency/locking implementation.
16. API-specific idempotency behavior.

These implementation decisions must remain consistent with the locked functional requirements.

## 23. Locked Decision Summary

| # | Locked requirement |
|---:|---|
| 1 | Address is entity-owned, not globally shared |
| 2 | Generic polymorphic AddressAssignment |
| 3 | Multiple addresses per entity |
| 4 | AddressType is platform-managed/data-driven |
| 5 | AddressType compatibility is explicit allow-list |
| 6 | Country/State/City are normalized references |
| 7 | C-13 owns postal geographic reference data |
| 8 | Geographic hierarchy is strictly enforced |
| 9 | Locality is free text |
| 10 | One effective Address per AddressType |
| 11 | Validity belongs to AddressAssignment |
| 12 | `valid_from` mandatory |
| 13 | `valid_to` inclusive |
| 14 | Future assignments supported |
| 15 | Historical assignments preserved |
| 16 | Address belongs to exactly one entity |
| 17 | Address changes are atomic |
| 18 | Address records cannot be reused |
| 19 | No generic primary address |
| 20 | AddressType immutable on Assignment |
| 21 | AddressAssignment may be hard-deleted |
| 22 | Owned Address is deleted with Assignment |
| 23 | Future Address can be edited |
| 24 | Effective assignment dates can be edited |
| 25 | Controlled correction of Effective Address allowed |
| 26 | Correction has separate authorization |
| 27 | One `address.delete` business permission |
| 28 | Compatibility managed by Platform |
| 29 | Compatibility removal blocked while assignments exist |
| 30 | No AddressType lifecycle |
| 31 | AddressType deletable only if never used |
| 32 | “Ever used” remains permanently protected |
| 33 | Compatibility is current-state only |
| 34 | AddressType code immutable; name editable |
| 35 | EntityType is a controlled registry |
| 36 | EntityTypes are module-owned |
| 37 | EntityTypes registered by migration/seed |
| 38 | EntityType code immutable |
| 39 | EntityType name immutable |
| 40 | EntityType deletable only if never referenced |
| 41 | EntityType deletion migration-only |
| 42 | Geographic data seed/migration managed only |
| 43 | Geographic records may be deleted through migration when unused |
| 44 | Geographic names may change through migration |
| 45 | Geographic records require stable codes |
| 46 | Geographic code uniqueness is hierarchical/scoped |
| 47 | Country, State, City mandatory on Address |
| 48 | Postal code optional |
| 49 | Address line 1 mandatory |
| 50 | Address line 1 max 500 |
| 51 | Address line 2 max 500 |
| 52 | Locality max 100 |
| 53 | Landmark max 100 |
| 54 | Postal code max 20 |
| 55 | Application rejects over-length input |
| 56 | Trim leading/trailing whitespace |
| 57 | Trimming applies to all address text fields |
| 58 | Optional blank values normalize to NULL |
| 59 | Missing/null/whitespace optional values normalize to NULL |
| 60 | Target entity facts + C-04 decision for scope/authorization |
| 61 | Scope is derived, not duplicated on C-13 records |
| 62 | All ERP addressable entities are scoped |
| 63 | Entity natural scope determines boundary |
| 64 | Cross-scope access is dynamically decided by C-04 |
| 65 | API design deferred to implementation grill-me |

## 24. Implementation Decisions

> **Source:** Grill session 2026-09-05
> **Impact Classification:** `docs/prd/c-13-impact-classification.md`

### 24.1 Module Boundary

The module is located at `backend/kernel/address/` (singular, matching existing conventions).

### 24.2 Entity Types

Only two EntityTypes for Phase 1:

| Code | Name | Covers |
|---|---|---|
| `INSTITUTION` | Institution | C-01 Institution |
| `PERSON` | Person | C-02 Person, plus Student/Employee/Staff (all reference Person) |

### 24.3 Polymorphic Association

Use generic `entity_type_id` + `entity_id` columns on AddressAssignment:

```sql
CREATE TABLE address_assignment (
    id UUID PRIMARY KEY,
    entity_type_id UUID NOT NULL REFERENCES entity_type(id),
    entity_id UUID NOT NULL,  -- No FK (polymorphic)
    address_id UUID NOT NULL REFERENCES address(id),
    address_type_id UUID NOT NULL REFERENCES address_type(id),
    valid_from DATE NOT NULL,
    valid_to DATE,
);
```

Entity existence is validated at application level.

### 24.4 Scope Derivation

Address and AddressAssignment do NOT store `client_id` or `institution_id`. Scope is derived from the target entity (Person/Institution) at query time.

### 24.5 Authorization

C-04/Casbin application-level authorization is the primary mechanism. RLS may be added later if required.

### 24.6 Seeded Data

### Default AddressTypes

| Code | Name |
|---|---|
| `RESIDENTIAL` | Residential |
| `PERMANENT` | Permanent |
| `CORRESPONDENCE` | Correspondence |
| `OFFICE` | Office |
| `EMERGENCY` | Emergency |

### Default Compatibility Matrix

| EntityType | Allowed AddressTypes |
|---|---|
| `PERSON` | RESIDENTIAL, PERMANENT, CORRESPONDENCE, EMERGENCY |
| `INSTITUTION` | OFFICE, CORRESPONDENCE, EMERGENCY |

### Geographic Data

Seed India data in migration (all states and major cities). Other countries added later via migration.

### 24.7 Temporal Overlap Enforcement

Application-level validation. Before creating/updating an assignment, query for overlapping periods and reject if found.

### 24.8 Address Deletion

When an AddressAssignment is deleted:
1. Delete the assignment
2. Delete the owned Address (hard delete)
3. No orphan Address records

### 24.9 Address Replacement (Business Change)

Single transactional service method:
1. End old assignment (set valid_to)
2. Create new Address record
3. Create new AddressAssignment

### 24.10 Address Correction

Separate API endpoint with its own permission (`address.correct`). Validates the address is Effective, applies the correction, and emits an audit event with before/after values.

### 24.11 Geographic Code Uniqueness

Composite unique constraints:
- Country: `code` UNIQUE
- State: `(country_id, code)` UNIQUE
- City: `(state_id, code)` UNIQUE

### 24.12 Audit Integration

Integrate with existing `AuditEmitter` interface. Events:
- `address.created`
- `address.updated`
- `address.deleted`
- `address.corrected`
- `address.assignment_created`
- `address.assignment_ended`

### 24.13 API Structure

```
kernel/address/routes/
    addresses.py                # Generic: GET/PATCH/DELETE/correct
    person_addresses.py         # GET/POST /persons/{id}/addresses
    institution_addresses.py    # GET/POST /institutions/{id}/addresses
    reference_data.py           # GET countries/states/cities
    address_types.py            # GET address types + compatibility
```

### 24.14 Module Structure

```
kernel/address/
├── models/
│   ├── address.py
│   ├── address_assignment.py
│   ├── address_type.py
│   ├── entity_type.py
│   ├── country.py
│   ├── state.py
│   └── city.py
├── repos/
│   ├── address_repo.py
│   ├── address_assignment_repo.py
│   ├── address_type_repo.py
│   ├── entity_type_repo.py
│   └── geographic_repo.py
├── services/
│   ├── address_service.py
│   ├── address_assignment_service.py
│   ├── address_type_service.py
│   └── geographic_service.py
├── routes/
│   ├── addresses.py
│   ├── person_addresses.py
│   ├── institution_addresses.py
│   ├── reference_data.py
│   └── address_types.py
├── schemas/
│   └── dtos.py
├── dependencies.py
└── manifest.py
```

## 25. Definition of Done

C-13 Phase 1 requirements are satisfied when implementation:

1. Provides Address and AddressAssignment capability.
2. Supports multiple typed addresses per entity.
3. Enforces temporal assignment rules.
4. Enforces geographic hierarchy.
5. Enforces AddressType/EntityType compatibility.
6. Preserves required historical semantics.
7. Supports controlled address correction.
8. Prevents orphan/reused Address records.
9. Enforces field validation and normalization.
10. Integrates with FastAPI authentication.
11. Integrates with C-04/Casbin authorization.
12. Preserves tenant/institution isolation.
13. Uses application and database integrity protections.
14. Provides comprehensive automated tests.
15. All implementation decisions from Section 24 are applied.
