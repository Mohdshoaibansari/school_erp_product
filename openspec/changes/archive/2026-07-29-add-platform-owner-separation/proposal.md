## Why

The platform owner is currently stored in the tenant-scoped `app_user` table with a `client_id` binding to `test-school`. This ties the platform-level administrator to a specific tenant, causing login failures from other subdomains and violating the principle that platform-wide users should not be domain-bound. The platform owner must operate independently of any client to manage all tenants without institution-level data access.

## What Changes

- **BREAKING**: Remove platform owner from `app_user` table — platform owner exists only in Supabase Auth with `user_metadata.is_platform_owner = true`
- Login flow: if Supabase Auth user metadata has `is_platform_owner = true`, skip `app_user` lookup and return a platform-level JWT with no `client_id` or `institution_id`
- JWT: platform owner token contains `{sub, is_platform_owner: true}` only — no tenant binding
- Middleware: detect platform owner ONLY from JWT claim `is_platform_owner: true`; remove DB role lookup and path prefix detection
- Middleware: skip subdomain resolution for platform owner (no Host header required)
- `require_platform_owner` dependency: validate JWT claim directly for defense-in-depth
- Repo base class: skip tenant filter when `ctx.is_platform_owner = True`
- RLS: add policy on `client` table allowing access when `app.is_platform_owner = true`
- Migration script: delete existing platform owner from `app_user` + `role_assignment`, create new Supabase Auth user (`admin@school-erp.com`) with metadata flag
- Whitelist: configurable list of paths not requiring `client_id` (platform endpoints, auth, health)

## Capabilities

### New Capabilities
- `platform-owner-separation`: Platform-level super-admin exists only in Supabase Auth, not in tenant-scoped `app_user`. Can manage all clients without domain binding. Cannot access institution-scoped data.

### Modified Capabilities
- `tenant-institution`: Platform endpoints (`/api/v1/platform/clients`, etc.) now use JWT-based platform owner detection instead of DB role lookup. Client RLS policy updated with platform owner bypass.

## Impact

- **kernel/middleware.py**: Remove role lookup query and path prefix detection; add JWT-only platform owner detection; skip subdomain resolution
- **kernel/auth/services/service.py**: Check Supabase Auth user metadata before `app_user` lookup; skip `app_user` lookup for platform owner; add `is_platform_owner` to JWT and login response
- **kernel/authz/dependencies.py**: `require_platform_owner` to decode JWT directly from `Authorization` header
- **kernel/repo_base.py**: Skip tenant filter for platform owner
- **kernel/user/routes/users.py**: `list_users` skips tenant filter for platform owner
- **config.py** (new): Whitelist of paths not requiring `client_id`
- **migrations/versions/007**: RLS policy on `client` table
- **scripts/migrate_platform_owner.py** (new): One-time migration script
- **openspec/specs/tenant-institution/spec.md** (delta): Platform owner detection changes
