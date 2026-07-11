# PRD — C-03 Authentication

> **Capability:** C-03 Authentication
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-07-11
> **Decisional source of truth:** Grill-me session (34 locked decisions, 2026-07-11)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-03; `docs/architecture/adr-platform-software-architecture.md` (A2, A5, A6); `docs/architecture/adr-platform-tech-stack.md` (AuthN row); `docs/prd/c-02-identity-user-management.md` (D1–D11 — user model C-03 depends on)
> **Scope note:** This is a **product** requirements document. Implementation detail (DTO shapes, Supabase API call signatures, middleware hook points) belongs in the spec/design phase. Decisions are referenced by their grill-me number (e.g., "per D1") rather than re-specified here.

---

## 1. Problem

Every business module in the School ERP — Attendance, Fees, Homework, Exams, Timetable — requires an authenticated user. Without a centralized authentication capability, each module would need to manage login, session, and credential flows independently, leading to fragmented security, duplicated logic, and no single point of audit for "who logged in and when."

C-03 provides the **single authentication gateway** for the entire platform. It answers: how does a user prove their identity, how is that proof represented (JWT), how long does a session last, and how does an admin invite and provision new users. C-03 sits between C-02 (which stores user identity) and all modules that need to know "who is making this request." Every authenticated API call flows through C-03's JWT validation.

