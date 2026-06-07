# School ERP SaaS — Shared Platform Capabilities

## Definitive Reference (v3)

> **Status:** Refined & Gap-Analyzed  
> **Author:** School ERP Architecture Expert  
> **Source:** Synthesis of `Functional_Requirement.md`, `School_ERP_Architecture_v1.md`, `Shared_Platform_Capabilities.md`, `StartUp_Strategy.md`  
> **Purpose:** Single source of truth for the shared platform foundation. Every business module must consume these capabilities. No module may duplicate, bypass, or redefine them.

---

# Part I: Framework

## 1. What Are Shared Platform Capabilities?

**Definition:** Foundational services that own a cross-cutting domain, are consumed by multiple business modules, and evolve independently.

```
┌──────────────────────────────────────────────────────────┐
│                 Business Modules                         │
│  (Attendance, Homework, Fees, Exams, Timetable, ...)     │
│         Consume          Consume          Consume        │
└────────┬─────────────────┬─────────────────┬─────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────┐
│              Shared Platform Capabilities                 │
│  (Tenant, Auth, Users, Academic, Notify, Audit, ...)     │
└──────────────────────────────────────────────────────────┘
```

**What They Are NOT:** Business modules implement *educational workflows*. Platform capabilities implement *infrastructure that all workflows share*.

| Business Module | Platform Capability |
|---|---|
| Attendance | Tenant & Institution Management |
| Homework | Identity & User Management |
| Fees | Authentication |
| Exams & Grading | Authorization |
| Parent Communication | Academic Structure Framework |
| Lesson Planning | Subscription Management |
| Report Cards | Notification Framework |
| Timetable | Audit & Observability Framework |

---

## 2. The Platform-First Principle

No business module may be built until the **Platform Kernel** exists:

1. Tenant & Institution Management
2. Identity & User Management
3. Authentication
4. Authorization
5. Academic Structure Framework
6. Subscription Management
7. Audit & Observability Framework
8. Notification Framework
9. Configuration Framework
10. **Relationship Management Framework** ← NEW: critical gap

These ten form the minimum viable platform before any business module can function.

---

## 3. Capability Classification System

Each capability is classified across four dimensions:

| Dimension | Values | Meaning |
|---|---|---|
| **Layer** | Kernel / Service / Pipeline | Kernel = every module requires it; Service = most modules use it; Pipeline = data processing |
| **Criticality** | Critical / Important / Future | Impact if absent during Phase 1 |
| **Institution Scope** | Agnostic / School-Optimized / Flexible | How tightly coupled to school model |
| **Ownership** | Single Source of Truth | Entity types this capability exclusively owns |

---

# Part II: Core Capability Inventory

---

## C-01: Tenant & Institution Management

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | Client, Institution, InstitutionType, LifecycleState, OrgUnit |

### Purpose
Multi-tenant foundation. Every entity in the system belongs to a tenant context.

### Domain Ownership (Single Source of Truth)

| Entity | Description |
|---|---|
| **PlatformOwner** | The SaaS provider operating the platform |
| **Client** | A customer organization (school, trust, chain, group) |
| **ClientLifecycle** | Prospective → Active → Suspended → Archived → Terminated |
| **Institution** | An operational unit (school, college, university, institute) |
| **InstitutionType** | Configurable classification (School, College, University, CoachingInstitute, etc.) |
| **InstitutionLifecycle** | Onboarding → Active → Inactive → Archived |
| **OrgUnit** | Hierarchy node (Faculty, Department, Division, etc.) |
| **OrgUnitHierarchy** | Parent-child relationships between OrgUnits |

### Tenant Model

```
Platform Owner
  └── Client A ──────────── Client B
       ├── School A1              └── College B1
       ├── School A2                   ├── Computer Science Dept
       └── College A3                   └── Mathematics Dept
```

### Critical Rules

1. Every Institution belongs to exactly one Client. No orphans.
2. Clients may own 1..N Institutions. Multi-institution clients do not require tenant restructuring.
3. InstitutionTypes are **configurable**, not hardcoded. New types may be added without code changes.
4. OrgUnits are **configurable** per InstitutionType. School OrgUnits differ from University OrgUnits.
5. Institutions cannot be deleted — only lifecycle-managed (Active → Archived). This preserves audit trail integrity.

### Startup Scope

- Client registration & creation
- Institution creation (School configuration only)
- Basic org structure: Grades → Classes → Sections
- InstitutionTypes: School only (configurable model but single type active)

---

## C-02: Identity & User Management

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | User, UserProfile, UserCategory, UserLifecycle |

### Purpose
Unified identity model. A person has **one identity** regardless of how many institutions or roles they hold.

### Domain Ownership

| Entity | Description |
|---|---|
| **User** | A person with a platform identity |
| **UserProfile** | Name, contact, photo, date of birth, gender, blood group, etc. |
| **UserCategory** | Classifiable group (Learner, AcademicStaff, AdminStaff, Executive, etc.) |
| **UserLifecycle** | Invited → Pending → Active → Suspended → Transferred → Archived |
| **UserIdentifier** | Student ID, Employee ID, Admission No. (see C-12: Code Generation) |

### Configurable User Categories

| Category | Phase 1 Examples | Future Examples |
|---|---|---|
| Learner | School Student | College Student, Trainee, Research Scholar |
| Academic Staff | Teacher | Lecturer, Professor, Visiting Faculty, Trainer |
| Academic Leadership | Principal, HOD | Dean, Vice Chancellor, Academic Director |
| Administrative Staff | Clerk, Accountant | Registrar, HR Officer, Office Manager |
| Executive Leadership | Director, Trustee | Chairman, Governing Board Member |

### Institutional Assignment

User belongs to **Client first**, then to one or more Institutions:

```
Client A
  └── User: Rajesh Sharma
       ├── Institution: School A1 → Role: Teacher (Mathematics)
       ├── Institution: School A1 → Role: HOD (Science Dept)
       └── Institution: School A2 → Role: Teacher (Mathematics)
```

### Critical Rules

1. A user has **one identity** even if associated with multiple institutions.
2. Role assignment is **per-institution**, not global.
3. A user may hold **multiple roles** within the same institution.
4. A user may be a **learner in one institution and academic staff in another** (rare but supported).

### 🔴 Gap Addressed from v2

| Gap | Detail |
|---|---|
| **UserIdentifier** | v2 had no entity for Student ID / Employee ID / Admission No. These institution-scoped identifiers are essential for school operations. Added to domain ownership. |
| **UserProfile** | v2 listed user capabilities but lacked explicit Profile entity. Schools need standardized profiles (DOB, blood group, emergency contact, photo). |

---

## C-03: Authentication

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | AuthenticationMethod, Session, IdentityProvider, LoginAttempt |

### Purpose
Centralized identity verification. **Single gateway** for all users across all clients.

### Domain Ownership

| Entity | Description |
|---|---|
| **AuthenticationMethod** | Email/Password, Google SSO, Microsoft SSO, etc. |
| **IdentityProvider** | External IdP configuration (per client) |
| **Session** | Active session with expiry, refresh, device info |
| **LoginAttempt** | Audit record of every login attempt (success/failure) |
| **MfaConfig** | Multi-factor authentication settings |

### Supported Methods Roadmap

| Method | Phase | Notes |
|---|---|---|
| Email + Password | Phase 1 | Argon2id, rate-limited |
| OTP-based (Email) | Phase 1 | For passwordless login option |
| OTP-based (SMS) | Phase 2 | Requires SMS integration |
| Google SSO | Phase 2 | OAuth 2.0 / OpenID Connect |
| Microsoft SSO | Phase 2 | OAuth 2.0 / OpenID Connect |
| Apple Sign-In | Future | |
| SAML | Future | For enterprise clients |
| LDAP | Future | For on-premise integration |

### Client Identification Strategy

Primary: **Client-specific subdomain**
```
schoola.acmeplatform.com
schoolb.acmeplatform.com
```

### Critical Rules

1. **Centralized** — no module implements its own login.
2. **Client-aware** — login identifies both user identity and client context.
3. **Brute-force protection** — account lockout after configurable failed attempts.
4. **MFA-ready** — architecture must support adding MFA without refactoring.

