## 1. Configuration

- [ ] 1.1 Create `backend/config.py` with `PLATFORM_PATHS` whitelist (`/api/v1/platform/`, `/api/auth/`, `/health`)

## 2. Auth Service — Platform Owner Login

- [ ] 2.1 Modify `kernel/auth/services/service.py` login flow: after Supabase Auth success, check `user_metadata.is_platform_owner` via Supabase Auth Admin API
- [ ] 2.2 If `is_platform_owner=true`: skip `app_user` lookup, add `is_platform_owner: true` to JWT payload, add `is_platform_owner: true` to login response
- [ ] 2.3 Ensure normal user login flow is unchanged (existing tests pass)

## 3. Middleware — Platform Owner Detection

- [ ] 3.1 Remove DB role lookup query (lines 270-285 in `kernel/middleware.py`)
- [ ] 3.2 Remove path prefix detection (`_PLATFORM_PREFIX` → `is_platform_owner=True`)
- [ ] 3.3 Detect platform owner ONLY from JWT claim `is_platform_owner: true`
- [ ] 3.4 If `is_platform_owner=true`: skip subdomain resolution, set `client_id=None`, `institution_id=None`, `roles=[]`
- [ ] 3.5 Add whitelist check: block (403) if `is_platform_owner=true`, `client_id=None`, and path not in `PLATFORM_PATHS`

## 4. Dependencies

- [ ] 4.1 Update `require_platform_owner` in `kernel/tenant_context.py`: decode JWT from `Authorization` header, verify `is_platform_owner: true` claim directly
- [ ] 4.2 Update `_base_query` in `kernel/repo_base.py`: skip tenant filter when `ctx.is_platform_owner = True`
- [ ] 4.3 Update `list_users` in `kernel/user/routes/users.py`: skip tenant filter when `ctx.is_platform_owner = True`

## 5. Database

- [ ] 5.1 Create migration `007_platform_owner_rls.py`: add RLS policy on `client` table allowing access when `app.is_platform_owner = 'true'`
- [ ] 5.2 Create `scripts/migrate_platform_owner.py`: delete existing platform owner from `role_assignment` and `app_user`, create new Supabase Auth user (`admin@school-erp.com`, password `Platform@2026!`) with `user_metadata.is_platform_owner = true`

## 6. Tests

- [ ] 6.1 Update test fixtures in `conftest.py`: platform owner tests use `mint_test_jwt(is_platform_owner=True)` without `app_user` row
- [ ] 6.2 Add test: platform owner login returns `is_platform_owner: true` in JWT and response
- [ ] 6.3 Add test: platform owner JWT has no `client_id` or `institution_id`
- [ ] 6.4 Add test: middleware sets `client_id=None` for platform owner
- [ ] 6.5 Add test: platform owner blocked (403) from tenant endpoints
- [ ] 6.6 Add test: `require_platform_owner` validates JWT claim directly
- [ ] 6.7 Add test: `_base_query` skips tenant filter for platform owner
- [ ] 6.8 Ensure all existing tests pass (no regressions)
