## ADDED Requirements

### Requirement: Fee structure definition

Feature: Fee Management
As a school admin
I want to define fee structures per class
So that each class has a clear fee schedule

#### Scenario: Admin creates a fee structure for a class
- **GIVEN** the school has defined Class 5
- **WHEN** the admin creates a fee structure with components: Tuition Fee (5000), Activity Fee (1000), and sets it for the academic year "2026-27"
- **THEN** the fee structure is saved for Class 5
- **AND** the total fee for the class is displayed as 6000

#### Scenario: Admin modifies an existing fee structure
- **GIVEN** a fee structure exists for Class 5
- **WHEN** the admin updates the Tuition Fee amount from 5000 to 5500
- **THEN** the fee structure is updated
- **AND** the new total is reflected for all students in Class 5

### Requirement: Fee collection

Feature: Fee Management
As an accountant
I want to record fee payments from students
So that payments are tracked against the fee structure

#### Scenario: Accountant records a full payment
- **GIVEN** a student in Class 5 has a pending fee of 6000
- **WHEN** the accountant records a payment of 6000 for that student
- **THEN** the payment is recorded with today's date
- **AND** the student's pending balance becomes 0

#### Scenario: Accountant records a partial payment
- **GIVEN** a student has a pending fee of 6000
- **WHEN** the accountant records a payment of 3000
- **THEN** the payment is recorded
- **AND** the student's pending balance becomes 3000

### Requirement: Fee receipt generation

Feature: Fee Management
As an accountant
I want to generate receipts for fee payments
So that parents receive proof of payment

#### Scenario: Receipt is generated for a payment
- **GIVEN** a fee payment of 6000 has been recorded
- **WHEN** the accountant generates a receipt
- **THEN** a receipt is created with a unique receipt number
- **AND** the receipt shows student name, class, amount paid, date, and payment method

### Requirement: Pending dues report

Feature: Fee Management
As an accountant
I want to view pending fee dues
So that I can follow up with parents who haven't paid

#### Scenario: Accountant views pending dues report
- **GIVEN** some students have pending fee balances
- **WHEN** the accountant views the pending dues report filtered by class
- **THEN** they see a list of students with outstanding balances
- **AND** each entry shows student name, class, total fee, amount paid, and pending balance

#### Scenario: Report shows zero pending when all fees are paid
- **GIVEN** all students in Class 5 have paid their full fees
- **WHEN** the accountant views the pending dues report for Class 5
- **THEN** the report shows zero pending dues for that class
