# School ERP SaaS Platform - Architecture & Analysis Document (v1)

> Status: Analysis Phase Only  
> Scope: Finalized decisions and principles only. No implementation details.

---

# 1. Vision

Build a multi-tenant School ERP SaaS platform where schools can subscribe to required offerings while sharing a common platform foundation.

The platform will support:

- Attendance
- Homework
- Fees
- Parent Communication
- Exam & Grading
- Principal Dashboard
- Teacher Planning & Teaching Preparation
- Additional future offerings

All offerings must be independently developable while sharing common platform services.

---

# 2. Core Architectural Principles

## 2.1 Modular by Design

Each offering must:

- Be independently developable
- Be independently deployable in the future
- Be independently subscribable by clients
- Share common platform services

## 2.2 Platform First

Before any business module:

1. Tenant Management
2. Identity & Access Management
3. Academic Structure
4. User Management
5. Audit Framework
6. Notification Framework
7. Subscription Framework

must be defined.

## 2.3 Avoid Premature Optimization

Architecture decisions should remain simple until measurable business growth requires additional complexity.

---

# 3. Tenant Hierarchy

```text
Platform Owner (SaaS Provider)
    │
    ├── Client A
    │      ├── School A1
    │      └── School A2
    │
    ├── Client B
    │      └── School B1
    │
    └── Client C
           ├── School C1
           ├── School C2
           └── School C3
```

## Definitions

### Platform Owner

Owns and operates the SaaS platform.

Responsibilities:

- Platform operations
- Billing
- Client onboarding
- Subscription management
- Support

### Client

A customer organization.

Examples:

- Single school
- School chain
- Educational trust
- Educational group

### School

Operational unit where ERP functions are used.

# 3.1 Multi-School Client Model

## Overview

The platform must support clients that operate one or more schools under a single subscription.

Examples include:

* Educational trusts
* School groups
* Foundations
* Franchise school networks
* Organizations managing multiple campuses

A client may onboard:

* A single school
* Multiple schools simultaneously
* Additional schools at a later date

The system must support client growth without requiring tenant restructuring.

---

## Client-to-School Relationship

A client acts as the administrative and billing owner.

A school acts as an operational unit.

Relationship:

```text
Client
  ├── School A
  ├── School B
  ├── School C
  └── School D
```

Rules:

* Every school belongs to exactly one client.
* A client may own one or many schools.
* Schools cannot belong to multiple clients.
* School ownership may only change through an approved migration process.

---

# 4.4 Multi-School Isolation Requirements

## School-Level Isolation

Each school is treated as an independent operational entity.

By default:

* Teachers only access their assigned school.
* Students only access their own school.
* Parents only access students belonging to their school.
* School administrators only manage their assigned school.

Data must remain isolated between schools even when those schools belong to the same client.

Examples:

* Attendance records
* Homework
* Fee transactions
* Examination data
* Parent communication
* Teacher planning content

---

## Cross-School Access

Certain users may require access across multiple schools.

Examples:

* Client Director
* Regional Manager
* Group Academic Head
* Finance Controller

These users may be granted access to:

* Selected schools
* All schools under a client

Cross-school access must never extend outside the client's organization.

---

## School Access Assignment

User access must be configurable at school level.

Examples:

Teacher:

* School A only

Principal:

* School B only

Regional Academic Head:

* School A + School B + School C

Client Director:

* All schools under the client

Access assignments must remain independent from role definitions.

---

# 6.1 Multi-School User Management Principles

The platform must support users operating across multiple schools.

Examples:

* Teacher teaching in multiple branches
* Finance manager handling multiple schools
* Director overseeing all schools

A user should maintain a single identity while receiving different permissions across assigned schools.

---

# 9.1 Subscription and School Expansion

Clients may add schools after initial onboarding.

Requirements:

* New schools inherit client ownership.
* Existing subscription remains active.
* Additional billing may be calculated based on pricing model.
* Existing users may be granted access to newly created schools.

