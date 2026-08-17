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

---
<!-- Synced from add-client-user-bootstrap delta spec -->
## MODIFIED Requirements

### Requirement: auth.jwtExpirySeconds

The `auth.jwtExpirySeconds` configuration key SHALL hold the platform-wide JWT TTL in seconds, applied to every custom HS256 JWT minted by the platform's auth service. **Widened for the `client-user-bootstrap` capability:** the key SHALL ALSO govern the TTL of the Client Director's custom HS256 JWT. This makes the key serve DOUBLE-DUTY: it governs the platform owner's JWT TTL AND the client-leadership (CD) JWT TTL. The key defaults to `3600` (one hour) and can be tuned by the PO without code deploy via `PATCH /api/v1/config/keys/$KEY_ID`. Stale values are reloaded into the in-memory cache via the C-08 NOTIFY/LISTEN mechanism.

The widened role of this key is the NATURAL-EXPIRY SAFETY NET for the `client-user-bootstrap` capability's deferred token-revocation design (per D12 of the `client-user-bootstrap` PRD). When the PO suspends a CD, the CD's currently-issued HS256 JWT keeps working until its TTL elapses; the smaller the `auth.jwtExpirySeconds` value, the shorter the replay window. The key itself, its default value, and its edit authorization matrix are unchanged — only the documented consumption surface grows.

#### Scenario: CD JWT TTL equals auth.jwtExpirySeconds
- **WHEN** the auth service mints a CD's custom HS256 JWT
- **THEN** the JWT's `exp` claim SHALL equal `iat + auth.jwtExpirySeconds` (resolved via `config.get('auth.jwtExpirySeconds')` at mint time)

#### Scenario: PO tunes TTL without code change
- **WHEN** the PO PATCHes the `auth.jwtExpirySeconds` key default to a different value
- **THEN** the next CD login SHALL mint a JWT with the NEW TTL
- **AND** no code deploy SHALL be required (the value is resolved at mint time from the C-08 resolver)

#### Scenario: Suspended CD replay window
- **WHEN** the PO suspends a CD whose HS256 JWT was minted with TTL = `auth.jwtExpirySeconds`
- **THEN** the suspended CD's JWT SHALL keep authorizing until `exp` is reached
- **AND** the next login attempt by that CD SHALL be rejected because `lifecycle_status != "active"`
- **AND** the replay window is bounded by `auth.jwtExpirySeconds` (per D12)

#### Scenario: Key default unchanged
- **WHEN** the C-08 migration seeds `auth.jwtExpirySeconds`
- **THEN** its `default_value` SHALL remain `3600`
- **AND** the widening introduced by `client-user-bootstrap` SHALL NOT require a new migration seeding step
---

### REQ-FE-CFG-01: Browse and Edit Config Keys and Values

The app SHALL provide a Configuration screen where the Institution Admin can browse config keys scoped to the institution and view/edit config values with type-aware input (P2-AC-8).

#### Scenario: Browse keys and edit values
- **WHEN** an Institution Admin opens the Configuration screen
- **THEN** they can browse institution-scoped config keys and view/edit config values with type-aware input

---

### REQ-FE-CFG-02: View Resolved (Effective) Value

The app SHALL allow the Institution Admin to view the resolved (effective) value for a config key, accounting for scope fallbacks (Institution → Client → Platform → default) (P2-AC-9).

#### Scenario: Effective value accounts for fallbacks
- **WHEN** an Institution Admin views a key's resolved value
- **THEN** the app shows the effective value after applying institution/client/platform fallbacks

---

### REQ-FE-CFG-03: View Config Audit Trail

The app SHALL allow the Institution Admin to view the config audit trail (who changed what, when) (P2-AC-10).

#### Scenario: Audit trail visible
- **WHEN** an Institution Admin views the config audit trail
- **THEN** they can see who changed what and when

---

### REQ-FE-CFG-04: All Keys Editable with Backend Validation

The app SHALL treat all config keys as editable; unsafe edits SHALL be blocked by backend validation, not hidden by the UI (R5).

#### Scenario: Unsafe edit rejected by backend
- **WHEN** an Institution Admin edits a key that backend validation considers unsafe
- **THEN** the backend rejects the edit and the app surfaces a friendly error, rather than the UI pre-hiding the key