### 🔴 Gap Addressed from v2

| Gap | Detail |
|---|---|
| **OTP-based login** | v2 listed only Email/Password and SSO. Real school systems need OTP login for parents who forget passwords. Added to roadmap. |
| **LoginAttempt audit** | v2 had no entity for tracking login attempts. This is essential for security monitoring. |
| **MFA readiness** | Schools with sensitive student data increasingly require MFA. Architecture must plan for it. |

---

## C-04: Authorization

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | Permission, Role, RoleAssignment, Scope, Policy |

### Purpose
Centralized access control. **No module implements its own permission system.**

### Domain Ownership

| Entity | Description |
|---|---|
| **Permission** | Granular action (e.g., `attendance.mark`, `homework.create`, `fee.collect`) |
| **Role** | Named collection of permissions (e.g., Teacher, Principal, Parent) |
| **RoleAssignment** | User + Role + Scope (which user has which role where) |
| **Scope** | Organizational boundary (Institution, Grade, Class, Subject) |
| **Policy** | Conditional rules (e.g., "Teacher can edit homework only if they created it") |

### Authorization Model (RBAC + ABAC)

```
┌──────────────────────────────────────┐
│         Authorization Decision       │
├──────────────────────────────────────┤
│  User Identity                       │
│  + Role Permissions      (RBAC)      │
│  + Scope Constraints     (ABAC)      │
│  + Context Rules         (ABAC)      │
│  + Policy Evaluations    (ABAC)      │
│  = Access Granted / Denied           │
└──────────────────────────────────────┘
```

### Authorization Layers

| Layer | Evaluates | Example |
|---|---|---|
| **Platform** | Is user a platform admin? | Platform Owner managing subscriptions |
| **Client** | Does user belong to this client? | Cross-school Director |
| **Institution** | Is user assigned to this institution? | Teacher in School A |
| **Org Unit** | Is user assigned to this department? | HOD of Science Dept |
| **Grade/Program** | Does user's scope include this grade? | Grade-level coordinator |
| **Class/Batch** | Does user's scope include this class? | Class teacher |
| **Subject/Course** | Does user's scope include this subject? | Subject teacher |
| **Context** | Does user own the entity? | Teacher editing own homework |

### Dynamic Role Management

- Roles are **configurable**, not hardcoded.
- A user may have **multiple roles** simultaneously.
- Roles may be **institution-specific** (School defines "Class Teacher" differently from "Subject Teacher").
- **Temporary roles** with expiry (substitute teacher, exam invigilator).
- **Delegated roles** (Principal delegates to Vice Principal for a period).

### 🔴 Gap Addressed from v2

| Gap | Detail |
|---|---|
| **Policy entity** | v2 lacked a formal Policy entity for ABAC rules. Real school access control needs context-sensitive rules ("can edit only own homework"), not just role-permission mapping. |
| **Temporary roles with expiry** | Schools frequently need temporary access for substitutes, volunteers, exam invigilators. This is a distinct concern from permanent role assignment. |

---

## C-05: Academic Structure Framework

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | School-Optimized (flexible model for future) |
| **Ownership** | AcademicYear, Term, GradeLevel, Program, Class, Section, Batch, Subject, SubjectGroup, Elective, Room, Building |

### Purpose
Flexible academic model that supports multiple institution types without hardcoding hierarchy.

### Domain Ownership

| Entity | School | College | University |
|---|---|---|---|
| AcademicYear | ✅ | ✅ | ✅ |
| Term / Semester | ✅ Term | ✅ Semester | ✅ Semester |
| GradeLevel | ✅ Grade | — | — |
| Program | — | ✅ Program | ✅ Program |
| Class / Cohort | ✅ Class | ✅ Batch | ✅ Batch |
| Section | ✅ Section | — | — |
| Subject / Course | ✅ Subject | ✅ Subject | ✅ Course |
| SubjectGroup | ✅ | ✅ | ✅ |
| Elective | ✅ | ✅ | ✅ |
| Room / Facility | ✅ Classroom | ✅ Lab | ✅ Lecture Hall |

### Hierarchy Examples

**School:**
```
AcademicYear → Term → Grade → Class → Section → Subject
                                                    └── Elective (optional)
```

**College:**
```
AcademicYear → Semester → Program → Batch → Subject
                                                └── Elective (optional)
```

**University:**
```
AcademicYear → Semester → Faculty → Program → Batch → Course
                                                        └── Elective (optional)
```

### 🔴 Gaps Addressed from v2

| Gap | Detail |
|---|---|
| **Room / Facility management** | v2 had no entity for rooms, buildings, labs, or facilities. Timetable needs rooms. Exams need room allocation. Events need venue assignment. This is a cross-cutting concern. |
| **Elective tracking** | Subject groups with elective/compulsory distinction is a fundamental school need. v2 had Subject Groups but no Elective entity with capacity constraints. |
| **Cohort concept** | Schools need "batch of 2026" as a grouping concern independent of current class. Used for graduation tracking, alumni management, and cohort-based analytics. |

---

## C-06: Relationship Management Framework ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | **Critical — Phase 1** |
| **Institution Scope** | Agnostic |
| **Ownership** | Relationship, RelationshipType, ContactRole, EmergencyContact, GuardianRelationship |

### Purpose

**Own the relationships between people in the system.** This is the single most common cross-cutting concern in any School ERP, yet it is missing from all existing documents.

Without it, every module independently models who is whose parent, leading to:
- Inconsistent parent-child mappings across Attendance, Fees, Communication
- No support for complex family structures (divorced parents, shared custody, step-parents, guardians)
- Duplicate data entry and maintenance
- No unified view of "who is responsible for this student"

### Why This Is a Platform Capability, Not a Module Concern

| Module | Relationship Need |
|---|---|
| Attendance | Who to notify when student is absent |
| Fees | Who is financially responsible |
| Communication | Who receives parent communications |
| Health | Who to contact in emergency |
| Transport | Who approves transport changes |
| Exams | Who receives report cards |
| Events | Who gives consent for field trips |
| Discipline | Who is notified of incidents |

Every single one of these needs to know: **"Who is this student's parent/guardian?"** This is a shared question, not a per-module question.

### Domain Ownership

| Entity | Description | Examples |
|---|---|---|
| **Relationship** | A typed connection between two users | Student-Parent, Student-Guardian, Staff-Student |
| **RelationshipType** | Configurable relationship classification | Mother, Father, Guardian, EmergencyContact, Sibling |
| **ContactRole** | Responsibilities assigned to a relationship | FinancialResponsible, EmergencyContact, PickupAuthorized |
| **GuardianRelationship** | Parent/guardian specific attributes | Has custody, Lives with student, Communication preference |
| **EmergencyContact** | Priority-ordered contacts | Primary: Mother, Secondary: Father, Tertiary: Grandparent |

### Relationship Model

```
                          User A (Student)
                         /        |        \
                        /         |         \
              Parent/Guardian   Sibling    Emergency Contact
                        \         |         /
                         \        |        /
                     User B, C, D (Related Persons)
```

### Contact Role Model

```
Student: Priya Sharma
  ├── Anita Sharma (Mother)
  │     ├── ContactRole: PrimaryGuardian
  │     ├── ContactRole: FinancialResponsible
  │     └── ContactRole: EmergencyContact
  ├── Rajesh Sharma (Father)
  │     ├── ContactRole: Guardian
  │     └── ContactRole: EmergencyContact
  └── Sunita Devi (Grandmother)
        └── ContactRole: EmergencyContact (Priority: 3)
```

### Critical Rules

1. Relationship model is **configurable** — new relationship types can be added without code changes.
2. A student may have **multiple guardians** with different contact roles.
3. Contact roles are **separate from relationship type** — a Guardian may or may not be FinancialResponsible.
4. Relationships respect **institution boundaries** — a parent at School A cannot be linked to a student at School B unless cross-institution linking is explicitly enabled.
5. Emergency contacts are **priority-ordered** and may include non-parent persons.

### Startup Scope (Phase 1)

- Student ↔ Parent/Guardian relationship (1:N — one student, multiple guardians)
- Contact roles: PrimaryGuardian, Guardian, EmergencyContact
- Financial responsibility assignment
- Must be built **before** Attendance, Fees, and Communication modules

