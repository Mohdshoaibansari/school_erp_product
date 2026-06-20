# School ERP Platform — Phase 1 Architecture & Development Guide

> **Version:** 1.0  
> **Date:** 2026-06-20  
> **Purpose:** Complete reference for Phase 1 implementation. Covers architecture, tech stack, platform capabilities, business modules, and development patterns.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tech Stack Decisions](#2-tech-stack-decisions)
3. [Platform Layers](#3-platform-layers)
4. [Phase 1 Scope](#4-phase-1-scope)
5. [Kernel Capabilities](#5-kernel-capabilities)
6. [Service Capabilities](#6-service-capabilities)
7. [Business Modules](#7-business-modules)
8. [Development Patterns](#8-development-patterns)
9. [Database Design](#9-database-design)
10. [API Design](#10-api-design)
11. [Project Structure](#11-project-structure)

---

## 1. Architecture Overview

### Core Philosophy: Thin Agent, Thick Service

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                         │
│                                                                     │
│   ┌──────────────────────┐              ┌──────────────────────┐   │
│   │   Expo (React Native)│              │  Future: Mobile App  │   │
│   │   Universal App      │              │  (Same codebase)     │   │
│   └──────────┬───────────┘              └──────────┬───────────┘   │
│              │                                      │               │
└──────────────┼──────────────────────────────────────┼───────────────┘
               │                                      │
               ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                   │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │                    Node.js Backend                            │ │
│   │                    (Express)                                  │ │
│   │                                                               │ │
│   │   ┌─────────────────────────────────────────────────────┐   │ │
│   │   │              Business Modules                        │   │ │
│   │   │   Students    │  Attendance  │  Fees                │   │ │
│   │   └─────────────────────────────────────────────────────┘   │ │
│   │                           │                                  │ │
│   │                           │ calls via library                │ │
│   │                           ▼                                  │ │
│   │   ┌─────────────────────────────────────────────────────┐   │ │
│   │   │           Platform Capabilities                      │   │ │
│   │   │   Kernel + Services (see Section 3)                  │   │ │
│   │   └─────────────────────────────────────────────────────┘   │ │
│   │                                                               │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                  │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │                    PostgreSQL                                 │ │
│   │                    Row-level tenancy (tenant_id)              │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

               ▲
               │ HTTP calls to service methods
               │
┌─────────────────────────────────────────────────────────────────────┐
│                    FUTURE: AGENT LAYER (Phase 2+)                    │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │              Python LangGraph Orchestrator                    │ │
│   │              Calls Node.js API endpoints                      │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Platform capabilities are infrastructure** — They enable the system to function
2. **Business modules are the product** — They deliver value to customers
3. **Both are services** — Same technical structure, different architectural role
4. **Agents call services** — AI layer is thin, business logic stays in services

---

## 2. Tech Stack Decisions

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Expo (React Native) | Universal app: web + iOS + Android from single codebase |
| **Backend** | Node.js (TypeScript) | Reusable by AI agents, TypeScript throughout |
| **HTTP Framework** | Express | Largest ecosystem, most middleware, easiest to learn |
| **Database** | PostgreSQL | Robust, JSON support, row-level security capable |
| **ORM** | Prisma or Drizzle | Type-safe, migration support |
| **Validation** | Zod | Shared validation between frontend and backend |
| **Auth** | JWT + Refresh tokens | Stateless, works for web + agents |
| **Styling** | NativeWind | Tailwind for React Native |
| **State Management** | Zustand (UI) + TanStack Query (server) | Separation of concerns |
| **Forms** | React Hook Form + Zod | Type-safe form validation |
| **AI Agents** | Python LangGraph (future) | Calls Node.js API, thin orchestrator |

### Multi-Tenancy Strategy

- **Phase 1**: Row-level isolation (`tenant_id` column on every table)
- **Future**: Document migration path to schema-per-tenant when scale demands
- **Enforcement**: Application-level via middleware + Prisma global filters

---

## 3. Platform Layers

The platform has three distinct layers with different purposes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   LAYER 1: KERNEL (Foundation)                                      │
│   ═══════════════════════════                                       │
│   • Must exist before anything else                                 │
│   • Every other layer depends on these                              │
│   • No dependencies on other custom code                            │
│                                                                     │
│   Capabilities:                                                     │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│   │ Tenant  │ │ Users   │ │  Auth   │ │AuthZ    │ │Academic │    │
│   │ C-01    │ │ C-02    │ │ C-03    │ │ C-04    │ │ C-05    │    │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│   ┌─────────┐                                                       │
│   │ Config  │                                                       │
│   │ C-08    │                                                       │
│   └─────────┘                                                       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   LAYER 2: SERVICES (Platform Capabilities)                         │
│   ═════════════════════════════════════════                         │
│   • Built after Layer 1                                             │
│   • Depend on Layer 1                                               │
│   • Most business modules depend on these                           │
│   • Could operate without them (degraded)                           │
│                                                                     │
│   Capabilities:                                                     │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│   │Relation │ │Notif    │ │Audit    │ │Code Gen │ │Address  │    │
│   │ C-06    │ │ C-09    │ │ C-11    │ │ C-12    │ │ C-13    │    │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│   ┌─────────┐ ┌─────────┐                                           │
│   │Document │ │Integrat │                                           │
│   │ C-14    │ │ C-24    │                                           │
│   └─────────┘ └─────────┘                                           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   LAYER 3: BUSINESS MODULES                                         │
│   ═════════════════════════                                         │
│   • Built after Layer 1 + 2                                         │
│   • Depend on Layer 1 + 2                                           │
│   • This is what customers pay for                                  │
│   • Expose HTTP APIs for frontend/mobile/agents                     │
│                                                                     │
│   Modules:                                                          │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │
│   │  Students   │ │ Attendance  │ │    Fees     │                  │
│   └─────────────┘ └─────────────┘ └─────────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Distinction

| Aspect | Layer 1 (Kernel) | Layer 2 (Services) | Layer 3 (Modules) |
|---|---|---|---|
| **Purpose** | Foundation | Cross-cutting concerns | Business workflows |
| **Dependency** | None (base) | Depends on Layer 1 | Depends on Layer 1 + 2 |
| **Criticality** | Must exist first | Can be added later | Revenue generating |
| **Consumed via** | Library import | Library import | HTTP API |
| **Has own tables** | Yes | Yes | Yes |
| **Exposes HTTP** | Admin only | Admin only | Yes (main API) |

---

## 4. Phase 1 Scope

### Phase 1A: Foundation (Weeks 1-3)

Build first. Nothing works without these.

| Capability | ID | Description |
|---|---|---|
| Tenant & Institution | C-01 | Multi-tenant root, institutions |
| Identity & Users | C-02 | Unified user model, profiles |
| Authentication | C-03 | Email/password, JWT, OTP |
| Authorization | C-04 | RBAC with predefined roles |
| Academic Structure | C-05 | Years, terms, grades, classes |
| Configuration | C-08 | Key-value config, feature flags |

### Phase 1B: Students Module (Weeks 4-5)

| Capability | ID | Description |
|---|---|---|
| Relationships | C-06 | Student-parent links |
| Audit | C-11 | Basic audit trail |
| Code Generation | C-12 | Student ID generation |
| Addresses | C-13 | Structured addresses |
| Documents | C-14 | File upload/download |
| **Students Module** | — | CRUD, enrollment, parent linking |

### Phase 1C: Attendance Module (Weeks 6-7)

| Capability | ID | Description |
|---|---|---|
| Notifications | C-09 | Email notifications |
| **Attendance Module** | — | Daily mark, reports, alerts |

### Phase 1D: Fees Module (Weeks 8-10)

| Capability | ID | Description |
|---|---|---|
| Integration | C-24 | Payment gateway abstraction |
| **Fees Module** | — | Structure, assessment, collection |

### Phase 1E: Polish (Weeks 11-12)

- Integration testing
- Frontend polish
- API documentation
- Deployment setup

---

## 5. Kernel Capabilities

Kernel capabilities are the foundation. They are structured as services with their own database tables, repositories, and internal logic. They are consumed via library import (dependency injection).

### C-01: Tenant & Institution Management

**Purpose**: Root of multi-tenant system. Every other capability operates within a tenant context.

**Entities**:
- `tenants` — Customer organizations
- `institutions` — Schools within a tenant
- `org_units` — Administrative departments

**Public API**:
```
tenant.create(data)
tenant.get(id)
tenant.list(filters)
tenant.update(id, data)
institution.create(tenantId, data)
institution.get(id)
```

**Key Rules**:
- Every Institution belongs to exactly one Client
- Clients may own 1..N Institutions
- Institutions are lifecycle-managed, never deleted
- `tenant_id` must be on EVERY table in the system

---

### C-02: Identity & User Management

**Purpose**: Unified identity model. A person has exactly one identity regardless of how many institutions or roles they hold.

**Entities**:
- `users` — Platform identity
- `user_profiles` — Name, contact, photo, DOB
- `user_institutions` — User ↔ Institution ↔ Role mapping
- `user_identifiers` — Student ID, Employee ID (institution-scoped)

**Public API**:
```
users.create(data)
users.get(id)
users.getByEmail(email)
users.list(filters)
users.update(id, data)
users.assignToInstitution(userId, institutionId, role)
```

**Key Rules**:
- A user belongs to a Client first, then to one or more Institutions
- Role assignment is per-institution, not global
- User identifiers are institution-scoped

---

### C-03: Authentication

**Purpose**: Centralized identity verification. Single gateway for all users.

**Entities**:
- `login_attempts` — Audit record of every login
- `sessions` — Active sessions with expiry
- `otp_codes` — One-time passwords

**Public API**:
```
auth.login(email, password)
auth.loginWithOTP(email)
auth.verifyOTP(email, code)
auth.refreshToken(refreshToken)
auth.logout(token)
```

**Key Rules**:
- Centralized — no module implements its own login
- Client-aware — login identifies both user and client context
- Brute-force protection — account lockout after configurable failed attempts

---

### C-04: Authorization

**Purpose**: Centralized access control. No module implements its own permission system.

**Entities**:
- `roles` — Named collections of permissions
- `permissions` — Granular actions (e.g., `attendance.mark`)
- `role_permissions` — Role ↔ Permission mapping

**Public API**:
```
authz.check(userId, permission, scope)
authz.require(userId, permission, scope)  // throws if denied
authz.getUserPermissions(userId)
authz.getUserRoles(userId, institutionId)
authz.assignRole(userId, roleId, scope)
```

**Predefined Roles (Phase 1)**:
- Director (all permissions)
- Principal (institution-wide)
- Teacher (class-scoped)
- Parent (child-scoped)
- Student (self-scoped)

---

### C-05: Academic Structure

**Purpose**: Configurable academic model for different institution types.

**Entities**:
- `academic_years` — Academic cycle (e.g., 2025-2026)
- `terms` — Academic subdivisions
- `grades` — Grade levels (1-12 for schools)
- `classes` — Class groups (e.g., 10A, 10B)
- `sections` — Sections within classes
- `subjects` — Academic subjects

**Public API**:
```
academic.getCurrentYear(institutionId)
academic.getCurrentTerm(institutionId, yearId)
academic.getGrades(institutionId)
academic.getClasses(institutionId, gradeId)
academic.getSubjects(institutionId, classId)
```

**Key Rules**:
- Academic structures are configurable per InstitutionType
- No module defines its own grade/class/subject model

---

### C-08: Configuration Framework

**Purpose**: Runtime-configurable behavior without code changes.

**Entities**:
- `config_keys` — Named settings with typed values
- `config_values` — Values at specific scope levels
- `feature_toggles` — Enable/disable features

**Public API**:
```
config.get(key, scope)
config.set(key, value, scope)
config.getFeatureFlag(flag, scope)
```

**Scopes** (with inheritance):
```
Platform (Global Defaults)
  └── Client Overrides
       └── Institution Overrides
```

---

## 6. Service Capabilities

Service capabilities provide cross-cutting concerns. They are structured identically to kernel capabilities but are not foundational.

### C-06: Relationship Management

**Purpose**: Own the relationships between people. Single source of truth for parent-student links.

**Entities**:
- `relationships` — Typed connections between users
- `relationship_types` — Mother, Father, Guardian, etc.
- `contact_roles` — PrimaryGuardian, FinancialResponsible, EmergencyContact

**Public API**:
```
relationships.getParents(studentId)
relationships.getStudents(parentId)
relationships.addRelationship(data)
relationships.isParent(userId, studentId)
relationships.getEmergencyContacts(studentId)
```

**Key Rules**:
- Relationship types are configurable
- A student may have multiple guardians with different ContactRoles
- ContactRoles are separate from RelationshipType

---

### C-09: Notification Framework

**Purpose**: Centralized notification delivery. No module sends its own notifications directly.

**Entities**:
- `notification_templates` — Reusable templates with variables
- `notification_deliveries` — Delivery attempts and status
- `user_notification_preferences` — Per-user channel preferences

**Public API**:
```
notification.send({
  recipients: [userId1, userId2],
  template: 'student-absent',
  channels: ['email', 'in-app'],
  data: { studentName: 'Ali', date: '2025-06-18' }
})
notification.getHistory(userId)
notification.markAsRead(notificationId)
```

**Internal Flow**:
1. Look up template
2. Check user preferences
3. Route to channels (email, in-app)
4. Execute delivery
5. Track status

**Phase 1 Scope**: Email only. In-app, SMS, Push in Phase 2+.

---

### C-11: Audit & Observability

**Purpose**: Record who did what, when, where. Non-repudiable audit trail.

**Entities**:
- `audit_logs` — Immutable audit records

**Public API**:
```
audit.log({
  actorId: userId,
  action: 'attendance.marked',
  targetType: 'class',
  targetId: classId,
  metadata: { date, count }
})
audit.query(filters)
audit.getHistory(entityType, entityId)
```

**Key Rules**:
- Non-repudiable — records cannot be altered (append-only)
- Async logging — must not impact transaction performance
- Queryable — administrators can search and filter

---

### C-12: Code & Identifier Generation

**Purpose**: Centralized generation of human-readable identifiers.

**Entities**:
- `identifier_templates` — Configurable format patterns
- `sequence_counters` — Auto-incrementing counters per scope

**Public API**:
```
codeGeneration.generate('student', institutionId)
// Returns: "STU-2025-00001"

codeGeneration.generate('receipt', institutionId)
// Returns: "REC-20250620-001"
```

**Format**: `{PREFIX}-{YEAR}-{SEQUENCE}` (configurable per institution)

---

### C-13: Location & Address Management

**Purpose**: Centralized address management for all entities.

**Entities**:
- `addresses` — Structured address records
- `address_assignments` — Links addresses to entities

**Public API**:
```
addresses.create(data)
addresses.get(id)
addresses.getByEntity(entityType, entityId)
addresses.update(id, data)
```

**Key Rules**:
- An entity may have multiple addresses with type classification
- One primary address per type per entity
- Address history is preserved (versioned)

---

### C-14: Document Management

**Purpose**: Unified file and document storage.

**Entities**:
- `documents` — File records
- `document_types` — Photo, Certificate, Receipt, etc.

**Public API**:
```
documents.upload(file, metadata)
documents.download(id)
documents.delete(id)
documents.getByEntity(entityType, entityId)
```

**Phase 1 Scope**: Local filesystem storage. Cloud storage (S3/Azure) in Phase 2.

---

### C-24: Integration Framework

**Purpose**: Standardized approach for external system integrations.

**Entities**:
- `integration_providers` — Provider configurations
- `provider_credentials` — Encrypted API keys

**Public API**:
```
integration.getProvider(category)
// Returns: { name: 'stripe', type: 'payment_gateway' }

integration.executePayment(amount, metadata)
integration.sendEmail(to, subject, body)
```

**Phase 1 Scope**: Single payment gateway (Stripe/Razorpay), email (SMTP/SendGrid).

---

## 7. Business Modules

Business modules implement specific business workflows. They expose HTTP APIs and consume platform capabilities.

### Students Module

**Purpose**: Manage student records, enrollment, and parent linking.

**Entities**:
- `students` — Student records (extends users)
- `enrollments` — Student ↔ Class ↔ AcademicYear mapping

**API Endpoints**:
```
POST   /api/students              — Create student
GET    /api/students              — List students (with filters)
GET    /api/students/:id          — Get student details
PUT    /api/students/:id          — Update student
POST   /api/students/:id/enroll   — Enroll student in class
GET    /api/students/:id/parents  — Get linked parents
POST   /api/students/:id/parents  — Link parent
```

**Dependencies**:
- C-01 (Tenant) — tenant context
- C-02 (Users) — student IS a user
- C-04 (AuthZ) — who can manage students
- C-05 (Academic) — grades, classes
- C-06 (Relationships) — parent linking
- C-08 (Config) — student ID format
- C-11 (Audit) — change tracking
- C-12 (Code Gen) — student ID generation
- C-13 (Addresses) — student addresses
- C-14 (Documents) — student photos

---

### Attendance Module

**Purpose**: Track daily student attendance, notify parents of absences.

**Entities**:
- `attendance_records` — Daily attendance entries

**API Endpoints**:
```
POST   /api/attendance/mark       — Mark attendance (class-wise)
GET    /api/attendance/report     — Get attendance report
GET    /api/attendance/student/:id — Get student attendance history
```

**Dependencies**:
- C-01 (Tenant) — tenant context
- C-02 (Users) — students and teachers
- C-04 (AuthZ) — who can mark attendance
- C-05 (Academic) — classes, sections
- C-06 (Relationships) — find parents to notify
- C-08 (Config) — cutoff time, rules
- C-09 (Notifications) — absent alerts
- C-11 (Audit) — who marked what

---

### Fees Module

**Purpose**: Manage fee structures, collect payments, generate receipts.

**Entities**:
- `fee_structures` — Fee definitions (grade-wise, component-wise)
- `fee_assessments` — Fees assigned to students
- `fee_payments` — Payment records

**API Endpoints**:
```
POST   /api/fees/structures       — Define fee structure
GET    /api/fees/structures       — List fee structures
POST   /api/fees/assess           — Assess fees to students
GET    /api/fees/outstanding      — Get outstanding fees
POST   /api/fees/collect          — Record payment
GET    /api/fees/receipts/:id     — Get receipt
```

**Dependencies**:
- C-01 (Tenant) — tenant context
- C-02 (Users) — students being billed
- C-04 (AuthZ) — who can collect fees
- C-05 (Academic) — grade-wise structures
- C-06 (Relationships) — financial responsibility
- C-08 (Config) — fee rules
- C-09 (Notifications) — reminders, receipts
- C-11 (Audit) — financial audit trail
- C-12 (Code Gen) — receipt numbers
- C-13 (Addresses) — billing addresses
- C-14 (Documents) — receipt PDFs
- C-24 (Integration) — payment gateway

---

## 8. Development Patterns

### Pattern 1: Repository Layer

Repositories handle data access. All queries must include `tenant_id`.

```
class StudentRepository {
  constructor(private db: PrismaClient) {}

  async findById(id: string, tenantId: string) {
    return this.db.student.findFirst({
      where: { id, tenantId, deletedAt: null }
    });
  }

  async create(data: CreateStudentInput, tenantId: string) {
    return this.db.student.create({
      data: { ...data, tenantId }
    });
  }
}
```

**Rules**:
- Every query includes `tenantId`
- Soft deletes: `deletedAt IS NULL`
- No business logic in repositories
- Transactions handled at service level

---

### Pattern 2: Service Layer

Services contain business logic. They receive kernel capabilities via dependency injection.

```
class AttendanceService {
  constructor(
    private academic: AcademicService,      // C-05
    private config: ConfigurationService,   // C-08
    private relationships: RelationshipService, // C-06
    private notification: NotificationService, // C-09
    private audit: AuditService,            // C-11
    private repo: AttendanceRepository,     // Own repository
  ) {}

  async markAttendance(ctx: RequestContext, dto: MarkAttendanceDTO) {
    // 1. Get academic context from kernel
    const currentYear = await this.academic.getCurrentAcademicYear(ctx.institutionId);

    // 2. Check business rules from config
    const cutoffTime = await this.config.get('attendance.cutoff_time', {...});

    // 3. Execute business logic
    await this.repo.upsertMany(records);

    // 4. Post-execution hooks (kernel services)
    await this.notification.send({...});
    await this.audit.log({...});

    return { success: true, stats };
  }
}
```

**Rules**:
- Services call kernel capabilities for cross-cutting concerns
- Services never touch HTTP (request/response)
- Services never have authorization checks (done in middleware)
- Services return structured results

---

### Pattern 3: Controller Layer

Controllers are thin HTTP adapters. They validate input and delegate to services.

```
class AttendanceController {
  constructor(private service: AttendanceService) {}

  async markAttendance(req: Request, res: Response) {
    const dto = validate(MarkAttendanceSchema, req.body);
    const result = await this.service.markAttendance(req.context, dto);
    res.json(result);
  }
}
```

**Rules**:
- No business logic in controllers
- Input validation via Zod schemas
- Delegate to service immediately
- Return structured JSON

---

### Pattern 4: Route Definition

Routes wire dependencies and apply middleware.

```
function createAttendanceRoutes(deps) {
  const router = Router();
  const repo = new AttendanceRepository(deps.db);
  const service = new AttendanceService(deps.academic, deps.config, ...repo);
  const controller = new AttendanceController(service);

  router.post('/mark',
    authenticate,
    resolveTenant,
    authorize('attendance.mark'),
    controller.markAttendance
  );

  return router;
}
```

**Middleware Pipeline**:
1. `authenticate` — Verify JWT, attach user context
2. `resolveTenant` — Validate tenant, attach tenant context
3. `authorize(permission)` — Check permission for this action

---

### Pattern 5: RequestContext

Every request carries context from middleware.

```
interface RequestContext {
  userId: string;
  tenantId: string;
  institutionId: string;
  roles: string[];
  permissions: string[];
}
```

This context is passed to every service method.

---

## 9. Database Design

### Multi-Tenancy: Row-Level Isolation

Every table includes:
```
tenant_id    UUID    NOT NULL REFERENCES tenants(id)
created_at   TIMESTAMP DEFAULT NOW()
updated_at   TIMESTAMP DEFAULT NOW()
deleted_at   TIMESTAMP NULL  -- soft delete
```

### Prisma Global Filter

```typescript
// Apply tenant filter to ALL queries automatically
prisma.$use(async (params, next) => {
  if (params.model !== 'Tenant') {
    params.args.where = {
      ...params.args.where,
      tenantId: getCurrentTenantId(),
      deletedAt: null,
    };
  }
  return next(params);
});
```

### Schema Organization

```
prisma/
├── schema.prisma           — Main schema
├── migrations/             — Auto-generated migrations
└── seed.ts                 — Seed data
```

---

## 10. API Design

### RESTful Conventions

```
GET    /api/{resource}          — List (with filters)
POST   /api/{resource}          — Create
GET    /api/{resource}/:id      — Get by ID
PUT    /api/{resource}/:id      — Update
DELETE /api/{resource}/:id      — Soft delete
```

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [...]
  }
}
```

### Authentication

All endpoints require JWT in Authorization header:
```
Authorization: Bearer <access_token>
```

### Tenant Context

Institution context via header:
```
X-Institution-Id: <institution_uuid>
```

---

## 11. Project Structure

### Monorepo with Workspace Packages

```
school-erp/
├── package.json                    — Root workspace config
├── turbo.json                      — Turborepo (build orchestration)
├── pnpm-workspace.yaml             — pnpm workspaces
│
├── packages/                       — Shared packages
│   ├── database/                   — @school-erp/database
│   │   ├── prisma/                 —   Schema, migrations
│   │   └── src/
│   │       ├── client.ts           —   Prisma client with tenant middleware
│   │       └── index.ts
│   │
│   ├── kernel/                     — @school-erp/kernel
│   │   └── src/
│   │       ├── tenant/             —   C-01
│   │       ├── auth/               —   C-03
│   │       ├── users/              —   C-02
│   │       ├── authorization/      —   C-04
│   │       ├── academic/           —   C-05
│   │       ├── config/             —   C-08
│   │       ├── relationships/      —   C-06
│   │       ├── notifications/      —   C-09
│   │       ├── audit/              —   C-11
│   │       ├── code-generation/    —   C-12
│   │       ├── addresses/          —   C-13
│   │       ├── documents/          —   C-14
│   │       ├── integration/        —   C-24
│   │       └── index.ts            —   Exports all capabilities
│   │
│   └── shared/                     — @school-erp/shared
│       └── src/
│           ├── types/              —   Common types
│           ├── validation/         —   Zod schemas
│           ├── errors/             —   Error classes
│           └── utils/              —   Helpers
│
├── modules/                        — Business domain modules
│   ├── students/                   — @school-erp/students
│   │   └── src/
│   │       ├── student.service.ts
│   │       ├── student.repository.ts
│   │       ├── student.controller.ts
│   │       ├── student.routes.ts
│   │       ├── student.types.ts
│   │       └── index.ts
│   │
│   ├── attendance/                 — @school-erp/attendance
│   │   └── src/
│   │       ├── attendance.service.ts
│   │       ├── attendance.repository.ts
│   │       ├── attendance.controller.ts
│   │       ├── attendance.routes.ts
│   │       ├── attendance.types.ts
│   │       └── index.ts
│   │
│   └── fees/                       — @school-erp/fees
│       └── src/
│           ├── fee.service.ts
│           ├── fee.repository.ts
│           ├── fee.controller.ts
│           ├── fee.routes.ts
│           ├── fee.types.ts
│           └── index.ts
│
└── apps/
    └── api/                        — @school-erp/api (the actual server)
        └── src/
            ├── server.ts           — Express setup
            ├── middleware/          — Global middleware
            └── routes/             — Aggregates all module routes
```

### Package Dependencies

```
@api → @students, @attendance, @fees, @kernel

@students → @kernel, @database, @shared
@attendance → @kernel, @database, @shared
@fees → @kernel, @database, @shared

@kernel → @database, @shared
```

---

## Appendix: Capability Quick Reference

| ID | Capability | Layer | Phase | Purpose |
|---|---|---|---|---|
| C-01 | Tenant & Institution | Kernel | 1A | Multi-tenant root |
| C-02 | Identity & Users | Kernel | 1A | Unified user model |
| C-03 | Authentication | Kernel | 1A | Login, JWT, OTP |
| C-04 | Authorization | Kernel | 1A | RBAC, permissions |
| C-05 | Academic Structure | Kernel | 1A | Years, grades, classes |
| C-08 | Configuration | Kernel | 1A | Key-value config |
| C-06 | Relationships | Service | 1B | Parent-student links |
| C-09 | Notifications | Service | 1C | Email notifications |
| C-11 | Audit | Service | 1B | Audit trail |
| C-12 | Code Generation | Service | 1B | Student IDs, receipt numbers |
| C-13 | Addresses | Service | 1B | Structured addresses |
| C-14 | Documents | Service | 1B | File storage |
| C-24 | Integration | Service | 1D | Payment gateway |

---

> **End of Phase 1 Architecture Document**