The onboarding process for additional schools must not require creation of a new client account.

---

# 14.1 Cross-School Reporting

The platform must support reporting at multiple levels.

## School View

Reports for a single school.

Examples:

* Attendance
* Fees
* Examination performance

## Multi-School View

Reports covering selected schools.

Examples:

* Region-wise performance
* Branch comparison

## Client View

Aggregated reporting across all schools belonging to a client.

Examples:

* Total student count
* Total fee collection
* Attendance trends
* Academic performance summaries

Only users with appropriate permissions may access multi-school or client-level reporting.

---

# 16.1 Unified Billing

Billing ownership exists at client level.

Requirements:

* One client receives one invoice.
* Invoice may include charges from multiple schools.
* School-level usage may be itemized.
* Billing remains consolidated under the client account.

Examples:

Client A
├─ School A
├─ School B
└─ School C

Invoice:

* Attendance Module
* Fees Module
* Homework Module
* Total students across all schools
* Consolidated amount payable

The billing relationship exists between the platform and the client, not between the platform and individual schools.

---

# 4. Data Isolation Principles

## 4.1 Client Isolation (Non-Negotiable)

Data belonging to one client must never be visible to another client.

Examples:

- Students
- Attendance
- Fees
- Exams
- Homework
- Parent communications

## 4.2 School Isolation

Within a client:

- Users only access assigned schools
- Cross-school access must be explicitly granted

## 4.3 Cross-School Visibility

Allowed only for approved roles such as:

- Client Director
- Regional Administrator
- Group Management

Access remains restricted to schools owned by the same client.

---

# 5. Identity & Access Management

## 5.1 Centralized Authentication

A single platform authentication system serves all clients.

Benefits:

- Consistent login experience
- Simplified administration
- Easier compliance
- Lower operational cost

## 5.2 Per-Client Authentication Configuration

Each client can independently choose:

- Email & Password
- Google SSO
- Microsoft SSO

Future possibilities:

- Apple Sign-In
- SAML
- LDAP

## 5.3 Client Identification Strategy

Primary strategy:

- Client-specific subdomain

Example:

```text
schoola.platform.com
schoolb.platform.com
```

## 5.4 Authorization Model

Authorization combines:

### Role-Based Access Control

Examples:

- Director
- Principal
- Teacher
- Parent
- Student

### Attribute-Based Access Control

Additional constraints such as:

- Assigned school
- Assigned class
- Academic year
- Ownership rules

---

# 6. User Ownership Model

Users belong to a Client first.

Users may then belong to:

- One school
- Multiple schools

Examples:

- Teacher teaching in multiple schools
- Director managing multiple schools

---

# 7. Common Platform Kernel

The following are shared across every offering.

## Academic Structure

- Academic Year
- Term
- Grade
- Class
- Section
- Subject

## Identity

- Users
- Roles
- Permissions

## Organization

- Client
- School

## Platform Services

- Notifications
- Audit Logs
- Configuration
- Subscription Management

These components become the system's source of truth.

---

# 8. SaaS Offering Framework

## Core Platform

Every client receives:

- School setup
- Academic structure
- User management
- Authentication
- Authorization

## Optional Offerings

Clients may subscribe to any combination.

Examples:

- Attendance
- Homework
- Fees
- Exams
- Parent Communication
- Teacher Planning

No offering should require unrelated offerings.

---

# 9. Module Subscription Model

Each client controls:

- Enabled modules
- Disabled modules

Examples:

### Client A

- Attendance ✓
- Homework ✓
- Fees ✓

### Client B

- Attendance ✓
- Fees ✗
- Homework ✗

### Client C

- Attendance ✗
- Homework ✓
- Exams ✓

Platform behavior:

- Disabled modules remain hidden.
- Disabled modules are inaccessible.
- Billing reflects subscribed offerings.

