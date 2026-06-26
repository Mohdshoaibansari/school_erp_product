## Proposal: Audit Logging, Notifications, Communication

### Summary
Implement three support services that provide cross-cutting concerns for the School ERP:
1. **Audit Service** — Immutable, append-only audit trail for every significant action
2. **Simple Notifications Service** — Email-only notification delivery with templates
3. **Simple Communication Service** — Direct teacher-parent messaging

### Motivation
These services enable compliance (audit logging), user communication (notifications), and parent-teacher interaction (messaging).

### Scope
- Audit logs with configurable retention (7 years for critical, 90 days for routine)
- Email notification delivery with template rendering
- Teacher-parent conversations with in-app notifications
- All services consumed via library import, not HTTP

### Dependencies
- Requires completed kernel services (Tenant, Institution, Users, Auth, AuthZ)
- Required by business modules for audit trails and notifications
