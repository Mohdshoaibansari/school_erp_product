# ADR-0008: Soft-Block Student Cap Enforcement

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP needs to enforce a 100-student cap for free-tier users while maintaining existing functionality. The challenge is balancing enforcement with user experience.

## Decision

Implement soft-block enforcement for the student cap:

1. **Rejection**: New student creation is rejected when the cap (100) is reached
2. **Preservation**: Existing functionality continues to work for enrolled students
3. **Messaging**: Clear error message indicating the cap has been reached
4. **Upgrade Path**: Users directed to upgrade via email/sales (not in-app)

### Key Design Choices

- **Soft Block**: Existing data is not affected; only new additions are blocked
- **No Data Loss**: Students can still view, edit, and manage existing students
- **Clear Feedback**: Error message: "Student limit reached (100/100). Please upgrade your subscription."
- **Out-of-Band Upgrade**: Upgrade path via email/sales, not in-app upsell

## Consequences

### Positive

- Schools can continue using the platform while evaluating upgrade
- No disruption to existing operations
- Clear incentive to upgrade without frustration

### Negative

- Schools may not realize they've hit the cap until they try to add a student
- No in-app upgrade path (must contact sales)

### Risks

- **Gaming the System**: Schools may not remove inactive students. Mitigation: automated archival after 2 inactive academic years.
- **Mid-Year Cap Hit**: Frustration for schools hitting cap mid-year. Mitigation: clear email communication about upgrade options.

## Alternatives Considered

1. **Hard Block**: Reject all operations at cap. Rejected due to trust destruction.
2. **Grace Period**: Allow temporary over-cap. Rejected due to billing complexity.
3. **In-App Upsell**: Show upgrade prompts at cap. Rejected due to UX concerns (hidden module gating).

## Related

- ADR-0001: Soft-block student cap enforcement (original decision)
- ADR-0009: Hidden module gating
- school-erp-foundation change
