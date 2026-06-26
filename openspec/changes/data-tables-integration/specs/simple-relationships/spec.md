## ADDED Requirements

### Requirement: Student-guardian mapping
Feature: Simple Relationships
Rule: Every student can have multiple guardians with defined relationship types and contact roles.

#### Scenario: Add parent to student
- **GIVEN** a student
- **WHEN** a guardian is added with type "Mother" and role "PrimaryGuardian"
- **THEN** the guardian is linked to the student

#### Scenario: Multiple guardians with different roles
- **GIVEN** a student with one guardian
- **WHEN** a second guardian is added with role "EmergencyContact"
- **THEN** both guardians are linked with distinct roles

#### Scenario: Query parents of a student
- **GIVEN** a student with two guardians
- **WHEN** querying guardians
- **THEN** both guardians are returned with their types and roles
