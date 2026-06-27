## ADDED Requirements

### Requirement: Role-based module access

Feature: Authorization
As the system
I want to restrict module access by role
So that users can only access features appropriate to their role

#### Scenario: Teacher accesses attendance module
- **GIVEN** a user with the Teacher role is logged in
- **WHEN** they navigate to the attendance module
- **THEN** access is granted because the Teacher role has attendance permission

#### Scenario: Accountant accesses attendance module
- **GIVEN** a user with the Accountant role is logged in
- **WHEN** they navigate to the attendance module
- **THEN** access is denied because the Accountant role lacks attendance permission

### Requirement: Attribute-based class teacher scoping

Feature: Authorization
As a class teacher
I want to see only my assigned section when taking attendance
So that I cannot accidentally modify another section's attendance

#### Scenario: Class teacher views attendance roster
- **GIVEN** Mr. Sharma is a class teacher for Section 5A only
- **WHEN** he opens the attendance page
- **THEN** the system shows only students from Section 5A
- **AND** Section 5B students are not visible

#### Scenario: Class teacher with multiple sections sees all assigned sections
- **GIVEN** Mrs. Gupta is a class teacher for both Section 5A and Section 5B
- **WHEN** she opens the attendance page
- **THEN** the system shows students from both Section 5A and Section 5B
- **AND** she can switch between sections to mark attendance

### Requirement: Attribute-based subject teacher scoping

Feature: Authorization
As a subject teacher
I want to see only my assigned classes and subject when entering grades
So that I see only the students and subjects I am responsible for

#### Scenario: Subject teacher views grade entry for their assigned classes
- **GIVEN** Mr. Sharma teaches Mathematics to Sections 5A, 5B, and 6A
- **WHEN** he opens the grade entry page for Mathematics
- **THEN** the system shows only Sections 5A, 5B, and 6A for Mathematics
- **AND** Section 5C Mathematics students are not visible

#### Scenario: Subject teacher cannot access another teacher's subject
- **GIVEN** Mr. Sharma teaches only Mathematics
- **WHEN** he tries to access grade entry for English
- **THEN** the system shows no classes available
