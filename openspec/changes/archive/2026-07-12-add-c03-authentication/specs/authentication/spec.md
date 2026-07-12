## Purpose

C-03 Authentication provides the centralized authentication gateway for the School ERP platform. It owns the LoginAttempt audit table, the SupabaseAuthClient Protocol (abstraction over Supabase Auth SDK), invite token minting, 9 auth endpoints (login, refresh, logout, activate, OTP request/verify, password reset request/confirm, password change), the bootstrap CLI for the first platform owner, and the middleware extension for unauthenticated auth routes. This spec is the behavioral source of truth derived from PRD `docs/prd/c-03-authentication.md` (AC-1..AC-28) and the grill-me session (34 locked decisions, D1–D34).

C-03 is **entirely Kernel** — authentication is platform infrastructure, not business domain. Every business module depends on C-03 for "who is making this request." C-03 sits between C-02 (user identity) and all modules that need authentication.

**Supabase Auth is the full authentication provider** (D1). Our backend never stores or hashes passwords. All credential verification goes through Supabase's `signInWithPassword`, `verifyOtp`, or `resetPasswordForEmail`. Our backend proxies login/refresh/OTP calls to Supabase and adds domain logic on top: lifecycle gating (only `active` users can log in), cross-tenant protection (login by email must match the subdomain's client), and audit recording (`login_attempt` table). The backend is the only service that talks to Supabase (D8 revised) — the frontend never talks to Supabase directly.

## Requirements

### Requirement: SupabaseAuthClient Protocol

The system SHALL define a `SupabaseAuthClient` Protocol that abstracts all Supabase Auth operations the backend calls. The Protocol defines methods: `create_user(id, email)`, `sign_in_with_password(email, password)`, `sign_in_with_otp(email)`, `verify_otp(email, token, type)`, `reset_password_for_email(email, redirect_to)`, `update_user(uid, **kwargs)`, `sign_out(uid, scope)`, `delete_user(uid)`, `refresh_token(refresh_token)`, `revoke_refresh_token(refresh_token)`.

A production `SupabaseAuthClientImpl` wraps the Supabase SDK using the `service_role` key. An in-memory `FakeSupabaseAuth` implements the Protocol for tests. The Protocol is extensible for future MFA methods (D26) — adding MFA in Phase 2 = adding new methods to the Protocol + new `/auth/mfa/*` routes.

Trace: D21, D23, D24, D26, AC-24, AC-25.

#### Scenario: SupabaseAuthClient Protocol defines all auth operations
- **WHEN** the SupabaseAuthClient Protocol is inspected
- **THEN** it defines methods for: create_user, sign_in_with_password, sign_in_with_otp, verify_otp, reset_password_for_email, update_user, sign_out, delete_user, refresh_token, revoke_refresh_token

#### Scenario: Production impl uses service_role key
- **WHEN** the `SupabaseAuthClientImpl` is instantiated
- **THEN** it uses the `SUPABASE_SERVICE_ROLE_KEY` environment variable to authenticate with Supabase Auth

#### Scenario: Fake impl is used in tests
- **WHEN** tests exercise auth endpoints
- **THEN** they use `FakeSupabaseAuth` — an in-memory implementation of the Protocol — with no Docker or live Supabase dependency

#### Scenario: Protocol is extensible for MFA
- **WHEN** MFA is added in Phase 2
- **THEN** the Protocol is extended with new methods (`enroll_mfa`, `challenge_mfa`, `verify_mfa`) without modifying existing methods or breaking the Protocol contract

### Requirement: Supabase Client Configuration

