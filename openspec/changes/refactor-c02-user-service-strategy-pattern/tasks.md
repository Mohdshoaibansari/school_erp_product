# Tasks — C-02 User Service Strategy Pattern Refactor

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Source:** `design.md`, `specs/**/spec.md`, `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6-D10)

Tasks are ordered by dependency. Phase 0 fixes the P1 bugs from the audit. Phase 1 builds the strategy classes. Phase 2 wires them into a new `UserService`. Phase 3 fixes the auth-side issues. Phase 4 is the test-fidelity fix. Phase 5 is integration. Each task has a verify command or check.

---

## Phase 0: P1 Bug Fixes (do first — fixes are small and self-contained)

### T-01: Fix `request_otp` NameError
**File:** `backend/kernel/auth/services/service.py` (line 457)
**Change:** Add `ip_address: str | None = None` (and `user_agent: str | None = None`) to the `request_otp` method signature. Route extracts them from `http_request`.
**Verify:** Call `auth_service.request_otp(ctx, email)` — no `NameError`. Call `auth_service.request_otp(ctx, email, ip_address="1.2.3.4")` — log line includes `ip=1.2.3.4`.

### T-02: Add `app.current_institution_id` to RLS hook
**File:** `backend/kernel/db.py` (the `_register_rls_hook` function, around line 60)
**Change:** Add the institution_id block to the existing `if ctx.institution_id is not None:` SET LOCAL statement.
**Verify:** Run any integration test with a context that has `institution_id` set. Confirm `SHOW app.current_institution_id` returns the UUID.

### T-03: Commit migration 012 to git
**File:** `backend/migrations/versions/012_app_user_institution_id_not_null.py`
**Change:** `git add backend/migrations/versions/012_app_user_institution_id_not_null.py && git commit -m "..."
**Verify:** `git log --oneline -- backend/migrations/versions/012_app_user_institution_id_not_null.py` shows the commit.

### T-04: Reorder activate flow — commit DB first + create Supabase user with password (D11)
**File:** `backend/kernel/auth/services/service.py` (the `activate` method, ~line 350)
**Change:** 
1. Move `session.commit()` to BEFORE the Supabase call.
2. Replace `self._supabase.update_user(user_id, password=password)` with `self._supabase.create_user(user_id, email, password=password, user_metadata={"user_tier": tier})`.
3. Remove the `update_user` call entirely from the activate flow.
4. Add a try/except around the Supabase call that raises `AuthError(502)` on failure (DB is ahead; saga retry needed).
**Verify:** Trace through the activate method by hand. The order must be: set lifecycle → add event → commit → create Supabase user WITH password → emit audit.

---

## Phase 1: Strategy Classes

### T-05: Create `CDStrategy` class
**File:** `backend/kernel/user/services/strategies/cd_strategy.py` (new)
**Change:** Create a new class `CDStrategy` with methods: `create_user`, `update_user`, `delete_user`, `get_user`, `list_users`, `transition_lifecycle`. Move the logic from `ClientUserService.bootstrap_invite` and the new logic (cross-tenant check, audit emit, role assignment) into this class.
**Verify:** `cd_strategy.create_user(ctx, ClientUserCreateDTO(...))` returns `{user: ClientUserDTO, invite_url: str}`. The Supabase `user_metadata.user_tier="client_leadership"` is stamped. Audit is emitted.

### T-06: Create `InstitutionUserStrategy` class
**File:** `backend/kernel/user/services/strategies/institution_strategy.py` (new)
**Change:** Create a new class `InstitutionUserStrategy` with the same six methods. Move the logic from `IdentityUserService` (with the audit emission and role validation reordered to be BEFORE the Supabase call).
**Verify:** `institution_strategy.create_user(ctx, UserCreateDTO(...))` returns `{user: UserDTO, invite_url: str}`. Invalid `role_id` raises `ValueError` BEFORE `self._supabase.create_user(...)`.

### T-07: Define `UserStrategy` Protocol
**File:** `backend/kernel/user/services/strategies/base.py` (new)
**Change:** Create a `UserStrategy(Protocol)` class with the six method signatures. Both strategies should be type-checked against it.
**Verify:** `isinstance(cd_strategy_instance, UserStrategy)` returns True.

---

## Phase 2: `UserService` + DI wiring

