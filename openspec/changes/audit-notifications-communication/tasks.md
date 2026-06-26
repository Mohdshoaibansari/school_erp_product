## 1. Audit Service (C-11)

- [ ] 1.1 Define Prisma model: audit_logs (append-only)
- [ ] 1.2 Implement AuditService: log, query with filters
- [ ] 1.3 Implement async audit pipeline (queue-based, non-blocking)

## 2. Simple Notifications Service (C-09)

- [ ] 2.1 Define Prisma models: notification_templates, notification_deliveries
- [ ] 2.2 Implement NotificationService: send with template rendering + email delivery
- [ ] 2.3 Configure email provider (SMTP/SendGrid)

## 3. Simple Communication Service (C-10)

- [ ] 3.1 Define Prisma models: conversations, messages, conversation_participants
- [ ] 3.2 Implement CommunicationService: sendMessage, getConversation, getMessages
- [ ] 3.3 Scope messaging to teacher-parent within an institution
