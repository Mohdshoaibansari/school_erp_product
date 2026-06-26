## Context

The Tenant & Institution services form the foundation of the multi-tenant School ERP architecture. Every API request flows through tenant resolution and isolation before reaching business logic. The implementation covers tenant lifecycle (create → active → suspended → archived), institution management within a tenant, and automatic tenant-aware data isolation via Prisma middleware.

```
System Context (Lightweight C4)
════════════════════════════════

  ┌──────────┐     ┌──────────────────┐     ┌─────────────┐
  │  School   │────▶│   School ERP     │────▶│  PostgreSQL │
  │  Admin    │     │   API + Kernel   │     │  Database   │
  └──────────┘     └──────────────────┘     └─────────────┘
                           │
                           │ manages
                           ▼
                    ┌──────────────┐
                    │   Tenants    │
                    │  (Schools)   │
                    └──────────────┘
```

```
Tenant & Institution - Container View
══════════════════════════════════════

  ┌──────────────────────────────────────────────────────────┐
  │                 School ERP Application                    │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐  │
  │  │              Kernel Package                        │  │
  │  │  ┌──────────────┐   ┌────────────────────────┐    │  │
  │  │  │ Tenant       │   │ Institution            │    │  │
  │  │  │ Service      │   │ Service                │    │  │
  │  │  │              │   │                        │    │  │
  │  │  │ • create     │   │ • create               │    │  │
  │  │  │ • getById    │   │ • getById              │    │  │
  │  │  │ • getBySlug  │   │ • list                 │    │  │
  │  │  │ • list       │   │ • update               │    │  │
  │  │  │ • update     │   │ • completeOnboarding   │    │  │
  │  │  │ • suspend    │   │ • suspend/reactivate   │    │  │
  │  │  │ • reactivate │   │ • archive              │    │  │
  │  │  │ • archive    │   │ • getStats             │    │  │
  │  │  │ • getStats   │   │ • getActiveByTenant    │    │  │
  │  │  └──────┬───────┘   └──────────┬─────────────┘    │  │
  │  │         │                      │                   │  │
  │  │         └──────────┬───────────┘                   │  │
  │  │                    ▼                               │  │
  │  │         ┌──────────────────────┐                   │  │
  │  │         │  Database Package    │                   │  │
  │  │         │  (Prisma Client)     │                   │  │
  │  │         │                      │                   │  │
  │  │         │  • Tenant middleware │                   │  │
  │  │         │  • Auto tenantId     │                   │  │
  │  │         │    filtering         │                   │  │
  │  │         └──────────┬───────────┘                   │  │
  │  └────────────────────┼───────────────────────────────┘  │
  └───────────────────────┼──────────────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │  PostgreSQL   │
                  │               │
                  │  Tenant       │
                  │  Institution  │
                  │  (soft delete │
                  │   via         │
                  │   deletedAt)  │
                  └───────────────┘
```

## Goals / Non-Goals

**Goals:**
- Document the Tenant and Institution service implementations as they exist in code
- Capture the multi-tenant isolation pattern (Prisma middleware, tenantId scoping, soft delete)
- Record the tenant lifecycle state machine and institution status transitions

**Non-Goals:**
- Not proposing new features or behavioral changes
- Not modifying existing services or data models
- Not covering subscription/tier integration beyond the Tenant→SubscriptionTier relation

## Decisions

### Decision 1: Row-level tenant isolation via Prisma middleware
**Choice**: A centralized Prisma middleware in `packages/database/src/index.ts` intercepts all queries and auto-filters by `tenantId` using AsyncLocalStorage. `Tenant` and `OrgUnit` models are exempt from tenant filtering.
**Rationale**: Eliminates repetitive `where: { tenantId }` in every service method. One place to audit and maintain. AsyncLocalStorage provides thread-safe context without passing tenantId through every function call.
**Alternative considered**: Passing tenantId explicitly to every service method was rejected due to boilerplate and risk of omission.

### Decision 2: Soft delete with `deletedAt` + status field
**Choice**: Both `Tenant` and `Institution` use `deletedAt: DateTime?` for soft deletion and a `status` enum for lifecycle state. Queries filter `deletedAt: null` to exclude archived records.
**Rationale**: Preserves referential integrity and allows recovery. The status field provides a richer lifecycle (ONBOARDING → ACTIVE → SUSPENDED → ARCHIVED) beyond binary deleted/not-deleted.
**Alternative considered**: Hard delete was rejected — would break audit trails and historical records.

### Decision 3: Tenant create bootstraps first institution
**Choice**: `TenantService.create()` automatically creates a "Main Campus" institution with ONBOARDING status alongside the tenant.
**Rationale**: Every tenant needs at least one institution to be operational. Coupling the creation ensures atomic setup — no orphan tenants.
**Trade-off**: The naming ("Main Campus") and type (SCHOOL) are hardcoded. Future multi-institution tenants would need a different flow.

### Decision 4: Suspending a tenant cascades to all institutions
**Choice**: `TenantService.suspend()` updates the tenant to SUSPENDED and bulk-updates all non-archived institutions to SUSPENDED.
**Rationale**: A suspended tenant should not have active institutions. Cascading prevent inconsistent states.
**Trade-off**: Rollback is manual — if the bulk update fails, the tenant may be SUSPENDED with active institutions still running.

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Tenant middleware blocks writes without tenant context | Low | Explicit check for `protectedActions` without tenantId throws a descriptive error |
| Tenant middleware converts `findUnique` to `findFirst`, potentially matching wrong record | Low | The added tenantId filter ensures the record belongs to the current tenant; unique constraints still apply within tenant scope |
| Slug collisions on tenant create | Low | `slug` is a unique constraint; service checks before create |
| Suspended tenant's institutions might miss the cascade | Low | The bulk update uses `updateMany` in the same transaction as tenant update |

## Migration Plan

Not applicable — this is a documentation-only artifact. No code migration or deployment changes.

## Open Questions

1. Should `OrgUnit` be exempt from tenant filtering? Currently it is in `SKIP_TENANT_FILTER_MODELS` — this seems intentional since OrgUnit belongs to Institution (which is tenant-filtered), but the exemption bypasses tenant scoping on direct OrgUnit queries.
2. The `Tenant` model is in `SKIP_TENANT_FILTER_MODELS` because tenant resolution happens before context is set — but this means tenant queries themselves are unscoped, which is correct.
