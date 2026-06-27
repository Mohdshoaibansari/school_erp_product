## ADDED Requirements

### Requirement: Exam schedule management

Feature: Exams Grades
As a school admin
I want to schedule exams
So that teachers and students know the exam timetable

#### Scenario: Admin creates an exam with subjects and dates
- **GIVEN** the school has defined subjects and classes
- **WHEN** the admin creates a "Mid-Term Exam" for Class 5, Section A with Mathematics on Monday, English on Tuesday, and Science on Wednesday
- **THEN** the exam schedule is created
- **AND** each subject has a date assigned

#### Scenario: Admin schedules exam for all sections of a class
- **GIVEN** Class 5 has Sections A and B
- **WHEN** the admin creates a "Final Exam" for Class 5 with subjects and dates
- **THEN** the exam schedule applies to both Section A and Section B

### Requirement: Marks entry

Feature: Exams Grades
As a subject teacher
I want to enter marks for my assigned subjects and classes
So that student performance is recorded

#### Scenario: Subject teacher enters marks for their class
- **GIVEN** Mr. Sharma teaches Mathematics to Sections 5A, 5B, and 6A
- **WHEN** he opens the marks entry page for the Mid-Term Mathematics exam
- **THEN** the system shows only Sections 5A, 5B, and 6A
- **AND** he can enter marks for each student in those sections

#### Scenario: Teacher cannot enter marks for another teacher's subject
- **GIVEN** Mr. Sharma teaches only Mathematics
- **WHEN** he tries to access marks entry for the English exam
- **THEN** the system shows no classes available for marks entry

#### Scenario: Marks entered exceed maximum marks
- **GIVEN** the exam is configured with a maximum of 100 marks
- **WHEN** a teacher enters 105 marks for a student
- **THEN** the entry is rejected
- **AND** the teacher is told the mark exceeds the maximum

### Requirement: Report card generation

Feature: Exams Grades
As a school admin
I want to generate report cards
So that student performance can be shared with parents

#### Scenario: Admin generates report cards for a class
- **GIVEN** all marks have been entered for the Final Exam for Class 5
- **WHEN** the admin generates report cards for Class 5
- **THEN** a report card is produced for each student
- **AND** each card shows the student's name, class, subject-wise marks, total, and percentage

#### Scenario: Report card generation blocked when marks are incomplete
- **GIVEN** marks for the English exam have not been entered for some students in Class 5
- **WHEN** the admin tries to generate report cards
- **THEN** the system warns that marks are incomplete
- **AND** the admin can choose to generate with missing marks shown as pending

### Requirement: Module gating for exams

Feature: Exams Grades
As the system
I want exam module access to be restricted to schools with the module enabled
So that only paying schools can use it

#### Scenario: School without exams module cannot access
- **GIVEN** a school does not have the Exams module enabled
- **WHEN** any user from that school tries to access exam endpoints
- **THEN** the request is rejected with a module-not-available response
