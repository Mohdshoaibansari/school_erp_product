# Impact Classification — C-03 Authentication

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-03 — Authentication
> **Decisional inputs:** `docs/prd/c-03-authentication.md` (PRD), grill-me session (34 locked decisions, 2026-07-11)
> **Verification:** `openspec/specs/tenant-institution/spec.md` exists (C-01 behavioral spec). No C-03 spec exists yet. `openspec/specs/identity-user-management/` exists (C-02 behavioral spec, archived).

---

## Classification
- Domain status: **NEW** (C-03 has no existing OpenSpec spec)
- Delta type: **ADDED** (new domain) + **MODIFIED** (C-02 behavioral contract changes)
- Cross-cutting: **YES** — C-03 modifies C-02's behavioral contract (admin user creation/lifecycle now propagates to Supabase Auth)
- Recommended OpenSpec domain name: `authentication`
- Recommended OpenSpec change name: `add-c03-authentication`

## Reasoning

### C-03 is a NEW domain (ADDED)

The `openspec/specs/` directory contains `tenant-institution/spec.md` (C-01) and `identity-user-management/spec.md` (C-02). There is no `authentication` spec. This makes C-03's primary delta type ADDED — a brand-new domain introducing `login_attempt`, the `SupabaseAuthClient` Protocol, invite tokens, auth endpoints, and the bootstrap mechanism.

### C-03 MODIFIES C-02's behavioral contract

This is the first capability in the stack that modifies an existing domain's behavioral spec. C-02's spec (archived in `2026-07-11-add-c02-identity-user-management`) currently defines `app_user` CRUD and lifecycle transitions as independent operations — create a row, transition state, done. C-03 changes this: admin user creation must now also call Supabase Admin API to create a matching `auth.users` row, and lifecycle transitions (suspend, archive) must propagate to Supabase Auth. This is a behavioral change to C-02's domain — the C-02 spec must be updated to reflect that user creation and lifecycle management are no longer pure DB operations.

Specifically, C-02's spec will need MODIFIED deltas for:
- **User creation** — now includes Supabase Auth `createUser` call with rollback on failure (D3, D20a)
- **User suspension** — now includes Supabase Auth `signOut(uid, 'global')` to revoke all refresh tokens (D20b)
- **User archival** — now includes Supabase Auth `signOut(uid, 'global')` + `deleteUser(uid)` to remove the auth identity (D20b)
- **User email change** — now includes Supabase Auth `updateUser(uid, { email, email_confirm: false })` (D20b)

### C-03 does NOT modify C-01's spec

The middleware extension (D25 — tolerating absent JWT for unauthenticated auth routes) is an implementation detail of C-03's ADDED requirements. C-01's behavioral contract (tenant isolation, Client/Institution/OrgUnit CRUD, lifecycles) is unchanged. The middleware modification does not alter C-01's spec — it extends the middleware's behavior to support C-03's new unauthenticated routes. This is a code-level change, not a spec-level change to C-01.

### Why cross-cutting is YES

C-03 has a bidirectional dependency with C-02:
- **C-03 depends on C-02** — C-03 reads `app_user` for lifecycle checks (D18), email lookup (D33), and user_id linkage. C-03's `login_attempt` table has FKs to `app_user`.
- **C-02 depends on C-03** — C-02's user creation and lifecycle transitions now call Supabase Auth (C-03's domain). C-02's behavioral contract is modified by C-03.

This makes C-03 cross-cutting. The MODIFIED deltas to C-02 are genuine behavioral changes, not boundary declarations.

## ADDED requirements (high-level — C-03's new domain)

These are the requirement areas that will become requirements/scenarios in `specs/authentication/spec.md` during prd-to-sdd. Each maps to PRD §5 Acceptance Criteria and grill-me decisions.

