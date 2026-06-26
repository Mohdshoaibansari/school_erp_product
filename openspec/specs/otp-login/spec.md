## ADDED Requirements

### Requirement: OTP-based passwordless login
Feature: OTP Login
Rule: Users can request a one-time password via email and use it to authenticate without their regular password.

#### Scenario: Request OTP for login
- **GIVEN** a user with a registered email
- **WHEN** they request an OTP for login
- **THEN** a 6-digit OTP is generated with a 10-minute expiration
- **AND** the OTP is sent to the user's registered email

#### Scenario: Verify OTP and login
- **GIVEN** a user with a valid, unexpired OTP
- **WHEN** they submit the correct OTP
- **THEN** the system returns a JWT access token and a refresh token
- **AND** the OTP is invalidated (single-use)

#### Scenario: OTP expires
- **GIVEN** a user with an expired OTP
- **WHEN** they attempt to verify the OTP
- **THEN** the system returns an error indicating the OTP has expired
- **AND** the user is prompted to request a new OTP

#### Scenario: Invalid OTP attempt
- **GIVEN** a user with an OTP
- **WHEN** they submit an incorrect OTP
- **THEN** the system returns an error
- **AND** the attempt is recorded for rate limiting

### Requirement: OTP for password reset
Feature: OTP Login
Rule: OTP can be used as a verification step for password reset flows.

#### Scenario: Request OTP for password reset
- **GIVEN** a user who has forgotten their password
- **WHEN** they request a password reset
- **THEN** an OTP is sent to their registered email
- **AND** the OTP is required before allowing password change

#### Scenario: Reset password with OTP
- **GIVEN** a user with a valid OTP for password reset
- **WHEN** they submit the OTP and a new password
- **THEN** the password is updated
- **AND** the OTP is invalidated
- **AND** all existing sessions are invalidated
