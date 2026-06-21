## ADDED Requirements

### Requirement: Append-only audit trail
Feature: Audit Logging
Rule: Every significant action is recorded in an immutable audit log.

#### Scenario: Log a user action
- **GIVEN** an authenticated user
- **WHEN** they perform an action (e.g., mark attendance)
- **THEN** an audit record is created with actor, action, target, timestamp, and tenant context
- **AND** the record cannot be modified or deleted

#### Scenario: Query audit logs
- **GIVEN** audit records exist for various actions
- **WHEN** an administrator queries with filters (actor, action, date range, tenant)
- **THEN** matching audit records are returned sorted by timestamp

### Requirement: Audit levels
Feature: Audit Logging
Rule: Audit records have configurable retention periods by severity level.

#### Scenario: Critical audit events
- **GIVEN** a critical audit event (login failure, role change, fee refund)
- **WHEN** the audit record is created
- **THEN** its retention period is set to 7 years

#### Scenario: Routine audit events
- **GIVEN** a routine audit event (profile view, report download)
- **WHEN** the audit record is created
- **THEN** its retention period is set to 90 days
