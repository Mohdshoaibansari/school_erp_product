# School ERP SaaS Platform - Shared Platform Capabilities

## Purpose

This document defines the shared platform capabilities that form the foundation of the School ERP SaaS platform.

These capabilities are not business modules.

Instead, they are platform services used by all present and future modules.

Examples:

* Attendance
* Homework
* Fees
* Examination
* Lesson Planning
* Curriculum Management
* Learning Outcomes
* Student Portfolio

must consume these capabilities rather than implementing their own versions.

---

# 1. Platform Capability Principles

## Single Source of Truth

Each shared capability should own its domain.

Examples:

* User Management owns users.
* Academic Structure owns classes and subjects.
* Authorization owns permissions.

Business modules must consume these capabilities rather than duplicate them.

---

## Reusable Across Modules

Every capability should be designed for platform-wide reuse.

Example:

Notification capability should be used by:

* Attendance
* Homework
* Fees
* Examination
* Parent Communication

rather than each module building separate notification systems.

---

## Evolvable

Platform capabilities must evolve as new modules are introduced.

New module requirements may extend a capability but must not replace it.

---

# 2. Tenant & Institution Management

## Purpose

Provide multi-tenant capabilities for managing educational organizations.

The platform must support various institution types without requiring architectural changes.

---

## Institution Types

The platform should support:

* School
* College
* University
* Coaching Institute
* Training Institute
* Corporate Learning Center
* Future Educational Organizations

Institution types should be configurable rather than hardcoded.

---

## Tenant Hierarchy

```text
Platform
    │
    ├── Client
    │
    ├── Institution
    │     ├── School
    │     ├── College
    │     ├── University
    │     └── Other Institution Types
    │
    └── Organizational Structure
```

---

## Responsibilities

Manage:

* Clients
* Institutions
* Institution Types
* Institution Lifecycle
* Institution Configuration
* Organizational Structures

---

# New Section 2.1 Organizational Structure Framework

## Purpose

Provide a flexible organizational model that supports different educational institutions.

The platform must avoid hardcoded organizational assumptions.

---

## Examples

### School

```text
School
 ├── Science Department
 ├── Mathematics Department
 └── Administration
```

### College

```text
College
 ├── Computer Science Department
 ├── Mechanical Department
 ├── Commerce Department
 └── Administration
```

### University

```text
University
 ├── Faculty of Engineering
 │     ├── Computer Science
 │     └── Mechanical
 │
 ├── Faculty of Commerce
 │
 └── Administration
```

---

## Responsibilities

Manage:

* Faculties
* Departments
* Divisions
* Academic Units
* Administrative Units
* Organizational Hierarchies

---

# 3. Authentication

## Purpose

Provide centralized identity verification.

---

## Responsibilities

Support:

* Login
* Logout
* Session Management
* Identity Verification

---

## Authentication Methods

Current:

* Email & Password
* Google SSO
* Microsoft SSO

Future:

* Apple Sign-In
* SAML
* LDAP

---

## Design Principle

Authentication should be centralized and shared across all modules.

---

# 4. Authorization

## Purpose

Control access to system capabilities.

---

## Responsibilities

Determine:

* Who can access a feature
* Which schools can be accessed
* Which actions can be performed

---

## Authorization Layers

### Tenant Level

Access to client information.

### School Level

Access to individual schools.

### Role Level

Access based on assigned role.

### Context Level

Access based on ownership and assignment.

---

## Example Roles

* Client Director
* Principal
* Teacher
* Parent
* Student

## Organizational Scope Access

Permissions may be granted at:

* Institution Level
* Faculty Level
* Department Level
* Program Level
* Class Level
* Subject Level

---

## Examples

Teacher

* Access only assigned classes.

Lecturer

* Access only assigned courses.

Dean

* Access entire faculty.

Principal

* Access entire school.

Director

* Access all institutions under a client.
---

# 5. Identity & User Management

## Purpose

Provide a unified identity model across all institution types.

The platform should manage people rather than institution-specific user types.

---

## User Categories

### Learners

Examples:

* School Student
* College Student
* University Student
* Trainee

---

### Academic Staff

Examples:

* Teacher
* Lecturer
* Professor
* Trainer
* Visiting Faculty

---

### Academic Leadership

Examples:

* HOD
* Principal
* Dean
* Academic Director
* Vice Chancellor

---

### Administrative Staff

Examples:

* Clerk
* Accountant
* HR Officer
* Office Administrator

---

### Executive Leadership

Examples:

* Director
* Trustee
* Chairman
* Governing Board Member

---

## Responsibilities

Manage:

* Identity
* User Lifecycle
* Organizational Assignment
* Role Assignment
* Institution Assignment

---

# New Section 5.1 Dynamic Role Management

## Purpose

Support institution-specific roles without platform redesign.

---

## Requirements

Support:

* Custom Roles
* Multiple Roles Per User
* Institution-Specific Roles
* Department-Level Roles
* Temporary Roles
* Delegated Roles

---

## Examples

### School

* Principal
* Teacher
* Academic Coordinator

### College

* Dean
* Lecturer
* Department Head

### University

* Vice Chancellor
* Professor
* Faculty Head

### Training Institute

* Trainer
* Program Coordinator

---

## Design Principle

The platform must never hardcode role definitions.

Roles should be configurable.

---

# 6. Academic Structure Framework

## Purpose