---

## C-07: Subscription Management

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | Offering, Subscription, AddOn, Trial, FeatureFlag |

### Purpose
Control client access to platform offerings. Enables the SaaS business model.

### Domain Ownership

| Entity | Description |
|---|---|
| **Offering** | A subscribable product (module or feature pack) |
| **Subscription** | A client's entitlement to one or more offerings |
| **AddOn** | Optional enhancement (e.g., "Advanced Reporting" add-on) |
| **Trial** | Time-limited access with start/end dates |
| **FeatureFlag** | Fine-grained feature toggle within a module |

### Subscription Model

```
Client A (School Chain)
  ├── Core Platform (always included, non-negotiable)
  ├── Attendance Module (subscribed)
  ├── Homework Module (subscribed)
  ├── Fees Module (subscribed)
  ├── Exams Module (not subscribed)
  └── AddOn: Advanced Analytics (subscribed)

Client B (Single School)
  ├── Core Platform (always included)
  └── Attendance Module (subscribed only)
```

### Critical Rules

1. **Core Platform** is always enabled (Tenant, Users, Auth, Academic Structure, Relationships).
2. Business modules are **individually subscribable**.
3. Disabled modules are **hidden and inaccessible** at all layers (UI, API, backend).
4. No module may require subscription to an **unrelated** module.
5. FeatureFlags allow **gradual rollout** within a module (e.g., "Advanced analytics" as an add-on).
6. Trial periods are **configurable** per offering.

---

## C-08: Configuration Framework

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | ConfigurationKey, ConfigurationValue, ConfigurationScope, FeatureToggle |

### Purpose
Runtime-configurable behavior without code changes or redeployment.

### Configuration Scopes (with Inheritance)

```
Platform (Global Defaults)
  └── Client Overrides
       └── Institution Overrides
            └── Module-Specific Overrides
```

Lower scopes inherit from higher scopes unless explicitly overridden.

### Configuration Categories

| Category | Examples |
|---|---|
| **Business Rules** | Attendance marking cutoff time, late fee calculation, auto-approve leave under 3 days |
| **Display Settings** | Date format (DD/MM/YYYY vs MM/DD/YYYY), timezone, language, number format |
| **Academic Settings** | Grading scale, pass percentage, term structure |
| **Notification Rules** | Which events trigger notifications, default channels |
| **Integration Settings** | API keys, webhook URLs, provider selection |
| **Feature Toggles** | Enable/disable features per tenant |

### Critical Rules

1. Configuration changes must **not require code deployment** or application restart.
2. Configuration must support **typed values** (string, number, boolean, JSON, date) with validation.
3. Business logic must **never hardcode** configurable behavior.
4. Configuration changes must be **audited** — who changed what and when.

---

## C-09: Notification Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | NotificationTemplate, NotificationChannel, NotificationDelivery, DeliveryStatus, UserPreference |

### Purpose
Centralized notification delivery. **No module sends its own notifications directly.**

### Domain Ownership

| Entity | Description |
|---|---|
| **NotificationTemplate** | Reusable template with variables (e.g., "Dear {parent_name}, your child {student_name} was marked absent.") |
| **NotificationChannel** | Delivery method (InApp, Email, SMS, Push) |
| **NotificationDelivery** | A single notification attempt with content, channel, recipient |
| **DeliveryStatus** | Queued → Sent → Delivered → Read → Failed |
| **UserPreference** | Per-user channel preference (e.g., receive alerts via Email, reminders via SMS) |
| **NotificationGroup** | Batched notifications (e.g., "3 new homework assignments" instead of 3 separate emails) |
| **ScheduleRule** | When to send (immediate, daily digest, weekly summary) |

### Channel Roadmap

| Channel | Phase | Notes |
|---|---|---|
| In-App | Phase 1 | Bell icon + notification center |
| Email | Phase 1 | Transactional + digest |
| SMS | Phase 2 | For urgent alerts |
| Push (Mobile) | Phase 3 | Requires mobile apps |
| WhatsApp | Future | High open rate |
| Voice Call | Future | Emergency alerts |

### Notification Flow

```
Module Event
  (e.g., homework.created)
       │
       ▼
Notification Framework
  ├── Resolve template
  ├── Check user preferences
  ├── Select channels
  ├── Apply batch rules
  ├── Deliver
  └── Record status (audit)
```

### Critical Rules

1. All modules **must** use this framework. Individual notification implementations are **prohibited**.
2. User preferences must be respected — a user who opts out of SMS should not receive SMS.
3. Batching reduces notification fatigue — configurable per module.
4. Delivery status must be trackable for debugging and compliance.
5. Rate limiting prevents provider throttling.

---

## C-10: Communication Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Important — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | Conversation, Message, ConversationParticipant, Announcement, ReadReceipt |

### Purpose
Structured, bidirectional communication — distinct from one-way notifications.

### Domain Ownership

| Entity | Description |
|---|---|
| **Conversation** | A thread of messages between two or more participants |
| **Message** | A single communication within a conversation |
| **ConversationParticipant** | User + Role within a conversation |
| **Announcement** | One-to-many broadcast (School → All Parents) |
| **AnnouncementTarget** | Target audience (Grade 10 Parents, Class 5A, All Teachers) |
| **ReadReceipt** | Track who has read what |
| **Attachment** | File attached to a message (uses Document Framework) |

### Communication Types

| Type | Participants | Examples |
|---|---|---|
| **Direct Message** | 1:1 | Teacher ↔ Parent |
| **Group Message** | 1:N | Teacher → Class 5A Parents |
| **Broadcast** | 1:Many | Principal → All School Parents |
| **Emergency Alert** | 1:All | School closure notification |
| **Department Chat** | M:N | Science Department discussion |

### 🔴 Gap Addressed from v2

| Gap | Detail |
|---|---|
| **AnnouncementTarget** | v2 had no entity for targeting announcements. Real schools need to send messages to specific groups (e.g., "All Grade 10 Parents" or "Class 5A Students"). This requires integration with Relationship Management and Academic Structure. |
| **Conversation model with roles** | v2 lacked conversation-level modeling. Schools need persistent conversation threads with role-based participation (e.g., Class Teacher can moderate the class parent group). |

---

## C-11: Audit & Observability Framework

| Attribute | Value |
|---|---|
| **Layer** | Kernel |
| **Criticality** | Critical — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | AuditEvent, AuditTrail, AuditLevel, RetentionPolicy |

### Purpose
Record **who did what, when, where, and what changed.** Every significant action must be auditable and traceable.

### Domain Ownership

| Field | Description |
|---|---|
| **ActorId** | Who performed the action |
| **ActorType** | User, System, API Key |
| **Action** | `attendance.marked`, `homework.created`, `fee.collected` |
| **TargetType** | Entity type (e.g., Student, Homework, FeeTransaction) |
| **TargetId** | Specific entity ID |
| **ClientId** | Client context |
| **InstitutionId** | Institution context |
| **AcademicYearId** | Academic year context |
| **Timestamp** | When the action occurred (UTC) |
| **Changeset** | Before/after values of changed fields |
| **Metadata** | IP address, user agent, device info |
| **CorrelationId** | Traceable ID across multiple audit events |

### Audit Levels

| Level | Description | Examples | Retention |
|---|---|---|---|
| **Critical** | Security, compliance, financial | Login failure, fee refund, role change | 7 years |
| **Operational** | Business transactions | Attendance mark, homework submission, exam entry | 3 years |
| **Activity** | Routine actions | Profile view, report download, login success | 90 days |
| **Debug** | System-level tracing | API calls, background job execution | 30 days |

### Critical Rules

1. **Non-repudiable** — audit records cannot be altered or deleted (append-only).
2. **Async logging** — audit must not impact transaction performance (queue-based).
3. **Queryable** — administrators must be able to search and filter audit logs.
4. **Correlation** — related events must be traceable via CorrelationId.

---

## C-12: Code & Identifier Generation Engine ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 1** |
| **Institution Scope** | School-Optimized |
| **Ownership** | IdentifierTemplate, GeneratedIdentifier, SequenceCounter, IdFormat |

### Purpose

