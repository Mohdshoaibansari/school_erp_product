## Purpose

C-02 Identity & User Management provides the unified user identity foundation for the School ERP platform. It owns User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, and UserLifecycleEvent entities, the User lifecycle state machine, and the tenant isolation contract for user data. This spec is the behavioral source of truth derived from the grill-me session (11 locked decisions) and PRD `docs/prd/c-02-identity-user-management.md` (AC-1..AC-20).

## Requirements

### Requirement: Tenant Isolation Contract for C-02 Entities

The system SHALL enforce tenant isolation for all C-02 entities using the same two-level hybrid model as C-01: (1) tenant-aware repositories as the data-access contract — business logic MUST NOT write SQL directly and MUST NOT rely on RLS as the primary filter; and (2) Postgres Row-Level Security (RLS) as a defense-in-depth backstop that filters by `client_id` on every tenant-scoped table even if a repository method is bypassed.

Every tenant-scoped C-02 table (User, UserProfile, RoleAssignment, UserIdentifier, UserLifecycleEvent) MUST carry a `client_id` column with an RLS policy that matches the JWT/TenantContext `client_id`. The UserCategory and Role lookup tables are NOT tenant-scoped (they are global/shared).

A user at School A can never see or edit user data from School B (even if they share the same Client).

Trace: Decision 1, AC-1, AC-17, AC-20.

#### Scenario: Repository injects client_id on every tenant-scoped query
- **WHEN** business logic calls a tenant-aware repository method on any tenant-scoped C-02 table
- **THEN** the repository injects the `client_id` from the TenantContext into the query filter without the caller passing it explicitly, and the returned rows are scoped to that client

#### Scenario: RLS backstop blocks a bypassed repository
- **WHEN** a query reaches a tenant-scoped C-02 table without the correct `client_id` filter (e.g., a repository method that forgets to inject `client_id`, or direct SQL)
- **THEN** Postgres RLS on `client_id` filters the rows so that no row belonging to a different Client is visible or returned

#### Scenario: A user belonging to Client A can never see Client B user data
- **WHEN** any request is processed with a TenantContext resolved to Client A
- **THEN** no user row belonging to Client B is visible or editable through any C-02 API, repository method, or direct database access path

### Requirement: Entity Identifiers — UUID v4

All C-02 entities — User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, UserLifecycleEvent — SHALL use UUID v4 as primary key. The system MUST NOT use autoincrement sequences. The system MUST NOT use C-12 (Code & Identifier Engine) generated codes for C-02 primary keys.

Trace: Decision 4, AC-4.

#### Scenario: UUID v4 on every C-02 primary key
- **WHEN** a new row is created in any C-02 entity table
- **THEN** its primary key is a UUID v4 value that is globally unique without central coordination

#### Scenario: No autoincrement sequences on C-02 tables
- **WHEN** the database schema for any C-02 entity is inspected
- **THEN** no SERIAL/BIGSERIAL/IDENTITY autoincrement column is used as the primary key

### Requirement: User Entity — Per-Institution Identity

The system SHALL model each user as a per-institution record. A person who works at two schools has two separate User accounts with two separate email addresses. There is NO Person table. Each User record belongs to exactly one Client and one Institution.

User intrinsic fields: `id` (UUID v4), `client_id` (FK, RLS tenant column), `institution_id` (FK, default business filter), `email` (globally unique), `name`, `user_category_id` (FK to lookup table), `lifecycle_status`, and audit timestamps (`created_at`, `updated_at`).

Trace: Decision 1, Decision 4, AC-1, AC-4.

#### Scenario: User belongs to exactly one Client and one Institution
- **WHEN** a User is created
- **THEN** the User record has a `client_id` and `institution_id` that are set at creation and define the user's tenant scope

#### Scenario: A person at two schools has two separate User accounts
- **WHEN** a person needs access to School A and School B
- **THEN** two separate User records are created (one per institution), each with its own unique email, and they are independent accounts with no cross-linking

### Requirement: User Email Uniqueness

Each User SHALL have a globally unique email address across the entire platform. No two User records (even across different Clients or Institutions) can share the same email. Email collision at creation returns an error.

Trace: Decision 2, AC-2.

#### Scenario: Unique email accepted at creation
- **WHEN** a User is created with an email that does not exist on any other User record
- **THEN** the User is created successfully