### T-08: Create `StrategyResolver`
**File:** `backend/kernel/user/services/strategies/resolver.py` (new)
**Change:** Class with `resolve_for_create(dto)` (DTO type dispatch) and `resolve_for_other(ctx, user_id)` (DB lookup dispatch).
**Verify:** `StrategyResolver(cd, inst).resolve_for_create(ClientUserCreateDTO(...))` returns the CD instance. `resolve_for_other(ctx, user_id=<CD uuid>)` returns the CD instance. `resolve_for_other(ctx, user_id=<institution uuid>)` returns the institution instance.

### T-09: Create new `UserService`
**File:** `backend/kernel/user/services/service.py` (overwrite the existing class)
**Change:** Replace `IdentityUserService` with `UserService`. The class holds a `StrategyResolver` and delegates each method to the resolved strategy. Method signatures stay compatible with the route layer.
**Verify:** `user_service.create_user(ctx, ClientUserCreateDTO(...))` and `user_service.create_user(ctx, UserCreateDTO(...))` both return the unified response shape.

### T-10: Update `kernel/user/dependencies.py`
**File:** `backend/kernel/user/dependencies.py`
**Change:** The DI factory returns the new `UserService` (with the resolver and strategies wired in).
**Verify:** Calling `Depends(get_identity_user_service)` returns a `UserService` instance.

### T-11: Update `kernel/business/tenant_institution/dependencies.py`
**File:** `backend/business/tenant_institution/dependencies.py`
**Change:** The DI factory returns the same `UserService` (so the PO bootstrap route uses the unified service).
**Verify:** Calling the bootstrap DI returns a `UserService` instance.

### T-12: Update `kernel/business/tenant_institution/routes/client_users.py`
**File:** `backend/business/tenant_institution/routes/client_users.py`
**Change:** The PO bootstrap route (`POST /api/v1/platform/clients/{id}/users`) calls `await user_service.create_user(ctx, ClientUserCreateDTO(...))` instead of `svc.bootstrap_invite(...)`. The response model becomes `UserCreateResponseDTO`.
**Verify:** Bootstrap endpoint returns `{user, invite_url}`. The unified response shape.

### T-13: Delete `ClientUserService`
**File:** `backend/kernel/user/services/client_user_service.py`
**Change:** Delete the file.
**Verify:** No remaining imports of `ClientUserService` in the codebase. `grep -r "ClientUserService" backend/` returns no matches.

