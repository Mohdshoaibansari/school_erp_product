## ADDED Requirements

### Requirement: Student lifecycle states
Feature: Student Enrollment
Rule: Every student has a lifecycle state that determines billing eligibility

#### Scenario: New student enrollment starts as active
- **GIVEN** a school with an active academic year
- **WHEN** a new student is enrolled
- **THEN** the student's status is set to "active"
- **AND** the student counts toward the billing seat total

#### Scenario: Student graduation transitions to alumni
- **GIVEN** an active student enrolled in the current academic year
- **WHEN** the student completes their final grade
- **AND** the academic year ends
- **THEN** the student status changes to "graduated"
- **AND** the student no longer counts toward the billing seat total

#### Scenario: Student transfer keeps data but changes enrollment
- **GIVEN** an active student at School A
- **WHEN** the student transfers to School B
- **THEN** the student's enrollment at School A is marked "transferred"
- **AND** the student no longer counts toward School A's billing
- **AND** historical attendance and fee records are preserved

#### Scenario: Student archive preserves data
- **GIVEN** an active student who has not been enrolled for 2 consecutive academic years
- **WHEN** the system runs the archival process
- **THEN** the student status changes to "archived"
- **AND** all historical data is retained
- **AND** the student does not count toward billing

### Requirement: Alumni are separate from active students
Feature: Student Enrollment
Rule: Alumni and archived students are managed separately and never counted in billing

#### Scenario: Alumni section is distinct from students
- **GIVEN** a school with active students and alumni
- **WHEN** an administrator views the student directory
- **THEN** alumni are listed in a separate "Alumni" section
- **AND** alumni cannot be modified through student management screens
- **AND** alumni records are read-only

#### Scenario: Reactivating an alumni creates a new enrollment
- **GIVEN** an alumni record for a former student
- **WHEN** the student re-enrolls at the school
- **THEN** a new active enrollment is created
- **AND** the student counts toward billing again
- **AND** the alumni record is preserved as history
