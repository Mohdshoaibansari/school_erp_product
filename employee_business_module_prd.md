# PRD — Employee Business Module

**Product:** Multi-Tenant School ERP  
**Module:** Employee  
**Architecture:** Modular Monolith  
**Backend:** Python + FastAPI  
**Database:** PostgreSQL / Supabase  
**ORM:** SQLAlchemy 2.x  
**Migrations:** Alembic  
**Authorization:** AuthZ Kernel + Casbin  
**Database Security:** PostgreSQL RLS  
**Status:** Proposed

## 1. Purpose

The Employee module manages people who have an employment relationship with an institution.

Employee is the foundation for future capabilities:

```text
Employee
├── Teacher
├── Leave
├── Payroll
├── HR
├── Performance
└── Benefits
```

This module establishes a stable employment identity and lifecycle without absorbing Teacher, Payroll, Leave, HR, or other downstream responsibilities.

## 2. Critical Identity and Authorization Distinction

**Employee is NOT an authenticated actor.**

A **User** authenticates and makes requests.

Correct flow:

```text
User
 │
 ├── Login
 ▼
Authentication
 │
 ▼
TenantContext / Request Context
 │
 ├── user_id
 ├── client_id
 ├── institution_id
 └── roles
 │
 ▼
AuthZ
 │
 │ "Can this User perform this action?"
 ▼
Business Module
 │
 ▼
Employee Resource
```

Therefore:

> AuthZ evaluates requests made by authenticated Users. Employee is a business resource, not an authenticated actor.

## 3. User → Employee Relationship

An authenticated User may be associated with an Employee:

```text
User U001
   │
   │ optional association
   ▼
Employee E001
   │
   ▼
Teacher T001
```

This relationship may later be used to derive authorization attributes.

Example:

```text
User U001
   ↓
Employee E001
   ↓
Teacher T001
   ↓
Teaching Assignment
   ↓
Section 1A
```

A later Homework request can determine:

```text
User U001 is the teacher assigned to Section 1A
```

and provide a trusted attribute such as:

```text
is_teacher_for_resource = true
```

The AuthZ Kernel evaluates the attribute; the Employee/Teacher domain remains the source of truth.

## 4. User and Employee Are Separate Concepts

```text
User
    = Authentication / portal identity

Person
    = Human identity

Employee
    = Employment relationship

Teacher
    = Academic responsibility of an Employee
```

Conceptually:

```text
Person
   │
   ├──────────────┐
   │              │
   ▼              ▼
Employee        Student
   │
   ▼
Teacher
```

Portal access remains separate:

```text
Person / Employee / Student
          │
          ▼
         User
          │
          ▼
        AuthZ
```

Not every Employee needs a User account.

## 5. Goals

The module must:

1. Represent employees independently from login accounts.
2. Maintain employment information.
3. Support employment types.
4. Support employee lifecycle states.
5. Associate employees with an institution.
6. Provide a stable Employee business identity.
7. Allow optional portal access through the existing Identity/User capability.
8. Provide the foundation for Teacher.
9. Provide the foundation for Payroll.
10. Provide the foundation for Leave.
11. Provide the foundation for HR.
12. Respect Client → Institution tenancy.
13. Integrate with the existing AuthZ Kernel.
14. Enforce PostgreSQL RLS.
15. Maintain domain/application/persistence/API separation.
16. Avoid implementing downstream capabilities prematurely.

## 6. Non-Goals

Do NOT implement:

- Teacher-specific academic assignments
- Class teacher assignments
- Subject assignments
- Student relationships
- Attendance
- Leave management
- Payroll
- Salary calculation
- Tax calculation
- Performance management
- Recruitment
- Benefits
- HR workflows
- Messaging
- Kafka
- Event bus
- Microservices
- External HR systems
- Authentication
- Password management
- JWT/session management
- Authorization policy evaluation

Authentication remains an Identity/Auth capability. Authorization remains the responsibility of the AuthZ Kernel.

## 7. Employee Domain

Employee represents:

> A person who has an employment relationship with an institution.

Conceptually:

```text
Employee
├── employee_id
├── person_id
├── institution_id
├── employee_number
├── employment_type
├── employment_status
├── joining_date
├── department
└── designation
```

Before implementation, inspect the existing codebase and reuse existing models where appropriate.

Do not create duplicate identity/person structures.

## 8. Person vs Employee

Do not automatically create a new Person entity.

First inspect the existing codebase.

