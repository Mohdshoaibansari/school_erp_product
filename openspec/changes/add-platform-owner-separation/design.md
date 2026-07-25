## Context

The platform owner is currently stored in the tenant-scoped `app_user` table with a `client_id` binding to the `test-school` client. This ties the platform-level administrator to a single tenant. Login from other subdomains fails because the cross-tenant check blocks users whose `client_id` doesn't match the subdomain.

The middleware detects platform owner through two mechanisms:
1. Path prefix `/api/v1/platform/` → sets `is_platform_owner=True`
2. Database role lookup → if `platform_owner` role found → sets `is_platform_owner=True`

Both are problematic: path prefix detection means any valid JWT can access platform endpoints; DB role lookup is a per-request query adding latency.

## Goals / Non-Goals

**Goals:**
- Remove platform owner from `app_user` table — exist only in Supabase Auth
- Detect platform owner from JWT claim only (source of truth)
- Allow platform owner to operate without subdomain/Host header
- Block platform owner from accessing institution-scoped data (tenant endpoints)
- Retain all existing platform endpoint functionality

**Non-Goals:**
- Frontend implementation (deferred)
- Changes to Casbin model or enforcer
- Changes to `SupabaseAuthClient` protocol
- New platform endpoints

## Decisions

### D1: Platform owner identity in Supabase Auth only
Platform owner user exists ONLY in Supabase Auth with `user_metadata.is_platform_owner = true`. No `app_user` row. **Rationale**: Supabase Auth is the identity source of truth. Tenant-scoped tables shouldn't hold platform-wide users.

### D2/D16: Login flow for platform owner
After Supabase Auth authentication, the auth service checks `user_metadata.is_platform_owner` via Supabase Auth Admin API. If true, the auth service skips `app_user` lookup entirely and constructs a JWT with `{sub, is_platform_owner: true}`. **Rationale**: Platform owner has no `app_user` row, so the lookup would always fail. The metadata check is the authoritative source.

### D3: JWT structure
Platform owner JWT: `{sub: <uuid>, is_platform_owner: true}`. No `client_id` or `institution_id`. Normal user JWT: unchanged. **Rationale**: Platform owner is not bound to any tenant, so tenant-scoped fields would be misleading.

### D8/D9: Middleware detection
Middleware reads JWT claim `is_platform_owner`. If true: skips subdomain resolution, sets `client_id=None`, `institution_id=None`, `is_platform_owner=True`, `roles=[]`. Removes: path prefix detection, DB role lookup query. **Rationale**: JWT is the single source of truth. Removing DB query reduces per-request overhead.

### D5/D18: Path whitelist
Middleware maintains a config file (`config.py`) with a whitelist of paths that don't require `client_id`. Platform owner with `client_id=None` is blocked (403) on any path not in the whitelist. **Rationale**: Defense-in-depth — even if `require_platform_owner` is missing from an endpoint, the middleware blocks access.

### D11/D24: require_platform_owner dependency
The dependency reads JWT from `Authorization` header, decodes it, and verifies `is_platform_owner: true` directly. Doesn't rely on middleware's `TenantContext`. **Rationale**: Double verification — middleware could be misconfigured, but the dependency independently validates the JWT.

### D14: Client table RLS
Add RLS policy on `client` table: `(app.is_platform_owner = 'true')` bypass. **Rationale**: The middleware already sets `SET LOCAL app.is_platform_owner = 'true'` for subdomain resolution. Extending this to the `client` table RLS provides defense-in-depth.

### D36: Repo base tenant filter
`_base_query` checks `ctx.is_platform_owner`. If true, skips tenant filter. **Rationale**: Platform owner with `client_id=None` would get zero results from tenant-filtered queries. The skip allows platform owner to list all data across clients.

## Risks / Trade-offs

- **[Breaking Change]**: Existing platform owner credentials stop working. → Migration script creates new credentials and documents them.
- **[Auth dependency]**: Auth service now calls Supabase Auth Admin API during login (previously only used `sign_in_with_password`). → The Admin API call is lightweight; latency is acceptable for the rare platform owner login.
- **[Test impact]**: Many tests create platform owner users in `app_user`. → Update test fixtures to mint platform owner JWTs directly without `app_user` rows. The `mint_test_jwt(is_platform_owner=True)` function already supports this.
- **[Middleware simplification]**: Removing role lookup removes the only way to populate `TenantContext.roles` from the DB. → Normal users still get roles from `_cached_auth` or Casbin lookups; platform owner doesn't need roles.

## Migration Plan

1. Run migration script (`scripts/migrate_platform_owner.py`):
   - Delete existing platform owner from `role_assignment` and `app_user`
   - Create new Supabase Auth user (`admin@school-erp.com`, password `Platform@2026!`) with `user_metadata.is_platform_owner = true`
2. Run migration `007_platform_owner_rls.py` to add RLS policy on `client` table
3. Deploy code changes (middleware, auth service, dependencies, repo base)
4. Update `.env` / `config.py` with whitelist paths
5. Verify: platform owner login without Host header, platform endpoints work, tenant endpoints blocked
6. Rollback: revert middleware changes, restore platform owner in `app_user` from backup

## Open Questions

- None — all 36 decisions locked in grill-me session.
