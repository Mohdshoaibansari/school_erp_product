## ADDED Requirements

### Requirement: School day calendar
Feature: Calendar Service
Rule: Every institution has a calendar that defines school days, holidays, and events.

#### Scenario: Define a school day
- **GIVEN** an active institution
- **WHEN** an administrator defines a date as a school day
- **THEN** attendance calculation treats it as a regular day

#### Scenario: Define a holiday
- **GIVEN** an active institution
- **WHEN** an administrator marks a date as a holiday
- **THEN** attendance calculation skips that day
- **AND** no absence is recorded for that date

### Requirement: Calendar queries
Feature: Calendar Service
Rule: Modules query the calendar to determine date types.

#### Scenario: Attendance checks if today is a school day
- **GIVEN** today's date
- **WHEN** the attendance module checks the calendar
- **THEN** it receives the day type (school_day, holiday, exam_day, event)
- **AND** decides whether to expect attendance marks

#### Scenario: Exam days are distinct from holidays
- **GIVEN** a date marked as exam_day
- **WHEN** the attendance module checks
- **THEN** the day is a school day for attendance purposes
- **AND** the event type is exam_day for scheduling purposes
