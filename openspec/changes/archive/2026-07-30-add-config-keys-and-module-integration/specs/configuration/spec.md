# Configuration — Delta Spec (Add Keys & Module Integration)

## ADDED Requirements

### Requirement: auth.jwtExpirySeconds

The system MUST seed a config key `auth.jwtExpirySeconds` with type `number`, default `3600`, category `Business Rules`, module `auth`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='auth.jwtExpirySeconds'` returns 1

#### Scenario: Auth module reads JWT expiry from config
- **WHEN** the auth service mints a JWT for a user login
- **THEN** the `exp` claim is set to `now + config.get('auth.jwtExpirySeconds', institution_id=ctx.institution_id)` seconds, NOT hardcoded 3600

#### Scenario: Institution override changes JWT expiry
- **WHEN** an institution sets `auth.jwtExpirySeconds` to 7200
- **THEN** users logging in at that institution get JWTs that expire in 2 hours instead of 1 hour

---

### Requirement: auth.inviteExpiryDays

The system MUST seed a config key `auth.inviteExpiryDays` with type `number`, default `7`, category `Business Rules`, module `auth`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='auth.inviteExpiryDays'` returns 1

#### Scenario: Invite token uses config value for expiry
- **WHEN** the auth service creates an invite token
- **THEN** the token's `exp` claim is set to `now + config.get('auth.inviteExpiryDays')` days, NOT hardcoded 7

---

### Requirement: auth.passwordResetRedirectUrl

The system MUST seed a config key `auth.passwordResetRedirectUrl` with type `string`, default `http://localhost:3000/reset-password`, category `Business Rules`, module `auth`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='auth.passwordResetRedirectUrl'` returns 1

#### Scenario: Password reset uses config URL
- **WHEN** the auth service sends a password reset email
- **THEN** the `redirect_to` parameter is `config.get('auth.passwordResetRedirectUrl')`, NOT hardcoded `http://localhost:3000/reset-password`

#### Scenario: Production override works
- **WHEN** a platform sets `auth.passwordResetRedirectUrl` to `https://school.example.com/reset-password`
- **THEN** password reset emails redirect to the production URL

---

### Requirement: homework.lateSubmissionPolicy

The system MUST seed a config key `homework.lateSubmissionPolicy` with type `string`, default `submitted`, category `Business Rules`, module `homework`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='homework.lateSubmissionPolicy'` returns 1

#### Scenario: Homework module reads policy from config
- **WHEN** a student submits homework after the due date
- **THEN** the submission status is determined by `config.get('homework.lateSubmissionPolicy', institution_id=ctx.institution_id)`, NOT hardcoded `"late"`

#### Scenario: Policy value "submitted" treats all as on-time
- **WHEN** `homework.lateSubmissionPolicy` is `"submitted"` and a student submits after due date
- **THEN** the submission status is `"submitted"` (no late penalty)

#### Scenario: Policy value "late" marks as late
- **WHEN** `homework.lateSubmissionPolicy` is `"late"` and a student submits after due date
- **THEN** the submission status is `"late"`

#### Scenario: Policy value "rejected" blocks late submissions
- **WHEN** `homework.lateSubmissionPolicy` is `"rejected"` and a student submits after due date
- **THEN** the system returns 400 "Homework submission deadline has passed"

---

### Requirement: platform.configDeprecatedHideDays

The system MUST seed a config key `platform.configDeprecatedHideDays` with type `number`, default `90`, category `Platform`, module `config`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='platform.configDeprecatedHideDays'` returns 1

#### Scenario: Config resolver uses dynamic threshold
- **WHEN** listing keys and a key has `is_deprecated=true`
- **THEN** the auto-hide threshold is `config.get('platform.configDeprecatedHideDays')` days, NOT hardcoded 90

#### Scenario: Platform override changes hide threshold
- **WHEN** platform sets `platform.configDeprecatedHideDays` to 30
- **THEN** deprecated keys auto-hide after 30 days instead of 90

---

### Requirement: homework.closedStatusValues

The system MUST seed a config key `homework.closedStatusValues` with type `json`, default `["active"]`, category `Business Rules`, module `homework`.

#### Scenario: Key is seeded on migration
- **WHEN** migration 010 is applied
- **THEN** `SELECT COUNT(*) FROM configuration_key WHERE key='homework.closedStatusValues'` returns 1

#### Scenario: Homework module reads allowed statuses from config
- **WHEN** checking if a homework accepts submissions
- **THEN** the module checks `hw.status in config.get('homework.closedStatusValues', institution_id=ctx.institution_id)`, NOT hardcoded `["active"]`

#### Scenario: Institution adds "closed" to allowed statuses
- **WHEN** an institution sets `homework.closedStatusValues` to `["active", "closed"]`
- **THEN** homeworks with status "closed" also accept submissions (grace period)

---

## MODIFIED Requirements

### Requirement: fee.lateFeePercentage (module integration)

The existing seeded key `fee.lateFeePercentage` (default `2`) MUST be consumed by the Fees module instead of the hardcoded value.

#### Scenario: Fees module reads late fee from config
- **WHEN** the Fees service calculates a late fee for an overdue payment
- **THEN** the late fee percentage is `config.get('fee.lateFeePercentage', institution_id=ctx.institution_id)`, NOT hardcoded `2`

#### Scenario: Institution override changes late fee
- **WHEN** an institution sets `fee.lateFeePercentage` to `5`
- **THEN** overdue payments at that institution incur 5% late fee instead of 2%

---

### Requirement: homework.maxAttachmentsPerAssignment (module integration)

The existing seeded key `homework.maxAttachmentsPerAssignment` (default `5`) MUST be consumed by the Homework module instead of the hardcoded value.

#### Scenario: Homework module reads max attachments from config
- **WHEN** the Homework DTO validates attachment count
- **THEN** the max is `config.get('homework.maxAttachmentsPerAssignment', institution_id=ctx.institution_id)`, NOT hardcoded `5`

#### Scenario: Institution override changes max attachments
- **WHEN** an institution sets `homework.maxAttachmentsPerAssignment` to `10`
- **THEN** teachers at that institution can attach up to 10 files per homework

---

### Requirement: homework.allowLateSubmission (module integration)

The existing seeded key `homework.allowLateSubmission` (default `false`) MUST be consumed by the Homework module instead of the hardcoded value.

#### Scenario: Homework module reads late submission toggle from config
- **WHEN** a student tries to submit homework after the due date
- **THEN** the module checks `config.get('homework.allowLateSubmission', institution_id=ctx.institution_id)`, NOT hardcoded `false`

#### Scenario: Institution enables late submissions
- **WHEN** an institution sets `homework.allowLateSubmission` to `true`
- **THEN** students can submit homework after the due date (status determined by `homework.lateSubmissionPolicy`)

#### Scenario: Institution disables late submissions
- **WHEN** an institution keeps `homework.allowLateSubmission` as `false`
- **THEN** students cannot submit homework after the due date (400 error)
