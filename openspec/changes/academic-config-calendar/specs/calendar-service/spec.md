## ADDED Requirements

### Requirement: School day calendar
Feature: Calendar Service
Rule: Every institution has a calendar defining school days, holidays, and events.

#### Scenario: Define a school day
- **GIVEN** an institution
- **WHEN** a date is marked as a school day
- **THEN** attendance treats it as a regular day

#### Scenario: Define a holiday
- **GIVEN** an institution
- **WHEN** a date is marked as a holiday
- **THEN** attendance skips that day, no absence recorded

### Requirement: Calendar queries
Feature: Calendar Service
Rule: Modules query the calendar to determine date types.

#### Scenario: Attendance checks if today is a school day
- **GIVEN** the attendance module
- **WHEN** it queries today's date type
- **THEN** it receives the day type and decides whether to expect marks

#### Scenario: Exam days are distinct from holidays
- **GIVEN** an exam day in the calendar
- **WHEN** the attendance module checks the date
- **THEN** exam_day is treated as a school day for attendance but distinct for scheduling
