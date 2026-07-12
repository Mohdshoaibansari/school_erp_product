## Context

C-03 (Authentication) is the fourth capability in the School ERP platform, after C-01 (Tenant & Institution), C-02 (Identity & User), and the kernel/business refactor. C-03 provides the centralized authentication gateway — every authenticated API call flows through C-03's JWT validation. C-03 is entirely Kernel — authentication is platform infrastructure, not business domain.

This is the **first cross-domain change** in the repo. C-03 introduces a NEW `authentication` domain (ADDED) and modifies C-02's `identity-user-management` domain (MODIFIED — user creation/lifecycle now propagates to Supabase Auth). The change folder contains two delta specs: `specs/authentication/spec.md` (ADDED) and `specs/identity-user-management/spec.md` (MODIFIED).

**Key architectural decision:** Supabase Auth is the full authentication provider (D1). Our backend never touches passwords. Supabase handles hashing, session management, and token issuance. Our backend proxies auth calls to Supabase and adds domain logic: lifecycle gating (D18), cross-tenant protection (D25), and audit recording (D9b). The backend is the only service that talks to Supabase (D8 revised) — the frontend never talks to Supabase directly.

**References:**
- Proposal: `openspec/changes/add-c03-authentication/proposal.md`
- Spec (ADDED): `openspec/changes/add-c03-authentication/specs/authentication/spec.md`
- Spec (MODIFIED): `openspec/changes/add-c03-authentication/specs/identity-user-management/spec.md`
- PRD: `docs/prd/c-03-authentication.md`
- Impact classification: `docs/prd/c-03-impact-classification.md`
- C-02 spec: `openspec/specs/identity-user-management/spec.md` (archived)
- C-02 service: `backend/kernel/user/services/service.py`
- C-02 design: `openspec/changes/archive/2026-07-11-add-c02-identity-user-management/design.md`
- C-01 spec: `openspec/specs/tenant-institution/spec.md`
- Platform architecture ADR: `docs/architecture/adr-platform-software-architecture.md` (A1–A11)
- Tech stack ADR: `docs/architecture/adr-platform-tech-stack.md`

## Goals / Non-Goals

**Goals:**
- Implement the `SupabaseAuthClient` Protocol + production impl + `FakeSupabaseAuth` test impl
- Implement the `login_attempt` table + RLS (new Alembic migration)
- Implement 9 auth endpoints: login, refresh, logout, activate, OTP request/verify, password reset request/confirm, password change
- Implement invite token minting (stateless JWT with separate secret)
- Extend the middleware to tolerate absent JWT for unauthenticated auth routes
- Modify C-02's `create_user`, `transition_lifecycle`, `update_user` to propagate to Supabase Auth
- Implement the bootstrap CLI for the first platform owner
- Implement IP forwarding (`X-Forwarded-For`) for `login_attempt.ip_address`
- Follow C-01/C-02's established patterns exactly (module structure, repo base, service layer, DTOs, manifest, RLS)

