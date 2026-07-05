# School ERP SaaS Platform — Shared Platform Capabilities (v2)

> **Status:** Synthesis & Structured Definition  
> **Source Documents:**
> - `Functional_Requirement.md` — Full capability catalog
> - `School_ERP_Architecture_v1.md` — Architecture principles & decisions
> - `Shared_Platform_Capabilities.md` — Initial shared capability definitions
> - `StartUp_Strategy.md` — Phased delivery & startup philosophy
>
> **Purpose:** This document defines *what* each shared platform capability is, *why* it exists, *what* it owns, and *how* business modules consume it. It serves as the single source of truth for the platform foundation.

---

# Table of Contents

1. [What Are Shared Platform Capabilities?](#1-what-are-shared-platform-capabilities)
2. [Capability Inventory](#2-capability-inventory)
   - 2.1 — Tenant & Institution Management
   - 2.2 — Identity & User Management
   - 2.3 — Authentication
   - 2.4 — Authorization
   - 2.5 — Academic Structure Framework
   - 2.6 — Curriculum Framework
   - 2.7 — Subscription Management
   - 2.8 — Notification Framework
   - 2.9 — Communication Framework
   - 2.10 — Audit Framework
   - 2.11 — Document Management Framework
   - 2.12 — Configuration Framework
   - 2.13 — Workflow Framework
   - 2.14 — Search Framework
   - 2.15 — Analytics Framework & Data Pipeline
   - 2.16 — Billing Framework
   - 2.17 — Integration Framework
   - 2.18 — AI Framework *(Future)*
3. [Capability Dependency Map](#3-capability-dependency-map)
4. [Development Sequencing](#4-development-sequencing)
5. [Capability Evolution Rules](#5-capability-evolution-rules)
6. [Non-Negotiable Platform Rules](#6-non-negotiable-platform-rules)

---

# 1. What Are Shared Platform Capabilities?

## Definition

Shared platform capabilities are **foundational services** that:

- **Are consumed by** all present and future business modules (e.g., Attendance, Homework, Fees, Exams, Lesson Planning).
- **Own their domain** as the single source of truth — no business module may duplicate or bypass them.
- **Are independently evolvable** — improvements triggered by one module benefit all modules.
- **Are institution-agnostic** — designed to support schools, colleges, universities, coaching institutes, and future educational organization types.

## What They Are Not

Shared platform capabilities are **not** business modules.

| Business Modules | Platform Capabilities |
|---|---|
| Attendance | Tenant & Institution Management |
| Homework | Identity & User Management |
| Fees | Authentication |
| Exams | Authorization |
| Parent Communication | Academic Structure Framework |
| Lesson Planning | Subscription Management |
| Report Cards | Notification Framework |
| Timetable | Audit Framework |

Business modules implement *educational workflows*. Platform capabilities implement *infrastructure that all workflows share*.

## Platform-First Principle

Before any business module is built, the following must exist:

1. Tenant & Institution Management
2. Identity & User Management
3. Authentication
4. Authorization
5. Academic Structure Framework
6. Subscription Management
7. Audit Framework
8. Notification Framework
9. Configuration Framework

These nine capabilities form the **Platform Kernel** — the minimum foundation required before any business module can function.

---

# 2. Capability Inventory

---

## 2.1 Tenant & Institution Management

### Purpose

Provide multi-tenant capabilities for managing educational organizations. This capability is the **root of the platform** — every other capability and module depends on it.

### Domain Ownership

| Entity | Description |
|---|---|
| **Platform Owner** | The SaaS provider operating the platform |
| **Client** | A customer organization (school, trust, group, chain) |
| **Institution** | An operational unit (school, college, university, institute) |
| **Institution Type** | Configurable classification (School, College, University, etc.) |
| **Organizational Unit** | Hierarchy nodes: Faculties, Departments, Divisions |
| **Institution Lifecycle** | Onboarding → Active → Suspended → Archived → Terminated |

### Tenant Hierarchy

```
Platform Owner
    │
    ├── Client A
    │      ├── Institution A1 (School)
    │      ├── Institution A2 (College)
    │      └── Institution A3 (School)
    │
    └── Client B
           └── Institution B1 (University)
                  ├── Faculty of Engineering
                  │     ├── Computer Science Department
                  │     └── Mechanical Department
                  └── Faculty of Commerce
```

### Key Rules

- Every institution belongs to exactly one client.
- A client may own one or many institutions.
- Institutions cannot belong to multiple clients.
- Institution types are **configurable**, not hardcoded.
- Organizational structures are **configurable**, not hardcoded.

### Consumer Modules

- **All business modules** — every module operates within an institution context.
- **All platform capabilities** — Authorization, Subscription, Billing, etc.

### Startup Scope (Phase 1)

- Client registration and creation
- Institution creation (School only initially)
- Institution type configuration (School hardcoded initially, configurable later)
- Basic organizational structure (Grades → Classes → Sections for School)

---

## 2.2 Identity & User Management

### Purpose

Provide a **unified identity model** for all people across all institution types. A person has a single identity regardless of how many institutions or roles they are associated with.

### Domain Ownership

| Entity | Description |
|---|---|
| **User** | A person with a platform identity |
| **User Categories** | Learners, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership |
| **User Lifecycle** | Invited → Active → Suspended → Transferred → Archived |
| **Role Assignment** | One or more roles per user, scoped to institution(s) |
| **Institution Assignment** | One or more institutions a user belongs to |

### User Categories (Configurable)

| Category | Examples |
|---|---|
| **Learners** | School Student, College Student, University Student, Trainee |
| **Academic Staff** | Teacher, Lecturer, Professor, Trainer, Visiting Faculty |
| **Academic Leadership** | HOD, Principal, Dean, Academic Director, Vice Chancellor |
| **Administrative Staff** | Clerk, Accountant, HR Officer, Office Administrator |
| **Executive Leadership** | Director, Trustee, Chairman, Governing Board Member |

### Dynamic Role Management

Roles must be **configurable**, not hardcoded:

- Custom roles per institution type
- Multiple roles per user
- Institution-specific roles
- Department-level roles
- Temporary / delegated roles

### Key Rules

- A user belongs to a **Client** first, then to one or more **Institutions**.
- A user may hold **different roles** across different institutions.
- Role definitions are **configurable** — new institution types may define new roles.
- Duplicate identity management across modules is **prohibited**.

### Consumer Modules

- Attendance (who marks, who is marked)
- Homework (who assigns, who submits)
- Fees (who pays, who collects)
- Exams (who invigilates, who appears)
- All communication and notification features

### Startup Scope (Phase 1)

- User creation (Students, Parents, Teachers, Staff, Principals)
- Basic role assignment (system-defined roles initially)
- Institution assignment (single school initially)
- User lifecycle: Create → Activate → Deactivate

---

## 2.3 Authentication

### Purpose

Provide **centralized identity verification** for all users across all clients. A single authentication system serves the entire platform.

### Domain Ownership

| Capability | Description |
|---|---|
| **Login** | Verify user identity |
| **Logout** | Terminate user session |
| **Session Management** | Maintain and expire sessions |
| **Identity Provider Integration** | External IdP support |

### Supported Methods

| Method | Phase |
|---|---|
| Email & Password | Phase 1 |
| Google SSO | Phase 2 |
| Microsoft SSO | Phase 2 |
| Apple Sign-In | Future |
| SAML | Future |
| LDAP | Future |

### Client Identification

Primary strategy: **Client-specific subdomain**

```
schoola.platform.com
schoolb.platform.com
```

Each client can independently choose which authentication methods to enable.

### Key Rules

- Authentication is **centralized** — no module implements its own login.
- Authentication is **client-aware** — login identifies both the user and their client context.
- Session management is **uniform** across all modules.

### Consumer Modules

- **All modules** — every authenticated action depends on this capability.

### Startup Scope (Phase 1)

- Email & Password authentication
- Basic session management
- Client subdomain routing

---

## 2.4 Authorization

### Purpose

Control **who can access what** across the platform. Authorization must be centralized, role-based, context-aware, and institution-aware.

### Domain Ownership

| Entity | Description |
|---|---|
| **Permissions** | Granular actions a user may perform |
| **Roles** | Named collections of permissions |
| **Scope** | Organizational boundary within which a permission applies |

### Authorization Layers

| Layer | Description | Example |
|---|---|---|
| **Role Level** | What the user is allowed to do | Teacher can create homework |
| **Institution Level** | Which institutions the user can access | Teacher assigned to School A |
| **Context Level** | Specific entities the user can act on | Teacher can only edit own homework |
| **Scope Level** | Organizational boundary | HOD can access entire department |

### Authorization Scope Model

Permissions may be granted at any level of the organizational hierarchy:

- Platform Level
- Client Level
- Institution Level
- Faculty / Department Level
- Program / Grade Level
- Class / Batch Level
- Subject / Course Level

### Key Rules

- Authorization is **centralized** — no module implements its own permission checks without going through the framework.
- Permissions must be **evaluated dynamically** — combining role, institution, and context.
- Cross-institution access must be **explicitly granted** and must never cross client boundaries.

### Consumer Modules

- **All modules** — every action requires authorization.

### Startup Scope (Phase 1)

- Role-based access (Director, Principal, Teacher, Parent, Student)
- Institution-scoped permissions
- Basic context-based rules (ownership checks)

---

## 2.5 Academic Structure Framework

### Purpose

Provide a **flexible, configurable academic model** that supports multiple institution types without hardcoding school-style hierarchy assumptions.

### Domain Ownership

| Entity | School Model | College Model | University Model |
|---|---|---|---|
| **Academic Year** | Academic Year | Academic Year | Academic Year |
| **Term** | Term | Semester | Semester |
| **Grade Level** | Grade | — | — |
| **Program** | — | Program | Program |
| **Class / Batch** | Class | Batch | Batch |
| **Section** | Section | — | — |
| **Subject / Course** | Subject | Subject | Course |
| **Faculty** | — | — | Faculty |
| **Department** | Department | Department | Department |

### Hierarchy Examples

**School:**
```
Academic Year
  └── Term
       └── Grade
            └── Class
                 └── Section
                      └── Subject
```

**College:**
```
Academic Year
  └── Semester
       └── Program
            └── Batch
                 └── Subject
```

**University:**
```
Academic Year
  └── Semester
       └── Faculty
            └── Program
                 └── Batch
                      └── Course
```

### Key Rules

- Academic structures are **configurable** per institution type.
- The platform must **not assume** every institution follows a school-style hierarchy.
- All business modules consume academic structure from this framework — **no module defines its own** grade/class/subject model.

### Consumer Modules

- Attendance (class/section context)
- Homework (subject/class assignment)
- Exams (grade/program association)
- Timetable (class/teacher/room assignment)
- Lesson Planning (subject/unit association)
- All academic modules

### Startup Scope (Phase 1)

- Academic Year, Term
- Grade, Class, Section, Subject (School model hardcoded)
- Subject-group association

---

## 2.6 Curriculum Framework

### Purpose

Provide a **common curriculum model** that future learning-oriented modules (Lesson Planning, Assessment, Learning Outcomes, Portfolio) will consume.

### Domain Ownership

| Entity | Description |
|---|---|
| **Curriculum** | A structured plan of study (e.g., CBSE Grade 10, IB Diploma) |
| **Board / Standard** | Governing educational board (CBSE, ICSE, IB, Cambridge, State Board) |
| **Unit** | A major division of a curriculum |
| **Chapter / Topic** | Sub-divisions within a unit |
| **Learning Objective** | Specific skill or knowledge to be acquired |
| **Learning Outcome** | Measurable result of learning |

### Key Rules

- The Curriculum Framework is **data and structure** — it does not implement workflows (those belong in business modules).
- Learning Objectives and Outcomes are defined here but **tracked** in business modules.
- The framework must support **multiple boards and standards** simultaneously within an institution.

### Future Consumers (Phase 3+)

- Lesson Planning — references curriculum units and objectives
- Assessment — aligns assessments to objectives
- Learning Outcomes — tracks achievement against objectives
- Student Portfolio — maps evidence to outcomes

### Startup Scope (Phase 1)

- Define the data model only — no UI or workflows until Phase 3.
- Support basic curriculum structure (Units → Chapters → Topics).

---

## 2.7 Subscription Management

### Purpose

Control **which modules and features** each client has access to. This capability enables the SaaS business model.

### Domain Ownership

| Entity | Description |
|---|---|
| **Offering** | A subscribable product (module or add-on) |
| **Subscription** | A client's entitlement to one or more offerings |
| **Add-on** | An optional enhancement to an offering |
| **Trial** | Time-limited access to an offering |
| **Module Status** | Active / Inactive per client |

### Subscription Model

```
Client A:
  ├── Core Platform (always enabled)
  ├── Attendance Module (subscribed)
  ├── Homework Module (subscribed)
  └── Fees Module (subscribed)

Client B:
  ├── Core Platform (always enabled)
  ├── Attendance Module (subscribed)
  └── Exams Module (subscribed)
```

### Key Rules

- **Core Platform** is always enabled for every client (Tenant, Users, Auth, Academic Structure).
- All business modules are **individually subscribable**.
- Disabled modules must be **hidden and inaccessible**.
- Billing reflects subscribed offerings.
- No module should require subscription to an **unrelated** module.

### Consumer Modules

- **All business modules** — each module checks subscription status before allowing access.
- **Billing Framework** — consumes subscription data for invoicing.

### Startup Scope (Phase 1)

- Module-level subscription (enable/disable per client)
- Trial support
- Subscription status API for module authentication

---

## 2.8 Notification Framework

### Purpose

Provide **centralized notification delivery** across all channels. Every module sends notifications through this framework rather than implementing its own delivery.

### Domain Ownership

| Capability | Description |
|---|---|
| **Channel Management** | Configure and manage delivery channels |
| **Template Management** | Reusable notification templates |
| **Delivery** | Send notifications through configured channels |
| **Delivery Status** | Track send, delivered, read, failed status |
| **Preference Management** | User-configurable notification preferences |

### Supported Channels

| Channel | Phase |
|---|---|
| In-App Notification | Phase 1 |
| Email | Phase 1 |
| SMS | Phase 2 |
| Push Notification (Mobile) | Phase 3 |
| WhatsApp | Future |
| Voice Notifications | Future |

### Key Rules

- All modules **must** use this framework — individual notification implementations are **prohibited**.
- Users should be able to configure **channel preferences** (e.g., receive homework alerts via email, fee reminders via SMS).
- The framework must support **high-volume** delivery without blocking operational workflows.

### Consumer Modules

- Attendance (absent alerts)
- Homework (new assignment notifications)
- Fees (payment reminders, receipts)
- Exams (schedule notifications)
- Parent Communication (all parent-facing messages)
- Leave Management (approval requests)

### Startup Scope (Phase 1)

- In-App notifications
- Email delivery (basic SMTP)
- Template support

---

## 2.9 Communication Framework

### Purpose

Enable **structured, bidirectional communication** across the platform — distinct from one-way notifications.

### Domain Ownership

| Capability | Description |
|---|---|
| **Messaging** | Person-to-person and person-to-group messaging |
| **Announcements** | Institution-wide or targeted broadcasts |
| **Thread Management** | Conversation organization |
| **Read Tracking** | Acknowledgment and read receipts |

### Communication Types

| Type | Description | Examples |
|---|---|---|
| **Direct Messages** | Person-to-person | Teacher ↔ Parent |
| **Group Messages** | Person-to-group | Teacher → Class Parents |
| **Announcements** | Broadcast | Principal → All Parents |
| **Emergency Alerts** | High-priority broadcast | School closure notification |

### Key Rules

- Communication must remain **independent** from individual modules — a message about homework is still a communication, not a module feature.
- Notifications may **reference** communications (e.g., "You have a new message from the Principal"), but the communication itself lives in this framework.
- Communication must respect **institution boundaries** — cross-institution communication requires explicit permission.

### Consumer Modules

- Parent Communication (primary consumer)
- All modules that generate person-to-person interaction

### Startup Scope (Phase 1)

- Basic teacher-parent messaging
- School announcements
- Thread-based conversations

---

## 2.10 Audit Framework

### Purpose

Record **who did what, when, and where** across the platform. Every significant action must be auditable.

### Domain Ownership

| Field | Description |
|---|---|
| **Actor** | Who performed the action (user ID) |
| **Action** | What was done (e.g., `homework.created`, `fee.collected`) |
| **Target** | Which entity was affected (entity type + ID) |
| **Timestamp** | When the action occurred |
| **Context** | Client, Institution, Academic Year |
| **Changes** | What changed (before/after values) |
| **IP / Device** | Where the action originated |

### Audit Levels

| Level | Description | Retention |
|---|---|---|
| **Critical** | Security, billing, compliance events | Long-term (5+ years) |
| **Operational** | Business transactions (fee collection, exam marks) | Medium (2 years) |
| **Activity** | Routine actions (viewed report, logged in) | Short (90 days) |

### Key Rules

- Audit logging must be **non-repudiable** — records cannot be altered or deleted.
- Audit must not significantly impact **transaction performance** — consider async/queue-based logging.
- Audit data must be **queryable** for compliance and investigation.

### Consumer Modules

- **All modules** — every module must emit audit events for significant actions.

### Startup Scope (Phase 1)

- Basic audit trail for key actions
- Configurable retention per audit level
- Queryable audit log for administrators

---

## 2.11 Document Management Framework

### Purpose

Provide **unified file and document storage** across the platform. No module should manage files independently.

### Domain Ownership

| Capability | Description |
|---|---|
| **File Storage** | Upload and store files (local or cloud) |
| **File Retrieval** | Download and preview files |
| **File Organization** | Folders, categories, tags |
| **Version Management** | Track file revisions |
| **Access Control** | Who can view/download/edit each file |

### Document Types (Examples)

| Module | Documents |
|---|---|
| Homework | Assignment attachments, submitted files |
| Student Management | Photos, ID documents, certificates |
| Fees | Receipts, invoices |
| Exams | Question papers, answer sheets |
| Report Cards | Generated PDF report cards |
| Learning Content | Worksheets, presentations, videos |

### Key Rules

- All file storage flows through this framework — **no module manages its own files**.
- Document access must respect **institution boundaries**.
- Storage provider should be **configurable** (local → S3 → Azure Blob) without application changes.

### Startup Scope (Phase 1)

- Basic file upload and download
- Institution-scoped storage
- Local filesystem storage (migrate to cloud later)

---

## 2.12 Configuration Framework

### Purpose

Enable **configurable behavior** across the platform without requiring code changes or redeployment.

### Domain Ownership

| Level | Description | Examples |
|---|---|---|
| **Platform** | Global platform settings | Default notification channels, audit retention |
| **Client** | Per-client configuration | Branding, default language, timezone |
| **Institution** | Per-institution configuration | Academic calendar, grading scale, attendance rules |
| **Module** | Per-module configuration | Homework submission deadline rules, late fee calculation |

### Configuration Types

| Type | Description |
|---|---|
| **Feature Toggle** | Enable/disable features per tenant |
| **Business Rules** | Configurable workflow rules (e.g., "auto-approve leave under 3 days") |
| **Display Settings** | Locale, date format, number format |
| **Integration Settings** | API keys, endpoint URLs per tenant |

### Key Rules

- Configuration changes must **not require code deployment**.
- Configuration must be **tenant-aware** — settings at platform, client, and institution levels with inheritance.
- Business logic must **never hardcode behavior** that should be configurable.

### Consumer Modules

- **All modules** — every module reads configuration from this framework.

### Startup Scope (Phase 1)

- Basic key-value configuration store
- Platform-level and institution-level settings
- Feature flags

---

## 2.13 Workflow Framework

### Purpose

Provide a **configurable approval and review workflow engine** used by multiple modules.

### Domain Ownership

| Capability | Description |
|---|---|
| **Workflow Definition** | Define steps, roles, and transitions |
| **Workflow Instance** | Track a specific item through its workflow |
| **Approval / Rejection** | Decision points with configured approvers |
| **Escalation** | Automatic escalation on timeout |
| **Notifications** | Trigger notifications at workflow steps |

### Future Workflow Consumers

| Module | Workflow Examples |
|---|---|
| Leave Management | Leave request → HOD approval → Principal approval |
| Fee Management | Fee waiver request → Finance approval → Principal approval |
| Assessment | Assessment review → HOD approval |
| Lesson Planning | Lesson plan → Department review → Principal approval |
| Admission | Application → Review → Approval |

### Key Rules

- Workflows must be **configurable per institution** — not hardcoded.
- The framework provides the engine; modules define their workflow templates.
- Notifications at each step should use the Notification Framework.

### Startup Scope (Phase 1)

- Define the **data model and engine interface** only.
- Implement basic approval workflow for **Leave Management** (Phase 2 launch).
- Expand to other modules in later phases.

---

## 2.14 Search Framework

### Purpose

Provide **unified, cross-module search** capabilities.

### Domain Ownership

| Capability | Description |
|---|---|
| **Indexing** | Build and maintain search indexes |
| **Query** | Full-text and filtered search |
| **Ranking** | Relevance-based result ordering |
| **Faceting** | Filter results by type, institution, date |

### Search Scope (Future)

- People: Students, Teachers, Staff, Parents
- Academics: Classes, Subjects, Programs
- Module Data: Homework, Assessments, Documents, Fees

### Key Rules

- Search must respect **authorization boundaries** — users only see results they are permitted to access.
- Search must respect **institution boundaries**.
- Indexing should be **async** to avoid impacting transaction performance.

### Startup Scope (Phase 1)

- Define the **search interface** and indexing contract.
- Basic user search (find students, teachers by name).
- Full implementation deferred to post-MVP.

---

## 2.15 Analytics Framework & Data Pipeline

### Purpose

Separate **operational workloads** from **analytical/reporting workloads**. Provide dashboards, reports, and business intelligence without degrading transactional performance.

### Domain Ownership

| Capability | Description |
|---|---|
| **Data Pipeline** | Extract, transform, and load data from operational systems to analytics store |
| **Reporting Engine** | Generate operational and management reports |
| **Dashboard Engine** | Render configurable dashboards |
| **Analytics Store** | Dedicated read-optimized data store |
| **Scheduled Processing** | Batch and scheduled data refresh |

### Data Flow

```
Transactional Systems
  (Attendance, Fees, Homework, Exams)
          │
          ▼
  Data Pipeline (Scheduled Batch)
          │
          ▼
  Analytics Store (Read-Optimized)
          │
          ├── School Reports (Attendance, Fees, Exams)
          ├── Multi-School Reports (Cross-school comparison)
          ├── Client Reports (Aggregated across institutions)
          └── Platform Reports (Usage, Revenue, Subscriptions)
```

### Reporting Levels

| Level | Audience | Examples |
|---|---|---|
| **School** | Principal, Teachers | Class attendance, fee collection, exam results |
| **Multi-School** | Regional Manager | Branch comparison, regional performance |
| **Client** | Director | Aggregated metrics across all schools |
| **Platform** | Platform Owner | Subscription analytics, revenue, usage |

### Key Rules

- Operational systems must **not** perform heavy analytical processing.
- Analytics data is generated through **scheduled batch processing** (daily initially).
- Reports must respect **authorization boundaries** — users only see data they are permitted to access.
- The analytics store is **read-only** for consumers.

### Startup Scope (Phase 1)

- Define the **analytics data model** and pipeline interface.
- Basic operational reports (attendance summary, fee collection).
- Daily batch refresh.
- Full analytics capabilities expand with each module.

---

## 2.16 Billing Framework

### Purpose

Manage **SaaS billing operations** — invoicing, usage tracking, and revenue management.

### Domain Ownership

| Capability | Description |
|---|---|
| **Invoice Generation** | Create invoices based on subscriptions |
| **Usage Tracking** | Track module usage for usage-based billing |
| **Pricing Model** | Define and manage pricing per offering |
| **Payment Reconciliation** | Track payments against invoices |
| **Tax Management** | Handle applicable taxes per region |

### Billing Model

```
Client A
  ├── School A
  ├── School B
  └── School C

Invoice:
  - Attendance Module: $X
  - Homework Module:  $Y
  - Fees Module:      $Z
  - Total Students:   1200
  - Consolidated Amount: $X + $Y + $Z
```

### Key Rules

- **Billing ownership exists at the Client level** — one client receives one invoice.
- Invoice may include charges from **multiple institutions** under the same client.
- Institution-level usage may be **itemized** on the invoice.
- Billing data must be **immutable** for audit purposes.

### Consumers

- **Platform Operations** — invoicing, revenue tracking.
- **Subscription Management** — pricing and plan changes.

### Startup Scope (Phase 2)

- Basic invoice generation based on subscribed modules.
- Manual payment reconciliation initially.
- Automated billing deferred until sufficient transaction volume.

---

## 2.17 Integration Framework

### Purpose

Provide a **standardized approach** for integrating with external systems, enabling the platform to connect with third-party services without module-specific implementations.

### Domain Ownership

| Capability | Description |
|---|---|
| **Provider Abstraction** | Common interface for each integration category |
| **Credential Management** | Secure storage of API keys and secrets |
| **Webhook Management** | Incoming and outgoing webhook handling |
| **Rate Limiting** | Manage external API rate limits |
| **Retry & Error Handling** | Resilient integration patterns |

### Integration Categories

| Category | Phase 1 | Future |
|---|---|---|
| **Payment Gateways** | Razorpay / Stripe | Multiple gateways |
| **Email Providers** | SMTP / SendGrid | SES, Mailgun |
| **SMS Providers** | — | Twilio, Vonage |
| **Video Platforms** | — | Zoom, Google Meet |
| **Learning Platforms** | — | Google Classroom, Moodle |
| **Storage Providers** | Local filesystem | S3, Azure Blob, GCS |

### Key Rules

- Each integration category must have a **common abstraction** so providers can be swapped.
- Credentials are stored **securely** and **per-tenant**.
- Module-specific integrations (e.g., a specific learning platform) should still use this framework's provider abstraction where possible.

### Startup Scope (Phase 1)

- Payment gateway integration (single provider)
- Email provider integration (single provider)
- Provider abstraction interface defined for future categories

---

## 2.18 AI Framework (Future)

### Purpose

Provide **shared AI/ML capabilities** that future intelligent modules will consume. AI should be a platform capability, not embedded within individual modules.

### Domain Ownership (Future)

| Capability | Description |
|---|---|
| **Content Generation** | Lesson plans, questions, assessments |
| **Prediction Engine** | Student risk analysis, learning gap detection |
| **Recommendation Engine** | Academic recommendations, parent insights |
| **Model Management** | Model versioning, A/B testing |
| **Usage Tracking** | Monitor AI usage for cost management |

### Potential Capabilities

| Capability | Consumer Module | Phase |
|---|---|---|
| Lesson Generation | Lesson Planning | Phase 6 |
| Question Generation | Assessment / Exam | Phase 6 |
| Assessment Generation | Assessment | Phase 6 |
| Learning Gap Detection | Learning Outcomes | Phase 6 |
| Student Risk Prediction | Intervention Management | Phase 6 |
| Academic Recommendations | Student Portfolio | Phase 6 |
| Parent Insights | Parent Communication | Phase 6 |
| Teacher Assistant | Multiple modules | Phase 6 |

### Key Rules

- AI capabilities must be **shared** — no module builds its own AI pipeline.
- AI must respect **data isolation** — models must not leak data across clients.
- AI usage must be **auditable** and **controllable** (opt-in per institution).

### Startup Scope

- **Not built in Phase 1.** Define the framework contract and interfaces.
- Implementation begins in Phase 6 (AI-Powered Education Platform).

---

# 3. Capability Dependency Map

This map shows which capabilities depend on which. Capabilities with no dependencies must be built first.

```
Level 1 (No Dependencies — Build First)
  ├── Tenant & Institution Management
  └── Configuration Framework

Level 2 (Depend Only on Level 1)
  ├── Identity & User Management (depends on Tenant)
  ├── Academic Structure Framework (depends on Tenant)
  └── Audit Framework (depends on Tenant, Config)

Level 3 (Depend on Level 1 + 2)
  ├── Authentication (depends on Tenant, User Management)
  ├── Authorization (depends on Tenant, User Management, Config)
  ├── Subscription Management (depends on Tenant, Config)
  └── Document Management (depends on Tenant, Authorization)

Level 4 (Depend on Level 1 + 2 + 3)
  ├── Notification Framework (depends on Tenant, User Management, Config)
  ├── Workflow Framework (depends on Authorization, Notification, Config)
  └── Search Framework (depends on Authorization, Config)

Level 5 (Depend on Multiple Lower Levels)
  ├── Communication Framework (depends on Notification, User Management, Authorization)
  ├── Analytics Framework (depends on all operational modules)
  ├── Billing Framework (depends on Subscription, Tenant)
  └── Integration Framework (depends on Tenant, Config)

Level 6 (Future)
  └── AI Framework (depends on Analytics, Content modules)
```

---

# 4. Development Sequencing

## Phase 1 — Foundation (Platform Kernel)

**Objective:** Build the minimum set of capabilities that every business module requires.

| Order | Capability | Delivers |
|---|---|---|
| 1 | Tenant & Institution Management | Multi-tenant foundation |
| 2 | Configuration Framework | Configurable behavior |
| 3 | Identity & User Management | User identity and lifecycle |
| 4 | Authentication | Login, logout, sessions |
| 5 | Authorization | Role and permission management |
| 6 | Academic Structure Framework | Grades, classes, subjects, terms |
| 7 | Subscription Management | Module enable/disable per client |
| 8 | Audit Framework | Action tracking |
| 9 | Notification Framework | In-app and email notifications |
| 10 | Communication Framework | Teacher-parent messaging, announcements |
| 11 | Document Management Framework | File upload and storage |
| 12 | Analytics Framework | Basic reporting and dashboards |
| 13 | Integration Framework | Payment gateway, email provider |

**When this is complete:** Business module development (Attendance, Homework, Fees, Parent Communication) can begin.

## Phase 2 — Operational Expansion

| Capability | Trigger |
|---|---|
| Workflow Framework | Leave Management requires it |
| Billing Framework | Subscription revenue needs automation |
| Search Framework (basic) | User growth makes search necessary |

## Phase 3+ — Advanced Capabilities

| Capability | Trigger |
|---|---|
| Curriculum Framework | Lesson Planning requires it |
| AI Framework | Academic Intelligence modules require it |
| Advanced Analytics | Reporting needs exceed batch processing |

---

# 5. Capability Evolution Rules

## Rule 1: Platform-First Evaluation

Every new requirement must first be evaluated:

1. **Does this belong to an existing platform capability?**
   - *Example:* "Send email when homework is assigned" → Notification Framework, not Homework module.

2. **Does an existing capability need enhancement?**
   - *Example:* "Attendance needs richer permissions" → Enhance Authorization Framework, not just Attendance.

3. **Is a new platform capability required?**
   - *Example:* "Multi-step approval process" → If no existing capability covers it, define a new Workflow Framework.

Only after answering these questions should a new business module be designed.

## Rule 2: Shared Services Improvement

Every new module **must** improve the platform.

- *Example:* Homework requires richer permissions → Authorization Framework is improved, benefiting all modules.
- *Example:* Fees requires better notifications → Notification Framework is improved, benefiting all modules.

This ensures the platform continuously becomes stronger as modules are added.

## Rule 3: No Duplicate Ownership

Once a platform capability owns a domain:

- No business module may **duplicate** that domain.
- No business module may **bypass** that capability.
- No business module may **redefine** entities owned by that capability.

## Rule 4: Independent Evolvability

- Platform capabilities must evolve **without breaking** consuming modules.
- Consuming modules must evolve **without requiring** platform capability changes.
- New module requirements may **extend** a capability but must not **replace** it.

---

# 6. Non-Negotiable Platform Rules

These rules govern all shared platform capability development:

| # | Rule |
|---|---|
| 1 | **Client isolation is mandatory.** Data belonging to one client must never be visible to another. |
| 2 | **Authentication is centralized.** No module implements its own login. |
| 3 | **Authorization is centralized.** No module implements its own permission system. |
| 4 | **Modules remain independently subscribable.** No module should require subscription to an unrelated module. |
| 5 | **Shared platform kernel is the single source of truth.** No module duplicates platform data. |
| 6 | **Analytics are separated from transactional workloads.** Operational systems must not perform heavy analytical processing. |
| 7 | **Database migration paths must remain open.** Business logic must not depend on physical storage strategy. |
| 8 | **Avoid premature optimization.** Add complexity only when measurable business growth requires it. |
| 9 | **Privacy-first SaaS operations.** Platform owner access to client data must be governed by strict boundaries. |
| 10 | **Business logic must remain independent from storage topology.** Tenant isolation strategy may change without code rewrites. |
| 11 | **Configuration must not require code changes.** All configurable behavior must be runtime-configurable. |
| 12 | **Every module must improve shared capabilities.** No module is allowed to work around platform gaps without fixing them. |

---

# Appendix A: Capability vs. Module Decision Matrix

When deciding whether something is a platform capability or a business module:

| Question | Platform Capability | Business Module |
|---|---|---|
| Is it used by multiple modules? | ✅ Yes | ❌ No (or minimal) |
| Does it own a core domain entity? | ✅ Yes (Users, Classes, Roles) | ❌ Uses, doesn't own |
| Does it provide infrastructure? | ✅ Yes | ❌ No |
| Does it implement educational workflow? | ❌ No | ✅ Yes |
| Is it independently subscribable? | ❌ Always included | ✅ Optional |
| Does it require per-module customization? | ❌ Generic by design | ✅ Module-specific |

---

# Appendix B: Glossary

| Term | Definition |
|---|---|
| **Platform Kernel** | The minimum set of shared capabilities required before any business module can function (Capabilities 2.1–2.9). |
| **Business Module** | A subscribable product that implements educational workflows (e.g., Attendance, Homework, Fees). |
| **Shared Platform Capability** | A foundational service consumed by multiple modules (e.g., Authorization, Notifications, Audit). |
| **Client** | A customer organization that owns one or more institutions. |
| **Institution** | An operational educational unit (school, college, university, institute). |
| **Tenant Isolation** | The principle that one client's data must never be accessible to another client. |
| **Modular Monolith** | A single deployment with independently developable but co-deployed modules. |
| **Single Source of Truth** | Each domain entity is owned by exactly one capability — no duplicates. |

---

> **Document Version:** 2.0  
> **Based On:** Functional_Requirement.md, School_ERP_Architecture_v1.md, Shared_Platform_Capabilities.md, StartUp_Strategy.md  
> **Next Step:** Proceed to detailed technical specification for each Phase 1 capability.
