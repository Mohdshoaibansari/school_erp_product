## Purpose

This is a **MODIFIED** delta spec for the `identity-user-management` domain (C-02). It describes the four behavioral changes to C-02's user creation and lifecycle management that result from C-03 Authentication being introduced. These are genuine behavioral changes — user creation and lifecycle transitions are no longer pure DB operations; they now propagate to Supabase Auth.

**Source of truth:** C-02's original spec (archived in `2026-07-11-add-c02-identity-user-management`). The ADDED spec for C-03 is at `specs/authentication/spec.md`.

## Requirements

### Requirement: User Creation — Supabase Auth Integration (MODIFIED)

C-02's `create_user` service method SHALL be modified to also call Supabase Admin API `createUser({ id=X, email, email_confirm: false })` to create a matching `auth.users` row. The shared UUID model (D2) ensures `auth.users.id == app_user.id`. On Supabase creation failure, the `app_user` insert is rolled back (transactional) — no orphaned rows (D20a).

The Supabase user is created with `email_confirm: false` — the user cannot log in until they accept the invitation (C-03's `/auth/activate` endpoint sets the password and confirms the email).

Trace: D3, D20a, AC-2, AC-19.

#### Scenario: User creation inserts both app_user and auth.users
- **WHEN** an admin creates a new user via `POST /users`
- **THEN** the service inserts an `app_user` row AND calls Supabase Admin API `createUser({ id=X, email, email_confirm: false })` with the same UUID

#### Scenario: Supabase creation failure rolls back app_user insert
- **WHEN** the Supabase `createUser` call fails (network error, Supabase unavailable, email already exists in Supabase)
- **THEN** the `app_user` insert is rolled back and the endpoint returns an error to the admin ("failed to create user"); no orphaned `app_user` row exists

#### Scenario: Shared UUID ensures identity alignment
- **WHEN** a user is created
- **THEN** `auth.users.id == app_user.id` — the same UUID is used for both records

### Requirement: User Suspension — Supabase Session Revocation (MODIFIED)

C-02's `transition_lifecycle` service method SHALL be modified so that when transitioning to `suspended`, it also calls Supabase Admin API `signOut(uid, 'global')` to revoke all refresh tokens. The suspended user's existing access token expires within the hour. D18 blocks re-login (lifecycle not `active`).

Trace: D20b, AC-20.

#### Scenario: Suspension revokes all Supabase sessions
- **WHEN** an admin suspends a user (transition to `suspended`)
- **THEN** the service calls Supabase `signOut(uid, 'global')` to revoke all refresh tokens; the suspended user's access token expires within ≤1h; re-login is blocked by D18 (lifecycle not `active`)

### Requirement: User Archival — Supabase Identity Deletion (MODIFIED)

C-02's `transition_lifecycle` service method SHALL be modified so that when transitioning to `archived`, it also calls Supabase Admin API `signOut(uid, 'global')` + `deleteUser(uid)` to remove the Supabase Auth identity entirely. The `app_user` row is retained for FK integrity (referenced by `role_assignment`, `user_identifier`, `user_lifecycle_event`).

Trace: D20b, AC-20.

#### Scenario: Archival removes Supabase Auth identity
- **WHEN** an admin archives a user (transition to `archived` — terminal)
- **THEN** the service calls Supabase `signOut(uid, 'global')` + `deleteUser(uid)`; the `app_user` row remains for FK integrity; the user cannot log in (Supabase identity is gone)

### Requirement: User Email Change — Supabase Email Propagation (MODIFIED)

C-02's `update_user` service method SHALL be modified so that when the email field changes, it also calls Supabase Admin API `updateUser(uid, { email, email_confirm: false })` to propagate the email change. Supabase sends a confirmation email to the new address.

Trace: D20b, AC-20.

#### Scenario: Email change propagates to Supabase
- **WHEN** an admin changes a user's email
- **THEN** the service calls Supabase `updateUser(uid, { email, email_confirm: false })` to update the Supabase Auth email; Supabase sends a confirmation email to the new address

#### Scenario: Non-email updates do not call Supabase
- **WHEN** an admin updates a user's name or category (not email)
- **THEN** no Supabase Auth call is made; the update is a pure DB operation