Provide a flexible academic model capable of supporting multiple institution types.

---

## Responsibilities

Manage:

* Academic Years
* Terms
* Semesters
* Grades
* Classes
* Batches
* Sections
* Programs
* Courses
* Subjects

---

## Institution Examples

### School

```text
Grade
 → Class
 → Section
 → Subject
```

### College

```text
Program
 → Semester
 → Subject
```

### University

```text
Faculty
 → Program
 → Semester
 → Course
```

---

## Design Principle

Academic structures must be configurable and institution-aware.

The platform should avoid assumptions that every institution follows a school-style hierarchy.

---

# 7. Curriculum Framework

## Purpose

Provide a common curriculum model for future learning systems.

---

## Responsibilities

Manage:

* Curriculum
* Units
* Chapters
* Learning Objectives
* Learning Outcomes

---

## Future Consumers

* Lesson Planning
* Assessment
* Learning Outcomes
* Student Portfolio

---

# 8. Subscription Management

## Purpose

Control client access to platform offerings.

---

## Responsibilities

Manage:

* Subscribed Modules
* Add-ons
* Trial Features
* Module Activation
* Module Deactivation

---

## Examples

Client A:

* Attendance
* Homework
* Fees

Client B:

* Attendance
* Exams

---

# 9. Notification Framework

## Purpose

Provide centralized communication capabilities.

---

## Notification Types

### Email

### SMS

### Push Notification

### In-App Notification

---

## Future Channels

* WhatsApp
* Voice Notifications

---

## Consumers

All modules should use this framework.

---

# 10. Communication Framework

## Purpose

Enable structured communication across the platform.

---

## Examples

* School Announcements
* Parent Communication
* Teacher Communication
* Emergency Communication

---

## Design Principle

Communication should remain independent from individual modules.

---

# 11. Audit Framework

## Purpose

Track important actions across the platform.

---

## Responsibilities

Record:

* Who performed the action
* When action occurred
* What changed
* Where change occurred

---

## Consumers

All modules.

---

# 12. Document Management Framework

## Purpose

Manage files and documents across the platform.

---

## Examples

* Homework Attachments
* Student Documents
* Fee Receipts
* Report Cards
* Learning Resources

---

## Design Principle

Documents should not be managed separately by each module.

---

# 13. Analytics Framework

## Purpose

Provide reporting and analytics capabilities.

---

## Responsibilities

Support:

* Operational Reporting
* Management Reporting
* Platform Reporting

---

## Reporting Levels

### School

Single-school reporting.

### Multi-School

Cross-school reporting.

### Client

Aggregated client reporting.

### Platform

SaaS business reporting.

# 13.1 Master Data Management Framework

## Purpose

Provide a single source of truth for all educational entities.

---

## Managed Entities

People

* Students
* Staff
* Parents
* Guardians

Organization

* Clients
* Institutions
* Departments

Academics

* Programs
* Courses
* Subjects
* Classes

Resources

* Rooms
* Buildings
* Facilities

---

## Design Principle

Every platform capability and business module must consume master data from this framework.

Duplicate master data ownership is prohibited.

---

# New Platform Design Rule

The platform should be internally designed as an Educational Institution Management Platform.

School ERP becomes the first supported product configuration rather than the architectural foundation.

This ensures future support for:

* Schools
* Colleges
* Universities
* Coaching Institutes
* Training Organizations

without requiring platform redesign.
---

# 14. Search Framework

## Purpose

Provide unified search capabilities.

---

## Future Search Scope

Search:

* Students
* Teachers
* Classes
* Homework
* Assessments
* Documents

---

# 15. Configuration Framework

## Purpose

Manage configurable behavior across the platform.

---

## Examples

* Attendance Rules
* Academic Rules
* Notification Rules
* School Preferences

---

## Design Principle

Configuration should not require software changes.

---

# 16. Workflow Framework

## Purpose

Provide approval and review workflows.

---

## Future Examples

* Leave Approval
* Fee Approval
* Assessment Approval
* Lesson Plan Approval

---

# 17. Integration Framework

## Purpose

Enable integration with external systems.

---

## Future Integrations

* Payment Gateways
* SMS Providers
* Email Providers
* Video Conferencing Platforms
* Learning Platforms

---

# 18. Billing Framework

## Purpose

Manage SaaS billing operations.

---

## Responsibilities

Support:

* Subscription Billing
* Usage Billing
* Add-on Billing
* School Expansion Billing

---

## Design Principle

Billing ownership exists at Client level.

---

# 19. Analytics Data Pipeline

## Purpose

Separate operational workloads from reporting workloads.

---

## Principles

Operational modules:

* Attendance
* Fees
* Homework
* Exams

should not perform heavy analytical processing.

Analytics data should be generated through scheduled processing and stored separately.

---

# 20. Future AI Framework

## Purpose

Provide shared AI capabilities for future modules.

---

## Potential Capabilities

* Lesson Generation
* Question Generation
* Assessment Generation
* Student Risk Analysis
* Learning Gap Detection

---

## Design Principle

AI should become a shared platform capability rather than being embedded individually within modules.

---

# Shared Platform Capability Rule

Every new requirement must first be evaluated:

1. Does this belong to an existing platform capability?
2. Does an existing capability need enhancement?
3. Is a new platform capability required?

Only after answering these questions should a new business module be designed.

This ensures the platform remains consistent, reusable, and scalable as new ERP capabilities are added.
