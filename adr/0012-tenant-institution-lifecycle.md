# ADR-0012: Tenant and Institution Lifecycle with Cascade Suspension

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP's tenant and institution models need well-defined lifecycles. Every tenant begins with a first institution, both go through status transitions, and their states are coupled — suspending a tenant should cascade to its institutions. The lifecycle rules and cascade semantics need to be explicit to ensure consistent behavior across all service interactions.

Key questions:
- What is the initial state of a new tenant and its institutions?
- Which status transitions are valid?
- Should tenant suspension cascade to institutions?
- Should tenant reactivation cascade back?
- Is archival reversible?

## Decision

### Tenant Lifecycle

```
CREATED → ACTIVE → SUSPENDED → ARCHIVED
                ↑         │
                └─────────┘ (reactivate)
```

| Transition | Method | Conditions |
|------------|--------|------------|
| → ACTIVE | TenantService.create | Auto-set on creation |
| ACTIVE → SUSPENDED | TenantService.suspend | Must not already be SUSPENDED |
| SUSPENDED → ACTIVE | TenantService.reactivate | Must be in SUSPENDED |
| ACTIVE/SUSPENDED → ARCHIVED | TenantService.archive | Must exist |

### Institution Lifecycle

```
ONBOARDING → ACTIVE → SUSPENDED → ARCHIVED
                 ↑         │
                 └─────────┘ (reactivate)
```

| Transition | Method | Conditions |
|------------|--------|------------|
| → ONBOARDING | InstitutionService.create | Auto-set on creation |
| ONBOARDING → ACTIVE | InstitutionService.completeOnboarding | Must be in ONBOARDING |
| ACTIVE → SUSPENDED | InstitutionService.suspend | Must not be SUSPENDED or ARCHIVED |
| SUSPENDED → ACTIVE | InstitutionService.reactivate | Must be in SUSPENDED |
| ACTIVE/SUSPENDED → ARCHIVED | InstitutionService.archive | Must not already be ARCHIVED |

### Cascade Semantics

**Tenant → Institutions (suspend):** When a tenant is suspended, all non-archived institutions under that tenant are also suspended. This prevents an inconsistent state where a suspended tenant has active institutions. The cascade uses a bulk `updateMany` operation.

**No cascade on reactivate:** Tenant reactivation does NOT cascade to institutions. Institutions suspended by the tenant suspension remain SUSPENDED and must be individually reactivated. This requires administrators to deliberately re-enable institutions after a tenant suspension is lifted.

**No cascade on archive:** Tenant archival does not cascade. Each institution must be archived independently. This preserves the ability to keep some institutions active if needed.

### Bootstrap on Tenant Creation

When a new tenant is created, a first institution named "{Tenant Name} - Main Campus" is auto-created in ONBOARDING status. This ensures:
- Every tenant has at least one institution immediately
- The institution can be configured and activated via the onboarding flow
- No orphan tenants exist

### Soft Delete Pattern

Both Tenant and Institution use soft delete: `status` is set to `ARCHIVED` and `deletedAt` is set to the current timestamp. Queries consistently filter `deletedAt: null` to exclude archived records. This preserves referential integrity and allows recovery.

## Consequences

### Positive

- Clear, documented lifecycle rules for both models
- Consistent cascade semantics prevent inconsistent tenant/institution states
- Soft delete preserves data integrity and audit trail
- Bootstrap ensures tenants are never created without an institution

### Negative

- Reactivation after suspension requires manual institution reactivation (no cascade back)
- "Main Campus" name is hardcoded — not configurable at creation
- No cascade on tenant archive means archived tenants may still have active institutions

### Risks

- **Partial Cascade Failure**: If the bulk institution update fails after the tenant status is updated, the tenant may show SUSPENDED while institutions remain ACTIVE. Mitigation: currently not in a transaction; should be transactional.
- **No Cascade on Reactivate**: Administrators may expect institutions to auto-reactivate. Mitigation: clear documentation of cascade behavior.

## Alternatives Considered

1. **No cascade**: Tenant suspension doesn't affect institutions. Rejected — inconsistent state risk.
2. **Bidirectional cascade**: Tenant suspend cascades down, tenant reactivate cascades up. Rejected — reactivation should be deliberate per institution.
3. **Hard delete**: Use actual DELETE instead of soft delete. Rejected — would break audit trails and historical records.
4. **Custom institution naming**: Allow tenant creation to specify institution name. Rejected for Phase 1 — naming can be changed after creation via update.

## Related

- `packages/kernel/src/tenant/tenant.service.ts` (implementation)
- `packages/kernel/src/institution/institution.service.ts` (implementation)
- ADR-0004: Single multi-tenant deployment with row-level isolation