- **SupabaseAuthClient Protocol** — A Python Protocol defining all Supabase Auth operations our backend calls: `createUser`, `signInWithPassword`, `signInWithOtp`, `verifyOtp`, `resetPasswordForEmail`, `updateUser`, `signOut`, `deleteUser`, `refreshToken`. Single `service_role` client implementation for production; in-memory `FakeSupabaseAuth` for tests. Protocol is extensible for future MFA methods. (D21, D23, D24, D26, AC-24, AC-25)
- **Login endpoint** — `POST /auth/login` accepts `{ email, password }`. Backend resolves `client_id` from subdomain, calls Supabase `signInWithPassword`. On Supabase success: looks up `app_user` by UUID (`sub`), checks lifecycle is `active` (D18), checks `app_user.client_id == ctx.client_id` (cross-tenant protection), records `login_success` in `login_attempt`, returns `{ access_token, refresh_token, expires_in }`. On failure: records `login_failure` with `user_id` from email lookup (D33). Returns 401 (bad creds), 403 (lifecycle/missing row), 502 (Supabase down), 429 (rate-limited). (D8, D8b, D18, D19, D25, D33, AC-2 through AC-8)
- **Refresh endpoint** — `POST /auth/refresh` accepts `{ refresh_token }`. Backend proxies to Supabase `token?grant_type=refresh_token`. Returns new access + refresh pair (Supabase rotation). Records `token_refresh` in `login_attempt`. (D8b, D28a, AC-9)
- **Logout endpoint** — `POST /auth/logout` accepts `{ refresh_token }`. Backend calls Supabase to revoke the refresh token. Records `logout` in `login_attempt`. Access token remains valid until expiry (≤1h). No JWT blocklist. (D17, D28a, AC-10)
- **Activate endpoint** — `POST /auth/activate` accepts `{ invite_token, password }`. Backend verifies invite JWT signature (HS256 with `APP_INVITE_JWT_SECRET`), checks `iss=school-erp/invite` and `exp`, extracts `user_id`. Rejects if user already `active`. Calls Supabase `updateUser(uid, { password, email_confirm: true })`. Transitions `app_user` from `invited` to `active`. Rejects expired/wrong-iss/invalid-signature tokens with 400. (D4, D5, D6, D29, AC-11, AC-12)
- **OTP request endpoint** — `POST /auth/otp/request` accepts `{ email }`. Backend proxies to Supabase `signInWithOtp({ email, shouldCreateUser: false })`. Supabase generates OTP and sends email. Returns 200. (D13, AC-13)
- **OTP verify endpoint** — `POST /auth/otp/verify` accepts `{ email, token }`. Backend proxies to Supabase `verifyOtp({ email, token, type: 'email' })`. On success: same lifecycle + client checks as login (D18, D25). Returns tokens. Records `login_success` or `login_failure`. (D13, D18, D19, AC-14)
- **Password reset request endpoint** — `POST /auth/password/reset/request` accepts `{ email }`. Backend proxies to Supabase `resetPasswordForEmail(email, redirectTo=<frontend reset URL>)`. Returns 200. (D15, AC-15)
- **Password reset confirm endpoint** — `POST /auth/password/reset/confirm` accepts `{ token, new_password }`. Backend calls Supabase `verifyOtp({ token, type: 'recovery' })` → `updateUser({ password })`. Returns 200. (D15, AC-16)
- **Password change endpoint** — `POST /auth/password/change` accepts `{ current_password, new_password }`. Backend calls Supabase `signInWithPassword` to verify current password (D16b). On success, calls Supabase `updateUser({ password })`. On re-login failure, returns 401. Records `login_success` from the re-login. (D16, D16b, AC-17)
- **Invite token minting** — Backend mints stateless signed JWT (`user_id`, `email`, `exp=7d`, `iss=school-erp/invite`) using separate HS256 secret (`APP_INVITE_JWT_SECRET`). No DB table. Cryptographically isolated from Supabase JWTs. (D4, D5, D6, AC-11)
- **LoginAttempt table + RLS** — Minimal audit-only table: `id`, `client_id` (FK, RLS), `user_id` (nullable FK, populated via email lookup per D33), `email`, `event_type` (`login_success` | `login_failure` | `logout` | `token_refresh`), `ip_address`, `user_agent`, `occurred_at`, `created_at`. RLS on `client_id` (platform owner sees all; tenant sees their own). (D11, D28a, D33, AC-5, AC-21, AC-22)
- **Synchronous audit recording** — All login attempts are recorded synchronously in the request path. No polling, no background worker, no `auth.audit_log_entries` access. `login_attempt` is the authoritative audit table for auth events. (D9b, AC-26)
- **Middleware extension for unauthenticated routes** — SubdomainJWTMiddleware tolerates absent JWT; resolves `client_id` from subdomain only for `/auth/*` routes that run before a JWT exists. Sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`. (D25, AC-3)
- **Supabase client configuration** — Single `service_role` client for all auth operations. Environment variables `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` loaded at app startup. Missing keys cause fatal startup error. (D21, D22, AC-18)
- **Bootstrap CLI** — `python -m kernel.auth.bootstrap` creates the first platform owner in Supabase Auth (matching the `app_user` row inserted by migration). Idempotent. Uses `PLATFORM_OWNER_INITIAL_PASSWORD` env var. (D30, AC-23)
- **IP forwarding** — Backend reads `X-Forwarded-For` headers to get the real client IP. IP stored in `login_attempt.ip_address` and forwarded to Supabase for rate limiting. (D31, AC-28)
- **Frontend token contract** — Documented binding contract: frontend stores access + refresh tokens, attaches `Authorization: Bearer <access_token>`, calls `/auth/refresh` on 401, clears tokens on logout. No frontend JS code implemented. (D32, AC-27)
- **ModuleManifest registration** — C-03 registers via the ModuleManifest Protocol (A5). Routes registered via `register_routes`. CLI registered via `register_cli`. (AC-23)

## MODIFIED requirements (C-02 behavioral contract changes)

C-02's spec must be updated with MODIFIED deltas reflecting that user creation and lifecycle management now propagate to Supabase Auth. These are genuine behavioral changes to C-02's domain — not boundary declarations.

- **User creation — Supabase Auth integration** — C-02's `create_user` service method now also calls Supabase Admin API `createUser({ id=X, email, email_confirm: false })` to create a matching `auth.users` row. On Supabase failure, the `app_user` insert is rolled back (transactional). The shared UUID model ensures `auth.users.id == app_user.id`. (D3, D20a, AC-2, AC-19)
- **User suspension — Supabase session revocation** — C-02's `transition_lifecycle` service method (when transitioning to `suspended`) now also calls Supabase Admin API `signOut(uid, 'global')` to revoke all refresh tokens. The suspended user's existing access token expires within the hour. D18 blocks re-login. (D20b, AC-20)
- **User archival — Supabase identity deletion** — C-02's `transition_lifecycle` service method (when transitioning to `archived`) now also calls Supabase Admin API `signOut(uid, 'global')` + `deleteUser(uid)` to remove the Supabase Auth identity entirely. The `app_user` row is retained for FK integrity. (D20b, AC-20)
- **User email change — Supabase email propagation** — C-02's `update_user` service method (when email changes) now also calls Supabase Admin API `updateUser(uid, { email, email_confirm: false })` to propagate the email change. (D20b, AC-20)

## REMOVED requirements

None. No existing requirements are removed.

## Boundary relationships (NOT modifications)

| C-03 relationship | Direction | Other capability | Nature | Why it is NOT a modification to the other domain |
|---|---|---|---|---|
| C-03 reads `app_user` for lifecycle checks, email lookup, user_id linkage | C-03 → C-02 | C-02 (Identity & User) | Data dependency | C-03 reads C-02's data (app_user table) but does not modify C-02's behavioral contract from C-03's side. The MODIFIED deltas are on C-02's side (admin propagation), not C-03's. |
| C-03's middleware extension tolerates absent JWT | C-03 → C-01 | C-01 (Tenant & Institution) | Infrastructure extension | C-03 extends the middleware to tolerate absent JWT for unauthenticated auth routes. This is a code-level change to kernel infrastructure, not a behavioral change to C-01's spec. C-01's tenant isolation contract is unchanged. |
| C-03 consumes AuditEmitter for lifecycle/credential audit events | C-03 → C-11 | C-01 (Audit) | Boundary / consumer | C-03 emits audit events via the AuditEmitter Protocol (C-11 boundary). C-11 owns the immutable event log. C-03 does not modify C-11's spec. |
| C-03's `login_attempt` table has FK to `app_user` | C-03 → C-02 | C-02 (Identity & User) | Schema dependency | `login_attempt.user_id` references `app_user.id`. This is a new FK from C-03 to C-02. C-02's schema is not modified (FK is on C-03's side). |
| C-04 (Authorization) will enforce permissions on auth endpoints | C-04 → C-03 | C-04 (Authorization) | Boundary / future consumer | C-04 will define Casbin policies for C-03's endpoints (e.g., who can view login attempts). C-03 does not modify C-04's spec. |

## Risk areas

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| **R1** | **C-02 spec modification complexity.** This is the first time we're modifying an existing OpenSpec spec. The prd-to-sdd subagent must handle the MODIFIED delta carefully — it must describe the exact behavioral change to C-02's user creation and lifecycle methods, not rewrite the entire C-02 spec. | Medium | The MODIFIED deltas are narrow: add Supabase Auth calls to `create_user`, `transition_lifecycle` (suspend/archive), and `update_user` (email change). Each delta is traceable to a D20 decision. The prd-to-sdd subagent should produce a separate delta spec file for C-02 modifications (`specs/identity-user-management/spec.md` delta). |
| **R2** | **Supabase availability dependency.** C-02's user creation now fails if Supabase is unavailable (D20a rollback). Previously, C-02 was self-contained (DB-only). This adds a hard external dependency. | High | Accepted per D20a. The rollback mechanism ensures no orphaned records. Tests use FakeSupabaseAuth (D24) so C-02's tests don't need live Supabase. |
| **R3** | **Two-domain change folder.** The change `add-c03-authentication` will contain delta specs for TWO domains: `authentication` (ADDED) and `identity-user-management` (MODIFIED). This is the first cross-domain change in the repo. | Medium | The prd-to-sdd subagent must create two delta spec files: `specs/authentication/spec.md` (ADDED) and `specs/identity-user-management/spec.md` (MODIFIED). The change folder is still one change — it's just multi-domain. |
| **R4** | **Middleware modification risk.** The middleware extension (D25) changes the request-path behavior for ALL requests, not just auth routes. If the "tolerate absent JWT" logic has bugs, it could affect authenticated routes. | Medium | The middleware change is narrow: only when no Authorization header is present AND the path is `/auth/*`, set a minimal TenantContext. All other paths continue to require a valid JWT. Tests must cover both paths (authenticated + unauthenticated). |
| **R5** | **C-02 test modifications.** C-02's existing tests (`test_c02_user.py`) will need updates to mock the SupabaseAuthClient Protocol when testing user creation and lifecycle transitions. | Medium | The prd-to-sdd subagent should note that C-02's test suite needs a `FakeSupabaseAuth` injection (same fake as C-03 uses). The existing C-02 tests that create users or transition lifecycles will now need the fake injected. |

## Recommendation for next phase (prd-to-sdd)

The prd-to-sdd subagent should create **one change folder** with **two domain delta specs**:

- Change folder: `openspec/changes/add-c03-authentication/`
- Delta spec 1: `openspec/changes/add-c03-authentication/specs/authentication/spec.md` — ADDED exclusively (new domain). Contains all C-03 requirements.
- Delta spec 2: `openspec/changes/add-c03-authentication/specs/identity-user-management/spec.md` — MODIFIED only. Contains the four behavioral changes to C-02 (user creation Supabase integration, suspend propagation, archive propagation, email change propagation).
- No REMOVED deltas.
- Requirements/scenarios in the ADDED spec: derived from the ADDED requirements list above, each traceable to a PRD AC and a grill-me decision ID (D1–D34).
- MODIFIED scenarios in the C-02 delta spec: derived from the MODIFIED requirements list above, each traceable to a D20 decision.
- Boundary notes: record the boundary relationships (table above) as part of C-03's own spec text, NOT as edits to C-01's domain.
- The change is multi-domain (first time), but the two domains are clearly scoped: `authentication` (ADDED) and `identity-user-management` (MODIFIED).
- The prd-to-sdd tasks should include updating C-02's archived OpenSpec spec to reflect the MODIFIED deltas.
