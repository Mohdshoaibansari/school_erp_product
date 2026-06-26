## ADDED Requirements

### Requirement: Unified identity model
Feature: Identity & User Management
Rule: A person has exactly one identity regardless of how many institutions they belong to.

#### Scenario: Create a new user
- **GIVEN** a tenant
- **WHEN** a new user is created with email and profile data
- **THEN** the user record is created in the tenant scope
- **AND** the user has no institution assignments yet

#### Scenario: Assign user to institution with role
- **GIVEN** an existing user and an active institution
- **WHEN** the user is assigned to the institution with a role
- **THEN** the user appears in that institution's roster
- **AND** the user's permissions are derived from their role

#### Scenario: User can belong to multiple institutions
- **GIVEN** a user assigned to Institution A
- **WHEN** the same user is assigned to Institution B
- **THEN** the user has separate role and permissions per institution

### Requirement: User lifecycle
Feature: Identity & User Management
Rule: Users follow a lifecycle from invited to active to archived.

#### Scenario: New user starts as invited
- **GIVEN** a user is created by an administrator
- **WHEN** the user has not yet logged in
- **THEN** their status is "invited"
- **AND** they cannot access the system until they set a password

#### Scenario: User can be deactivated
- **GIVEN** an active user
- **WHEN** an administrator deactivates them
- **THEN** the user cannot log in
- **AND** their historical data is preserved
