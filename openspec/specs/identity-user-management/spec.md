# identity-user-management Specification

## Purpose
TBD - created by archiving change add-c02-user-creation-activation. Update Purpose after archive.
## Requirements
### Requirement: Unified invite token minting for institution users

`POST /api/v1/users` SHALL mint an invite JWT for every newly created institution user and return it alongside the user record. The response contract SHALL be `{user: UserDTO, invite_url: str}`. The invite JWT SHALL be minted using the existing `mint_invite_token()` function from `kernel/auth/services/invite_token.py` with the user's UUID and email. Per D1.

#### Scenario: Institution user creation returns invite_url
- **GIVEN** a Client Director is authenticated with a valid `client_id` and `institution_id`
- **WHEN** `POST /api/v1/users` is called with `{email, name, user_category_id, institution_id}`
- **THEN** the response SHALL contain `user` (a full `UserDTO` as currently returned) AND `invite_url` (a string containing the invite JWT)
- **AND** the Supabase Auth user SHALL be created with no password
- **AND** the `app_user` row SHALL have `lifecycle_status = "invited"`

#### Scenario: Invite JWT is valid and verifiable
- **GIVEN** the invite_url returned from user creation
- **WHEN** the token is extracted and verified via `verify_invite_token()`
- **THEN** the decoded payload SHALL contain `sub` (the user's UUID) and `email`
- **AND** the `iss` claim SHALL be `"school-erp/invite"`
- **AND** the `exp` claim SHALL be `now + config.get('auth.inviteExpiryDays')` days

#### Scenario: PO-created Client Director already returns invite_url (no regression)
- **GIVEN** the Platform Owner bootstrap endpoint `POST /api/v1/platform/clients/{id}/users`
- **WHEN** called with CD details
- **THEN** the response SHALL continue to include `invite_url` as before
- **AND** the invite JWT SHALL be structurally identical to institution-user invite JWTs

---

### Requirement: Optional role_id on user creation

`POST /api/v1/users` SHALL accept an optional `role_id` field in the request body. When provided, the role SHALL be assigned atomically in the same database transaction as user creation by inserting a row into the `role_assignment` table (or its equivalent). When omitted, the user SHALL be created without a role assignment — role assignment can be performed later via `POST /api/v1/users/{id}/roles`. Per D2.

#### Scenario: User created with role_id
- **GIVEN** a valid `role_id` for a role available in the current institution
- **WHEN** `POST /api/v1/users` is called with `{email, name, user_category_id, institution_id, role_id}`
- **THEN** the response SHALL contain the created user AND `invite_url`
- **AND** a `role_assignment` row SHALL exist linking the user to the role in the specified institution
- **AND** the role assignment SHALL be committed in the same transaction as the `app_user` row

#### Scenario: User created without role_id
- **GIVEN** a request body that does NOT include `role_id`
- **WHEN** `POST /api/v1/users` is called
- **THEN** the user SHALL be created successfully with `lifecycle_status = "invited"`
- **AND** no `role_assignment` row SHALL exist for this user
- **AND** the existing `POST /api/v1/users/{id}/roles` endpoint SHALL still be available for later assignment

#### Scenario: Invalid role_id returns 400
- **GIVEN** a `role_id` that does not exist or is not available at this institution
- **WHEN** `POST /api/v1/users` is called
- **THEN** the response SHALL be `400 Bad Request` with a message indicating the role is invalid
- **AND** no user SHALL be created (atomic rollback)

---

### Requirement: Single lifecycle arc for all user types

Both `client_user` and `app_user` rows SHALL follow the lifecycle `invited → active` via `/api/auth/activate`. The `pending` state SHALL be retained on the lifecycle state machine for manual admin transitions via `POST /api/v1/users/{id}/transition` but SHALL NOT be used in the normal activation flow. Per D1.

#### Scenario: Institution user transitions invited → active via activate
- **GIVEN** an institution user in `invited` state
- **WHEN** the user completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `app_user.lifecycle_status` SHALL be `"active"`
- **AND** a `user_lifecycle_event` row SHALL record the transition with reason `"Completed invite activation"`

#### Scenario: Client Director transitions invited → active via activate (no regression)
- **GIVEN** a CD in `invited` state
- **WHEN** the CD completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `client_user.lifecycle_status` SHALL be `"active"`
- **AND** a `client_user_lifecycle_event` row SHALL record the transition

#### Scenario: pending state preserved on state machine
- **GIVEN** the user lifecycle state machine definition
- **WHEN** inspected
- **THEN** `pending` SHALL remain a valid state
- **AND** `POST /api/v1/users/{id}/transition` SHALL still support `invited → pending` and `pending → active` transitions

---

### Requirement: Config-driven invite URL

The invite URL returned by both `POST /api/v1/users` (institution users) and `POST /api/v1/platform/clients/{id}/users` (CDs) SHALL be built using the config key `app.activationBaseUrl`. The URL format SHALL be `{app.activationBaseUrl}/activate?token={invite_jwt}`. The hardcoded `"http://127.0.0.1:8000"` SHALL be removed from `client_user_service.py`. Per D3.

#### Scenario: Invite URL uses config value
- **GIVEN** `app.activationBaseUrl` is set to `"https://app.school-erp.com"`
- **WHEN** any user creation endpoint mints an invite URL
- **THEN** the URL SHALL be `"https://app.school-erp.com/activate?token=<jwt>"`
- **AND** SHALL NOT be `"http://127.0.0.1:8000/activate?token=<jwt>"`

#### Scenario: Dev default when config not explicitly set
- **GIVEN** `app.activationBaseUrl` has its seeded default value
- **WHEN** the invite URL is built in a local dev environment
- **THEN** the URL SHALL default to a value suitable for local development (e.g., `"http://127.0.0.1:8000"`)

