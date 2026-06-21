## ADDED Requirements

### Requirement: Typed configuration with scope inheritance
Feature: Config & Rules Engine
Rule: Configuration values are typed and inherited from platform ? client ? institution scope.

#### Scenario: Config at platform level
- **GIVEN** a platform-wide config key with a default value
- **WHEN** an institution queries that key
- **THEN** the platform default is returned if no institution override exists

#### Scenario: Config override at institution level
- **GIVEN** a platform config key with default value
- **AND** an institution overrides that key
- **WHEN** the institution queries the key
- **THEN** the override value is returned

#### Scenario: Config scopes
- **GIVEN** a config key
- **WHEN** set at platform scope
- **THEN** it applies to all tenants
- **WHEN** overridden at institution scope
- **THEN** only that institution sees the override

### Requirement: Rules engine
Feature: Config & Rules Engine
Rule: Modules evaluate configurable rules for decisions like attendance cutoff, leave calculation, and fee calculation.

#### Scenario: Attendance cutoff rule
- **GIVEN** a config rule attendance.cutoff_time set to 09:30
- **WHEN** a student arrives at 09:45
- **THEN** the attendance module evaluates the rule
- **AND** marks the student as late

#### Scenario: Late fee calculation rule
- **GIVEN** a config rule fees.late_fee_percent set to 2
- **WHEN** a fee payment is 15 days overdue
- **THEN** the fees module evaluates the rule
- **AND** applies the late fee percentage