The system SHALL configure a single Supabase client with the `service_role` key for all auth operations. Environment variables `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are loaded at app startup (D22). Missing keys cause a fatal startup error. The client is constructed once in the app factory and injected via FastAPI dependency.

Trace: D21, D22, AC-18.

#### Scenario: Supabase client configured at startup
- **WHEN** the app starts
- **THEN** the Supabase client is constructed from `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` env vars

#### Scenario: Missing keys cause fatal startup error
- **WHEN** either `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` is missing from the environment
- **THEN** the app fails to start with a clear error message identifying the missing key

#### Scenario: Single client used for all auth operations
- **WHEN** any auth endpoint calls Supabase Auth
- **THEN** it uses the same service-role client instance (not a per-request client)

### Requirement: Login Endpoint — Email + Password

`POST /auth/login` SHALL accept `{ email, password }`. Backend resolves `client_id` from subdomain (D25), calls Supabase `signInWithPassword`. On Supabase success: looks up `app_user` by UUID (`sub`), checks lifecycle is `active` (D18), checks `app_user.client_id == ctx.client_id` (cross-tenant protection), records `login_success` in `login_attempt`, returns `{ access_token, refresh_token, expires_in }`. On failure: records `login_failure` with `user_id` from email lookup (D33). Returns 401 (bad credentials), 403 (lifecycle not active or missing row), 502 (Supabase unavailable), 429 (rate-limited).

The frontend stores both tokens (D8b). The access token is used for API calls. The refresh token is used to get new access tokens when they expire.

Trace: D8, D8b, D18, D19, D25, D33, AC-2, AC-4, AC-5, AC-6, AC-7, AC-8.

#### Scenario: Successful login returns tokens
- **WHEN** a user with `lifecycle_status='active'` submits correct email + password at the correct subdomain
- **THEN** the endpoint returns HTTP 200 with `{ access_token, refresh_token, expires_in }` and records a `login_success` in `login_attempt`

#### Scenario: Bad credentials return 401
- **WHEN** a user submits incorrect password
- **THEN** the endpoint returns HTTP 401 with `{ detail: "Invalid email or password" }` (never reveals whether the email exists) and records a `login_failure`

#### Scenario: Lifecycle not active returns 403
- **WHEN** Supabase auth succeeds but `app_user.lifecycle_status` is not `active` (e.g., suspended, invited, archived)
- **THEN** the endpoint returns HTTP 403 with `{ detail: "Account is not active. Contact administrator." }` (includes the specific state) and records a `login_failure`

#### Scenario: Cross-tenant login rejected
- **WHEN** Supabase auth succeeds but `app_user.client_id != ctx.client_id` (resolved from subdomain)
- **THEN** the endpoint returns HTTP 403 and records a `login_failure` with `client_id` from subdomain

#### Scenario: Missing app_user row returns 403
- **WHEN** Supabase auth succeeds but no `app_user` row exists for that UUID (data inconsistency)
- **THEN** the endpoint returns HTTP 403 with `{ detail: "User record missing. Contact administrator." }`

#### Scenario: Supabase unavailable returns 502
- **WHEN** the Supabase Auth API is unreachable (network error, timeout)
- **THEN** the endpoint returns HTTP 502 with `{ detail: "Authentication service unavailable" }`

#### Scenario: Supabase rate-limited returns 429
- **WHEN** Supabase returns 429 (too many attempts)
- **THEN** the endpoint returns HTTP 429 with `{ detail: "Too many attempts. Try again later." }`

#### Scenario: Failed login records user_id from email lookup
- **WHEN** a login fails (bad credentials, lifecycle check, cross-tenant)
- **THEN** the endpoint looks up `app_user` by email; if found, records `user_id` and `client_id` in the `login_attempt` row; if not found, records `user_id=NULL` and `client_id` from subdomain

#### Scenario: IP address from X-Forwarded-For
- **WHEN** a login attempt is recorded
- **THEN** the `ip_address` field is populated from the `X-Forwarded-For` header (or the request's direct IP if no proxy header)

### Requirement: Refresh Endpoint

`POST /auth/refresh` SHALL accept `{ refresh_token }`. Backend proxies to Supabase `token?grant_type=refresh_token`. Supabase returns a new access + refresh pair (rotation). Backend returns the new pair. Records `token_refresh` in `login_attempt`.

Trace: D8b, D28a, AC-9.

#### Scenario: Successful refresh returns new tokens
- **WHEN** a valid refresh token is provided
- **THEN** the endpoint returns HTTP 200 with `{ access_token, refresh_token, expires_in }` (new pair) and records a `token_refresh`

#### Scenario: Invalid/revoked refresh token returns 401
- **WHEN** an invalid or revoked refresh token is provided
- **THEN** the endpoint returns HTTP 401

### Requirement: Logout Endpoint

`POST /auth/logout` SHALL accept `{ refresh_token }`. Backend calls Supabase to revoke the refresh token. Records `logout` in `login_attempt`. The current access token remains valid until expiry (≤1h). No JWT blocklist. After expiry, frontend cannot refresh — user is effectively logged out.

Trace: D17, D28a, AC-10.

#### Scenario: Logout revokes refresh token
- **WHEN** a user calls logout with a valid refresh token
- **THEN** the refresh token is revoked at Supabase, a `logout` event is recorded in `login_attempt`, and the endpoint returns HTTP 200

#### Scenario: Access token remains valid after logout
- **WHEN** a user logs out
- **THEN** the current access token remains valid until it expires (≤1h); the user cannot get new access tokens because the refresh token is revoked

### Requirement: Activate Endpoint — Accept Invitation

`POST /auth/activate` SHALL accept `{ invite_token, password }`. Backend verifies the invite JWT signature (HS256 with `APP_INVITE_JWT_SECRET`), checks `iss=school-erp/invite` and `exp`, extracts `user_id` and `email`. Rejects if user already `active` (return 400 "Account already activated"). Calls Supabase `updateUser(uid, { password, email_confirm: true })`. Transitions `app_user` from `invited` to `active` (single step, D29). Rejects expired tokens, tokens with wrong `iss`, and tokens with invalid signatures (400).

Trace: D4, D5, D6, D29, AC-11, AC-12.

#### Scenario: Valid invite token sets password and activates
- **WHEN** a user submits a valid invite token + new password
- **THEN** the endpoint verifies the JWT, calls Supabase `updateUser({ password, email_confirm: true })`, transitions `app_user` from `invited` to `active`, and returns HTTP 200

#### Scenario: Expired invite token rejected
- **WHEN** an expired invite token is submitted
- **THEN** the endpoint returns HTTP 400 with a descriptive message

#### Scenario: Wrong issuer rejected
- **WHEN** an invite token with `iss != "school-erp/invite"` is submitted
- **THEN** the endpoint returns HTTP 400

#### Scenario: Invalid signature rejected
- **WHEN** an invite token with an invalid signature is submitted (tampered or wrong secret)
- **THEN** the endpoint returns HTTP 400

#### Scenario: Already-active user rejected
- **WHEN** a user whose `app_user.lifecycle_status == 'active'` submits an invite token
- **THEN** the endpoint returns HTTP 400 with `{ detail: "Account already activated" }`

### Requirement: OTP Request Endpoint

`POST /auth/otp/request` SHALL accept `{ email }`. Backend proxies to Supabase `signInWithOtp({ email, shouldCreateUser: false })`. Supabase generates a 6-digit OTP and emails it. Our backend returns HTTP 200 (no OTP code is returned to the caller).

Trace: D13, AC-13.

#### Scenario: OTP sent via Supabase
- **WHEN** a user requests an OTP with their email
- **THEN** Supabase generates a 6-digit code and emails it; the endpoint returns HTTP 200

### Requirement: OTP Verify Endpoint

`POST /auth/otp/verify` SHALL accept `{ email, token }`. Backend proxies to Supabase `verifyOtp({ email, token, type: 'email' })`. On success: performs the same lifecycle + client checks as login (D18, D25 — only `active` users, cross-tenant protection). Returns tokens. Records `login_success` or `login_failure`.

Trace: D13, D18, D19, AC-14.

#### Scenario: Valid OTP returns tokens
- **WHEN** a user submits a valid OTP for an `active` user at the correct subdomain
- **THEN** the endpoint returns HTTP 200 with `{ access_token, refresh_token, expires_in }` and records `login_success`

#### Scenario: Invalid OTP returns 401
- **WHEN** a user submits an invalid or expired OTP
- **THEN** the endpoint returns HTTP 401 and records `login_failure`

#### Scenario: Lifecycle check applies to OTP login
- **WHEN** OTP verification succeeds but `app_user.lifecycle_status` is not `active`
- **THEN** the endpoint returns HTTP 403 and records `login_failure`

### Requirement: Password Reset Request Endpoint

`POST /auth/password/reset/request` SHALL accept `{ email }`. Backend proxies to Supabase `resetPasswordForEmail(email, redirectTo=<frontend reset URL>)`. Supabase sends a recovery email. Returns HTTP 200.

Trace: D15, AC-15.

#### Scenario: Reset email sent
- **WHEN** a user requests a password reset with their email
- **THEN** Supabase sends a recovery email with a link to the frontend reset-password page; the endpoint returns HTTP 200

### Requirement: Password Reset Confirm Endpoint

`POST /auth/password/reset/confirm` SHALL accept `{ token, new_password }`. Backend calls Supabase `verifyOtp({ token, type: 'recovery' })` to validate the recovery token, then calls `updateUser({ password })` to set the new password. Returns HTTP 200 on success.

Trace: D15, AC-16.

#### Scenario: Valid recovery token sets new password
- **WHEN** a user submits a valid recovery token + new password
- **THEN** the endpoint verifies the token via Supabase, updates the password, and returns HTTP 200

#### Scenario: Invalid/expired recovery token rejected
- **WHEN** a user submits an invalid or expired recovery token
- **THEN** the endpoint returns HTTP 400

### Requirement: Password Change Endpoint — Authenticated

`POST /auth/password/change` SHALL accept `{ current_password, new_password }`. Backend calls Supabase `signInWithPassword` to verify the current password (D16b). On success, calls Supabase `updateUser({ password })` to set the new password. On Supabase re-login failure, returns HTTP 401 ("current password incorrect"). Records a `login_success` from the re-login.

Trace: D16, D16b, AC-17.

#### Scenario: Correct current password allows change
- **WHEN** an authenticated user submits the correct current password + new password
- **THEN** the endpoint verifies via Supabase, updates the password, and returns HTTP 200

#### Scenario: Incorrect current password rejected
- **WHEN** an authenticated user submits an incorrect current password
- **THEN** the endpoint returns HTTP 401 with `{ detail: "Current password incorrect" }`

### Requirement: LoginAttempt Table + RLS

The system SHALL provide a `login_attempt` table with: `id` (UUID v4 PK), `client_id` (FK → client, nullable, RLS), `user_id` (FK → app_user, nullable — populated via email lookup per D33), `email` (TEXT NOT NULL), `event_type` (TEXT NOT NULL — `login_success` | `login_failure` | `logout` | `token_refresh`), `ip_address` (TEXT), `user_agent` (TEXT), `occurred_at` (TIMESTAMPTZ NOT NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

RLS on `client_id`: platform owner sees all; tenant sees their own. Same pattern as C-01/C-02 tenant-scoped tables.

Trace: D11, D28a, D33, AC-5, AC-21, AC-22.

#### Scenario: login_attempt records login_success
- **WHEN** a successful login occurs
- **THEN** a `login_attempt` row is written with `event_type='login_success'`, `client_id` from subdomain, `user_id` from `app_user`, `email`, `ip_address` from `X-Forwarded-For`, `user_agent`, `occurred_at=now()`

#### Scenario: login_attempt records login_failure with user_id from email lookup
- **WHEN** a failed login occurs
- **THEN** a `login_attempt` row is written with `event_type='login_failure'`, `user_id` populated by looking up `app_user` by email (if found) or NULL (if not found), `client_id` from subdomain

#### Scenario: login_attempt records logout and token_refresh
- **WHEN** a logout or token refresh occurs
- **THEN** a `login_attempt` row is written with the appropriate `event_type`

#### Scenario: RLS on client_id
- **WHEN** a tenant queries `login_attempt`
- **THEN** only rows with matching `client_id` are visible; platform owner sees all rows

#### Scenario: Controlled vocabulary
- **WHEN** a `login_attempt` row is written
- **THEN** `event_type` is one of: `login_success`, `login_failure`, `logout`, `token_refresh`. Administrative lifecycle events (user creation, suspend, archive) are NOT recorded here — they go via C-11 AuditEmitter

### Requirement: Synchronous Audit Recording

All login attempts SHALL be recorded synchronously in the request path. No polling, no background worker, no `auth.audit_log_entries` access. `login_attempt` is the authoritative audit table for auth events.

Trace: D9b, AC-26.

#### Scenario: Audit recorded in request path
- **WHEN** any auth endpoint processes a login/refresh/logout
- **THEN** the `login_attempt` row is written before the response is returned (synchronous)

#### Scenario: No background worker or polling
- **WHEN** the auth system is inspected
- **THEN** no background worker, cron job, or Supabase `auth.audit_log_entries` polling exists for `login_attempt` recording

### Requirement: Invite Token Minting

The system SHALL mint stateless signed JWT invite tokens for user onboarding. The token is signed with HS256 using a separate secret (`APP_INVITE_JWT_SECRET`), carries claims: `sub` (user_id), `email`, `exp` (7 days), `iss` ("school-erp/invite"). No DB table. Cryptographically isolated from Supabase JWTs (different secret, different issuer).

Trace: D4, D5, D6, AC-11.

#### Scenario: Invite token minted with correct claims
- **WHEN** an admin creates a user (D3)
- **THEN** the backend mints a JWT with `sub=user_id`, `email`, `exp=7d`, `iss="school-erp/invite"`, signed with `APP_INVITE_JWT_SECRET`

#### Scenario: Invite token cryptographically isolated from Supabase JWTs
- **WHEN** an invite token is presented to the middleware
- **THEN** the middleware recognizes it via `iss="school-erp/invite"` and routes it to the auth activate handler; Supabase's middleware would reject it (wrong secret)

### Requirement: Middleware Extension for Unauthenticated Routes

The middleware SHALL tolerate an absent JWT for `/auth/*` routes that run before a JWT exists. When no `Authorization` header is present (or the JWT has `iss="school-erp/invite"`), the middleware sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`. Auth routes that need `client_id` read it from context.

Trace: D25, AC-3.

#### Scenario: No JWT → subdomain-only TenantContext
- **WHEN** a request arrives at `/auth/login` (or any unauthenticated auth route) with no `Authorization` header
- **THEN** the middleware resolves `client_id` from the subdomain and sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`

#### Scenario: Invite JWT → subdomain context + invite claims
- **WHEN** a request arrives at `/auth/activate` with an invite JWT (`iss="school-erp/invite"`)
- **THEN** the middleware recognizes the invite issuer, sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`, and the route handler reads the invite claims from the JWT directly

#### Scenario: Supabase JWT → normal authenticated path
- **WHEN** a request arrives at `/auth/refresh`, `/auth/logout`, or `/auth/password/change` with a valid Supabase JWT
- **THEN** the middleware decodes the JWT, looks up `app_user` by `sub`, and sets full `TenantContext(client_id, institution_id, user_id, roles)` (normal path)

### Requirement: Bootstrap CLI

The system SHALL provide a CLI command `python -m kernel.auth.bootstrap` that creates the first platform owner in Supabase Auth. The migration inserts the `app_user` row (no Supabase call). The CLI calls Supabase Admin API `createUser({ id=X, email, password, email_confirm: true })` using `PLATFORM_OWNER_INITIAL_PASSWORD` env var. The CLI is idempotent (checks if user exists first).

Trace: D30, AC-23.

#### Scenario: Bootstrap creates platform owner in Supabase
- **WHEN** the operator runs `uv run python -m kernel.auth.bootstrap` after `alembic upgrade`
- **THEN** the CLI creates the matching Supabase Auth user for the platform owner `app_user` row, with `email_confirm: true`

#### Scenario: Bootstrap is idempotent
- **WHEN** the CLI is run when the Supabase user already exists
- **THEN** the CLI skips creation and exits cleanly

#### Scenario: Missing PLATFORM_OWNER_INITIAL_PASSWORD is fatal
- **WHEN** the CLI is run without `PLATFORM_OWNER_INITIAL_PASSWORD` in the environment
- **THEN** the CLI exits with a clear error message

### Requirement: IP Forwarding

The backend SHALL read `X-Forwarded-For` headers to get the real client IP. The IP is stored in `login_attempt.ip_address` and forwarded to Supabase so its rate limits work correctly.

Trace: D31, AC-28.

#### Scenario: IP from X-Forwarded-For
- **WHEN** a request arrives through a proxy with `X-Forwarded-For: 1.2.3.4`
- **THEN** the `login_attempt.ip_address` is set to `1.2.3.4`

#### Scenario: Direct IP when no proxy header
- **WHEN** a request arrives without `X-Forwarded-For`
- **THEN** the `login_attempt.ip_address` is set to the request's direct IP address

### Requirement: Frontend Token Contract

The C-03 spec SHALL document the binding contract the frontend must follow: frontend stores access + refresh tokens (D8b), attaches `Authorization: Bearer <access_token>` to every API call, calls `/auth/refresh` on 401, clears tokens on logout. No frontend JS code is implemented in C-03 (D32).

Trace: D32, AC-27.

#### Scenario: Contract documented
- **WHEN** the C-03 spec is read by a frontend implementer
- **THEN** the token storage, header attachment, refresh-on-401, and clear-on-logout behaviors are clearly specified

### Requirement: Module Manifest Registration

C-03 SHALL register via the ModuleManifest Protocol (A5). Routes registered via `register_routes`. CLI registered via `register_cli`. No Casbin policies (C-04 will define them later).

Trace: AC-23.

#### Scenario: C-03 manifest registers routes and CLI
- **WHEN** the app starts
- **THEN** C-03's manifest `register_routes` mounts `/auth/*` routes, and `register_cli` registers the bootstrap command

### Requirement: Capability Boundary Declarations

C-03 SHALL record all cross-capability boundary relationships as part of its own spec, and SHALL NOT issue MODIFIED/REMOVED deltas against C-01's domain. The middleware extension (D25) is a code-level change to kernel infrastructure, not a behavioral change to C-01's spec.

| C-03 relationship | Direction | Other capability | Nature |
|---|---|---|---|
| C-03 reads `app_user` for lifecycle checks, email lookup | C-03 → C-02 | C-02 (Identity & User) | Data dependency |
| C-03 extends middleware to tolerate absent JWT | C-03 → C-01 | C-01 (Tenant & Institution) | Infrastructure extension |
| C-03 consumes AuditEmitter for lifecycle/credential audit events | C-03 → C-11 | C-11 (Audit) | Boundary / consumer |
| C-03's `login_attempt` has FK to `app_user` | C-03 → C-02 | C-02 (Identity & User) | Schema dependency |
| C-04 will enforce permissions on auth endpoints | C-04 → C-03 | C-04 (Authorization) | Boundary / future consumer |
| C-03 propagates user lifecycle to Supabase Auth | C-03 → C-02 | C-02 (Identity & User) | Behavioral modification (MODIFIED delta in C-02 spec) |

Trace: impact-classification boundary table.

#### Scenario: C-03 does NOT modify C-01's spec
- **WHEN** the C-03 change is inspected for cross-domain modifications
- **THEN** no MODIFIED deltas exist for C-01; the middleware extension is a code-level change, not a spec change

#### Scenario: C-03's MODIFIED delta to C-02 is in a separate spec file
- **WHEN** the C-03 change folder is inspected
- **THEN** a separate `specs/identity-user-management/spec.md` contains the MODIFIED deltas for C-02
