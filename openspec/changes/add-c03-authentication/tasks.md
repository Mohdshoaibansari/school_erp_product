# Implementation Tasks — C-03 Authentication

> **Traceability.** Each task traces to grill-me decision IDs (D1–D34) and PRD AC IDs (AC-1..AC-28). Tasks are grouped by concern and ordered by dependency. This is a checklist for the apply phase — no implementation is performed here.
>
> **Stack & architecture note.** The platform tech-stack ADR locks the stack (Postgres+Supabase, Python+FastAPI, SQLAlchemy 2.0+Alembic, Supabase Auth JWT, Casbin RBAC+ABAC, pytest). The platform software-architecture ADR locks the modular-monolith + module-manifest + monorepo structure (A1–A11). C-03 follows C-01/C-02's established patterns exactly.
>
> **Cross-domain note.** This is the first cross-domain change. Tasks include both C-03 ADDED tasks and C-02 MODIFIED tasks (admin propagation to Supabase Auth). C-02 modification tasks are in §12.
>
> **References:** proposal.md, specs/authentication/spec.md, specs/identity-user-management/spec.md, design.md; PRD `docs/prd/c-03-authentication.md`; C-02 service `backend/kernel/user/services/service.py`; C-02 design `openspec/changes/archive/2026-07-11-add-c02-identity-user-management/design.md`.

## 1. Module structure & manifest (A5, AC-23)

> C-03 is a kernel-tier module (A2). It registers via the ModuleManifest Protocol (A5). The manifest hooks are invoked by the app factory in dependency order (after C-02).

- [x] 1.1 Create the C-03 module directory structure under `/backend/kernel/auth/` with `__init__.py`, `manifest.py`, `models/`, `repos/`, `routes/`, `services/`, `dependencies.py`, `bootstrap.py`, `supabase_client.py`. — evidence: directory structure exists; `__init__.py` files importable.
- [x] 1.2 Implement `AuthenticationManifest` (subclass of `ManifestBase`) with `register_routes`, `register_casbin_policies`, `on_startup`, `on_shutdown`, `register_cli` hooks. Create a `manifest` singleton. — evidence: `manifest.py` exists; `manifest` object importable; `register_routes` mounts `/auth/*`; `register_cli` registers bootstrap command.
- [x] 1.3 Register C-03 manifest in the app factory's module list (after C-02, in dependency order). — evidence: `test_app_boots_with_c03_manifest` passes; C-03 routes mounted.

## 2. Database schema — login_attempt table (D11, D28a, D33, AC-5, AC-21, AC-22) — Alembic migration `003_c03_authentication.py`

> All C-03 migrations live in the single Alembic env at `/backend/migrations/` (A7) under filenames prefixed `003_c03_*`. RLS policies are written as raw SQL inside the same Alembic migration.

