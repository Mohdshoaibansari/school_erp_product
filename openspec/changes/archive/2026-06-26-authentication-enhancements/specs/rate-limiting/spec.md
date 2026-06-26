## ADDED Requirements

### Requirement: Failed attempt tracking
Feature: Rate Limiting
Rule: The system tracks failed login attempts per user account.

#### Scenario: Track failed login attempt
- **GIVEN** a user attempts to login with incorrect credentials
- **WHEN** the authentication fails
- **THEN** the failed attempt count is incremented
- **AND** the timestamp is recorded

#### Scenario: Reset failed attempt count
- **GIVEN** a user with previous failed attempts
- **WHEN** they successfully authenticate
- **THEN** the failed attempt count is reset to zero

### Requirement: Account lockout
Feature: Rate Limiting
Rule: Accounts are temporarily locked after a configurable number of consecutive failed attempts.

#### Scenario: Account locked after threshold
- **GIVEN** a user with 5 consecutive failed login attempts (configurable)
- **WHEN** they attempt another login
- **THEN** the account is locked for 15 minutes (configurable)
- **AND** the user receives an error message indicating the account is locked
- **AND** the lockout expiration time is communicated

#### Scenario: Account automatically unlocks
- **GIVEN** a locked account
- **WHEN** the lockout period expires
- **THEN** the account is automatically unlocked
- **AND** the failed attempt count is reset

#### Scenario: Manual unlock by administrator
- **GIVEN** a locked account
- **WHEN** an administrator unlocks the account
- **THEN** the account is immediately unlocked
- **AND** the failed attempt count is reset

### Requirement: Configurable thresholds
Feature: Rate Limiting
Rule: Rate limiting thresholds are configurable per institution via Config Service.

#### Scenario: Institution configures rate limits
- **GIVEN** an institution administrator
- **WHEN** they configure rate limiting settings
- **THEN** the following values are settable:
  - `auth.max_failed_attempts`: Number of failed attempts before lockout (default: 5)
  - `auth.lockout_duration_minutes`: Duration of lockout in minutes (default: 15)
  - `auth.otp_max_attempts`: Max OTP verification attempts (default: 3)
  - `auth.otp_expiry_minutes`: OTP expiration time in minutes (default: 10)

#### Scenario: Rate limits apply per institution
- **GIVEN** two institutions with different rate limit configurations
- **WHEN** a user fails login at both institutions
- **THEN** each institution's rate limits are applied independently
