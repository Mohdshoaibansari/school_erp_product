## ADDED Requirements

### Requirement: Subscription tier tracking
Feature: Subscription Management
Rule: Every tenant has a subscription tier that determines module access and student cap.

#### Scenario: Free tier has student cap
- **GIVEN** a tenant on the free tier
- **WHEN** subscription status is checked
- **THEN** the tier is "free"
- **AND** the student cap is 100
- **AND** only free modules are accessible

#### Scenario: Paid tier has no cap
- **GIVEN** a tenant on the paid tier
- **WHEN** subscription status is checked
- **THEN** the tier is "paid"
- **AND** there is no student cap
- **AND** all modules are accessible

### Requirement: Module entitlement
Feature: Subscription Management
Rule: Module availability is determined by subscription tier.

#### Scenario: Paid tier sees all modules
- **GIVEN** a paid tenant
- **WHEN** the module availability API is called
- **THEN** all modules are returned as available

#### Scenario: Free tier sees limited modules
- **GIVEN** a free tenant
- **WHEN** the module availability API is called
- **THEN** only Students, Attendance, and Fees are returned
