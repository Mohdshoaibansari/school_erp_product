# ADR-0011: Prisma Middleware for Tenant Isolation

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP is a multi-tenant platform where each tenant's data must be isolated. The architecture decision ADR-0004 established row-level tenancy (tenant_id on every table) as the isolation strategy. However, the implementation mechanism was left unspecified — services could either pass tenantId explicitly to every query or use a middleware layer to apply it automatically.

Explicit tenantId passing has several drawbacks:
- Every service method must accept and forward tenantId
- Risk of omission — a missing tenantId filter leaks data across tenants
- Boilerplate pollution in every query
- Refactoring cost if the tenant resolution strategy changes

An automated approach could eliminate these risks but introduces its own concerns around thread safety, testability, and debuggability.

## Decision

Implement tenant isolation via a centralized Prisma middleware using Node.js `AsyncLocalStorage` for thread-safe context propagation.

### Architecture

```
HTTP Request → Tenant Resolver → runWithTenant(tenantId, handler)
                                      │
                                      ▼
                              Service Layer (no tenant awareness)
                                      │
                                      ▼
                              Prisma Middleware (auto-injects tenantId)
                                      │
                                      ▼
                              PostgreSQL (row-level tenancy)
```

### Tenant Context

A `TenantContext` interface holds the current `tenantId`. It is stored in `AsyncLocalStorage` and accessed via helper functions:

- `setTenantContext(tenantId)` — sets context for the current async chain
- `getTenantId()` — returns current tenantId (undefined if not set)
- `runWithTenant(tenantId, fn)` — wraps execution in a tenant-scoped context

### Middleware Behavior

The Prisma middleware intercepts all database operations. For models with a `tenantId` field:

| Action | Behavior |
|--------|----------|
| findMany / findFirst | Adds tenantId to where clause |
| findUnique | Converts to findFirst + adds tenantId filter |
| create | Auto-injects tenantId into data |
| update / upsert | Adds tenantId to where clause |
| delete | Adds tenantId to where clause |
| count / aggregate | Adds tenantId to where clause |

### Exempted Models

Three models skip tenant filtering because they serve architectural roles that precede tenant resolution:

- **Tenant**: Identity provider for the tenant context itself
- **OrgUnit**: Belongs to Institution (which is tenant-filtered), but direct queries are unscoped
- **Permission**: Global permission registry, not tenant-specific

### Write Guard

Write operations (create, update, upsert, delete) throw an error if no tenant context is set, preventing accidental cross-tenant writes.

## Consequences

### Positive

- Eliminates repetitive `where: { tenantId }` across all services
- Single point of audit and maintenance for isolation logic
- Thread-safe via AsyncLocalStorage — no shared mutable state
- Read operations without context still work (for admin/cross-tenant queries)
- Write guard prevents data leaks on create operations

### Negative

- `findUnique` converted to `findFirst` changes Prisma's "not found" semantics — cross-tenant lookups silently return null rather than throw
- Middleware adds overhead to every query (minor, but non-zero)
- Debugging isolation issues requires understanding the middleware layer
- AsyncLocalStorage context can be lost if promises escape the scope chain

### Risks

- **Context Loss**: If a promise is created outside the AsyncLocalStorage scope but resolves inside it, context is lost. Mitigated by ensuring all async work stays within `runWithTenant`.
- **OrgUnit Exemption**: OrgUnit's exemption from tenant filtering is inconsistent with the pattern. Mitigated by accepting that OrgUnit queries are indirectly scoped through Institution joins.
- **Read Leak**: Reads without tenant context return all records. Mitigated by ensuring production request paths always set tenant context.

## Alternatives Considered

1. **Explicit tenantId passing**: Every method accepts tenantId as a parameter. Rejected due to boilerplate and omission risk.
2. **Schema-per-tenant**: Separate PostgreSQL schema per tenant. Rejected per ADR-0004 — migration complexity outweighs benefits.
3. **Custom Prisma client wrapper**: A wrapper class around Prisma that adds tenantId. Rejected — middleware is cleaner and doesn't require changing service constructors.
4. **Per-request Prisma instance**: Instantiate a new PrismaClient per request with tenant-scoped config. Rejected due to connection pool overhead.

## Related

- ADR-0004: Single multi-tenant deployment with row-level isolation
- `packages/database/src/index.ts` (implementation)
