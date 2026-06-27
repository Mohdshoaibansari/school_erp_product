## ADDED Requirements

### Requirement: Daily attendance marking

Feature: Attendance
As a class teacher
I want to mark daily attendance for my section
So that the school can track student presence

#### Scenario: Teacher marks attendance for assigned section
- **GIVEN** Mr. Sharma is the class teacher of Section 5A
- **WHEN** he opens the attendance page for today and marks each student as Present or Absent
- **THEN** attendance records are saved for all students in Section 5A for today
- **AND** a confirmation message shows the count of present and absent students

#### Scenario: Teacher cannot mark attendance for unassigned section
- **GIVEN** Mr. Sharma is class teacher of Section 5A only
- **WHEN** he tries to access the attendance page for Section 5B
- **THEN** the system shows no students
- **AND** he cannot mark attendance for Section 5B

#### Scenario: Attendance already marked for today shows existing records
- **GIVEN** attendance was already marked for Section 5A today
- **WHEN** the class teacher opens the attendance page
- **THEN** they see today's existing attendance records
- **AND** they can modify any student's status

### Requirement: Bulk attendance marking

Feature: Attendance
As a class teacher
I want to mark all students present by default
So that I can quickly mark attendance for the whole section

#### Scenario: Teacher marks all present then changes absentees
- **GIVEN** the teacher opens the attendance page for Section 5A
- **WHEN** they click "Mark All Present"
- **THEN** all students are initially set to Present
- **AND** the teacher can then individually mark specific students as Absent

### Requirement: Attendance reports

Feature: Attendance
As a principal
I want to view attendance reports
So that I can monitor student presence across the school

#### Scenario: Principal views attendance summary by date
- **GIVEN** the principal selects a date range
- **WHEN** they view the school-wide attendance report
- **THEN** they see per-section attendance counts for each day in the range
- **AND** the report shows present, absent, and percentage for each section

#### Scenario: Teacher views their section attendance history
- **GIVEN** a class teacher selects Section 5A and a month
- **WHEN** they view the attendance history
- **THEN** they see a day-by-day grid showing each student's attendance status for the month