### T-14: Update `kernel/user/routes/users.py` to remove the old comment
**File:** `backend/kernel/user/routes/users.py` (line 31 area)
**Change:** The permission resource name is `user` (per D10 bug #10). Verify the route uses `require_permission("user", "create")` (not `client_user` or `institution_user`).
**Verify:** `grep "require_permission" backend/kernel/user/routes/users.py` shows `"user"` resource.

---

## Phase 3: Auth-Side Fixes

### T-15: Add cross-tenant check to CD login branch
**File:** `backend/kernel/auth/services/service.py` (the `user_tier == "client_leadership"` branch in `login`, around line 200)
**Change:** Add the cross-tenant check BEFORE minting the CD JWT: `if ctx.client_id and user_obj.client_id != ctx.client_id and "platform_owner" not in (ctx.roles or []): raise AuthError("Access denied. Account does not belong to this client.", 403)`.
**Verify:** A CD from client A attempting to log in from client B's subdomain gets a 403.

### T-16: Fix `request_otp` signature (T-01 already covered — but the route must also pass ip_address)
**File:** `backend/kernel/auth/routes/auth.py` (the `otp_request` route)
**Change:** Extract `client_ip` from `http_request` and pass it to `auth_service.request_otp(ctx, email, ip_address=client_ip)`.
**Verify:** `POST /api/auth/otp/request` no longer raises `NameError`.

### T-17: Add `LoginResponse` model
**File:** `backend/kernel/auth/routes/auth.py`
**Change:** Add a `LoginResponse` Pydantic model with optional `is_platform_owner`, `user_tier`, `client_id` fields. Replace `TokenResponse` in the login route's `response_model=`.
**Verify:** `POST /api/auth/login` response JSON contains `is_platform_owner`, `user_tier`, `client_id` as appropriate to the tier.

### T-18: Reorder activate flow (T-04 already covered — but verify the implementation)

### T-19: Update activate route to use unified `ActivateResponse` (already present in predecessor, verify)
**File:** `backend/kernel/auth/routes/auth.py` (the `activate` route)
**Change:** Confirm `response_model=ActivateResponse` is set (it is in the predecessor). No change needed if already correct.
**Verify:** `POST /api/auth/activate` returns `{message, user_id, user_tier, client_slug}`.

### T-19.1: Add `set_rls_session_vars` helper to `kernel/db.py`
**File:** `backend/kernel/db.py` (new function, near the existing `_register_rls_hook`)
**Change:** Add a public function `set_rls_session_vars(session, *, user_id=None, client_id=None, institution_id=None, is_platform_owner=False)` that runs `SET LOCAL` for each provided variable. See design doc §8.5.
**Verify:** Calling `set_rls_session_vars(session, user_id=uuid, client_id=uuid)` runs `SET LOCAL app.current_user_id = '<uuid>'` and `SET LOCAL app.current_client_id = '<uuid>'`. A subsequent query can read the values via `current_setting()`.

### T-19.2: Re-architect activate service to use the two-session pattern
**File:** `backend/kernel/auth/services/service.py` (the `activate` method, ~line 350)
**Change:** Rewrite the activate method to:
1. Verify the invite token → extract `user_id`
2. Open a short-lived elevated session (call `set_rls_session_vars(session, is_platform_owner=True)`)
3. Look up the user record (CD or institution), read `client_id` and `institution_id`
4. Close the elevated session
5. Open a new session (call `set_rls_session_vars(session, user_id=..., client_id=..., institution_id=...)`)
6. Do the activate work: set lifecycle, record event, commit
7. Close the session
8. Call `self._supabase.update_user(...)` (no DB)
9. Emit audit with `actor=user_id_from_token` (NOT `ctx.user_id`)

DO NOT set `_tenant_context_var` from the service (A6 invariant). The full identity is held in memory in the service's local variables.
**Verify:** Call `auth_service.activate(subdomain_only_ctx, invite_token, password)`:
- The user lookup succeeds (RLS doesn't block because the session has `app.is_platform_owner = 'true'`)
- The commit succeeds (RLS doesn't block because the session has `app.current_user_id`, `app.current_client_id`, `app.current_institution_id` set)
- The Supabase call succeeds
- The audit emit has `actor=user_id_from_token` (not `ctx.user_id` which is `None`)

### T-19.3: Add a regression test for the unauthenticated-activate flow
**File:** `backend/tests/test_c03_auth.py` (new test method)
**Change:** Create a user in `invited` state. Call `auth_service.activate(subdomain_only_ctx, invite_token, password)` with a `TenantContext` that has `user_id=None`. Assert the activation succeeds and the audit `actor` is the user's UUID (from the token), not `None`.
**Verify:** The test passes. The user is in `active` state in the DB, the password is set in Supabase, and the audit record has the proper `actor`.

### T-20: Fix `FakeSupabaseAuth.update_user` overwrite semantics
**File:** `backend/tests/fake_supabase_auth.py` (line ~168)
**Change:** Replace `user["user_metadata"].update(user_metadata)` with `user["user_metadata"] = user_metadata`. Matches real impl.
**Verify:** A test that calls `fake.update_user(user_id, user_metadata={"a": 1})` then `fake.update_user(user_id, user_metadata={"b": 2})` — final `user["user_metadata"]` is `{"b": 2}` (not `{"a": 1, "b": 2}`).

### T-20.1: Add `password` parameter to `SupabaseAuthClient.create_user` (D11)
**File:** `backend/kernel/auth/supabase_client.py` (Protocol + Impl)
**Change:** Add `password: str | None = None` keyword-only parameter to both the `SupabaseAuthClient` Protocol and `SupabaseAuthClientImpl.create_user`. When provided, include `"password": password` in the httpx payload.
**Verify:** `create_user(user_id, email, password="test123")` sends `password` in the payload. `create_user(user_id, email)` (no password) works as before.

### T-20.2: Add `password` parameter to `FakeSupabaseAuth.create_user` (D11)
**File:** `backend/tests/fake_supabase_auth.py`
**Change:** Add `password: str | None = None` keyword-only parameter to `FakeSupabaseAuth.create_user`. When provided, store the password on the user record.
**Verify:** `fake.create_user(user_id, email, password="test123")` stores the password. `fake.sign_in_with_password(email, "test123")` succeeds.

### T-20.3: Remove Supabase create_user from `CDStrategy.create_user` (D11)
**File:** `backend/kernel/user/services/strategies/cd_strategy.py`
**Change:** Remove the `self._supabase.create_user(...)` call and its associated logging from the `create_user` method. The bootstrap creates only the DB row and mints the invite JWT.
**Verify:** `cd_strategy.create_user(ctx, ClientUserCreateDTO(...))` returns `{user, invite_url}` without calling Supabase. No `SupabaseAuthError` can be raised from bootstrap.

### T-20.4: Remove Supabase create_user from `InstitutionUserStrategy.create_user` (D11)
**File:** `backend/kernel/user/services/strategies/institution_strategy.py`
**Change:** Remove the `self._supabase.create_user(...)` call and its associated try/except from the `create_user` method. The bootstrap creates only the DB row, assigns role, and mints the invite JWT.
**Verify:** `institution_strategy.create_user(ctx, UserCreateDTO(...))` returns `{user, invite_url}` without calling Supabase. No `SupabaseAuthError` can be raised from bootstrap.

### T-20.5: Update activate flow to create Supabase user with password (D11)
**File:** `backend/kernel/auth/services/service.py` (the `activate` method)
**Change:** After DB commit, call `self._supabase.create_user(user_id, email, password=password, user_metadata={"user_tier": user_tier})` instead of `self._supabase.update_user(user_id, password=password)`. Remove the `update_user` call entirely.
**Verify:** The activate flow creates the Supabase Auth user WITH password. `sign_in_with_password(email, password)` succeeds after activation.

### T-20.6: Update tests for D11 flow
**File:** `backend/tests/test_c02_user.py`, `backend/tests/test_c03_auth.py`
**Change:** 
- Update `test_c02_service_accepts_supabase_client` — no Supabase call during create_user
- Update `test_c02_create_user_propagates_to_supabase` — Supabase user NOT created during bootstrap
- Update `test_c02_create_user_supabase_failure_rolls_back` — no Supabase failure at bootstrap (remove or repurpose)
- Update `test_integration_full_auth_flow` — activate creates Supabase user, no prior `fake.create_user` + `fake.update_user` needed
- Add test: activate with valid password creates Supabase user and login succeeds
- Add test: activate failure after DB commit leaves user active but no Supabase user
**Verify:** All tests pass.

---

## Phase 6: D12 — `user_account` parent table

### T-30.1: Create `UserAccount` model
**File:** `backend/kernel/user/models/user_account.py` (new)
**Change:** Create `UserAccount(Base)` with `id: Mapped[uuid.UUID] = mapped_column(primary_key=True)`. No other columns — it's a pure identity anchor.
**Verify:** Model imports, table name is `user_account`.

### T-30.2: Update `AppUser` model with FK to `UserAccount`
**File:** `backend/kernel/user/models/user.py`
**Change:** Add `id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), primary_key=True)` — the PK becomes a FK to the parent. Import `UserAccount`.
**Verify:** `AppUser.id` references `user_account.id`.

### T-30.3: Update `ClientUser` model with FK to `UserAccount`
**File:** `backend/kernel/user/models/client_user.py`
**Change:** Same as T-30.2 — `id` FK to `user_account.id`.
**Verify:** `ClientUser.id` references `user_account.id`.

### T-30.4: Update `RoleAssignment` and `LoginAttempt` FKs
**File:** `backend/kernel/user/models/role_assignment.py`, `backend/kernel/auth/models/login_attempt.py`
**Change:** Change `user_id` FK from `ForeignKey("app_user.id")` to `ForeignKey("user_account.id")`.
**Verify:** Both models reference `user_account.id`.

### T-30.5: Update `user_repo.create()` to insert `user_account` first
**File:** `backend/kernel/user/repos/user_repo.py`
**Change:** Before inserting `app_user`, insert `user_account` row with the same UUID. Use raw SQL or ORM. The UUID is generated in the strategy and passed to `repo.create(session, ctx, dto, user_id=uuid)`.
**Verify:** Creating an institution user results in both `user_account` and `app_user` rows.

### T-30.6: Update `client_user_repo.create()` to insert `user_account` first
**File:** `backend/kernel/user/repos/client_user_repo.py`
**Change:** Same pattern as T-30.5 — insert `user_account` before `client_user`.
**Verify:** Creating a CD results in both `user_account` and `client_user` rows.

### T-30.7: Create migration `015_user_account_parent_table.py`
**File:** `backend/migrations/versions/015_user_account_parent_table.py` (new)
**Change:** 
1. CREATE TABLE `user_account` (id UUID PK)
2. INSERT INTO `user_account` SELECT id FROM `app_user` UNION SELECT id FROM `client_user`
3. ALTER TABLE `app_user` ADD FK (id) REFERENCES `user_account(id)`
4. ALTER TABLE `client_user` ADD FK (id) REFERENCES `user_account(id)`
5. DROP old FK on `role_assignment.user_id`
6. ADD new FK on `role_assignment.user_id` REFERENCES `user_account(id)`
7. DROP old FK on `login_attempt.user_id`
8. ADD new FK on `login_attempt.user_id` REFERENCES `user_account(id)`
**Verify:** `alembic upgrade head` succeeds. `role_assignment` accepts CD user UUIDs.

### T-30.8: Update CDStrategy to insert `role_assignment` + update bootstrap.py
**File:** `backend/kernel/user/services/strategies/cd_strategy.py`, `backend/kernel/auth/bootstrap.py`
**Change:** 
- CDStrategy: `create_user` inserts `role_assignment` row after `client_user` (now works with D12 FK)
- bootstrap.py: insert `user_account` before `app_user` for platform owner
**Verify:** CD creation inserts `role_assignment` row. Platform Owner bootstrap inserts `user_account` + `app_user`.

---

## Phase 4: Tests

### T-21: Update `test_c02_user.py` to use the new DTO shapes
**File:** `backend/tests/test_c02_user.py`
**Change:** Update test fixtures to construct `ClientUserCreateDTO` and `UserCreateDTO` correctly. Update assertions to read the unified response shape (`response.json()["user"]["id"]`).
**Verify:** The test suite runs without errors related to response shape.

### T-22: Update `test_c03_auth.py` to use the unified `LoginResponse`
**File:** `backend/tests/test_c03_auth.py`
**Change:** Update login tests to expect the new `LoginResponse` fields. Update the user_tier fixture stamping (already done in D5 fix). Update the activate flow test to expect the unified response.
**Verify:** Login integration tests pass with the new shape.

### T-23: Add a regression test for the cross-tenant check on CD login
**File:** `backend/tests/test_c03_auth.py` (new test method)
**Change:** Create a CD in client A, log in from client B's subdomain, assert 403.
**Verify:** The test passes — 403 is returned for cross-tenant CD login.

### T-24: Add a regression test for the activate transaction ordering
**File:** `backend/tests/test_c03_auth.py` (new test method)
**Change:** Mock `self._supabase.update_user` to raise an exception. Call activate. Assert the user record's lifecycle_status is "active" in the DB (DB committed before Supabase).
**Verify:** The test passes — the user record is in `active` state even though Supabase failed.

### T-25: Add a regression test for `FakeSupabaseAuth.update_user` overwrite semantics
**File:** `backend/tests/test_c02_user.py` (new test method)
**Change:** Call `fake.update_user` twice with different `user_metadata` dicts. Assert the second call replaces the first.
**Verify:** The test passes — the second `user_metadata` overwrites the first.

---

## Phase 5: Integration

### T-26: Full test suite — zero regressions
**Command:** `cd backend && .venv/Scripts/python -m pytest tests/ -x --tb=short`
**Verify:** All tests pass.

### T-27: Manual journey flow verification
**Manual:** Run all affected journey flows (`01`, `02`, `09`) in sequence. Confirm each step completes and the HTML UI reflects expected outcomes.
**Verify:** All flows complete end-to-end without errors.

### T-28: Update journey flow HTML for the unified response shape
**File:** `backend/static/journey_flows/*.html`
**Change:** The flows already use the unified shape from the predecessor (Step 7 of Flow 01, Step 5 of Flow 02, etc.). Verify the refactor doesn't break any extraction paths.
**Verify:** Open the journey flow HTML files and check that `user.id`, `invite_url`, `user_tier`, `client_slug` are correctly extracted.

---

## Total: 49 tasks

| Phase | Task count | Critical path? |
|---|---|---|
| Phase 0 (P1 bug fixes) | 4 | YES — do first |
| Phase 1 (Strategy classes) | 3 | YES — do before Phase 2 |
| Phase 2 (UserService + DI) | 7 | YES — core refactor |
| Phase 3 (Auth-side fixes) | 9 | YES — required for correct login/activate |
| Phase 4 (Tests) | 5 | YES — verify the refactor |
| Phase 5 (Integration) | 3 | YES — final validation |
| D11 tasks (T-20.1 – T-20.6) | 6 | YES — fixes the Supabase "User not allowed" blocker |
| D12 tasks (T-30.1 – T-30.8) | 8 | YES — fixes cross-tier FK integrity for role_assignment + login_attempt |

## Recommended order of execution

1. Phase 0 first (4 tasks) — fixes P1 bugs that block the rest
2. Phase 1 (3 tasks) — strategy classes
3. Phase 2 (7 tasks) — `UserService` + DI + bootstrap route
4. Phase 3 (6 tasks) — auth-side fixes
5. Phase 4 (5 tasks) — test updates
6. Phase 5 (3 tasks) — integration validation

Total estimated effort: ~2-3 days of focused work.