**Non-Goals:**
- MFA — architecture is extensible via Protocol (D26), but zero MFA code in Phase 1
- SSO (Google, Microsoft, SAML, LDAP) — `AuthenticationMethod` and `IdentityProvider` tables deferred to Phase 2 (D27)
- SMS OTP — requires SMS integration (not in Supabase's built-in OTP)
- Frontend auth client (token storage, Axios interceptor, route guards) — deferred to frontend architecture phase (D32)
- `/auth/me` endpoint — frontend uses existing C-02 user endpoints (D14)
- `/auth/resend-invite` — admin can re-create the user or we add later (D14)
- App-layer rate limiting — Supabase owns brute-force protection (D31)
- Smoke tests against live Supabase — all tests use FakeSupabaseAuth (D23b)
- Session table — Supabase is the sole session store (D12b)
- JWT blocklist — on logout, only the refresh token is revoked (D17)
- Pending lifecycle transitions — `Pending` state is kept in C-02's state machine but no flow transitions into it (D29b)

## Decisions

### Decision 1: Supabase Auth as Full Provider

**Choice:** Supabase Auth handles all password hashing, session management, and token issuance. Our backend never stores or hashes passwords. All credential verification goes through Supabase's `signInWithPassword`, `verifyOtp`, or `resetPasswordForEmail`.

**Rationale:** POC-validated. Supabase Auth is battle-tested. Our backend adds domain logic on top (lifecycle gating, cross-tenant protection, audit recording). The backend is the only service that talks to Supabase — the frontend never talks to Supabase directly (D8 revised).

### Decision 2: Shared UUID Between auth.users and app_user

**Choice:** Supabase Auth's `auth.users` and our `app_user` share the same UUID. When an admin creates a user, our service creates both records with the same UUID. Middleware does a DB lookup per request to resolve `client_id`/`institution_id`/`roles` from the JWT `sub`.

**Rationale:** Single source of truth for identity = Supabase Auth; single source of truth for domain = our DB. The shared UUID is the link between them. No second JWT, no Supabase triggers, no custom claims.

### Decision 3: SupabaseAuthClient Protocol

**Choice:** Define a `SupabaseAuthClient` Protocol that abstracts all Supabase Auth operations. Production `SupabaseAuthClientImpl` wraps the Supabase SDK using the `service_role` key. In-memory `FakeSupabaseAuth` implements the Protocol for tests. The Protocol is extensible for future MFA methods (D26).

**Rationale:** Decouples our auth logic from Supabase's SDK. Tests use the fake (no Docker dependency). Adding MFA in Phase 2 = adding new methods to the Protocol. Clean separation of concerns.

### Decision 4: Single service_role Client

**Choice:** Our backend uses one Supabase client configured with the `service_role` key for all auth operations (login proxy, OTP, activate, password flows, admin actions like createUser/signOut/deleteUser/updateUser).

**Rationale:** Dead simple. No key-switching logic. RLS on `app_user` still protects our domain data because that data is accessed via our own SQLAlchemy session (user's JWT), not via the service-role Supabase client.

### Decision 5: Invite Token as Stateless JWT

**Choice:** Invite tokens are stateless signed JWTs (HS256 with `APP_INVITE_JWT_SECRET`), carrying `sub` (user_id), `email`, `exp` (7 days), `iss` ("school-erp/invite"). No DB table. Cryptographically isolated from Supabase JWTs (different secret, different issuer).

**Rationale:** No DB storage, no cleanup, simple. The invite token is sent as a URL parameter in the invite link. `/auth/activate` verifies the JWT and sets the password via Supabase Admin API.

### Decision 6: Middleware Extension for Unauthenticated Routes

**Choice:** SubdomainJWTMiddleware tolerates absent JWT for `/auth/*` routes. When no `Authorization` header is present (or the JWT has `iss="school-erp/invite"`), the middleware sets `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`. Auth routes that need `client_id` read it from context.

**Rationale:** Minimal middleware change. Subdomain still resolved. Cross-tenant login blocked. Consistent with the "single gateway" principle. Auth routes don't need a JWT to function.

### Decision 7: Synchronous LoginAttempt Recording

**Choice:** All login attempts are recorded synchronously in the request path. No polling, no background worker, no `auth.audit_log_entries` access. `login_attempt` is the authoritative audit table for auth events.

**Rationale:** Since the backend proxies login (D8 revised), it sees every login attempt directly. No need for polling. Simple, synchronous, reliable.

### Decision 8: Admin Propagation to Supabase

**Choice:** C-02's `create_user`, `transition_lifecycle` (suspend/archive), and `update_user` (email change) now propagate to Supabase Auth. On user creation failure, the `app_user` insert is rolled back (transactional). On suspend, `signOut(uid, 'global')` revokes all refresh tokens. On archive, `signOut` + `deleteUser` removes the Supabase Auth identity. On email change, `updateUser(uid, { email, email_confirm: false })` propagates.

**Rationale:** Domain changes must reflect immediately to auth. Suspended users must lose access within the hour. Archived users (terminal) must not be able to refresh. Email changes must propagate so password reset and OTP work with the new email.

### Decision 9: Bootstrap via CLI

**Choice:** A migration inserts the platform owner `app_user` row (no Supabase call). A CLI command `python -m kernel.auth.bootstrap` creates the matching Supabase Auth user with `email_confirm: true`. Idempotent. Uses `PLATFORM_OWNER_INITIAL_PASSWORD` env var.

**Rationale:** Clean separation (migration = data; bootstrap = external service calls). Keeps migrations free of external service calls (D20a lesson). Idempotent for safety.

### Decision 10: Lifecycle Gating on Login

**Choice:** Only `app_user.lifecycle_status == 'active'` users may log in. All other states (invited, pending, suspended, archived) are rejected after Supabase auth succeeds. Returns 403 with the specific state.

**Rationale:** Simplest rule. One state is the "can log in" state. Since D29 transitions `invited → active` directly on activation, `pending` is unused (D29b). `suspended` and `archived` users must be blocked immediately (D20b propagation ensures their Supabase sessions are revoked).

### Decision 11: Phase 1 Endpoint Scope

**Choice:** 9 Phase 1 endpoints: login, refresh, logout, activate, OTP request/verify, password reset request/confirm, password change. Defer `/auth/me` (frontend uses C-02 endpoints), `/auth/resend-invite` (admin can re-create), MFA, SSO.

**Rationale:** Covers all authentication flows needed for Phase 1. MFA and SSO are Phase 2. `/auth/me` is redundant (C-02 user endpoints exist).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Supabase as a single point of failure for authentication | Accepted per D1. Supabase Auth has high availability (99.9%+ SLA on hosted). 502 response gives frontend a clear signal. |
| Access token window after logout (≤1h) | Accepted per D17. Standard JWT trade-off. Short access token lifetime + refresh token rotation mitigates. |
| Cross-tenant login detection depends on email lookup | Accepted per D2. Shared UUID model ensures sync. D20a rollback prevents orphaned records. |
| Invite token security (sent as URL param) | Accepted. Sent over TLS, valid for 7 days, cryptographically isolated from Supabase JWTs. Only allows setting a password. |
| Supabase service_role key exposure | Accepted per D21/D22. Key loaded from env vars, never logged. Same risk as any database credential. |
| C-02 now depends on Supabase availability for user creation | Accepted per D20a. Rollback mechanism ensures no orphaned records. Tests use FakeSupabaseAuth. |
| D16b re-login creates noisy login_success audit row | Accepted. Extra row is harmless noise. Future enhancement: add `verification` event type. |

## Open Questions

| # | Item | Disposition |
|---|---|---|
| OQ-1 | Supabase email templates and provider configuration | Deferred. Phase 1 uses Supabase defaults. |
| OQ-2 | Frontend reset-password URL (`redirectTo` parameter) | Deferred to implementation. Read from env var or `Origin` header. |
| OQ-3 | Supabase IP forwarding | Addressed in D31. Backend reads `X-Forwarded-For`. |
| OQ-4 | Invite token reuse on already-active user | Resolved. `/auth/activate` rejects if user already `active`. |
| OQ-5 | `PLATFORM_OWNER_INITIAL_PASSWORD` env var security | Operational concern. CLI enforces minimum length. |
| OQ-6 | Supabase Auth version pinning | Operational concern. Pin in Supabase CLI config. |
| OQ-7 | Bulk user import (CSV) | Deferred. Phase 1 user creation is one-at-a-time via API. |
