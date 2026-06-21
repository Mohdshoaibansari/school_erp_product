## 1. Project Setup

- [ ] 1.1 Initialize pnpm workspace with monorepo structure (packages/database, packages/kernel, packages/shared, apps/api)
- [ ] 1.2 Set up TypeScript, ESLint, Prettier across all packages
- [ ] 1.3 Configure Prisma with PostgreSQL connection and tenant_id middleware
- [ ] 1.4 Create initial Prisma schema with base fields (tenant_id, created_at, updated_at, deleted_at)

## 2. Tenant & Institution Service (C-01)

- [ ] 2.1 Define Prisma models: tenants, institutions, org_units
- [ ] 2.2 Implement TenantService: create, get, list, update, lifecycle transitions
- [ ] 2.3 Implement InstitutionService: create, get, list, archive, reactivate
- [ ] 2.4 Implement Prisma middleware that auto-filters tenant_id on all queries

## 3. Identity & Users Service (C-02)

- [ ] 3.1 Define Prisma models: users, user_profiles, user_institutions, user_identifiers
- [ ] 3.2 Implement UserService: create, get, getByEmail, list, update, assignToInstitution
- [ ] 3.3 Implement user lifecycle: invited → active → suspended → archived
- [ ] 3.4 Implement user profile management

## 4. Authentication Service (C-03)

- [ ] 4.1 Implement email/password login with Argon2id hashing
- [ ] 4.2 Implement JWT access token + refresh token generation
- [ ] 4.3 Implement OTP-based passwordless login via email
- [ ] 4.4 Implement rate limiting: account lockout after configurable failed attempts

## 5. Authorization Service (C-04)

- [ ] 5.1 Define Prisma models: roles, permissions, role_permissions, role_assignments
- [ ] 5.2 Implement AuthZService: check, require, getUserPermissions, assignRole
- [ ] 5.3 Define predefined roles: Director, Principal, Teacher, Parent, Student
- [ ] 5.4 Implement scope resolution (institution, grade, class level)

## 6. Subscription Service (C-07)

- [ ] 6.1 Define Prisma models: subscription_tiers, module_entitlements
- [ ] 6.2 Implement SubscriptionService: getTier, getAvailableModules, checkStudentCap
- [ ] 6.3 Define free tier: 100 student cap, 3 modules (Students, Attendance, Fees)
- [ ] 6.4 Define paid tier: unlimited students, all modules
- [ ] 6.5 Implement entitlement middleware helper for module gating

## 7. Academic Structure Service (C-05)

- [ ] 7.1 Define Prisma models: academic_years, terms, grades, classes, sections, subjects
- [ ] 7.2 Implement AcademicService: getCurrentYear, getCurrentTerm, getGrades, getClasses
- [ ] 7.3 Implement class management within grade hierarchy

## 8. Config & Rules Engine (C-08)

- [ ] 8.1 Define Prisma models: config_keys, config_values with typed values
- [ ] 8.2 Implement ConfigService: get, set with scope inheritance (platform → client → institution)
- [ ] 8.3 Implement rule evaluation: config keys consumable by modules for decision logic
- [ ] 8.4 Implement config change audit trail

## 9. Calendar Service

- [ ] 9.1 Define Prisma model: calendar_events with date, type, label
- [ ] 9.2 Implement CalendarService: getToday, getDayType, isHoliday, getEventsInRange
- [ ] 9.3 Support event types: school_day, holiday, exam_day, event

## 10. Audit Service (C-11)

- [ ] 10.1 Define Prisma model: audit_logs (append-only)
- [ ] 10.2 Implement AuditService: log, query with filters
- [ ] 10.3 Implement async audit pipeline (queue-based, non-blocking)

## 11. Simple Notifications Service (C-09)

- [ ] 11.1 Define Prisma models: notification_templates, notification_deliveries
- [ ] 11.2 Implement NotificationService: send with template rendering + email delivery
- [ ] 11.3 Configure email provider (SMTP/SendGrid)

## 12. Simple Communication Service (C-10)

- [ ] 12.1 Define Prisma models: conversations, messages, conversation_participants
- [ ] 12.2 Implement CommunicationService: sendMessage, getConversation, getMessages
- [ ] 12.3 Scope messaging to teacher-parent within an institution

## 13. Simple Data Tables

- [ ] 13.1 Define Prisma model: student_guardians with relationship type and contact role
- [ ] 13.2 Define Prisma model: identifier_sequences for atomic ID generation
- [ ] 13.3 Define Prisma model: addresses with entity FK and type classification
- [ ] 13.4 Define Prisma model: documents with file metadata and storage abstraction
- [ ] 13.5 Implement IdentifierService: generate with per-institution, per-year sequence logic

## 14. Integration & Validation

- [ ] 14.1 Write integration tests covering all kernel services
- [ ] 14.2 Run `openspec validate kernel-foundation --type change --strict`
