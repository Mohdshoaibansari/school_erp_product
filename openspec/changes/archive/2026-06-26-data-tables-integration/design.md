## Context

The School ERP needs simple data tables (Prisma models only, no service classes) and integration testing for all kernel services:

1. **Student-Guardian Relationships** — Mapping with relationship types and contact roles
2. **Code Generation** — Auto-incrementing identifiers with configurable formats
3. **Addresses** — Structured address records linked to entities
4. **Documents** — Centralized file storage with metadata
5. **Integration Tests** — Test coverage for all kernel services

### Existing ADRs in Force

- ADR-0004: Single multi-tenant deployment with row-level isolation — every table must include `tenant_id`

## Goals / Non-Goals

**Goals:**
- Implement student-guardian mapping with relationship types
- Implement atomic ID generation per institution per year
- Implement structured addresses with type labels
- Implement document metadata and storage abstraction
- Implement integration tests for all kernel services

**Non-Goals:**
- No full family tree management (future enhancement)
- No complex ID format expressions (simple patterns only)
- No address validation against postal services (future enhancement)
- No file versioning or check-in/check-out (future enhancement)

## C4 Diagrams

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                      School ERP System                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Student     │  │  Identifier  │  │  Address     │         │
│  │  Guardian    │  │  Service     │  │  Service     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  Document    │  │  Integration │                            │
│  │  Service     │  │  Tests       │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                        │
│  student_guardians | identifiers | addresses | documents        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  File Storage    │
                    │  (Local/S3)      │
                    └──────────────────┘
```

### Level 2: Container

```
┌─────────────────────────────────────────────────────────────────┐
│                    Express API Server                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Kernel Package                          │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Student      │  │ Identifier   │  │ Address      │   │ │
│  │  │ Guardian     │  │ Service      │  │ (Prisma only)│   │ │
│  │  │ (Prisma only)│  │              │  │              │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │  ┌──────────────┐  ┌──────────────┐                      │ │
│  │  │ Document     │  │ Test Suite   │                      │ │
│  │  │ (Prisma only)│  │ (Vitest)     │                      │ │
│  │  └──────────────┘  └──────────────┘                      │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Level 3: Component (Identifier Service)

```
┌─────────────────────────────────────────────────────────────────┐
│                    IdentifierService                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Methods                                                   │   │
│  │  • generate(scope, pattern, year?)                       │   │
│  │  • getNextSequence(scope, year)                          │   │
│  │  • validatePattern(pattern)                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PrismaClient                                              │   │
│  │  • IdentifierSequence                                     │   │
│  │    • scope (institutionId + year + pattern)              │   │
│  │    • currentSequence                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Atomic Increment                                          │   │
│  │  • SELECT ... FOR UPDATE                                  │   │
│  │  • UPDATE sequence = sequence + 1                        │   │
│  │  • RETURN formatted ID                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: Student-Guardian as Join Table

**Decision:** Student-guardian relationships stored in dedicated `student_guardians` join table with relationship type and contact role.

**Rationale:**
- Many-to-many relationship (one guardian can have multiple students)
- Relationship metadata (type: Mother, Father, Guardian)
- Contact priority (role: PrimaryGuardian, EmergencyContact)

**Consequences:**
- Join table with `studentId`, `guardianId`, `relationshipType`, `contactRole`
- Guardian is a User with specific role assignment
- Query: get all guardians for a student, get all students for a guardian

### Decision 2: Atomic ID Generation with Sequences

**Decision:** Identifiers generated atomically using database sequences with configurable patterns.

**Rationale:**
- No duplicate IDs under concurrent access
- Per-institution, per-year sequences
- Configurable format: `STU-{YEAR}-{SEQ:5}`

**Consequences:**
- `identifier_sequences` table with `scope`, `year`, `currentSequence`
- Atomic increment using `SELECT ... FOR UPDATE`
- Pattern parsing: `{YEAR}`, `{SEQ:5}`, `{INST}`

### Decision 3: Addresses as Structured Records

**Decision:** Addresses stored as structured records with line1, city, state, postalCode, country fields.

**Rationale:**
- Enables filtering by city, state, postal code
- Supports multiple addresses per entity (home, billing)
- Consistent address format across entities

**Consequences:**
- `addresses` table with entity FK (polymorphic: `entityType`, `entityId`)
- Address type label (HOME, BILLING, WORK)
- One address marked as primary per entity per type

### Decision 4: Documents as Metadata Only

**Decision:** Document service stores metadata only. Actual files stored in external storage (local filesystem or S3).

**Rationale:**
- Database stays small and fast
- File storage can scale independently
- Supports multiple storage backends

**Consequences:**
- `documents` table with metadata (name, type, size, path)
- Storage abstraction interface (LocalStorage, S3Storage)
- File operations go through storage interface

### Decision 5: Co-Located Tests

**Decision:** Test files co-located with source files (e.g., `user.service.test.ts` next to `user.service.ts`).

**Rationale:**
- Easy to find tests for a given file
- Encourages writing tests alongside code
- Standard convention in TypeScript projects

**Consequences:**
- Test files use `.test.ts` suffix
- Vitest as test framework
- Separate test database for integration tests

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| ID generation bottleneck | Sequence caching, batch allocation |
| Address data quality | Validation rules, address lookup (future) |
| File storage costs | Configurable retention, archival |
| Test database isolation | Separate test DB, transaction rollback |

## Open Questions

1. Should addresses support geocoding? (Future: latitude/longitude)
2. Should documents support versioning? (Future: file history)
3. Should identifiers support check digits? (Future: validation)