If an appropriate Person/human identity model already exists, Employee should reference it.

Conceptually:

```text
Person
------
person_id
name
contact/basic personal information
address
...

Employee
--------
employee_id
person_id
institution_id
employee_number
joining_date
employment_type
employment_status
department
designation
```

Person owns human identity.

Employee owns employment information.

## 9. Employee Identity

Employee must have its own stable business identity:

```text
employee_id
```

It is not the same conceptual identity as:

```text
user_id
```

An Employee without portal access is valid.

## 10. Employee Number

Employee Number is a human/business identifier, for example:

```text
EMP-00001
EMP-00002
```

Do not introduce a new generic Identifier Generation Kernel capability.

If a human-readable employee number is required, follow existing project conventions.

The database must enforce uniqueness within the appropriate institution scope.

## 11. Employment Type

Support common types as required:

```text
FULL_TIME
PART_TIME
CONTRACT
TEMPORARY
INTERN
CONSULTANT
```

The exact values must follow product requirements and existing conventions.

Avoid an unnecessarily complex HR taxonomy.

## 12. Employment Status

Employment status is separate from User account status.

Possible values:

```text
ACTIVE
ON_NOTICE
SUSPENDED
INACTIVE
TERMINATED
RETIRED
```

The exact values should follow existing terminology.

Valid example:

```text
Employee = ACTIVE
User = DISABLED
```

This means the person remains employed but has no current portal access.

## 13. Department and Designation

Employee may contain:

```text
department
designation
```

Examples:

```text
Department:
    Administration
    Mathematics
    Accounts
    Library

Designation:
    Teacher
    Accountant
    Librarian
    Receptionist
```

However:

> `designation = Teacher` must NOT itself create a Teacher business entity.

Teacher is a separate business module.

## 14. Employee → Teacher

Teacher should eventually be a separate business capability associated with Employee:

```text
Employee E001
      │
      ▼
Teacher T001
```

Teacher owns:

```text
teaching assignments
section assignments
subject assignments
academic responsibilities
```

Employee owns:

```text
employment relationship
```

Do not put teaching assignments into Employee.

## 15. Employee → User

Portal access is optional:

```text
Employee
    │
    └── 0..1 User
```

Employee must not own authentication.

Do not duplicate:

```text
password
JWT
session management
login workflow
```

The existing Identity/User capability owns those concerns.

## 16. Authentication vs Authorization

Authentication answers:

> Who is making this request?

```text
User U001
```

Authorization answers:

> Is User U001 allowed to perform this operation?

```text
User U001
    ↓
AuthZ
    ↓
employee.update
    ↓
ALLOW / DENY
```

Employee itself never "goes through AuthZ."

Instead:

```text
Authenticated User
        ↓
AuthZ
        ↓
Employee Resource
```

## 17. Employee as an Authorization Resource

Employee records are protected business resources.

Example:

```text
Subject:
    user_id = U001
    roles = [HR_ADMIN]

Action:
    employee.update

Resource:
    employee_id = E002
    institution_id = I001
```

AuthZ evaluates whether the authenticated User can perform the operation.

The Employee module does not implement authorization independently.

## 18. AuthZ Integration

Employee operations use the centralized AuthZ Kernel:

```text
Employee API
     ↓
Authorization Service
     ↓
Casbin
     ↓
ALLOW / DENY
     ↓
Employee Application Service
```

Do not implement hardcoded role checks such as:

```python
if user.role == "admin":
    ...
```

Use existing AuthZ dependency/service conventions.

## 19. Domain Authorization

Initial Employee authorization should primarily use:

```text
Role
+
Permission
+
Client scope
+
Institution scope
```

Do not create unnecessary ABAC attributes.

Complex attributes such as:

```text
is_subject_teacher
is_class_teacher
```

belong to future Teacher/Academic domain logic.

## 20. Multi-Tenancy

Employee is institution-scoped:

```text
Client
   │
   └── Institution
          │
          └── Employee
```

Every Employee must belong to an institution.

Respect:

```text
client_id
institution_id
```

Employees from Institution A must never be accessible through Institution B.

## 21. Platform Owner Boundary

Platform Owner is a platform-level administrative identity.

Platform Owner must NOT automatically gain access to operational Employee data.

Conceptually:

```text
Platform Owner
      ↓
Employee records
      ↓
DENY
```

unless an explicitly configured platform-level capability legitimately requires access.

The Employee module must use normal AuthZ.

