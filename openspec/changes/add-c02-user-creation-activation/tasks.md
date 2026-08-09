# Tasks — C-02 User Creation & Activation

> **Change ID:** `add-c02-user-creation-activation`
> **Source:** `design.md`, `specs/**/spec.md`

Tasks are ordered by dependency: prerequisite bug fixes first, then infrastructure, then feature work, then integration/testing.

---

## Phase 1: Prerequisites — D5 Bug Fixes

### T-01: Fix `update_user` NameError in supabase_client.py ✅
**File:** `backend/kernel/auth/supabase_client.py`
**Change:** Add `user_metadata: dict | None = None` to `SupabaseAuthClientImpl.update_user()` signature (line ~256). The body at line ~270 already references `user_metadata`; only the signature is missing.
**Verify:** Run any activation test that calls `update_user` with `user_metadata`; confirm no `NameError`. Existing tests must continue to pass.

### T-02: Add RLS session-variable hook to middleware ✅
**File:** `backend/kernel/db.py` (SQLAlchemy event listener)
**Change:** After `TenantContext` is resolved, execute `SET LOCAL app.is_platform_owner`, `SET LOCAL app.current_client_id`, `SET LOCAL app.current_user_id` on the endpoint's database session. Uses a SQLAlchemy `event.listen()` on `engine.connect` that reads TenantContext from the contextvar.
**Verify:** 
- Authenticated request: `SHOW app.current_user_id` returns the user's UUID.
- Platform Owner request: `SHOW app.is_platform_owner` returns `'true'`.
- Unauthenticated activate request: session vars are NULL but endpoint does not error.

### T-03: Populate `app.current_user_id` from TenantContext ✅
**File:** Same hook as T-02 (`backend/kernel/db.py`)
**Change:** In the RLS session-var hook, set `SET LOCAL app.current_user_id = '<ctx.user_id>'` when `ctx.user_id` is not None; otherwise leave NULL.
**Verify:** CD own-row SELECT (RLS policy `client_user_cd_select_own`) returns only the CD's own row when `app.current_user_id` matches.

### T-04: Update conftest.py RLS bypass ✅
**File:** `tests/conftest.py`
**Change:** Updated comment on line ~142 (`SET LOCAL app.is_platform_owner = 'true'`) to clarify it's cleanup-only. Per-test RLS context is now set by the production hook in `kernel/db.py` which reads TenantContext from the contextvar.
**Verify:** Test suite passes without the blanket bypass; tests that need platform-owner context explicitly set it.

---

## Phase 2: Configuration Infrastructure

### T-05: Create migration for app.activationBaseUrl ✅
**File:** `backend/migrations/versions/013_add_activation_base_url.py`
**Change:** Seed `app.activationBaseUrl` config key with type `string`, default `"http://127.0.0.1:8000"`, category `Business Rules`, module `app`.
**Verify:** After migration: `SELECT * FROM configuration_key WHERE key = 'app.activationBaseUrl'` returns one row. Local dev invite URLs use the default.

### T-06: Replace hardcoded URL in client_user_service.py ✅
**File:** `backend/kernel/user/services/client_user_service.py`
**Change:** Replaced `frontend_url = "http://127.0.0.1:8000"` (line ~91) with `frontend_url = config.get("app.activationBaseUrl") or "http://127.0.0.1:8000"`.
**Verify:** CD bootstrap still returns a valid `invite_url`. When config is overridden, the URL reflects the override.

---

## Phase 3: Feature Implementation — C-02 Identity & User Management

### T-07: Add optional role_id to UserCreateDTO ✅
**File:** `backend/kernel/user/services/dtos.py`
**Change:** Added `role_id: uuid.UUID | None = None` to `UserCreateDTO`.
**Verify:** DTO serialization works with and without `role_id`. Existing tests that construct `UserCreateDTO` without `role_id` continue to pass.

### T-08: Assign role atomically in create_user service ✅
**File:** `backend/kernel/user/services/service.py`
**Change:** In the `create_user` method, after inserting the `app_user` row, if `dto.role_id` is provided:
- Validate that the role exists via SELECT on the role table
- Insert a `role_assignment` row in the same transaction
- Roll back if role is invalid
**Verify:** 
- Create user with valid `role_id` → `role_assignment` row exists; user created.
- Create user with invalid `role_id` → 400; no user created.
- Create user without `role_id` → user created; no role_assignment.

### T-09: Mint invite JWT and return invite_url in create_user ✅
**File:** `backend/kernel/user/services/service.py`
**Change:** After user row and role are committed:
- Call `mint_invite_token(user_id, email)` from `kernel/auth/services/invite_token.py`
- Build `invite_url = f"{config.get('app.activationBaseUrl')}/activate?token={invite_jwt}"`
- Changed response from `UserDTO` to `{user: UserDTO, invite_url: str}`
**Verify:** `POST /api/v1/users` response includes `user` and `invite_url`. The `invite_url` contains a valid JWT that `verify_invite_token()` can decode.

