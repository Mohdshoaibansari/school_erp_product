# platform-owner-followups Specification

## Purpose
TBD - created by archiving change formalize-platform-owner-followups. Update Purpose after archive.
## Requirements
### Requirement: Middleware role resolution

The system SHALL resolve user roles and tenant context correctly for all request types: regular authenticated users, the platform owner, and clients without an `Host` subdomain header. The middleware MUST support both subdomain-based tenant resolution and a fallback that infers tenant context from `app_user` when no subdomain is provided (Swagger UI, curl without `Host` header, etc.).

#### Scenario: Normal user role lookup
- **WHEN** a request arrives with a valid Supabase JWT for a non-platform-owner user
- **THEN** the middleware SHALL look up the user's roles in the `role_assignment` table joined with `role`
- **AND** set `TenantContext.roles` to the resolved list

#### Scenario: Platform owner is excluded from app_user-based role lookup
- **WHEN** a request arrives with a JWT containing `is_platform_owner: true`
- **THEN** the middleware SHALL NOT query the `role_assignment` table for roles
- **AND** `TenantContext.roles` SHALL remain `[]`

#### Scenario: Subdomain missing — fallback to app_user
- **WHEN** a request arrives without a usable `Host` header (e.g., Swagger UI sends `Host: 127.0.0.1:8000`)
- **THEN** the middleware SHALL look up the user's `client_id` and `institution_id` from `app_user`
- **AND** populate `TenantContext` with those values
- **AND** use the resolved `client_id` to look up roles from `role_assignment`

#### Scenario: Subdomain present — middleware prefers Host header
- **WHEN** a request arrives with both a valid JWT and a `Host` header that resolves to a `client` slug
- **THEN** the middleware SHALL use the subdomain-resolved `client_id` (not `app_user`)
- **AND** still look up roles from `role_assignment` using that `client_id`

### Requirement: Cross-cutting refactors

The system SHALL provide reliable lookup endpoints for institution and org unit types, correctly import the `Submission` model in the homework grade flow, and use direct HTTP for Supabase admin operations (not the Python SDK which has known issues with admin endpoints).

#### Scenario: GET /api/v1/lookups/institution-types
- **WHEN** any authenticated user requests `GET /api/v1/lookups/institution-types`
- **THEN** the system SHALL return a list of `InstitutionType` records with `{id, code}` fields
- **AND** this endpoint is required for the institution creation UI in the journey flows

#### Scenario: GET /api/v1/lookups/org-unit-types
- **WHEN** any authenticated user requests `GET /api/v1/lookups/org-unit-types`
- **THEN** the system SHALL return a list of `OrgUnitType` records with `{id, name}` fields
- **AND** this endpoint is required for the org unit creation UI in the journey flows

#### Scenario: Homework grade_submission uses imported Submission model
- **WHEN** a teacher grades a submission via `POST /api/v1/submissions/{id}/grade`
- **THEN** the system SHALL successfully load the `Submission` model from the imports
- **AND** update the submission's `status` to `"graded"` after the grade is created
- **AND** return the grade to the caller

#### Scenario: Supabase admin create_user uses httpx not Python SDK
- **WHEN** the backend's auth service calls `create_user` on the `SupabaseAuthClientImpl`
- **THEN** the system SHALL use direct `httpx` HTTP calls (not the Supabase Python SDK)
- **AND** send both `apikey` and `Authorization: Bearer <service_role_key>` headers (the Python SDK sends only `apikey` which GoTrue rejects for admin operations)

### Requirement: Client Director lifecycle support

The system SHALL support a **Client Director** user type — a user that manages an entire client (tenant) but is not bound to any specific institution. This requires:
1. A `client_director` role with `institution.create` permission
2. A nullable `app_user.institution_id` column (so the director's `app_user` row has no `institution_id`)

The Client Director creates the client's institutions and bootstraps all child users (admin, teacher, student) within those institutions.

#### Scenario: client_director role has institution.create permission
- **WHEN** a `Client Director` user attempts to create an institution via `POST /api/v1/institutions`
- **THEN** the system SHALL permit the operation
- **AND** the institution is created under the user's `client_id`

#### Scenario: client_director user has institution_id = NULL
- **WHEN** a `Client Director` user is inserted into `app_user`
- **THEN** `institution_id` SHALL be nullable
- **AND** the row can be created with `institution_id = NULL`

#### Scenario: Admin role does NOT have institution.create
- **WHEN** an `Admin` user (institution-scoped) attempts to create an institution
- **THEN** the system SHALL reject with `403 Permission denied`
- **AND** only the `client_director` role has the `institution.create` permission

#### Scenario: Client Director can list users across own client
- **WHEN** a `Client Director` queries `GET /api/v1/users`
- **THEN** the system SHALL return all users under the director's `client_id`
- **AND** the result is tenant-scoped to that single client (no leakage from other clients)


---
<!-- Synced from add-client-user-bootstrap delta spec -->
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