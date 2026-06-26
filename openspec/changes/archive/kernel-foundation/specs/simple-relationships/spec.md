## ADDED Requirements

### Requirement: Student-guardian mapping
Feature: Simple Relationships
Rule: Every student can have multiple guardians with defined relationship types and contact roles.

#### Scenario: Add parent to student
- **GIVEN** an enrolled student
- **WHEN** a parent is linked as guardian with type Mother and role PrimaryGuardian
- **THEN** the relationship is recorded
- **AND** the parent appears in the student's guardian list

#### Scenario: Multiple guardians with different roles
- **GIVEN** a student with one guardian
- **WHEN** a second guardian is added with role EmergencyContact
- **THEN** both guardians are associated with the student
- **AND** each has their own contact role

#### Scenario: Query parents of a student
- **GIVEN** a student with two guardians
- **WHEN** any module queries the student's parents
- **THEN** both guardians are returned with their types and roles