**Centralized generation of all human-readable identifiers across the platform.** Every school system generates identifiers — Student IDs, Admission Numbers, Employee IDs, Receipt Numbers, Transaction References, Registration Numbers. Without a shared engine, each module generates them independently, resulting in:

- Inconsistent formats across the platform
- No centralized sequence control (risk of duplicates)
- Inability to configure ID formats per institution
- Fragmented audit trail for ID issuance

### Why This Is a Platform Capability

| Consumer | Identifier Examples |
|---|---|
| **Identity & User Mgmt** | Student ID, Employee ID, Admission No. |
| **Fees** | Receipt No., Invoice No., Transaction Ref. |
| **Exams** | Roll Number, Hall Ticket No. |
| **Homework** | Assignment Reference No. |
| **Documents** | Certificate No., Document Ref. |
| **Communication** | Ticket/Complaint No. |
| **Library** | Membership No., Accession No. |

### Domain Ownership

| Entity | Description | Examples |
|---|---|---|
| **IdentifierTemplate** | Configurable format pattern | `{INST}-{YEAR}-{SEQ:5}` |
| **SequenceCounter** | Auto-incrementing counter per scope | Per-institution, per-year, per-prefix |
| **IdentifierScheme** | Defines prefix, separator, padding, suffix | `SCH-2025-00001` |
| **GeneratedIdentifier** | Record of every generated identifier | |

### Identifier Format Components

```
{SCHOOL-CODE}{YEAR}{SEPARATOR}{SEQUENCE}{CHECK-DIGIT?}

Examples:
  STU-2025-00001    (Student ID)
  EMP-2025-0042     (Employee ID)
  REC-20250607-001  (Receipt No. with date)
  ADM-25-0001       (Admission No., short year)
```

### Configurable Rules

| Rule | Description | Example |
|---|---|---|
| **Prefix** | Institution or module prefix | `STU`, `EMP`, `REC` |
| **Year Format** | Full year or short year | `2025` or `25` |
| **Separator** | Character between segments | `-`, `/`, none |
| **Sequence Padding** | Minimum digit width | `00001` (5 digits) |
| **Scope** | Counter reset boundary | Per-year, per-institution, global |
| **Check Digit** | Validation digit for integrity | Luhn algorithm or custom |

### Critical Rules

1. ID formats are **configurable per institution** — School A may use `STU-{YEAR}-{SEQ}` while School B uses `{INST-CODE}{SEQ}`.
2. Sequence generation must be **atomic** — no duplicates even under concurrent access.
3. Generated IDs must be **immutable** — once assigned, never changed.
4. The engine must support **retroactive numbering** (back-dated admission numbers within sequence).
5. Must integrate with **archival rules** — IDs should remain valid for audit purposes even after entity is archived.

### Startup Scope

- Student ID, Employee ID generation
- Per-institution format configuration
- Per-year sequence reset
- Atomic counter implementation (database sequence or equivalent)

---

## C-13: Location & Address Management ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 1** |
| **Institution Scope** | Agnostic |
| **Ownership** | Address, AddressType, GeoLocation, LocationValidation |

### Purpose

**Centralized address and location management.** Addresses are used everywhere — student home address, parent work address, school location, bus stop locations, staff residence. Without a shared service:

- Every module invents its own address fields
- Address validation is inconsistent
- No geocoding for transport optimization
- Address change requires updating in multiple places

### Why This Is a Platform Capability

| Consumer | Address Usage |
|---|---|
| **Identity & User Mgmt** | Student home address, parent address, staff residence |
| **Tenant Management** | Institution address (school location) |
| **Transport** | Pickup/drop addresses, bus stop locations |
| **Fees** | Billing address |
| **Communication** | Postal mailings |
| **Health** | Emergency contact addresses |
| **Compliance** | Address verification for regulatory reporting |

### Domain Ownership

| Entity | Description |
|---|---|
| **Address** | Structured address with fields (line1, line2, city, state, postalCode, country) |
| **AddressType** | Classification (Home, Work, School, Billing, Emergency) |
| **GeoLocation** | Latitude, longitude for mapping and routing |
| **LocationValidation** | Verification status of an address |
| **AddressAssignment** | Association between an address and an entity |
| **AddressPreference** | Primary/secondary/previous address marking |

### Address Model

```
User: Priya Sharma
  ├── Home Address (Primary)
  │     ├── 123, MG Road, Bangalore, 560001, Karnataka
  │     └──  [Geocoded: 12.9716, 77.5946]
  ├── Previous Address
  │     └── 45, Brigade Road, Bangalore, 560025
  └── Work Address (Parent)
        └── 789, Whitefield, Bangalore, 560066

Institution: Sunshine School
  └── School Address
        └── 1st Cross, Indiranagar, Bangalore, 560038
```

### Address History & Timeline

- Address changes are **versioned** — previous addresses are retained.
- Change is **audited** — who changed the address and when.
- Effective dates supported — "student will move to this address from next month."

### Critical Rules

1. An entity may have **multiple addresses** with type classification.
2. Each entity may have **one primary address** per address type.
3. Address history is **preserved** — changes are versioned, not overwritten.
4. Address reuse is supported — multiple users may share the same address (siblings).
5. Address validation may be **async** (postal verification) but address creation must not be blocked.

### Startup Scope

- Structured address fields with country/state/city hierarchy
- Multiple address types per entity
- Primary address designation
- Address versioning
- Institution location setup (for Transport module)

---

## C-14: Document Management Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Important — Phase 1 |
| **Institution Scope** | Agnostic |
| **Ownership** | Document, DocumentType, DocumentVersion, StorageProvider, AccessControl |

### Purpose
Unified file and document storage. **No module manages files independently.**

### Domain Ownership

| Entity | Description |
|---|---|
| **Document** | A file or document record |
| **DocumentType** | Classification (Photo, Certificate, ReportCard, Assignment, Receipt) |
| **DocumentVersion** | Version tracking for documents |
| **StorageProvider** | Storage backend abstraction (Local, S3, Azure Blob) |
| **DocumentAccess** | Who can view, download, edit a document |
| **Thumbnail** | Auto-generated preview for images and PDFs |
| **DocumentFolder** | Organizational folder structure |

### Document Type Examples

| Module | Documents |
|---|---|
| User Management | Student photo, ID proof, birth certificate |
| Homework | Assignment PDF, submitted image, attached worksheet |
| Fees | Fee receipt, invoice, payment proof |
| Exams | Question paper, answer sheet, marksheet |
| Report Cards | Generated PDF report card |
| Learning Content | Worksheet, presentation, video, lesson plan |
| Health | Medical certificate, vaccination record |
| Transport | Route map, vehicle document |

### Storage Abstraction

```
Module
  │
  ▼
Document Framework (Unified API)
  │
  ├── Local Filesystem (Phase 1)
  ├── Amazon S3 (Phase 2)
  ├── Azure Blob Storage (Phase 2)
  └── Google Cloud Storage (Future)
```

### Critical Rules

1. All file storage flows through this framework — **no module bypasses it**.
2. Document access must respect **institution + authorization boundaries**.
3. Storage provider is **configurable** without application changes.
4. Documents support **versioning** — overwriting a file creates a new version, does not delete the original.
5. Thumbnails and previews are generated **async** after upload.
6. File type and size limits are **configurable per DocumentType**.

---

## C-15: Workflow Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Important — Phase 2 |
| **Institution Scope** | Agnostic |
| **Ownership** | WorkflowTemplate, WorkflowInstance, WorkflowStep, Approval, EscalationRule |

### Purpose
Configurable approval and review workflow engine. **Not hardcoded per module.**

### Domain Ownership

| Entity | Description |
|---|---|
| **WorkflowTemplate** | Definable workflow (e.g., "Leave Approval") |
| **WorkflowInstance** | A running workflow for a specific item |
| **WorkflowStep** | A single stage (approval/review) in the workflow |
| **Approval** | Decision at a step (Approved, Rejected, Pending, Rework) |
| **EscalationRule** | Auto-escalate if no action within time limit |
| **WorkflowNotification** | Notification trigger per step |

### Phase 2 Consumers

