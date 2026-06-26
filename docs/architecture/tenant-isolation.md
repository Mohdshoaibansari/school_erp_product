# Multi-Tenant Isolation Pattern

**Middleware file:** `packages/database/src/index.ts`
**Package:** `@school-erp/database`

## Overview

Tenant isolation is enforced at the database access layer via Prisma middleware. Every query to a tenant-scoped model is automatically filtered by `tenantId`, and every create operation auto-injects the current tenant context. This eliminates repetitive `where: { tenantId }` clauses across all services.

Thread-safe tenant context is provided by Node.js `AsyncLocalStorage`, ensuring concurrent requests do not leak tenant boundaries.

## Tenant Context

### `AsyncLocalStorage`-based context

```typescript
interface TenantContext {
  tenantId: string;
}
```

The tenant context is stored using `AsyncLocalStorage`, which provides:
- **Thread safety**: Each async chain gets its own context — no shared mutable state
- **Automatic cleanup**: Context is cleaned up when the async chain completes
- **No explicit passing**: Services never need to pass `tenantId` through method chains

### Helper Functions

```typescript
function setTenantContext(tenantId: string): void
function getTenantContext(): TenantContext | undefined
function getTenantId(): string | undefined
function clearTenantContext(): void
function runWithTenant<T>(tenantId: string, fn: () => T): T
```

**Usage pattern (API layer):**

```typescript
// In request middleware:
const tenant = await resolveTenantFromRequest(req);
runWithTenant(tenant.id, () => {
  next();
});

// In service (no tenantId needed):
const result = await someService.list(); // auto-filtered
```

## Prisma Middleware

The middleware intercepts all Prisma operations and applies tenant scoping based on model type and action.

### Tenanted Models

These models have a `tenantId` field and are auto-filtered:

`Institution`, `User`, `UserInstitution`, `UserProfile`, `Role`, `RoleAssignment`, `ModuleEntitlement`

### Models Exempt from Tenant Filtering

These models are excluded because they serve a different architectural role:

| Model | Reason for Exemption |
|-------|---------------------|
| `Tenant` | Tenant resolution happens before context is set — it's the identity provider for the context itself |
| `OrgUnit` | Belongs to Institution which is already tenant-filtered; direct OrgUnit queries bypass tenant scope |
| `Permission` | Global permission registry — not tenant-specific |

### Middleware Behavior by Action

| Action | Behavior |
|--------|----------|
| `findMany` | Adds `tenantId` to the `where` clause |
| `findFirst` | Adds `tenantId` to the `where` clause |
| `findUnique` | Converts to `findFirst` and adds `tenantId` filter |
| `create` | Auto-injects `tenantId` into the `data` object |
| `update` | Adds `tenantId` to the `where` clause — ensures cross-tenant updates fail |
| `upsert` | Adds `tenantId` to the `where` clause |
| `delete` | Adds `tenantId` to the `where` clause |
| `count` | Adds `tenantId` to the `where` clause |
| `aggregate` | Adds `tenantId` to the `where` clause |

### Write Operation Guard

For write operations (`create`, `update`, `upsert`, `delete`), the middleware **requires** a tenant context. If none is set, it throws:

```
Tenant context required for write operations
```

This prevents accidental cross-tenant writes or data creation without proper scoping. Read operations (`findMany`, `findFirst`, `count`) are allowed without a context — they simply return unscoped results.

## Architecture Summary

```
HTTP Request
     │
     ▼
Auth Middleware (resolves user)
     │
     ▼
Tenant Resolver (identifies tenantId)
     │
     ▼
runWithTenant(tenantId, handler)
     │
     ▼
Service Layer (no tenant awareness needed)
     │
     ▼
Prisma Middleware (auto-injects tenantId filter)
     │
     ▼
PostgreSQL (row-level tenant isolation)
```

## Trade-offs & Considerations

- **`findUnique` conversion**: The middleware converts `findUnique` to `findFirst` for tenanted models. This is safe because the added `tenantId` filter makes the query unique within the tenant scope, not globally. However, it means Prisma's "not found" response for cross-tenant queries is indistinguishable from the record not existing (desirable for security — don't leak existence across tenants).
- **Reads without context**: If no tenant context is set, reads return all records across all tenants. This is intentional for administrative and cross-tenant operations but should be used carefully.
- **`OrgUnit` exemption**: OrgUnit's exemption from tenant filtering is notable — although OrgUnit belongs to Institution (which is tenant-filtered), direct OrgUnit queries bypass tenant scope. This may be an oversight or intentional for cross-institution queries within a tenant.
