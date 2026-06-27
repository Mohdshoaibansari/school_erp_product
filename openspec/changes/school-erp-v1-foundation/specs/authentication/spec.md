## ADDED Requirements

### Requirement: Magic link login

Feature: Authentication
As a user
I want to log in using a magic link sent to my email
So that I can access the system without remembering a password

#### Scenario: User requests magic link for their school
- **GIVEN** a user navigates to their school subdomain login page
- **WHEN** they enter their registered email and request a login link
- **THEN** Supabase sends a magic link email
- **AND** the user is told to check their email

#### Scenario: User clicks valid magic link
- **GIVEN** a user has received a magic link email
- **WHEN** they click the link
- **THEN** they are authenticated and redirected to the dashboard
- **AND** their session is established with the correct tenant context

#### Scenario: Magic link is expired
- **GIVEN** a magic link was generated more than its validity period ago
- **WHEN** the user clicks the expired link
- **THEN** they are told the link has expired
- **AND** they are prompted to request a new link

#### Scenario: Unregistered email requests magic link
- **GIVEN** an email is not associated with any user in the school
- **WHEN** someone enters that email on the login page
- **THEN** the system does not send a magic link
- **AND** the user is told the email is not recognized

### Requirement: Tenant-scoped session

Feature: Authentication
As the system
I want sessions to be scoped to a specific tenant
So that a user logged into one school cannot access another school's data

#### Scenario: User with account in one school cannot access another
- **GIVEN** a user is logged into "stmarys.schoolerp.com"
- **WHEN** they change the URL to "otherschoool.schoolerp.com"
- **THEN** the session is not valid for the new subdomain
- **AND** they are prompted to log in again

### Requirement: Logout

Feature: Authentication
As a user
I want to log out of the system
So that my session is terminated

#### Scenario: User logs out successfully
- **GIVEN** a user is logged in
- **WHEN** they click logout
- **THEN** their session is terminated
- **AND** they are redirected to the login page
