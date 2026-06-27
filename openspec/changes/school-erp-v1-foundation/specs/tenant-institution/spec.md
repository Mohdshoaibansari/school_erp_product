## ADDED Requirements

### Requirement: School self-service signup

Feature: Tenant Institution
As a prospective school administrator
I want to register my school on the platform
So that I can start using the ERP system

#### Scenario: School admin completes signup with valid information
- **GIVEN** a visitor is on the public signup page
- **WHEN** they submit the form with school name, board affiliation, admin name, admin email, and admin phone number
- **THEN** a new tenant record is created with the school name
- **AND** the school subdomain is provisioned for the school name
- **AND** an admin user account is created with the School Admin role
- **AND** a verification magic link is sent to the admin email

#### Scenario: Signup fails with duplicate school name
- **GIVEN** a school named "St. Mary's School" is already registered
- **WHEN** another visitor submits signup with the same school name
- **THEN** the signup is rejected
- **AND** the visitor is told the school name is already taken

#### Scenario: Signup fails with invalid email format
- **GIVEN** a visitor is on the public signup page
- **WHEN** they submit the form with an invalid email address
- **THEN** the signup is rejected
- **AND** the visitor is told the email format is invalid

### Requirement: Subdomain resolution

Feature: Tenant Institution
As the platform
I need to resolve which tenant a request belongs to
So that all data is scoped to the correct school

#### Scenario: Request is routed by subdomain
- **GIVEN** a teacher visits "stmarys.schoolerp.com"
- **WHEN** the API server receives the request
- **THEN** the subdomain "stmarys" is extracted
- **AND** the tenant matching that subdomain is loaded
- **AND** the request context is set to that tenant for all downstream operations

#### Scenario: Request with unknown subdomain returns error
- **GIVEN** no tenant is registered with subdomain "unknownschool"
- **WHEN** a user visits "unknownschool.schoolerp.com"
- **THEN** the system responds with an error indicating the school is not found

### Requirement: First-time setup wizard

Feature: Tenant Institution
As a newly registered school admin
I want a guided setup wizard
So that I can configure my school before using the system

#### Scenario: School admin sees setup wizard on first login
- **GIVEN** a school admin has verified their email and logged in for the first time
- **WHEN** they access the dashboard
- **THEN** they are presented with a setup wizard prompting them to configure academic levels, subjects, invite teachers, and enroll students

#### Scenario: School admin skips wizard step
- **GIVEN** a school admin is on step 2 of the setup wizard
- **WHEN** they skip to a later step without completing step 2
- **THEN** the wizard allows navigation
- **AND** the onboarding status remains incomplete until all required steps are finished

### Requirement: Tenant lifecycle

Feature: Tenant Institution
As the super admin
I want to manage tenant statuses
So that I can suspend or archive schools as needed

#### Scenario: Super admin suspends a school
- **GIVEN** a school tenant is active
- **WHEN** the super admin marks the tenant as SUSPENDED
- **THEN** all users from that school are prevented from logging in
- **AND** API requests for that tenant return an access denied response
