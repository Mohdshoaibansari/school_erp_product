## ADDED Requirements

### Requirement: Role-based access control
Feature: Authorization
Rule: Every action is authorized through this service. No module implements its own permission checks.

#### Scenario: User has permissions derived from role
- **GIVEN** a user assigned the Teacher role at an institution
- **WHEN** they attempt to mark attendance
- **THEN** the system checks their permissions
- **AND** grants access if the Teacher role includes attendance.mark

#### Scenario: Permission denied for unauthorized action
- **GIVEN** a user assigned the Parent role
- **WHEN** they attempt to create a homework assignment
- **THEN** the system denies access
- **AND** returns a 403 Forbidden

### Requirement: Scope-based authorization
Feature: Authorization
Rule: Permissions are scoped to institutions, grades, or classes.

#### Scenario: Teacher can only act within their assigned class
- **GIVEN** a Teacher assigned to Class 10A
- **WHEN** they attempt to mark attendance for Class 10B
- **THEN** the system denies access
- **AND** returns a 403 Forbidden

#### Scenario: Principal has institution-wide scope
- **GIVEN** a Principal role at an institution
- **WHEN** they access any class within that institution
- **THEN** the system grants access
