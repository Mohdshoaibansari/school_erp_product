# ADR-0009: Hidden Module Gating

## Status

Accepted

## Date

2026-06-26

## Context

The School ERP needs to gate paid modules for free-tier users without creating a negative user experience. The challenge is preventing access to paid features while maintaining a clean, functional product for free users.

## Decision

Implement hidden module gating:

1. **Invisibility**: Paid modules are completely invisible to free-tier users
2. **No Upsell**: No lock icons, upgrade banners, or disabled buttons
3. **Clean UX**: Free-tier users see a complete, functional product
4. **API Enforcement**: Module gating enforced at API level (not just frontend)

### Key Design Choices

- **Complete Invisibility**: Paid modules don't appear in navigation, menus, or API responses
- **No Disabled State**: Free users never see features they can't use
- **API-First Enforcement**: Frontend gating is UX; API gating is security
- **Out-of-Band Conversion**: Upsell handled via email, sales, marketing (not in-app)

## Consequences

### Positive

- Clean, uncluttered UX for free-tier users
- Free-tier users see a complete product (not a limited version)
- No frustration from seeing features they can't access
- Conversion strategy can evolve independently

### Negative

- Missed in-app conversion opportunities
- Users may not know paid features exist
- Requires out-of-band marketing/sales effort

### Risks

- **Direct URL Bypass**: Users may try to access paid features via direct URLs. Mitigation: API-level enforcement blocks access regardless of how request arrives.
- **Low Conversion**: Users may not upgrade if they don't know about paid features. Mitigation: email campaigns, sales outreach, documentation.

## Alternatives Considered

1. **Lock Icons**: Show locked features with upgrade prompts. Rejected due to UX concerns.
2. **Disabled Buttons**: Show but disable paid features. Rejected due to frustration.
3. **Upgrade Banners**: Show upgrade prompts throughout app. Rejected due to clutter.

## Related

- ADR-0002: Hidden module gating (original decision)
- ADR-0008: Soft-block student cap enforcement
- school-erp-foundation change
