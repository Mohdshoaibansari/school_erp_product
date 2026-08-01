## ADDED Requirements

### Requirement: Two-tier user model

The platform SHALL model users in two physically distinct tables: `client_user` for client-leadership-scope users (Client Director and future Client Admins / Billing Contacts, who manage an entire client and have NO institution) and `app_user` for institution-scoped users (Admin, Teacher, Student, Parent inside one institution). No row in `client_user` SHALL have an `institution_id` column. No row in `app_user` SHALL have a NULL `institution_id` (enforced NOT NULL per the tenant-institution MODIFIED requirement). Per D1.

#### Scenario: Physically distinct tables
- **WHEN** the database schema is inspected
- **THEN** there SHALL exist a `client_user` table with `client_id` and `role_id` columns and NO `institution_id` column
- **AND** the `app_user` table SHALL have `institution_id` declared NOT NULL

#### Scenario: Client-leadership user lives in client_user
- **WHEN** a Client Director (or future Client Admin / Billing Contact) is created
- **THEN** the row SHALL be inserted into `client_user`
- **AND** MUST NOT be inserted into `app_user`

### Requirement: client_user table structure

The `client_user` table SHALL mirror `app_user` columns (`id`, `email`, `name`, `user_category_id`, `lifecycle_status`, `created_at`, `updated_at`) and add `role_id` (UUID FK to `role`) and `client_id` (UUID FK to `client`). The `role_id` column SHALL store the single client-leadership role directly on the row — there SHALL be NO separate `client_role_assignment` table (D3). Multiple CDs in a client are represented as multiple rows in `client_user`.

#### Scenario: Column set
- **WHEN** the `client_user` table is created
- **THEN** it SHALL include `id`, `email`, `name`, `user_category_id`, `lifecycle_status`, `role_id`, `client_id`, `created_at`, `updated_at`
- **AND** it SHALL NOT include `institution_id`

#### Scenario: Role FK target
- **WHEN** a `client_user.role_id` value is inspected
- **THEN** it SHALL reference an existing row in the global `role` table
- **AND** the referenced role SHALL be a client-leadership role (e.g., `client_director`)

### Requirement: client_user_lifecycle_event table

A parallel `client_user_lifecycle_event` table SHALL record every lifecycle transition of a `client_user` (mirroring `user_lifecycle_event` for `app_user` per D10). Each row SHALL capture the actor (the user who initiated the transition), the reason, the previous state, the new state, and the timestamp. The CD SHALL NOT drive their own lifecycle transitions EXCEPT the `invited → active` transition triggered by completing the invite flow.

#### Scenario: Event row on every transition
- **WHEN** a `client_user.lifecycle_status` transitions between any of `invited`, `active`, `suspended`, `archived`
- **THEN** a corresponding row SHALL be inserted into `client_user_lifecycle_event`
- **AND** the row SHALL record actor, reason, previous state, new state, timestamp

#### Scenario: CD completes invite themselves
- **WHEN** a CD clicks the invite link and sets their own password
- **THEN** the `invited → active` transition is recorded with actor = the CD themselves
- **AND** all other lifecycle transitions for that CD MUST be initiated by the PO only

### Requirement: Login lookup by user_metadata.user_tier

The `/api/auth/login` flow SHALL read `user_metadata.user_tier` from the Supabase Auth response and branch to the correct table lookup. For `user_tier = "client_leadership"`, login SHALL query `client_user`. For `user_tier = "institution"`, login SHALL query `app_user` as before. Every user-creation path in the backend (PO bootstrap CD, CD creating institution user) SHALL stamp `user_metadata.user_tier` at the time of Supabase Auth user creation. Per D2.

#### Scenario: Client-leadership login resolves to client_user
- **WHEN** a Supabase Auth user with `user_metadata.user_tier = "client_leadership"` submits login credentials
- **THEN** the login flow SHALL look up the user in `client_user`
- **AND** MUST NOT consult `app_user`

#### Scenario: Institution login resolves to app_user
- **WHEN** a Supabase Auth user with `user_metadata.user_tier = "institution"` submits login credentials
- **THEN** the login flow SHALL look up the user in `app_user`
- **AND** MUST NOT consult `client_user`

#### Scenario: user_tier stamped at user creation
- **WHEN** the PO bootstrap endpoint creates a CD via Supabase Admin API
- **THEN** the new Auth user's `user_metadata.user_tier` SHALL be set to `"client_leadership"` in the same creation call
- **AND** when the CD creates an institution user via `POST /api/v1/users`, the Auth user's `user_metadata.user_tier` SHALL be set to `"institution"`

### Requirement: Strict-fail login for users without user_tier

