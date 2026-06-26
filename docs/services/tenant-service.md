# Tenant Service

**File:** `packages/kernel/src/tenant/tenant.service.ts`
**Exported from:** `packages/kernel/src/tenant/index.ts`
**Package:** `@school-erp/kernel`

## Overview

The Tenant service manages multi-tenant lifecycle: creation, activation, suspension, and archival of tenant organizations. Each tenant represents a school or educational institution group that operates as an isolated unit within the platform.

Every tenant is automatically provisioned with a first institution at creation. Tenant records are soft-deleted via `deletedAt` timestamp and `ARCHIVED` status.

## Data Model

The `Tenant` model in Prisma schema (`packages/database/prisma/schema.prisma`):

| Field | Type | Notes |
|-------|------|-------|
| `id` | String (UUID) | Primary key |
| `name` | String | Display name |
| `slug` | String (unique) | URL-friendly identifier, used for lookup |
| `status` | TenantStatus enum | ACTIVE, SUSPENDED, ARCHIVED |
| `tierId` | String? | FK to SubscriptionTier (nullable for unassigned) |
| `deletedAt` | DateTime? | Soft-delete timestamp |

### Relations
- `institutions: Institution[]` — schools under this tenant
- `users: User[]` — all users registered under this tenant
- `Role: Role[]` — tenant-level roles

### Status Lifecycle

```
CREATED → ACTIVE → SUSPENDED → ARCHIVED
                ↑         │
                └─────────┘ (reactivate)
```

- **ACTIVE**: Tenant is operational, all features available
- **SUSPENDED**: Tenant is temporarily disabled, institutions cascade to SUSPENDED
- **ARCHIVED**: Terminal state, soft-deleted, cannot reactivate

## Service Methods

### `create(data: CreateTenantInput): Promise<Tenant>`

Creates a new tenant with an auto-provisioned "Main Campus" institution in ONBOARDING status.

```typescript
interface CreateTenantInput {
  name: string;
  slug: string;
}
```

**Validation:**
- Slug uniqueness is enforced by a database unique constraint and checked before creation
- An error is thrown if the slug is already taken

**Atomic setup:** The tenant and its first institution are created in a single Prisma `create` call with nested `institutions.create`. This ensures the tenant is never without at least one institution.

### `getById(id: string): Promise<Tenant | null>`

Fetches a tenant by UUID. Excludes soft-deleted records (`deletedAt: null`).

### `getBySlug(slug: string): Promise<Tenant | null>`

Fetches a tenant by URL-friendly slug. Excludes soft-deleted records.

### `list(options: ListTenantsOptions): Promise<Tenant[]>`

Lists tenants with optional status filtering and pagination.

```typescript
interface ListTenantsOptions {
  status?: TenantStatus;
  limit?: number;  // default 10
  offset?: number; // default 0
}
```

Always excludes soft-deleted records. Ordered by `createdAt` descending.

### `update(id: string, data: UpdateTenantInput): Promise<Tenant>`

Updates tenant fields. Checks existence before update. If slug is being changed, validates uniqueness against other tenants.

### `suspend(id: string): Promise<Tenant>`

Suspends the tenant and cascades suspension to all non-archived institutions.

**Validation:**
- Tenant must exist
- Tenant must not already be SUSPENDED

**Cascade behavior:** Uses Prisma `updateMany` on institutions to set status to SUSPENDED for all institutions not already ARCHIVED.

### `reactivate(id: string): Promise<Tenant>`

Reactivates a suspended tenant back to ACTIVE status. Does NOT cascade reactivation to institutions.

**Validation:**
- Tenant must exist
- Tenant must be in SUSPENDED status

### `archive(id: string): Promise<Tenant>`

Soft-deletes a tenant by setting status to ARCHIVED and `deletedAt` to the current timestamp.

**Validation:**
- Tenant must exist

### `getStats(id: string): Promise<TenantStats>`

Returns aggregated statistics for a tenant:

```typescript
{
  id: string;
  name: string;
  status: TenantStatus;
  institutionCount: number; // non-deleted institutions
  userCount: number;        // non-deleted users
  createdAt: DateTime;
  updatedAt: DateTime;
}
```

Excludes soft-deleted institutions and users from counts.

## Patterns & Conventions

- All queries filter `deletedAt: null` to exclude soft-deleted records
- Tenant ID is the root isolation boundary — all tenant-scoped models reference `tenantId`
- The Tenant model itself is exempt from the auto-tenant-filtering middleware (tenant resolution happens before context is set)