#### Scenario: Duplicate email rejected
- **WHEN** a User is created with an email that already exists on another User record (even across different Clients or Institutions)
- **THEN** creation is rejected with a clear error indicating the email is already taken

### Requirement: UserProfile — Separate Extended Profile

UserProfile SHALL be a separate table linked 1:1 to User. Profile fields: `photo` (URL/path), `date_of_birth`, `gender`, `blood_group`. A User can exist without a UserProfile (optional).

Trace: Decision 5, AC-5.

#### Scenario: UserProfile created for a User
- **WHEN** a UserProfile is created for an existing User
- **THEN** the UserProfile is linked to the User via `user_id` FK and contains the extended profile fields

#### Scenario: User exists without a UserProfile
- **WHEN** a User is created but no UserProfile is created
- **THEN** the User record is valid and functional without a UserProfile

#### Scenario: UserProfile cannot exist without a User
- **WHEN** a UserProfile is created with a non-existent `user_id`
- **THEN** creation is rejected due to FK constraint violation

### Requirement: UserCategory Lookup Table

UserCategory SHALL be a configurable lookup table. Default categories: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. Adding a new category (e.g., "Visiting Faculty") is a data insert, not a code change.

UserCategory is NOT tenant-scoped (global/shared).

Trace: Decision 9, AC-12, AC-14, AC-19.

#### Scenario: User created with a valid UserCategory
- **WHEN** a User is created with a `user_category_id` that references a valid UserCategory
- **THEN** the User is created successfully

#### Scenario: User created with invalid UserCategory rejected
- **WHEN** a User is created with a `user_category_id` that does not reference a valid UserCategory
- **THEN** creation is rejected due to FK constraint violation

#### Scenario: Adding a new UserCategory requires no code change
- **WHEN** an administrator inserts a new row into the `user_category` table
- **THEN** the new category is immediately available for User creation without any code change or redeployment

### Requirement: Role Lookup Table

Role SHALL be a configurable lookup table. Default roles: Teacher, HOD, Principal, Student, Parent, Staff, Admin. Adding a new role (e.g., "Librarian") is a data insert, not a code change.

Role is NOT tenant-scoped (global/shared).

Trace: Decision 10, AC-13, AC-15, AC-19.

#### Scenario: RoleAssignment created with a valid Role
- **WHEN** a RoleAssignment is created with a `role_id` that references a valid Role
- **THEN** the RoleAssignment is created successfully

#### Scenario: RoleAssignment created with invalid Role rejected
- **WHEN** a RoleAssignment is created with a `role_id` that does not reference a valid Role
- **THEN** creation is rejected due to FK constraint violation

#### Scenario: Adding a new Role requires no code change
- **WHEN** an administrator inserts a new row into the `role` table
- **THEN** the new role is immediately available for RoleAssignment creation without any code change or redeployment

### Requirement: RoleAssignment — User + Role + Scope

RoleAssignment SHALL link a User to a Role with an optional `scope` field. A user can hold multiple RoleAssignments at the same institution (e.g., Teacher + HOD). The `scope` field defines what the role covers (e.g., "Mathematics Department"). RoleAssignment does NOT store `institution_id` — the institution comes from the User record.

Trace: Decision 6, AC-6, AC-7.

#### Scenario: User holds multiple roles at the same institution
- **WHEN** a User at School A has a RoleAssignment for Teacher and another RoleAssignment for HOD
- **THEN** both RoleAssignments are valid and the user holds both roles at School A

#### Scenario: RoleAssignment does not store institution_id
- **WHEN** the RoleAssignment schema is inspected
- **THEN** there is no `institution_id` column; the institution is inferred from the User record's `institution_id`

#### Scenario: RoleAssignment scope defines role coverage
- **WHEN** a RoleAssignment is created with `scope = "Mathematics Department"`
- **THEN** the scope is stored and can be queried to identify what the role covers

### Requirement: UserIdentifier — Institution-Scoped Business Identifiers

UserIdentifier SHALL store typed, institution-scoped business identifiers (Student ID, Employee ID, Admission Number). Each identifier has `user_id`, `type`, and `value`. Identifiers are unique per (institution, type, value) via the User record's `institution_id`. UserIdentifier does NOT store `institution_id`.

Trace: Decision 7, AC-8, AC-9.

