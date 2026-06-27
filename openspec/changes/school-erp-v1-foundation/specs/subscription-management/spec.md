## ADDED Requirements

### Requirement: Free tier with student cap

Feature: Subscription Management
As the platform
I want every new school to start on a free tier with a student limit
So that schools can try the core modules before purchasing

#### Scenario: New school gets free tier with default modules
- **GIVEN** a school completes signup
- **WHEN** the tenant record is created
- **THEN** the school is assigned the free tier
- **AND** the Student Management, Attendance, and Fee Management modules are enabled
- **AND** the student limit is set to 100

### Requirement: Hard student limit enforcement

Feature: Subscription Management
As the platform
I want to prevent schools from exceeding their student cap
So that the free tier cannot be overused without payment

#### Scenario: School at limit cannot add another student
- **GIVEN** a school on the free tier has exactly 100 active students
- **WHEN** the school admin tries to enroll a 101st student
- **THEN** the enrollment is rejected
- **AND** the admin is told the student limit has been reached
- **AND** the admin is prompted to upgrade

#### Scenario: School below limit can add students
- **GIVEN** a school on the free tier has 95 active students
- **WHEN** the school admin enrolls a new student
- **THEN** the enrollment succeeds
- **AND** the active student count becomes 96

#### Scenario: Existing modules continue working at limit
- **GIVEN** a school is at the 100-student limit
- **WHEN** a teacher marks attendance for an existing class
- **THEN** attendance marking works normally
- **AND** the limit does not affect existing operations

### Requirement: Paid module add-ons

Feature: Subscription Management
As a school admin
I want to add paid modules to my subscription
So that my school can access additional features

#### Scenario: School admin enables a paid module
- **GIVEN** a school is on the free tier
- **WHEN** the admin selects Timetable as a paid add-on
- **THEN** the Timetable module is enabled for the school
- **AND** the module appears in the school's navigation

#### Scenario: Request for disabled module is blocked
- **GIVEN** a school does not have the Exams module enabled
- **WHEN** a teacher tries to access the exams API endpoint
- **THEN** the request is rejected with a module-not-available response

### Requirement: Module visibility

Feature: Subscription Management
As a school admin
I want to see which modules are available and which are paid
So that I can make informed purchasing decisions

#### Scenario: Admin views module management page
- **GIVEN** a school admin is logged in
- **WHEN** they view the subscription management page
- **THEN** they see all modules listed with their current status
- **AND** free modules are marked as included
- **AND** paid modules show their add-on status
- **AND** the admin can see their current student count relative to the limit