It must not introduce a Platform Owner bypass.

## 22. RLS

Employee persistence must be protected by PostgreSQL RLS:

```text
Authenticated User
        ↓
TenantContext
        ↓
AuthZ
        ↓
Employee Repository
        ↓
PostgreSQL
        ↓
RLS
```

Application authorization does not replace RLS.

Do not create an RLS bypass for Platform Owner.

## 23. Employee Lifecycle

Initial lifecycle:

```text
Create
  ↓
Active
  ↓
On Notice / Suspended
  ↓
Inactive / Terminated / Retired
```

Do not implement complex HR workflows yet.

Domain rules should prevent invalid transitions.

## 24. Employee Creation

Conceptually:

```text
Create Employee
       ↓
Validate context
       ↓
Validate Person
       ↓
Validate employment data
       ↓
Create Employee
       ↓
Return DTO
```

Creating Employee must NOT automatically create a User account unless explicitly required by existing product requirements.

## 25. Employee Update

Separate:

### Person information

```text
name
contact
address
```

from:

### Employment information

```text
department
designation
employment_type
joining_date
status
```

If Person is a separate capability, use its application contract rather than directly manipulating another module's ORM model.

## 26. Employee Deletion

Prefer deactivation/termination over physical deletion:

```text
Employee
    status = TERMINATED
```

rather than:

```text
DELETE Employee
```

because future modules will reference Employee:

```text
Teacher
Payroll
Leave
Performance
HR
```

Physical deletion should be highly restricted.

## 27. API Layer

FastAPI controllers must remain thin:

```text
API
 ↓
Application Service
 ↓
Domain
 ↓
Repository
 ↓
Database
```

API responsibilities:

- request validation
- dependency injection
- authorization invocation
- application-service invocation
- response DTO

Do not put domain rules inside endpoints.

## 28. Application Layer

Application services/use cases should orchestrate:

```text
CreateEmployee
GetEmployee
ListEmployees
UpdateEmployee
ActivateEmployee
DeactivateEmployee
TerminateEmployee
```

The application layer coordinates:

```text
authorization/context
domain logic
repositories
transactions
DTO mapping
```

## 29. Domain Layer

Domain layer contains:

- Employee entity
- employment status
- employment type concepts
- lifecycle rules
- domain invariants
- domain validation

It must NOT directly depend on:

```text
FastAPI
SQLAlchemy Session
Casbin
HTTPException
Pydantic request models
```

## 30. Persistence Layer

Follow the existing module architecture.

If the project convention is:

```text
employee/
├── domain/
├── application/
├── infrastructure/
└── dependencies/
```

follow it consistently.

Use SQLAlchemy 2.x.

Do not create a different architectural style for Employee.

## 31. Repository

Repository responsibilities:

- persistence
- queries
- transaction participation
- mapping persistence data

Repositories must respect:

```text
client_id
institution_id
```

and the existing RLS architecture.

Do not create a new generic repository framework just for Employee.

## 32. DTOs

Do not return ORM entities directly from FastAPI.

Use Pydantic DTOs:

```text
EmployeeCreateRequest
EmployeeUpdateRequest
EmployeeResponse
EmployeeListResponse
```

Expose only appropriate API fields.

## 33. Employee List

Initial listing should support:

```text
status
employment_type
department
designation
search
pagination
```

Do not implement advanced HR analytics.

## 34. Employee Search

Search should support appropriate fields such as:

```text
employee_number
first_name
last_name
```

Use appropriate PostgreSQL indexes and avoid uncontrolled expensive queries.

## 35. Audit

Integrate with the existing audit mechanism for:

```text
employee.created
employee.updated
employee.activated
employee.deactivated
employee.terminated
```

Do not create a separate audit subsystem.

## 36. Transactions

Use existing application transaction/unit-of-work conventions.

Conceptually:

```text
Create Employee
      ↓
transaction
      ├── validate
      ├── persist
      └── commit
```

Do not independently commit inside repositories if the existing architecture expects application-level transaction ownership.

## 37. Database Constraints

Fundamental invariants should be enforced at database level.

Examples:

```text
employee_id → PRIMARY KEY
institution_id → NOT NULL
person_id → NOT NULL
employee_number → unique within institution
employment_status → valid value
```

Follow existing schema conventions.

## 38. Indexing

Consider indexes based on actual query patterns:

```text
institution_id
employee_number
person_id
employment_status
employment_type
department
```

Do not blindly index every field.