#### Scenario: Identifier unique within an institution
- **WHEN** a UserIdentifier is created with type "student_id" and value "STU-001" for a User at School A
- **THEN** another UserIdentifier with the same type and value at School A is rejected

#### Scenario: Identifier can be reused across institutions
- **WHEN** a UserIdentifier with type "student_id" and value "STU-001" exists at School A
- **THEN** a UserIdentifier with the same type and value can be created for a User at School B

#### Scenario: UserIdentifier does not store institution_id
- **WHEN** the UserIdentifier schema is inspected
- **THEN** there is no `institution_id` column; the institution is inferred from the User record's `institution_id`

### Requirement: User Lifecycle State Machine

User lifecycle SHALL follow the state machine: `Invited → Pending → Active → Suspended → Archived`. Archived is terminal (no outgoing arcs). Allowed transitions: Invited→Pending, Pending→Active, Active→Suspended, Suspended→Active, Active→Archived, Suspended→Archived. Every transition records a lifecycle event (state, reason, actor) and is audited via C-11.

Trace: Decision 8, AC-10, AC-11.

#### Scenario: Valid lifecycle transition accepted
- **WHEN** a User with lifecycle_status "active" is transitioned to "suspended"
- **THEN** the transition succeeds, `lifecycle_status` is updated, and a lifecycle event is recorded

#### Scenario: Invalid lifecycle transition rejected
- **WHEN** a User with lifecycle_status "active" is transitioned to "invited"
- **THEN** the transition is rejected with a clear error

#### Scenario: Archived is terminal
- **WHEN** a User with lifecycle_status "archived" is transitioned to any other state
- **THEN** the transition is rejected; Archived is terminal with no outgoing arcs

#### Scenario: Lifecycle event recorded on every transition
- **WHEN** any valid lifecycle transition occurs
- **THEN** a row is inserted into `user_lifecycle_event` with `user_id`, `state` (the new state), `reason`, `actor`, and `entered_at`

#### Scenario: Lifecycle transition audited via C-11
- **WHEN** any valid lifecycle transition occurs
- **THEN** a synchronous audit event is emitted via the AuditEmitter Protocol with action "user_lifecycle_transition"

### Requirement: Module Manifest Registration

C-02 SHALL register via the ModuleManifest Protocol (A5). Routes are registered via `register_routes`. Casbin policies are registered via `register_casbin_policies` (no-op until C-04 is built).

Trace: AC-16.

#### Scenario: C-02 manifest registers routes
- **WHEN** the app factory invokes `register_routes` on the C-02 manifest
- **THEN** C-02's FastAPI routers are mounted (user CRUD, profile, role assignment, identifier endpoints)

#### Scenario: C-02 manifest registers Casbin policies (no-op)
- **WHEN** the app factory invokes `register_casbin_policies` on the C-02 manifest
- **THEN** the call succeeds (no-op until C-04 is built)

### Requirement: Audit Emission

C-02 SHALL emit synchronous audit events via the AuditEmitter Protocol for: user creation, lifecycle transitions, role assignment/removal, identifier creation/deletion.

Trace: AC-18.

#### Scenario: User creation audit event
- **WHEN** a User is created
- **THEN** a synchronous audit event is emitted with action "user_created", `client_id`, `institution_id`, `actor`, and payload containing user details

#### Scenario: Role assignment audit event
- **WHEN** a RoleAssignment is created
- **THEN** a synchronous audit event is emitted with action "role_assignment_created", `client_id`, `institution_id`, `actor`, and payload containing assignment details

#### Scenario: Identifier creation audit event
- **WHEN** a UserIdentifier is created
- **THEN** a synchronous audit event is emitted with action "user_identifier_created", `client_id`, `institution_id`, `actor`, and payload containing identifier details

### Requirement: Seed Data

UserCategory and Role lookup tables SHALL have seed data in the Alembic migration. Default categories: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. Default roles: Teacher, HOD, Principal, Student, Parent, Staff, Admin.

Trace: R6.

#### Scenario: UserCategory seed data present after migration
- **WHEN** `alembic upgrade head` completes
- **THEN** the `user_category` table contains the 5 default categories

#### Scenario: Role seed data present after migration
- **WHEN** `alembic upgrade head` completes
- **THEN** the `role` table contains the 7 default roles