- [x] 2.1 Create the `login_attempt` table (`id` UUID v4 PK, `client_id` UUID FK → client nullable, `user_id` UUID FK → app_user nullable, `email` TEXT NOT NULL, `event_type` TEXT NOT NULL, `ip_address` TEXT, `user_agent` TEXT, `occurred_at` TIMESTAMPTZ NOT NULL, `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()). — evidence: migration creates `login_attempt` table; `test_login_attempt_pk_is_uuid_v4` + `test_login_attempt_has_client_id` + `test_login_attempt_has_user_id` pass.
- [x] 2.2 Enable RLS and create `client_id`-matching policy on `login_attempt` (same pattern as C-02's tenant-scoped tables). — evidence: migration enables FORCE RLS + creates policies; `test_login_attempt_rls_tenant_select` + `test_login_attempt_rls_platform_owner_select` pass.
- [x] 2.3 Seed the platform owner `app_user` row in the migration (no Supabase call — migration is data-only). — evidence: migration inserts platform owner `app_user` row with `lifecycle_status='active'`; `test_platform_owner_app_user_exists` passes.

## 3. SupabaseAuthClient Protocol + impls (D21, D23, D24, D26, AC-24, AC-25)

> The Protocol lives at `/backend/kernel/auth/supabase_client.py`. Production impl wraps the Supabase SDK. Fake impl is in-memory.

- [x] 3.1 Define `SupabaseAuthClient` Protocol with methods: `create_user`, `sign_in_with_password`, `sign_in_with_otp`, `verify_otp`, `reset_password_for_email`, `update_user`, `sign_out`, `delete_user`, `refresh_token`, `revoke_refresh_token`. — evidence: `supabase_client.py` exists; Protocol is a `typing.Protocol` subclass; `test_protocol_methods_defined` passes.
- [x] 3.2 Implement `SupabaseAuthClientImpl` (production impl) wrapping the Supabase SDK. Uses `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` env vars. — evidence: `supabase_client.py` contains `SupabaseAuthClientImpl`; `test_production_impl_uses_service_role_key` passes.
- [x] 3.3 Implement `FakeSupabaseAuth` (test impl) — in-memory dict store, happy-path + documented failure modes (invalid credentials, user not found, user already exists, refresh revoked). — evidence: `tests/fake_supabase_auth.py` exists; `test_fake_create_user` + `test_fake_sign_in_with_password_success` + `test_fake_sign_in_with_password_failure` + `test_fake_update_user` + `test_fake_sign_out` + `test_fake_delete_user` pass.

## 4. Supabase client configuration (D22, AC-18)

> Supabase client constructed at app startup from env vars. Injected via FastAPI dependency.

- [x] 4.1 Load `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from env at app startup. Missing keys cause fatal startup error. — evidence: `supabase_client.py` raises `ValueError` on missing keys; `test_missing_supabase_url_fatal` + `test_missing_supabase_key_fatal` pass.
- [x] 4.2 Wire the Supabase client into the app factory as a singleton. Injected via FastAPI dependency `get_supabase_auth_client()`. — evidence: `dependencies.py` contains `get_supabase_auth_client`; `test_dependency_supabase_client` passes.

## 5. Invite token minting (D4, D5, D6, AC-11)

> Invite token is a stateless JWT signed with `APP_INVITE_JWT_SECRET`. No DB table.

- [ ] 5.1 Implement `mint_invite_token(user_id, email)` → JWT with `sub=user_id`, `email`, `exp=7d`, `iss="school-erp/invite"`, signed with `APP_INVITE_JWT_SECRET` (HS256). — evidence: `services/invite_token.py` exists; `test_mint_invite_token_claims` + `test_mint_invite_token_signature` pass.
- [ ] 5.2 Implement `verify_invite_token(token)` → returns `{ user_id, email }` or raises `InvalidInviteTokenError`. Checks signature, `iss`, `exp`. — evidence: `services/invite_token.py` exists; `test_verify_valid_token` + `test_verify_expired_token` + `test_verify_wrong_iss` + `test_verify_invalid_signature` pass.
- [ ] 5.3 Load `APP_INVITE_JWT_SECRET` from env at app startup. Missing key causes fatal startup error. — evidence: `test_missing_invite_secret_fatal` passes.

## 6. Middleware extension for unauthenticated routes (D25, AC-3)

> Middleware at `/backend/kernel/middleware.py` is extended to tolerate absent JWT for `/auth/*` routes.

- [ ] 6.1 Extend `SubdomainJWTMiddleware.dispatch()` to detect absent `Authorization` header (or invite JWT with `iss="school-erp/invite"`) and set `TenantContext(client_id=<from subdomain>, institution_id=None, user_id=None, roles=[])`. — evidence: `test_middleware_no_jwt_sets_subdomain_context` + `test_middleware_invite_jwt_sets_subdomain_context` pass.
- [ ] 6.2 Ensure existing authenticated path (Supabase JWT present) is unchanged. — evidence: `test_middleware_supabase_jwt_full_context` + `test_middleware_no_subdomain_returns_400` pass (existing tests still pass).

## 7. Auth service — domain logic (D8, D8b, D13, D15, D16, D16b, D17, D18, D19, D25, D28a, D33)

> Auth service lives at `/backend/kernel/auth/services/service.py`. Orchestrates SupabaseAuthClient + app_user repo + login_attempt repo + invite token + TenantContext.

- [ ] 7.1 Implement `AuthService` with `__init__` accepting `SupabaseAuthClient`, `UserRepository`, `LoginAttemptRepository`, `session_factory`, `audit_emitter`. — evidence: `services/service.py` exists; `test_auth_service_init` passes.
- [ ] 7.2 Implement `login(ctx, email, password)` → calls Supabase `sign_in_with_password`, looks up `app_user` by UUID (`sub`), checks lifecycle is `active` (D18), checks `app_user.client_id == ctx.client_id` (cross-tenant), records `login_success`/`login_failure`, returns tokens or raises `AuthError`. — evidence: `test_login_success` + `test_login_bad_credentials_401` + `test_login_lifecycle_not_active_403` + `test_login_cross_tenant_403` + `test_login_missing_app_user_403` + `test_login_supabase_down_502` + `test_login_records_user_id_from_email_lookup` pass.
- [ ] 7.3 Implement `refresh(ctx, refresh_token)` → calls Supabase `refresh_token`, returns new pair, records `token_refresh`. — evidence: `test_refresh_success` + `test_refresh_invalid_token` pass.
- [ ] 7.4 Implement `logout(ctx, refresh_token)` → calls Supabase `revoke_refresh_token`, records `logout`. — evidence: `test_logout_success` pass.
- [ ] 7.5 Implement `activate(ctx, invite_token, password)` → verifies invite JWT, checks user not already `active`, calls Supabase `update_user(uid, password, email_confirm=true)`, transitions `app_user` from `invited` to `active`. — evidence: `test_activate_success` + `test_activate_expired_token` + `test_activate_wrong_iss` + `test_activate_already_active` pass.
- [ ] 7.6 Implement `request_otp(ctx, email)` → calls Supabase `sign_in_with_otp`, returns 200. — evidence: `test_request_otp_success` pass.
- [ ] 7.7 Implement `verify_otp(ctx, email, token)` → calls Supabase `verify_otp`, same lifecycle + client checks as login, returns tokens, records `login_success`/`login_failure`. — evidence: `test_verify_otp_success` + `test_verify_otp_invalid_code` + `test_verify_otp_lifecycle_check` pass.
- [ ] 7.8 Implement `request_password_reset(ctx, email)` → calls Supabase `reset_password_for_email`, returns 200. — evidence: `test_request_password_reset_success` pass.
- [ ] 7.9 Implement `confirm_password_reset(ctx, token, new_password)` → calls Supabase `verify_otp(recovery)` + `update_user(password)`, returns 200. — evidence: `test_confirm_password_reset_success` + `test_confirm_password_reset_invalid_token` pass.
- [ ] 7.10 Implement `change_password(ctx, current_password, new_password)` → calls Supabase `sign_in_with_password` (re-login), then `update_user(password)`, records `login_success`. — evidence: `test_change_password_success` + `test_change_password_wrong_current` pass.

## 8. LoginAttempt repository (D11, D28a, D33, AC-5, AC-21)

> LoginAttempt repo lives at `/backend/kernel/auth/repos/login_attempt_repo.py`. Inherits `TenantAwareRepositoryBase`.

- [x] 8.1 Implement `LoginAttemptRepository` (inherits `TenantAwareRepositoryBase[LoginAttempt]`). Methods: `record(session, ctx, email, event_type, user_id=None, ip_address=None, user_agent=None)`. Returns `LoginAttemptDTO`. — evidence: `repos/login_attempt_repo.py` exists; `test_login_attempt_repo_record` + `test_login_attempt_repo_filters_by_client_id` pass.
- [x] 8.2 Implement `LoginAttempt` ORM model at `models/login_attempt.py`. — evidence: `models/login_attempt.py` exists; `test_login_attempt_model_fields` pass.
- [x] 8.3 Implement `LoginAttemptDTO` at `services/dtos.py`. — evidence: DTO exists; `test_login_attempt_dto_serialization` passes.

## 9. Auth routes — FastAPI endpoints (D14, D19)

> Auth routes live at `/backend/kernel/auth/routes/`. Routes registered via the manifest `register_routes` hook (A5). Unauthenticated routes read `client_id` from `TenantContext` (set by extended middleware).

- [ ] 9.1 Implement `POST /auth/login` endpoint. Accepts `{ email, password }`. Calls `AuthService.login()`. Returns tokens on success, appropriate HTTP errors on failure (D19). — evidence: `routes/auth.py` exists; `test_route_login_success` + `test_route_login_bad_credentials` + `test_route_login_lifecycle_not_active` + `test_route_login_cross_tenant` pass.
- [ ] 9.2 Implement `POST /auth/refresh` endpoint. Accepts `{ refresh_token }`. Calls `AuthService.refresh()`. — evidence: `test_route_refresh_success` + `test_route_refresh_invalid_token` pass.
- [ ] 9.3 Implement `POST /auth/logout` endpoint. Accepts `{ refresh_token }`. Calls `AuthService.logout()`. — evidence: `test_route_logout_success` pass.
- [ ] 9.4 Implement `POST /auth/activate` endpoint. Accepts `{ invite_token, password }`. Calls `AuthService.activate()`. — evidence: `test_route_activate_success` + `test_route_activate_expired_token` + `test_route_activate_already_active` pass.
- [ ] 9.5 Implement `POST /auth/otp/request` endpoint. Accepts `{ email }`. Calls `AuthService.request_otp()`. — evidence: `test_route_otp_request_success` pass.
- [ ] 9.6 Implement `POST /auth/otp/verify` endpoint. Accepts `{ email, token }`. Calls `AuthService.verify_otp()`. — evidence: `test_route_otp_verify_success` + `test_route_otp_verify_failure` pass.
- [ ] 9.7 Implement `POST /auth/password/reset/request` endpoint. Accepts `{ email }`. Calls `AuthService.request_password_reset()`. — evidence: `test_route_password_reset_request_success` pass.
- [ ] 9.8 Implement `POST /auth/password/reset/confirm` endpoint. Accepts `{ token, new_password }`. Calls `AuthService.confirm_password_reset()`. — evidence: `test_route_password_reset_confirm_success` + `test_route_password_reset_confirm_invalid_token` pass.
- [ ] 9.9 Implement `POST /auth/password/change` endpoint. Accepts `{ current_password, new_password }`. Calls `AuthService.change_password()`. — evidence: `test_route_password_change_success` + `test_route_password_change_wrong_current` pass.

## 10. Auth dependencies — FastAPI dependency injection (A6)

> Dependencies live at `/backend/kernel/auth/dependencies.py`.

- [ ] 10.1 Implement `get_auth_service()` dependency (returns the AuthService singleton with injected SupabaseAuthClient, UserRepository, LoginAttemptRepository). — evidence: `dependencies.py` exists; `test_dependency_get_auth_service` passes.
- [ ] 10.2 Wire dependencies in auth route handlers via `Depends(get_auth_service)`. — evidence: all auth route handlers use `Depends`; `test_auth_route_dependency_wiring` passes.

## 11. IP forwarding (D31, AC-28)

> Backend reads `X-Forwarded-For` to get the real client IP.

- [ ] 11.1 Implement `get_client_ip(request)` utility that reads `X-Forwarded-For` header (first IP if multiple) or falls back to request's direct IP. — evidence: `utils/ip.py` exists; `test_get_client_ip_from_x_forwarded_for` + `test_get_client_ip_direct` pass.
- [ ] 11.2 Wire `get_client_ip` into auth endpoints so `login_attempt.ip_address` is populated correctly. — evidence: `test_login_attempt_records_ip_from_x_forwarded_for` pass.

## 12. C-02 modifications — admin propagation to Supabase Auth (D3, D20a, D20b, AC-2, AC-19, AC-20)

> These tasks modify `backend/kernel/user/services/service.py` (C-02's service). C-02's service constructor gains an optional `SupabaseAuthClient` parameter. The `create_user`, `transition_lifecycle`, and `update_user` methods are extended to propagate to Supabase Auth.

- [ ] 12.1 Add optional `SupabaseAuthClient` parameter to `IdentityUserService.__init__()`. Default to `None` (backwards compatible — C-02 tests that don't inject it work unchanged). — evidence: `test_c02_service_accepts_supabase_client` passes.
- [ ] 12.2 Extend `create_user` to call Supabase `create_user(id, email)` after `app_user` insert. On Supabase failure, rollback the `app_user` insert and raise. — evidence: `test_c02_create_user_creates_supabase_user` + `test_c02_create_user_supabase_failure_rolls_back` pass.
- [ ] 12.3 Extend `transition_lifecycle` (when new_state == 'suspended') to call Supabase `sign_out(uid, 'global')`. — evidence: `test_c02_suspend_revokes_supabase_sessions` pass.
- [ ] 12.4 Extend `transition_lifecycle` (when new_state == 'archived') to call Supabase `sign_out(uid, 'global')` + `delete_user(uid)`. — evidence: `test_c02_archive_deletes_supabase_user` pass.
- [ ] 12.5 Extend `update_user` (when email changes) to call Supabase `update_user(uid, email=email, email_confirm=False)`. — evidence: `test_c02_email_change_propagates_to_supabase` + `test_c02_non_email_update_no_supabase_call` pass.

## 13. Bootstrap CLI (D30, AC-23)

> Bootstrap CLI at `/backend/kernel/auth/bootstrap.py`. Run once after `alembic upgrade`.

- [ ] 13.1 Implement `bootstrap.py` as a `__main__` module. Loads `PLATFORM_OWNER_INITIAL_PASSWORD` from env. Looks up the platform owner `app_user` row. Calls Supabase `create_user(id, email)` + `update_user(uid, password, email_confirm=True)`. Idempotent (checks if Supabase user exists first). — evidence: `test_bootstrap_creates_supabase_user` + `test_bootstrap_idempotent` + `test_bootstrap_missing_password_fatal` pass.

## 14. Integration tests — end-to-end scenarios (AC-1..AC-28)

> Integration tests verify the full request flow: middleware → route → service → repo → database. All tests use `FakeSupabaseAuth` — no Docker, no live Supabase.

- [ ] 14.1 Test full login flow: create user → activate → login → get tokens → refresh → logout. — evidence: `test_integration_full_auth_flow` passes.
- [ ] 14.2 Test cross-tenant login rejection: user at School A cannot log in at School B's subdomain. — evidence: `test_integration_cross_tenant_login_rejected` passes.
- [ ] 14.3 Test lifecycle gating: suspended/archived users cannot log in. — evidence: `test_integration_lifecycle_gating_suspended` + `test_integration_lifecycle_gating_archived` pass.
- [ ] 14.4 Test admin propagation: create user → Supabase user exists; suspend user → Supabase sessions revoked; archive user → Supabase user deleted. — evidence: `test_integration_admin_create_propagation` + `test_integration_admin_suspend_propagation` + `test_integration_admin_archive_propagation` pass.
- [ ] 14.5 Test OTP flow: request OTP → verify OTP → get tokens. — evidence: `test_integration_otp_flow` passes.
- [ ] 14.6 Test password reset flow: request reset → confirm reset → login with new password. — evidence: `test_integration_password_reset_flow` passes.
- [ ] 14.7 Test password change flow: change password → login with new password. — evidence: `test_integration_password_change_flow` passes.
- [ ] 14.8 Test login attempt audit: verify `login_attempt` rows are recorded for success, failure, logout, refresh. — evidence: `test_integration_login_attempt_audit` passes.

## 15. C-02 test updates — FakeSupabaseAuth injection

> Existing C-02 tests that create users or transition lifecycles now need the `FakeSupabaseAuth` injected.

- [ ] 15.1 Update C-02 test fixtures to inject `FakeSupabaseAuth` into `IdentityUserService`. — evidence: existing C-02 tests pass with the new service constructor parameter.
