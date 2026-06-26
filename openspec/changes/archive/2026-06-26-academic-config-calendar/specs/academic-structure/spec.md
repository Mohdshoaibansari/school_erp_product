## ADDED Requirements

### Requirement: Academic year and terms
Feature: Academic Structure
Rule: Each institution independently configures academic years with start/end dates and terms.

#### Scenario: Define academic year
- **GIVEN** an institution
- **WHEN** an academic year is created with start and end dates
- **THEN** the year becomes "current" if today falls within the date range

#### Scenario: Terms within an academic year
- **GIVEN** an academic year with terms defined
- **WHEN** the system checks the current term
- **THEN** the term containing today's date is returned

### Requirement: Grade, class, section hierarchy
Feature: Academic Structure
Rule: Schools follow a Grade → Class → Section hierarchy where grades are created first, then classes within grades.

#### Scenario: Create grade levels
- **GIVEN** an institution
- **WHEN** grades 1-12 are created
- **THEN** classes can be created within each grade

#### Scenario: Create classes within a grade
- **GIVEN** Grade 10 exists
- **WHEN** classes 10A and 10B are created
- **THEN** each class has its own roster and optional class teacher
