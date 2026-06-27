# ADR-0002: Three-layer DDD architecture

## Status

Accepted

## Context

The system must ensure tenant isolation, soft-delete filtering, and consistent data-access patterns across all business modules. If each module writes its own database queries, these invariants are easy to forget, leading to cross-tenant data leaks or inconsistent behavior. Modules express domain intent (e.g., "get students in section 5A for attendance"), but should not know database table schemas or SQL.

## Decision

Enforce a strict three-layer dependency model:

1. **Database layer** (`packages/database`): Prisma schema, generated client. Imported only by kernel.
2. **Kernel layer** (`packages/kernel`): Data access services that own all database interactions. Enforces tenant scoping, soft-delete filtering, validation. Imported by modules and API.
3. **Business modules** (`packages/<module>`): Domain logic only. Never imports `@school-erp/database` directly — only kernel and shared.

Dependency direction: `shared ← database ← kernel ← modules ← api`. No downward or circular imports.

## Consequences

- **Easier**: Tenant isolation is enforced in one place. Schema changes affect only kernel. Modules are testable by mocking kernel interfaces. New developers cannot accidentally skip tenant filters.
- **Harder**: Kernel becomes a bottleneck package — every new data shape requires a kernel method. Over time, kernel may grow large; future ADRs may split it into domain-specific kernel sub-packages (e.g., `kernel-academic`, `kernel-finance`).
