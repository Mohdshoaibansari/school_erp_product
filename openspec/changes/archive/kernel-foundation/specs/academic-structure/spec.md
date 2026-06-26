## ADDED Requirements

### Requirement: Academic year and terms
Feature: Academic Structure
Rule: Every institution has an academic calendar configured independently.

#### Scenario: Define academic year
- **GIVEN** an active institution
- **WHEN** an administrator defines an academic year with start and end dates
- **THEN** the year is created
- **AND** it becomes the current year if the current date falls within its range

#### Scenario: Terms within an academic year
- **GIVEN** an academic year
- **WHEN** terms are defined with start and end dates
- **THEN** the current term is determined by the current date

### Requirement: Grade, class, section hierarchy
Feature: Academic Structure
Rule: Schools follow a Grade ? Class ? Section hierarchy.

#### Scenario: Create grade levels
- **GIVEN** an institution of type School
- **WHEN** an administrator defines grades (1-12)
- **THEN** each grade is available for class creation

#### Scenario: Create classes within a grade
- **GIVEN** Grade 10 at an institution
- **WHEN** classes 10A and 10B are created
- **THEN** each class has its own roster of students
- **AND** each class can have a designated class teacher
