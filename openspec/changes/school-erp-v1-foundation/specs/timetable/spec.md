## ADDED Requirements

### Requirement: Weekly timetable grid

Feature: Timetable
As a school admin
I want to create a weekly timetable for each section
So that teachers and students know their daily schedule

#### Scenario: Admin creates a timetable entry
- **GIVEN** Section 5A exists with defined subjects and teachers
- **WHEN** the admin assigns Mathematics with Mr. Sharma to Monday, Period 1 for Section 5A
- **THEN** the timetable entry is created
- **AND** it appears in Section 5A's weekly grid at the correct slot

#### Scenario: Admin creates full weekly grid for a section
- **GIVEN** Section 5A has subjects and teachers assigned
- **WHEN** the admin fills the weekly grid with subjects for each period and day
- **THEN** the complete timetable is saved for Section 5A
- **AND** the grid shows all subjects, teachers, and time slots

### Requirement: Teacher allocation in timetable

Feature: Timetable
As a school admin
I want to see teacher availability when creating the timetable
So that I avoid scheduling conflicts

#### Scenario: Admin sees teacher already assigned to another section
- **GIVEN** Mr. Sharma is already assigned to Section 5A on Monday Period 1
- **WHEN** the admin tries to assign Mr. Sharma to Section 5B on Monday Period 1
- **THEN** the system shows that Mr. Sharma has a conflict
- **AND** the admin can choose to override or pick a different time

### Requirement: Timetable viewing

Feature: Timetable
As a teacher
I want to view my personal timetable
So that I know which classes I have each day

#### Scenario: Teacher views their weekly schedule
- **GIVEN** Mr. Sharma teaches Mathematics to multiple sections
- **WHEN** he views his personal timetable
- **THEN** he sees all periods assigned to him across all sections
- **AND** each entry shows the section, subject, period, and room

### Requirement: Module gating for timetable

Feature: Timetable
As the system
I want timetable access to be restricted to schools with the module enabled
So that only paying schools can use it

#### Scenario: School without timetable module cannot access
- **GIVEN** a school does not have the Timetable module enabled
- **WHEN** any user from that school tries to access timetable endpoints
- **THEN** the request is rejected with a module-not-available response