A Supabase Auth user without a `user_metadata.user_tier` flag SHALL be rejected at login with a clear error: "Account requires reconfiguration — contact administrator." There SHALL be NO self-heal fallback logic. The platform SHALL remedy such users by recreating them through the backend (which stamps the flag) rather than by retroactively touching legacy Auth accounts. Per D14.

#### Scenario: Legacy user rejected
- **WHEN** a Supabase Auth user without `user_metadata.user_tier` submits login credentials
- **THEN** the response SHALL be `403 Account requires reconfiguration`
- **AND** no row SHALL be returned from either `client_user` or `app_user`

#### Scenario: Greenfield wipe before go-live
- **WHEN** the operator runs the documented greenfield wipe step (delete all Supabase Auth users except `admin@school-erp.com`)
- **THEN** after the wipe every subsequent user SHALL be created through the backend which sets `user_tier` at creation
- **AND** strict-fail login will not reject any user created post-wipe

### Requirement: Client-leadership custom HS256 JWT

A CD login SHALL mint a custom HS256 JWT (extending today's Platform Owner JWT pattern) carrying the claims `{sub, user_tier = "client_leadership", client_id, role_id, exp}`. The JWT SHALL NOT contain an `institution_id` claim (the CD manages all institutions under their client). Per D9.

#### Scenario: JWT claims on CD login
- **WHEN** a CD logs in successfully
- **THEN** the response access_token SHALL be a HS256 JWT
- **AND** its payload SHALL contain `sub`, `user_tier = "client_leadership"`, `client_id`, `role_id`, `exp`
- **AND** its payload SHALL NOT contain `institution_id`

#### Scenario: JWT TTL governed by C-08 auth.jwtExpirySeconds
- **WHEN** a CD JWT is minted
- **THEN** its TTL SHALL equal the value of `auth.jwtExpirySeconds` from the C-08 resolver
- **AND** this TTL serves as the natural-expiry safety net for suspended-CD JWT replay (per D12)

### Requirement: Middleware handling of user_tier claim

The middleware SHALL read the `user_tier` claim directly from the HS256 JWT on every authenticated request. For `user_tier = "client_leadership"`, the middleware SHALL set `app.current_client_id` to the JWT's `client_id` and set `institution_id = None`. The middleware SHALL perform NO additional DB lookup on each request.

#### Scenario: Middleware reads claims without DB lookup
- **WHEN** a request arrives with a `client_leadership` JWT
- **THEN** the middleware SHALL set `app.current_client_id` from the JWT's `client_id`
- **AND** SHALL NOT query `client_user` to resolve the tenant context

#### Scenario: No app.is_platform_owner for CDs
- **WHEN** a request arrives with a `client_leadership` JWT
- **THEN** the session SHALL NOT have `app.is_platform_owner = 'true'`
- **AND** the CD's access is gated by client_id matching RLS on tenant tables

### Requirement: PO endpoint surface — /api/v1/platform/clients/$ID/users/*

The PO SHALL manage Client Directors through a nested endpoint surface under the platform client namespace: `POST /api/v1/platform/clients/{client_id}/users` (bootstrap), `GET /api/v1/platform/clients/{client_id}/users` (list CDs in that client), `PATCH /api/v1/platform/clients/{client_id}/users/{user_id}` (transition / suspend), `DELETE /api/v1/platform/clients/{client_id}/users/{user_id}` (revoke). All four endpoints SHALL require `require_platform_owner` — NOT `require_permission`. All four SHALL require NO `Host` header. Per D4.

#### Scenario: Bootstrap endpoint requires PO
- **WHEN** a non-PO token calls `POST /api/v1/platform/clients/$ID/users`
- **THEN** the response SHALL be `403 Forbidden`

#### Scenario: Bootstrap requires no Host header
- **WHEN** the PO calls `POST /api/v1/platform/clients/$ID/users` with no `Host` header
- **THEN** the request SHALL succeed (PO is client-independent in their own session)

#### Scenario: List CDs in a client
- **WHEN** the PO calls `GET /api/v1/platform/clients/$ID/users`
- **THEN** the response SHALL return every `client_user` row whose `client_id = $ID`
- **AND** across all lifecycle states (invited, active, suspended, archived)

#### Scenario: Suspend a CD
- **WHEN** the PO calls `PATCH /api/v1/platform/clients/$ID/users/$UID` with `{new_state: "suspended", reason: "..."}`
- **THEN** the CD's `lifecycle_status` SHALL transition `active → suspended`
- **AND** a `client_user_lifecycle_event` row SHALL be recorded with actor = PO

#### Scenario: Revoke a CD
- **WHEN** the PO calls `DELETE /api/v1/platform/clients/$ID/users/$UID`
- **THEN** the CD SHALL be revoked (archived state) and the corresponding Supabase Auth user SHALL be blocked or deleted in the SAME operation (per the user_tier integrity rule)

### Requirement: Bootstrap creates an invited CD with no password

The bootstrap endpoint SHALL create the CD's Supabase Auth user in the `invited` state with NO password set. The endpoint SHALL NOT accept a `password` field in its request. The CD completes activation by accepting the invite (next requirement). Per D6.

#### Scenario: No password in request
- **WHEN** the PO calls bootstrap with a request body containing a `password` field
- **THEN** the request SHALL be rejected with `400 unexpected field password`

#### Scenario: Auth user created with no password
- **WHEN** the PO calls bootstrap with `{email, name, role}` and the user is created successfully
- **THEN** the resulting Supabase Auth user SHALL have no password set
- **AND** the user SHALL be in an `invited` state until they accept the invite link

### Requirement: Bootstrap returns out-of-band invite URL

The bootstrap endpoint SHALL mint an invite JWT reusing the existing `kernel/auth/services/invite_token.py` machinery and construct the invite URL. The endpoint SHALL return the invite URL in the POST response payload. The PO SHALL forward the URL to the invitee out-of-band (Slack, WhatsApp, phone); the platform SHALL NOT send the URL via SMTP in Phase 1. Per D7.

#### Scenario: Invite URL in bootstrap response
- **WHEN** the PO bootstrap endpoint creates a CD successfully
- **THEN** the response payload SHALL contain an `invite_url` field
- **AND** the URL SHALL embed a single-use invite JWT signed with the C-03 invite secret

#### Scenario: Single-use short-lived invite
- **WHEN** the invite URL is consumed once successfully (CD sets password, lifecycle → active)
- **THEN** the invite JWT SHALL NOT be re-consumable
- **AND** the invite JWT SHALL have an expiry governed by the C-08 `auth.inviteExpiryDays` key

### Requirement: CD completes invite to activate

The CD accepting the invite SHALL be the only lifecycle transition a CD drives for themselves. The flow SHALL: verify the invite JWT (via existing `verify_invite_token`), set the CD's Supabase Auth password, mark `email_confirm = true`, transition `client_user.lifecycle_status` from `invited` to `active`, and record a `client_user_lifecycle_event` row (actor = the CD themselves). Per D6.

#### Scenario: CD accepts invite
- **WHEN** the CD submits the invite JWT and a chosen password to the activate endpoint
- **THEN** the backend SHALL verify the invite JWT
- **AND** set the Supabase Auth password
- **AND** transition `client_user.lifecycle_status = "active"`
- **AND** record a `client_user_lifecycle_event` row with actor = the CD and reason = "completed invite"

#### Scenario: Already-active CD rejected
- **WHEN** an invite token is presented for a `client_user` row whose `lifecycle_status` is already `active`
- **THEN** the request SHALL be rejected with `400 User is already active`

### Requirement: CD own-row access only

A CD SHALL be able to SELECT and UPDATE only their own row in `client_user` (e.g., to update display name). A CD SHALL NOT read sibling CDs, list CDs, insert new CDs, or delete any client_user row. RLS on `client_user` SHALL enforce: SELECT/WHERE `id = current_user_id()`, UPDATE/WHERE `id = current_user_id()`. INSERT and DELETE on `client_user` SHALL be denied to CDs at the RLS layer. Sibling-list and INSERT/DELETE/write operations SHALL be PO-only. Per D5.

#### Scenario: CD reads own row
- **WHEN** a CD calls `GET /api/v1/platform/clients/$ID/users/$SELF_ID`
- **THEN** the response SHALL return the CD's own row
- **AND** RLS SHALL filter the row through `id = current_user_id()`

#### Scenario: CD cannot read sibling CD
- **WHEN** a CD calls `GET /api/v1/platform/clients/$ID/users/$SIBLING_ID`
- **THEN** the response SHALL be `404` (RLS filtered the row out)

#### Scenario: CD cannot list CDs
- **WHEN** a CD calls `GET /api/v1/platform/clients/$ID/users` (list endpoint)
- **THEN** the operation SHALL be rejected (PO-only)
- **AND** because the route requires `require_platform_owner`, the CD receives `403 Forbidden`

#### Scenario: CD updates own row
- **WHEN** a CD calls `PATCH /api/v1/platform/clients/$ID/users/$SELF_ID` with `{name: "New Display Name"}`
- **THEN** the update SHALL succeed
- **AND** RLS SHALL filter the UPDATE through `id = current_user_id()`

#### Scenario: CD cannot update sibling
- **WHEN** a CD calls `PATCH .../$SIBLING_ID`
- **THEN** the response SHALL be `404` (the UPDATE finds zero rows matching the RLS WHERE clause)

#### Scenario: CD cannot insert or delete
- **WHEN** a CD attempts any INSERT or DELETE against `client_user`
- **THEN** RLS SHALL reject the operation

### Requirement: client_user RLS — PO CRUD

RLS on `client_user` SHALL allow the PO (when `app.is_platform_owner = 'true'` session variable is set) to SELECT, INSERT, UPDATE, and DELETE any row across all clients. RLS SHALL NOT permit the PO to use `client_user` RLS as a wedge to access `app_user` or any other institution table — those tables' existing RLS stays AS-IS. Per D8.

#### Scenario: PO reads all client_user rows
- **WHEN** the middleware sets `app.is_platform_owner = 'true'` and the query scans `client_user`
- **THEN** all `client_user` rows across all clients SHALL be visible

#### Scenario: PO inserts a client_user row
- **WHEN** the PO calls `POST /api/v1/platform/clients/$ID/users` and the middleware sets `app.is_platform_owner = 'true'`
- **THEN** the INSERT SHALL succeed regardless of session `client_id`

#### Scenario: PO cannot read app_user via client_user
- **WHEN** the PO requests `GET /api/v1/users`
- **THEN** the `app_user` query SHALL return ZERO rows (existing `app_user` RLS unchanged — PO lacks `app.current_client_id`)
- **AND** `client_user` access SHALL NOT bypass `app_user` RLS

### Requirement: PO walled off from institution data

The PO SHALL NOT be able to read or write any row in `app_user`, `institution`, `org_unit`, `role_assignment` (institution-scoped), `homework`, `submission`, `grade`, `fee_type`, `fee_assignment`, `fee_payment`. The middleware SHALL set `app.is_platform_owner = 'true'` for the PO session but SHALL NOT set `app.current_client_id` (PO has no client). Existing RLS policies on those tables SHALL return ZERO rows to the PO. The `require_permission` PO bypass (per D28 of platform-owner-separation) SHALL STAY — defense-in-depth — but RLS SHALL be the actual wall. Per D8.

#### Scenario: PO sees zero app_user rows
- **WHEN** the PO (via middleware with `app.is_platform_owner = 'true'` and no `app.current_client_id`) queries `app_user`
- **THEN** the response SHALL contain ZERO rows

#### Scenario: PO cannot insert app_user
- **WHEN** the PO attempts `POST /api/v1/users`
- **THEN** the `app_user` INSERT SHALL be rejected by RLS because `client_id = NULL` does not match `current_client_id`

#### Scenario: require_permission bypass stays
- **WHEN** the PO calls a `require_permission`-protected endpoint (e.g., `GET /api/v1/users`)
- **THEN** `require_permission` SHALL bypass for the PO (per D28)
- **AND** the result SHALL be ZERO rows due to RLS
- **AND** this layered defense confirms "PO bypass at the gate, RLS at the data"

### Requirement: Casbin policy loader — dual source

The Casbin policy loader SHALL continue to read `role_assignment` as the source for institution roles, AND SHALL additionally read `client_user.role_id` as the source for client-leadership roles. Load order SHALL be deterministic. The loader SHALL be invoked at startup and on demand (for the rare case of a CD role change triggered by the PO). Per D3.

#### Scenario: Loader reads both sources
- **WHEN** the platform starts up
- **THEN** the Casbin enforcer SHALL be populated with mappings from `role_assignment` (institution roles for `app_user` users)
- **AND** with mappings from `client_user.role_id` (client-leadership roles for `client_user` users)

#### Scenario: CD role resolved from JWT on every request
- **WHEN** a CD makes a request with a `client_leadership` JWT carrying `role_id`
- **THEN** the middleware SHALL use the JWT's `role_id` claim directly
- **AND** SHALL NOT consult the Casbin enforcer per request to resolve the CD's role

### Requirement: Audit on every client_user write

Every CREATE, UPDATE, and DELETE on `client_user` SHALL produce a corresponding row in `kernel/audit.py`'s audit infrastructure with actor identity and reason. This is in addition to the `client_user_lifecycle_event` row produced on lifecycle transitions. Per D10.

#### Scenario: Bootstrap produces audit row
- **WHEN** the PO bootstraps a CD via the bootstrap endpoint
- **THEN** an audit row SHALL be recorded capturing the PO as actor and "client_user.bootstrap" as the action

#### Scenario: Suspended CD produces audit row
- **WHEN** the PO suspends a CD via the PATCH endpoint
- **THEN** an audit row SHALL be recorded alongside the `client_user_lifecycle_event` row