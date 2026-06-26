## Why

The School ERP needs three support services that provide cross-cutting concerns:

1. **Audit Service** — Immutable, append-only audit trail for every significant action
2. **Simple Notifications Service** — Email-only notification delivery with templates
3. **Simple Communication Service** — Direct teacher-parent messaging

Without these services, the system cannot track compliance (audit), communicate with users (notifications), or enable parent-teacher interaction (messaging).

## What Changes

- Implement immutable audit trail with configurable retention (7 years critical, 90 days routine)
- Implement email notification delivery with template rendering
- Implement teacher-parent conversations with in-app notifications
- All services consumed via library import, not HTTP

## Capabilities

### New Capabilities

- `audit-logging`: Immutable, append-only audit trail for every significant action
- `simple-notifications`: Email-only notification delivery with templates
- `simple-communication`: Direct teacher-parent messaging with in-app notifications

### Modified Capabilities

- None

## Impact

- **Packages affected**: `packages/database/prisma/schema.prisma`, `packages/kernel/src/audit/`, `packages/kernel/src/notifications/`, `packages/kernel/src/communication/`
- **Dependencies**: Requires completed kernel services (Tenant, Institution, Users, Auth, AuthZ)
- **Required by**: All business modules (for audit trails and notifications)
- **Database**: New tables for audit_logs, notification_templates, notification_deliveries, conversations, messages
- **API**: New endpoints for audit queries, notification sending, messaging
