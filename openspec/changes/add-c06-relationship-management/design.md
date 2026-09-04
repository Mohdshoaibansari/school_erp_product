# Design — C-06 Relationship Management Framework

> **Change:** add-c06-relationship-management
> **Status:** Draft
> **Date:** 2026-09-03

---

## Context

The platform lacks a centralized person-to-person relationship model. Business modules create independent parent/guardian/contact mappings, causing duplicated data and conflicting definitions. C-06 provides one authoritative relationship framework.

### Current State

- No relationship tables exist
- Person model exists in `kernel/user/models/person.py`
- AuditEmitter exists in `kernel/audit/`
- C-04 authorization framework in place

### Target State

- 5 new tables: `relationship_type`, `contact_role`, `relationship_type_contact_role`, `relationship`, `contact_role_assignment`
- New module at `backend/kernel/relationship/`
- Integration with Person (C-02), Authorization (C-04), Audit (C-11)

---

## Goals / Non-Goals

### Goals

1. Implement person-to-person relationship model
2. Support directional and symmetric relationship types
3. Support temporal relationships (valid_from, valid_to)
4. Support relationship-specific responsibilities (ContactRoles)
5. Seed default RelationshipTypes and ContactRoles
6. Integrate with existing AuditEmitter
7. Enforce tenant boundaries via RLS

### Non-Goals

1. Priority ordering for EmergencyContact (deferred)
2. Institution-specific customization (deferred)
3. Cross-institution relationships (deferred)
4. Advanced family graph queries (deferred)

---

## Decisions

### D1: Tenant Scoping

**Decision:** Relationships use `client_id` only, no `institution_id`.

**Rationale:** Institution context is derived from Person when needed. Keeps relationship model simple.

### D2: Symmetric Normalization

**Decision:** For symmetric relationships, store `person_a_id < person_b_id` (UUID comparison). Add `normalized_pair` column for unique constraint.

**Rationale:** Enforces unordered uniqueness at database level. Prevents concurrent duplicates.

### D3: Temporal Overlap Enforcement

**Decision:** Application-level validation, not PostgreSQL exclusion constraints.

**Rationale:** Simpler implementation. Database constraints can be added later if concurrency issues arise.

### D4: Status Computation

**Decision:** Dynamic status computation from dates (no `status` column).

**Rationale:** Consistent with C-05 Term model. Avoids stale status values.

### D5: Containment Enforcement

**Decision:** Service-level validation for role containment within Relationship validity.

**Rationale:** Complex validation logic better suited to application code.

### D6: Inverse Type Generation

**Decision:** Auto-generate inverse RelationshipType in same transaction.

**Rationale:** Simpler API. User creates one type, system creates the pair.

### D7: Audit Integration

**Decision:** Inject AuditEmitter into services, emit events for all mutations.

**Rationale:** Consistent with existing platform pattern.

---

## Risks / Trade-offs

### Risk: Concurrent Duplicate Relationships

**Impact:** Two requests could create duplicate relationships for same person pair.

**Mitigation:** `normalized_pair` UNIQUE constraint prevents database-level duplicates. App-level overlap check prevents temporal duplicates.

### Risk: Complex Temporal Validation

**Impact:** Multiple temporal constraints (relationship overlap, role containment, role overlap) add complexity.

**Mitigation:** Clear separation of concerns. Each validation is independent and testable.

---

## Migration Plan

### Steps

1. Create C-06 tables (5 tables)
2. Seed default RelationshipTypes with inverse pairs
3. Seed default ContactRoles
4. Seed compatibility matrix
5. Add RLS policies
6. Seed permissions

### Rollback

- C-06 tables are new — drop on rollback
- Permissions soft-deleted on rollback

---

## Open Questions

None — all decisions resolved in grill session.