The key architectural decision that shaped this PRD: **Supabase Auth is the full authentication provider** (D1). Our backend never touches passwords — Supabase handles hashing (bcrypt), session management, and token issuance. Our backend proxies login/refresh/OTP calls to Supabase and adds domain logic on top: lifecycle gating (only `active` users can log in), cross-tenant protection (login by email must match the subdomain's client), and audit recording (`login_attempt` table). The backend is the only service that talks to Supabase (D8 revised) — the frontend never talks to Supabase directly.

---

## 2. Goals & Non-goals

### 2.1 In scope — C-03 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **LoginAttempt** (audit record of every login attempt) | D11, D28a, D33 | Minimal audit-only table: `id`, `client_id`, `user_id` (nullable — populated via email lookup even on failures per D33), `email`, `event_type` (`login_success` | `login_failure` | `logout` | `token_refresh`), `ip_address`, `user_agent`, `occurred_at`, `created_at`. RLS on `client_id`. |
| **SupabaseAuthClient Protocol** (abstraction over Supabase Auth SDK) | D21, D23 | A Python Protocol defining all Supabase Auth operations our backend calls. Single `service_role` client implementation for production; in-memory `FakeSupabaseAuth` for tests (D24). |
| **Invite token** (stateless JWT for user onboarding) | D4, D5, D6 | Backend mints a signed JWT (`user_id`, `email`, `exp=7d`, `iss=school-erp/invite`) using a separate HS256 secret (`APP_INVITE_JWT_SECRET`). No DB table. Cryptographically isolated from Supabase JWTs. |
| **Auth endpoints** (9 Phase 1 routes) | D14 | See §2.1.1 below for the full endpoint list. |
| **Admin ↔ Supabase user lifecycle synchronization** | D3, D20a, D20b | When an admin creates a user (C-02), our service also creates the matching Supabase Auth user. When an admin suspends/archives/changes email, our service propagates to Supabase. Rollback on Supabase creation failure (D20a). |
| **Bootstrap** (first platform owner) | D30 | Migration inserts `app_user` row; CLI command `python -m kernel.auth.bootstrap` creates the matching Supabase Auth user with `email_confirm: true`. |
| **Middleware extension for unauthenticated auth routes** | D25 | Middleware tolerates absent JWT; resolves `client_id` from subdomain only for `/auth/*` routes that run before a JWT exists. |

#### 2.1.1 Phase 1 endpoints

| # | Endpoint | Purpose | Key decisions |
|---|---|---|---|
| 1 | `POST /auth/login` | Email + password → access + refresh tokens | D8, D8b, D18, D19, D9b, D33 |
| 2 | `POST /auth/refresh` | Refresh access token using refresh token | D8b, D28a |
| 3 | `POST /auth/logout` | Revoke refresh token at Supabase | D17, D28a |
| 4 | `POST /auth/activate` | Verify invite JWT, set password, transition `invited → active` | D4, D5, D6, D29 |
| 5 | `POST /auth/otp/request` | Request email OTP via Supabase | D13 |
| 6 | `POST /auth/otp/verify` | Verify OTP, return tokens | D13 |
| 7 | `POST /auth/password/reset/request` | "Forgot password" — send reset email via Supabase | D15 |
| 8 | `POST /auth/password/reset/confirm` | Set new password with Supabase recovery token | D15 |
| 9 | `POST /auth/password/change` | Authenticated user changes own password (requires `current_password`) | D16, D16b |

### 2.2 Out of scope — owned by other capabilities

| Concern | Owned by | Notes |
|---|---|---|
| User identity and domain fields (name, category, roles, profile) | C-02 | C-03 authenticates the user; C-02 stores who they are. |
| Authorization framework (Casbin, RBAC, ABAC, permission matrix) | C-04 | C-03 verifies identity; C-04 enforces what the identity can do. |
| Audit framework (append-only event store, AuditEmitter) | C-11 | C-03 records `login_attempt` rows (auth audit); lifecycle/credential audit events (user creation, suspend, archive, password change) go via C-11's AuditEmitter Protocol. |
| Notification delivery (email sending) | C-09 | Supabase Auth sends its own emails (invite, OTP, password reset) via its built-in email provider. C-09 is not used for auth emails in Phase 1. |
| Frontend auth client (token storage, Axios interceptor, route guards) | Frontend architecture phase | C-03 defines the **binding contract** the frontend must follow (D32); the frontend implementation is a separate concern. |
| Multi-factor authentication (MFA) | Phase 2 | Architecture is MFA-ready via Protocol extensibility (D26). No MFA code, tables, or stubs in Phase 1. |
| SSO (Google, Microsoft, SAML, LDAP) | Phase 2 | `AuthenticationMethod` and `IdentityProvider` tables deferred to Phase 2 (D27). |
| SMS OTP | Phase 2 | Requires SMS integration (not in Supabase's built-in OTP). |

### 2.3 Explicit non-goals for Phase 1

- **No `/auth/login` endpoint for direct Supabase SDK use** — the frontend never talks to Supabase directly (D8 revised). All auth goes through our backend.
- **No session table** — Supabase is the sole session store (D12b). Our backend is fully stateless for sessions. Admin force-logout = call Supabase Admin API `signOut(userId)`.
- **No JWT blocklist** — on logout, only the refresh token is revoked (D17). The access token remains valid until it expires (≤1h). This is the standard JWT trade-off.
- **No app-layer rate limiting** — Supabase owns brute-force protection (D31). Our backend reads `X-Forwarded-For` to forward the real client IP so Supabase's limits work correctly.
- **No MFA code or tables** — architecture is extensible via Protocol (D26), but zero MFA implementation in Phase 1.
- **No SSO** — Google/Microsoft/SAML/LDAP deferred to Phase 2 (D27). `AuthenticationMethod` and `IdentityProvider` tables not created.
- **No `/auth/me` endpoint** — frontend uses existing C-02 user endpoints (D14).
- **No `/auth/resend-invite`** — admin can re-create the user or we add later (D14).
- **No smoke tests against live Supabase** — all tests use the `FakeSupabaseAuth` mock (D23b).
- **No pending lifecycle transitions** — `Pending` state is kept in the C-02 state machine but no flow transitions into it (D29b). `/auth/activate` transitions `Invited → Active` directly (D29).

---

## 3. Users / Personas

| Persona | Who they are | Scope | C-03 reach |
|---|---|---|---|
| **Platform Owner** | The SaaS provider operating the platform. | All tenants. | Bootstrap the first platform owner via CLI (D30). View all login attempts across all clients. Force-logout any user via Supabase Admin API. |
| **Client Director** | The client's top administrator (trust director, chain owner). | Own client only. | Create users (triggers Supabase Auth user creation). Suspend/archive users (propagated to Supabase). View login attempts for their client. |
| **Institution Admin / Principal** | The institution's top in-building administrator. | Own institution only. | Create users at their institution (triggers Supabase Auth user creation). Suspend/archive users. View login attempts for their institution. |
| **Teacher / Staff** | A regular user of the system. | Own account only. | Log in via email+password or OTP. Accept invitations (set password via invite link). Change own password. Request password reset. View own login history (future). |
| **Student / Parent** | Learners and their guardians. | Own account only. | Same as Teacher/Staff. OTP login is especially important for parents who may not remember passwords. |

---

## 4. User Journeys

| # | Persona | Journey | Key decisions |
|---|---|---|---|
| **J1** | Institution Admin | **Invite a new teacher.** Admin creates a User record (C-02). C-03's service creates a matching Supabase Auth user (`createUser({ id=X, email, email_confirm: false })`). C-03 mints a stateless invite JWT and emails a link. Teacher clicks the link, arrives at `/auth/activate`, sets a password. Backend calls Supabase `updateUser({ password, email_confirm: true })` and transitions `app_user` from `invited` to `active`. Teacher can now log in. | D3, D4, D5, D6, D20a, D29 |
| **J2** | Teacher | **Log in with email and password.** Teacher enters email + password on the login page. Frontend calls `POST /auth/login`. Backend resolves `client_id` from subdomain, calls Supabase `signInWithPassword`. If Supabase returns a JWT, backend looks up `app_user` by `sub` (UUID), checks lifecycle is `active` (D18), checks `app_user.client_id == ctx.client_id` (cross-tenant protection), records `login_success`, returns access + refresh tokens. | D8, D8b, D18, D19, D25, D33 |
| **J3** | Parent | **Log in with OTP.** Parent enters their email on the login page. Frontend calls `POST /auth/otp/request`. Backend calls Supabase `signInWithOtp` — Supabase generates a 6-digit code and emails it. Parent enters the code. Frontend calls `POST /auth/otp/verify`. Backend calls Supabase `verifyOtp` — on success, same lifecycle + client checks as J2. Returns tokens. | D13, D18, D19 |
| **J4** | Teacher | **Forgot password.** Teacher clicks "Forgot password" on the login page. Frontend calls `POST /auth/password/reset/request` with `{ email }`. Backend calls Supabase `resetPasswordForEmail(email, redirectTo=<frontend reset URL>)`. Supabase sends a recovery email. Teacher clicks the link, arrives at the frontend reset page, enters a new password. Frontend calls `POST /auth/password/reset/confirm` with `{ token, new_password }`. Backend calls Supabase `verifyOtp(recovery)` + `updateUser({ password })`. | D15 |
| **J5** | Teacher | **Change password while logged in.** Teacher navigates to settings, enters current password + new password. Frontend calls `POST /auth/password/change`. Backend calls Supabase `signInWithPassword` with the current password to verify (D16b), then calls Supabase `updateUser({ password })` with the new password. Records a `login_success` event from the re-login. | D16, D16b |
| **J6** | Teacher | **Log out.** Teacher clicks "Log out." Frontend calls `POST /auth/logout` with `{ refresh_token }`. Backend calls Supabase to revoke the refresh token. Records `logout` in `login_attempt`. The access token remains valid until it expires (≤1h). After expiry, frontend cannot refresh — teacher is effectively logged out. | D17, D28a |
| **J7** | Client Director | **Suspend a user (auth propagation).** Director suspends a user via C-02's lifecycle transition. C-03's propagation hook calls Supabase `signOut(uid, 'global')` to revoke all refresh tokens. The suspended user's existing access token expires within the hour. D18 blocks re-login (lifecycle not `active`). | D18, D20b |
| **J8** | Client Director | **Archive a user (auth propagation).** Director archives a user (terminal). C-03's propagation hook calls Supabase `signOut(uid, 'global')` + `deleteUser(uid)` to remove the Supabase Auth identity entirely. The `app_user` row is retained for FK integrity. | D20b |
| **J9** | Platform Owner | **Bootstrap the first platform owner.** After running `alembic upgrade` (which inserts the platform owner `app_user` row), the operator runs `uv run python -m kernel.auth.bootstrap`. The CLI calls Supabase Admin API `createUser({ id=X, email, password, email_confirm: true })`. The platform owner can now log in. | D30 |
| **J10** | Teacher | **Refresh access token.** Frontend detects the access token is expired. Frontend calls `POST /auth/refresh` with `{ refresh_token }`. Backend calls Supabase `token?grant_type=refresh_token` with the refresh token. Supabase returns a new access + refresh pair (rotation). Backend returns the new pair. Frontend stores the new tokens. Records `token_refresh` in `login_attempt`. | D8b, D28a |
| **J11** | Institution Admin | **Failed login attempt — cross-tenant protection.** An attacker knows a teacher's email but the teacher's `app_user` record belongs to a different client. Attacker logs in at `attacker-school.localhost` with the teacher's email. Supabase returns a JWT (correct password), but backend sees `app_user.client_id != ctx.client_id` → rejects with 403. Records `login_failure` with `client_id` from subdomain. | D18, D19, D33 |

---

## 5. Acceptance Criteria

All criteria are testable and trace to a locked decision.

| # | Criterion | Trace |
|---|---|---|
| **AC-1** | Supabase Auth is the sole authentication provider. Our backend never stores or hashes passwords. All credential verification goes through Supabase's `signInWithPassword`, `verifyOtp`, or `resetPasswordForEmail`. | D1 |
| **AC-2** | Supabase Auth `auth.users` and our `app_user` share the same UUID. When an admin creates a user, our service creates both records with the same UUID. On Supabase creation failure, the `app_user` insert is rolled back (no orphaned rows). | D2, D3, D20a |
| **AC-3** | The middleware resolves `client_id` from the subdomain even when no JWT is present (for unauthenticated auth routes). `TenantContext` is set with `client_id`, `institution_id=None`, `user_id=None`, `roles=[]`. | D25 |
| **AC-4** | `/auth/login` returns HTTP 200 with `{ access_token, refresh_token, expires_in }` on success. The frontend stores both tokens (D8b). | D8b |
| **AC-5** | `/auth/login` records a `login_attempt` row on every call — `login_success` on success, `login_failure` on failure. The row includes `client_id` (from subdomain), `user_id` (from email lookup even on failures per D33), `email`, `event_type`, `ip_address` (from `X-Forwarded-For`), `user_agent`, `occurred_at`. | D9b, D11, D33 |
| **AC-6** | `/auth/login` rejects users whose `app_user.lifecycle_status` is not `active` — even if Supabase auth succeeds. Returns 403 with the specific lifecycle state (suspended/invited/archived). | D18, D19 |
| **AC-7** | `/auth/login` rejects cross-tenant login attempts — if `app_user.client_id != ctx.client_id` (resolved from subdomain), returns 403. Records `login_failure`. | D18, D19, D25 |
| **AC-8** | `/auth/login` returns 401 for bad credentials (never reveals whether the email exists). Returns 502 if Supabase is unavailable. Returns 429 if Supabase rate-limits. | D19 |
| **AC-9** | `/auth/refresh` accepts a refresh token and returns a new access + refresh pair (Supabase refresh rotation). Records `token_refresh` in `login_attempt`. | D8b, D28a |
| **AC-10** | `/auth/logout` revokes the provided refresh token at Supabase. The current access token remains valid until expiry (≤1h). Records `logout` in `login_attempt`. No JWT blocklist. | D17, D28a |
| **AC-11** | `/auth/activate` verifies the invite JWT signature (HS256 with `APP_INVITE_JWT_SECRET`), checks `iss=school-erp/invite` and `exp`, extracts `user_id` and `email`. Calls Supabase `updateUser(uid, { password, email_confirm: true })`. Transitions `app_user` from `invited` to `active`. | D4, D5, D6, D29 |
| **AC-12** | `/auth/activate` rejects expired invite tokens, tokens with wrong `iss`, and tokens with invalid signatures. Returns 400 with descriptive message. | D5, D6 |
| **AC-13** | `/auth/otp/request` proxies to Supabase `signInWithOtp({ email, shouldCreateUser: false })`. Supabase generates the OTP and sends the email. Our backend returns 200 (no OTP code is returned to the caller). | D13 |
| **AC-14** | `/auth/otp/verify` proxies to Supabase `verifyOtp({ email, token, type: 'email' })`. On success, performs the same lifecycle + client checks as `/auth/login` (AC-6, AC-7). Returns tokens. Records `login_success` or `login_failure`. | D13, D18, D19 |
| **AC-15** | `/auth/password/reset/request` proxies to Supabase `resetPasswordForEmail(email, redirectTo=<frontend reset URL>)`. Supabase sends the recovery email. Returns 200. | D15 |
| **AC-16** | `/auth/password/reset/confirm` proxies to Supabase `verifyOtp({ token, type: 'recovery' })` → `updateUser({ password })`. Returns 200 on success. | D15 |
| **AC-17** | `/auth/password/change` requires `current_password` in the request body. Backend calls Supabase `signInWithPassword` to verify the current password (D16b). On success, calls Supabase `updateUser({ password })`. On Supabase re-login failure, returns 401 ("current password incorrect"). | D16, D16b |
| **AC-18** | The Supabase client is configured with the `service_role` key (D21). Environment variables `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are loaded at app startup (D22). Missing keys cause a fatal startup error. | D21, D22 |
| **AC-19** | Admin user creation (C-02's `POST /users`) is extended to also call Supabase Admin API `createUser({ id=X, email, email_confirm: false })`. On Supabase failure, the `app_user` insert is rolled back. | D3, D20a |
| **AC-20** | Admin suspend propagates to Supabase: `signOut(uid, 'global')` revokes all refresh tokens. Admin archive propagates: `signOut(uid, 'global')` + `deleteUser(uid)` removes the Supabase Auth identity. Admin email change propagates: `updateUser(uid, { email, email_confirm: false })`. | D20b |
| **AC-21** | `login_attempt` table has RLS policy on `client_id` (same pattern as C-01/C-02 tenant-scoped tables). Platform owner sees all; tenant sees their own. | D11 |
| **AC-22** | The `login_attempt.event_type` controlled vocabulary is: `login_success`, `login_failure`, `logout`, `token_refresh`. Administrative lifecycle events (user creation, suspend, archive) are audited via C-11 AuditEmitter, not `login_attempt`. | D28a |
| **AC-23** | A bootstrap CLI command `python -m kernel.auth.bootstrap` creates the first platform owner in Supabase Auth (matching the `app_user` row inserted by migration). Idempotent. Uses `PLATFORM_OWNER_INITIAL_PASSWORD` env var. | D30 |
| **AC-24** | The `SupabaseAuthClient` Protocol defines all Supabase Auth operations (D24: `createUser`, `signInWithPassword`, `signInWithOtp`, `verifyOtp`, `resetPasswordForEmail`, `updateUser`, `signOut`, `deleteUser`, `refreshToken`). The Protocol is extensible for future MFA methods (D26). | D21, D23, D24, D26 |
| **AC-25** | Tests use `FakeSupabaseAuth` — an in-memory implementation of the `SupabaseAuthClient` Protocol. Tests exercise all endpoint logic (lifecycle gating, audit recording, failure mapping) without Docker or live Supabase. | D23, D23b, D24 |
| **AC-26** | `login_attempt` is the authoritative audit table for auth events. No polling, no background worker, no `auth.audit_log_entries` access. All recording is synchronous in the request path. | D9b |
| **AC-27** | Frontend token contract is documented in the C-03 spec: frontend stores access + refresh tokens, attaches `Authorization: Bearer <access_token>`, calls `/auth/refresh` on 401, clears tokens on logout. No frontend JS code is implemented in C-03 (D32). | D32 |
| **AC-28** | The backend reads `X-Forwarded-For` headers to get the real client IP. This IP is stored in `login_attempt.ip_address` and forwarded to Supabase so its rate limits work correctly. | D31 |

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| **R1** | **Supabase as a single point of failure for authentication.** If Supabase Auth is down, no user can log in, refresh tokens, or reset passwords. All auth endpoints return 502. | Accepted per D1. Supabase Auth has high availability (99.9%+ SLA on hosted). For self-hosted Supabase, the operator manages uptime. The 502 response (D19) gives the frontend a clear signal to retry or show a maintenance message. |
| **R2** | **Access token window after logout.** On `/auth/logout`, only the refresh token is revoked (D17). The current access token remains valid until it expires (≤1h). A stolen access token could still be used during this window. | Accepted per D17. This is the universal JWT trade-off. Mitigated by: (a) short access token lifetime (1h default), (b) refresh token rotation on every refresh, (c) a stolen access token gives the attacker up to 1h of access but they cannot refresh without the (now-revoked) refresh token. |
| **R3** | **Cross-tenant login detection depends on email lookup.** When a user logs in with an email that belongs to a different client's `app_user`, we detect and reject it (D18, D25). But Supabase auth succeeds first (it doesn't know about our client model). If the `app_user` lookup fails (data inconsistency), we return 403 "User record missing." | Accepted per D2. The shared-UUID model (D2) ensures `auth.users` and `app_user` are in sync. The D20a rollback mechanism prevents orphaned records. The 403 "User record missing" error (D19) triggers operator investigation. |
| **R4** | **Invite token security.** The invite token (D5) is a stateless JWT sent as a URL parameter. If the email is intercepted, the token could be used to set the user's password before they do. | Accepted. The invite token is: (a) sent over TLS (HTTPS in production), (b) valid for 7 days, (c) cryptographically isolated from Supabase JWTs (D6), (d) only allows setting a password — not logging in (the user must also use `/auth/login` afterward). For higher security, the invite flow could be replaced with OTP (D13) in a future enhancement. |
| **R5** | **Supabase `service_role` key exposure.** The `service_role` key bypasses all Supabase RLS. If leaked, an attacker has full access to the Supabase project. | Accepted per D21/D22. The key is loaded from env vars, never logged, never returned in API responses. Same risk as any database credential. Rotation requires an app restart (acceptable for Phase 1). |
| **R6** | **Login attempt email lookup on failures.** On failed logins, we look up `app_user` by email to record the `user_id` (D33). This confirms the email exists in our domain, but only in the `login_attempt` table (not returned to the caller). The generic 401 response (D19) does not leak this information. | Accepted. The lookup is for audit quality only. The 401 response is always generic (D19), so no information is leaked to the attacker. |
| **R7** | **D16b re-login creates a noisy `login_success` audit row.** When a user changes their password (D16b), the Supabase `signInWithPassword` call to verify the current password creates a `login_success` row in `login_attempt`. This is technically a verification, not a login. | Accepted. The extra row is harmless noise. A future enhancement could add a `verification` event type to distinguish it. For Phase 1, `login_success` is acceptable. |
| **R8** | **No MFA or SSO in Phase 1.** Some institutions may require MFA or SSO for compliance (e.g., GDPR, student data protection). Phase 1 only supports email/password and OTP. | Accepted per D26/D27. The Protocol is extensible for MFA (D26). SSO tables are deferred to Phase 2 (D27). The architecture supports adding both without refactoring. |

---

## 7. Open Questions / Notes

| # | Item | Disposition |
|---|---|---|
| **OQ-1** | Supabase email templates and provider configuration. Supabase sends emails for invite, OTP, and password reset using its built-in email provider (console in dev, SMTP in prod). The email templates are Supabase-controlled. Customization requires configuring a custom SMTP provider in Supabase. | **Deferred.** Phase 1 uses Supabase defaults. Custom email templates and SMTP configuration are operational concerns for production deployment. |
| **OQ-2** | Frontend reset-password URL. The `redirectTo` parameter in `/auth/password/reset/request` (D15) must point to the frontend's reset-password page. The URL is environment-specific (dev vs prod). | **Deferred to implementation.** The URL will be read from an env var or derived from the request's `Origin` header. |
| **OQ-3** | Supabase `signInWithPassword` IP forwarding. Supabase's rate limiting tracks by IP. If our backend proxies all requests, Supabase sees our backend's IP. We must forward `X-Forwarded-For` so Supabase tracks the real client IP. | **Addressed in D31.** The backend reads `X-Forwarded-For` and passes it through. Implementation detail for the spec. |
| **OQ-4** | Invite token reuse. A user could use the invite link to set a password, then use the same link again (the JWT is still valid for 7 days). Should `/auth/activate` reject tokens for users already in `active` state? | **Resolved.** Yes — `/auth/activate` should check `app_user.lifecycle_status` and reject if already `active` (return 400 "Account already activated"). This prevents reuse. |
| **OQ-5** | `PLATFORM_OWNER_INITIAL_PASSWORD` env var security. The bootstrap CLI (D30) uses this env var for the first platform owner's password. If set to a weak value, the platform is compromised from day one. | **Operational concern.** The CLI should enforce a minimum password length (e.g., 12 chars) and warn if the default/example value is used. Force-change on first login is a future enhancement. |
| **OQ-6** | Supabase Auth version pinning. Supabase Auth (Gotrue) evolves. API shapes may change. We should pin the Supabase Auth version in `docker-compose.yml` for local dev and in the hosted project config for prod. | **Operational concern.** Pin in the Supabase CLI config (`config.toml`) and Docker compose. |
| **OQ-7** | `app_user` ↔ `auth.users` sync on data import. If an operator bulk-imports users into `app_user` (e.g., from a CSV), they also need Supabase Auth users. The import tool must call Supabase Admin API for each user. | **Deferred.** Bulk import is a Phase 2 concern. Phase 1 user creation is one-at-a-time via the API. |

---

## 8. Traceability Matrix (compact)

| PRD section | Primary anchors |
|---|---|
| §1 Problem | platform-capabilities-v3 §C-03; tech-stack ADR (AuthN row) |
| §2.1 In scope | D1, D3, D4, D5, D6, D8, D11, D14, D20a, D20b, D21, D22, D25, D28a, D30, D33 |
| §2.2 Out of scope | C-02 (user identity), C-04 (authz), C-09 (notification), C-11 (audit framework), frontend architecture |
| §2.3 Phase 1 non-goals | D12b, D17, D23b, D26, D27, D29b, D31, D32 |
| §3 Personas | D8, D13, D18, D30 |
| §4 Journeys J1–J11 | D3–D6, D8, D8b, D13, D15, D16, D16b, D17, D18, D19, D20a, D20b, D25, D28a, D29, D30, D33 |
| §5 AC-1…AC-28 | All 34 decisions |
| §6 Risks | D1, D2, D5, D6, D17, D19, D21, D22, D26, D27, D33 |
| §7 Open questions | D15, D30, D31 |

---

## 9. Decision Log (from grill-me session)

| # | Decision | Lock |
|---|---|---|
| D1 | Auth provider | Supabase Auth is the full auth provider |
| D2 | Identity model | Shared UUID between `auth.users` and `app_user`; middleware DB lookup per request |
| D3 | User creation | Admin creates both `app_user` and `auth.users` at once via Supabase Admin API |
| D4 | Invitation flow | Backend generates invite token; `/auth/activate` calls Supabase `updateUser` |
| D5 | Invite token format | Stateless signed JWT (`user_id`, `email`, `exp=7d`); no DB table |
| D6 | Invite token secret | Separate HS256 secret `APP_INVITE_JWT_SECRET` with `iss=school-erp/invite` |
| D7 | JWT structure | Bare Supabase JWT; middleware reads only `sub`; DB lookup for context |
| D8 | Login endpoint (revised) | Backend proxies login to Supabase; C-03 owns all auth routes |
| D8b | Token response | `/auth/login` returns access + refresh in JSON; frontend stores both |
| D9b | Audit approach | Synchronous `LoginAttempt` recording; no poller; `login_attempt` is authoritative |
| D11 | `login_attempt` schema | Minimal audit-only: `client_id`, `user_id` (nullable), `email`, `event_type`, `ip_address`, `user_agent`, `occurred_at` |
| D12b | Session storage | No `session` table; Supabase is the sole session store; backend stateless |
| D13 | OTP | Supabase built-in OTP via `signInWithOtp`/`verifyOtp` |
| D14 | Endpoint scope | 9 Phase 1 endpoints; defer `/auth/me` and `/auth/resend-invite` |
| D15 | Password reset | Supabase built-in `resetPasswordForEmail` + `verifyOtp(recovery)` |
| D16 | Password change | Backend proxies to Supabase `updateUser` with service-role key |
| D16b | Current password | Require `current_password`; verify via Supabase `signInWithPassword` before update |
| D17 | Logout | Revoke only the refresh token; no JWT blocklist |
| D18 | Lifecycle gating | Only `active` users may log in; all other states rejected |
| D19 | Failure responses | Distinct status codes: 401 (bad creds), 403 (lifecycle/missing), 502 (Supabase down), 429 (rate-limited) |
| D20a | Creation failure | Rollback `app_user` insert on Supabase failure |
| D20b | Admin propagation | Email change → `updateUser`; suspend → `signOut(global)`; archive → `signOut` + `deleteUser` |
| D21 | Supabase client | Single `service_role` client for all auth operations |
| D22 | Config loading | Env vars (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`); missing → fatal |
| D23 | Test strategy | Mock Supabase client via `SupabaseAuthClient` Protocol |
| D23b | Smoke tests | No smoke tests; pure mock; no Docker dependency |
| D24 | Fake behavior | Thin fake: happy-path + documented failure modes only |
| D25 | Middleware extension | Auth routes unauthenticated; middleware tolerates absent JWT; resolves `client_id` from subdomain |
| D26 | MFA readiness | Architecture-only via Protocol extensibility; no dead columns/tables/stubs |
| D27 | SSO deferral | Defer `AuthenticationMethod` and `IdentityProvider` tables to Phase 2 |
| D28a | Event vocabulary | `login_attempt` limited to: `login_success`, `login_failure`, `logout`, `token_refresh` |
| D29 | Activation transition | Single step `Invited → Active` on `/auth/activate` |
| D29b | Pending state | Kept in state machine but no flow transitions into it |
| D30 | Bootstrap | CLI `python -m kernel.auth.bootstrap`; migration inserts `app_user`; CLI creates Supabase user |
| D31 | Rate limiting | Supabase-only; backend reads `X-Forwarded-For` |
| D32 | Frontend contract | Frontend token handling deferred; C-03 records binding contract only |
| D33 | Failure user_id lookup | On any failed login, look up `app_user` by email; record `user_id` if found |
| D34 | Scope confirmed | Phase 1 scope confirmed as enumerated |

---

> End of PRD — C-03 Authentication. Next SDD phase: impact classification → proposal/spec/design/tasks.
