# Shared Platform Capabilities — Definitive Reference

> **Status:** Final  
> **Version:** 3.0  
> **Last Updated:** 2026-06-07  
> **Author:** School ERP Architecture Expert  
> **Purpose:** Define every shared platform capability that business modules must consume. No module may duplicate, bypass, or redefine these capabilities.  
> **Derived From:**  
> - `Functional_Requirement.md` — Full capability catalog  
> - `School_ERP_Architecture_v1.md` — Architecture principles & decisions  
> - `Shared_Platform_Capabilities.md` — Initial capability definitions  
> - `StartUp_Strategy.md` — Phased delivery philosophy  
> - Gap analysis against real-world School ERP requirements  
>
> **Cross-References:**  
> - [Architecture v1](../architecture/architecture-v1.md) — Tenant model, data isolation  
> - [Functional Requirements](../requirements/functional-requirements.md) — Full module catalog  
> - [Startup Strategy](../strategy/startup-strategy.md) — Phased delivery plan  
> - [Document Template](../reference/document-template.md) — Formatting standards  

---

## Table of Contents

**Part I — Foundation**
- [1. What Are Shared Platform Capabilities?](#1-what-are-shared-platform-capabilities)
- [2. Platform-First Principle](#2-platform-first-principle)
- [3. Capability Classification System](#3-capability-classification-system)

**Part II — Capability Inventory**
- [C-01: Tenant & Institution Management](#c-01-tenant--institution-management)
- [C-02: Identity & User Management](#c-02-identity--user-management)
- [C-03: Authentication](#c-03-authentication)
- [C-04: Authorization](#c-04-authorization)
- [C-05: Academic Structure Framework](#c-05-academic-structure-framework)
- [C-06: Relationship Management Framework](#c-06-relationship-management-framework)
- [C-07: Subscription Management](#c-07-subscription-management)
- [C-08: Configuration Framework](#c-08-configuration-framework)
- [C-09: Notification Framework](#c-09-notification-framework)
- [C-10: Communication Framework](#c-10-communication-framework)
- [C-11: Audit & Observability Framework](#c-11-audit--observability-framework)
- [C-12: Code & Identifier Generation Engine](#c-12-code--identifier-generation-engine)
- [C-13: Location & Address Management](#c-13-location--address-management)
- [C-14: Document Management Framework](#c-14-document-management-framework)
- [C-15: Workflow Framework](#c-15-workflow-framework)
- [C-16: Calendar & Scheduling Framework](#c-16-calendar--scheduling-framework)
- [C-17: Dynamic Group Management](#c-17-dynamic-group-management)
- [C-18: Bulk Operations Framework](#c-18-bulk-operations-framework)
- [C-19: Export & Document Generation Engine](#c-19-export--document-generation-engine)
- [C-20: Task & Reminder Framework](#c-20-task--reminder-framework)
- [C-21: Search Framework](#c-21-search-framework)
- [C-22: Analytics Framework & Data Pipeline](#c-22-analytics-framework--data-pipeline)
- [C-23: Billing Framework](#c-23-billing-framework)
- [C-24: Integration Framework](#c-24-integration-framework)
- [C-25: AI Framework](#c-25-ai-framework)

**Part III — Analysis**
- [3. Gap Analysis](#3-gap-analysis)
- [4. Dependency Map](#4-dependency-map)
- [5. Development Sequencing](#5-development-sequencing)
- [6. Platform Evolution Rules](#6-platform-evolution-rules)
- [7. Non-Negotiable Rules](#7-non-negotiable-rules)

**Appendices**
- [A: Capability Classification Matrix](#appendix-a-capability-classification-matrix)
- [B: Module Dependency Matrix](#appendix-b-module-dependency-matrix)
- [C: Glossary](#appendix-c-glossary)

---

# Part I — Foundation

## 1. What Are Shared Platform Capabilities?

### 1.1 Definition

Shared platform capabilities are **foundational services** that:

| Attribute | Description |
|---|---|
| **Consumed by** | All present and future business modules |
| **Own** | A domain as the single source of truth |
| **Evolve** | Independently — improvements triggered by one module benefit all |
| **Cross-institution** | Designed to support schools, colleges, universities, and future types |

### 1.2 What They Are Not

Business modules implement **educational workflows**. Platform capabilities implement **infrastructure that all workflows share**.

| Business Module | → Consumes → | Platform Capability |
|---|---|---|
| Attendance | → | Tenant & Institution Management |
| Homework | → | Identity & User Management |
| Fees | → | Authentication |
| Exams & Grading | → | Authorization |
| Parent Communication | → | Academic Structure Framework |
| Lesson Planning | → | Subscription Management |
| Report Cards | → | Notification Framework |
| Timetable | → | Audit & Observability Framework |

### 1.3 Architectural Relationship

```
┌──────────────────────────────────────────────────────────────┐
│                     Business Modules                          │
│  Attendance  │  Homework  │  Fees  │  Exams  │  Timetable   │
│  Lesson Plan │ Transport  │ Leave  │ Events  │  ...          │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│                 Shared Platform Capabilities                  │
│  Tenant  │  Users  │  Auth  │  AuthZ  │  Academic  │  Rel.   │
│  Subscr. │  Config │  Notif │  Comm   │  Audit     │  Doc.   │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                       │
│  Database  │  Storage  │  Queue  │  Cache  │  Search Engine  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Platform-First Principle

**No business module may be built until the Platform Kernel exists.**

The **Platform Kernel** is the minimum set of capabilities that every business module requires:

| # | Capability | Why Required |
|---|---|---|
| 1 | C-01: Tenant & Institution Management | Root of all multi-tenant operations |
| 2 | C-08: Configuration Framework | Every capability needs configurable behavior |
| 3 | C-02: Identity & User Management | Who are the users? |
| 4 | C-03: Authentication | How do users log in? |
| 5 | C-04: Authorization | What can users do? |
| 6 | C-05: Academic Structure Framework | Grades, classes, subjects, terms |
| 7 | **C-06: Relationship Management** | Who is whose parent/guardian? |
| 8 | C-11: Audit & Observability Framework | Compliance and traceability |
| 9 | C-09: Notification Framework | How do we alert users? |
| 10 | C-10: Communication Framework | How do users message each other? |
| 11 | C-14: Document Management Framework | File storage and retrieval |
| 12 | C-07: Subscription Management | Which modules does the client have? |
| 13 | C-24: Integration Framework | External system connectivity |
| 14 | C-12: Code & Identifier Generation | Student IDs, receipt numbers |
| 15 | C-13: Location & Address Management | Addresses for students, schools |
| 16 | C-22: Analytics Framework (model) | Report readiness from day one |

---

## 3. Capability Classification System

Each capability is classified across four dimensions:

| Dimension | Values | Description |
|---|---|---|
| **Layer** | Kernel / Service / Pipeline | How foundational the capability is |
| **Criticality** | Critical / Important / Medium / Future | Impact if absent |
| **Phase** | 1 / 2 / 3 / 4+ / Future | When to build |
| **Institution Scope** | Agnostic / School-Optimized / Flexible | How tied to school model |

| Layer | Definition | Examples |
|---|---|---|
| **Kernel** | Every module requires it. Must exist before any business module. | Tenant, Users, Auth |
| **Service** | Most modules use it. Provides cross-cutting functionality. | Notification, Document |
| **Pipeline** | Data processing and reporting. Separated from transactional systems. | Analytics, Billing |

---

# Part II — Capability Inventory

---

## C-01: Tenant & Institution Management

> **Layer:** Kernel (C-01a infrastructure) + Business (C-01b domain) — see §5.1 for split  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** Every capability and every business module

### 1. Purpose

Provide multi-tenant capabilities for managing educational organizations. This is the **root of the platform** — every other capability and module operates within a tenant context.

### 2. Domain Ownership (Single Source of Truth)

This capability exclusively owns the following entities. No other module may duplicate or redefine them.

| Entity | Description | Owned By |
|---|---|---|
| **PlatformOwner** | The SaaS provider operating the platform | This capability |
| **Client** | A customer organization (school, trust, chain, group) | This capability |
| **ClientLifecycle** | Prospective → Active → Suspended → Archived → Terminated | This capability |
| **Institution** | An operational unit (school, college, university, institute) | This capability |
| **InstitutionType** | Determines the default OrgUnit structure template applied at institution creation. Clients may modify the structure after setup. | This capability |
| **InstitutionLifecycle** | Onboarding → Active → Inactive → Archived | This capability |
| **OrgUnit** | Hierarchy node (Faculty, Department, Division) | This capability |
| **OrgUnitHierarchy** | Parent-child relationships between OrgUnits | This capability |

### 3. Tenant Model

```
Platform Owner
  └── Client A ────────────────── Client B
       ├── Institution: School A1      └── Institution: College B1
       │     ├── OrgUnit: Science Dept       ├── OrgUnit: Computer Science
       │     └── OrgUnit: Math Dept          └── OrgUnit: Mathematics
       │
       ├── Institution: School A2
       └── Institution: College A3
```

### 4. Key Rules

1. **Every Institution belongs to exactly one Client.** No orphan institutions.
2. **Clients may own 1..N Institutions.** Multi-institution clients do not require tenant restructuring.
3. **InstitutionTypes are configurable**, not hardcoded. New types may be added without code changes.
4. **InstitutionType determines the default OrgUnit structure template** applied when an institution is created. The client may modify this structure after setup to suit their needs.
5. **InstitutionType does not drive runtime module behavior.** All modules (Attendance, Fees, Homework, etc.) operate identically regardless of institution type.
6. **Institutions are lifecycle-managed** (Active → Archived), never deleted. This preserves audit trail integrity.
7. **Institution ownership may only change** through an approved migration process.

### 5. Dependencies

| Dependency | Type | Rationale |
|---|---|---|
| C-01a (Tenant Identity Infrastructure) | Infrastructure | Subdomain resolution, TenantContext, tenant-aware repository base, AuditEmitter, TransferCoordinator — built first within C-01 |
| None (domain) | — | C-01b has no business-module dependencies beyond its own kernel infrastructure |

### 5.1 Infrastructure vs. Domain

C-01 is composed of two separately classified concerns:

| Sub-capability | ID | Layer | What it provides | Consumed by |
|---|---|---|---|---|
| Tenant Identity Infrastructure | C-01a | **Kernel** | `TenantContext` (request-scoped tenant identity), subdomain+JWT middleware (sets contextvar), `TenantAwareRepositoryBase` (auto-injects `client_id` into every query, returns DTOs), `AuditEmitter` Protocol (synchronous C-11 audit emission), `TransferCoordinator` Protocol (ownership-transfer boundary hooks for C-05/C-02/C-07/C-23/C-11) | Every business module — Attendance, Fees, Exams, and all future modules import these from `kernel/` |
| Tenant & Institution Domain | C-01b | **Business** | Client CRUD + lifecycle state machine, Institution CRUD + lifecycle + effective-state gating, OrgUnit hierarchy + cycle-prevented moves + recursive CTE, InstitutionType template materialization, ownership transfer workflow, D11 Casbin permission matrix | Only C-01's own domain workflows — no other module imports Client lifecycle transitions or OrgUnit move logic |

The infrastructure packages live under `kernel/` (flat: `kernel/repo_base.py`, `kernel/audit.py`, `kernel/transfer_coordinator.py`, alongside existing `kernel/tenant_context.py` and `kernel/middleware.py`). The domain logic lives under `business/tenant_institution/`. C-01a and C-01b share the same database migration (`001_c01_initial.py`) and are developed together, but the architectural split ensures future modules never import domain logic when they only need tenant identity infrastructure.

### 6. Startup Scope (Phase 1)

| Feature | Scope | Notes |
|---|---|---|
| Client registration & creation | ✅ Build | — |
| Institution creation | ✅ Build (School model) | — |
| InstitutionType configuration (add College) | 🔄 Phase 2 | Needed before onboarding any College |
| OrgUnit: administrative departments (flat) | ✅ Build | Accounts, HR, Transport, etc. |
| C-05: School academic structure (Grade→Class→Section) | ✅ Build | This is separate from OrgUnits |
| InstitutionType configuration (add University) | 🔄 Phase 3 | Deeper academic structure changes needed |
| Flexible multi-level OrgUnit (Faculty→Dept→Lab) | 🔄 Phase 3+ | Only needed for University hierarchies |

---

## C-02: Identity & User Management

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All business modules + Authentication, Authorization, Notification, Communication

### 1. Purpose

Provide a **unified identity model** for all people across all institution types. A person has exactly one identity regardless of how many institutions or roles they hold.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **User** | A person with a platform identity | This capability |
| **UserProfile** | Name, contact, photo, date of birth, gender, blood group | This capability |
| **UserCategory** | Classifiable group (Learner, AcademicStaff, AdminStaff, Executive) | This capability |
| **UserLifecycle** | Invited → Pending → Active → Suspended → Transferred → Archived | This capability |
| **UserIdentifier** | Student ID, Employee ID, Admission Number (typed, institution-scoped) | This capability |
| **RoleAssignment** | User + Role + Institution + Scope | This capability + Authorization |

### 3. User Categories (Configurable)

| Category | Phase 1 Examples | Future Examples |
|---|---|---|
| Learner | School Student | College Student, Trainee, Research Scholar |
| Academic Staff | Teacher | Lecturer, Professor, Visiting Faculty, Trainer |
| Academic Leadership | Principal, HOD | Dean, Vice Chancellor, Academic Director |
| Administrative Staff | Clerk, Accountant | Registrar, HR Officer |
| Executive Leadership | Director, Trustee | Chairman, Governing Board Member |

### 4. Institutional Assignment Model

```
Client A
  └── User: Rajesh Sharma
       ├── Institution: School A1 → Role: Teacher (Mathematics), HOD (Science)
       └── Institution: School A2 → Role: Teacher (Physics)
```

### 5. Key Rules

1. **A user belongs to a Client first**, then to one or more Institutions.
2. **Role assignment is per-institution**, not global.
3. **A user may hold multiple roles** within the same institution.
4. **User identifiers** (Student ID, Employee ID) are **institution-scoped** and generated by C-12.
5. **User lifecycle is traceable** — each state transition is audited.

### 6. Startup Scope (Phase 1)

| Feature | Scope | Notes |
|---|---|---|
| User creation (Student, Parent, Teacher, Staff, Principal) | ✅ Build | Basic profile fields |
| Role assignment (system-defined roles) | ✅ Build | Configurable role definition deferred |
| Institution assignment (single school) | ✅ Build | Multi-institution deferred |
| User lifecycle: Create → Activate → Deactivate | ✅ Build | Transfer and archive deferred |
| UserProfile with standard fields | ✅ Build | DOB, blood group, photo, contact |
| UserIdentifier (Student ID, Employee ID) | ✅ Build | Uses C-12 Code Generation |

---

## C-03: Authentication

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All modules — every authenticated action

### 1. Purpose

Centralized identity verification. **Single gateway** for all users across all clients. No module implements its own login.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **AuthenticationMethod** | Email/Password, Google SSO, Microsoft SSO, OTP | This capability |
| **IdentityProvider** | External IdP configuration (per client) | This capability |
| **Session** | Active session with expiry, refresh, device info | This capability |
| **LoginAttempt** | Audit record of every login attempt (success/failure) | This capability |
| **MfaConfig** | Multi-factor authentication settings (per user, per client) | This capability |

### 3. Supported Methods — Roadmap

| Method | Phase | Notes |
|---|---|---|
| Email + Password (Argon2id, rate-limited) | Phase 1 | Primary method |
| OTP via Email (passwordless) | Phase 1 | For parent convenience |
| OTP via SMS | Phase 2 | Requires SMS integration |
| Google SSO | Phase 2 | OAuth 2.0 / OpenID Connect |
| Microsoft SSO | Phase 2 | OAuth 2.0 / OpenID Connect |
| Apple Sign-In | Future | For iOS parent app |
| SAML | Future | For enterprise clients |
| LDAP | Future | For on-premise integration |

### 4. Client Identification Strategy

```
Primary:  Client-specific subdomain
          schoola.acmeplatform.com
          schoolb.acmeplatform.com

Fallback: Custom domain (future)
          attendance.schoola.com → CNAME → platform
```

### 5. Key Rules

1. **Centralized** — no module implements its own login.
2. **Client-aware** — login identifies both user identity and client context.
3. **Brute-force protection** — account lockout after configurable failed attempts.
4. **MFA-ready** — architecture supports adding MFA without refactoring.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Email + Password authentication | ✅ Build |
| Session management with refresh tokens | ✅ Build |
| Client subdomain routing | ✅ Build |
| Login attempt audit | ✅ Build |
| OTP via Email (passwordless option) | ✅ Build |
| Google SSO, Microsoft SSO | 🔄 Phase 2 |
| MFA | ✅ Plan architecture only |

### 7. 🔴 Gap Addressed from v2

The v2 document omitted OTP-based login (critical for parent users who forget passwords), login attempt audit trail (essential for security), and MFA readiness (increasingly required for student data protection). All three have been added.

---

## C-04: Authorization

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All modules — every action requires authorization check

### 1. Purpose

Centralized access control. **No module implements its own permission system.**

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Permission** | Granular action (e.g., `attendance.mark`, `homework.create`) | This capability |
| **Role** | Named collection of permissions (e.g., Teacher, Principal, Parent) | This capability |
| **RoleAssignment** | User + Role + Scope (which user, which role, where) | This capability |
| **Scope** | Organizational boundary (Institution, Grade, Class, Subject) | This capability |
| **Policy** | Conditional ABAC rules (e.g., "can edit only own homework") | This capability |
| **TemporaryRole** | Role with expiry (substitute teacher, exam invigilator) | This capability |

### 3. Authorization Model (RBAC + ABAC)

```
┌─────────────────────────────────────────┐
│           Authorization Decision          │
├─────────────────────────────────────────┤
│  [1] Who is the user?     (Identity)     │
│  [2] What role do they have?  (RBAC)     │
│  [3] Where are they acting?   (Scope)    │
│  [4] What entity? What context? (ABAC)   │
│  [5] Any applicable policies?  (ABAC)    │
│         →  Access GRANTED / DENIED       │
└─────────────────────────────────────────┘
```

### 4. Authorization Layers

| Layer | Evaluates | Example |
|---|---|---|
| Platform | Is user a platform admin? | Platform Owner managing subscriptions |
| Client | Does user belong to this client? | Cross-school Director |
| Institution | Is user assigned to this institution? | Teacher in School A |
| Org Unit | Is user assigned to this department? | HOD of Science Dept |
| Grade/Program | Does user's scope include this grade? | Grade-level coordinator |
| Class/Batch | Does user's scope include this class? | Class teacher |
| Subject/Course | Does user's scope include this subject? | Subject teacher |
| Context | Does user own the entity? | Teacher editing own homework |

### 5. Key Rules

1. **Authorization is centralized** — no module bypasses this framework.
2. **Permissions are evaluated dynamically** — combining role, scope, and policy.
3. **Cross-institution access must be explicitly granted** and must never cross client boundaries.
4. **Temporary roles** have expiry dates — auto-revoked after expiration.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Role-based access (Director, Principal, Teacher, Parent, Student) | ✅ Build |
| Institution-scoped permissions | ✅ Build |
| Basic context rules (ownership checks) | ✅ Build |
| Configurable roles | 🔄 Phase 2 |
| Temporary roles with expiry | 🔄 Phase 2 |
| ABAC Policy engine | 🔄 Phase 3 |

---

## C-05: Academic Structure Framework

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** School-Optimized (flexible model for future types)  
> **Consumed By:** Attendance, Homework, Exams, Timetable, Lesson Planning, Report Cards, Analytics

### 1. Purpose

Provide a **flexible, configurable academic model** that supports multiple institution types without hardcoding school-style hierarchy.

### 2. Domain Ownership

| Entity | School | College | University | Description |
|---|---|---|---|---|
| **AcademicYear** | ✅ | ✅ | ✅ | Academic cycle (Apr 2025–Mar 2026) |
| **Term** / **Semester** | ✅ Term | ✅ Semester | ✅ Semester | Academic sub-division |
| **GradeLevel** | ✅ Grade | — | — | Grade 1–12 (school-specific) |
| **Program** | — | ✅ Program | ✅ Program | B.Sc., B.Com., M.A. |
| **Class** / **Batch** | ✅ Class | ✅ Batch | ✅ Batch | 5A, Batch of 2026 |
| **Section** | ✅ Section | — | — | Section A, B (school-specific) |
| **Subject** / **Course** | ✅ Subject | ✅ Subject | ✅ Course | Mathematics, Physics |
| **SubjectGroup** | ✅ | ✅ | ✅ | Science group, Commerce group |
| **Elective** | ✅ | ✅ | ✅ | With capacity limits |
| **Room** / **Facility** | ✅ | ✅ | ✅ | Classrooms, labs, halls |
| **Building** | ✅ | ✅ | ✅ | Campus building |

### 3. School Hierarchy

```
AcademicYear 2025-2026
  └── Term 1
       └── Grade 10
            └── Class 10A ───── Class 10B
                 ├── Section A     ├── Section A
                 └── Section B     └── Section B
                      └── Subject: Mathematics
                      └── Subject: Science
                      └── Subject: English
```

### 4. Key Rules

1. **Academic structures are configurable per InstitutionType** — new types define their own hierarchy.
2. **No module defines its own grade/class/subject model** — all consume this framework.
3. **Electives have capacity constraints** — a subject can have max seats, triggering waitlist logic.

### 5. Startup Scope (Phase 1)

| Feature | Scope | Notes |
|---|---|---|
| AcademicYear, Term | ✅ Build | — |
| Grade, Class, Section | ✅ Build (School model) | — |
| Subject with SubjectGroup | ✅ Build | — |
| Room / Facility | ✅ Build | Required by Timetable |
| Semester, Program, Batch (College model) | 🔄 Phase 2 | Add when ready to onboard Colleges |
| Faculty → Program → Course (University model) | 🔄 Phase 3+ | Deeper hierarchy for Universities |

---

## C-06: Relationship Management Framework ★ NEW

> **Layer:** Kernel  
> **Criticality:** **Critical**  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** Attendance (absent alerts), Fees (billing), Communication (messaging), Health (emergency contacts), Transport (pickup), Exams (report cards), Events (consent)

### 1. Purpose

**Own the relationships between people in the system.** This is the single most common cross-cutting concern in any School ERP.

Without it, every module independently models who is whose parent, leading to:
- Inconsistent parent-child mappings across Attendance, Fees, Communication
- No support for complex family structures (divorced parents, shared custody, guardians)
- Duplicate data entry and maintenance
- No unified view of "who is responsible for this student"

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Relationship** | A typed connection between two users | This capability |
| **RelationshipType** | Configurable relationship classification (Mother, Father, Guardian, Sibling, EmergencyContact) | This capability |
| **ContactRole** | Responsibilities assigned within a relationship (PrimaryGuardian, FinancialResponsible, EmergencyContact, PickupAuthorized) | This capability |
| **GuardianRelationship** | Parent/guardian-specific attributes (hasCustody, livesWithStudent, communicationPreference) | This capability |
| **EmergencyContact** | Priority-ordered contacts with relationship context | This capability |

### 3. Relationship Model

```
                        Priya Sharma (Student)
                       /          |           \
                      /           |            \
              Anita Sharma    Rajesh Sharma   Sunita Devi
               (Mother)        (Father)      (Grandmother)
              Contact Roles:  Contact Roles:  Contact Role:
              • PrimaryGuardian • Guardian     • EmergencyContact
              • FinancialResp.  • Emergency    (Priority: 3)
              • EmergencyContact
```

### 4. Consumer Trace — Every Module Needs Relationships

| Module | Question It Asks of C-06 | Without C-06 |
|---|---|---|
| Attendance | Who to notify when student is absent? | Each module builds its own parent map |
| Fees | Who is financially responsible? | Duplicate guardian data in Fees module |
| Communication | Who receives parent messages? | Inconsistent parent lists |
| Health | Who to contact in emergency? | Emergency contacts scattered |
| Transport | Who can authorize pickup? | Transport builds its own authorization |
| Exams | Who receives report cards? | Report card delivery logic duplicated |
| Events | Who gives consent for field trips? | Consent management fragmented |

### 5. Key Rules

1. **Relationship types are configurable** — new types (Step-parent, Foster parent, Grandparent) can be added without code changes.
2. **A student may have multiple guardians** with different ContactRoles.
3. **ContactRoles are separate from RelationshipType** — a Guardian may or may not be FinancialResponsible.
4. **Relationships respect institution boundaries** — cross-institution linking requires explicit configuration.
5. **Emergency contacts are priority-ordered** and may include non-parent persons.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Student ↔ Parent/Guardian relationship (1:N) | ✅ Build |
| Relationship types: Mother, Father, Guardian | ✅ Build |
| Contact roles: PrimaryGuardian, Guardian, FinancialResponsible, EmergencyContact | ✅ Build |
| Emergency contact priority ordering | ✅ Build |
| Complex family structures (divorced, step-parents) | 🔄 Phase 2 |

---

## C-07: Subscription Management

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All business modules + Billing Framework

### 1. Purpose

Control **which modules and features** each client can access. Enables the SaaS business model.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Offering** | A subscribable product (module or feature pack) | This capability |
| **Subscription** | A client's entitlement to one or more offerings | This capability |
| **AddOn** | Optional enhancement (e.g., "Advanced Analytics") | This capability |
| **Trial** | Time-limited access with start/end dates | This capability |
| **FeatureFlag** | Fine-grained feature toggle within a module | This capability |

### 3. Subscription Model

```
Client A (School Chain)
  ├── Core Platform (always included)
  ├── Attendance Module (subscribed)
  ├── Homework Module (subscribed)
  ├── Fees Module (subscribed)
  └── AddOn: Advanced Analytics (subscribed)

Client B (Single School)
  ├── Core Platform (always included)
  └── Attendance Module (subscribed only)
```

### 4. Key Rules

1. **Core Platform** is always enabled for every client.
2. **Business modules are individually subscribable** — no unrelated module dependencies.
3. **Disabled modules are hidden and inaccessible** at all layers (UI, API, backend).
4. **FeatureFlags enable gradual rollout** within a module (e.g., beta features).
5. **Trials are configurable** per offering with duration limits.

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Module-level subscription (enable/disable per client) | ✅ Build |
| Trial support with configurable duration | ✅ Build |
| Feature flags | ✅ Build |
| Usage-based billing data | 🔄 Phase 2 |

---

## C-08: Configuration Framework

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All capabilities and modules

### 1. Purpose

Enable **runtime-configurable behavior** across the platform without code changes or redeployment.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **ConfigurationKey** | A named setting with typed value | This capability |
| **ConfigurationValue** | The value at a specific scope level | This capability |
| **ConfigurationScope** | Platform | Client | Institution | Module | This capability |
| **FeatureToggle** | Enable/disable named features | This capability |

### 3. Configuration Scopes (with Inheritance)

```
Platform (Global Defaults)   ← highest priority fallback
  └── Client Overrides       ← overrides platform defaults for a client
       └── Institution Overrides  ← overrides client defaults for an institution
            └── Module Overrides  ← overrides institution defaults for a module
```

### 4. Configuration Categories

| Category | Examples |
|---|---|
| **Business Rules** | Attendance cutoff time, late fee calculation, auto-approve leave under 3 days |
| **Display Settings** | Date format, timezone, language, number format |
| **Academic Settings** | Grading scale, pass percentage, term structure |
| **Notification Rules** | Which events trigger notifications, default channels |
| **Integration Settings** | API keys, webhook URLs, provider selection |

### 5. Key Rules

1. **Configuration changes must not require code deployment or application restart.**
2. **Typed values** with validation (string, number, boolean, JSON, date).
3. **Inheritance** — lower scopes inherit from higher scopes unless explicitly overridden.
4. **Audit trail** — every configuration change records who changed what and when.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Key-value configuration store | ✅ Build |
| Platform-level and institution-level scopes | ✅ Build |
| Feature toggles | ✅ Build |
| Configuration change audit | ✅ Build |
| Module-level scopes | 🔄 Phase 2 |

---

## C-09: Notification Framework

> **Layer:** Service  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All business modules

### 1. Purpose

Centralized notification delivery. **No module sends its own notifications directly.**

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **NotificationTemplate** | Reusable template with variables | This capability |
| **NotificationChannel** | InApp, Email, SMS, Push | This capability |
| **NotificationDelivery** | A single notification attempt | This capability |
| **DeliveryStatus** | Queued → Sent → Delivered → Read → Failed | This capability |
| **UserPreference** | Per-user channel and frequency preferences | This capability |
| **NotificationGroup** | Batched notifications for digest | This capability |
| **ScheduleRule** | Immediate / Daily digest / Weekly summary | This capability |

### 3. Channel Roadmap

| Channel | Phase | Use Case |
|---|---|---|
| In-App (notification center) | Phase 1 | All non-urgent notifications |
| Email (transactional) | Phase 1 | Homework alerts, fee receipts |
| Email (digest) | Phase 2 | Weekly attendance summary |
| SMS | Phase 2 | Urgent alerts, emergency |
| Push (Mobile) | Phase 3 | Requires mobile apps |
| WhatsApp | Future | High open-rate messages |
| Voice Call | Future | Emergency alerts |

### 4. Notification Flow

```
Business Module Event
  (e.g., homework.assigned)
       │
       ▼
Notification Framework
  ├── Resolve template: "New homework: {title} in {subject}"
  ├── Check user preferences: Parent → Email preferred
  ├── Select channels: Email + In-App
  ├── Apply batching rules (if digest)
  ├── Deliver via Email provider
  ├── Deliver In-App notification
  └── Record delivery status for audit
```

### 5. Key Rules

1. **All modules must use this framework** — individual notification implementations are prohibited.
2. **User preferences are respected** — a user who opts out of SMS does not receive SMS.
3. **Batching reduces notification fatigue** — configurable per module.
4. **Delivery status is trackable** for debugging and compliance.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| In-App notifications | ✅ Build |
| Email delivery (SMTP/SendGrid) | ✅ Build |
| Template support with variables | ✅ Build |
| User preference management | ✅ Build |
| SMS channel | 🔄 Phase 2 |
| Push notifications | 🔄 Phase 3 |

---

## C-10: Communication Framework

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** Parent Communication module, all person-to-person interactions

### 1. Purpose

Enable **structured, bidirectional communication** — distinct from one-way notifications. Includes messaging, announcements, and emergency alerts.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Conversation** | A thread of messages between participants | This capability |
| **Message** | A single communication within a conversation | This capability |
| **ConversationParticipant** | User + Role within a conversation | This capability |
| **Announcement** | One-to-many broadcast | This capability |
| **AnnouncementTarget** | Target audience definition (Grade 10 Parents, Class 5A) | This capability |
| **ReadReceipt** | Track who has read what | This capability |
| **Attachment** | File attached to a message (delegates to C-14) | This capability |

### 3. Communication Types

| Type | Direction | Participants | Examples |
|---|---|---|---|
| Direct Message | 1:1 | Teacher ↔ Parent | Student progress discussion |
| Group Message | 1:N | Teacher → Class Parents | Field trip information |
| Broadcast | 1:Many | Principal → All School Parents | Holiday announcement |
| Emergency Alert | 1:All | School → All | School closure, lockdown |
| Department Chat | M:N | Science Dept | Teacher collaboration |

### 4. Key Rules

1. **Communication is independent from individual modules** — a message about homework is still a communication.
2. **Notifications reference communications** — "You have a new message from the Principal" uses C-09.
3. **Communication respects institution boundaries** — cross-institution communication requires explicit permission.
4. **Announcements can target dynamic groups** — "All parents of Grade 10" uses Relationship Management (C-06) to resolve recipients.

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Direct teacher-parent messaging | ✅ Build |
| School announcements (broadcast) | ✅ Build |
| Conversation threads | ✅ Build |
| Announcement targeting by grade/class | ✅ Build |
| Group messaging for class parents | 🔄 Phase 2 |

---

## C-11: Audit & Observability Framework

> **Layer:** Kernel  
> **Criticality:** Critical  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** All modules — every significant action emits an audit event

### 1. Purpose

Record **who did what, when, where, and what changed.** Every significant action must be auditable and traceable. Audit records are non-repudiable.

### 2. Domain Ownership

| Field | Description | Owned By |
|---|---|---|
| **ActorId** | Who performed the action (User ID) | This capability |
| **ActorType** | User, System, API Key | This capability |
| **Action** | `attendance.marked`, `homework.created`, `fee.collected` | This capability |
| **TargetType** | Entity type (Student, Homework, FeeTransaction) | This capability |
| **TargetId** | Specific entity ID | This capability |
| **ClientId** | Client context | This capability |
| **InstitutionId** | Institution context | This capability |
| **AcademicYearId** | Academic year context | This capability |
| **Timestamp** | When the action occurred (UTC) | This capability |
| **Changeset** | Before/after values of changed fields | This capability |
| **Metadata** | IP address, user agent, device info | This capability |
| **CorrelationId** | Traceable ID across related events | This capability |

### 3. Audit Levels

| Level | Description | Examples | Retention |
|---|---|---|---|
| **Critical** | Security, compliance, financial | Login failure, role change, fee refund | 7 years |
| **Operational** | Business transactions | Attendance mark, homework submission | 3 years |
| **Activity** | Routine actions | Profile view, report download | 90 days |
| **Debug** | System tracing | API calls, background jobs | 30 days |

### 4. Key Rules

1. **Non-repudiable** — audit records cannot be altered or deleted (append-only store).
2. **Async logging** — audit must not impact transaction performance (queue-based).
3. **Queryable** — administrators can search and filter audit logs.
4. **Correlatable** — related events are traceable via CorrelationId.

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Basic audit trail for key actions | ✅ Build |
| Configurable retention per level | ✅ Build |
| Queryable audit log for admins | ✅ Build |
| Async audit pipeline | ✅ Build |

---

## C-12: Code & Identifier Generation Engine ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 1  
> **Institution Scope:** School-Optimized  
> **Consumed By:** User Management, Fees, Exams, Documents, Library, all modules that assign identifiers

### 1. Purpose

**Centralized generation of all human-readable identifiers.** Student IDs, Admission Numbers, Employee IDs, Receipt Numbers, Transaction References — every module needs them. Without a shared engine, each module generates its own with inconsistent formats and no centralized sequence control.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **IdentifierTemplate** | Configurable format pattern (`{INST}-{YEAR}-{SEQ:5}`) | This capability |
| **SequenceCounter** | Auto-incrementing counter per scope (per-institution, per-year) | This capability |
| **IdentifierScheme** | Defines prefix, separator, padding, suffix | This capability |
| **GeneratedIdentifier** | Record of every generated identifier (for audit) | This capability |

### 3. Identifier Format

```
{PREFIX}{SEPARATOR}{YEAR}{SEPARATOR}{SEQUENCE}
  STU    -       2025    -       00001

Examples:
  STU-2025-00001    (Student ID, year-based sequence)
  EMP-2025-0042     (Employee ID)
  REC-20250607-001  (Receipt with date-based sequence)
  ADM-25-0001       (Admission with short year)
```

### 4. Configurable Rules

| Rule | Options | Example |
|---|---|---|
| Prefix | Alphanumeric code | `STU`, `EMP`, `REC` |
| Year format | Full (`2025`) or short (`25`) | `2025` or `25` |
| Separator | `-`, `/`, none | `-` |
| Sequence padding | Digit width | `00001` (5 digits) |
| Scope | Per-institution, per-year, global | Reset counter each year |
| Check digit | Luhn, modulus, or none | Optional integrity check |

### 5. Key Rules

1. **ID formats are configurable per institution** — School A may use a different format from School B.
2. **Sequence generation is atomic** — no duplicates under concurrent access.
3. **Generated IDs are immutable** — once assigned, never changed.
4. **All generated IDs are recorded** in GeneratedIdentifier for audit.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Student ID generation | ✅ Build |
| Employee ID generation | ✅ Build |
| Per-institution format configuration | ✅ Build |
| Per-year sequence reset | ✅ Build |
| Receipt number format | ✅ Build |
| Check digit support | 🔄 Phase 2 |

---

## C-13: Location & Address Management ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** User Management, Transport, Fees, Tenant Management, Health, Compliance

### 1. Purpose

**Centralized address and location management.** Addresses are used everywhere — student home address, parent work address, school location, bus stops, staff residence. Without a shared service, every module invents its own address fields with no validation, no versioning, and no geocoding.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Address** | Structured address (line1, line2, city, state, postalCode, country) | This capability |
| **AddressType** | Home, Work, School, Billing, Emergency | This capability |
| **GeoLocation** | Latitude, longitude for mapping and routing | This capability |
| **LocationValidation** | Verification status of an address | This capability |
| **AddressAssignment** | Association between an address and an entity | This capability |
| **AddressPreference** | Primary, Secondary, Previous marking | This capability |

### 3. Address Model

```
User: Priya Sharma
  ├── Home Address (Primary)
  │     ├── 123, MG Road, Bangalore, 560001, Karnataka
  │     └── [Geocoded: 12.9716, 77.5946]
  ├── Previous Address (versioned)
  │     └── 45, Brigade Road, Bangalore, 560025
  └── Work Address (Parent's employer)
        └── 789, Whitefield, Bangalore, 560066

Institution: Sunshine School
  └── School Address
        └── 1st Cross, Indiranagar, Bangalore, 560038
```

### 4. Key Rules

1. **An entity may have multiple addresses** with type classification.
2. **One primary address per type** per entity.
3. **Address history is preserved** — changes are versioned, not overwritten.
4. **Address reuse is supported** — siblings share the same home address.

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Structured address fields (line1, line2, city, state, postalCode, country) | ✅ Build |
| Country/State/City reference data | ✅ Build |
| Multiple addresses per entity | ✅ Build |
| Primary address designation | ✅ Build |
| Address versioning | ✅ Build |
| Geocoding | 🔄 Phase 2 (when Transport requires it) |

---

## C-14: Document Management Framework

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** Homework (attachments), Student Management (photos, IDs), Fees (receipts), Exams (papers), Report Cards (PDF), Learning Content

### 1. Purpose

**Unified file and document storage.** No module manages files independently.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Document** | A file or document record | This capability |
| **DocumentType** | Photo, Certificate, ReportCard, Assignment, Receipt | This capability |
| **DocumentVersion** | Version tracking (overwrite creates new version) | This capability |
| **StorageProvider** | Storage backend (Local, S3, Azure Blob) | This capability |
| **DocumentAccess** | Who can view, download, edit | This capability + Authorization |
| **Thumbnail** | Auto-generated preview | This capability |
| **DocumentFolder** | Organizational folder structure | This capability |

### 3. Storage Abstraction

```
Module (Homework, Fees, etc.)
       │
       ▼
Document Framework (Unified API)
       │
       ├── Local Filesystem (Phase 1)
       ├── Amazon S3 (Phase 2)
       ├── Azure Blob Storage (Phase 2)
       └── Google Cloud Storage (Future)
```

### 4. Key Rules

1. **All file storage flows through this framework** — no module bypasses it.
2. **Access respects institution + authorization boundaries.**
3. **Storage provider is configurable** without application changes.
4. **Documents are versioned** — overwriting creates a new version.
5. **File type and size limits are configurable per DocumentType.**

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| File upload and download | ✅ Build |
| Institution-scoped storage | ✅ Build |
| Local filesystem storage | ✅ Build |
| Document type classification | ✅ Build |
| Cloud storage (S3/Azure) | 🔄 Phase 2 |

---

## C-15: Workflow Framework

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** Agnostic  
> **Consumed By:** Leave Management, Fee Management, Assessment, Lesson Planning, Admission

### 1. Purpose

Provide a **configurable approval and review workflow engine** used by multiple modules. Workflows are defined per module, executed by this framework.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **WorkflowTemplate** | Definable workflow (e.g., "Leave Approval — 2 steps") | This capability |
| **WorkflowInstance** | A running workflow for a specific item | This capability |
| **WorkflowStep** | A single stage (Pending → HOD Approval → Principal Approval) | This capability |
| **Approval** | Decision: Approved, Rejected, Pending, Rework | This capability |
| **EscalationRule** | Auto-escalate if no action within time limit | This capability |
| **WorkflowNotification** | Notification trigger configuration per step | This capability |

### 3. Key Rules

1. **Workflows are configurable per institution** — not hardcoded.
2. **The framework provides the engine; modules define workflow templates.**
3. **Notifications at each step use C-09 (Notification Framework).**
4. **Escalation rules are configurable per step with timeout.**

### 4. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| Workflow definition (DSL/config) | ✅ Build |
| Approval engine | ✅ Build |
| Escalation rules | ✅ Build |
| Notification integration (C-09) | ✅ Build |

---

## C-16: Calendar & Scheduling Framework ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** School-Optimized  
> **Consumed By:** Exams (schedules), Events, Attendance (holidays), Fees (due dates), Timetable, Communication (PTM)

### 1. Purpose

**Unified calendar and event management.** Schools run on calendars — academic calendars, exam schedules, events, fee due dates. Without a shared framework, each module manages dates independently, and scheduling conflicts go undetected.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **CalendarEvent** | A dated event with time, duration, location | This capability |
| **EventType** | Holiday, Exam, Event, Meeting, Deadline | This capability |
| **RecurrenceRule** | Daily, weekly, term-based repeating pattern | This capability |
| **Schedule** | A collection of events forming a timeline | This capability |
| **ConflictRule** | Rules for conflict detection and severity | This capability |
| **EventVisibility** | Public, School, Class, Private | This capability |

### 3. School Calendar Model

```
Academic Year 2025-2026
  ├── Term 1: June 1 – October 15
  │     ├── Holidays: Independence Day, Teacher's Day
  │     ├── Events: Sports Day (Aug 15), Science Fair (Sep 10)
  │     ├── Exams: Mid-Term (Sep 20-25)
  │     ├── Fees: Term Fee Due (June 15)
  │     └── PTM: Parent-Teacher Meeting (Oct 5)
  │
  └── Term 2: October 20 – March 31
        ├── Holidays: Diwali Break, Winter Break
        ├── Exams: Final Exam (Mar 1-15)
        └── Fees: Term Fee Due (Oct 25)
```

### 4. Conflict Detection

| Conflict Type | Severity |
|---|---|
| Exam scheduled on a holiday | Error |
| Two events at same venue simultaneously | Warning |
| Assignment deadline on exam day | Warning |
| Teacher assigned to two events simultaneously | Error |

### 5. Key Rules

1. **Calendar is the single source of truth** for all date-related operations.
2. **Attendance calculation references the calendar** — holidays don't count as absences.
3. **Events support visibility levels** — Public, Student-specific, Teacher-specific.

### 6. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| Event creation with date, time, type, location | ✅ Build |
| Academic calendar (term dates, holidays) | ✅ Build |
| Event visibility (school/public/class) | ✅ Build |
| Basic conflict detection | ✅ Build |
| Recurrence rules | 🔄 Phase 3 |
| Calendar export (iCal, Google) | 🔄 Phase 3 |

---

## C-17: Dynamic Group Management ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** Agnostic  
> **Consumed By:** Homework (project groups), Communication (group messaging), Transport (bus route groups), Events (club participation), Sports

### 1. Purpose

**Flexible, dynamic grouping** that cuts across the static academic structure. Schools need groups not tied to classes — remedial groups, sports teams, clubs, project groups, bus route groups.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Group** | A named collection with purpose | This capability |
| **GroupType** | Configurable: Remedial, Sports, Club, Project, Transport | This capability |
| **GroupMember** | User + Group + Role within group | This capability |
| **GroupRole** | Member, Leader, Coordinator, Coach | This capability |
| **GroupSchedule** | Meeting/activity schedule (optional) | This capability |

### 3. Group Types & Behavior

| GroupType | Cross-Class? | Temporary? | Examples |
|---|---|---|---|
| Remedial | ✅ Yes | ✅ Semester-based | "Math Remedial – Grade 5" |
| Sports | ✅ Yes | ✅ Year-based | "Football Team" |
| Club | ✅ Yes | ✅ Year-based | "Debate Club" |
| Project | ✅ Yes | ✅ Weeks-based | "Science Fair Group A" |
| Transport | ✅ Yes | ✅ Year-based | "Bus Route 7" |
| Interest | ✅ Yes | ✅ Ongoing | "Robotics Enthusiasts" |

### 4. Key Rules

1. **Groups are dynamic** — membership changes over time.
2. **Groups are not tied to academic structure** — a group may contain students from different classes/grades.
3. **Groups have typed roles** — not every member has the same permissions.
4. **Groups may be temporary with auto-expiry** — project groups dissolve after deadline.
5. **Group membership is auditable** — who joined, who left, when.

### 6. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| Group creation with type | ✅ Build |
| Member management (add, remove) | ✅ Build |
| Group roles (Member, Coordinator) | ✅ Build |
| Integration with Communication (group messaging) | ✅ Build |
| Auto-expiry for temporary groups | 🔄 Phase 3 |

---

## C-18: Bulk Operations Framework ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** School-Optimized  
> **Consumed By:** Student Management (promotions), Fees (bulk assessment), Communication (bulk messaging), Exams (marks entry), Reports (batch generation)

### 1. Purpose

**Standardized bulk operations.** Schools promote 200 students, send 500 fee reminders, generate 800 report cards. Every module needs bulk operations. Without a shared framework, each builds its own — inconsistent UI, no progress tracking, no rollback.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **BulkJob** | A bulk operation request with parameters | This capability |
| **BulkOperationType** | Promote, Assign, Send, Generate, Import | This capability |
| **JobStatus** | Pending → Validating → Processing → Completed → Failed | This capability |
| **ValidationResult** | Pre-execution validation (errors, warnings) | This capability |
| **ErrorRecord** | Per-item error with entity reference | This capability |
| **JobAudit** | Who initiated, what was affected, when | This capability |

### 3. Bulk Operation Lifecycle

```
[1] Select / Upload Entities
        │
[2] Validation Phase
    ├── Check permissions
    ├── Validate data
    ├── Identify errors
    └── Show preview: "195 items valid, 5 errors"
        │
[3] User Confirmation
        │
[4] Execution Phase
    ├── Process items asynchronously
    ├── Track progress: "145/200 processed"
    ├── Handle errors per item (configurable: continue or fail-fast)
    └── Generate summary report
        │
[5] Audit Record
    ├── 195 processed, 5 failed
    ├── Duration: 45s
    └── Initiator: Principal Sharma
```

### 4. Key Rules

1. **Every bulk operation has a validation phase before execution.**
2. **Users see a preview** of what will happen before confirming.
3. **Progress is visible** — "145/200 students processed".
4. **Errors are per-item** — one failure does not block the entire operation (configurable).
5. **Large operations are async** — UI does not block.
6. **Full audit trail** — every bulk operation is recorded.

### 6. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| Bulk operation framework contract | ✅ Design in Phase 1 |
| Student promotion (bulk) | ✅ Build in Phase 2 |
| Bulk fee assessment | ✅ Build in Phase 2 |
| Async processing with progress | ✅ Build in Phase 2 |
| CSV import for student creation | 🔄 Phase 3 |

---

## C-19: Export & Document Generation Engine ★ NEW

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** School-Optimized  
> **Consumed By:** Exams (report cards), Student Management (certificates), Fees (receipts), Attendance (registers), Reports (exports)

### 1. Purpose

**Centralized document generation and data export.** Report cards, certificates, fee receipts, ID cards — every module generates documents. Without a shared engine, each builds its own PDF generation with different formatting and no template reuse.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **ReportTemplate** | Configurable document template with placeholders | This capability |
| **TemplateVariable** | Bound data field (`{{student.name}}`, `{{marks.total}}`) | This capability |
| **GeneratedDocument** | A rendered document (PDF, Excel, CSV) | This capability |
| **ExportFormat** | PDF, HTML, XLSX, CSV | This capability |
| **DataBinding** | Mapping between template variables and data sources | This capability |
| **BatchGeneration** | Generate documents for many entities at once | This capability |

### 3. Document Generation Flow

```
[1] Select Template
    "ReportCard – CBSE Grade 10"
        │
[2] Bind Data
    ├── Student: Priya Sharma
    ├── Marks: Math 95, Science 88
    ├── Attendance: 92%
    └── Grade: A+
        │
[3] Render (PDF/HTML)
    ├── Apply template
    ├── Substitute variables
    ├── Apply formatting (logo, layout)
    └── Generate output
        │
[4] Store in Document Framework (C-14)
    └── Notify stakeholders (C-09)
```

### 4. Key Rules

1. **Templates are configurable per institution** — each school may have its own report card format.
2. **Batch generation** — generate 500 report cards in one operation (uses C-18 Bulk Operations).
3. **Generated documents are stored in C-14** — not orphaned.
4. **Multiple output formats** — PDF for print, Excel for analysis.
5. **Templates support conditional sections** — "Show grade only if configured."

### 6. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| PDF generation with template support | ✅ Build |
| Variable substitution (`{{student.name}}`) | ✅ Build |
| Integration with Document Framework | ✅ Build |
| Batch generation | ✅ Build |
| Multi-format (Excel, CSV) | 🔄 Phase 3 |

---

## C-20: Task & Reminder Framework ★ NEW

> **Layer:** Service  
> **Criticality:** Medium  
> **Phase:** 3  
> **Institution Scope:** Agnostic  
> **Consumed By:** Homework (student tasks), Fees (reminders), Workflow (approval tasks), Exams (preparation tasks), Events (coordinator tasks)

### 1. Purpose

**Shared task and reminder capability.** Students have homework tasks. Teachers have lesson tasks. Staff has approval tasks. Without a shared framework, users have fragmented task lists across modules with no consolidated "My To-Do" view.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Task** | An action item with due date and status | This capability |
| **TaskType** | Homework, Approval, Reminder, Preparation | This capability |
| **TaskAssignment** | User(s) assigned to a task | This capability |
| **Reminder** | Configurable reminder at N days/hours before due date | This capability |
| **TaskStatus** | Pending, InProgress, Completed, Overdue, Cancelled | This capability |
| **TaskPriority** | High, Medium, Low | This capability |

### 3. Key Rules

1. **Tasks have a type, due date, status, and priority.**
2. **Reminders are configurable per task type** and use C-09 for delivery.
3. **Users see a unified task dashboard** across all modules.
4. **Tasks respect authorization boundaries** — users only see their assigned tasks.

### 4. Startup Scope (Phase 3)

| Feature | Scope |
|---|---|
| Define interfaces in Phase 1 | ✅ Plan |
| Unified task dashboard | 🔄 Phase 3 |

---

## C-21: Search Framework

> **Layer:** Service  
> **Criticality:** Medium  
> **Phase:** 3  
> **Institution Scope:** Agnostic  
> **Consumed By:** All modules — cross-module search

### 1. Purpose

**Unified, cross-module search.** Respects authorization and institution boundaries.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **SearchIndex** | Index definition per entity type | This capability |
| **SearchQuery** | Full-text and filtered query | This capability |
| **SearchResult** | Results with relevance ranking | This capability |
| **Facet** | Filter by type, institution, date | This capability |
| **Suggestion** | Auto-complete suggestions | This capability |

### 3. Search Scope Roadmap

| Phase | Search Scope |
|---|---|
| Phase 1 | User search (find students, teachers by name) |
| Phase 2 | Academic search (classes, subjects, programs) |
| Phase 3 | Full-text module search (homework, assessments, documents) |

### 4. Key Rules

1. **Search respects authorization + institution boundaries.**
2. **Indexing is async** — no impact on transaction performance.
3. **Results are faceted** — filter by type, institution, date.

### 5. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Basic user search | ✅ Build |
| Define search interface | ✅ Plan |

---

## C-22: Analytics Framework & Data Pipeline

> **Layer:** Pipeline  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** Agnostic  
> **Consumed By:** Principal Dashboard, Director Dashboard, Platform Reports, Client Reports

### 1. Purpose

Separate **analytical workloads from transactional systems.** Provide dashboards and reports without degrading operational performance.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **DataPipeline** | ETL from transactional to analytics store | This capability |
| **AnalyticsStore** | Read-optimized data store | This capability |
| **ReportDefinition** | Configurable report with data sources | This capability |
| **Dashboard** | Collection of charts and metrics | This capability |
| **ScheduledReport** | Time-triggered report generation | This capability |

### 3. Data Flow

```
Transactional DB (Attendance, Fees, Homework, Exams)
       │
       ▼
  ETL Pipeline (Scheduled Batch — Daily)
       │
       ▼
  Analytics DB (Read-Optimized)
       │
       ├── School Reports ─── Principal
       ├── Multi-School ───── Regional Manager
       ├── Client Reports ─── Director
       └── Platform Reports ── Platform Owner
```

### 4. Reporting Levels

| Level | Audience | Examples |
|---|---|---|
| School | Principal, Teachers | Class attendance, fee collection, exam results |
| Multi-School | Regional Manager | Branch comparison |
| Client | Director | Aggregated metrics across institutions |
| Platform | Platform Owner | Revenue, usage, subscriptions |

### 5. Key Rules

1. **Operational systems do not perform heavy analytical processing.**
2. **Analytics data is read-only** for consumers.
3. **Scheduled refresh** — daily batch initially.
4. **Reports respect authorization boundaries.**

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Define analytics data model | ✅ Plan |
| Daily batch pipeline | 🔄 Phase 2 |
| School-level reports | 🔄 Phase 2 |

---

## C-23: Billing Framework

> **Layer:** Pipeline  
> **Criticality:** Important  
> **Phase:** 2  
> **Institution Scope:** Agnostic  
> **Consumed By:** Platform Operations

### 1. Purpose

Manage **SaaS billing operations** — invoicing, payments, revenue tracking at the platform level.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **Invoice** | Client-level invoice with itemized line items | This capability |
| **InvoiceLineItem** | Per-module, per-institution charge | This capability |
| **Payment** | Payment record against an invoice | This capability |
| **TaxRule** | Tax calculation per region | This capability |
| **PricingPlan** | Pricing model per offering | This capability |

### 3. Billing Model

```
Client A (3 Schools)
  Invoice:
  ├── Core Platform: $0 (included)
  ├── Attendance Module: 3 schools × $50 = $150
  ├── Homework Module: 3 schools × $40 = $120
  ├── Fees Module: 3 schools × $60 = $180
  ├── Total Students: 100
  └── Total Amount: $450
```

### 4. Key Rules

1. **Billing at Client level** — one invoice per client, itemized by institution.
2. **Pricing is configurable** — per-school, per-student, or flat rate.
3. **Invoices are immutable** once generated.

### 5. Startup Scope (Phase 2)

| Feature | Scope |
|---|---|
| Invoice generation (manual) | ✅ Build |
| Payment reconciliation (manual) | ✅ Build |
| Automated billing | 🔄 Phase 3 |

---

## C-24: Integration Framework

> **Layer:** Service  
> **Criticality:** Important  
> **Phase:** 1  
> **Institution Scope:** Agnostic  
> **Consumed By:** Fees (payment gateway), Notification (email provider), all external integrations

### 1. Purpose

Standardized approach for integrating with external systems. Each integration category has a **common interface** allowing provider swapping.

### 2. Domain Ownership

| Entity | Description | Owned By |
|---|---|---|
| **IntegrationProvider** | Provider configuration per category | This capability |
| **ProviderCredential** | Encrypted API keys and secrets | This capability |
| **Webhook** | Incoming/outgoing webhook handler | This capability |
| **IntegrationLog** | Request/response log for debugging | This capability |

### 3. Provider Abstraction

```
PaymentGateway (Interface)
  ├── RazorpayProvider
  ├── StripeProvider
  └── FutureProvider

EmailProvider (Interface)
  ├── SmtpProvider
  ├── SendGridProvider
  └── FutureProvider
```

### 4. Integration Roadmap

| Category | Phase 1 | Phase 2 | Future |
|---|---|---|---|
| Payment | Stripe / Razorpay | Additional gateways | — |
| Email | SMTP / SendGrid | SES | Mailgun |
| SMS | — | Twilio | Vonage |
| Storage | Local | S3 | Azure, GCS |
| Video | — | Zoom, Meet | — |
| LMS | — | Google Classroom | Moodle |

### 5. Key Rules

1. **Each category has a common interface** — providers are swappable at runtime.
2. **Credentials are encrypted at rest** and stored per-tenant.
3. **Webhook handling is centralized** — one endpoint per provider type.
4. **Rate limiting and retry logic** are built into the provider abstraction.

### 6. Startup Scope (Phase 1)

| Feature | Scope |
|---|---|
| Payment gateway (single provider) | ✅ Build |
| Email provider (SMTP/SendGrid) | ✅ Build |
| Provider abstraction pattern | ✅ Build |
| SMS provider | 🔄 Phase 2 |

---

## C-25: AI Framework (Future)

> **Layer:** Service  
> **Criticality:** Future  
> **Phase:** 6+  
> **Institution Scope:** Agnostic  
> **Consumed By:** Lesson Planning, Assessment, Intervention, Portfolio (Phase 6 modules)

### 1. Purpose

**Shared AI/ML capabilities** for future intelligent modules. AI is a platform capability, not embedded within individual modules.

### 2. Domain Ownership (Future)

| Entity | Description |
|---|---|
| **AIModel** | Model version and configuration |
| **InferenceResult** | Result of model inference |
| **TrainingData** | Anonymized data for model training |
| **AIGuardrail** | Data isolation and privacy controls |

### 3. Potential Capabilities

| Capability | Consumer Module | Phase |
|---|---|---|
| Lesson Generation | Lesson Planning | Phase 6 |
| Question Generation | Assessment | Phase 6 |
| Learning Gap Detection | Learning Outcomes | Phase 6 |
| Student Risk Prediction | Intervention Management | Phase 6 |
| Academic Recommendations | Student Portfolio | Phase 6 |

### 4. Key Rules

1. **AI is a shared platform capability** — no module builds its own AI pipeline.
2. **Data isolation** — models must not leak data across clients.
3. **Opt-in per institution** — schools choose whether to enable AI features.

### 5. Startup Scope

- ❌ Not built in Phase 1.
- Define framework contract and interfaces.
- Implementation begins in Phase 6.

---

# Part III — Analysis

## 3. Gap Analysis

### 3.1 Missing Capabilities (Not in Original Documents)

The following capabilities were absent from all four source documents. They are essential for a production-ready School ERP platform.

| # | Capability | Criticality | Phase Needed | Impact of Absence |
|---|---|---|---|---|
| G-01 | **C-06: Relationship Management Framework** | 🔴 Critical | Phase 1 | Every module builds its own parent-child mapping. Data fragmentation. No unified guardian view. |
| G-02 | **C-12: Code & Identifier Generation** | 🟡 Important | Phase 1 | Inconsistent ID formats. No centralized sequence control. Duplicate ID risk. |
| G-03 | **C-13: Location & Address Management** | 🟡 Important | Phase 1 | Each module invents its own address fields. No geocoding for Transport. No address versioning. |
| G-04 | **C-16: Calendar & Scheduling** | 🟡 Important | Phase 2 | No consolidated school calendar. Scheduling conflicts undetected. Fragmented date management. |
| G-05 | **C-17: Dynamic Group Management** | 🟡 Important | Phase 2 | Each module needing groups (Homework, Sports, Clubs, Transport) builds its own group model. |
| G-06 | **C-18: Bulk Operations Framework** | 🟡 Important | Phase 2 | Each module builds its own bulk UI. No progress tracking. No validation preview. No audit. |
| G-07 | **C-19: Export & Document Generation** | 🟡 Important | Phase 2 | Each module builds its own PDF generation. Inconsistent output. No template reuse. |
| G-08 | **C-20: Task & Reminder Framework** | 🔵 Medium | Phase 3 | Fragmented task lists across modules. No consolidated "My To-Do" view. |
| G-09 | **Multi-language / Localization** | 🔵 Medium | Phase 3 | Hard to retrofit. Required for regional expansion. |
| G-10 | **Consent & Permission (Parental)** | 🔵 Medium | Phase 3 | Required for field trips, photos, data sharing. |

### 3.2 Refinements to Existing Capabilities

| # | Capability | Gap in v2 | Fix Applied |
|---|---|---|---|
| R-01 | C-02: Identity & User | Missing `UserIdentifier` (Student ID, Employee ID) and `UserProfile` entity | Added to domain ownership |
| R-02 | C-03: Authentication | Missing OTP-based login, `LoginAttempt` audit, MFA readiness | Added to roadmap and domain |
| R-03 | C-04: Authorization | Missing `Policy` entity for ABAC rules, `TemporaryRole` with expiry | Added |
| R-04 | C-05: Academic Structure | Missing `Room`/`Facility`, `Elective` capacity, `Cohort` tracking | Added |
| R-05 | C-10: Communication | Missing `AnnouncementTarget` and conversation role model | Added |

---

## 4. Dependency Map

### 4.1 Level Structure

```
Level 1 (No Dependencies — Build First)
  ├── C-01a: Tenant Identity Infrastructure
  ├── C-08: Configuration Framework
  ├── C-01b: Tenant & Institution Domain (depends on C-01a + C-08)
  └── C-22: Analytics Framework (define data model only)

Level 2 (Depend on Level 1)
  ├── C-02: Identity & User Management
  ├── C-05: Academic Structure Framework
  ├── C-03: Authentication
  └── C-13: Location & Address Management  ← NEW

Level 3 (Depend on Levels 1–2)
  ├── C-04: Authorization
  ├── C-07: Subscription Management
  ├── C-06: Relationship Management  ← NEW
  ├── C-12: Code & Identifier Generation  ← NEW
  └── C-11: Audit & Observability Framework

Level 4 (Depend on Levels 1–3)
  ├── C-09: Notification Framework
  ├── C-10: Communication Framework
  ├── C-14: Document Management
  ├── C-16: Calendar & Scheduling  ← NEW
  ├── C-17: Dynamic Group Management  ← NEW
  └── C-18: Bulk Operations Framework  ← NEW

Level 5 (Depend on Levels 1–4)
  ├── C-15: Workflow Framework
  ├── C-19: Export & Document Generation  ← NEW
  ├── C-21: Search Framework
  ├── C-23: Billing Framework
  └── C-24: Integration Framework

Level 6 (Depend on Multiple Levels)
  ├── C-20: Task & Reminder Framework  ← NEW
  └── C-22: Analytics Framework (full implementation)

Level 7 (Future)
  └── C-25: AI Framework
```

---

## 5. Development Sequencing

### 5.1 Phase 1 — Foundation (Months 1–4)

**Objective:** Build the minimum platform that business modules require.

| Priority | Capability | Rationale |
|---|---|---|
| P1 | C-01a: Tenant Identity Infrastructure | Root of all multi-tenant operations |
| P1 | C-01b: Tenant & Institution Domain | First business module; depends on C-01a + C-08 |
| P2 | C-08: Configuration Framework | Every capability needs configuration |
| P3 | C-02: Identity & User Management | Users are foundational |
| P4 | C-03: Authentication | Login required |
| P5 | C-04: Authorization | Permission control |
| P6 | C-05: Academic Structure Framework | Grades, classes, subjects |
| P7 | **C-06: Relationship Management** ⚡ | Parent-student links needed by all modules |
| P8 | C-11: Audit & Observability | Compliance |
| P9 | C-09: Notification Framework | Alerts for all modules |
| P10 | C-10: Communication Framework | Messaging |
| P11 | C-14: Document Management | File storage |
| P12 | C-07: Subscription Management | Module enable/disable |
| P13 | C-24: Integration Framework | Payment, email |
| P14 | **C-12: Code & Identifier Generation** ⚡ | Student IDs, receipt numbers |
| P15 | **C-13: Location & Address Management** ⚡ | Addresses |
| P16 | C-22: Analytics Framework (model only) | Report readiness |

### 5.2 Phase 2 — Operational Enhancement (Months 5–7)

| Priority | Capability | Trigger |
|---|---|---|
| P1 | C-15: Workflow Framework | Leave Management needs approvals |
| P2 | **C-16: Calendar & Scheduling** ⚡ | Exam schedules, events |
| P3 | **C-18: Bulk Operations Framework** ⚡ | Student promotions, fee assessment |
| P4 | **C-19: Export & Document Generation** ⚡ | Report cards, certificates |
| P5 | **C-17: Dynamic Group Management** ⚡ | Sports teams, clubs, groups |
| P6 | C-23: Billing Framework | Revenue automation |
| P7 | C-22: Analytics Pipeline (full) | Reporting needs grow |

### 5.3 Phase 3 — Platform Maturity (Months 8–10)

| Priority | Capability | Trigger |
|---|---|---|
| P1 | C-21: Search Framework | User growth |
| P2 | **C-20: Task & Reminder Framework** ⚡ | Consolidated to-do |
| P3 | Multi-language / Localization ⚡ | Regional expansion |

### 5.4 Phase 4+ — Advanced

| Capability | Trigger |
|---|---|
| C-07: Curriculum Framework | Lesson Planning requires it |
| Consent & Permission Framework ⚡ | Field trips require it |
| C-25: AI Framework | Academic Intelligence modules |

---

## 6. Platform Evolution Rules

### Rule 1: Platform-First Evaluation

Every new requirement must be evaluated in this order:

1. **Does this belong to an existing platform capability?**
   - *Example:* "Send email on homework assignment" → C-09 Notification, not Homework module.

2. **Does an existing capability need enhancement?**
   - *Example:* "Attendance needs parent-student link" → C-06 Relationship Management, not Attendance.

3. **Is a new platform capability required?**
   - *Example:* "Multi-step approval workflows" → Define C-15 Workflow Framework.

Only after these three questions should a business module be designed.

### Rule 2: Shared Services Improvement

Every new module **must** leave the platform stronger:

| New Module | Platform Capabilities It Improves |
|---|---|
| Attendance | C-06 (Relationships), C-04 (Authorization), C-16 (Calendar) |
| Homework | C-09 (Notifications), C-14 (Documents), C-20 (Tasks) |
| Fees | C-09, C-19 (Export), C-24 (Integration), C-18 (Bulk Ops) |
| Exams | C-16 (Calendar), C-19 (Export), C-05 (Academic Structure) |

### Rule 3: No Duplicate Ownership

Once a capability owns a domain:

- ❌ No module may **duplicate** that domain.
- ❌ No module may **bypass** that capability.
- ❌ No module may **redefine** entities owned by that capability.

### Rule 4: Independent Evolvability

- Capabilities evolve **without breaking** consumers.
- Modules evolve **without requiring** capability changes.
- Module requirements may **extend** but must not **replace** a capability.

---

## 7. Non-Negotiable Rules

| # | Rule | Violation Consequence |
|---|---|---|
| 1 | **Client isolation is mandatory.** One client's data must never leak to another. | Security incident, legal liability |
| 2 | **Authentication is centralized.** No module implements its own login. | Inconsistent security, SSO impossible |
| 3 | **Authorization is centralized.** No module implements its own permission system. | Audit gaps, permission bypass |
| 4 | **Modules are independently subscribable.** No unrelated module dependencies. | Cannot sell modules separately |
| 5 | **Platform kernel is single source of truth.** No duplicates. | Data inconsistency |
| 6 | **Analytics separated from transactional workloads.** | Performance degradation |
| 7 | **Database migration paths remain open.** Business logic independent of storage topology. | Vendor lock-in |
| 8 | **Avoid premature optimization.** Add complexity only when required. | Wasted development effort |
| 9 | **Privacy-first SaaS operations.** Platform operator access to client data is governed by strict boundaries. | Trust erosion |
| 10 | **Relationships owned by C-06, not by modules.** | Data fragmentation |
| 11 | **Configuration requires no code changes.** | Operations bottleneck |
| 12 | **Every module improves shared capabilities.** No workarounds. | Platform decay |

---

# Appendices

## Appendix A: Capability Classification Matrix

| ID | Capability | Layer | Criticality | Phase | Gap? |
|---|---|---|---|---|---|
| C-01a | Tenant Identity Infrastructure | Kernel | Critical | 1 | Split from C-01 |
| C-01b | Tenant & Institution Domain | Business | Critical | 1 | Split from C-01 |
| C-02 | Identity & User Management | Kernel | Critical | 1 | Refined |
| C-03 | Authentication | Kernel* | Critical | 1 | Refined |
| C-04 | Authorization | Kernel* | Critical | 1 | Refined |
| C-05 | Academic Structure Framework | Kernel* | Critical | 1 | Refined |
| C-06 | **Relationship Management Framework** | Kernel* | Critical | 1 | **🆕 NEW** |
| C-07 | Subscription Management | Kernel | Critical | 1 | |
| C-08 | Configuration Framework | Kernel | Critical | 1 | |
| C-09 | Notification Framework | Service | Critical | 1 | |
| C-10 | Communication Framework | Service | Important | 1 | Refined |
| C-11 | Audit & Observability Framework | Kernel* | Critical | 1 | |
| C-12 | **Code & Identifier Generation Engine** | Service | Important | 1 | **🆕 NEW** |
| C-13 | **Location & Address Management** | Service | Important | 1 | **🆕 NEW** |
| C-14 | Document Management Framework | Service | Important | 1 | |
| C-15 | Workflow Framework | Service | Important | 2 | |
| C-16 | **Calendar & Scheduling Framework** | Service | Important | 2 | **🆕 NEW** |
| C-17 | **Dynamic Group Management** | Service | Important | 2 | **🆕 NEW** |
| C-18 | **Bulk Operations Framework** | Service | Important | 2 | **🆕 NEW** |
| C-19 | **Export & Document Generation Engine** | Service | Important | 2 | **🆕 NEW** |
| C-20 | **Task & Reminder Framework** | Service | Medium | 3 | **🆕 NEW** |
| C-21 | Search Framework | Service | Medium | 3 | |
| C-22 | Analytics Framework & Data Pipeline | Pipeline | Important | 2 | |
| C-23 | Billing Framework | Pipeline | Important | 2 | |
| C-24 | Integration Framework | Service | Important | 1 | |
| C-25 | AI Framework | Service | Future | 6+ | |

> \* Capabilities marked `Kernel*` produce both kernel infrastructure packages AND a business domain module. When built, each will be split into `<ID>a` (infrastructure) and `<ID>b` (domain) rows in this matrix, following the C-01a/C-01b precedent established by C-01. The infrastructure lives under `kernel/` and is consumed by every business module; the domain lives under `business/` and is used only by the capability's own workflows. **Note:** C-02 (Identity & User Management) was originally marked `Kernel*` but is now classified as entirely `Kernel` — user management is platform infrastructure, not business domain (no school administrator wants to "create users"; they want to take attendance and manage homework).

## Appendix B: Module Dependency Matrix

Which platform capabilities does each business module depend on?

| Business Module | C01 Tenant | C02 Users | C03 Auth | C04 AuthZ | C05 Academic | C06 Relations | C07 Subscr | C08 Config | C09 Notif | C10 Comm | C11 Audit | C12 Code | C13 Address | C14 Doc | C15 Workflow | C16 Calendar | C17 Groups | C18 BulkOps | C19 Export | C21 Search | C22 Analytics |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Attendance** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | — | — | ✅ | — | — | ✅ | — | ✅ |
| **Homework** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | — | ✅ | ✅ | — | — | — | ✅ |
| **Fees** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | ✅ |
| **Exams** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | — | ✅ | — | ✅ |
| **Parent Comm.** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — | — | ✅ | ✅ | ✅ | — | — | — |
| **Timetable** | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | — | ✅ | — | ✅ | — | — | ✅ | — | — | — | — | — |
| **Leave Mgmt** | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | — | ✅ | — | — | — | ✅ | ✅ | — | — | — | — | — |
| **Lesson Plan** | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | — | ✅ | — | — | ✅ | ✅ | — | — | — | — | — | — |
| **Transport** | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | — | — | ✅ | ✅ | — | — | — | — |
| **Events** | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | ✅ | — | — | — | — |

## Appendix C: Glossary

| Term | Definition |
|---|---|
| **Platform Kernel** | Minimum set of capabilities required before any business module can function (all Phase 1 capabilities: C-01a+b through C-13). Defined by build order, not dependency depth — includes both kernel infrastructure (e.g., C-01a) and business domain modules that must exist first (e.g., C-01b). |
| **Business Module** | A subscribable product that implements educational workflows (e.g., Attendance, Homework, Fees). |
| **Shared Platform Capability** | A foundational service consumed by multiple modules (e.g., Authorization, Notifications, Relationships). |
| **Client** | A customer organization that owns one or more institutions. |
| **Institution** | An operational educational unit (school, college, university, institute). |
| **Tenant Isolation** | One client's data must never be accessible to another client. |
| **Modular Monolith** | Single deployment, independently developable modules, shared services. |
| **Single Source of Truth** | Each domain entity is owned by exactly one capability. |
| **ABAC** | Attribute-Based Access Control — permissions based on attributes. |
| **RBAC** | Role-Based Access Control — permissions via roles. |
| **ETL** | Extract, Transform, Load — data pipeline. |

---

> **End of Document**  
> **Version:** 3.0  
> **Total Capabilities:** 25 (18 existing + 7 new via gap analysis)  
> **Gaps Found:** 10 total (3 critical, 5 important, 2 medium)  
> **Next:** Technical specifications for Phase 1 capabilities
