## ADDED Requirements

### Requirement: Email/password authentication
Feature: Authentication
Rule: All authentication flows through this service. No module implements its own login.

#### Scenario: User logs in with valid credentials
- **GIVEN** an active user with a registered email and password
- **WHEN** they submit the correct email and password
- **THEN** the system returns a JWT access token and a refresh token
- **AND** the login attempt is recorded

#### Scenario: User logs in with wrong password
- **GIVEN** an active user with a registered email
- **WHEN** they submit the correct email but wrong password
- **THEN** the system returns an authentication error
- **AND** the failed attempt is recorded

#### Scenario: Account locks after failed attempts
- **GIVEN** a user with 5 consecutive failed login attempts
- **WHEN** they attempt another login
- **THEN** the account is temporarily locked for a configurable period
- **AND** the user is notified

### Requirement: Session management
Feature: Authentication
Rule: Sessions are managed via JWT with refresh token rotation.

#### Scenario: Access token expires
- **GIVEN** a user with an expired access token
- **WHEN** they present the token to a protected endpoint
- **THEN** the system returns a 401 Unauthorized
- **AND** the user can use their refresh token to obtain a new access token

#### Scenario: Refresh token rotation
- **GIVEN** a user with a valid refresh token
- **WHEN** they request a new access token
- **THEN** the old refresh token is invalidated
- **AND** a new refresh token is issued