| Module | Workflows |
|---|---|
| Leave Management | Leave Request → HOD → Principal |
| Fee Management | Fee Waiver → Finance → Principal |
| Assessment | Assessment Review → HOD |
| Lesson Planning | Lesson Plan → Department Review → Principal |
| Admission | Application → Review → Approval |
| Event Management | Event Approval → Principal |

### Critical Rules

1. Workflows are **configurable per institution** — not hardcoded.
2. The framework provides the engine; **modules define workflow templates** using a DSL or configuration.
3. Notifications at each step use **Notification Framework**.
4. Escalation rules are **configurable** per workflow step.

---

## C-16: Calendar & Scheduling Framework ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 2** |
| **Institution Scope** | School-Optimized |
| **Ownership** | CalendarEvent, EventType, RecurrenceRule, Schedule, ConflictDetection |

### Purpose

**Unified calendar and event management.** Schools run on calendars — academic calendars, exam schedules, event calendars, fee due dates, parent-teacher meeting schedules. Without a shared framework:

- Every module builds its own date management
- No consolidated school calendar for parents and staff
- Scheduling conflicts go undetected (exam on same day as sports day)
- No single source of truth for "what happens when"

### Why This Is a Platform Capability

| Consumer | Calendar Usage |
|---|---|
| **Academic Structure** | Term dates, holidays, break periods |
| **Exams** | Exam dates, practical schedules |
| **Attendance** | Holiday calendar (affects attendance counting) |
| **Events** | Sports day, cultural events, competitions |
| **Fees** | Due dates, late fee start dates |
| **Homework** | Assignment deadlines |
| **Communication** | Parent-teacher meeting schedules |
| **Transport** | Route schedule, holiday schedule |

### Domain Ownership

| Entity | Description |
|---|---|
| **CalendarEvent** | A dated event with time, duration, location |
| **EventType** | Classification (Holiday, Exam, Event, Meeting, Deadline) |
| **RecurrenceRule** | Repeating event pattern (daily, weekly, term-based) |
| **Schedule** | A collection of events forming a timeline |
| **ConflictRule** | Rules for detecting and resolving scheduling conflicts |
| **EventVisibility** | Who can see this event (Public, School, Class, Private) |

### School Calendar Model

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
        ├── Holidays: Diwali Break (Oct 20-25), Winter Break (Dec 22-Jan 2)
        ├── Events: Annual Day (Feb 15)
        ├── Exams: Final Exam (Mar 1-15)
        └── Fees: Term Fee Due (Oct 25)
```

### Conflict Detection

- Exam date conflicts with holiday → Flag
- Two events competing for same venue → Flag
- Assignment deadline on exam day → Flag (configurable severity)
- Teacher assigned to two events simultaneously → Flag

### Critical Rules

1. The calendar is the **single source of truth** for all date-related operations.
2. Attendance calculation must reference the calendar (holidays don't count as absences).
3. Events may be **institution-scoped** (School A events are invisible to School B).
4. Events support **visibility levels** (Public, Student-specific, Teacher-specific).
5. The framework must support **calendar export** (iCal, Google Calendar sync).

### Startup Scope (Phase 2)

- Basic event creation with date, time, type
- Academic calendar (term dates, holidays)
- Event visibility (school/public)
- Conflict detection (basic)
- Defer recurrence rules and calendar export to Phase 3

---

## C-17: Dynamic Group Management ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 2** |
| **Institution Scope** | Agnostic |
| **Ownership** | Group, GroupType, GroupMember, GroupRole |

### Purpose

**Flexible, dynamic grouping** of people and entities that cuts across the static academic structure. Schools need groups that are not tied to classes or sections:

- Remedial groups (students from different classes needing math help)
- Sports teams (football team with students from multiple grades)
- Club members (debate club, art club, music club)
- Project groups (temporary groups for assignments)
- Bus route groups (students taking the same bus)
- Interest groups (students interested in robotics)

### Why This Is a Platform Capability

| Consumer | Group Usage |
|---|---|
| **Homework** | Group assignments, project teams |
| **Communication** | Group messaging (sports team parents) |
| **Attendance** | Group-based attendance (club meetings) |
| **Events** | Group participation tracking |
| **Transport** | Bus route groups |
| **Health** | Medical condition support groups |
| **Analytics** | Group performance comparison |

### Domain Ownership

| Entity | Description |
|---|---|
| **Group** | A named collection with purpose |
| **GroupType** | Configurable classification (Remedial, Sports, Club, Project, Transport) |
| **GroupMember** | User + Group + Role within group |
| **GroupRole** | Role within a group (Member, Leader, Coordinator, Coach) |
| **GroupSchedule** | Meeting/activity schedule for the group |

### Group Types & Examples

| GroupType | Example | Cross-Class? | Temporary? |
|---|---|---|---|
| Remedial | "Math Remedial - Grade 5" | ✅ Yes | ✅ Semester |
| Sports | "Football Team" | ✅ Yes | ✅ Year |
| Club | "Debate Club" | ✅ Yes | ✅ Year |
| Project | "Science Fair Group A" | ✅ Yes | ✅ 4 weeks |
| Transport | "Bus Route 7" | ✅ Yes | ✅ Year |
| Interest | "Robotics Enthusiasts" | ✅ Yes | ✅ Ongoing |
| Class Group | "5A Project Teams" | ❌ Within class | ✅ Per assignment |

### Critical Rules

1. Groups are **dynamic** — membership may change over time.
2. Groups are **not tied to academic structure** — a group may contain students from different classes/grades.
3. Groups have **typed roles** — not every member has the same permissions within the group.
4. Groups may be **temporary with expiry** — project groups auto-dissolve after deadline.
5. Group membership is **auditable** — who joined, who left, when.
6. A user may belong to **many groups** simultaneously.

### Startup Scope (Phase 2)

- Basic group creation with type and description
- Member management (add, remove)
- Group roles (Member, Coordinator)
- Integration with Communication (group messaging)
- Defer scheduling and auto-expiry to Phase 3

---

## C-18: Bulk Operations Framework ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 2** |
| **Institution Scope** | School-Optimized |
| **Ownership** | BulkJob, BulkOperation, JobStatus, ValidationResult, ErrorRecord |

### Purpose

**Standardized bulk operations** for school administration. Schools frequently perform actions on many entities at once:

- Promote 200 students to next grade
- Assign 50 students to sections
- Send fee reminders to 500 parents
- Generate report cards for 800 students
- Transfer 30 students between sections
- Import 1000 students from spreadsheet

Without a shared framework, each module builds its own bulk operation logic — inconsistent UI, no progress tracking, no rollback, no audit trail.

### Why This Is a Platform Capability

| Consumer | Bulk Operations |
|---|---|
| **Student Management** | Bulk create, promote, transfer, archive |
| **Fees** | Bulk fee assessment, bulk reminders |
| **Attendance** | Bulk attendance marking |
| **Exams** | Bulk marks entry, grade calculation |
| **Communication** | Bulk messaging |
| **Reports** | Bulk report generation |
| **Any Module** | Data import/export |

### Domain Ownership

| Entity | Description |
|---|---|
| **BulkJob** | A bulk operation request (type, target, parameters) |
| **BulkOperationType** | Configurable operation type (Promote, Assign, Send, Generate) |
| **JobStatus** | Pending → Validating → Processing → Completed → Failed → RolledBack |
| **ValidationResult** | Pre-execution validation (errors, warnings, info) |
| **ErrorRecord** | Per-item error with entity reference and message |
| **JobAudit** | Who initiated, when, what was affected |

### Bulk Operation Lifecycle

```
Upload / Select Entities
        │
        ▼
  Validation Phase
  ├── Check permissions
  ├── Validate data
  ├── Identify errors
  └── Show preview (N items will be processed, X errors)
        │
        ▼
  Confirmation
        │
        ▼
  Execution Phase
  ├── Process items
  ├── Track progress (45/200 completed)
  ├── Handle errors per item (continue on error or fail-fast)
  └── Generate summary report
        │
        ▼
  Audit Record
  ├── Items processed: 195/200
  ├── Items failed: 5
  ├── Time taken: 45 seconds
  └── Initiator: Principal Sharma
