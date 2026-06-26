# ADR-0010: Per-Student Billing with Bundled Modules

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP needs a pricing model for paid-tier users that is simple, fair, and easy to understand. The challenge is balancing simplicity with flexibility.

## Decision

Implement per-student billing with bundled modules:

1. **Per-Student Pricing**: Paid clients pay per actively enrolled student
2. **All Modules Included**: Every module is unlocked for paid clients
3. **Student Lifecycle Billing**: Only actively enrolled students count toward billing
4. **No Per-Module Pricing**: No option to pay for individual modules

### Key Design Choices

- **Simple Pricing**: One price per student, all modules included
- **Active Enrollment Only**: Graduated, transferred, and archived students don't count
- **No Module Selection**: Paid tier includes everything (no à la carte)
- **Clear Billing**: Invoice shows: "X students × $Y/student = $Z total"

## Consequences

### Positive

- Simple to understand and implement
- No complex module entitlement tracking
- Clear value proposition for paid tier
- Easy to calculate and predict costs

### Negative

- Clients who only need one paid module still pay full per-student rate
- No flexibility for different school sizes or needs
- May be expensive for small schools with few students

### Risks

- **Student Count Drift**: Inactive students may still count. Mitigation: automated archival after 2 inactive years.
- **Billing Disputes**: Disagreements over student count. Mitigation: audit trail for enrollment changes, period snapshots.
- **Re-enrollment Billing**: Alumni re-enrolling may count as new billing units. Mitigation: acceptable — re-enrolled student is actively using system.

## Alternatives Considered

1. **Per-Module Pricing**: Charge per module. Rejected due to complexity.
2. **Tiered Bundles**: Different bundles for different needs. Rejected for Phase 1 simplicity.
3. **Flat Monthly Fee**: Fixed price regardless of students. Rejected due to unfairness to small schools.

## Related

- ADR-0003: Bundled paid tier with per-student pricing (original decision)
- ADR-0005: Student lifecycle billing based on active enrollment
- school-erp-foundation change