## 39. Module Dependencies

Employee should have minimal dependencies:

```text
Employee
   ↓
Kernel
   ├── Tenant Context
   ├── AuthZ contracts
   └── shared infrastructure/contracts
```

Employee must NOT depend on:

```text
Teacher
Payroll
Leave
Attendance
Homework
Student
```

at this stage.

## 40. Dependency Direction

Preferred:

```text
Kernel
   ↑
Employee
   ↑
Teacher / Leave / Payroll / HR
```

Conceptually:

```text
Employee
   ↓
Kernel contracts

Teacher
   ↓
Employee contract

Payroll
   ↓
Employee contract

Leave
   ↓
Employee contract
```

Avoid circular dependencies.

## 41. Testing

### Domain tests

Test:

```text
valid employee creation
invalid status transition
valid activation
valid deactivation
termination rules
```

### Application tests

Test:

```text
create employee
update employee
get employee
list employees
activate employee
deactivate employee
terminate employee
```

### Authorization tests

Test:

```text
authorized institution user → ALLOW
unauthorized role → DENY
wrong institution → DENY
wrong client → DENY
Platform Owner → DENY for operational Employee data
```

### RLS tests

Verify:

```text
Client A cannot access Client B employees
Institution A cannot access Institution B employees
```

## 42. User Account Tests

Verify:

```text
Employee without User
    → valid

Employee with User
    → valid

Employee active + User disabled
    → valid
```

Employee status and User account status remain independent.

## 43. Future Teacher Integration

Teacher will reference Employee:

```text
Teacher
    employee_id → Employee
```

Teacher then adds:

```text
teaching assignments
section assignments
subject assignments
academic responsibilities
```

Employee remains responsible only for employment identity.

## 44. Future Payroll Integration

Payroll references Employee:

```text
Payroll
    employee_id
```

Employee provides:

```text
employment identity
employment status
employment type
```

Payroll owns:

```text
salary
pay cycle
earnings
deductions
tax
payslip
```

Do not add salary fields to Employee.

## 45. Future Leave Integration

Leave references Employee:

```text
LeaveRequest
    employee_id
```

Leave owns:

```text
leave types
leave balances
leave requests
approval workflow
```

Do not put leave balances or workflows into Employee.

## 46. Future HR Integration

HR may reference Employee for:

```text
performance
documents
career history
training
disciplinary records
```

Those remain separate domain concepts.

Employee is the stable employment identity.

## 47. Initial Data Model

Minimum conceptual model:

```text
Person
------
person_id
basic personal information
...

Employee
--------
employee_id
person_id
institution_id
employee_number
joining_date
employment_type
employment_status
department
designation
created_at
updated_at
```

Reconcile against the existing codebase before implementation.

Do not create duplicate Person/User structures.

## 48. Initial API Surface

Keep the API intentionally small:

```text
POST   /employees
GET    /employees
GET    /employees/{employee_id}
PATCH  /employees/{employee_id}

POST   /employees/{employee_id}/activate
POST   /employees/{employee_id}/deactivate
POST   /employees/{employee_id}/terminate
```

Follow existing API naming/versioning conventions.

## 49. Authorization Matrix

Exact role assignments must come from existing AuthZ configuration.

Conceptually:

| Operation | Capability | Scope |
|---|---|---|
| Create Employee | `employee.create` | Institution |
| Read Employee | `employee.read` | Institution |
| Update Employee | `employee.update` | Institution |
| Deactivate Employee | `employee.deactivate` | Institution |
| Terminate Employee | `employee.terminate` | Institution |

Do not hardcode role checks.

## 50. Security Requirements

The module MUST:

- validate tenant context;
- validate institution context;
- use centralized AuthZ;
- treat the authenticated User as the authorization subject;
- treat Employee as the protected business resource;
- use PostgreSQL RLS as defense in depth;
- prevent cross-client access;
- prevent cross-institution access;
- prevent unauthorized lifecycle changes;
- avoid exposing unnecessary personal information;
- never trust client-supplied authorization attributes;
- never introduce a Platform Owner bypass.

## 51. Implementation Sequence

### Phase 1 — Existing Architecture Review

Before coding:

1. Inspect current User/Identity model.
2. Inspect existing Person-related models.
3. Inspect Client/Institution relationships.
4. Inspect existing business module structure.
5. Inspect AuthZ dependencies and contracts.
6. Inspect RLS migrations.
7. Inspect audit infrastructure.
8. Inspect DTO conventions.
9. Inspect repository patterns.
10. Inspect transaction/unit-of-work conventions.
11. Identify reusable Kernel contracts.

