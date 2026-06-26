## Proposal: Data Tables & Integration Testing

### Summary
Implement simple data tables (Prisma models only, no service classes) and integration testing for all kernel services:
1. **Student-Guardian Relationships** — Mapping with relationship types and contact roles
2. **Code Generation** — Auto-incrementing identifiers with configurable formats
3. **Addresses** — Structured address records linked to entities
4. **Documents** — Centralized file storage with metadata
5. **Integration Tests** — Test coverage for all kernel services

### Motivation
These data tables are prerequisites for business modules (Students, Fees) that need structured data. Integration tests ensure correctness.

### Scope
- Student-guardian mapping with relationship types
- Atomic ID generation per institution per year
- Structured addresses with type labels
- Document metadata and storage abstraction
- Integration tests for all kernel services

### Dependencies
- Requires completed kernel services
- Required by business modules (Students, Fees)
