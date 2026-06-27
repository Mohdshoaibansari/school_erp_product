## ADDED Requirements

### Requirement: Student enrollment

Feature: Student Management
As a school admin
I want to enroll students into classes
So that students are registered in the system

#### Scenario: Admin enrolls a student manually
- **GIVEN** the school has defined academic levels and classes
- **WHEN** the admin enters student name, date of birth, guardian name, guardian phone, and assigns them to Class 5, Section A
- **THEN** a student record is created with the provided details
- **AND** the student is assigned to Class 5, Section A
- **AND** the admission date is recorded

#### Scenario: Admin enrolls student with missing required fields
- **GIVEN** the admin is filling the enrollment form
- **WHEN** they submit without providing the student name
- **THEN** the enrollment is rejected
- **AND** the admin is told which required fields are missing

### Requirement: Bulk student import via CSV

Feature: Student Management
As a school admin
I want to import students from a CSV spreadsheet
So that I can onboard an entire school quickly

#### Scenario: Admin uploads valid CSV file
- **GIVEN** the admin has a CSV file with columns: name, dob, guardian_name, guardian_phone, class, section
- **WHEN** they upload the file for import
- **THEN** the system processes the CSV and creates student records for each row
- **AND** returns a summary of how many students were created and any errors

#### Scenario: CSV contains invalid rows
- **GIVEN** a CSV file has some rows with missing names or invalid dates
- **WHEN** the admin uploads the file
- **THEN** valid rows are processed
- **AND** invalid rows are reported with the specific error for each row
- **AND** the admin can download an error report

### Requirement: Student profile

Feature: Student Management
As a school admin or teacher
I want to view and update student profiles
So that student information stays current

#### Scenario: Teacher views student details
- **GIVEN** a student "Rahul" is enrolled in Section 5A
- **WHEN** the class teacher of Section 5A views Rahul's profile
- **THEN** they see Rahul's name, date of birth, guardian contact, and current class assignment

#### Scenario: Admin updates guardian phone number
- **GIVEN** a student record exists with an old guardian phone number
- **WHEN** the admin updates the guardian phone number
- **THEN** the profile is updated with the new number

### Requirement: Academic year promotion

Feature: Student Management
As a school admin
I want to promote students to the next class at year end
So that the school can transition to a new academic year

#### Scenario: Admin bulk promotes students from one class to the next
- **GIVEN** Class 5A has 40 students at the end of academic year "2026-27"
- **WHEN** the admin selects all 40 students and promotes them to Class 6A for the new academic year "2027-28"
- **THEN** all 40 students are assigned to Class 6A in "2027-28"
- **AND** their historical enrollment in Class 5A for "2026-27" is preserved

#### Scenario: Admin excludes a detained student from promotion
- **GIVEN** Class 5A has 40 students including one who is being detained
- **WHEN** the admin unchecks the detained student and promotes the remaining 39
- **THEN** 39 students are promoted to Class 6A
- **AND** the detained student remains in Class 5A

#### Scenario: Admin promotes to stream at senior secondary
- **GIVEN** Class 10 students are being promoted to Class 11 which has streams Science and Commerce
- **WHEN** the admin promotes a student and selects the Science stream
- **THEN** the student is placed in Class 11, Science for the new academic year

### Requirement: Student status management

Feature: Student Management
As a school admin
I want to manage student statuses
So that only active students appear in day-to-day operations

#### Scenario: Admin archives a transferred student
- **GIVEN** a student has transferred to another school
- **WHEN** the admin marks the student as TRANSFERRED
- **THEN** the student no longer appears in active attendance rosters
- **AND** the student's historical data remains accessible for reports