---

# 10. Module Dependency Principles

Dependencies must remain minimal.

## Shared Dependencies

Every offering may depend on:

- Academic Structure
- Users
- Schools
- Authorization

## Aggregation Modules

Some modules consume data from others.

Example:

Principal Dashboard

May aggregate:

- Attendance
- Fees
- Exams
- Homework

Aggregation modules should not become mandatory dependencies.

---

# 11. Database Strategy

## Current Decision

Start with:

### Shared Database

### Shared Tables

### Strong Tenant Isolation

Reasons:

- Lowest operational cost
- Fastest development
- Ideal for SaaS startup stage

## Migration Readiness Requirement

Future migration paths must remain possible.

### Path 1

```text
Shared Tables
    → Separate Schema
```

### Path 2

```text
Separate Schema
    → Separate Database
```

### Path 3

```text
Shared Tables
    → Separate Database
```

Business logic must not depend on physical storage strategy.

---

# 12. Coding Standards for Migration Readiness

All future development must assume that tenant storage strategy may change.

Requirements:

- Tenant-aware architecture
- Tenant-aware repositories
- No business logic tied to storage model
- No assumptions about table location
- No assumptions about database topology

Objective:

Migration should require infrastructure changes, not business logic rewrites.

---

# 13. Analytics Strategy

## Decision

Use a dedicated analytics data store populated through batch processing.

## Rationale

Keeps transactional systems simple.

Avoids:

- Complex indexing strategies
- Materialized view management
- Premature database optimization

## Data Flow

```text
Transactional Data
        ↓
Batch Processing
        ↓
Analytics Store
        ↓
Dashboards & Reports
```

## Reporting Sources

### Transactional System

Operational workflows:

- Attendance marking
- Fee collection
- Homework creation

### Analytics System

Reporting workflows:

- Director dashboards
- Usage metrics
- Business reporting
- Trend analysis

## Refresh Strategy

Initial recommendation:

- Daily batch processing

---

# 14. Platform Analytics Principles

Platform analytics must be separated from client operational data.

Platform Owner should primarily view:

- Client counts
- School counts
- Subscription metrics
- Usage metrics
- Revenue metrics

Student-level operational data should not be required for platform management.

---

# 15. Platform Director Access Boundaries

Platform Owner responsibilities:

- Manage platform
- Manage subscriptions
- Manage billing
- Manage onboarding
- Manage support

Platform Owner access should be governed by privacy-first principles.

---

# 16. School Onboarding Framework

Standard onboarding flow:

```text
Client Registration
        ↓
Client Creation
        ↓
School Creation
        ↓
Administrator Creation
        ↓
Module Selection
        ↓
Configuration
        ↓
Go Live
```

---

# 17. Development Sequencing Principles

Build foundational capabilities before business modules.

Recommended order:

1. Tenant Management
2. Authentication
3. Authorization
4. User Management
5. Academic Structure
6. Subscription Management
7. Attendance
8. Homework
9. Fees
10. Exams
11. Parent Communication
12. Teacher Planning
13. Principal Dashboard

---

# 18. Future Evolution Triggers

Do not add complexity before it becomes necessary.

Potential future upgrades:

- Separate schema per client
- Separate database per enterprise client
- Regional deployments
- Enterprise authentication options
- Dedicated infrastructure for premium customers

Adoption and performance metrics should drive these decisions.

---

# 19. Non-Negotiable Rules

1. Client isolation is mandatory.
2. Authentication is centralized.
3. Authorization is centralized.
4. Modules remain independently subscribable.
5. Shared platform kernel remains the single source of truth.
6. Analytics are separated from transactional workloads.
7. Database migration paths must remain open.
8. Avoid premature optimization.
9. Privacy-first SaaS operations.
10. Business logic must remain independent from storage topology.

---

# Document Status

Version: 1.0

Contains only finalized architecture and analysis decisions discussed so far.