```

### Critical Rules

1. Every bulk operation must have a **validation phase** before execution.
2. Users must see a **preview** of what will happen before confirming.
3. Progress must be **visible** — show "145/200 students processed".
4. Errors must be **per-item** — a single failure should not block the entire operation (configurable).
5. Bulk operations must be **auditable** — full record of what happened.
6. Large operations must be **async** — UI should not block while processing.
7. **Rollback capability** where feasible (operations should be designed for reversibility).

### Startup Scope (Phase 2)

- Define framework contract and interfaces in Phase 1
- Implement for Student Promotion and Bulk Fee Assessment in Phase 2

---

## C-19: Export & Document Generation Engine ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | **Important — Phase 2** (Plan in Phase 1) |
| **Institution Scope** | School-Optimized |
| **Ownership** | ReportTemplate, GeneratedDocument, ExportFormat, DataBinding |

### Purpose

**Centralized document generation and data export.** Schools generate numerous documents:

- Report cards (PDF)
- Student certificates (Transfer Certificate, Bonafide, Character)
- Fee receipts (PDF)
- ID cards
- Class lists (Excel)
- Attendance registers (PDF/Excel)
- Marksheets (PDF/Excel)
- Letters to parents (PDF)

Without a shared engine, every module builds its own PDF generation with different formatting, no template reuse, and inconsistent output.

### Why This Is a Platform Capability

| Consumer | Generated Documents |
|---|---|
| **Exams** | Report cards, marksheets, grade sheets |
| **Student Management** | TC, Bonafide, Character certificate, ID card |
| **Fees** | Fee receipts, invoices, demand letters |
| **Attendance** | Attendance registers, monthly summaries |
| **Homework** | Assignment cover sheets |
| **Reports** | Exports to PDF/Excel/CSV |

### Domain Ownership

| Entity | Description |
|---|---|
| **ReportTemplate** | Configurable document template with placeholders |
| **TemplateVariable** | Bound data field (e.g., `{{student.name}}`, `{{marks.total}}`) |
| **GeneratedDocument** | A rendered document (PDF, Excel, CSV) |
| **ExportFormat** | Supported output format (PDF, HTML, XLSX, CSV) |
| **DataBinding** | Mapping between template variables and data sources |
| **BatchGeneration** | Generate documents for many entities at once |

### Document Generation Flow

```
Select Template
  (e.g., "ReportCard – CBSE Grade 10")
       │
       ▼
  Bind Data
  ├── Student: Priya Sharma
  ├── Marks: Math 95, Science 88, ...
  ├── Attendance: 92%
  └── Grade: A+
       │
       ▼
  Render Document
  ├── Apply template
  ├── Substitute variables
  ├── Apply formatting
  └── Generate PDF
       │
       ▼
  Store in Document Framework
  └── Notify stakeholders
```

### Template Variable Examples

```
Student:      {{student.name}}, {{student.grade}}, {{student.section}}
Academic:     {{academic.year}}, {{academic.term}}
Marks:        {{marks.subject}}, {{marks.score}}, {{marks.grade}}
Attendance:   {{attendance.percentage}}
School:       {{school.name}}, {{school.address}}, {{school.logo}}
Date:         {{generated.date}}, {{generated.time}}
```

### Critical Rules

1. Templates are **configurable per institution** — each school may have its own report card format.
2. The engine must support **batch generation** — generate 500 report cards in one operation.
3. Generated documents are **stored in Document Framework** — not orphaned.
4. The engine must support **multiple output formats** — PDF for print, Excel for analysis.
5. Templates support **conditional sections** — "Show Grade only if configured."
6. Data binding is **modular** — a report card template binds to Exam data, Attendance data, and Student data.

### Startup Scope (Phase 2)

- Basic PDF generation with template support
- Variable substitution
- Integration with Document Framework for storage
- Defer batch generation and multi-format to Phase 3

---

## C-20: Task & Reminder Framework ← NEW CAPABILITY

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Medium — Phase 3 |
| **Institution Scope** | Agnostic |
| **Ownership** | Task, TaskType, TaskAssignment, Reminder, TaskStatus, TaskPriority |

### Purpose

**Shared task and reminder capability.** Students have homework tasks. Teachers have lesson planning tasks. Staff have approval tasks. Fee reminders are tasks for accounts. Without a shared framework:

- Users have fragmented task lists in different modules
- No consolidated "My To-Do" view
- Reminder logic is duplicated across modules
- Task dependencies cannot be modeled

### Why This Is a Platform Capability

| Consumer | Task Examples |
|---|---|
| **Homework** | Student tasks (assignments, submissions) |
| **Fees** | Staff tasks (follow up on defaulters) |
| **Workflow** | User tasks (pending approvals) |
| **Exams** | Student tasks (exam preparation) |
| **Events** | Coordinator tasks (event preparation) |
| **Teacher Planning** | Teacher tasks (lesson preparation) |

### Critical Rules

1. Tasks have a **type** (Homework, Approval, Reminder) and status (Pending, InProgress, Completed, Overdue).
2. Tasks may have **due dates** with configurable reminders.
3. Users see a **unified task dashboard** across all modules.
4. Tasks respect **authorization boundaries** — users only see their assigned tasks.

### Startup Scope

- Phase 3 — after core modules are operational
- Define interfaces in Phase 1 for module integration readiness

---

## C-21: Search Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Medium — Phase 3 |
| **Institution Scope** | Agnostic |
| **Ownership** | SearchIndex, SearchQuery, SearchResult, Facet, Suggestion |

### Purpose
Unified, cross-module search. Respects authorization boundaries.

### Search Scope

| Phase | Scope |
|---|---|
| Phase 1 | User search (find students, teachers by name) |
| Phase 2 | Academic search (classes, subjects, programs) |
| Phase 3 | Full-text module search (homework, assessments, documents) |

### Critical Rules

- Search respects **authorization + institution boundaries**.
- Indexing is **async** — no impact on transaction performance.
- Results are **faceted** by type, institution, date.

---

## C-22: Analytics Framework & Data Pipeline

| Attribute | Value |
|---|---|
| **Layer** | Pipeline |
| **Criticality** | Important — Phase 2 |
| **Institution Scope** | Agnostic |
| **Ownership** | DataPipeline, AnalyticsStore, ReportDefinition, Dashboard, ScheduledReport |

### Purpose
Separate analytical workloads from transactional systems.

### Data Flow

```
Transactional DB (Operational)
  │
  ▼
  ETL Pipeline (Scheduled Batch — Daily initially)
  │
  ▼
Analytics DB (Read-Optimized)
  │
  ├── School Reports
  ├── Multi-School Reports
  ├── Client Reports
  └── Platform Reports
```

### Reporting Levels

| Level | Audience | Examples |
|---|---|---|
| School | Principal, Teachers | Class attendance, fee collection, exam results |
| Multi-School | Regional Manager | Branch comparison |
| Client | Director | Aggregated metrics |
| Platform | Platform Owner | Revenue, usage, subscriptions |

### Critical Rules

1. Operational systems must **not** perform heavy analytical processing.
2. Analytics data is **read-only** for consumers.
3. Scheduled refresh (daily batch initially, real-time streaming later if needed).
4. Reports respect **authorization boundaries**.

---

## C-23: Billing Framework

| Attribute | Value |
|---|---|
| **Layer** | Pipeline |
| **Criticality** | Important — Phase 2 |
| **Institution Scope** | Agnostic |
| **Ownership** | Invoice, InvoiceLineItem, Payment, TaxRule, PricingPlan |

### Purpose
SaaS billing operations — invoicing, payments, revenue tracking.

### Billing Model

```
Client A
  ├── School A (50 students)
  ├── School B (30 students)
  └── School C (20 students)

Invoice:
  ├── Core Platform: free
  ├── Attendance Module: 3 schools × $X = $3X
  ├── Homework Module: 3 schools × $X = $3X
  ├── Fees Module: 3 schools × $X = $3X
  ├── Total Students: 100
  └── Total Amount: $9X
