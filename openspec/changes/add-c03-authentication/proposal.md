## Why

Every business module in the School ERP needs an authenticated user. Attendance, Fees, Homework, Exams, Timetable — every API call requires knowing "who is making this request." Without a centralized authentication capability, each module would manage login, session, and credential flows independently, leading to fragmented security, duplicated logic, and no single point of audit for "who logged in and when."

C-03 provides the **single authentication gateway** for the entire platform. It answers: how does a user prove their identity, how is that proof represented (JWT), how long does a session last, and how does an admin invite and provision new users. C-03 sits between C-02 (which stores user identity) and all modules that need to know "who is making this request." Every authenticated API call flows through C-03's JWT validation.

Key architectural decisions: **Supabase Auth is the full authentication provider** (D1). Our backend never touches passwords — Supabase handles hashing (bcrypt), session management, and token issuance. Our backend proxies login/refresh/OTP calls to Supabase and adds domain logic on top: lifecycle gating (only `active` users can log in), cross-tenant protection (login by email must match the subdomain's client), and audit recording (`login_attempt` table). The backend is the only service that talks to Supabase (D8 revised) — the frontend never talks to Supabase directly.

This is the **first cross-domain change** in the repo. C-03 modifies C-02's behavioral contract: admin user creation and lifecycle transitions now propagate to Supabase Auth. The change contains two delta specs: `authentication` (ADDED) and `identity-user-management` (MODIFIED).

## What Changes

- **NEW: SupabaseAuthClient Protocol** — A Python Protocol defining all Supabase Auth operations our backend calls: `createUser`, `signInWithPassword`, `signInWithOtp`, `verifyOtp`, `resetPasswordForEmail`, `updateUser`, `signOut`, `deleteUser`, `refreshToken`. Single `service_role` client implementation for production; in-memory `FakeSupabaseAuth` for tests. Protocol is extensible for future MFA methods (D26).
- **NEW: LoginAttempt table + RLS** — Minimal audit-only table: `id`, `client_id` (FK, RLS), `user_id` (nullable FK, populated via email lookup per D33), `email`, `event_type` (`login_success` | `login_failure` | `logout` | `token_refresh`), `ip_address`, `user_agent`, `occurred_at`, `created_at`. RLS on `client_id` (platform owner sees all; tenant sees their own).
- **NEW: 9 auth endpoints** — `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/activate`, `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/password/reset/request`, `POST /auth/password/reset/confirm`, `POST /auth/password/change`. All endpoints proxy to Supabase Auth and add domain logic (lifecycle gating, cross-tenant protection, audit recording).
- **NEW: Invite token minting** — Stateless signed JWT (`user_id`, `email`, `exp=7d`, `iss=school-erp/invite`) using separate HS256 secret (`APP_INVITE_JWT_SECRET`). No DB table. Cryptographically isolated from Supabase JWTs.
- **NEW: Middleware extension for unauthenticated routes** — SubdomainJWTMiddleware tolerates absent JWT; resolves `client_id` from subdomain only for `/auth/*` routes that run before a JWT exists. Sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`.
- **NEW: Bootstrap CLI** — `python -m kernel.auth.bootstrap` creates the first platform owner in Supabase Auth (matching the `app_user` row inserted by migration). Idempotent. Uses `PLATFORM_OWNER_INITIAL_PASSWORD` env var.
- **MODIFIED: C-02 user creation** — C-02's `create_user` service method now also calls Supabase Admin API `createUser({ id=X, email, email_confirm: false })` to create a matching `auth.users` row. On Supabase failure, the `app_user` insert is rolled back (transactional).
- **MODIFIED: C-02 user suspension** — C-02's `transition_lifecycle` service method (when transitioning to `suspended`) now also calls Supabase Admin API `signOut(uid, 'global')` to revoke all refresh tokens.
- **MODIFIED: C-02 user archival** — C-02's `transition_lifecycle` service method (when transitioning to `archived`) now also calls Supabase Admin API `signOut(uid, 'global')` + `deleteUser(uid)` to remove the Supabase Auth identity entirely.
- **MODIFIED: C-02 user email change** — C-02's `update_user` service method (when email changes) now also calls Supabase Admin API `updateUser(uid, { email, email_confirm: false })` to propagate the email change.

## Capabilities

### New Capabilities
- `authentication`: Centralized authentication — SupabaseAuthClient Protocol, LoginAttempt table, 9 auth endpoints, invite token minting, middleware extension, bootstrap CLI, IP forwarding, frontend token contract.

### Modified Capabilities
- `identity-user-management`: C-02's user creation, suspension, archival, and email change now propagate to Supabase Auth. Behavioral contract modified — user lifecycle management is no longer a pure DB operation.

## Impact

- **New code:** `backend/kernel/auth/` (models, repos, routes, services, manifest, bootstrap CLI, SupabaseAuthClient Protocol + impl)
- **New migration:** `003_c03_authentication.py` — `login_attempt` table + RLS + platform owner `app_user` seed row
- **Modified code:** `backend/kernel/user/services/service.py` — `create_user`, `transition_lifecycle`, `update_user` now call Supabase Auth
- **Modified code:** `backend/kernel/middleware.py` — tolerate absent JWT for `/auth/*` routes
- **Kernel dependencies:** C-03 inherits TenantAwareRepositoryBase, TenantContext, AuditEmitter from kernel (no kernel infrastructure modifications)
- **Config:** New env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_INVITE_JWT_SECRET`, `PLATFORM_OWNER_INITIAL_PASSWORD`
- **Future consumers:** C-04 (AuthZ) will enforce permissions on auth endpoints; C-09 (Notification) will consume auth events; C-11 (Audit) receives lifecycle/credential audit events
- **Boundary declarations:** C-03 does NOT own user identity (C-02), authorization (C-04), audit storage (C-11), or frontend auth client (deferred to frontend architecture phase)
