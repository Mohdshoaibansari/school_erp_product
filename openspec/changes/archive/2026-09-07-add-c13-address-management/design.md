# Design — C-13 Address Management

> **Change:** add-c13-address-management
> **Status:** Draft
> **Date:** 2026-09-05

---

## Context

The platform lacks a centralized Address Management capability. Business modules handle addresses independently. C-13 provides one authoritative Address Management framework.

### Current State

- No address tables exist
- Person model exists in `kernel/user/models/person.py`
- Institution model exists in `kernel/tenant_institution/models/`
- AuditEmitter exists in `kernel/audit/`
- C-04 authorization framework in place

### Target State

- 8 new tables: `entity_type`, `address_type`, `address_type_entity_type`, `address`, `address_assignment`, `country`, `state`, `city`
- New module at `backend/kernel/address/`
- Integration with Person (C-02), Institution (C-01), Authorization (C-04), Audit (C-11)

---

## Goals / Non-Goals

### Goals

1. Implement address management with temporal assignments
2. Support geographic reference data (Country, State, City)
3. Support address type compatibility matrix
4. Seed default data (EntityTypes, AddressTypes, India geographic data)
5. Integrate with existing AuditEmitter
6. Enforce tenant boundaries via C-04

### Non-Goals

1. Latitude/longitude/GPS (deferred)
2. Geocoding/reverse geocoding (deferred)
3. Institution-specific AddressType customization (deferred)
4. RLS implementation (can be added later)
5. Pagination/filtering (can be added later)

---

## Decisions

### D1: Module Boundary

**Decision:** Module at `backend/kernel/address/`

**Rationale:** Matches existing conventions (kernel/academic/, kernel/relationship/)

### D2: Entity Types

**Decision:** Only 2 EntityTypes: INSTITUTION, PERSON

**Rationale:** Student/Employee/Staff all reference Person. No separate entity types needed.

### D3: Polymorphic Association

**Decision:** Generic `entity_type_id` + `entity_id` on AddressAssignment

**Rationale:** Flexible, simple, aligns with PRD's "generic polymorphic association" language

### D4: Scope Derivation

**Decision:** No `client_id`/`institution_id` on Address tables

**Rationale:** Scope derived from target entity. C-04 handles authorization.

### D5: Authorization

**Decision:** C-04 app-level authorization, no RLS initially

**Rationale:** Consistency with existing pattern. RLS can be added later.

### D6: Temporal Overlap

**Decision:** Application-level validation

**Rationale:** Simpler than DB constraints. Can be added later if concurrency issues arise.

### D7: Address Deletion

**Decision:** Hard delete Address with Assignment

**Rationale:** No reuse, no orphans. PRD explicitly states this.

### D8: Address Replacement

**Decision:** Single transactional service method

**Rationale:** Atomic business change. PRD requires this.

### D9: Address Correction

**Decision:** Separate endpoint with `address.correct` permission

**Rationale:** Controlled modification of effective data. PRD requires separate authorization.

### D10: Geographic Data

**Decision:** Seed India data in migration

**Rationale:** Manageable dataset. Other countries added later via migration.

---

## Risks / Trade-offs

### Risk: Concurrent Duplicate Assignments

**Impact:** Two requests could create overlapping assignments

**Mitigation:** Application-level overlap check. Unique constraint on (entity_type_id, entity_id, address_type_id, valid_from) as additional protection.

### Risk: Scope Resolution Complexity

**Impact:** Address queries need to JOIN through entity for scope

**Mitigation:** Service layer handles this transparently. Polymorphic helper methods.

---

## Migration Plan

### Steps

1. Create C-13 tables (8 tables)
2. Seed EntityTypes (INSTITUTION, PERSON)
3. Seed AddressTypes (RESIDENTIAL, PERMANENT, CORRESPONDENCE, OFFICE, EMERGENCY)
4. Seed compatibility matrix
5. Seed geographic data (India)
6. Seed permissions

### Rollback

- C-13 tables are new — drop on rollback
- Permissions soft-deleted on rollback

---

## Open Questions

None — all decisions resolved in grill session.