```

### Critical Rules

1. **Billing at Client level** — one invoice per client, itemized by institution.
2. Pricing may be **per-school, per-student, or flat** — configurable.
3. Invoices are **immutable** once generated.
4. Integrates with **Integration Framework** for payment gateway.

---

## C-24: Integration Framework

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Important — Phase 1 (payment + email) |
| **Institution Scope** | Agnostic |
| **Ownership** | IntegrationProvider, ProviderCredential, Webhook, IntegrationLog |

### Purpose
Standardized external system integration.

### Provider Abstraction

Each integration category has a **common interface**:

```
PaymentGateway (Interface)
  ├── RazorpayProvider
  ├── StripeProvider
  └── FutureGatewayProvider

EmailProvider (Interface)
  ├── SmtpProvider
  ├── SendGridProvider
  └── FutureEmailProvider
```

### Integration Categories

| Category | Phase 1 | Phase 2 | Future |
|---|---|---|---|
| Payment | Stripe / Razorpay | Multiple gateways | |
| Email | SMTP / SendGrid | SES | Mailgun |
| SMS | — | Twilio | Vonage |
| Storage | Local | S3 | Azure, GCS |
| Video | — | Zoom, Meet | |
| LMS | — | Google Classroom | Moodle |

### Critical Rules

1. Each category has a **common interface** — providers are swappable.
2. Credentials are **encrypted at rest** and **per-tenant**.
3. Webhook handling is **centralized** — one endpoint per provider type.

---

## C-25: AI Framework (Future)

| Attribute | Value |
|---|---|
| **Layer** | Service |
| **Criticality** | Future — Phase 6 |
| **Institution Scope** | Agnostic |
| **Ownership** | AIModel, InferenceResult, TrainingData, AIGuardrail |

### Purpose
Shared AI capabilities for future intelligent modules.

### Potential Capabilities

| Capability | Consumer Module | Phase |
|---|---|---|
| Lesson Generation | Lesson Planning | Phase 6 |
| Question Generation | Assessment | Phase 6 |
| Learning Gap Detection | Learning Outcomes | Phase 6 |
| Student Risk Prediction | Intervention Management | Phase 6 |
| Academic Recommendations | Student Portfolio | Phase 6 |

### Critical Rules

1. AI is a **shared platform capability** — no module builds its own AI pipeline.
2. **Data isolation** — models must not leak data across clients.
3. **Opt-in per institution** — schools choose whether to enable AI features.

---

# Part III: Gap Analysis Summary

## Gaps Identified (Missing from Original Documents)

| # | Missing Capability | Criticality | Missing From | Phase Needed |
|---|---|---|---|---|
| **G-01** | **Relationship Management Framework** | 🔴 **Critical** | All documents | **Phase 1** |
| **G-02** | **Code & Identifier Generation Engine** | 🟡 Important | All documents | Phase 1 |
| **G-03** | **Location & Address Management** | 🟡 Important | All documents | Phase 1 |
| **G-04** | **Calendar & Scheduling Framework** | 🟡 Important | All documents | Phase 2 |
| **G-05** | **Dynamic Group Management** | 🟡 Important | All documents | Phase 2 |
| **G-06** | **Bulk Operations Framework** | 🟡 Important | All documents | Phase 2 |
| **G-07** | **Export & Document Generation Engine** | 🟡 Important | All documents | Phase 2 |
| **G-08** | **Task & Reminder Framework** | 🔵 Medium | All documents | Phase 3 |
| **G-09** | **Multi-language / Localization** | 🔵 Medium | All documents | Phase 3 |
| **G-10** | **Consent & Permission (Parental)** | 🔵 Medium | All documents | Phase 3 |

## Gaps Within Existing Capabilities (Refinements to v2)

| # | Capability | Gap in v2 | Fix Applied |
|---|---|---|---|
| **R-01** | Identity & User Management | Missing UserIdentifier (Student ID, Employee ID) and UserProfile entity | Added to domain ownership |
| **R-02** | Authentication | Missing OTP-based login, LoginAttempt audit, MFA readiness | Added to roadmap & domain |
| **R-03** | Authorization | Missing Policy entity for ABAC, missing TemporaryRole with expiry | Added |
| **R-04** | Academic Structure | Missing Room/Facility, Elective, Cohort entities | Added |
| **R-05** | Communication | Missing AnnouncementTarget and Conversation role model | Added |

---

# Part IV: Updated Dependency Map

```
Level 1 (No Dependencies — Build First)
  ├── C-01: Tenant & Institution Management
  ├── C-08: Configuration Framework
  └── C-22: Analytics Framework (define data model only)

Level 2 (Depend Only on Level 1)
  ├── C-02: Identity & User Management (depends on Tenant)
  ├── C-05: Academic Structure Framework (depends on Tenant)
  ├── C-03: Authentication (depends on Tenant, Users)
  └── C-13: Location & Address Management (depends on Tenant)

Level 3 (Depend on Level 1 + 2)
  ├── C-04: Authorization (depends on Tenant, Users, Config)
  ├── C-07: Subscription Management (depends on Tenant, Config)
  ├── C-06: Relationship Management (depends on Tenant, Users) ← NEW
  ├── C-12: Code & Identifier Generation (depends on Tenant, Config) ← NEW
  └── C-11: Audit Framework (depends on Tenant, Config)

Level 4 (Depend on Level 2 + 3)
  ├── C-09: Notification Framework (depends on Users, Config, Auth)
  ├── C-10: Communication Framework (depends on Users, Relationships, Auth) ← adjusted
  ├── C-14: Document Management (depends on Tenant, Auth, Config)
  ├── C-16: Calendar & Scheduling (depends on Academic Structure, Config) ← NEW
  ├── C-17: Dynamic Group Management (depends on Users, Relationships, Auth) ← NEW
  └── C-18: Bulk Operations Framework (depends on Auth, Audit) ← NEW

Level 5 (Depend on Level 2 + 3 + 4)
  ├── C-15: Workflow Framework (depends on Auth, Notification, Config)
  ├── C-19: Export & Document Generation (depends on Document, Config) ← NEW
  ├── C-21: Search Framework (depends on Auth, Config)
  ├── C-23: Billing Framework (depends on Subscription, Tenant)
  └── C-24: Integration Framework (depends on Tenant, Config)

Level 6 (Depend on Multiple Levels)
  ├── C-20: Task & Reminder Framework (depends on Users, Notification, Calendar) ← NEW
  └── C-22: Analytics Framework (full implementation depends on all modules)

Level 7 (Future)
  └── C-25: AI Framework (depends on Analytics, Content modules)
