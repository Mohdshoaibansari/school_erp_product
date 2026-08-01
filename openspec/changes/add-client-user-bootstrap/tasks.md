## 1. Database — client_user + lifecycle event tables (migration 011)

- [x] 1.1 Create migration `011_client_user_bootstrap.py` with `upgrade()` and `downgrade()`
- [x] 1.2 Create `client_user` table mirroring `app_user` columns (id UUID PK, email, name, user_category_id UUID FK, lifecycle_status TEXT, created_at, updated_at) PLUS `role_id` UUID FK → `role.id` and `client_id` UUID FK → `client.id`; NO `institution_id` column
- [x] 1.3 Create `client_user_lifecycle_event` table mirroring `user_lifecycle_event` columns (id UUID PK, client_user_id UUID FK → client_user.id, previous_state, new_state, actor_user_id UUID, reason TEXT, timestamp TIMESTAMPTZ)
- [x] 1.4 Enable RLS + FORCE on `client_user`. Add PO CRUD policy: SELECT/INSERT/UPDATE/DELETE bypass when `app.is_platform_owner = 'true'`. Add CD own-row policy: SELECT/UPDATE WHERE `id = current_setting('app.current_user_id', true)::uuid` (the middleware sets `app.current_user_id` for CDs). CDs cannot INSERT or DELETE.
- [x] 1.5 Data-migration step: for every `app_user` row with `institution_id IS NULL`, copy the row into `client_user` (resolve `role_id` from the user's existing `role_assignment` for the `client_director` role, scope='client'), then DELETE the row from `app_user`
- [x] 1.6 Data-migration step: for each migrated user, call Supabase Admin API `PUT /auth/v1/admin/users/$ID` to set `user_metadata.user_tier = "client_leadership"`. Implement idempotency (skip if already set). Implement retry on network failure. On final failure, roll back the DB-side move so the migration is RE-runnable.
- [x] 1.7 Post-migration assertion: `SELECT count(*) FROM app_user WHERE institution_id IS NULL` returns 0. Assert inside the migration; fail loudly if not.
- [x] 1.8 Grant table permissions to `test_tenant_user` role consistent with the existing tenant-scoped tables
- [x] 1.9 Write `downgrade()` that reverses the migration (move rows back to `app_user` with nullable `institution_id`, un-set `user_metadata.user_tier`, drop both tables)

## 2. Database — app_user.institution_id NOT NULL (migration 012, BREAKING)

- [x] 2.1 Create migration `012_app_user_institution_id_not_null.py`
- [x] 2.2 In `upgrade()`: assert `SELECT count(*) FROM app_user WHERE institution_id IS NULL` returns 0 (post-011 invariant); if not, NO-OP and log a clear "Migration 011 must run first" error
- [x] 2.3 In `upgrade()`: `ALTER TABLE app_user ALTER COLUMN institution_id SET NOT NULL`
- [x] 2.4 In `downgrade()`: `ALTER TABLE app_user ALTER COLUMN institution_id DROP NOT NULL` (restores migration 008 behavior)

## 3. Backend — client_user model + repo + service layer

- [x] 3.1 Create `backend/kernel/user/models/client_user.py` with SQLAlchemy ORM model `ClientUser` matching the migration 011 schema
- [x] 3.2 Create `backend/kernel/user/models/client_user_lifecycle_event.py` with ORM model `ClientUserLifecycleEvent`
- [x] 3.3 Create `backend/kernel/user/repos/client_user_repo.py` with methods: `create`, `get_by_id`, `list_by_client`, `update`, `transition_lifecycle`, `delete` (archived transition)
- [x] 3.4 Create `backend/kernel/user/services/client_user_service.py` with methods: `bootstrap_invite`, `accept_invite`, `list_in_client`, `get_own`, `update_own`, `transition_lifecycle`, `revoke`
- [x] 3.5 Create DTOs `backend/kernel/user/services/dtos.py` adds `ClientUserCreateDTO`, `ClientUserDTO`, `ClientUserTransitionDTO`, `ClientUserUpdateDTO`. Per open question R9, `user_category_id` is REQUIRED on create for now (provisional: reuse existing `user_category` lookup with "Executive Leadership" for CDs).
- [x] 3.6 Register the new ORM models in the SQLAlchemy declarative base / imports shared by `kernel/user/models/__init__.py`
- [x] 3.7 Wire the repo and service into existing dependency providers in `backend/kernel/user/dependencies.py` (`get_client_user_service`, `get_client_user_repo`)

## 4. Backend — login flow + user_tier branch (D2, D9)

- [x] 4.1 In `backend/kernel/auth/services/service.py`, modify `login()` to read `user_metadata.user_tier` from the Supabase Auth response after credential verification
- [x] 4.2 If `user_tier == "client_leadership"`: look up the user in `client_user` (by auth `user_id`); else if `user_tier == "institution"`: look up in `app_user` as before; else: raise `AuthError("Account requires reconfiguration", status_code=403)` per D14
- [x] 4.3 For `client_leadership` logins: validate `lifecycle_status == "active"`; reject with `403 Account suspended` if not
- [x] 4.4 For `client_leadership` logins: mint a custom HS256 JWT containing `{sub, user_tier: "client_leadership", client_id, role_id, exp: now + auth.jwtExpirySeconds}`. Reuse the existing PO JWT minting path extended with the new claims.
- [x] 4.5 For `institution` logins: ensure `user_metadata.user_tier == "institution"` is stamped on every new Auth user created by `POST /api/v1/users` (existing endpoint) — modify the user-creation service to set this metadata in the Supabase Admin API `create_user` call
- [x] 4.6 Add unit tests covering all 4 login branches: `client_leadership + active`; `client_leadership + suspended`; `institution + active`; legacy-no-tier → 403 strict-fail

## 5. Backend — middleware user_tier claim handling (D9)

- [x] 5.1 In `backend/kernel/middleware.py`, decode `user_tier` claim from the HS256 JWT (if present) and set `app.current_client_id` from `client_id` for `client_leadership` tokens
- [x] 5.2 Set `app.current_user_id` (a NEW session variable) so `client_user` RLS OWN-row policy can read it; ALSO set it for institution users (so the existing `app_user` and any future own-row RLS can use it consistently)
- [x] 5.3 Verify `app.is_platform_owner` is NOT set for `client_leadership` tokens (CDs are NOT POs)
- [x] 5.4 Add middleware tests: CD request → `app.current_client_id` set, `app.is_platform_owner` unset; PO request → `app.is_platform_owner` set, `app.current_client_id` unset

## 6. Backend — PO platform endpoint surface (D4, D6)

- [x] 6.1 Create `backend/business/tenant_institution/routes/client_users.py` (or extend `platform.py`) with a router mounted at `/api/v1/platform/clients/{client_id}/users`
- [x] 6.2 Implement `POST /api/v1/platform/clients/{client_id}/users` (bootstrap): body `{email, name, role, user_category_id}`; requires `require_platform_owner`. Service: create Supabase Auth user in `invited` state (no password) with `user_metadata.user_tier = "client_leadership"`, insert `client_user` row (`lifecycle_status = "invited"`, `role_id` resolved from `role`), mint invite JWT via `kernel/auth/services/invite_token.py:mint_invite_token`, return `{user_id, invite_url, ...}`.
- [x] 6.3 Implement `GET /api/v1/platform/clients/{client_id}/users` (list): returns all `client_user` rows with `client_id == $ID` across all lifecycle states. Requires `require_platform_owner`.
- [x] 6.4 Implement `PATCH /api/v1/platform/clients/{client_id}/users/{user_id}` (transition): body `{new_state, reason}`; transitions `client_user.lifecycle_status` and inserts a `client_user_lifecycle_event` row with actor = PO. Requires `require_platform_owner`.
- [x] 6.5 Implement `DELETE /api/v1/platform/clients/{client_id}/users/{user_id}` (revoke): archives the `client_user` row AND blocks (bans) or soft-deletes the corresponding Supabase Auth user in the SAME transactional operation (per R2). Requires `require_platform_owner`.
- [x] 6.6 Implement the CD-side profile endpoints (mirror surface for the OWN-row use case per D5): `GET /api/v1/platform/clients/{client_id}/users/{user_id}` (CD can fetch their own; RLS filters siblings → 404) and `PATCH /api/v1/platform/clients/{client_id}/users/{user_id}` (CD can update own `name`; RLS filters). Both gated by `require_platform_owner` for the PO path AND a CD-self path — decide on routing strategy during apply (recommend: same endpoint, RLS does the gating).

## 7. Backend — invite accept endpoint (CD completes invite, D6)

- [x] 7.1 Reuse or extend the existing `/api/auth/activate` endpoint (from C-03) to handle the `client_leadership` tier
- [x] 7.2 When the invite JWT is verified AND the `client_user` row exists with `lifecycle_status = "invited"`: set the Supabase Auth password, mark `email_confirm = true`, transition `client_user.lifecycle_status` to `active`, insert `client_user_lifecycle_event` row with actor = the CD themselves
- [x] 7.3 Reject with `400 User is already active` if the `client_user.lifecycle_status != "invited"` (per the spec scenario "Already-active CD rejected")
- [x] 7.4 Add tests: CD accepts invite → active; invite reused → 400; invite for archived CD → 404 / 400

## 8. Backend — Casbin policy loader extension (D3)

- [x] 8.1 In `backend/kernel/authz/services/policy_loader.py`, add a SECOND source: read `client_user.role_id` mappings and push them into the enforcer as `(role, *, *, scope='client')` entries
- [x] 8.2 Make load order deterministic: institution `role_assignment` source first, `client_user.role_id` source second. Tests assert the deterministic order.
- [x] 8.3 Verify per-request role resolution for CDs reads from the JWT's `role_id` claim (NOT the enforcer) — middleware already does this; ensure no regression
- [x] 8.4 Add policy-loader tests: loaded count = `role_assignment` count + `client_user` count; CD role mappings present

## 9. Backend — tighten UserCreateDTO (D13)

- [x] 9.1 In `backend/kernel/user/services/dtos.py`, change `UserCreateDTO.institution_id` from optional to required (Pydantic `UUID` field, no default)
- [x] 9.2 Update `POST /api/v1/users` to validate `institution_id` is present (handled automatically by Pydantic; verify integration tests)
- [x] 9.3 Verify existing institution-admin → teacher creation test cases still pass with `institution_id` provided in the body
- [x] 9.4 Add an integration test that `POST /api/v1/users` without `institution_id` returns `422` post-migration-012

## 10. Backend — config.py whitelist check

- [x] 10.1 Verify `/api/v1/platform/clients/{client_id}/users` is reachable by the PO (the parent `/api/v1/platform/` is whitelisted in `config.PLATFORM_PATHS`; nested path should inherit; verify in middleware test)
- [x] 10.2 Add a middleware test asserting the nested users endpoint admits a PO JWT without `Host` header

## 11. Backend — tests aligned to acceptance criteria (AC-1 through AC-10)

- [ ] 11.1 `tests/test_client_user_bootstrap.py` covering: bootstrap returns invite_url (AC-3); CD accept-invite flow (AC-3 step 4.2); CD login mints custom HS256 JWT with correct claims (AC-2); PO list / suspend / revoke (AC-4); CD own-row selection (AC-5); CD cannot read sibling (AC-5); RLS denies CD INSERT/DELETE (AC-5)
- [ ] 11.2 `tests/test_client_user_rls.py` covering: PO reads all client_user rows (AC-6 partial); PO cannot read app_user via client_user (AC-6); PO sees zero app_user rows via middleware (AC-6, AC-7); PO cannot POST /api/v1/users (AC-6)
- [ ] 11.3 `tests/test_login_user_tier_lookup.py` covering: `client_leadership` → client_user lookup (AC-2); `institution` → app_user lookup (AC-2); no-tier → 403 strict-fail (AC-9)
- [ ] 11.4 `tests/test_migration_011_012.py` covering: 011 moves NULL rows to client_user + backfills user_tier (AC-10); 011 idempotency; 012 ALTER NotNull success; 012 NO-OP if 011 not run; 012 rollback (AC-10)
- [ ] 11.5 Extend `tests/test_c03_auth.py` (or new file) to cover the `invited → active` transition for `client_user` rows
- [ ] 11.6 Extend `tests/test_c04_authz.py` to verify the dual-source Casbin loader (AC-2 partial)

## 12. Backend — AppUser creation now stamps user_tier (D2 integrity)

- [x] 12.1 Modify `kernel/user/services/service.py:create_user` to stamp `user_metadata.user_tier = "institution"` on the new Supabase Auth user when an `app_user` is created (via existing `SupabaseAuthClient`)
- [x] 12.2 Verify the CD creating a Teacher / Student results in `user_metadata.user_tier = "institution"` on the new Auth user
- [x] 12.3 Add integration test: CD creates a teacher → the teacher's Auth user has `user_metadata.user_tier = "institution"`; teacher login resolves to `app_user` row

## 13. Backend — revoke endpoint transactional auth cleanup (R2 mitigation)

- [x] 13.1 Implement the `DELETE` endpoint so the `client_user` archive and the Supabase Auth block happen in a try/except; if either fails, roll back both sides and write a failed-revocation audit row
- [x] 13.2 Add integration test: revoke succeeds → both `client_user.archived == true` AND Supabase Auth user is banned
- [x] 13.3 Add integration test: revoke fails on the Auth block step → `client_user` row unchanged, audit row records the failure, response is `500` or `502` with a clear error

## 14. Operational — greenfield wipe (D14)

- [x] 14.1 Document the greenfield wipe procedure in `scripts/BOOTSTRAP_GUIDE.md` or a new `scripts/CLIENT_USER_GUIDE.md`: (a) delete all Supabase Auth users except `admin@school-erp.com` BEFORE running migration 011; (b) confirm `app_user` table is empty on the cloud DB; (c) then run migrations 011 + 012 in order
- [x] 14.2 Provide a one-shot cleanup script `backend/scripts/greenfield_wipe_auth_users.py` that uses the Supabase Admin API to delete all Auth users except the PO. Idempotent.

## 15. Documentation — flow doc + OpenSpec

- [x] 15.1 Update `school_erp_flow/c01_tenant_institution/_c01_flow_bootstrap_via_po.html` (or `01_platform_owner.html`) to show the NEW bootstrap step (`POST /api/v1/platform/clients/$ID/users`) instead of direct Supabase REST calls. Track separately from the spec change to avoid coupling spec approval to UI work.
- [x] 15.2 Add a flow doc entry in `school_erp_flow/client_user_bootstrap/` covering: PO bootstrap → CD accept-invite → CD login → CD manages own profile → PO suspends CD
- [x] 15.3 After apply + verify, run the OpenSpec archive step (`/opsx-archive`) to move this change into `openspec/changes/archive/<date>-add-client-user-bootstrap/` and merge the delta specs into `openspec/specs/`

## 16. Verification (verify.md)

- [x] 16.1 Create `verify.md` mapping each requirement/scenario in the spec files to the test(s) that verify it (per the openspec-verify conventions)
- [x] 16.2 Run the full test suite locally: `cd backend && uv run pytest -q` — all tests green before archive
- [x] 16.3 Run migration 011 + 012 against a fresh local DB to confirm idempotency + the post-011 assertion + the NOT NULL ALTER successfully applies
- [x] 16.4 Run the migration against the CLOUD Supabase DB after the greenfield wipe and verify the invariants hold (zero NULL `institution_id` rows in `app_user`; zero users without `user_tier` flag except the PO)