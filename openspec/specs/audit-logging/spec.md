## ADDED Requirements

### Requirement: Append-only audit trail
Feature: Audit Logging
Rule: Every significant action creates an immutable audit record with actor, action, target, timestamp, and tenant context.

#### Scenario: Log a user action
- **GIVEN** a user performs an action
- **WHEN** the action is logged
- **THEN** an audit record is created with actor, action, target, timestamp, tenant context
- **AND** the record is immutable

#### Scenario: Query audit logs
- **GIVEN** audit logs exist
- **WHEN** querying with filters
- **THEN** filtered results are returned sorted by timestamp

### Requirement: Audit levels
Feature: Audit Logging
Rule: Different audit events have different retention periods.

#### Scenario: Critical audit events
- **GIVEN** a critical event (login failure, role change, fee refund)
- **WHEN** logged
- **THEN** retention period is set to 7 years

#### Scenario: Routine audit events
- **GIVEN** a routine event (profile view, report download)
- **WHEN** logged
- **THEN** retention period is set to 90 days
