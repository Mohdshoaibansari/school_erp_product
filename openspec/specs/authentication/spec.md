# authentication Specification

## Purpose
TBD - created by archiving change add-c02-user-creation-activation. Update Purpose after archive.
## Requirements
### Requirement: Unified activation for both user tiers

`POST /api/auth/activate` SHALL handle both `client_user` and `app_user` tables. It SHALL first look up the user by UUID in `app_user`, and if not found, fall back to `client_user`. The lookup SHALL use `session.get()` (by primary key) for both tables, bypassing tenant filters since the activate endpoint operates without a resolved subdomain. Per D1.

#### Scenario: Activate resolves institution user in app_user
- **GIVEN** a valid invite JWT with `sub` pointing to an `app_user` row in `invited` state
- **WHEN** `POST /api/auth/activate` is called with `{invite_token, password}`
- **THEN** the user SHALL be found in `app_user`
- **AND** the lifecycle SHALL transition `invited → active`
- **AND** the response SHALL include `user_tier: "institution"`

#### Scenario: Activate resolves Client Director in client_user
- **GIVEN** a valid invite JWT with `sub` pointing to a `client_user` row in `invited` state
- **WHEN** `POST /api/auth/activate` is called with `{invite_token, password}`
- **THEN** the user SHALL be found in `client_user`
- **AND** the lifecycle SHALL transition `invited → active`
- **AND** the response SHALL include `user_tier: "client_leadership"`

#### Scenario: Activate returns 404 when user not found in either table
- **GIVEN** a valid invite JWT but the user_id does not exist in `app_user` or `client_user`
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `404 User not found`

---

### Requirement: Activate response includes user_tier and client_slug (no tokens)

The response from `POST /api/auth/activate` SHALL be `{message, user_id, user_tier, client_slug}`. It SHALL NOT return `access_token` or `refresh_token`. The `client_slug` field SHALL be derived from the user's owning client (`client.slug` for CDs, or `institution → client.slug` for institution users). The `user_tier` field SHALL be `"client_leadership"` for `client_user` rows and `"institution"` for `app_user` rows. Per D4.

#### Scenario: Activate response for institution user
- **GIVEN** an institution user activating via `/api/auth/activate`
- **WHEN** activation succeeds
- **THEN** the response SHALL be `{message: "User activated successfully", user_id: "<uuid>", user_tier: "institution", client_slug: "<slug>"}`
- **AND** SHALL NOT contain `access_token`, `refresh_token`, or `token`

#### Scenario: Activate response for Client Director
- **GIVEN** a CD activating via `/api/auth/activate`
- **WHEN** activation succeeds
- **THEN** the response SHALL be `{message: "User activated successfully", user_id: "<uuid>", user_tier: "client_leadership", client_slug: "<slug>"}`
- **AND** SHALL NOT contain `access_token`, `refresh_token`, or `token`

#### Scenario: Frontend redirects to client-scoped login
- **GIVEN** the activate response includes `client_slug: "greenwood"`
- **WHEN** the frontend processes the response
- **THEN** it SHALL redirect the user to `greenwood.<host>/login`
- **AND** the user SHALL log in with email + new password at that URL

---

### Requirement: Password validation on activate

`POST /api/auth/activate` SHALL delegate password strength validation to Supabase Auth via `update_user(password=..., email_confirm=True)`. If Supabase rejects the password (too short, too common), the endpoint SHALL return the Supabase error as a `400 Bad Request` (or `502 Bad Gateway` if the Supabase call itself fails). Per D1.

#### Scenario: Weak password rejected
- **GIVEN** a valid invite JWT
- **WHEN** `POST /api/auth/activate` is called with password `"123"`
- **THEN** Supabase Auth SHALL reject it
- **AND** the endpoint SHALL return `400 Bad Request` (or `502 Bad Gateway`) with the Supabase error message
- **AND** the user's lifecycle SHALL remain `invited`

#### Scenario: Already-active user returns 400
- **GIVEN** a valid invite JWT for a user whose lifecycle is already `active`
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `400 User is already active`

#### Scenario: Invalid or expired invite token returns 400
- **GIVEN** an invite JWT that is expired or has been tampered with
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `400 Invalid invite token`