```

---

# Part V: Refined Development Sequencing

## Phase 1 — Foundation Platform (Months 1-4)

Build the minimum platform for any business module:

| Priority | Capability | Rationale |
|---|---|---|
| **P1** | Tenant & Institution Management | Root of everything |
| **P2** | Configuration Framework | Every capability needs config |
| **P3** | Identity & User Management | Users are foundational |
| **P4** | Authentication | Login required for access |
| **P5** | Authorization | Permission control |
| **P6** | Academic Structure Framework | Grades, classes, subjects |
| **P7** | **Relationship Management** ⚡ | Parent-student links needed by Attendance/Fees/Comm |
| **P8** | Audit & Observability | Compliance requirement |
| **P9** | Notification Framework | Alerts for all modules |
| **P10** | Communication Framework | Teacher-parent messaging |
| **P11** | Document Management | File storage |
| **P12** | **Code & Identifier Generation** ⚡ | Student IDs, Receipt numbers |
| **P13** | **Location & Address Management** ⚡ | Student/school addresses |
| **P14** | Subscription Management | Module enable/disable |
| **P15** | Integration (payment + email) | External integrations |
| **P16** | Analytics Framework (model only) | Report readiness |

**Phase 1 Gate:** When these 16 are complete, business modules can begin.

## Phase 2 — Operational Enhancement (Months 5-7)

| Priority | Capability | Trigger |
|---|---|---|
| P1 | Workflow Framework | Leave Management needs approvals |
| P2 | **Calendar & Scheduling** ⚡ | Exam schedules, event management |
| P3 | **Bulk Operations Framework** ⚡ | Student promotions, bulk fee assessment |
| P4 | **Export & Document Generation** ⚡ | Report cards, certificates |
| P5 | **Dynamic Group Management** ⚡ | Sports teams, remedial groups, clubs |
| P6 | Billing Framework | Revenue automation |
| P7 | Analytics Pipeline (full) | Reporting needs grow |

## Phase 3 — Platform Maturity (Months 8-10)

| Priority | Capability | Trigger |
|---|---|---|
| P1 | Search Framework (full) | User growth |
| P2 | **Task & Reminder Framework** ⚡ | Consolidated todo across modules |
| P3 | **Multi-language / Localization** ⚡ | Regional expansion |

## Phase 4+ — Advanced

| Capability | Trigger |
|---|---|
| Curriculum Framework | Lesson Planning requires it |
| **Consent & Permission Framework** ⚡ | Field trips, data sharing require it |
| AI Framework | Academic Intelligence modules |

---

# Part VI: Capability Evolution Rules

## Rule 1: Platform-First Evaluation

Every new requirement must be evaluated in this order:

1. **Does this belong to an existing platform capability?**
   - *Example:* "Send email when homework is assigned" → Notification Framework, not Homework module.

2. **Does an existing capability need enhancement?**
   - *Example:* "Attendance needs parent-student link" → Relationship Management, not Attendance module.

3. **Is a new platform capability required?**
   - *Example:* "Multi-step approval workflows" → Define Workflow Framework.

Only after these three questions should a business module be designed.

## Rule 2: Shared Services Improvement

Every new module **must** leave the platform stronger:

| Module | Platform Improvement |
|---|---|
| Attendance | Enhances Relationship Management, Authorization |
| Homework | Enhances Notification Framework, Document Management |
| Fees | Enhances Notification, Document Generation, Integration |
| Exams | Enhances Calendar, Export Engine, Academic Structure |

## Rule 3: No Duplicate Ownership

Once a capability owns a domain:

- No module may **duplicate** that domain.
- No module may **bypass** that capability.
- No module may **redefine** entities owned by that capability.

## Rule 4: Independent Evolvability

- Capabilities evolve **without breaking** consumers.
- Modules evolve **without requiring** capability changes.
- Module requirements may **extend** a capability but must not **replace** it.

---

# Part VII: Non-Negotiable Platform Rules

| # | Rule | Violation Consequence |
|---|---|---|
| 1 | **Client isolation is mandatory.** One client's data must never leak to another. | Security incident, legal liability |
| 2 | **Authentication is centralized.** No module implements its own login. | Inconsistent security, SSO impossible |
| 3 | **Authorization is centralized.** No module implements its own permission system. | Audit gaps, permission bypass |
| 4 | **Modules are independently subscribable.** No unrelated module dependencies. | Cannot sell modules separately |
| 5 | **Platform kernel is the single source of truth.** No module duplicates kernel data. | Data inconsistency, update complexity |
| 6 | **Analytics separated from transactional workloads.** | Performance degradation |
| 7 | **Database migration paths remain open.** Business logic independent of storage topology. | Vendor lock-in, costly migration |
| 8 | **Avoid premature optimization.** Add complexity only when growth requires it. | Wasted development effort |
| 9 | **Privacy-first SaaS operations.** Platform operator access to client data is governed by strict boundaries. | Trust erosion, compliance failure |
| 10 | **Relationships between people are owned once — by Relationship Management.** Not by Attendance, not by Fees, not by Communication. | Fragmented data, maintenance burden |
| 11 | **Configuration must not require code changes.** All configurable behavior is runtime-settable. | Operations bottleneck |
| 12 | **Every module must improve shared capabilities.** No module works around platform gaps without fixing them. | Platform decay |

---

# Appendix A: Capability Classification Matrix

| ID | Capability | Layer | Criticality | Phase | New in v3? |
|---|---|---|---|---|---|
| C-01 | Tenant & Institution Management | Kernel | Critical | 1 | — |
| C-02 | Identity & User Management | Kernel | Critical | 1 | Refined |
| C-03 | Authentication | Kernel | Critical | 1 | Refined |
| C-04 | Authorization | Kernel | Critical | 1 | Refined |
| C-05 | Academic Structure Framework | Kernel | Critical | 1 | Refined |
| C-06 | **Relationship Management Framework** | **Kernel** | **Critical** | **1** | **🆕 NEW** |
| C-07 | Subscription Management | Kernel | Critical | 1 | — |
| C-08 | Configuration Framework | Kernel | Critical | 1 | — |
| C-09 | Notification Framework | Service | Critical | 1 | — |
| C-10 | Communication Framework | Service | Important | 1 | Refined |
| C-11 | Audit & Observability Framework | Kernel | Critical | 1 | — |
| C-12 | **Code & Identifier Generation Engine** | **Service** | **Important** | **1** | **🆕 NEW** |
| C-13 | **Location & Address Management** | **Service** | **Important** | **1** | **🆕 NEW** |
| C-14 | Document Management Framework | Service | Important | 1 | — |
| C-15 | Workflow Framework | Service | Important | 2 | — |
| C-16 | **Calendar & Scheduling Framework** | **Service** | **Important** | **2** | **🆕 NEW** |
| C-17 | **Dynamic Group Management** | **Service** | **Important** | **2** | **🆕 NEW** |
| C-18 | **Bulk Operations Framework** | **Service** | **Important** | **2** | **🆕 NEW** |
| C-19 | **Export & Document Generation Engine** | **Service** | **Important** | **2** | **🆕 NEW** |
| C-20 | **Task & Reminder Framework** | **Service** | **Medium** | **3** | **🆕 NEW** |
| C-21 | Search Framework | Service | Medium | 3 | — |
| C-22 | Analytics Framework & Data Pipeline | Pipeline | Important | 2 | — |
| C-23 | Billing Framework | Pipeline | Important | 2 | — |
| C-24 | Integration Framework | Service | Important | 1 | — |
| C-25 | AI Framework | Service | Future | 6+ | — |

---

# Appendix B: Capability-to-Module Dependency Matrix

Which business modules depend on which platform capabilities?

| Business Module | Tenant | Users | Auth | AuthZ | Acad | Relation | Subscr | Notif | Comm | Audit | Doc | Config | Calendar | Groups | CodeGen | Address | Workflow | BulkOps | Export | Search | Analytics |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Attendance** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | — | ✅ | — | — | — | ✅ | — | ✅ |
| **Homework** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | — | ✅ |
| **Fees** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| **Exams** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | — | ✅ | — | ✅ |
| **Parent Comm.** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | — | — | ✅ | — | — | — |
| **Timetable** | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | — | ✅ | ✅ | — | — | ✅ | — | — | — | — | — |
| **Leave Mgmt** | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | — | — | — | ✅ | — | — | — | — |
| **Lesson Plan** | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ | ✅ | — | — | — | — | ✅ | — | — | — | — |
| **Transport** | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | ✅ | — | ✅ | — | — | — | — | — |

---

# Appendix C: Glossary

| Term | Definition |
|---|---|
| **Platform Kernel** | Minimum set of shared capabilities required before any business module can function (C-01 through C-09 in Phase 1, plus C-12, C-13). |
| **Business Module** | A subscribable product that implements educational workflows (e.g., Attendance, Homework, Fees). |
| **Shared Platform Capability** | A foundational service consumed by multiple modules (e.g., Authorization, Notifications, Relationship Management). |
| **Client** | A customer organization that owns one or more institutions. |
| **Institution** | An operational educational unit (school, college, university, institute). |
| **Tenant Isolation** | The principle that one client's data must never be accessible to another client. |
| **Modular Monolith** | A single deployment with independently developable but co-deployed modules. |
| **Single Source of Truth** | Each domain entity is owned by exactly one capability — no duplicates. |
| **ABAC** | Attribute-Based Access Control — permissions based on user, resource, and environment attributes. |
| **RBAC** | Role-Based Access Control — permissions assigned to roles, users inherit via role assignment. |
| **ETL** | Extract, Transform, Load — data pipeline from operational to analytics store. |

---

> **Document:** Shared_Platform_Capabilities_v3.md  
> **Version:** 3.0 (Refined & Gap-Analyzed)  
> **Status:** Ready for technical specification  
> **Total Capabilities Defined:** 25 (18 carried forward from v2, **7 new** identified via gap analysis)  
> **Critical Gaps Found:** 10 (3 critical for Phase 1, 5 important for Phase 2, 2 medium for Phase 3)  
> **Next Step:** Proceed to detailed technical specification for each Phase 1 capability