Do not assume a new Person entity is required.

### Phase 2 — Domain Model

Implement only Employee domain concepts:

```text
Person reference
Employee
EmploymentStatus
EmploymentType
```

where appropriate.

### Phase 3 — Persistence

Implement:

```text
SQLAlchemy model
Alembic migration
constraints
indexes
RLS
repository
```

### Phase 4 — Application Services

Implement:

```text
CreateEmployee
GetEmployee
ListEmployees
UpdateEmployee
ActivateEmployee
DeactivateEmployee
TerminateEmployee
```

### Phase 5 — Authorization Integration

Integrate with the existing AuthZ Kernel:

```text
Authenticated User
       ↓
Authorization Request
       ↓
employee.create/read/update/...
       ↓
Casbin
       ↓
ALLOW / DENY
```

Do not make Employee itself an AuthZ subject.

### Phase 6 — API

Add the minimum Employee endpoints.

Keep controllers thin.

### Phase 7 — Testing

Run:

```text
Employee domain tests
Employee application tests
Employee API tests
AuthZ regression tests
RLS tests
Full backend regression suite
```

## 52. Definition of Done

- [ ] Employee is a first-class business module.
- [ ] Employee is independent from User authentication.
- [ ] Employee can exist without a User.
- [ ] Employee has a stable business identity.
- [ ] Employee belongs to an institution.
- [ ] Client/institution isolation is enforced.
- [ ] Employee lifecycle is implemented.
- [ ] Employment type/status are modeled correctly.
- [ ] Employee does not contain Teacher-specific academic relationships.
- [ ] Employee does not contain Payroll logic.
- [ ] Employee does not contain Leave logic.
- [ ] Employee does not contain HR workflow logic.
- [ ] Authenticated Users are the subjects evaluated by AuthZ.
- [ ] Employee is treated as an authorization resource.
- [ ] No hardcoded role checks exist in Employee.
- [ ] Platform Owner cannot automatically access operational Employee data.
- [ ] PostgreSQL RLS protects Employee data.
- [ ] SQLAlchemy 2.x conventions are followed.
- [ ] API DTOs are separate from ORM models.
- [ ] Business logic is outside FastAPI controllers.
- [ ] Existing module architecture is followed.
- [ ] No unnecessary generic abstractions are introduced.
- [ ] No Kafka/event bus is introduced.
- [ ] Existing tests continue to pass.

## 53. Final Architecture

```text
                         Identity
                            │
                            ▼
                           User
                            │
                     authenticates
                            │
                            ▼
                          AuthZ
                            │
                     authorization
                            │
                            ▼
Person ───────────────── Employee
                              │
                ┌─────────────┼──────────────┐
                │             │              │
                ▼             ▼              ▼
             Teacher        Payroll         Leave
                │
                ▼
             Academic
                │
        ┌───────┴────────┐
        ▼                ▼
   Attendance         Homework
```

Responsibilities:

```text
User
    = Who can authenticate?

Person
    = Who is the human?

Employee
    = Who is employed by the institution?

Teacher
    = What academic responsibilities does the employee have?

AuthZ
    = What is the authenticated User allowed to do?

Payroll
    = How is the employee compensated?

Leave
    = What leave can the employee take?
```

The critical authorization distinction is:

```text
Authenticated User
        ↓
      AuthZ
        ↓
Employee Resource
```

NOT:

```text
Employee
    ↓
AuthZ
```

Employee is a business resource whose data and relationships may be used when evaluating authorization, but Employee itself never authenticates and never independently passes through AuthZ.

## 54. Final Architectural Principle

> **Authentication establishes the User. AuthZ authorizes the User's request. Employee represents the employment relationship and becomes a protected business resource. Future modules such as Teacher, Payroll, Leave, and HR build on Employee without moving their domain responsibilities into Employee.**

The Employee module is therefore the employment foundation while Identity, AuthZ, Teacher, Payroll, Leave, and HR remain separate responsibilities.


# 14A. Employee → Teacher Operational Flow

This section defines how Employee is used by the Teacher business module.

## 14A.1 Core Relationship

Employee represents the employment relationship.

Teacher represents the academic responsibilities of an employee.

```text
Person
  │
  │ personal information
  ▼
Employee
  │
  │ employment information
  ▼
Teacher
  │
  │ academic responsibilities
  ▼
Teaching Assignments
```

