## ADDED Requirements

### Requirement: Configurable academic levels

Feature: Academic Structure
As a school admin
I want to define my school's academic hierarchy
So that the system matches my school's actual structure

#### Scenario: School with Class and Section levels
- **GIVEN** a school admin is configuring academic structure
- **WHEN** they add "Class" as level 1 and "Section" as level 2
- **THEN** the system accepts the level definitions with their display order
- **AND** subsequent operations require both levels to be specified for student placement

#### Scenario: School with Class, Stream, and Section levels
- **GIVEN** a school admin is configuring academic structure
- **WHEN** they add "Class" as level 1, "Stream" as level 2, and "Section" as level 3
- **THEN** the system accepts all three level definitions
- **AND** student placement requires all three levels

#### Scenario: School with Class only and no sections
- **GIVEN** a small school only uses Class as the sole academic level
- **WHEN** the admin configures only "Class" as a single required level
- **THEN** the system accepts a single-level structure
- **AND** students are placed directly into class instances

### Requirement: Academic level instances

Feature: Academic Structure
As a school admin
I want to create class sections and streams
So that students can be assigned to specific groups

#### Scenario: Admin creates section under a class
- **GIVEN** academic levels "Class" and "Section" are defined
- **WHEN** the admin creates "Class 5" and then creates "Section A" as a child of "Class 5"
- **THEN** Section A is linked to Class 5 in the hierarchy
- **AND** students can now be placed in Class 5, Section A

#### Scenario: Admin creates stream under senior class
- **GIVEN** academic levels "Class", "Stream", and "Section" are defined
- **WHEN** the admin creates "Class 11", then "Science" under it, then "Section A" under Science
- **THEN** the three-level hierarchy is correctly formed
- **AND** students can be placed in Class 11, Science, Section A

### Requirement: Subject catalog

Feature: Academic Structure
As a school admin
I want to define the subjects taught at the school
So that teachers can be assigned to subjects and classes

#### Scenario: Admin adds subjects to the school catalog
- **GIVEN** a school admin is setting up the school
- **WHEN** they add subjects Mathematics, English, Hindi, and Science
- **THEN** the subjects are available for teacher assignment and grade entry

### Requirement: Academic year management

Feature: Academic Structure
As a school admin
I want to manage academic years
So that data is organized by school year

#### Scenario: Admin creates a new academic year
- **GIVEN** the current academic year "2026-27" is active
- **WHEN** the admin creates a new academic year "2027-28" with start and end dates
- **THEN** the new year is created in draft status
- **AND** the current year remains active until explicitly changed

#### Scenario: Only one academic year is active at a time
- **GIVEN** academic year "2026-27" is active
- **WHEN** the admin activates "2027-28"
- **THEN** "2026-27" is automatically marked as completed
- **AND** "2027-28" becomes the active academic year

### Requirement: Teacher to class assignment

Feature: Academic Structure
As a school admin
I want to assign teachers as class teachers and subject teachers
So that each teacher's scope is correctly defined

#### Scenario: Admin assigns class teacher
- **GIVEN** a teacher Mr. Sharma exists and Section 5A exists
- **WHEN** the admin assigns Mr. Sharma as the class teacher of Section 5A
- **THEN** Mr. Sharma can now take attendance for Section 5A

#### Scenario: Admin assigns subject teacher
- **GIVEN** a teacher Mrs. Iyer exists and Mathematics is a defined subject
- **WHEN** the admin assigns Mrs. Iyer as the Mathematics teacher for Section 5A, 5B, and 6A
- **THEN** Mrs. Iyer can enter Mathematics grades for those sections only
