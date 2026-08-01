## ADDED Requirements

### Requirement: PO bootstraps Client Director via invite

The Platform Owner SHALL bootstrap the first Client Director of any client through the `POST /api/v1/platform/clients/$ID/users` endpoint (owned by the `client-user-bootstrap` capability). The PO SHALL provide `{email, name, role}` in the request body; the PO SHALL NOT provide a password. The endpoint SHALL return an `invite_url` that the PO forwards to the invitee out-of-band. This is the ONLY sanctioned way a Client Director's identity is created on the platform.

#### Scenario: PO bootstraps first CD
- **WHEN** the PO has created + activated a new client and calls `POST /api/v1/platform/clients/$ID/users` with `{email, name, role: "client_director"}`
- **THEN** the response SHALL contain an `invite_url` field with a single-use, short-lived invite JWT
- **AND** a `client_user` row SHALL exist with `lifecycle_status = "invited"`, `client_id = $ID`, `role_id` resolved from `"client_director"`

#### Scenario: PO forwards invite out-of-band
- **WHEN** the PO has received the `invite_url` from the bootstrap response
- **THEN** the PO SHALL deliver it to the future CD via Slack/WhatsApp/phone (NOT via SMTP — the platform does not send email in Phase 1)
- **AND** the platform SHALL NOT attempt to email the URL automatically

### Requirement: PO lists Client Directors in any client

The PO SHALL be able to list every Client Director (and future Client Admin / Billing Contact) under any client via `GET /api/v1/platform/clients/$ID/users`. The list SHALL include rows across ALL lifecycle states (`invited`, `active`, `suspended`, `archived`). The operation SHALL require `require_platform_owner`.

#### Scenario: PO lists CDs in a client
- **WHEN** the PO calls `GET /api/v1/platform/clients/$ID/users`
- **THEN** the response SHALL contain every `client_user` row with `client_id = $ID`
- **AND** the response SHALL include each row's `lifecycle_status`

#### Scenario: Non-PO cannot list
- **WHEN** a non-PO token calls `GET /api/v1/platform/clients/$ID/users`
- **THEN** the response SHALL be `403 Forbidden`

### Requirement: PO suspends a Client Director

The PO SHALL be able to suspend a Client Director via `PATCH /api/v1/platform/clients/$ID/users/$UID` with body `{new_state: "suspended", reason: "..."}`. The CD's `lifecycle_status` SHALL transition from `active` to `suspended` and a `client_user_lifecycle_event` row SHALL be recorded with actor = PO. The CD's currently-issued HS256 JWT SHALL remain valid until natural expiry (per D12 — token revocation is a future concern); the CD's NEXT login attempt SHALL be rejected because `lifecycle_status != "active"`.

#### Scenario: PO suspends a CD
- **WHEN** the PO calls `PATCH /api/v1/platform/clients/$ID/users/$UID` with `{new_state: "suspended", reason: "Departure"}`
- **THEN** the CD's `lifecycle_status` SHALL become `"suspended"`
- **AND** a `client_user_lifecycle_event` row SHALL be recorded with actor = PO and reason = "Departure"

#### Scenario: Suspended CD cannot re-login
- **WHEN** a CD whose `lifecycle_status = "suspended"` submits login credentials
- **THEN** the login SHALL be rejected with a 403 / "Account suspended" error
- **AND** the existing HS256 JWT (if unexpired) keeps working until natural expiry (per D12)

### Requirement: PO revokes a Client Director

The PO SHALL be able to revoke a Client Director via `DELETE /api/v1/platform/clients/$ID/users/$UID`. The revocation SHALL archive the `client_user` row (soft state transition) AND SHALL block or delete the corresponding Supabase Auth user in the SAME operation — to prevent `user_tier` drift between Supabase Auth and our tables. The operation SHALL require `require_platform_owner`.

#### Scenario: PO revokes a CD
- **WHEN** the PO calls `DELETE /api/v1/platform/clients/$ID/users/$UID`
- **THEN** the `client_user` row SHALL transition to `archived` state
- **AND** the corresponding Supabase Auth user SHALL be blocked (banned until further notice) or soft-deleted in the same transactional operation
- **AND** a `client_user_lifecycle_event` row SHALL be recorded with actor = PO and reason captured

#### Scenario: Revoked CD cannot re-login
- **WHEN** a revoked CD submits login credentials
- **THEN** Supabase Auth SHALL reject the credential check OR the `lifecycle_status != "active"` check SHALL reject
- **AND** no new HS256 JWT SHALL be minted

#### Scenario: Revocation stays transactional
- **WHEN** the Auth user block step fails
- **THEN** the `client_user` archive SHALL be rolled back
- **AND** the audit log SHALL record the failed-revocation attempt