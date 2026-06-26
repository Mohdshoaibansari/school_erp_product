## Why

The School ERP needs simple data tables (Prisma models only, no service classes) and integration testing for all kernel services:

1. **Student-Guardian Relationships** — Mapping with relationship types and contact roles
2. **Code Generation** — Auto-incrementing identifiers with configurable formats
3. **Addresses** — Structured address records linked to entities
4. **Documents** — Centralized file storage with metadata
5. **Integration Tests** — Test coverage for all kernel services

Without these data tables, business modules (Students, Fees) cannot store structured data. Without integration tests, kernel service correctness is unverified.

## What Changes

- Implement student-guardian mapping with relationship types
- Implement atomic ID generation per institution per year
- Implement structured addresses with type labels
- Implement document metadata and storage abstraction
- Implement integration tests for all kernel services

## Capabilities

### New Capabilities

- `simple-relationships`: Student-guardian mapping with relationship types and contact roles
- `simple-code-generation`: Auto-incrementing identifiers with configurable formats
- `simple-addresses`: Structured address records linked to entities
- `simple-documents`: Centralized file storage with metadata

### Modified Capabilities

- None

## Impact

- **Packages affected**: `packages/database/prisma/schema.prisma`, `packages/kernel/src/identifier/`, test files across all packages
- **Dependencies**: Requires completed kernel services
- **Required by**: Business modules (Students, Fees)
- **Database**: New tables for student_guardians, identifier_sequences, addresses, documents
- **API**: No new endpoints (data tables consumed via Prisma directly)
- **Testing**: Vitest framework installed, integration tests for all kernel services