Example:

```text
Person
  id = P001
  name = Ahmed Khan

Employee
  id = E001
  person_id = P001
  institution_id = I001
  employee_number = EMP-001
  joining_date = 2026-06-01
  employment_type = FULL_TIME
  status = ACTIVE

Teacher
  id = T001
  employee_id = E001
```

Employee answers:

> Who is employed by the institution?

Teacher answers:

> What academic responsibilities does this employee have?

## 14A.2 Teacher Assignments

Teacher-specific academic relationships must NOT be stored directly on Employee.

A Teacher can have multiple assignments.

Example:

```text
Employee E001
      │
      ▼
Teacher T001
      │
      ├── Class Teacher → Section 1A
      │
      ├── Mathematics → Section 1A
      ├── Mathematics → Section 2A
      └── Physics → Section 3B
```

The assignment relationship belongs to the Teacher/Academic domain.

This allows one teacher to:

- teach multiple sections;
- teach multiple subjects;
- be class teacher for a section;
- have different responsibilities for different sections.

Do not add fields such as `class_id`, `subject_id`, or `section_id` directly to Employee merely to support teaching.

## 14A.3 User → Employee → Teacher

Portal access remains separate from employment and teaching.

```text
Person
   │
   ├── Employee
   │      │
   │      └── Teacher
   │
   └── User
```

Conceptually:

```text
User U001
   │
   └── Employee E001
             │
             └── Teacher T001
```

The User authenticates.

Employee and Teacher provide business context.

Employee and Teacher do not authenticate independently.

## 14A.4 Teacher Homework Authorization Example

Suppose Ahmed logs into the ERP.

```text
User U001
   ↓
Authentication
   ↓
Request Context
   ↓
AuthZ
```

Ahmed requests:

```text
POST /homework

section_id = 1A
subject_id = Mathematics
```

The authorization context can be resolved through the business relationships:

```text
User U001
   ↓
Employee E001
   ↓
Teacher T001
   ↓
Teaching Assignment
   ↓
Section 1A + Mathematics
```

The Teacher/Academic domain can establish:

```text
is_subject_teacher = true
```

The AuthZ Kernel then evaluates:

```text
homework.create
+
institution scope
+
is_subject_teacher
```

and returns:

```text
ALLOW
```

Important:

- AuthZ does not own the teacher assignment.
- Casbin does not store the teacher assignment.
- The Teacher/Academic domain is the source of truth.
- AuthZ consumes the trusted business fact.

## 14A.5 Unauthorized Teacher Example

Suppose Ahmed has these assignments:

```text
1A → Mathematics
2A → Mathematics
3B → Physics
```

Ahmed attempts:

```text
Section = 3B
Subject = Mathematics
```

The Teacher/Academic domain determines:

```text
Teacher T001
is NOT assigned to
3B + Mathematics
```

Therefore:

```text
is_subject_teacher = false
```

Casbin evaluates:

```text
homework.create     ✓
institution scope   ✓
is_subject_teacher  ✗
```

Result:

```text
DENY
```

This demonstrates why Teacher must own teaching relationships rather than Employee.

## 14A.6 Responsibility Boundaries

Employee owns:

```text
employee identity
institution
employee number
joining date
employment type
employment status
department
designation
```

Teacher owns:

```text
teaching profile
subject assignments
section assignments
class-teacher assignments
academic responsibilities
```

User owns:

```text
authentication identity
login credentials/session
portal access identity
```

AuthZ owns:

```text
permission evaluation
scope evaluation
policy evaluation
ABAC evaluation
authorization decision
```

The overall relationship is:

```text
                         User
                          │
                     authenticates
                          │
                          ▼
                         AuthZ
                          │
                    authorizes request
                          │
                          ▼
Person ─────────────── Employee
                          │
                          │ employment role
                          ▼
                       Teacher
                          │
                          │ academic assignments
                          ▼
                Teaching Assignment
                   /            \
                  /              \
             Section           Subject
```

## 14A.7 Downstream Module Consumption

Future academic modules consume Teacher relationships:

```text
Teacher
   │
   ├── Attendance
   ├── Homework
   ├── Exams
   └── Academic
```

Future employment modules consume Employee relationships:

```text
Employee
   │
   ├── Payroll
   ├── Leave
   ├── HR
   ├── Performance
   └── Benefits
```

This keeps Employee as the employment foundation and Teacher as the academic specialization.
