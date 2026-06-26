## ADDED Requirements

### Requirement: Typed configuration with scope inheritance
Feature: Config & Rules Engine
Rule: Configuration values inherit from platform → client → institution scope.

#### Scenario: Config at platform level
- **GIVEN** a platform-level config value exists
- **WHEN** no institution-level override exists
- **THEN** the platform default is returned

#### Scenario: Config override at institution level
- **GIVEN** an institution-level config override
- **WHEN** the config value is requested
- **THEN** the institution override is returned instead of the platform default

#### Scenario: Config scopes
- **GIVEN** platform and institution config scopes
- **WHEN** querying config
- **THEN** platform applies to all tenants, institution override is scoped to that institution

### Requirement: Rules engine
Feature: Config & Rules Engine
Rule: Modules evaluate configurable rules for decision logic.

#### Scenario: Attendance cutoff rule
- **GIVEN** an attendance cutoff time configured at institution level
- **WHEN** a student arrives after the cutoff
- **THEN** the student is marked as late

#### Scenario: Late fee calculation rule
- **GIVEN** a late fee percentage configured at institution level
- **WHEN** a payment is overdue
- **THEN** the late fee percentage is applied to the overdue amount
