## Context

The School ERP platform needs a lean but solid foundation. Earlier architecture documents listed 25 platform capabilities — many of which (Relationships, Addresses, Code Gen, Documents) are thin data models that don't warrant service abstractions. This change defines the true kernel services and simplifies the rest.

Pre-existing ADRs (0004: single multi-tenant deployment, row-level isolation) constrain this design: every table must include tenant_id, and all queries must filter by tenant context.

## Goals / Non-Goals

**Goals:**
- Implement 7 kernel services with real business logic (Tenant, Users, Auth, AuthZ, Subscription, Academic, Config+Rules)
- Implement support services: Calendar, Audit, Notifications, Communication
- Implement simple data tables: Relationships, Code Gen, Addresses, Documents
- All services consumed via library import (dependency injection), not HTTP
- Prisma ORM with tenant_id middleware on all queries

**Non-Goals:**
- No workflow engine (deferred)
- No full notification framework with channels, preferences, batching (deferred)
- No messaging beyond simple teacher-parent conversations
- No search, analytics, export, or integration frameworks (deferred)
- No per-module pricing (paid = all modules or free = limited modules)

## Decisions

### Decision 1: Services vs. Tables

Services get their own class with business logic. Tables are just Prisma models consumed by modules directly.

```
SERVICES (class + logic):         TABLES (Prisma model only):
─────────────────────────         ─────────────────────────
TenantService                     student_guardians
UserService                       identifier_sequences
AuthService                       addresses
AuthZService                      documents
AcademicService
ConfigService (incl. rules)
CalendarService
AuditService
NotificationService
CommunicationService
SubscriptionService
```

### Decision 2: Monorepo structure

```
packages/
├── database/       → Prisma schema + client with tenant middleware
├── kernel/         → All kernel service classes
│   └── src/
│       ├── tenant/
│       ├── auth/
│       ├── users/
│       ├── authorization/
│       ├── academic/
│       ├── config/
│       ├── calendar/
│       ├── audit/
│       ├── notifications/
│       ├── communication/
│       └── subscription/
├── shared/         → Types, validation schemas, errors, utils
```

### Decision 3: Config + Rules Engine

Config is typed key-value with scope inheritance (Platform → Client → Institution). Rules are a subset of config keys that modules evaluate for decision logic (attendance cutoff, late fee percent, leave approval threshold). No workflow engine — just structured data.

```
config.get("attendance.cutoff_time", { scope: institutionId })
→ returns { value: "09:30", scope: "institution" }
```

### Decision 4: Simple services first

Notifications: email-only. One template table, one delivery table. No preference management, no batching.
Communication: conversations + messages. Direct teacher-parent only. No groups, no announcements yet.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Tenant_id filter bugs could leak data | Prisma global middleware forces tenant_id on every query |
| Simple services outgrow simplicity | They can be refactored into proper services later without breaking callers (same import interface) |
| Config engine not expressive enough for complex rules | Can evolve rule definitions without changing the config interface |
| Calendar too basic for scheduling needs | Event types + recurrence can be added as needed — same table, more features |

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                         Express API Server                         │
│                                                                   │
│  Middleware: auth → resolveTenant → authorize → subscriptionCheck │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Kernel (library import)                   │ │
│  │                                                             │ │
│  │  Tenant  │  Users  │  Auth  │  AuthZ  │  Academic          │ │
│  │  Config  │  Cal.   │  Audit │  Notif  │  Comm.  │  Sub.    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Business Modules                            │ │
│  │  Students │ Attendance │ Fees │ Exams │ Homework │ etc.     │ │
│  │  (consume kernel via import, join tables directly)           │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                           │
┌───────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                  │
│                         tenant_id on every table                   │
└───────────────────────────────────────────────────────────────────┘
```
