## Why

The platform lacks a centralized person-to-person relationship model. Business modules (Student, Parent, Fees, Communication, Transport, Attendance) each create independent parent/guardian/contact mappings, causing duplicated data, conflicting definitions, poor historical support, and difficulty representing complex families.

C-06 provides one authoritative relationship framework that all modules must consume instead of creating parallel relationship models.

## What Changes

### New Entities

- **RelationshipType** — Data-driven, platform-managed classification of relationships (Mother, Child, Father, Guardian, Sibling, etc.)
- **ContactRole** — Responsibilities attached to relationships (PrimaryGuardian, FinancialResponsible, EmergencyContact, PickupAuthorized)
- **Relationship** — Connects exactly two Persons with temporal validity (valid_from, valid_to)
- **ContactRoleAssignment** — Attaches a ContactRole to a Relationship with independent temporal validity
- **relationship_type_contact_role** — Compatibility matrix (which roles are valid for which relationship types)

### Key Behaviors

- Relationships are directional with derived inverse perspective
- Symmetric relationships (Sibling) use normalized Person IDs
- Temporal overlap prevention for same Person pair
- Role validity contained within Relationship validity
- RelationshipType changes validate existing role compatibility
- Historical data preserved (no hard delete)

### Seeded Data

- 11 RelationshipTypes with inverse pairs (Mother/Child, Father/Child, Guardian/Child, Sibling, Grandparent/Grandchild, Foster Parent/Child, Step Parent/Child)
- 5 ContactRoles (PrimaryGuardian, Guardian, FinancialResponsible, EmergencyContact, PickupAuthorized)
- Compatibility matrix defining which roles are valid for which relationship types

## Capabilities

### New Capabilities

- `relationship-management`: Centralized person-to-person relationship model with typed, temporal relationships and relationship-specific responsibilities

### Modified Capabilities

None — this is a new capability.

## Impact

### Affected Code

- New module: `backend/kernel/relationship/`
- Models, repos, services, routes, DTOs, tests

### Affected APIs

- 11 new API endpoints for relationship management

### Affected Dependencies

- C-02 (Person) — References `person.id` for relationship endpoints
- C-04 (Authorization) — 11 new permissions
- C-11 (Audit) — AuditEmitter integration for mutation events

### Migration Strategy

Greenfield implementation — no production data to preserve. Alembic migration creates tables and seeds default data.
