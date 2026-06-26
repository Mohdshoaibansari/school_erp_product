## Context

The School ERP needs three support services that provide cross-cutting concerns:

1. **Audit Service** — Immutable, append-only audit trail for every significant action
2. **Simple Notifications Service** — Email-only notification delivery with templates
3. **Simple Communication Service** — Direct teacher-parent messaging

These services enable compliance (audit logging), user communication (notifications), and parent-teacher interaction (messaging).

### Existing ADRs in Force

- ADR-0004: Single multi-tenant deployment with row-level isolation — every table must include `tenant_id`

## Goals / Non-Goals

**Goals:**
- Implement immutable audit trail with configurable retention (7 years critical, 90 days routine)
- Implement email notification delivery with template rendering
- Implement teacher-parent conversations with in-app notifications
- All services consumed via library import, not HTTP

**Non-Goals:**
- No SMS or push notifications (future enhancement)
- No notification preferences or batching (future enhancement)
- No group messaging or announcements (future enhancement)
- No message search or full-text indexing (future enhancement)

## C4 Diagrams

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                      School ERP System                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Audit       │  │ Notification │  │ Communication│         │
│  │  Service     │  │ Service      │  │ Service      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                        │
│  audit_logs | templates | deliveries | conversations | messages │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Email Provider  │
                    │  (SMTP/SendGrid) │
                    └──────────────────┘
```

### Level 2: Container

```
┌─────────────────────────────────────────────────────────────────┐
│                    Express API Server                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Kernel Package                          │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Audit        │  │ Notification │  │ Communication│   │ │
│  │  │ Service      │  │ Service      │  │ Service      │   │ │
│  │  │              │  │              │  │              │   │ │
│  │  │ • log        │  │ • send       │  │ • sendMessage│   │ │
│  │  │ • query      │  │ • render     │  │ • getConvos  │   │ │
│  │  │ • archive    │  │ • deliver    │  │ • getMessages│   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Level 3: Component (Notification Service)

```
┌─────────────────────────────────────────────────────────────────┐
│                    NotificationService                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Methods                                                   │   │
│  │  • send(templateCode, recipientId, data)                 │   │
│  │  • render(template, data)                                │   │
│  │  • deliver(email, subject, body)                         │   │
│  │  • recordDelivery(status, error?)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PrismaClient                                              │   │
│  │  • NotificationTemplate                                   │   │
│  │  • NotificationDelivery                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ EmailProvider (SMTP/SendGrid)                             │   │
│  │  • sendEmail(to, subject, body)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: Append-Only Audit Logs

**Decision:** Audit logs are immutable and append-only. No updates or deletes allowed.

**Rationale:**
- Compliance requirement for tamper-proof audit trail
- Simplifies queries (no need to check deletedAt)
- Enables long-term retention

**Consequences:**
- No `deletedAt` field on audit_logs
- No update or delete methods in AuditService
- Retention managed by archival, not deletion

### Decision 2: Email-Only Notifications

**Decision:** Notifications are delivered via email only. No SMS or push notifications.

**Rationale:**
- Email is universal and reliable
- Reduces complexity (no SMS gateway, no push service)
- Can add SMS/push later without breaking changes

**Consequences:**
- NotificationService depends on email provider
- Email templates stored in database
- Delivery status tracked per notification

### Decision 3: Template-Based Rendering

**Decision:** Notifications use stored templates with variable substitution.

**Rationale:**
- Consistent messaging across the application
- Easy to update without code changes
- Supports multi-language (future)

**Consequences:**
- Template stored in `notification_templates` table
- Variables passed as JSON data
- Simple `{{variable}}` substitution syntax

### Decision 4: Conversation-Based Messaging

**Decision:** Communication uses conversation threads between two participants.

**Rationale:**
- Simple model for teacher-parent communication
- Easy to implement and query
- Supports message history

**Consequences:**
- Conversations have exactly 2 participants
- Messages linked to conversations
- In-app notifications for new messages

### Decision 5: Async Audit Pipeline

**Decision:** Audit logging uses a queue-based async pipeline to avoid blocking business logic.

**Rationale:**
- Audit writes should not slow down operations
- Queue absorbs spikes in audit volume
- Failed audit writes don't crash business operations

**Consequences:**
- AuditService.log() returns immediately
- Background worker processes queue
- Failed writes are retried

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Audit log volume grows unbounded | Configurable retention, archival |
| Email delivery failures | Retry with exponential backoff, status tracking |
| Conversation privacy | Strict tenant isolation, no cross-tenant access |
| Template injection attacks | Sanitize template variables |

## Open Questions

1. Should audit logs support file attachments? (Future: screenshots, documents)
2. Should notifications support HTML templates? (Future: rich formatting)
3. Should conversations support file sharing? (Future: document exchange)
