## Why

The platform lacks a centralized Address Management capability. Business modules (Institution, Person, future Student/Employee) each handle addresses independently, causing duplicated data, inconsistent validation, and no support for temporal address history.

C-13 provides one authoritative Address Management framework that all modules must consume instead of creating parallel address models.

## What Changes

### New Entities

- **EntityType** — Controlled registry of entity types that can have addresses (INSTITUTION, PERSON)
- **AddressType** — Semantic purpose of address (RESIDENTIAL, PERMANENT, CORRESPONDENCE, OFFICE, EMERGENCY)
- **AddressTypeEntityType** — Compatibility matrix (which address types are valid for which entity types)
- **Address** — The actual address data (address lines, locality, city, state, country)
- **AddressAssignment** — Associates an entity with an address, address type, and validity period
- **Country/State/City** — Geographic reference data (hierarchy enforced)

### Key Behaviors

- Generic polymorphic association (entity_type + entity_id)
- Temporal address assignments (valid_from, valid_to)
- One effective address per entity + address type
- Geographic hierarchy validation
- Address replacement (end old, create new - transactional)
- Address correction (separate permission for effective addresses)
- Hard delete of assignment + owned address (no orphans, no reuse)

### Seeded Data

- 2 EntityTypes: INSTITUTION, PERSON
- 5 AddressTypes: RESIDENTIAL, PERMANENT, CORRESPONDENCE, OFFICE, EMERGENCY
- Compatibility matrix
- India geographic data (states + major cities)

## Capabilities

### New Capabilities

- `address-management`: Centralized address management with temporal assignments, geographic reference data, and address type compatibility

### Modified Capabilities

None — this is a new capability.

## Impact

### Affected Code

- New module: `backend/kernel/address/`
- Models, repos, services, routes, DTOs, tests

### Affected APIs

- 14 new API endpoints for address management

### Affected Dependencies

- C-01 (Institution) — References `institution.id` for INSTITUTION type
- C-02 (Person) — References `person.id` for PERSON type
- C-04 (Authorization) — 8 new permissions
- C-11 (Audit) — AuditEmitter integration for mutation events

### Migration Strategy

Greenfield implementation — no production data to preserve. Alembic migration creates tables and seeds default data.