### T-10: Update POST /api/v1/users route response schema ✅
**File:** `backend/kernel/user/routes/users.py`
**Change:** Updated the route's response model to `UserCreateResponseDTO` reflecting `{user: UserDTO, invite_url: str}`.
**Verify:** OpenAPI schema reflects the new response shape. Journey flows receive the new fields.

---

## Phase 4: Feature Implementation — C-03 Authentication

### T-11: Add client_slug and user_tier to activate response ✅
**File:** `backend/kernel/auth/services/service.py` (activate method)
**Change:** After the user is activated:
- Resolve `client_slug`: for `client_user`, `SELECT client.slug FROM client WHERE id = client_user.client_id`; for `app_user`, join through `institution` to `client.slug`
- Determine `user_tier`: `"client_leadership"` for `client_user`, `"institution"` for `app_user`
- Changed return from `{message, user_id}` to `{message, user_id, user_tier, client_slug}`
**Verify:** 
- Activate CD → `user_tier: "client_leadership"`, `client_slug` is correct.
- Activate institution user → `user_tier: "institution"`, `client_slug` is correct.
- Response does NOT contain `access_token` or `refresh_token`.

### T-12: Update activate route response schema ✅
**File:** `backend/kernel/auth/routes/auth.py`
**Change:** Added `ActivateResponse` Pydantic model with `user_tier: str` and `client_slug: str`. Updated the activate endpoint to use `response_model=ActivateResponse`.
**Verify:** OpenAPI schema reflects the new response shape.

---

## Phase 5: Journey Flow HTML Updates

### T-13: Update 02_client_director.html — user creation and activation ✅
**File:** `backend/static/journey_flows/02_client_director.html`
**Changes:**
- Steps 5, 8, 10 that call `POST /api/v1/users`: updated response handling to extract `user.id` and `invite_url` from the new shape
- Steps 7, 9, 11 that used Supabase Admin API (`PUT auth/v1/admin/users`) plus lifecycle transitions: **removed** and replaced with extract-token + backend `POST /api/auth/activate` calls
- Removed all `invited→pending→active` lifecycle transition steps (activate handles it directly)
**Verify:** Run the HTML flow in a browser. No `SUPABASE_SERVICE_ROLE_KEY` usage remains for user activation. All user types activate through the backend.

### T-14: Update 01_platform_owner.html — step 7 activate response ✅
**File:** `backend/static/journey_flows/01_platform_owner.html`
**Change:** Updated step 7 (activate call) to extract the new response fields: `user_tier`, `client_slug`. Updated expected response note.
**Verify:** Flow runs end-to-end: PO creates CD → CD activates → redirected to `{client_slug}.localhost:8000/login`.

### T-15: Update 09_platform_bootstrap.html — Supabase Admin workaround removal ✅
**File:** `backend/static/journey_flows/09_platform_bootstrap.html`
**Changes:**
- Steps 9c-9d (Supabase Admin API calls + lifecycle transitions): **removed and replaced** with extract-token + backend `POST /api/auth/activate`
- Updated prerequisite note: no `SUPABASE_SERVICE_ROLE_KEY` needed
- Institution users now activate through the backend
**Verify:** Full platform bootstrap flow works without Supabase Admin API calls.

---

## Phase 6: Integration Testing & Verification

### T-16: End-to-end test — institution user creation + activation
**Test:** New test in `tests/` that:
1. Creates an institution user via `POST /api/v1/users` with `role_id`
2. Asserts response has `user` and `invite_url`
3. Extracts token from `invite_url`
4. Calls `POST /api/auth/activate` with the token + password
5. Asserts response has `message`, `user_id`, `user_tier="institution"`, `client_slug`
6. Asserts `POST /api/auth/login` works with the new password
**Status:** Requires running test suite with Supabase running. Integration tests depend on live DB.

### T-17: End-to-end test — CD creation + activation (regression)
**Test:** New or existing test that:
1. Creates a CD via `POST /api/v1/platform/clients/{id}/users`
2. Asserts `invite_url` uses config value
3. Activates via `POST /api/auth/activate`
4. Asserts response has `user_tier="client_leadership"` and valid `client_slug`
5. Asserts login works
**Status:** Requires running test suite with Supabase running.

### T-18: Test — activate edge cases
**Test:** New tests covering:
- Activate with expired token → 400
- Activate with tampered token → 400
- Activate already-active user → 400
- Activate with weak password → 400/502
- Activate with non-existent user_id → 404
**Status:** Requires running test suite with Supabase running.

### T-19: Full test suite — zero regressions
**Command:** Run the full test suite.
**Status:** Python compilation check passed (all files compile). Full test run requires Supabase stack running.

### T-20: Manual journey flow verification
**Manual:** Run all affected journey flows (`01`, `02`, `09`) in sequence. Confirm each step completes and the HTML UI reflects expected outcomes.
**Status:** HTML files updated. Manual browser verification requires backend running.
