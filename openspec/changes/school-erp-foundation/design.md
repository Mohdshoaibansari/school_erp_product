## Context

School ERP platform targeting the Indian school market. The system follows a three-layer architecture: Kernel (foundational capabilities), Services (cross-cutting concerns), and Business Modules (revenue-generating features).

Current state: Architecture documented, no code written. This change establishes the business model foundation — subscription tiers, per-student billing, student enrollment lifecycle, and module gating — on top of the existing multi-tenant kernel design.

Key constraints: Single codebase serving both free and paid tiers. Free tier drives adoption. Paid tier generates revenue via per-student billing. All modules are bundled for paid clients — no per-module selection.

```
┌──────────────────────────────────────────────────────────────┐
│                        API Gateway                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ Auth     │ │ Tenant   │ │ Module   │ │ Subscription    │ │
│  │ MW       │ │ Resolver │ │ Gating   │ │ Enforcement MW  │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    Business Modules                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ Students │ │Attendance│ │  Fees    │ │ Exams, Homework │ │
│  │ (Free)   │ │ (Free)   │ │ (Free)   │ │ (Paid, gated)   │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                 Subscription Engine (C-07+)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Tier & Caps  │ │ Student      │ │ Module Entitlements  │ │
│  │ (free/paid)  │ │ Counting     │ │ (what's unlocked)    │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Goals / Non-Goals

**Goals:**
- Define free tier with 100-student cap and 3 free modules (Students, Attendance, Fees)
- Define paid tier with per-student billing, all modules unlocked
- Track student lifecycle (active → graduated/transferred/archived) for accurate billing
- Implement hidden module gating — paid modules invisible to free users
- Soft block on student cap — existing functionality unaffected, new adds rejected

**Non-Goals:**
- Not building self-host infrastructure (deferred)
- Not building per-module pricing (paid = all modules)
- Not building trial management (can be added later)
- Not building usage metering beyond student count
- Not building alumni management as a service (students only)

## Decisions

### Decision 1: Soft block on student cap
**Choice**: Reject new student creation at 100, keep existing functionality
**Rationale**: Minimizes disruption — schools can continue using the platform while evaluating upgrade. Hard block would destroy trust.
**Trade-off**: Schools may game the system by not removing inactive students. Mitigation: automated archival of students inactive for 2+ consecutive academic years.

### Decision 2: Hidden module gating (no upsell)
**Choice**: Paid modules are invisible to free-tier users. No lock icons, no upgrade banners, no disabled buttons.
**Rationale**: Clean UX. Free-tier users see a complete, functional product. Upsell is handled through out-of-band channels (email, sales).
**Trade-off**: Missed in-app conversion opportunities. Acceptable for Phase 1 — conversion strategy can evolve later.

### Decision 3: Per-student billing, all modules included
**Choice**: Paid clients pay per active student and get every module.
**Rationale**: Simplest pricing model. No per-module complexity in billing, entitlement tracking, or frontend gating.
**Trade-off**: Clients who only need one paid module still pay full per-student rate. Future tiered bundles can address this.

### Decision 4: Student lifecycle based on enrollment
**Choice**: Only actively enrolled students count toward billing. Graduation, transfer, and archival change status.
**Rationale**: Aligns billing with actual usage. Schools don't pay for students who have left.
**Trade-off**: Requires precise enrollment management — a bug in the lifecycle could affect billing.

### Decision 5: Single codebase, single deployment
**Choice**: One SaaS app serves all clients. Dedicated instances are a manual exception.
**Rationale**: Simplest operations. One deploy, one DB cluster, one monitoring surface.
**Trade-off**: Data isolation is row-level only. If a client demands physical isolation, a new instance must be deployed manually.

```
Enforcement Flow
═════════════════

Request → Auth → Tenant Resolve → Subscription Check
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                    Module Gated?          Student Cap?
                          │                     │
                     ┌────┴────┐          ┌────┴────┐
                     ▼         ▼          ▼         ▼
                  403 OK    Blocked?   Under cap?  At cap?
                              │         │          │
                           Hidden    Proceed   402 + block
```

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Student count drift (inactive students still counting) | Medium | Incorrect billing | Automated archival after 2 inactive years |
| Free tier users hitting cap mid-year | High | Frustration | Graceful soft block, clear upgrade path via email |
| Module gating bypass via direct URL | Low | Free tier accesses paid features | API-level enforcement as second gate — frontend gating is UX, API gating is security |
| Billing disputes over student count | Medium | Revenue loss | Audit trail for all enrollment changes, period snapshots |
| Alumni re-enrollment counting as new billing unit | Low | Minor revenue gain | Acceptable — re-enrolled student is actively using the system |

## Migration Plan

Phase 1: Build subscription engine and student lifecycle alongside existing kernel
Phase 2: Implement module gating middleware and frontend visibility
Phase 3: Launch free tier with 100-student cap and 3 free modules
Phase 4: Launch paid tier with per-student billing
Phase 5: Add automated archival, billing reports, and audit

Rollback: Freeze new subscriptions, convert all to paid legacy with manual pricing.

## Open Questions

1. Billing cycle: monthly or annual? Affects proration logic for mid-cycle enrollment changes.
2. Maximum concurrent enrollment vs. peak for billing: do we bill at end-of-cycle count or max during cycle?
3. What happens to module data when a paid client downgrades to free? (Hidden, archived, or deleted?)
4. Automated archival period: is 2 consecutive academic years the right threshold?
