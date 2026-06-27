## ADDED Requirements

### Requirement: User profile management

Feature: Identity Users
As a school admin
I want to manage user profiles
So that staff accounts exist in the system

#### Scenario: School admin creates a teacher account
- **GIVEN** a school admin is logged in
- **WHEN** they create a new user with name, email, phone, and the Teacher role
- **THEN** a user account is created linked to the school's tenant
- **AND** an invitation email is sent to the teacher's email address

#### Scenario: School admin creates a duplicate user
- **GIVEN** a user with email "sharma@school.com" already exists in the school
- **WHEN** the admin tries to create another user with the same email
- **THEN** the creation is rejected
- **AND** the admin is told the email is already in use within this school

### Requirement: Role assignment

Feature: Identity Users
As a school admin
I want to assign roles to users
So that each staff member has appropriate access

#### Scenario: School admin assigns Principal role
- **GIVEN** a user account exists with the Teacher role
- **WHEN** the school admin changes their role to Principal
- **THEN** the user's role is updated to Principal
- **AND** their permissions update accordingly

#### Scenario: School admin cannot assign Super Admin role
- **GIVEN** a school admin is managing a user's roles
- **WHEN** they attempt to assign the Super Admin role
- **THEN** the assignment is rejected
- **AND** the admin is told they do not have permission to assign that role

### Requirement: Staff invitation

Feature: Identity Users
As a school admin
I want to invite staff members to join the system
So that teachers and other staff can access the ERP

#### Scenario: Teacher accepts invitation
- **GIVEN** a school admin has invited a teacher via email
- **WHEN** the teacher clicks the invitation link and verifies their email
- **THEN** the teacher's account becomes active
- **AND** the teacher can log in to the school's subdomain

### Requirement: User suspension

Feature: Identity Users
As a school admin
I want to suspend a user
So that former staff can no longer access the system

#### Scenario: Admin suspends an active teacher
- **GIVEN** a teacher is actively using the system
- **WHEN** the school admin suspends the teacher's account
- **THEN** the teacher is immediately logged out
- **AND** the teacher cannot log in again
